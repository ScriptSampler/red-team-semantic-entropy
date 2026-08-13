"""Power of the exceedance test under the RANDOMIZED tie rule, at the empirical saturation.

Supersedes scripts/power_sim_ceiling.py, whose zero-power result was an artifact of the
conservative tie rule (critique_log 26), not of the ceiling. This answers the question that
actually sets the definitive run's cost: with the correct tie rule and the real per-target
headroom distribution, how many benign draws m does the false-alarm analysis need?

Model, anchored to data rather than convenience:
  - per-target headroom drawn from the empirical n=80 FA distribution (ceiling - baseline),
  - every draw censored at that headroom (this is what creates the ceiling atom),
  - attack = max of N*mult draws; b = how many of those land on the cap (the multiplicity
    the instrumented optimiser now records as n_feasible_at_best),
  - benign = m draws; K = strict exceedances + Binomial(ties, 1/(b+1)) tie credit,
  - the null is simulated with the SAME rule (mult=1), so the test is calibrated by
    construction and `level` below is a check, not an assumption.

    .venv/Scripts/python.exe scripts/power_sim_randomized.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from se.config import RESULTS_DIR                     # noqa: E402

N_ATTACK = 181
CAP10 = math.log(10)


def load_headroom(fa_jsonl: Path) -> np.ndarray:
    rows = [json.loads(l) for l in fa_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    return np.array([CAP10 - r["entropy_before"] for r in rows], dtype=float)


def one_target(scale, h, m, mult, rng):
    """Returns the randomized-tie exceedance count for one target."""
    n_att = int(round(N_ATTACK * mult))
    att_raw = rng.exponential(scale, n_att)
    att = np.minimum(att_raw, h)
    A = att.max()
    b = max(1, int((att >= h - 1e-12).sum())) if A >= h - 1e-12 else 1
    ben = np.minimum(rng.exponential(scale, m), h)
    strict = int((ben > A + 1e-12).sum())
    tied = int(np.isclose(ben, A).sum())
    credit = rng.binomial(tied, 1.0 / (b + 1)) if tied else 0
    return strict + credit


def run(scale, hr, m, n_targets, mult, trials, rng):
    return np.array([[one_target(scale, h, m, mult, rng)
                      for h in hr[rng.integers(0, len(hr), n_targets)]]
                     for _ in range(trials)]).sum(axis=1)


def power(scale, hr, m, n_targets, mult, seed, trials=400, alpha=0.05):
    rng = np.random.default_rng(seed)
    null = run(scale, hr, m, n_targets, 1.0, 2500, rng)
    crit = np.quantile(null, alpha)                       # reject when S <= crit
    obs = run(scale, hr, m, n_targets, mult, trials, np.random.default_rng(seed + 1))
    lvl = run(scale, hr, m, n_targets, 1.0, trials, np.random.default_rng(seed + 2))
    return (obs <= crit).mean(), (lvl <= crit).mean(), null.mean()


def main() -> int:
    # The headroom used to come from a session-scoped temp file, so this script stopped
    # being reproducible the moment that scratch directory was cleaned. It now resolves the
    # same 80 targets from the attack cache, falling back to the committed mirror
    # results/fa80_headroom.md (2026-08-13). The vector is byte-identical to the old scratch
    # extract: same question ids, same order, same entropy_before.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from power_sim_deployed import resolve_headroom       # noqa: E402  (lazy: avoids a cycle)
    hr, _qids, provenance = resolve_headroom()
    print(f"empirical headroom from {provenance}: n={len(hr)} mean {hr.mean():.3f} "
          f"zero-headroom {int((hr <= 1e-9).sum())}")

    # calibrate the per-draw scale to the observed 49% attack saturation
    best = None
    for s in (0.04, 0.06, 0.09, 0.12, 0.16, 0.20):
        rng = np.random.default_rng(3)
        sat = np.mean([1.0 if one_target(s, h, 5, 1.0, rng) is not None and
                       (np.minimum(rng.exponential(s, N_ATTACK), h).max() >= h - 1e-12)
                       else 0.0 for h in hr])
        if best is None or abs(sat - 0.49) < abs(best[1] - 0.49):
            best = (s, sat)
    scale = best[0]
    print(f"calibrated scale {scale} (saturation {best[1]:.0%} vs observed 49%)\n")

    print(f"{'m':>5}{'E[S]|H0':>10}{'level':>8}{'pow 2x':>9}{'pow 3x':>9}{'pow 5x':>9}")
    rows = []
    for m in (20, 30, 50, 80):
        p2, lvl, e0 = power(scale, hr, m, 80, 2.0, seed=11)
        p3, _, _ = power(scale, hr, m, 80, 3.0, seed=11)
        p5, _, _ = power(scale, hr, m, 80, 5.0, seed=11)
        print(f"{m:>5}{e0:>10.2f}{lvl:>8.3f}{p2:>9.2f}{p3:>9.2f}{p5:>9.2f}")
        rows.append((m, e0, lvl, p2, p3, p5))

    L = ["# Power under the RANDOMIZED tie rule (supersedes power_under_ceiling.md)", "",
         "Empirical n=80 headroom distribution, draws censored at the ceiling, null "
         "simulated with the same rule as the statistic.", "",
         "| m | E[S] under H0 | level | power @2x | power @3x | power @5x |",
         "|---|---|---|---|---|---|"]
    for m, e0, lvl, p2, p3, p5 in rows:
        L.append(f"| {m} | {e0:.2f} | {lvl:.3f} | {p2:.2f} | {p3:.2f} | {p5:.2f} |")
    L += ["", "The conservative rule gave 0.00 power at every m; that was the rule, not the "
          "ceiling (critique_log 26). Pick the smallest m clearing the pre-committed bar and "
          "cost the definitive run from it: the judge arm is ~(2+m+n_seeds) clusterings per "
          "target, ~55s each."]
    out = RESULTS_DIR / "power_randomized.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
