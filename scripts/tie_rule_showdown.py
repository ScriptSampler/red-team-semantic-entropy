"""Does ANY tie rule rescue the max-based exceedance test under a ceiling?

The verification claimed a randomized/exchangeable tie rule gives power 0.40/0.82/0.99 at
m=30/50/60 where my conservative rule gave 0.00. Before I rebuild the analysis on that
claim I want to see it myself, because my own derivation suggests something stronger and
more pessimistic: once the ceiling atom is common, the attack max is AT the ceiling under
BOTH H0 and H1, so a statistic that only sees the max cannot distinguish them at all —
which no tie convention can fix.

Three rules, each with a null computed the SAME way as its observed statistic (that
consistency is what my first attempt got wrong):
  strict        K = #{benign >  attack_max}
  conservative  K = #{benign >= attack_max}          <- what I used; provably wrong
  randomized    ties broken uniformly at random      <- what the verification recommends

H0: attack candidates and benign draws are exchangeable draws from one distribution.
H1: the attack draws from the same distribution but with `mult` times the budget
    ("worth mult x its budget in random paraphrases" = the n_eff effect size).
Both under a top atom of mass q (the log N ceiling).
"""
import numpy as np

N_ATTACK = 181


def draw(k, q, rng):
    """k draws from: atom at 1.0 with mass q, Uniform(0,1) below. Only ranks matter."""
    return np.where(rng.random(k) < q, 1.0, rng.random(k))


def one_target(q, m, mult, rule, rng):
    A = draw(int(round(N_ATTACK * mult)), q, rng).max()
    B = draw(m, q, rng)
    if rule == "strict":
        return float((B > A).sum())
    if rule == "conservative":
        return float((B >= A).sum())
    if rule == "randomized":
        strict = (B > A).sum()
        tied = int((B == A).sum())
        if tied:
            # b = attack candidates at the max. Under exchangeability each tied benign
            # draw beats the attack max with prob 1/(b+1); we simulate the tie-break.
            b = max(1, int(rng.binomial(int(round(N_ATTACK * mult)) - 1, q)) + 1)
            strict += rng.binomial(tied, 1.0 / (b + 1))
        return float(strict)
    raise ValueError(rule)


def run(q, m, n_targets, mult, rule, trials, rng):
    return np.array([[one_target(q, m, mult, rule, rng) for _ in range(n_targets)]
                     for _ in range(trials)]).sum(axis=1)


def power(q, m, n_targets, mult, rule, trials=600, seed=0, alpha=0.05):
    """Null distribution simulated with the SAME rule, so the test is calibrated by
    construction; then measure rejection rate under H1 (small S = evidence for attack)."""
    rng = np.random.default_rng(seed)
    null = run(q, m, n_targets, 1.0, rule, 4000, rng)
    crit = np.quantile(null, alpha)                 # one-sided: reject if S <= crit
    obs = run(q, m, n_targets, mult, rule, trials, np.random.default_rng(seed + 1))
    lvl_obs = run(q, m, n_targets, 1.0, rule, trials, np.random.default_rng(seed + 2))
    return (obs <= crit).mean(), (lvl_obs <= crit).mean(), null.mean()


print("Saturation q is the per-PARAPHRASE chance of reaching the ceiling.")
print("P(attack max saturates) = 1-(1-q)^181 is shown so the regime is visible.\n")
print(f"{'q':>6} {'P(sat)':>8} {'rule':>14} {'m':>4} {'E[S]|H0':>9} {'level':>7} "
      f"{'pow 2x':>7} {'pow 5x':>7}")
for q in (0.0, 0.002, 0.01, 0.05):
    psat = 1 - (1 - q) ** N_ATTACK
    for rule in ("strict", "conservative", "randomized"):
        for m in (30, 60):
            p2, lvl, e0 = power(q, m, 80, 2.0, rule, seed=7)
            p5, _, _ = power(q, m, 80, 5.0, rule, seed=7)
            print(f"{q:>6.3f} {psat:>8.3f} {rule:>14} {m:>4} {e0:>9.3f} {lvl:>7.3f} "
                  f"{p2:>7.2f} {p5:>7.2f}")
    print()
