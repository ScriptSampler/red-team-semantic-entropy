"""Week 10: assemble the full result matrix from Week 9 campaign files.

For each (dataset, detector) we combine the Hide campaign (all questions
the model answers WRONG, label 1) and the False-alarm campaign (all RIGHT,
label 0) into one pool, then compute:

  clean AUROC      labels vs entropy_before  (detector before any attack)
  attacked AUROC   labels vs entropy_after   (each question's adversarial paraphrase)
  degradation      clean - attacked          (higher = attack more effective)

plus per-attack success rates. A detector that the attack defeats has its
AUROC collapse toward 0.5. This produces the 12+ AUROC numbers the plan
calls for. Reads only cached JSONL, loads no models.

Run after the Week 9 campaigns you care about have produced files in
~/.cache/se-research/samples/attacks/wk9/.
"""
from __future__ import annotations

import sys
from pathlib import Path

from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import read_outcomes


CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"
DATASETS = ["triviaqa", "squad"]
DETECTORS = ["se", "sre"]


def _auc(labels, scores):
    if 0 < sum(labels) < len(labels):
        return roc_auc_score(labels, scores)
    return None


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Week 10: full attack result matrix")
    log("")
    log("Label convention: positive class is the hallucination case.")
    log("Hide campaign questions are model-wrong (label 1); False-alarm are")
    log("model-right (label 0). Clean AUROC uses pre-attack entropy, attacked")
    log("AUROC uses the adversarial paraphrase's entropy.")
    log("")

    numbers = 0
    summary_rows: list[str] = []

    for dataset in DATASETS:
        for detector in DETECTORS:
            hide_f = CAMPAIGN_DIR / f"{dataset}_{detector}_hide.jsonl"
            fa_f = CAMPAIGN_DIR / f"{dataset}_{detector}_false_alarm.jsonl"
            if not hide_f.exists() and not fa_f.exists():
                log(f"## {dataset} x {detector}: no campaign files yet, skipped")
                log("")
                continue

            hide = read_outcomes(hide_f) if hide_f.exists() else []
            fa = read_outcomes(fa_f) if fa_f.exists() else []

            labels = [1] * len(hide) + [0] * len(fa)
            before = [o.entropy_before for o in hide] + [o.entropy_before for o in fa]
            after = [o.entropy_after for o in hide] + [o.entropy_after for o in fa]

            clean = _auc(labels, before)
            attacked = _auc(labels, after)

            log(f"## {dataset} x {detector}")
            log(f"pool: {len(hide)} hide (wrong) + {len(fa)} false-alarm (right) = {len(labels)}")
            if clean is not None:
                log(f"clean AUROC:    {clean:.3f}")
                numbers += 1
            if attacked is not None:
                log(f"attacked AUROC: {attacked:.3f}")
                numbers += 1
            if clean is not None and attacked is not None:
                log(f"degradation:    {clean - attacked:+.3f}")
                summary_rows.append(f"| {dataset} | {detector} | {clean:.3f} | "
                                    f"{attacked:.3f} | {clean - attacked:+.3f} |")
            if hide:
                sr = sum(o.success for o in hide) / len(hide)
                log(f"Hide success rate:        {sr:.0%}")
            if fa:
                sr = sum(o.success for o in fa) / len(fa)
                log(f"False-alarm success rate: {sr:.0%}")
            log("")

    log("## Summary table")
    log("| dataset | detector | clean AUROC | attacked AUROC | degradation |")
    log("| ------- | -------- | ----------- | -------------- | ----------- |")
    for r in summary_rows:
        log(r)
    log("")
    log(f"AUROC numbers reported: {numbers} (target 12+)")
    log("")
    log("If SRE degrades less than SE under the same attacks, that is the")
    log("'SRE is more robust' story. If both collapse, that is the headline")
    log("vulnerability result. Either is a publishable finding.")

    (RESULTS_DIR / "attack_matrix.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'attack_matrix.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
