"""SCRATCH: independent re-derivation + simulation audit of src/se/stats.py.

Does NOT modify stats.py or any test. Read-only w.r.t. the repo.
Run:  .venv/Scripts/python.exe scratch_stats_audit.py <part>
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import betabinom, hypergeom

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from se.stats import (  # noqa: E402
    analytic_max_percentile, benign_equivalent_budget, ceiling_saturation,
    exceedance_counts, exceedance_counts_randomized, exceedance_test,
    exceedance_test_over_seeds, expected_max_at_budget, flip_test_conditional,
    paired_max_net,
)

A_DEFAULT = 181
NTARGETS = 80


# --------------------------------------------------------------------------------------
# Fast, verified replica of exceedance_test's null (all m_j equal -> one cached CDF).
# --------------------------------------------------------------------------------------
_NULL_CACHE: dict = {}


def null_cdf(m: int, n_targets: int, N: int) -> np.ndarray:
    """CDF of S = sum_j K_j, K_j ~ BetaBinom(m;1,N), built exactly as exceedance_test does."""
    key = (m, n_targets, N)
    if key not in _NULL_CACHE:
        pmf = betabinom.pmf(np.arange(m + 1), m, 1, N)
        pmf = np.asarray(pmf, dtype=float)
        pmf = pmf / pmf.sum()
        dist = np.array([1.0])
        for _ in range(n_targets):
            dist = np.convolve(dist, pmf)
        _NULL_CACHE[key] = np.cumsum(dist)
    return _NULL_CACHE[key]


def fast_p(obs, m: int, n_targets: int, N: int):
    """Vectorised P(S <= obs), identical to exceedance_test's p_value for equal-m counts."""
    cdf = null_cdf(m, n_targets, N)
    obs = np.asarray(obs, dtype=int)
    p = np.where(obs < len(cdf), cdf[np.clip(obs, 0, len(cdf) - 1)], 1.0)
    return np.clip(p, 0.0, 1.0)


def verify_fast_path():
    rng = np.random.default_rng(0)
    worst = 0.0
    for m, nt, N in ((20, 80, 181), (30, 80, 181), (50, 40, 181), (80, 12, 181)):
        for _ in range(25):
            ks = rng.integers(0, m + 1, nt)
            ref = exceedance_test([(int(k), m) for k in ks], N)["p_value"]
            got = float(fast_p(int(ks.sum()), m, nt, N))
            worst = max(worst, abs(ref - got))
    print(f"[fast-path check] max |p_fast - p_shipped| over 100 cases = {worst:.3e}")
    assert worst < 1e-12, "fast path does not replicate the shipped null"


# --------------------------------------------------------------------------------------
# Data generator: atom of mass q at 1.0, Uniform(0,1) below.  Only ranks matter.
# --------------------------------------------------------------------------------------
def gen_targets(q, m, n_targets, N, mult, rng):
    """Returns (attack_max[nt], b[nt], strict[nt], tied[nt]) for n_targets targets."""
    n_att = int(round(N * mult))
    # attack draws
    at_atom = rng.random((n_targets, n_att)) < q
    att = np.where(at_atom, 1.0, rng.random((n_targets, n_att)))
    A = att.max(axis=1)
    sat = A >= 1.0                                    # attack max pinned at the atom
    b = np.where(sat, at_atom.sum(axis=1), 1)
    b = np.maximum(b, 1)
    # benign draws
    bn_atom = rng.random((n_targets, m)) < q
    ben = np.where(bn_atom, 1.0, rng.random((n_targets, m)))
    strict = (ben > A[:, None]).sum(axis=1)
    tied = (ben == A[:, None]).sum(axis=1)
    return A, b.astype(int), strict.astype(int), tied.astype(int)


def credit_binomial(tied, b, rng):
    """What stats.py does: Binomial(tied, 1/(b+1))."""
    return rng.binomial(tied, 1.0 / (b + 1.0))


def credit_betabinom(tied, b, rng):
    """Exchangeable-exact: BetaBinomial(tied; 1, b) == #benign ahead of all b attack
    in a uniform random permutation of the tie group."""
    p = rng.beta(1.0, b.astype(float))
    return rng.binomial(tied, p)


# --------------------------------------------------------------------------------------
PARTS = {}


def part(name):
    def deco(fn):
        PARTS[name] = fn
        return fn
    return deco


