"""Power of the exact exceedance test UNDER THE CEILING (critic ruling, 2026-08-02).

The published power figures (0.66/0.92 at 2x/3x) assumed a CONTINUOUS score. Real scores
have an atom at ln(N): on saturated targets the benign draws reach the ceiling too, so
under the conservative tie rule they count as exceedances and the target contributes
ANTI-evidence regardless of attack quality. This re-simulates power with:
  - the EMPIRICAL per-target headroom distribution from the completed n=80 FA cell,
  - censoring of every draw at that target's headroom (i.e. at the ln(10) ceiling),
  - conservative ties (benign >= attack counts),
calibrated so the simulated attack-saturation rate matches the observed 49%.
"""
import json, math, sys
import numpy as np

sys.path.insert(0, r"I:\GITHUBPROJECTS\SE Research\src")
from se.stats import exceedance_test

FA = r"C:\Users\Abhi\AppData\Local\Temp\claude\I--GITHUBPROJECTS-SE-Research\85d40e73-48d6-4927-b8b8-9fe3d295986d\scratchpad\fa80.jsonl"
rows = [json.loads(l) for l in open(FA) if l.strip()]
CAP = math.log(10)
HEADROOM = np.array([CAP - r["entropy_before"] for r in rows])   # empirical, n=80

N = 181            # attacker's candidate budget


def simulate(scale, m, n_targets, mult, trials, rng, alpha=0.05, headroom=None):
    """mult=1 -> H0 (attack is just a max over N draws from the same law).
    mult>1 -> attack behaves like a max over mult*N draws ('worth mult x its budget')."""
    hr_pool = HEADROOM if headroom is None else headroom
    rejects = 0
    sat_hits = 0
    sat_tot = 0
    for _ in range(trials):
        counts = []
        idx = rng.integers(0, len(hr_pool), n_targets)
        for h in hr_pool[idx]:
            n_att = int(round(N * mult))
            att = min(rng.exponential(scale, n_att).max(), h)     # censored at the ceiling
            ben = np.minimum(rng.exponential(scale, m), h)
            counts.append((int((ben >= att).sum()), m))           # CONSERVATIVE ties
            sat_tot += 1
            sat_hits += int(att >= h - 1e-12)
        if exceedance_test(counts, N)["p_value"] <= alpha:
            rejects += 1
    return rejects / trials, sat_hits / max(1, sat_tot)


rng = np.random.default_rng(0)
# Calibrate the per-draw scale so simulated attack saturation ~ the observed 49%.
print("calibrating scale to the observed 49% attack saturation ...")
best = None
for scale in [0.02, 0.03, 0.04, 0.05, 0.07, 0.09, 0.12, 0.16]:
    _, sat = simulate(scale, 30, 80, 1.0, 40, np.random.default_rng(1))
    if best is None or abs(sat - 0.49) < abs(best[1] - 0.49):
        best = (scale, sat)
    print(f"  scale={scale:<5} -> attack saturation {sat:.0%}")
scale = best[0]
print(f"=> using scale={scale} (saturation {best[1]:.0%} vs observed 49%)\n")

TRIALS = 400
print(f"{'m':>4} {'n':>4} {'H0 level':>9} {'pow 2x':>8} {'pow 3x':>8} {'pow 5x':>8}   (trials={TRIALS})")
for m in (30, 50, 60):
    lvl, _ = simulate(scale, m, 80, 1.0, TRIALS, np.random.default_rng(7))
    p2, _ = simulate(scale, m, 80, 2.0, TRIALS, np.random.default_rng(8))
    p3, _ = simulate(scale, m, 80, 3.0, TRIALS, np.random.default_rng(9))
    p5, _ = simulate(scale, m, 80, 5.0, TRIALS, np.random.default_rng(10))
    print(f"{m:>4} {80:>4} {lvl:>9.3f} {p2:>8.2f} {p3:>8.2f} {p5:>8.2f}")

# What if the ceiling were lifted (N=20 -> cap ln(20)), holding baselines fixed?
print("\nIf N=20 lifted the ceiling (headroom += ln(20)-ln(10) = 0.693 nats):")
HR20 = HEADROOM + (math.log(20) - math.log(10))
for m in (30, 50):
    lvl, sat = simulate(scale, m, 80, 1.0, TRIALS, np.random.default_rng(11), headroom=HR20)
    p2, _ = simulate(scale, m, 80, 2.0, TRIALS, np.random.default_rng(12), headroom=HR20)
    p3, _ = simulate(scale, m, 80, 3.0, TRIALS, np.random.default_rng(13), headroom=HR20)
    print(f"  m={m:<3} saturation {sat:.0%}  level {lvl:.3f}  pow2x {p2:.2f}  pow3x {p3:.2f}")
