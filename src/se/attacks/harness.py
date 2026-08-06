"""Shared harness for the Phase 2 attack experiments.

Holds the bits every week-script reuses: load Llama and NLI co-resident,
select attackable questions by correctness, run a batch of attacks with
JSONL checkpointing (the Week 9 scale-up is a multi-day run that must be
resumable), and compute the AUROC-degradation summary.

Attack success definition. An attack on one question succeeds if the
optimiser found a feasible paraphrase (bidirectionally NLI-equivalent to
the original) that moved entropy in the intended direction by at least
`min_delta_nats`. Direction:
  Hide        entropy must DROP (model stays wrong, looks confident)
  False-alarm entropy must RISE (model stays right, looks uncertain)
The paper-level metric is AUROC degradation; per-question success is the
prototype gate the plan uses in Weeks 6 and 7 (">50% of 10 examples").
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable

from .. import model as M
from ..config import GenConfig, ModelConfig
from ..data import TriviaQAExample
from ..nli import NLI
from ..scoring import is_acceptable
from ..se_pipeline import semantic_entropy
from . import objectives, optimizer, proposer


def _stable_seed(s: str) -> int:
    """Deterministic 32-bit seed from a string (stable across runs, unlike hash())."""
    return int.from_bytes(hashlib.sha1(s.encode("utf-8")).digest()[:4], "big")


@dataclass
class LoadedPair:
    lm: M.LoadedModel
    nli: NLI


def load_pair(model_cfg: ModelConfig | None = None) -> LoadedPair:
    """Load Llama 4-bit and DeBERTa NLI together (~7 GB VRAM total).

    The attack inner loop scores every candidate paraphrase through the SE
    pipeline, which needs both models resident at once, so unlike the Week 4
    replication this phase cannot split the models across processes.
    """
    lm = M.load_llama(model_cfg or ModelConfig())
    nli = NLI()
    return LoadedPair(lm, nli)


@dataclass
class AttackOutcome:
    question_id: str
    question: str
    attack: str                 # "hide" | "false_alarm"
    detector: str               # "se" | "sre"
    entropy_before: float
    entropy_after: float
    delta: float                # after - before
    best_query: str
    feasible: bool
    improved: bool
    success: bool
    n_objective_calls: int
    n_iterations_run: int
    # B2 (external review §3): hold hallucination status fixed under Q'.
    entropy_and_feasible: bool = False   # the OLD criterion (entropy moved + feasible)
    answer_under_q_prime: str = ""        # greedy answer under Q' (audit; re-oracle later)
    correct_under_q_prime: bool = False   # model GREEDY correct under Q' (same rule as label)
    status_held: bool = True              # hallucination status unchanged under Q' (greedy)
    # B7 finding 16: greedy status can disagree with the T=1.0 sampled set the detector
    # actually clusters. Fraction of the N detector samples correct under Q' (-1 = not
    # computed, i.e. the re-check did not run). Reported alongside the greedy status.
    frac_correct_under_q_prime: float = -1.0
    # B2 budget-matching (critique_log 21): the optimiser's running-best FEASIBLE objective
    # after each iteration. trajectory_best_obj[t] is the best the attack had achieved using
    # only its first 1 + t*top_N*candidate_size_M candidates, so the attack's move at ANY
    # smaller budget is recoverable post-hoc (attack_move_at_budget) and can be compared
    # against a benign floor drawn at that same budget — without re-running the attack.
    # Defaulted so records written before this field remain readable.
    trajectory_best_obj: list[float] = field(default_factory=list)
    # Real equivalence-gate statistics (critique_log 22). `feasible` above is True BY
    # CONSTRUCTION and is NOT a gate measurement; these count the candidates actually
    # submitted to the gate and how many it admitted. 0/0 on records written earlier.
    n_feasibility_checks: int = 0
    n_feasibility_passed: int = 0
    # Tie multiplicity at the attack's maximum (critique_log 26) — the quantity that
    # carries the signal once the log(N) ceiling pins the max VALUE. 0 on older records.
    n_feasible_at_best: int = 0
    feasible_objs: list[float] = field(default_factory=list)


def _entropy_moved(attack: str, entropy_before: float, entropy_after: float,
                   min_delta_nats: float) -> bool:
    if attack == "hide":
        return (entropy_before - entropy_after) >= min_delta_nats
    return (entropy_after - entropy_before) >= min_delta_nats


def _status_held(attack: str, correct_under_q_prime: bool) -> bool:
    """B2: does the hallucination status survive the paraphrase?

    A hide attack is only meaningful if the model is STILL wrong under Q' (else
    entropy fell because the model got it right — nothing to hide). A false-alarm
    is only meaningful if the model is STILL right under Q' (else the "alarm" is
    a true positive). Same span oracle as the label the pool was built on."""
    if attack == "hide":
        return not correct_under_q_prime
    return bool(correct_under_q_prime)


def run_attack_on_example(
    ex: TriviaQAExample,
    attack: str,
    pair: LoadedPair,
    *,
    detector: str = "se",
    gen_cfg: GenConfig | None = None,
    sre_kwargs: dict | None = None,
    max_iteration: int = 20,
    candidate_size_M: int = 3,
    top_N: int = 3,
    min_delta_nats: float = 0.25,
    verbose: bool = False,
) -> AttackOutcome:
    # Reproducible candidate search: seed the proposer's instruction RNG per
    # question (stable across runs and resumes) — external review B7 (finding 6).
    proposer.seed_proposer(_stable_seed(ex.question_id))
    bundle = objectives.make_objective(
        attack, pair.lm, pair.nli,
        detector=detector, gen_cfg=gen_cfg, sre_kwargs=sre_kwargs,
    )
    result = optimizer.optimize(
        ex.question, bundle.fn, pair.lm, pair.nli,
        max_iteration=max_iteration, candidate_size_M=candidate_size_M,
        top_N=top_N, verbose=verbose,
    )
    entropy_before = bundle.entropy(ex.question)
    entropy_after = bundle.entropy(result.best_query)
    feasible = result.best_is_feasible
    moved = _entropy_moved(attack, entropy_before, entropy_after, min_delta_nats)
    entropy_and_feasible = bool(moved and feasible)

    # B2 (external review §3): a hide "success" requires the model to STILL answer
    # incorrectly under Q' (else the entropy dropped because the model got it right
    # -> no hallucination to hide); false-alarm requires it to STILL answer right.
    # We only pay for the re-check when it could change a success, i.e. when the
    # entropy moved AND the paraphrase is feasible. The re-check uses the SAME rule
    # as the original greedy label (greedy generate_one) at the pinned generation
    # length, so it is on the same footing as the label the pool was stratified on.
    answer_qp, correct_qp, status_held, frac_correct_qp = "", False, True, -1.0
    if entropy_and_feasible:
        # One seeded SE evaluation under Q' yields BOTH the greedy status (same rule
        # and pinned decode as the pool label) AND the fraction of the N detector
        # samples that are correct (finding 16: the greedy status can disagree with
        # the T=1.0 sampled set the detector actually clusters).
        base = gen_cfg or GenConfig()
        probe = GenConfig(max_new_tokens=base.max_new_tokens, temperature=base.temperature,
                          top_p=base.top_p, n_samples=base.n_samples, seed=base.seed)
        res = semantic_entropy(result.best_query, pair.lm, pair.nli, probe,
                               example=ex, compute_greedy=True)
        answer_qp = res.greedy or ""
        correct_qp = bool(res.greedy_correct)
        status_held = _status_held(attack, correct_qp)
        if res.samples_correct:
            frac_correct_qp = sum(res.samples_correct) / len(res.samples_correct)

    success = bool(entropy_and_feasible and status_held)
    return AttackOutcome(
        question_id=ex.question_id,
        question=ex.question,
        attack=attack,
        detector=detector,
        entropy_before=entropy_before,
        entropy_after=entropy_after,
        delta=entropy_after - entropy_before,
        best_query=result.best_query,
        feasible=feasible,
        improved=result.improved,
        success=success,
        n_objective_calls=result.n_objective_calls,
        n_iterations_run=result.n_iterations_run,
        entropy_and_feasible=entropy_and_feasible,
        answer_under_q_prime=answer_qp,
        correct_under_q_prime=correct_qp,
        status_held=status_held,
        frac_correct_under_q_prime=frac_correct_qp,
        trajectory_best_obj=list(result.trajectory_best_obj),
        n_feasibility_checks=result.n_feasibility_checks,
        n_feasibility_passed=result.n_feasibility_passed,
        n_feasible_at_best=result.n_feasible_at_best,
        feasible_objs=list(result.feasible_objs),
    )


def run_attack_batch(
    examples: list[TriviaQAExample],
    attack: str,
    pair: LoadedPair,
    out_jsonl: Path,
    *,
    detector: str = "se",
    progress_every: int = 5,
    **attack_kwargs,
) -> list[AttackOutcome]:
    """Resumable batch. Skips question_ids already present in out_jsonl."""
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    done: set[str] = set()
    if out_jsonl.exists():
        for line in out_jsonl.read_text().splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["question_id"])
                except Exception:
                    pass
    todo = [ex for ex in examples if ex.question_id not in done]
    print(f"attack={attack} detector={detector}: {len(done)} done, {len(todo)} to do",
          flush=True)

    outcomes: list[AttackOutcome] = []
    t0 = time.perf_counter()
    with out_jsonl.open("a", encoding="utf-8") as f:
        for i, ex in enumerate(todo):
            outcome = run_attack_on_example(ex, attack, pair, detector=detector, **attack_kwargs)
            f.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")
            f.flush()
            outcomes.append(outcome)
            if (i + 1) % progress_every == 0:
                el = time.perf_counter() - t0
                sr = sum(o.success for o in outcomes) / len(outcomes)
                print(f"  {i+1}/{len(todo)} in {el:.0f}s, running success rate {sr:.0%}",
                      flush=True)
    return outcomes


def read_outcomes(out_jsonl: Path) -> list[AttackOutcome]:
    out: list[AttackOutcome] = []
    for line in out_jsonl.read_text().splitlines():
        if line.strip():
            out.append(AttackOutcome(**json.loads(line)))
    return out