# ======================================================================================
@part("A")
def part_a():
    """Derivations, checked numerically against the shipped code's assumptions."""
    print("=" * 86)
    print("PART A — re-derivation checks")
    print("=" * 86)
    verify_fast_path()

    N, m = 181, 50
    rng = np.random.default_rng(1)
    # A1: continuous case, K = #benign above max-of-N ~ BetaBinom(m;1,N)
    draws = 200_000
    att = rng.random((draws, N)).max(axis=1)
    ben = rng.random((draws, m))
    K = (ben > att[:, None]).sum(axis=1)
    print(f"\n[A1] no-atom, K=#benign>attack-max, N={N} m={m}, {draws} reps")
    print(f"     E[K] measured {K.mean():.5f}   m/(N+1) = {m/(N+1):.5f}")
    print(f"     Var[K] measured {K.var():.5f}   BetaBinom(m;1,N) var "
          f"{betabinom.var(m, 1, N):.5f}")
    ks = np.bincount(K, minlength=8)[:6] / draws
    print(f"     pmf 0..5 measured {np.round(ks,4)}")
    print(f"     pmf 0..5 BetaBin  {np.round(betabinom.pmf(np.arange(6), m, 1, N),4)}")
    print(f"     P(attack beats all m) measured {(K==0).mean():.5f}  N/(N+m) = {N/(N+m):.5f}")

    # A2: the tie-credit law.  Exact answer is BetaBinom(tied;1,b), NOT Binom(tied,1/(b+1)).
    print("\n[A2] tie-credit law: #benign that outrank the best of b attack, in a uniform "
          "random\n     permutation of the tie group (tied benign + b attack)")
    print(f"     {'tied':>5}{'b':>5} | {'perm E':>8}{'perm Var':>10} | {'BetaBin E':>10}"
          f"{'BetaBin V':>10} | {'Binom E':>9}{'Binom V':>9}")
    for tied, b in ((10, 1), (20, 1), (10, 9), (30, 9), (20, 60), (80, 60)):
        r = np.random.default_rng(7)
        reps = 200_000
        # brute-force random permutation of the tie group
        u_ben = r.random((reps, tied))
        u_att = r.random((reps, b)).min(axis=1)
        T = (u_ben < u_att[:, None]).sum(axis=1)
        bb_e, bb_v = betabinom.mean(tied, 1, b), betabinom.var(tied, 1, b)
        bi_e, bi_v = tied / (b + 1), tied * (1 / (b + 1)) * (b / (b + 1))
        print(f"     {tied:>5}{b:>5} | {T.mean():>8.4f}{T.var():>10.4f} | {bb_e:>10.4f}"
              f"{bb_v:>10.4f} | {bi_e:>9.4f}{bi_v:>9.4f}")

    # A3: does the code's rule still give the right MEAN for K under H0 with an atom?
    print("\n[A3] H0 with atom: E[K] under the shipped Binomial credit vs m/(N+1)")
    print(f"     {'q':>7}{'m':>5} | {'E[K] shipped':>13}{'E[K] exact-BB':>15}"
          f"{'m/(N+1)':>10} | {'Var shipped':>12}{'Var exact-BB':>13}{'Var null':>10}")
    for q in (0.0, 0.01, 0.05):
        for m in (30, 80):
            r = np.random.default_rng(11)
            reps = 60_000
            _, b, s, t = gen_targets(q, m, reps, N, 1.0, r)
            k_bin = s + credit_binomial(t, b, r)
            k_bb = s + credit_betabinom(t, b, r)
            print(f"     {q:>7.3f}{m:>5} | {k_bin.mean():>13.5f}{k_bb.mean():>15.5f}"
                  f"{m/(N+1):>10.5f} | {k_bin.var():>12.5f}{k_bb.var():>13.5f}"
                  f"{betabinom.var(m,1,N):>10.5f}")


# ======================================================================================
@part("B")
def part_b():
    """Measured H0 level of the SHIPPED exceedance_counts_randomized + exceedance_test."""
    print("=" * 86)
    print("PART B — measured H0 rejection rate, nominal alpha=0.05, A=181, 80 targets")
    print("=" * 86)
    verify_fast_path()
    N, nt, trials, alpha = 181, NTARGETS, 20_000, 0.05
    print(f"\ntrials={trials} per cell.  MC se on a 0.05 level ~ {np.sqrt(.05*.95/trials):.4f}\n")
    print(f"{'q':>7}{'P(sat)':>8}{'m':>5} | {'level SHIPPED':>14}{'level exact-BB':>15}"
          f"| {'E[S] obs':>9}{'E[S] null':>10}{'sd obs':>8}{'sd null':>8}")
    rows = []
    for q in (0.0, 0.01, 0.05):
        psat = 1 - (1 - q) ** N
        for m in (20, 30, 50, 80):
            r = np.random.default_rng(20260812)
            S_bin = np.empty(trials, dtype=int)
            S_bb = np.empty(trials, dtype=int)
            chunk = 200
            for i in range(0, trials, chunk):
                n = min(chunk, trials - i)
                _, b, s, t = gen_targets(q, m, n * nt, N, 1.0, r)
                kb = (s + credit_binomial(t, b, r)).reshape(n, nt).sum(axis=1)
                kx = (s + credit_betabinom(t, b, r)).reshape(n, nt).sum(axis=1)
                S_bin[i:i + n] = kb
                S_bb[i:i + n] = kx
            lvl_bin = float((fast_p(S_bin, m, nt, N) <= alpha).mean())
            lvl_bb = float((fast_p(S_bb, m, nt, N) <= alpha).mean())
            cdf = null_cdf(m, nt, N)
            pmf = np.diff(np.concatenate([[0.0], cdf]))
            supp = np.arange(len(pmf))
            e_null = float((supp * pmf).sum())
            sd_null = float(np.sqrt((supp**2 * pmf).sum() - e_null**2))
            print(f"{q:>7.3f}{psat:>8.3f}{m:>5} | {lvl_bin:>14.4f}{lvl_bb:>15.4f}"
                  f"| {S_bin.mean():>9.2f}{e_null:>10.2f}{S_bin.std():>8.2f}{sd_null:>8.2f}")
            rows.append((q, m, lvl_bin, lvl_bb))
    print("\nSHIPPED = Binomial(tied,1/(b+1)) credit (what stats.py does).")
    print("exact-BB = BetaBinomial(tied;1,b) credit (the exchangeable-correct draw).")


