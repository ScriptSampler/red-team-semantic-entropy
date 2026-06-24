"""Week 7: False-alarm attack on 10 questions the model answers correctly.

Mirror of Week 6 with the objective sign flipped: find a paraphrase Q' of a
right-answered question Q such that SE(Q') is MAXIMISED while NLI confirms
Q == Q'. The detector then flags a correct answer as a hallucination.
Success target is >50% of the 10.

Targets are the lowest-entropy right cases (most headroom to raise).

Run after Week 4 completes and the GPU is free:
    python scripts/wk7_false_alarm.py
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


N = int(os.environ.get("ATTACK_N", "10"))
MAX_ITER = int(os.environ.get("ATTACK_MAX_ITER", "20"))
M = int(os.environ.get("ATTACK_M", "3"))
TOP_N = int(os.environ.get("ATTACK_TOPN", "3"))
OUT = DEFAULT_SAMPLES_DIR / "attacks" / "wk7_false_alarm.jsonl"


def main() -> int:
    examples = select_examples("right", N)
    print(f"selected {len(examples)} right-answered questions", flush=True)

    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    outcomes = run_attack_batch(
        examples, "false_alarm", pair, OUT,
        detector="se", gen_cfg=gen,
        max_iteration=MAX_ITER, candidate_size_M=M, top_N=TOP_N, min_delta_nats=0.25,
    )

    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Week 7: False-alarm attack vs vanilla SE on TriviaQA (10 right questions)")
    log("")
    n_succ = sum(o.success for o in outcomes)
    n_feas = sum(o.feasible for o in outcomes)
    rises = [o.entropy_after - o.entropy_before for o in outcomes if o.feasible]
    log(f"success (feasible + entropy rise >= 0.25 nats): {n_succ}/{len(outcomes)}")
    log(f"feasible paraphrase found:                      {n_feas}/{len(outcomes)}")
    if rises:
        log(f"mean entropy rise among feasible:               {statistics.mean(rises):.3f} nats")
    log("")
    log("| qid | SE before | SE after | delta | feasible | success |")
    log("| --- | --------- | -------- | ----- | -------- | ------- |")
    for o in outcomes:
        log(f"| {o.question_id} | {o.entropy_before:.3f} | {o.entropy_after:.3f} | "
            f"{o.delta:+.3f} | {'yes' if o.feasible else 'no'} | {'yes' if o.success else 'no'} |")
    log("")
    verdict = "PASS" if n_succ > len(outcomes) / 2 else "BELOW TARGET"
    log(f"## Verdict: {verdict} ({n_succ}/{len(outcomes)} > 50%?)")

    (RESULTS_DIR / "wk7_false_alarm.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'wk7_false_alarm.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
