"""Regenerate an attack summary from a cached campaign JSONL. No models, no GPU.

Useful when a run was resumed (so the inline report saw only the new questions)
or when you just want a fresh summary from the full cache.

    python scripts/report_attack.py <campaign.jsonl> <attack> [out.md]
    # attack in {hide, false_alarm}
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.harness import read_outcomes
from se.attacks.report import summarize_cell, render_cell_md


def summarize(jsonl: Path, attack: str) -> str:
    outcomes = read_outcomes(jsonl)
    s = summarize_cell(outcomes)
    lines: list[str] = [f"# Attack summary: {attack} ({jsonl.name})", ""]
    lines += render_cell_md(s)
    lines += [
        "",
        "Success is the B2 invariance-gated criterion (entropy moved AND feasible "
        "AND the model's hallucination status held under Q'); the entropy-only line "
        "is the pre-B2 number, and their gap is the attrition. All rates carry "
        "bootstrap 95% CIs.",
        "",
        "| qid | SE before | SE after | delta | feasible | ent+feas | correct@Q' | held | success |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for o in outcomes:
        lines.append(
            f"| {o.question_id} | {o.entropy_before:.3f} | {o.entropy_after:.3f} | "
            f"{o.delta:+.3f} | {'yes' if o.feasible else 'no'} | "
            f"{'yes' if o.entropy_and_feasible else 'no'} | "
            f"{'yes' if o.correct_under_q_prime else 'no'} | "
            f"{'yes' if o.status_held else 'no'} | "
            f"{'yes' if o.success else 'no'} |"
        )
    lines += ["", f"## Verdict (B2-gated): "
              f"{'PASS' if s['success_gated'].point > 0.5 else 'BELOW TARGET'} "
              f"({int(round(s['success_gated'].point * s['n']))}/{s['n']} = "
              f"{s['success_gated'].point*100:.0f}%)"]
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