# ======================================================================================
@part("C")
def part_c():
    """exceedance_test_over_seeds: is median-p valid?"""
    print("=" * 86)
    print("PART C — exceedance_test_over_seeds (median p across 101 tie-breaks)")
    print("=" * 86)
    verify_fast_path()

    # C1: the identity median_seeds(p) == G(median_seeds(S)) -- p is a monotone fn of S,
    # and the null G does not change across seeds.  Demonstrate on the real functions.
    print("\n[C1] identity check on the SHIPPED functions: median-p == p(median S)")
    rng = np.random.default_rng(3)
    CAP = float(np.log(10))
    for trial in range(3):
        nt, m, b = 40, 30, 9
        head = rng.random(nt) * 0  # all targets share the ceiling value
        am = [CAP] * nt
        bl = [list(np.where(rng.random(m) < 0.4, CAP, rng.random(m) * CAP)) for _ in range(nt)]
        tb = [b] * nt
        res = exceedance_test_over_seeds(am, bl, tb, 181, n_seeds=101)
        S = []
        ps = []
        for s in range(101):
            c = exceedance_counts_randomized(am, bl, tb, seed=s)
            S.append(sum(k for k, _ in c))
            ps.append(exceedance_test(c, 181)["p_value"])
        med_S = int(np.median(S))
        p_of_med_S = exceedance_test([(0, m)] * 0 + [(med_S, m)] + [(0, m)] * (nt - 1), 181)
        # rebuild p at the median TOTAL using the same null
        p_medS = float(fast_p(med_S, m, nt, 181))
        print(f"     trial {trial}: median-p={res['p_median']:.6f}  "
              f"p(median S)={p_medS:.6f}  median S={med_S}  "
              f"S range [{min(S)},{max(S)}]  p range [{min(ps):.4f},{max(ps):.4f}]")
    del head, p_of_med_S

    # C2: measured level of the median-p decision rule vs the single-draw rule
    print("\n[C2] measured H0 level, nominal 0.05, A=181, 80 targets, 101 seeds")
    N, nt, alpha = 181, NTARGETS, 0.05
    trials = 4000
    print(f"     trials={trials}\n")
    print(f"     {'q':>7}{'m':>5} | {'single draw':>12}{'median-p':>10}{'frac<=.05 rule':>16}"
          f" | {'sd(S) single':>13}{'sd(median S)':>13}")
    for q in (0.0, 0.01, 0.05):
        for m in (20, 30, 50, 80):
            r = np.random.default_rng(555)
            S1 = np.empty(trials, dtype=int)
            Smed = np.empty(trials, dtype=float)
            frac05 = np.empty(trials)
            chunk = 40
            for i in range(0, trials, chunk):
                n = min(chunk, trials - i)
                _, b, s, t = gen_targets(q, m, n * nt, N, 1.0, r)
                # 101 independent tie-break realisations of the SAME data
                cred = np.stack([credit_binomial(t, b, r) for _ in range(101)])   # (101, n*nt)
                Sall = (s[None, :] + cred).reshape(101, n, nt).sum(axis=2)        # (101, n)
                S1[i:i + n] = Sall[0]
                Smed[i:i + n] = np.median(Sall, axis=0)
                pall = fast_p(np.rint(Sall).astype(int), m, nt, N)
                frac05[i:i + n] = (pall <= alpha).mean(axis=0)
            lvl1 = float((fast_p(S1, m, nt, N) <= alpha).mean())
            lvlmed = float((fast_p(np.rint(Smed).astype(int), m, nt, N) <= alpha).mean())
            lvlfrac = float((frac05 >= 0.5).mean())
            print(f"     {q:>7.3f}{m:>5} | {lvl1:>12.4f}{lvlmed:>10.4f}{lvlfrac:>16.4f}"
                  f" | {S1.std():>13.2f}{Smed.std():>13.2f}")
    print("\n     'median-p' rejects when the median over 101 tie-breaks of p is <= 0.05,")
    print("     which (p monotone in S, null fixed) is identical to p(median S) <= 0.05.")


# ======================================================================================
@part("D")
def part_d():
    """Power cost of the Binomial-instead-of-BetaBinomial tie credit."""
    print("=" * 86)
    print("PART D — power: shipped Binomial credit vs exchangeable-exact BetaBinomial")
    print("=" * 86)
    verify_fast_path()
    N, nt, alpha, trials = 181, NTARGETS, 0.05, 6000
    print(f"\nH1 = the attack is worth `mult` x its budget. trials={trials}\n")
    print(f"{'q':>7}{'m':>5}{'mult':>6} | {'SHIPPED lvl':>12}{'SHIPPED pow':>12}"
          f"| {'exactBB lvl':>12}{'exactBB pow':>12}")
    for q in (0.0, 0.01, 0.05):
        for m in (30, 50):
            for mult in (1.0, 2.0):
                r = np.random.default_rng(99)
                out = {}
                for tag, credit in (("bin", credit_binomial), ("bb", credit_betabinom)):
                    S = np.empty(trials, dtype=int)
                    chunk = 100
                    rr = np.random.default_rng(99)
                    for i in range(0, trials, chunk):
                        n = min(chunk, trials - i)
                        _, b, s, t = gen_targets(q, m, n * nt, N, mult, rr)
                        S[i:i + n] = (s + credit(t, b, rr)).reshape(n, nt).sum(axis=1)
                    out[tag] = float((fast_p(S, m, nt, N) <= alpha).mean())
                lab = "level" if mult == 1.0 else "power"
                print(f"{q:>7.3f}{m:>5}{mult:>6.1f} | {lab:>12}{out['bin']:>12.4f}"
                      f"| {lab:>12}{out['bb']:>12.4f}")


