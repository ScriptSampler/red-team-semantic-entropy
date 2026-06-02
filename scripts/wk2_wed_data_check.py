"""Week 2 Wednesday session.

Download TriviaQA rc.nocontext, load the validation split, print 20
example records, and produce a short stats summary. Writes
results/triviaqa_inspect.md.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk2_wed_data_check.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.data import load_triviaqa


SPLIT = "validation"
N_INSPECT = 20


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log(f"# Week 2 Wed: TriviaQA rc.nocontext inspection")
    log(f"split: {SPLIT}")
    log("")

    log("## Load")
    examples = load_triviaqa(split=SPLIT)
    log(f"total examples: {len(examples)}")
    log("")

    log("## Field shape (first record)")
    first = examples[0]
    log(f"question_id: {first.question_id}")
    log(f"question:    {first.question!r}")
    log(f"answer:      {first.answer!r}")
    log(f"aliases ({len(first.aliases)}): {first.aliases[:5]}{'...' if len(first.aliases) > 5 else ''}")
    log("")

    log(f"## First {N_INSPECT} examples")
    for i, ex in enumerate(examples[:N_INSPECT]):
        accepted = ex.all_acceptable()
        log(f"### [{i}] {ex.question_id}")
        log(f"Q: {ex.question}")
        log(f"A: {ex.answer}")
        if len(accepted) > 1:
            log(f"accepted ({len(accepted)}): {accepted[:6]}{'...' if len(accepted) > 6 else ''}")
        log("")

    log("## Stats over the full split")
    q_lens = [len(ex.question) for ex in examples]
    a_lens = [len(ex.answer) for ex in examples]
    alias_counts = [len(ex.all_acceptable()) for ex in examples]
    empty_answers = sum(1 for ex in examples if not ex.answer)

    log(f"question length chars: mean={statistics.mean(q_lens):.1f}, median={statistics.median(q_lens):.0f}, min={min(q_lens)}, max={max(q_lens)}")
    log(f"answer length chars:   mean={statistics.mean(a_lens):.1f}, median={statistics.median(a_lens):.0f}, min={min(a_lens)}, max={max(a_lens)}")
    log(f"accepted forms per Q:  mean={statistics.mean(alias_counts):.1f}, median={statistics.median(alias_counts):.0f}, max={max(alias_counts)}")
    log(f"empty canonical answers: {empty_answers}")
    log("")

    log("## Notes for SE scoring")
    log(
        "Use TriviaQAExample.all_acceptable() to match a model output against "
        "any accepted form of the answer. Farquhar et al. consider a generation "
        "correct if it contains any of these forms after light normalisation "
        "(lowercase, strip punctuation). We will replicate that in Week 3 when "
        "we build the SE correctness check."
    )

    out_path = RESULTS_DIR / "triviaqa_inspect.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
