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

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .. import model as M
from ..config import GenConfig, ModelConfig
from ..data import TriviaQAExample
from ..nli import NLI
from . import objectives, optimizer


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


def _success(attack: str, entropy_before: float, entropy_after: float,
             feasible: bool, min_delta_nats: float) -> bool:
    if not feasible:
        return False
    if attack == "hide":
        return (entropy_before - entropy_after) >= min_delta_nats
    return (entropy_after - entropy_before) >= min_delta_nats


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
    success = _success(attack, entropy_before, entropy_after,
                       result.best_is_feasible, min_delta_nats)
    return AttackOutcome(
        question_id=ex.question_id,
        question=ex.question,
        attack=attack,
        detector=detector,
        entropy_before=entropy_before,
        entropy_after=entropy_after,
        delta=entropy_after - entropy_before,
        best_query=result.best_query,
        feasible=result.best_is_feasible,
        improved=result.improved,
        success=success,
        n_objective_calls=result.n_objective_calls,
        n_iterations_run=result.n_iterations_run,
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
