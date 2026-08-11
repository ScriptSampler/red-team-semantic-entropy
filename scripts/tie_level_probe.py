"""Why is the randomized-tie test running at H0 level ~0.093 instead of 0.05?

Candidate causes:
  (A) DISCRETENESS. S = sum of integer-ish counts, so P(S <= c) jumps. A one-sided test that
      rejects on p <= 0.05 with a discrete statistic has ACTUAL level equal to the largest
      attainable P(S <= c) that is <= 0.05 -- which should make it CONSERVATIVE, not
      anti-conservative. So discreteness alone cannot explain 0.093.
  (B) ROUNDING. exceedance_counts_randomized returns FRACTIONAL counts (averaged over
      tie-break draws) and null_control rounds them to int before the exact convolution.
      Rounding a fractional statistic against an integer null is a mismatch and can shift
      the level either way. <-- prime suspect.
  (C) The convolution null assumes independent per-target K_j with the theoretical
      BetaBinomial(m;1,N) marginal, but the ACTUAL statistic uses measured b, whose
      distribution differs from the theoretical one.

This isolates them.
"""
import sys
import numpy as np

sys.path.insert(0, r"I:\GITHUBPROJECTS\SE Research\src")
from se.stats import exceedance_test

N, M, T = 181, 30, 80
rng = np.random.default_rng(0)


def draw_target(q, mult=1.0):
    """H0/H1 draws with a ceiling atom of mass q. Returns (K_fractional, K_rounded)."""
    n_att = int(round(N * mult))
    att = np.where(rng.random(n_att) < q, 1.0, rng.random(n_att))
    A = att.max()
    b = max(1, int((att >= 1.0 - 1e-12).sum())) if A >= 1.0 - 1e-12 else 1
    ben = np.where(rng.random(M) < q, 1.0, rng.random(M))
    strict = int((ben > A + 1e-12).sum())
    tied = int(np.isclose(ben, A).sum())
    frac = strict + (tied / (b + 1) if tied else 0.0)          # expected credit
    randomized = strict + (rng.binomial(tied, 1 / (b + 1)) if tied else 0)   # one draw
    return frac, randomized


def level(q, mode, trials=1500, alpha=0.05):
    rej = 0
    for _ in range(trials):
        ks = []
        for _ in range(T):
            f, r = draw_target(q)
            ks.append(int(round(f)) if mode == "rounded-expected" else int(r))
        if exceedance_test([(k, M) for k in ks], N)["p_value"] <= alpha:
            rej += 1
    return rej / trials


print("H0 level of the analytic-convolution test, nominal alpha = 0.05")
print(f"{'q':>6} {'rounded-expected':>18} {'single randomized draw':>24}")
for q in (0.0, 0.01, 0.05):
    a = level(q, "rounded-expected")
    b = level(q, "randomized")
    print(f"{q:>6.2f} {a:>18.3f} {b:>24.3f}")

print("\nIf 'rounded-expected' is inflated and 'single randomized draw' is near 0.05,")
print("the defect is the ROUNDING of a fractional statistic against an integer null,")
print("not the tie rule itself.")
