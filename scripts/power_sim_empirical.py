"""Decisive power simulation using the N=20 pilot's EMPIRICAL headroom gains.

The first simulation (scripts/power_sim_ceiling.py) assumed lifting N=10 -> N=20 adds the
full log(20)-log(10) = 0.693 nats of headroom. The pilot refutes that: baselines rise with N
too, so realized gains are heterogeneous and often far smaller. This re-runs the power
calculation with the gains actually observed, and applies the pre-committed decision rule
(critique_log 23a): proceed at N=20 iff power >= 0.60 at a 2x effect with m <= 50.

    .venv/Scripts/python.exe scripts/power_sim_empirical.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from se.config import RESULTS_DIR                      # noqa: E402
from se.stats import exceedance_test                   # noqa: E402

N_ATTACK = 181
CAP10, CAP20 = math.log(10), math.log(20)


def load_pilot(path: Path):
    """Per-target (headroom_at_N10, headroom_at_N20) from the pilot checkpoint."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out.append((CAP10 - r["entropy_before_old"], CAP20 - r["entropy_before_new"]))
    return out


def simulate(scale, headrooms, m, n_targets, mult, trials, seed, alpha=0.05):
    rng = np.random.default_rng(seed)
    hr = np.array(headrooms, dtype=float)
    hr = np.clip(hr, 1e-6, None)
    rejects = sat = tot = 0
    for _ in range(trials):
        counts = []
        for h in hr[rng.integers(0, len(hr), n_targets)]:
            att = min(rng.exponential(scale, int(round(N_ATTACK * mult))).max(), h)
            ben = np.minimum(rng.exponential(scale, m), h)
            counts.append((int((ben >= att).sum()), m))    # conservative ties
            tot += 1
            sat += int(att >= h - 1e-12)
        if exceedance_test(counts, N_ATTACK)["p_value"] <= alpha:
            rejects += 1
    return rejects / trials, sat / max(1, tot)


def main() -> int:
    ck = RESULTS_DIR / "pilot_n20_ckpt_def.jsonl"
    if not ck.exists():
        print(f"no pilot checkpoint at {ck}"); return 1
    pairs = load_pilot(ck)
    h10 = [a for a, _ in pairs]
    h20 = [b for _, b in pairs]
    gains = [b - a for a, b in pairs]
    print(f"pilot targets: {len(pairs)}")
    print(f"  headroom at N=10: mean {np.mean(h10):.3f}")
    print(f"  headroom at N=20: mean {np.mean(h20):.3f}")
    print(f"  EMPIRICAL gain  : mean {np.mean(gains):+.3f}  median {np.median(gains):+.3f} "
          f"(the naive assumption was +{CAP20-CAP10:.3f})")

    # Calibrate the per-draw scale to reproduce the observed N=10 saturation (49%) on the
    # full empirical N=10 headroom distribution, then hold it fixed for the N=20 arm.
    fa = RESULTS_DIR.parent / "results"          # placeholder to keep paths obvious
    best, TRIALS = None, 300
    for scale in [0.04, 0.06, 0.09, 0.12, 0.16, 0.20]:
        _, s = simulate(scale, h10, 30, 60, 1.0, 60, 11)
        if best is None or abs(s - 0.49) < abs(best[1] - 0.49):
            best = (scale, s)
    scale = best[0]
    print(f"  calibrated scale {scale} (N=10 saturation {best[1]:.0%} vs observed 49%)\n")

    print(f"{'cfg':<10}{'m':>4}{'saturation':>12}{'level':>8}{'pow@2x':>9}{'pow@3x':>9}")
    rows = []
    for label, hr in (("N=10", h10), ("N=20", h20)):
        for m in (30, 50):
            lvl, sat = simulate(scale, hr, m, 80, 1.0, TRIALS, 21)
            p2, _ = simulate(scale, hr, m, 80, 2.0, TRIALS, 22)
            p3, _ = simulate(scale, hr, m, 80, 3.0, TRIALS, 23)
            print(f"{label:<10}{m:>4}{sat:>11.0%}{lvl:>8.3f}{p2:>9.2f}{p3:>9.2f}")
            rows.append((label, m, sat, lvl, p2, p3))

    ok = [r for r in rows if r[0] == "N=20" and r[1] <= 50 and r[4] >= 0.60]
    verdict = ("PROCEED at N=20 (pre-committed bar met: power >= 0.60 at 2x with m <= 50)"
               if ok else
               "DO NOT PROCEED: power < 0.60 at 2x for every m <= 50. Per critique_log 23a, "
               "FA nats and the FA exceedance test are NOT identifiable at feasible N; report "
               "censoring-robust statistics only.")
    print(f"\nVERDICT: {verdict}")

    L = ["# Power at N=20 using the pilot's EMPIRICAL headroom gains", "",
         f"Pilot targets: {len(pairs)}. Mean headroom {np.mean(h10):.3f} (N=10) -> "
         f"{np.mean(h20):.3f} (N=20); empirical gain {np.mean(gains):+.3f} nats vs the "
         f"+{CAP20-CAP10:.3f} the first simulation naively assumed (baselines rise with N too).",
         "", "| config | m | saturation | H0 level | power @2x | power @3x |",
         "|---|---|---|---|---|---|"]
    for label, m, sat, lvl, p2, p3 in rows:
        L.append(f"| {label} | {m} | {sat:.0%} | {lvl:.3f} | {p2:.2f} | {p3:.2f} |")
    L += ["", f"**VERDICT: {verdict}**", "",
          "Decision rule pre-committed in critique_log 23a BEFORE the pilot completed."]
    out = RESULTS_DIR / "power_n20_empirical.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[report] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