# ======================================================================================
@part("E")
def part_e():
    """flip_test_conditional: exactness / level."""
    print("=" * 86)
    print("PART E — flip_test_conditional, stratified hypergeometric")
    print("=" * 86)

    # E1: hand-check one 2x2 against scipy's Fisher exact (one-sided greater)
    from scipy.stats import fisher_exact
    for (a, na, k, m) in ((7, 20, 3, 30), (0, 10, 5, 40), (12, 50, 1, 10)):
        r = flip_test_conditional([a], [na], [k], [m])
        _, pf = fisher_exact([[a, na - a], [k, m - k]], alternative="greater")
        print(f"[E1] a={a} na={na} k={k} m={m}: flip_test p={r['p_value']:.6f}  "
              f"fisher greater p={pf:.6f}  exp={r['expected']:.4f}  "
              f"hyp mean={na*(a+k)/(na+m):.4f}")

    # E2: level by simulation, H0 = common crossing rate pi per target
    print("\n[E2] measured H0 level (alpha=0.05), attack n=181/target, benign m/target")
    rng = np.random.default_rng(4)
    trials = 4000
    print(f"     {'pi':>7}{'m':>5}{'targets':>9} | {'level':>8}{'mean p':>9}")
    for pi_lo, pi_hi in ((0.02, 0.02), (0.01, 0.20), (0.001, 0.005)):
        for m in (30, 80):
            for nt in (20, 80):
                rej = 0
                psum = 0.0
                for _ in range(trials):
                    pis = rng.uniform(pi_lo, pi_hi, nt)
                    ac = rng.binomial(181, pis)
                    bc = rng.binomial(m, pis)
                    res = flip_test_conditional(ac, [181] * nt, bc, [m] * nt)
                    psum += res["p_value"]
                    rej += res["p_value"] <= 0.05
                lab = f"{pi_lo}-{pi_hi}"
                print(f"     {lab:>7}{m:>5}{nt:>9} | {rej/trials:>8.4f}{psum/trials:>9.4f}")

    # E3: power sanity — the attack really does cross more often
    print("\n[E3] power sanity (attack rate = 2x benign rate)")
    rng = np.random.default_rng(5)
    for m, nt, pi in ((30, 20, 0.02), (30, 80, 0.02), (80, 80, 0.01)):
        rej = 0
        for _ in range(2000):
            pis = np.full(nt, pi)
            ac = rng.binomial(181, np.minimum(1, 2 * pis))
            bc = rng.binomial(m, pis)
            rej += flip_test_conditional(ac, [181] * nt, bc, [m] * nt)["p_value"] <= 0.05
        print(f"     m={m} targets={nt} pi={pi}: power {rej/2000:.3f}")


