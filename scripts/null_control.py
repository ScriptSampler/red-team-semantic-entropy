"""Null / noise-floor control for the attack (external review B7, finding 13).

The confirmatory SE headline is BLOCKED until attack success is reported NET OF a
noise floor. Seeded SE is reproducible but each candidate's entropy is a finite
N=10 Monte-Carlo estimate, so the beam search's max over ~180 candidates is
upward-biased even without adversarial signal. This script quantifies that floor:

For each attacked target it draws K RANDOM NLI-passing paraphrases (the proposer +
feasibility gate, but NO optimization), scores each under the same seeded detector,
and takes the best intended-direction move over those K as the "null best" — the
move a non-adversarial search of the same size would achieve by chance. It then
compares the ATTACK's move to that floor and reports:

  attack_move        intended-direction entropy move of the optimized best_query
  null_best_move     max intended move over K benign feasible paraphrases
  net = attack - null_best         (>0 => the attack beats chance/benign variation)
  net_success_rate   fraction of targets with net > 0, with a bootstrap CI
  orig_seed_std      std of the original's entropy over k>=3 seeds (the N=10 floor)

If the attack effect survives net of the floor, the headline stands; if it collapses
into the floor, that is the finding. GPU; ~K detector evals/target (<< the ~180 the
attack uses), so far cheaper than the attack itself.

    # in Ubuntu-24.04:  export HF_HOME=/home/abhi/.cache/huggingface
    ./.venv-wsl/bin/python scripts/null_control.py --tag _fair --K 8 --n_seeds 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import load_pair, read_outcomes, _stable_seed
from se.attacks import proposer, feasibility
from se.se_pipeline import semantic_entropy
from se.stats import rate_ci, bootstrap_ci

CELLS = [("false_alarm", "se"), ("hide", "se")]


def _move(attack: str, before: float, after: float) -> float:
    return (before - after) if attack == "hide" else (after - before)


def _benign_moves(question: str, before: float, attack: str, pair, gen,
                  K: int, seed: int) -> list[float]:
    """Intended-direction moves for K benign (unoptimized) feasible paraphrases."""
    proposer.seed_proposer(seed)
    moves: list[float] = []
    tries = 0
    while len(moves) < K and tries < K * 5:
        tries += 1
        cand = proposer.propose(question, pair.lm)
        if not feasibility.check(cand, question, pair.nli).feasible:
            continue
        ent = semantic_entropy(cand, pair.lm, pair.nli, gen).entropy_nats
        moves.append(_move(attack, before, ent))
    return moves


def _orig_seed_std(question: str, pair, base_gen, n_seeds: int) -> float:
    """Std of the ORIGINAL question's SE entropy across n_seeds seeds — the raw
    N=10 estimator noise, independent of any paraphrase."""
    vals = []
    for s in range(n_seeds):
        g = GenConfig(max_new_tokens=base_gen.max_new_tokens,
                      temperature=base_gen.temperature, top_p=base_gen.top_p,
                      n_samples=base_gen.n_samples, seed=s)
        vals.append(semantic_entropy(question, pair.lm, pair.nli, g).entropy_nats)
    return float(np.std(vals)) if len(vals) > 1 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_fair")
    ap.add_argument("--K", type=int, default=8, help="benign paraphrases per target")
    ap.add_argument("--n_seeds", type=int, default=3, help="seeds for the original noise band")
    ap.add_argument("--max_targets", type=int, default=0, help="0 = all completed targets")
    args = ap.parse_args()

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    pair = load_pair()
    print(f"[load] pair ready; dir={campaign_dir}", flush=True)

    L: list[str] = ["# Null / noise-floor control (attack move vs benign floor)", ""]
    L.append(f"K={args.K} benign feasible paraphrases per target; original noise band "
             f"over {args.n_seeds} seeds. Success net of floor = attack move exceeds the "
             f"best benign move. All on the fair pool ({campaign_dir.name}).")
    L.append("")

    for attack, detector in CELLS:
        f = campaign_dir / f"triviaqa_{detector}_{attack}.jsonl"
        if not f.exists():
            L.append(f"## {detector}_{attack}: no outcomes yet"); L.append(""); continue
        outcomes = read_outcomes(f)
        if args.max_targets:
            outcomes = outcomes[: args.max_targets]

        atk_moves, null_moves, nets, seed_stds = [], [], [], []
        for o in outcomes:
            bm = _benign_moves(o.question, o.entropy_before, o.attack, pair, gen,
                               args.K, seed=_stable_seed("null:" + o.question_id))
            null_best = max(bm) if bm else 0.0
            atk = _move(o.attack, o.entropy_before, o.entropy_after)
            atk_moves.append(atk); null_moves.append(null_best)
            nets.append(atk - null_best)
            seed_stds.append(_orig_seed_std(o.question, pair, gen, args.n_seeds))
            print(f"  {o.question_id}: attack {atk:+.3f} vs null_best {null_best:+.3f} "
                  f"-> net {atk-null_best:+.3f}", flush=True)

        net_success = [n > 0 for n in nets]
        L.append(f"## {detector.upper()} / {attack}  (n={len(outcomes)})")
        L.append("")
        L.append(f"- mean attack move:      {np.mean(atk_moves):+.3f} nats")
        L.append(f"- mean null-best move:   {np.mean(null_moves):+.3f} nats  "
                 f"(benign paraphrase floor)")
        nci = bootstrap_ci(nets, np.mean)
        L.append(f"- mean net (attack-floor): {nci.point:+.3f} [{nci.lo:+.3f}, {nci.hi:+.3f}] nats")
        sci = rate_ci(net_success)
        L.append(f"- success NET of floor:  {sci.point:.0%} [{sci.lo:.0%}, {sci.hi:.0%}] "
                 f"(attack beats the best of {args.K} benign paraphrases)")
        L.append(f"- original entropy noise (std over {args.n_seeds} seeds): "
                 f"mean {np.nanmean(seed_stds):.3f} nats")
        L.append("")
        L.append("Interpretation: if 'success NET of floor' and the net-move CI stay well "
                 "above 0, the attack is real signal, not selection-on-noise. If they "
                 "collapse toward 0, the apparent effect is largely the N=10 floor.")
        L.append("")

    out = RESULTS_DIR / "null_control_report.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
