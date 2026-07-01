"""Week 11: qualitative failure-mode analysis + Phase 2 close-out.

Reads the Week 9 campaign outcomes and surfaces patterns the paper's
analysis section needs: which questions are attackable, what the
successful adversarial paraphrases look like versus the failures, and
whether SE or SRE is the softer target.

For each campaign file present, it prints the 10 biggest attack successes
(largest entropy move in the intended direction) and 10 clear failures,
with the original and adversarial phrasing side by side, plus aggregate
patterns (entropy-move distribution, objective-call cost, success by
detector).

Run after the Week 9 campaigns exist:
    python scripts/wk11_analysis.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import read_outcomes, AttackOutcome


CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"


def _move(o: AttackOutcome) -> float:
    """Entropy move in the intended direction (positive = attack worked)."""
    return (o.entropy_before - o.entropy_after) if o.attack == "hide" \
        else (o.entropy_after - o.entropy_before)


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Week 11: qualitative failure-mode analysis")
    log("")

    files = sorted(CAMPAIGN_DIR.glob("*.jsonl")) if CAMPAIGN_DIR.exists() else []
    if not files:
        log("No Week 9 campaign files found. Run scripts/wk9_scaleup.py first.")
        (RESULTS_DIR / "wk11_analysis.md").write_text("\n".join(report) + "\n")
        return 0

    for fpath in files:
        outcomes = read_outcomes(fpath)
        if not outcomes:
            continue
        name = fpath.stem
        moves = [_move(o) for o in outcomes]
        feas = [o for o in outcomes if o.feasible]
        log(f"## Campaign {name}")
        log(f"questions: {len(outcomes)}, feasible paraphrase found: {len(feas)}, "
            f"successes: {sum(o.success for o in outcomes)}")
        log(f"entropy move (intended direction): mean {statistics.mean(moves):+.3f}, "
            f"median {statistics.median(moves):+.3f}, max {max(moves):+.3f}")
        log(f"objective calls per question: mean {statistics.mean([o.n_objective_calls for o in outcomes]):.0f}")
        log("")

        # Top/bottom lists only make sense when they cannot overlap; with a small
        # campaign (n < 20) ranked[:10] and ranked[-10:] would share rows and
        # mislead. Suppress the lists below that size and cap k = n // 2.
        successes = [o for o in outcomes if o.success]
        failures = [o for o in outcomes if not o.success]
        if len(outcomes) < 20:
            log(f"(campaign has {len(outcomes)} questions; per-example strongest/"
                f"weakest lists suppressed below n=20 to avoid overlap. "
                f"{len(successes)} successes, {len(failures)} non-successes.)")
            log("")
        else:
            k = min(10, len(outcomes) // 2)
            top = sorted(successes, key=_move, reverse=True)[:k]
            bot = sorted(failures, key=_move)[:k]
            log(f"### {len(top)} strongest successes")
            for o in top:
                log(f"- {o.question_id} move {_move(o):+.3f} (SE {o.entropy_before:.2f} -> {o.entropy_after:.2f})")
                log(f"    orig: {o.question}")
                log(f"    adv:  {o.best_query}")
            log("")
            log(f"### {len(bot)} clearest failures (non-successes only)")
            for o in bot:
                log(f"- {o.question_id} move {_move(o):+.3f} feasible={o.feasible}")
                log(f"    orig: {o.question}")
                if o.best_query != o.question:
                    log(f"    adv:  {o.best_query}")
            log("")

    log("## Patterns to write into methodology.md")
    log("- Which question types yield the largest entropy moves?")
    log("- Do successful paraphrases share structural traits (length, hedging,")
    log("  added qualifiers, reordering)?")
    log("- Is SRE harder to move than SE (compare mean moves across detectors)?")
    log("- Failure cluster: questions where no feasible paraphrase changed entropy.")

    (RESULTS_DIR / "wk11_analysis.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'wk11_analysis.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
