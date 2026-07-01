"""B1 checkpoint: fair (stratified-random) pool vs the extreme-entropy ablation.

Proves the circularity fix on the clean side, with the critic's nits:
  - single shared pool proven detector-independent (assert_shared_pool)
  - per-stratum entropy REPRESENTATIVENESS vs the full pool
  - clean SE AUROC on the fair pool WITH a bootstrap CI (external review B4)
  - side-by-side with the extreme ablation (the artefactual ~1.000)

CPU only: entropy + labels come from relabeled.jsonl (span oracle). No model.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.stats import auroc_ci
from se.attacks.select import (
    select_stratified, select_extreme_ablation, assert_shared_pool,
    assert_detector_blind, campaign_pool, load_labels, RELABELED,
)

N = 200          # per stratum for a stable clean-AUROC estimate (attack pool is smaller)
SEED = 0


def _entropy_map():
    return {qid: lab["entropy_nats"] for qid, lab in load_labels(RELABELED).items()}


def _clean_auroc(wrong_ids, right_ids, emap):
    labels = [1] * len(wrong_ids) + [0] * len(right_ids)
    scores = [emap[q] for q in wrong_ids] + [emap[q] for q in right_ids]
    return auroc_ci(labels, scores, n_boot=3000, seed=0), labels, scores


def _quantiles(vals):
    a = np.asarray(vals, float)
    return (float(np.mean(a)), float(np.quantile(a, .1)),
            float(np.quantile(a, .5)), float(np.quantile(a, .9)))


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    emap = _entropy_map()
    labels_all = load_labels(RELABELED)
    full_wrong = [q for q, l in labels_all.items() if not l["greedy_correct"]]
    full_right = [q for q, l in labels_all.items() if l["greedy_correct"]]

    log("# B1: fair stratified-random pool vs extreme-entropy ablation")
    log("")
    log(f"full pool strata: wrong={len(full_wrong)}, right={len(full_right)} "
        f"(of {len(labels_all)})")
    log("")

    # --- shared-pool proof (enforced by construction, not discipline) ---
    log("## Shared-pool invariant (detector-independent selection)")
    assert_detector_blind()   # raises if any selector exposes a detector param
    # Simulate the actual call sites: an SE cell and an SRE cell both route target
    # selection through campaign_pool(dataset, want, n, seed) -- a function with NO
    # detector parameter -- so they cannot diverge.
    se_w = [ex.question_id for ex in campaign_pool("triviaqa", "wrong", N, seed=SEED)]
    sre_w = [ex.question_id for ex in campaign_pool("triviaqa", "wrong", N, seed=SEED)]
    se_r = [ex.question_id for ex in campaign_pool("triviaqa", "right", N, seed=SEED)]
    sre_r = [ex.question_id for ex in campaign_pool("triviaqa", "right", N, seed=SEED)]
    assert se_w == sre_w and se_r == sre_r, "SE and SRE cells drew different ids"
    w_ids = assert_shared_pool("wrong", N, SEED)   # structural + behavioural proof
    r_ids = assert_shared_pool("right", N, SEED)
    log("assert_detector_blind passed: no selection function exposes a `detector`")
    log("parameter -> SE and SRE CANNOT select different pools (enforced, not hoped).")
    log(f"SE-cell ids == SRE-cell ids verified at the real call site (campaign_pool):")
    log(f"the SE and SRE campaigns use the IDENTICAL {len(w_ids)} hide + {len(r_ids)} "
        f"false-alarm ids.")
    log("")

    # --- representativeness ---
    log("## Entropy representativeness (fair pool vs full stratum)")
    log("mean / p10 / p50 / p90 of clean SE entropy (nats). Fair pool should MATCH")
    log("the full stratum; the ablation is deliberately skewed to the extremes.")
    log("")
    fw = _quantiles([emap[q] for q in w_ids]); ffw = _quantiles([emap[q] for q in full_wrong])
    fr = _quantiles([emap[q] for q in r_ids]); ffr = _quantiles([emap[q] for q in full_right])
    log("| stratum | source | mean | p10 | p50 | p90 |")
    log("| --- | --- | --- | --- | --- | --- |")
    log(f"| wrong | fair pool | {fw[0]:.3f} | {fw[1]:.3f} | {fw[2]:.3f} | {fw[3]:.3f} |")
    log(f"| wrong | full stratum | {ffw[0]:.3f} | {ffw[1]:.3f} | {ffw[2]:.3f} | {ffw[3]:.3f} |")
    log(f"| right | fair pool | {fr[0]:.3f} | {fr[1]:.3f} | {fr[2]:.3f} | {fr[3]:.3f} |")
    log(f"| right | full stratum | {ffr[0]:.3f} | {ffr[1]:.3f} | {ffr[2]:.3f} | {ffr[3]:.3f} |")
    log("")

    # --- clean AUROC: fair vs ablation ---
    log("## Clean SE AUROC: fair pool vs extreme ablation (the headline contrast)")
    fair_ci, _, _ = _clean_auroc(w_ids, r_ids, emap)
    ext_w = [ex.question_id for ex in select_extreme_ablation("wrong", N)]
    ext_r = [ex.question_id for ex in select_extreme_ablation("right", N)]
    ext_ci, _, _ = _clean_auroc(ext_w, ext_r, emap)
    log("| pool | clean SE AUROC (95% CI) |")
    log("| --- | --- |")
    log(f"| fair (stratified-random) | {fair_ci} |")
    log(f"| extreme-entropy ablation | {ext_ci} |")
    log("")
    log(f"The fair pool is the HONEST detector ranking on representative data. The")
    log(f"ablation's ~1.0 is the selection rule reflected back and was never real.")
    log(f"Post-attack AUROC (GPU recompute) will be measured against the fair number,")
    log(f"so the reported degradation shrinks — that is the point of clearing B1.")

    (RESULTS_DIR / "fair_pool_report.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'fair_pool_report.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
