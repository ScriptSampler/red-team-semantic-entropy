"""Week 6: Hide attack on 10 questions the model answers incorrectly.

Goal: find a paraphrase Q' of a wrong-answered question Q such that SE(Q')
is minimised while NLI confirms Q == Q'. Success target is >50% of the 10.

Targets are drawn from the Week 4 entropy.jsonl, preferring the
highest-entropy wrong cases (most headroom to hide).

Run after Week 4 completes and the GPU is free:
    python scripts/wk6_hide_attack.py
"""
from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import load_pair, run_attack_batch
from se.attacks.select import select_examples


# Overridable from the overnight driver; defaults match the plan's prototype.
N = int(os.environ.get("ATTACK_N", "10"))
MAX_ITER = int(os.environ.get("ATTACK_MAX_ITER", "20"))
M = int(os.environ.get("ATTACK_M", "3"))
TOP_N = int(os.environ.get("ATTACK_TOPN", "3"))
OUT = DEFAULT_SAMPLES_DIR / "attacks" / "wk6_hide.jsonl"


def main() -> int:
    examples = select_examples("wrong", N)
    print(f"selected {len(examples)} wrong-answered questions", flush=True)

    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    outcomes = run_attack_batch(
        examples, "hide", pair, OUT,
        detector="se", gen_cfg=gen,
        max_iteration=MAX_ITER, candidate_size_M=M, top_N=TOP_N, min_delta_nats=0.25,
    )

    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Week 6: Hide attack vs vanilla SE on TriviaQA (10 wrong questions)")
    log("")
    n_succ = sum(o.success for o in outcomes)
    n_feas = sum(o.feasible for o in outcomes)
    drops = [o.entropy_before - o.entropy_after for o in outcomes if o.feasible]
    log(f"success (feasible + entropy drop >= 0.25 nats): {n_succ}/{len(outcomes)}")
    log(f"feasible paraphrase found:                      {n_feas}/{len(outcomes)}")
    if drops:
        log(f"mean entropy drop among feasible:               {statistics.mean(drops):.3f} nats")
    log("")
    log("| qid | SE before | SE after | delta | feasible | success |")
    log("| --- | --------- | -------- | ----- | -------- | ------- |")
    for o in outcomes:
        log(f"| {o.question_id} | {o.entropy_before:.3f} | {o.entropy_after:.3f} | "
            f"{o.delta:+.3f} | {'yes' if o.feasible else 'no'} | {'yes' if o.success else 'no'} |")
    log("")
    log("## Two example attacks")
    for o in outcomes[:2]:
        log(f"### {o.question_id}")
        log(f"original:  {o.question}")
        log(f"best Q':   {o.best_query}")
        log(f"SE {o.entropy_before:.3f} -> {o.entropy_after:.3f}, feasible={o.feasible}")
        log("")

    verdict = "PASS" if n_succ > len(outcomes) / 2 else "BELOW TARGET"
    log(f"## Verdict: {verdict} ({n_succ}/{len(outcomes)} > 50%? {n_succ > len(outcomes)/2})")

    (RESULTS_DIR / "wk6_hide_attack.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'wk6_hide_attack.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
