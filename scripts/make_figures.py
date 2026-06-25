"""Generate the headline figure from the wk9 attack campaigns.

Reads the per-question campaign JSONLs (the source of truth, same as
wk10_matrix.py) and renders a grouped bar chart of clean vs attacked AUROC for
each (dataset, detector), with the two attack directions shown separately and
False-alarm placed first per the paper's framing.

GPU-free (sklearn + matplotlib). Run after the wk9 campaigns exist:
    python scripts/make_figures.py
Writes results/figures/headline_auroc.png and a machine-readable
results/figures/headline_auroc.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from se.config import RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import read_outcomes

CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"
DATASETS = ["triviaqa", "squad"]
DETECTORS = ["se", "sre"]
FIG_DIR = RESULTS_DIR / "figures"


def _auc(labels, scores):
    if 0 < sum(labels) < len(labels):
        return float(roc_auc_score(labels, scores))
    return None


def cell_numbers(dataset: str, detector: str) -> dict | None:
    hide_f = CAMPAIGN_DIR / f"{dataset}_{detector}_hide.jsonl"
    fa_f = CAMPAIGN_DIR / f"{dataset}_{detector}_false_alarm.jsonl"
    if not hide_f.exists() and not fa_f.exists():
        return None
    hide = read_outcomes(hide_f) if hide_f.exists() else []
    fa = read_outcomes(fa_f) if fa_f.exists() else []
    labels = [1] * len(hide) + [0] * len(fa)
    before = [o.entropy_before for o in hide] + [o.entropy_before for o in fa]
    # Attacked-by-direction: hide questions use their attacked score, FA likewise.
    after_hide = [o.entropy_after for o in hide] + [o.entropy_before for o in fa]
    after_fa = [o.entropy_before for o in hide] + [o.entropy_after for o in fa]
    after_both = [o.entropy_after for o in hide] + [o.entropy_after for o in fa]
    return {
        "clean": _auc(labels, before),
        "hide_only": _auc(labels, after_hide),
        "false_alarm_only": _auc(labels, after_fa),
        "both": _auc(labels, after_both),
        "n": len(labels),
    }


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    for ds in DATASETS:
        for det in DETECTORS:
            nums = cell_numbers(ds, det)
            if nums:
                data[f"{ds}/{det}"] = nums
    if not data:
        print("No campaign files yet; nothing to plot.", file=sys.stderr)
        return 1

    (FIG_DIR / "headline_auroc.json").write_text(json.dumps(data, indent=2))

    cells = list(data.keys())
    series = [("clean", "clean"), ("false_alarm_only", "False-alarm"),
              ("hide_only", "Hide"), ("both", "both")]
    x = range(len(cells))
    w = 0.2
    fig, ax = plt.subplots(figsize=(max(6, 1.6 * len(cells)), 4.5))
    for i, (key, label) in enumerate(series):
        vals = [data[c].get(key) or 0.0 for c in cells]
        ax.bar([xi + (i - 1.5) * w for xi in x], vals, width=w, label=label)
    ax.axhline(0.5, color="gray", ls="--", lw=0.8, label="chance")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cells, rotation=0)
    ax.set_ylabel("AUROC")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Detector AUROC: clean vs adversarial paraphrase (False-alarm leads)")
    ax.legend(ncol=5, fontsize=8, loc="lower center")
    fig.tight_layout()
    out = FIG_DIR / "headline_auroc.png"
    fig.savefig(out, dpi=150)
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
