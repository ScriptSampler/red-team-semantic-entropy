"""Regenerate an attack summary from a cached campaign JSONL. No models, no GPU.

Useful when a run was resumed (so the inline report saw only the new questions)
or when you just want a fresh summary from the full cache.

    python scripts/report_attack.py <campaign.jsonl> <attack> [out.md]
    # attack in {hide, false_alarm}
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.harness import read_outcomes


def summarize(jsonl: Path, attack: str) -> str:
    outcomes = read_outcomes(jsonl)
    lines: list[str] = []
    direction = "drop" if attack == "hide" else "rise"
    lines.append(f"# Attack summary: {attack} ({jsonl.name})")
    lines.append("")
    n = len(outcomes)
    n_succ = sum(o.success for o in outcomes)
    n_feas = sum(o.feasible for o in outcomes)
    moves = [(o.entropy_before - o.entropy_after) if attack == "hide"
             else (o.entropy_after - o.entropy_before) for o in outcomes if o.feasible]
    lines.append(f"questions: {n}")
    lines.append(f"success (feasible + entropy {direction} >= 0.25 nats): {n_succ}/{n}")
    lines.append(f"feasible paraphrase found: {n_feas}/{n}")
    if moves:
        lines.append(f"mean entropy {direction} among feasible: {statistics.mean(moves):.3f} nats")
        lines.append(f"max entropy {direction} among feasible: {max(moves):.3f} nats")
    lines.append("")
    lines.append("| qid | SE before | SE after | delta | feasible | success |")
    lines.append("| --- | --------- | -------- | ----- | -------- | ------- |")
    for o in outcomes:
        lines.append(f"| {o.question_id} | {o.entropy_before:.3f} | {o.entropy_after:.3f} | "
                     f"{o.delta:+.3f} | {'yes' if o.feasible else 'no'} | "
                     f"{'yes' if o.success else 'no'} |")
    lines.append("")
    rate = n_succ / n if n else 0.0
    lines.append(f"## Verdict: {'PASS' if rate > 0.5 else 'BELOW TARGET'} "
                 f"({n_succ}/{n} = {rate*100:.0f}%)")
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__); return 2
    jsonl = Path(sys.argv[1])
    attack = sys.argv[2]
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    text = summarize(jsonl, attack)
    if out:
        out.write_text(text)
        print(f"wrote {out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