# ======================================================================================
@part("F")
def part_f():
    """Edge cases across the smaller helpers."""
    print("=" * 86)
    print("PART F — edge cases")
    print("=" * 86)

    def probe(label, fn):
        try:
            print(f"  {label:<62} -> {fn()!r}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  {label:<62} -> {type(e).__name__}: {e}")

    print("\nanalytic_max_percentile")
    for m in (0, -3, 1, 181, 10**9):
        probe(f"analytic_max_percentile({m})", lambda m=m: analytic_max_percentile(m))
    # brute-force the identity
    rng = np.random.default_rng(0)
    for m in (1, 5, 181):
        x = rng.random((200_000, m + 1))
        emp = (x[:, 0] < x[:, 1:].max(axis=1)).mean()
        print(f"  m={m:<4} P(B < max of m) empirical {emp:.5f}  formula "
              f"{analytic_max_percentile(m):.5f}")

    print("\nexpected_max_at_budget — exact vs brute-force enumeration")
    from itertools import combinations
    rng = np.random.default_rng(1)
    for M in (5, 8):
        v = list(np.round(rng.random(M) * 3, 4))
        for b in range(1, M + 1):
            brute = np.mean([max(c) for c in combinations(v, b)])
            got = expected_max_at_budget(v, b)
            flag = "OK " if abs(brute - got) < 1e-9 else "MISMATCH"
            print(f"  M={M} b={b}: exact {got:.6f}  brute {brute:.6f}  {flag}")
    probe("expected_max_at_budget([], 1)", lambda: expected_max_at_budget([], 1))
    probe("expected_max_at_budget([1,2,3], 0)", lambda: expected_max_at_budget([1, 2, 3], 0))
    probe("expected_max_at_budget([1,2,3], -1)", lambda: expected_max_at_budget([1, 2, 3], -1))
    probe("expected_max_at_budget([1,2,3], 99)", lambda: expected_max_at_budget([1, 2, 3], 99))
    probe("expected_max_at_budget([5,5,5], 2) all-tied",
          lambda: expected_max_at_budget([5, 5, 5], 2))
    probe("expected_max_at_budget([7], 1) single", lambda: expected_max_at_budget([7], 1))
    probe("expected_max_at_budget([1,nan,3], 2)",
          lambda: expected_max_at_budget([1, float("nan"), 3], 2))
    print("  -- OverflowError sweep: comb(M,b) exceeds float range --")
    for M, b in ((181, 90), (500, 250), (900, 450), (1030, 515), (1100, 550), (2000, 900)):
        probe(f"expected_max_at_budget(M={M}, b={b})",
              lambda M=M, b=b: round(expected_max_at_budget(list(np.random.random(M)), b), 4))
    t0 = time.time()
    expected_max_at_budget(list(np.random.random(2000)), 3)
    print(f"  timing M=2000 b=3: {time.time()-t0:.3f}s")

    print("\nbenign_equivalent_budget")
    v = list(np.linspace(0, 1, 50))
    probe("beb(0.5, 50 pts 0..1)", lambda: benign_equivalent_budget(0.5, v))
    probe("beb(0.99, v)", lambda: benign_equivalent_budget(0.99, v))
    probe("beb(1.0, v)  == max", lambda: benign_equivalent_budget(1.0, v))
    probe("beb(1.001, v) above max", lambda: benign_equivalent_budget(1.001, v))
    probe("beb(0.5, [])", lambda: benign_equivalent_budget(0.5, []))
    probe("beb(0.5, v, max_budget=3) reachable only at b>3",
          lambda: benign_equivalent_budget(0.5, v, max_budget=3))
    probe("beb(0.5, v, max_budget=0)", lambda: benign_equivalent_budget(0.5, v, max_budget=0))
    probe("beb(nan, v)", lambda: benign_equivalent_budget(float("nan"), v))
    probe("beb(-5, v) trivially reachable", lambda: benign_equivalent_budget(-5, v))
    probe("beb(0.5, [0.5]*50) all tied", lambda: benign_equivalent_budget(0.5, [0.5] * 50))

    print("\nceiling_saturation")
    probe("ceiling_saturation([])", lambda: ceiling_saturation([]))
    probe("ceiling_saturation([2.3026]*3, 10)", lambda: ceiling_saturation([2.3026] * 3, 10))
    probe("ceiling_saturation([0.0, 1.0], n_samples=1)",
          lambda: ceiling_saturation([0.0, 1.0], 1))
    probe("ceiling_saturation([0.0, 1.0], n_samples=0)",
          lambda: ceiling_saturation([0.0, 1.0], 0))
    probe("ceiling_saturation([5.0], n_samples=10) ABOVE ceiling",
          lambda: ceiling_saturation([5.0], 10))
    probe("ceiling_saturation([nan], 10)", lambda: ceiling_saturation([float("nan")], 10))

    print("\npaired_max_net")
    probe("paired_max_net([], [])", lambda: paired_max_net([], []))
    probe("paired_max_net([1.0], [[]]) all-empty benign",
          lambda: paired_max_net([1.0], [[]]))
    probe("paired_max_net([1.0], [[0.5]]) single target",
          lambda: paired_max_net([1.0], [[0.5]], n_boot=50))
    probe("paired_max_net len mismatch (3 attack, 1 benign)",
          lambda: paired_max_net([1.0, 2.0, 3.0], [[0.5]], n_boot=50))
    probe("paired_max_net all tied", lambda: paired_max_net([1.0] * 5, [[1.0]] * 5, n_boot=50))

    print("\nexceedance_counts_randomized")
    CAP = float(np.log(10))
    probe("m=0 (empty benign list)",
          lambda: exceedance_counts_randomized([CAP], [[]], [5]))
    probe("b=0 -> clamped", lambda: exceedance_counts_randomized([CAP], [[CAP] * 4], [0]))
    probe("b=-7 -> clamped", lambda: exceedance_counts_randomized([CAP], [[CAP] * 4], [-7]))
    probe("b=10**6 (>> candidate count) NOT clamped above",
          lambda: exceedance_counts_randomized([CAP], [[CAP] * 40], [10**6]))
    probe("len(tie_multiplicity) < len(attack) -> silent truncation",
          lambda: exceedance_counts_randomized([CAP] * 3, [[CAP]] * 3, [5]))
    probe("len(benign_lists) < len(attack) -> silent truncation",
          lambda: exceedance_counts_randomized([CAP] * 3, [[CAP]], [5] * 3))
    # isclose double-count
    a = 2.302585092994046
    just_above = a * (1 + 4e-6)          # inside np.isclose default rtol=1e-5 AND > a
    got = exceedance_counts_randomized([a], [[just_above] * 20], [1], seed=0)
    print(f"  isclose double-count: 20 benign at a*(1+4e-6), a={a}")
    print(f"    strict={(np.asarray([just_above]*20) > a).sum()}  "
          f"isclose-tied={np.isclose([just_above]*20, a).sum()}  "
          f"returned k={got[0][0]} of m={got[0][1]}  -> k>m possible: {got[0][0] > got[0][1]}")
    ks = [exceedance_counts_randomized([a], [[just_above] * 20], [1], seed=s)[0][0]
          for s in range(200)]
    print(f"    over 200 seeds: k ranges [{min(ks)},{max(ks)}], mean {np.mean(ks):.2f}, "
          f"P(k>m)={np.mean([k > 20 for k in ks]):.2f}")
    r = exceedance_test([(max(ks), 20)], 181)
    print(f"    exceedance_test with k=21 > m=20: p={r['p_value']}")

    print("\nexceedance_counts (non-randomised)")
    probe("empty benign skipped", lambda: exceedance_counts([1.0], [[]]))
    probe("bad ties policy", lambda: exceedance_counts([1.0], [[1.0]], ties="random"))
    probe("nan attack max", lambda: exceedance_counts([float("nan")], [[1.0, 2.0]]))

    print("\nexceedance_test")
    probe("empty counts", lambda: exceedance_test([], 181))
    probe("all m=0", lambda: exceedance_test([(0, 0), (0, 0)], 181))
    probe("k > m (impossible count)", lambda: exceedance_test([(21, 20)], 181))
    probe("N=0", lambda: exceedance_test([(0, 20)], 0))
    probe("N=-5", lambda: exceedance_test([(0, 20)], -5))
    probe("k=0 -> n_eff", lambda: exceedance_test([(0, 30)] * 10, 181)["n_eff"])

    print("\nflip_test_conditional")
    probe("empty", lambda: flip_test_conditional([], [], [], []))
    probe("all na=0", lambda: flip_test_conditional([0], [0], [1], [10]))
    probe("a > na (impossible)", lambda: flip_test_conditional([25], [20], [0], [30]))
    probe("degenerate: no crossings anywhere",
          lambda: flip_test_conditional([0, 0], [181, 181], [0, 0], [30, 30]))
    probe("degenerate: everything crosses",
          lambda: flip_test_conditional([181, 181], [181, 181], [30, 30], [30, 30]))
    probe("len mismatch -> silent zip truncation",
          lambda: flip_test_conditional([1, 2, 3], [181], [0], [30]))


