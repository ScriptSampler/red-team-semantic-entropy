"""Derive and CHECK the correct null for the exceedance statistic when the score has an
atom at the ceiling. My last attempt failed because I changed the tie convention on the
OBSERVED statistic (conservative counting) while keeping an analytic null that assumed a
CONTINUOUS score. Mismatch -> degeneracy. Both sides must use the same convention.

Setup. Score distribution F has an atom of mass q at the top value v (the log N ceiling),
the rest continuous below. A = max of N attack candidates. B = one benign draw.

Claim (derived):
  P(B > A) = (1-q)^N * [ q + (1-q)/(N+1) ]
  - case A = v (prob 1-(1-q)^N): nothing can strictly exceed v  -> 0
  - case A < v (prob (1-q)^N): B exceeds if B is the atom (q), or B continuous and above
    the max of N continuous draws ((1-q)/(N+1))
Sanity: q=0 -> 1/(N+1)  (the classic exchangeability result). q=1 -> 0.

This says a SATURATED target is expected to yield ~ZERO exceedances under H0 — so
observing zero there is NOT evidence for the attack, which is exactly the information the
old conservative rule destroyed by counting ties as exceedances.

Below: verify the formula by simulation, then check whether K ~ Binomial(m, p) is an
adequate null (the benign draws are dependent through A, so this needs checking).
"""
import numpy as np

rng = np.random.default_rng(0)


def p_exceed_theory(q, N):
    return (1 - q) ** N * (q + (1 - q) / (N + 1))


def simulate_once(q, N, m, rng):
    """Draw N attack + m benign from a distribution with an atom of mass q at 1.0 and
    Uniform(0,1) below. Only ranks matter, so this is fully general."""
    def draw(k):
        atom = rng.random(k) < q
        vals = rng.random(k)          # continuous part in (0,1)
        return np.where(atom, 1.0, vals)
    A = draw(N).max()
    B = draw(m)
    return int((B > A).sum())         # STRICT ties, matching the null


print(f"{'q':>6} {'N':>5} {'theory P(B>A)':>15} {'simulated':>12} {'E[K] th':>9} {'E[K] sim':>9}")
N, m, T = 181, 30, 20000
for q in (0.0, 0.01, 0.05, 0.1, 0.2, 0.4):
    ks = [simulate_once(q, N, m, rng) for _ in range(T)]
    p_th = p_exceed_theory(q, N)
    print(f"{q:>6.2f} {N:>5} {p_th:>15.6f} {np.mean(ks)/m:>12.6f} "
          f"{m*p_th:>9.4f} {np.mean(ks):>9.4f}")

# Is Binomial(m, p) an adequate null for K, or does the dependence through A matter?
print("\nvariance check (Binomial would give m*p*(1-p)):")
for q in (0.0, 0.05, 0.2):
    ks = np.array([simulate_once(q, N, m, rng) for _ in range(T)])
    p_th = p_exceed_theory(q, N)
    print(f"  q={q:<5} sim var {ks.var():.4f}   binomial var {m*p_th*(1-p_th):.4f}   "
          f"ratio {ks.var()/max(1e-12, m*p_th*(1-p_th)):.2f}")
