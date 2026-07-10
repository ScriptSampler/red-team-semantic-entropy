"""Diagnose the benign-paraphrase noise floor per clustering arm, from a null_control
--dump_diag JSON. Answers the critic's open gate: why is the judge benign floor (~-0.19)
far more negative than NLI's (~-0.02), and how should that shape reading the judge net?

Pre-registered hypotheses (docs/benign_floor_diagnosis.md):
  H_split  judge over-splits the BASELINE -> inflated baseline_judge -> benign moves go
           negative. Signature: mean(baseline_judge - baseline_nli) > 0 AND benign_judge
           correlates negatively with that per-target baseline gap.
  H_rtm    regression to the mean of selected targets. Signature: benign_judge correlates
           negatively with the baseline_judge LEVEL, with baseline gap ~ 0.
  H_noise  n=6 artefact. Signature: judge floor CI wide / overlaps the other arms at scale.

Pure-CPU analysis of already-computed numbers; no models. Run after the definitive judge
null control:  python scripts/null_control.py ... --dump_diag results/diag_def.json
               python scripts/diagnose_benign_floor.py results/diag_def.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from se.stats import bootstrap_ci  # noqa: E402

ARMS = ("nli", "exact", "embed", "judge")


def _corr(x, y):
    """Pearson r, or nan if either series is constant / too short."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def diagnose(records: list[dict], detector: str = "se", attack: str = "false_alarm") -> dict:
    """Core analysis (testable). Returns per-arm floors + the H_split/H_rtm signatures."""
    rows = [r for r in records
            if r.get("detector") == detector and r.get("attack") == attack]
    if not rows:
        return {"n": 0, "detector": detector, "attack": attack, "arms": {}, "verdict": "no data"}

    out: dict = {"n": len(rows), "detector": detector, "attack": attack, "arms": {}}
    for arm in ARMS:
        # per-target mean benign move (robust to unequal K); skip arms with no data
        per_target = [float(np.mean(r["benign"][arm]))
                      for r in rows
                      if r["benign"].get(arm) not in (None, [])]
        if not per_target:
            continue
        ci = bootstrap_ci(per_target, np.mean)
        out["arms"][arm] = {"benign_floor": ci.point, "lo": ci.lo, "hi": ci.hi,
                            "n_targets": len(per_target)}

    # H_split / H_rtm signatures need per-target baseline gap + benign_judge, paired.
    paired = [r for r in rows
              if r["benign"].get("judge") not in (None, [])
              and r["baseline"].get("judge") is not None
              and r["baseline"].get("nli") is not None]
    if len(paired) >= 3:
        base_judge = [float(r["baseline"]["judge"]) for r in paired]
        base_nli = [float(r["baseline"]["nli"]) for r in paired]
        gap = [j - n for j, n in zip(base_judge, base_nli)]
        benign_judge = [float(np.mean(r["benign"]["judge"])) for r in paired]
        gap_ci = bootstrap_ci(gap, np.mean)
        out["baseline_gap_judge_minus_nli"] = {"point": gap_ci.point, "lo": gap_ci.lo,
                                               "hi": gap_ci.hi}
        out["corr_benign_judge_vs_gap"] = _corr(benign_judge, gap)      # H_split if < 0
        out["corr_benign_judge_vs_baseline_judge"] = _corr(benign_judge, base_judge)  # H_rtm if < 0
        out["verdict"] = _verdict(out)
    else:
        out["verdict"] = "insufficient paired judge data"
    return out


def _verdict(out: dict) -> str:
    gap = out.get("baseline_gap_judge_minus_nli", {})
    r_gap = out.get("corr_benign_judge_vs_gap", float("nan"))
    r_base = out.get("corr_benign_judge_vs_baseline_judge", float("nan"))
    judge = out["arms"].get("judge", {})
    # H_noise: judge floor CI straddles 0 (no robust floor to explain)
    if judge and judge["lo"] <= 0.0 <= judge["hi"]:
        return ("H_noise-leaning: judge benign-floor CI straddles 0 "
                f"[{judge['lo']:+.3f}, {judge['hi']:+.3f}] — no robust floor at this n")
    gap_pos = gap.get("lo", -1) > 0  # baseline gap CI strictly > 0
    if gap_pos and (r_gap == r_gap and r_gap < -0.2):
        return ("H_split: judge splits the baseline more than NLI "
                f"(gap {gap['point']:+.3f} [{gap['lo']:+.3f},{gap['hi']:+.3f}]) and benign_judge "
                f"falls with that gap (r={r_gap:+.2f}). Judge is CONSERVATIVE for false-alarm; "
                "a null judge net is ambiguous. Percentile stays the headline.")
    if (r_base == r_base and r_base < -0.2) and not gap_pos:
        return ("H_rtm: benign_judge regresses toward the mean (r vs baseline_judge "
                f"{r_base:+.2f}) with no baseline gap. Floor is target-selection, symmetric; "
                "net inflation real, percentile the right headline.")
    return ("mixed/inconclusive: report the floors + correlations verbatim and lean on the "
            "scale-free percentile; do not over-interpret the net.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("diag_json", help="path to a null_control --dump_diag JSON")
    ap.add_argument("--detector", default="se")
    ap.add_argument("--attack", default="false_alarm")
    args = ap.parse_args()

    records = json.loads(Path(args.diag_json).read_text())
    d = diagnose(records, args.detector, args.attack)
    print(f"# Benign-floor diagnosis - {d['detector']}/{d['attack']}  (n={d['n']})\n")
    if not d["arms"]:
        print("no data for this cell"); return 0
    print("Per-arm benign floor (per-target mean move, nats; bootstrap CI over targets):")
    for arm in ARMS:
        a = d["arms"].get(arm)
        if a:
            print(f"  {arm:6s}: {a['benign_floor']:+.3f} [{a['lo']:+.3f}, {a['hi']:+.3f}]"
                  f"  (n={a['n_targets']})")
    if "baseline_gap_judge_minus_nli" in d:
        g = d["baseline_gap_judge_minus_nli"]
        print(f"\nbaseline gap (judge - nli): {g['point']:+.3f} [{g['lo']:+.3f}, {g['hi']:+.3f}]")
        print(f"corr(benign_judge, gap):            {d['corr_benign_judge_vs_gap']:+.3f}  "
              "(< 0 -> H_split)")
        print(f"corr(benign_judge, baseline_judge): {d['corr_benign_judge_vs_baseline_judge']:+.3f}  "
              "(< 0, gap~0 -> H_rtm)")
    print(f"\nVERDICT: {d['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