# ======================================================================================
@part("G")
def part_g():
    """Reproduce the two published power/level claims."""
    print("=" * 86)
    print("PART G — reproduce results/power_randomized.md and results/tie_rule_showdown.md")
    print("=" * 86)

    # G1: tie_rule_showdown — atom model, MC null (as the published script does)
    print("\n[G1] tie_rule_showdown model: atom mass q, MC-calibrated null (same rule),")
    print("     80 targets, A=181.  Published: q=0.05 m=30 randomized level 0.093 pow2x 0.71")
    N, nt = 181, NTARGETS

    def sim_S(q, m, mult, trials, rng, credit):
        S = np.empty(trials, dtype=int)
        chunk = 200
        for i in range(0, trials, chunk):
            n = min(chunk, trials - i)
            _, b, s, t = gen_targets(q, m, n * nt, N, mult, rng)
            S[i:i + n] = (s + credit(t, b, rng)).reshape(n, nt).sum(axis=1)
        return S

    print(f"\n     {'q':>7}{'m':>5} | {'E[S]|H0':>9}{'crit':>6}{'MC level':>10}"
          f"{'MC pow2x':>10}{'MC pow5x':>10} | {'analytic-null level':>20}")
    for q, m in ((0.0, 30), (0.01, 30), (0.05, 30), (0.05, 60)):
        r = np.random.default_rng(7)
        null = sim_S(q, m, 1.0, 20_000, r, credit_binomial)
        crit = np.quantile(null, 0.05)
        obs2 = sim_S(q, m, 2.0, 4000, np.random.default_rng(8), credit_binomial)
        obs5 = sim_S(q, m, 5.0, 4000, np.random.default_rng(9), credit_binomial)
        lvl = sim_S(q, m, 1.0, 4000, np.random.default_rng(10), credit_binomial)
        an = float((fast_p(lvl, m, nt, N) <= 0.05).mean())
        print(f"     {q:>7.3f}{m:>5} | {null.mean():>9.2f}{crit:>6.0f}"
              f"{(lvl<=crit).mean():>10.3f}{(obs2<=crit).mean():>10.2f}"
              f"{(obs5<=crit).mean():>10.2f} | {an:>20.3f}")

    # G2: power_randomized — empirical headroom, exponential moves censored at headroom
    print("\n[G2] power_randomized model: empirical n=80 headroom, exponential(scale) moves")
    print("     censored at the per-target headroom.  Published: m=50 level 0.068 pow2x 0.84")
    hr = load_headroom()
    if hr is None:
        print("     !! empirical headroom file not found; using the repo's FA n=80 jsonl")
        return
    print(f"     headroom: n={len(hr)} mean {hr.mean():.3f} zero-headroom "
          f"{int((hr <= 1e-9).sum())} ({(hr<=1e-9).mean():.0%})")
    scale = calibrate_scale(hr)
    print(f"     calibrated per-draw scale {scale} (target: 49% attack saturation)\n")
    print(f"     {'m':>5}{'E[S]|H0':>10}{'MC level':>10}{'pow2x':>8}{'pow3x':>8}{'pow5x':>8}"
          f" | {'analytic-null level':>20}{'analytic pow2x':>16}")
    for m in (20, 30, 50, 80):
        e0, lvl, p2, p3, p5, anl, anp = headroom_power(hr, scale, m)
        print(f"     {m:>5}{e0:>10.2f}{lvl:>10.3f}{p2:>8.2f}{p3:>8.2f}{p5:>8.2f}"
              f" | {anl:>20.3f}{anp:>16.2f}")


def load_headroom():
    import json
    CAP10 = float(np.log(10))
    cands = [
        Path(r"C:\Users\Abhi\AppData\Local\Temp\claude\I--GITHUBPROJECTS-SE-Research"
             r"\85d40e73-48d6-4927-b8b8-9fe3d295986d\scratchpad\fa80.jsonl"),
        Path(__file__).resolve().parent / "results" / "winners_curse_ckpt_se_false_alarm_def.jsonl",
    ]
    for p in cands:
        if p.exists():
            rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
                    if l.strip()]
            eb = [r.get("entropy_before") for r in rows]
            eb = [x for x in eb if x is not None]
            if eb:
                print(f"     headroom source: {p.name} ({len(eb)} rows)")
                return np.maximum(0.0, CAP10 - np.asarray(eb, dtype=float))
    return None


def one_target_headroom(scale, h, m, mult, rng):
    n_att = int(round(181 * mult))
    att = np.minimum(rng.exponential(scale, n_att), h)
    A = att.max()
    sat = A >= h - 1e-12
    b = max(1, int((att >= h - 1e-12).sum())) if sat else 1
    ben = np.minimum(rng.exponential(scale, m), h)
    strict = int((ben > A + 1e-12).sum())
    tied = int(np.isclose(ben, A).sum())
    credit = int(rng.binomial(tied, 1.0 / (b + 1))) if tied else 0
    return strict + credit


def calibrate_scale(hr):
    best = None
    for s in (0.04, 0.06, 0.09, 0.12, 0.16, 0.20):
        rng = np.random.default_rng(3)
        sat = np.mean([1.0 if np.minimum(rng.exponential(s, 181), h).max() >= h - 1e-12
                       else 0.0 for h in hr])
        if best is None or abs(sat - 0.49) < abs(best[1] - 0.49):
            best = (s, sat)
    return best[0]


def headroom_power(hr, scale, m, nt=80, trials=600, null_trials=4000):
    def run(mult, trials, rng):
        return np.array([[one_target_headroom(scale, h, m, mult, rng)
                          for h in hr[rng.integers(0, len(hr), nt)]]
                         for _ in range(trials)]).sum(axis=1)
    rng = np.random.default_rng(11)
    null = run(1.0, null_trials, rng)
    crit = np.quantile(null, 0.05)
    obs2 = run(2.0, trials, np.random.default_rng(12))
    obs3 = run(3.0, trials, np.random.default_rng(13))
    obs5 = run(5.0, trials, np.random.default_rng(14))
    lvl = run(1.0, trials, np.random.default_rng(15))
    anl = float((fast_p(lvl, m, nt, 181) <= 0.05).mean())
    anp = float((fast_p(obs2, m, nt, 181) <= 0.05).mean())
    return (null.mean(), (lvl <= crit).mean(), (obs2 <= crit).mean(),
            (obs3 <= crit).mean(), (obs5 <= crit).mean(), anl, anp)


# ======================================================================================
@part("H")
def part_h():
    """Structural limits, the prior-bug reproduction, and b-misspecification."""
    print("=" * 86)
    print("PART H — structural limits / regression / b sensitivity")
    print("=" * 86)
    verify_fast_path()
    N = 181

    # H1: the test cannot reject at all unless it has enough targets.
    print("\n[H1] MINIMUM attainable p-value = P(S=0) = (N/(N+m))^n_targets.")
    print("     If that exceeds alpha the test can NEVER reject, whatever the data.")
    print(f"     {'m':>5} | " + "".join(f"{'nt=' + str(t):>10}" for t in (6, 12, 20, 40, 80))
          + f" | {'min nt for a=.05':>18}")
    for m in (20, 30, 50, 80):
        cells = []
        for nt in (6, 12, 20, 40, 80):
            pmin = float(fast_p(0, m, nt, N))
            cells.append(f"{pmin:>10.4f}")
        need = int(np.ceil(np.log(0.05) / np.log(N / (N + m))))
        print(f"     {m:>5} | " + "".join(cells) + f" | {need:>18}")
    print("     (verified against the shipped exceedance_test:)")
    for m, nt in ((30, 6), (30, 20), (20, 20), (80, 9)):
        r = exceedance_test([(0, m)] * nt, N)
        print(f"       m={m:>3} nt={nt:>3}  all-zero counts -> shipped p = {r['p_value']:.4f}"
              f"  {'CANNOT REJECT' if r['p_value'] > 0.05 else 'can reject'}")

    # H2: reproduce the KNOWN prior bug (mean tie credit, rounded) as a simulator check.
    print("\n[H2] REGRESSION CHECK — reproduce the documented prior bug so the simulator is")
    print("     validated against a known answer (docstring claims 0.034 / 0.372 / 0.996).")
    nt, m, trials = 80, 30, 4000
    print(f"     {'q':>7} | {'mean-credit ROUNDED':>21}{'single draw':>13}{'mean-credit floor':>19}")
    for q in (0.0, 0.01, 0.05):
        r = np.random.default_rng(31)
        S_round = np.empty(trials, dtype=int)
        S_draw = np.empty(trials, dtype=int)
        S_floor = np.empty(trials, dtype=int)
        chunk = 200
        for i in range(0, trials, chunk):
            n = min(chunk, trials - i)
            _, b, s, t = gen_targets(q, m, n * nt, N, 1.0, r)
            frac = s + t / (b + 1.0)
            S_round[i:i + n] = np.rint(frac).astype(int).reshape(n, nt).sum(axis=1)
            S_floor[i:i + n] = np.floor(frac).astype(int).reshape(n, nt).sum(axis=1)
            S_draw[i:i + n] = (s + credit_binomial(t, b, r)).reshape(n, nt).sum(axis=1)
        print(f"     {q:>7.3f} | {float((fast_p(S_round,m,nt,N)<=.05).mean()):>21.4f}"
              f"{float((fast_p(S_draw,m,nt,N)<=.05).mean()):>13.4f}"
              f"{float((fast_p(S_floor,m,nt,N)<=.05).mean()):>19.4f}")

    # H3: what if the MEASURED b does not match the exchangeable pool of size N?
    print("\n[H3] b MISSPECIFICATION — level when the recorded b is scaled by `f`.")
    print("     f<1 = b undercounted (e.g. only gate-PASSING candidates counted);")
    print("     f>1 = b overcounted (e.g. target ran more candidates than the median N).")
    print(f"     {'q':>7}{'m':>5} | " + "".join(f"{'f=' + str(f):>9}"
                                                for f in (0.25, 0.5, 1.0, 2.0, 4.0, 10.0)))
    for q in (0.01, 0.05):
        for m in (30, 80):
            cells = []
            for f in (0.25, 0.5, 1.0, 2.0, 4.0, 10.0):
                r = np.random.default_rng(41)
                S = np.empty(3000, dtype=int)
                for i in range(0, 3000, 200):
                    n = min(200, 3000 - i)
                    _, b, s, t = gen_targets(q, m, n * nt, N, 1.0, r)
                    bf = np.maximum(1, np.rint(b * f).astype(int))
                    S[i:i + n] = (s + credit_binomial(t, bf, r)).reshape(n, nt).sum(axis=1)
                cells.append(f"{float((fast_p(S,m,nt,N)<=.05).mean()):>9.4f}")
            print(f"     {q:>7.3f}{m:>5} | " + "".join(cells))

    # H4: median-p identity, on a case where p actually varies across seeds
    print("\n[H4] median-p == p(median S) on a case where p VARIES across tie-breaks")
    CAP = float(np.log(10))
    for seed0 in (0, 1, 2):
        rg = np.random.default_rng(seed0)
        nt2, m2, bb = 30, 30, 40
        am = [CAP] * nt2
        bl = [[CAP if u < 0.55 else float(v) for u, v in
               zip(rg.random(m2), rg.random(m2) * CAP)] for _ in range(nt2)]
        tb = [bb] * nt2
        res = exceedance_test_over_seeds(am, bl, tb, N, n_seeds=101)
        S, ps = [], []
        for s in range(101):
            c = exceedance_counts_randomized(am, bl, tb, seed=s)
            S.append(sum(k for k, _ in c))
            ps.append(exceedance_test(c, N)["p_value"])
        pm = float(fast_p(int(np.median(S)), m2, nt2, N))
        print(f"     case {seed0}: median-p {res['p_median']:.6f} | p(median S) {pm:.6f} | "
              f"S med {int(np.median(S))} range [{min(S)},{max(S)}] | "
              f"p range [{min(ps):.4f},{max(ps):.4f}] | frac<=.05 {res['frac_below_05']:.2f}")

    # H5: level at the target counts the campaign actually uses
    print("\n[H5] level of the SHIPPED single-draw test vs n_targets (m=30, q=0.05)")
    print(f"     {'n_targets':>10}{'level':>9}{'min p':>9}")
    for ntx in (6, 12, 20, 40, 80, 160):
        r = np.random.default_rng(51)
        S = np.empty(6000, dtype=int)
        for i in range(0, 6000, 200):
            n = min(200, 6000 - i)
            _, b, s, t = gen_targets(0.05, 30, n * ntx, N, 1.0, r)
            S[i:i + n] = (s + credit_binomial(t, b, r)).reshape(n, ntx).sum(axis=1)
        print(f"     {ntx:>10}{float((fast_p(S,30,ntx,N)<=.05).mean()):>9.4f}"
              f"{float(fast_p(0,30,ntx,N)):>9.4f}")

    # H6: power cost of median-p vs single draw
    print("\n[H6] POWER cost of the median-p rule (H1 = attack worth 2x / 5x its budget)")
    print(f"     {'q':>7}{'m':>5} | {'single 2x':>10}{'median 2x':>10} | "
          f"{'single 5x':>10}{'median 5x':>10}")
    for q in (0.0, 0.01, 0.05):
        for m in (30, 50):
            row = []
            for mult in (2.0, 5.0):
                r = np.random.default_rng(61)
                tr = 1500
                p1 = np.empty(tr)
                pm = np.empty(tr)
                for i in range(0, tr, 30):
                    n = min(30, tr - i)
                    _, b, s, t = gen_targets(q, m, n * nt, N, mult, r)
                    cred = np.stack([credit_binomial(t, b, r) for _ in range(101)])
                    Sall = (s[None, :] + cred).reshape(101, n, nt).sum(axis=2)
                    p1[i:i + n] = fast_p(Sall[0], m, nt, N)
                    pm[i:i + n] = fast_p(np.rint(np.median(Sall, axis=0)).astype(int),
                                         m, nt, N)
                row += [float((p1 <= .05).mean()), float((pm <= .05).mean())]
            print(f"     {q:>7.3f}{m:>5} | {row[0]:>10.3f}{row[1]:>10.3f} | "
                  f"{row[2]:>10.3f}{row[3]:>10.3f}")


if __name__ == "__main__":
    for name in (sys.argv[1:] or sorted(PARTS)):
        t0 = time.time()
        PARTS[name]()
        print(f"\n[{name} done in {time.time()-t0:.1f}s]\n")
