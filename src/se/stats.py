"""Statistics for honest reporting: bootstrap CIs, operating-point effects, and
success-cutoff sensitivity. Pure functions, CPU, unit-tested.

Addresses external-review B4 (no uncertainty on any number), §6 (a detector is a
threshold, not a ranking; report operating-point effects), and §6 (the 0.25-nat
success cutoff is unmotivated -> report a sensitivity curve).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def youden_j_threshold(labels, scores):
    """Operating-point calibration for the embedding clusterer's cosine threshold
    (critic entry 15): the threshold maximizing Youden's J = TPR - FPR on a labeled
    paraphrase (1) vs non-paraphrase (0) set. Returns (threshold, auroc, j_at_threshold).
    The AUROC is the encoder's paraphrase-discrimination power — report it so a reviewer
    can judge whether the encoder is even a trustworthy equivalence oracle."""
    y = np.asarray(labels)
    s = np.asarray(scores, dtype=float)
    if not (0 < y.sum() < len(y)):
        return float("nan"), float("nan"), float("nan")
    fpr, tpr, thr = roc_curve(y, s)
    j = tpr - fpr
    # roc_curve prepends an inf threshold (fpr=tpr=0, J=0). If the encoder is at/below
    # chance, that sentinel would win argmax and freeze thr=inf -> the embedding clusterer
    # would never union (all singletons, max SE), silently corrupting the arm in exactly
    # the near-chance regime this calibration exists to DETECT. Mask non-finite thresholds
    # and report "no usable threshold" (nan) when the best Youden J is <= 0.
    j_masked = np.where(np.isfinite(thr), j, -np.inf)
    k = int(np.argmax(j_masked))
    auroc = float(roc_auc_score(y, s))
    if not np.isfinite(thr[k]) or j[k] <= 0.0:
        return float("nan"), auroc, float(j[k])          # no usable threshold
    return float(thr[k]), auroc, float(j[k])


@dataclass
class CI:
    point: float
    lo: float
    hi: float

    def __str__(self) -> str:
        return f"{self.point:.3f} [{self.lo:.3f}, {self.hi:.3f}]"


def bootstrap_ci(values, statistic_fn, *, n_boot: int = 2000, alpha: float = 0.05,
                 seed: int = 0) -> CI:
    """Percentile bootstrap CI for a statistic of a 1-D sample (resampled i.i.d.)."""
    v = np.asarray(values)
    rng = np.random.default_rng(seed)
    n = len(v)
    point = float(statistic_fn(v))
    if n == 0:
        return CI(point, float("nan"), float("nan"))
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        stats[b] = statistic_fn(v[idx])
    lo = float(np.quantile(stats, alpha / 2))
    hi = float(np.quantile(stats, 1 - alpha / 2))
    return CI(point, lo, hi)


def auroc_ci(labels, scores, *, n_boot: int = 2000, alpha: float = 0.05,
             seed: int = 0) -> CI:
    """Bootstrap CI for AUROC, resampling paired (label, score) questions.

    Bootstrap replicates that turn out single-class (all one label) are skipped;
    the CI is over the replicates that remain defined.
    """
    y = np.asarray(labels)
    s = np.asarray(scores, dtype=float)
    n = len(y)
    point = float(roc_auc_score(y, s)) if 0 < y.sum() < n else float("nan")
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yb, sb = y[idx], s[idx]
        if 0 < yb.sum() < len(yb):
            vals.append(roc_auc_score(yb, sb))
    if not vals:
        return CI(point, float("nan"), float("nan"))
    return CI(point, float(np.quantile(vals, alpha / 2)),
              float(np.quantile(vals, 1 - alpha / 2)))


def auroc_diff_ci(labels, clean_scores, attacked_scores, *,
                  n_boot: int = 3000, alpha: float = 0.05, seed: int = 0) -> dict:
    """Paired bootstrap CIs for clean AUROC, attacked AUROC, and the degradation
    (clean - attacked), resampling QUESTIONS jointly.

    Clean and attacked AUROC are measured on the SAME questions (entropy_before vs
    entropy_after of the same outcomes), and per question the two scores are
    strongly correlated (attacked == clean unless the attack moved it). A valid CI
    on the difference must therefore resample the question index ONCE per replicate
    and recompute both AUROCs on that shared resample; taking two independent
    auroc_ci's and subtracting would overstate the interval and break the pairing.
    Positive degradation = the attack made the detector worse. Returns a dict with
    CI objects under keys 'clean', 'attacked', 'degradation'."""
    y = np.asarray(labels)
    c = np.asarray(clean_scores, dtype=float)
    a = np.asarray(attacked_scores, dtype=float)
    n = len(y)

    def _auc(yy, ss):
        return float(roc_auc_score(yy, ss)) if 0 < yy.sum() < len(yy) else float("nan")

    pt_c, pt_a = _auc(y, c), _auc(y, a)
    rng = np.random.default_rng(seed)
    cs, ats, ds = [], [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yb = y[idx]
        if not (0 < yb.sum() < len(yb)):
            continue                                   # single-class replicate
        ac, aa = roc_auc_score(yb, c[idx]), roc_auc_score(yb, a[idx])
        cs.append(ac); ats.append(aa); ds.append(ac - aa)

    def _ci(pt, vals):
        if not vals:
            return CI(pt, float("nan"), float("nan"))
        return CI(pt, float(np.quantile(vals, alpha / 2)),
                  float(np.quantile(vals, 1 - alpha / 2)))

    return {"clean": _ci(pt_c, cs), "attacked": _ci(pt_a, ats),
            "degradation": _ci(pt_c - pt_a, ds)}


def rate_ci(flags, *, n_boot: int = 2000, alpha: float = 0.05, seed: int = 0) -> CI:
    """Bootstrap CI for a success/proportion (list of bools/0-1)."""
    return bootstrap_ci([1.0 if f else 0.0 for f in flags], np.mean,
                        n_boot=n_boot, alpha=alpha, seed=seed)


def analytic_max_percentile(m: int) -> float:
    """H0 expected percentile of a MAX-of-m within a reference sample drawn from the SAME
    distribution (critique_log 21, B2). By exchangeability, for one reference draw B and m
    iid candidates, P(B < max of the m) = 1 - 1/(m+1) = m/(m+1) — distribution-free.

    This is the null baseline the attack's percentile-in-benign must be read against: the
    attack move is a max over ~m=180 optimiser candidates, so even with ZERO adversarial
    signal it sits at ~m/(m+1) ~ 99.4% of the benign INDIVIDUAL-draw distribution, not 50%.
    An observed percentile below this baseline is evidence of NO targeted effect. Companion
    only — the optimiser's candidates are dependent/concentrated, not iid, so the honest
    control is the budget-matched benign-MAX (paired_max_net), not this baseline."""
    if m < 1:
        raise ValueError("m must be >= 1")
    return m / (m + 1)


def attack_move_at_budget(trajectory_best_obj, budget: int, *,
                          top_N: int = 3, candidate_size_M: int = 3):
    """The intended-direction move the attack had achieved using only its FIRST `budget`
    candidates (critique_log 21, B2 budget-matching).

    `trajectory_best_obj[t]` is the optimiser's running-best FEASIBLE objective after
    iteration t, i.e. after `1 + t*top_N*candidate_size_M` objective calls; index 0 is the
    original query's objective. Because the objective is signed so that larger is better
    for the attacker, `traj[t] - traj[0]` IS the intended-direction move.

    This is a genuine PREFIX (what a true budget-`budget` attack run achieved), not a
    random subsample of the trajectory: the first t iterations of a beam search are exactly
    the run a smaller budget would have produced, since later iterations cannot influence
    earlier ones. It therefore supports an honest like-for-like comparison against a benign
    floor drawn at the same budget, with no re-running of the attack. Returns None if the
    trajectory is empty; budgets past the end clamp to the full run."""
    traj = list(trajectory_best_obj or [])
    if not traj:
        return None
    per_iter = max(1, int(top_N) * int(candidate_size_M))
    t = (int(budget) - 1) // per_iter
    t = max(0, min(t, len(traj) - 1))
    return float(traj[t]) - float(traj[0])


def expected_max_at_budget(values, b: int) -> float:
    """EXACT expected maximum of a uniformly random size-`b` subset of `values`, i.e. what
    a benign search of budget b would have achieved on average, computed from the empirical
    sample with NO distributional assumption (critique_log 22, refinement 4).

    For sorted v_(1) <= ... <= v_(M), the max of a random b-subset equals v_(i) with
    probability C(i-1, b-1) / C(M, b) — choose the other b-1 members from the i-1 values
    below it. So E[max_b] = sum_i v_(i) * C(i-1, b-1) / C(M, b).

    This is preferable to fitting an extreme-value tail whenever b <= M: it is unbiased,
    assumption-free, and cheap. (Extrapolating ABOVE M is where EVT would be needed — and
    is exactly what we avoid by matching budgets instead.) Requires 1 <= b <= len(values).
    """
    from math import comb
    v = sorted(float(x) for x in values)
    M = len(v)
    if M == 0:
        return float("nan")
    b = int(b)
    if b < 1:
        raise ValueError("budget must be >= 1")
    if b >= M:
        return v[-1]                      # the whole sample: the observed max
    denom = comb(M, b)
    total = 0.0
    for i in range(b, M + 1):             # 1-indexed order statistic i
        total += v[i - 1] * comb(i - 1, b - 1)
    return total / denom


def benign_equivalent_budget(attack_move: float, benign_values, *, max_budget: int | None = None):
    """The smallest benign search budget b whose EXPECTED max reaches the attack's move —
    "how many random paraphrases would it take to match this attack by chance?".

    Returns an int b, or None if even the full benign sample never reaches it (report as
    '> len(benign_values)'). This is the scale-free way to read the budget curve: b* far
    ABOVE the attacker's own budget means the attack genuinely beats budget-matched benign
    search; b* far BELOW it means the "attack" is doing no better than cheap random
    rephrasing. It needs no attack trajectory, so it works on outcome records that predate
    trajectory logging."""
    v = [float(x) for x in benign_values]
    if not v:
        return None
    hi = min(len(v), max_budget or len(v))
    if max(v) < float(attack_move):
        return None                        # even the full-sample max falls short
    for b in range(1, hi + 1):             # E[max_b] is nondecreasing in b
        if expected_max_at_budget(v, b) >= float(attack_move):
            return b
    return None


def flip_test(attack_crossed, benign_crossed, benign_n, n_attack_candidates: int,
              *, n_sim: int = 20000, seed: int = 0) -> dict:
    """⚠ NOT CALIBRATED — DO NOT USE AS A CLAIM STATISTIC (measured 2026-08-04).

    Simulated H0 rejection rate at nominal 0.05: **0.81 (m=30), 0.78 (m=60), 0.48 (m=120),
    0.35 (m=181)** — anti-conservative at every benign budget, so raising m does not fix it.
    Cause: P(attack crosses) = 1-(1-pi)^N is CONCAVE in pi, so integrating it over a
    posterior for pi that is wide (pi is small and estimated from few crossings) gives
    E[f(pi)] < f(E[pi]) by Jensen — the null systematically under-predicts crossings, and
    the observed count beats it for free. A correct version needs a test that CONDITIONS on
    the observed benign crossings (permutation / conditional-exact) rather than plugging an
    estimated rate into a nonlinear transform. Left in place because the underlying idea is
    sound and endorsed — threshold crossing is genuinely immune to the log(N) ceiling — but
    the null must be rebuilt before it is used. See tests/test_flip_test.py, which asserts
    the failure so a silent "fix" cannot slip through unvalidated.

    Budget-corrected test on OPERATING-POINT CROSSINGS.

    WHY THIS EXISTS. The entropy-magnitude statistic dies under the log(N) ceiling: once a
    meaningful fraction of paraphrases can saturate, the attack's MAX is at the ceiling under
    both H0 and H1, so a max-based comparison carries no information and no tie convention
    recovers it (see results/ and the derivation in critique_log). Threshold CROSSING is
    binary — past the operating point is past it — so the ceiling cannot censor it.

    THE NULL, with the search budget priced in. Let pi_j be the probability that a single
    meaning-preserving paraphrase of target j pushes the score across the detector's
    operating point. Under H0 the attack is just the best of N exchangeable draws, so
        P(attack crosses | pi_j) = 1 - (1 - pi_j)^N,
    which is large even for small pi_j -- exactly the winner's-curse correction, in the
    binary setting. pi_j is ESTIMATED from that target's benign draws (k_j of m_j crossed)
    with a Jeffreys Beta(k+1/2, m-k+1/2) posterior, so k_j = 0 does not collapse the null to
    zero and estimation uncertainty is carried rather than ignored.

    The null distribution of the total number of targets where the attack crosses is
    obtained by Monte Carlo over that posterior (a Poisson-binomial with uncertain rates).
    Evidence FOR the attack is MORE crossings than the budget-corrected null predicts, so
    the one-sided p-value is P(S_null >= observed).

    Returns observed/expected counts, the p-value, and the per-target null rates.
    """
    a = [bool(x) for x in attack_crossed]
    k = [int(x) for x in benign_crossed]
    m = [int(x) for x in benign_n]
    if not (len(a) == len(k) == len(m)) or not a:
        return {"n_targets": 0, "observed": 0, "expected": float("nan"),
                "p_value": float("nan")}
    N = int(n_attack_candidates)
    rng = np.random.default_rng(seed)

    # Posterior draws of pi_j, then the H0 crossing probability for the attack.
    pi = np.column_stack([rng.beta(kj + 0.5, mj - kj + 0.5, n_sim)
                          for kj, mj in zip(k, m)])          # (n_sim, n_targets)
    p_cross_h0 = 1.0 - (1.0 - pi) ** N
    sim = (rng.random(p_cross_h0.shape) < p_cross_h0).sum(axis=1)

    obs = int(sum(a))
    p_val = float((sim >= obs).mean())
    return {
        "n_targets": len(a),
        "observed": obs,
        "expected": float(sim.mean()),
        "p_value": p_val,
        "mean_null_rate": float(p_cross_h0.mean()),
        "benign_crossing_rate": float(sum(k) / max(1, sum(m))),
    }


def exceedance_counts(attack_max, benign_lists, *, ties: str = "conservative"):
    """Per target, how many benign draws reach the attack's max: K_j, plus the benign
    sample size m_j — the sufficient statistic for exceedance_test.

    TIES MATTER HERE AND ARE NOT HYPOTHETICAL. Semantic entropy over N samples is bounded
    by log(N) (every sample its own cluster), and real targets DO saturate: on the first
    ablation target the attack, a null-objective beam, and plain random paraphrasing all
    landed on exactly log(10)=2.3026. The exchangeability null assumes a continuous F, under
    which ties have probability zero; with an atom at the ceiling, counting only strict
    exceedances (b > a) scores a benign draw that MATCHED the attack as a non-exceedance,
    which inflates the evidence for the attack. Policies:
      'conservative' (default) — b >= a counts. Ties count AGAINST the attack.
      'strict'                 — b > a only. Anti-conservative under atoms; for comparison.

    ⚠ BOTH POLICIES ARE WRONG, AND 'conservative' IS BADLY WRONG (verified 2026-08-02, see
    results/CORRECTIONS_2026-08-02.md). Under exchangeability the credit for a ties is itself
    random: T ~ BetaBinomial(a; 1, b) where b is the number of ATTACK candidates also at that
    value, so E[T] = a/(b+1). Since the attack's own max is one of the tied values, b >= 1
    always and the maximum defensible credit is a/2 — never a. Measured mean b on saturated
    targets is 60.4, so 'conservative' overcounts ties by ~61x. That artifact, not the
    ceiling, is what made the test degenerate: with a correct randomized rule the test is
    calibrated and powerful at N=10 (power 0.40/0.82/0.99 at m=30/50/60) and power RISES with
    m rather than falling. Do not use these policies for a claim statistic until the
    exchangeable rule is implemented (it needs the attack-side tie count recorded too).
    Report both; if they disagree, the effect is driven by ceiling saturation, not by the
    attack outperforming chance."""
    if ties not in ("conservative", "strict"):
        raise ValueError("ties must be 'conservative' or 'strict'")
    out = []
    for a, bl in zip(attack_max, benign_lists):
        if not bl:
            continue
        a = float(a)
        k = (sum(1 for b in bl if float(b) >= a) if ties == "conservative"
             else sum(1 for b in bl if float(b) > a))
        out.append((k, len(bl)))
    return out


def ceiling_saturation(values, n_samples: int = 10, *, tol: float = 1e-6) -> float:
    """Fraction of `values` (entropies, nats) sitting at the log(n_samples) ceiling — the
    maximum semantic entropy attainable when every one of the N sampled answers forms its
    own cluster. A high rate means the score is saturated and differences between an
    optimised attack and random paraphrasing are censored, not absent."""
    v = [float(x) for x in values]
    if not v:
        return float("nan")
    cap = float(np.log(n_samples))
    return sum(1 for x in v if x >= cap - tol) / len(v)


def exceedance_counts_randomized(attack_max, benign_lists, tie_multiplicity, *,
                                 seed: int = 0, n_rep: int = 200):
    """Exceedance counts with EXCHANGEABLE (randomized) tie-breaking — the only tie rule
    that stays calibrated AND powerful once the score has an atom at the log(N) ceiling
    (critique_log 26; simulation in results/tie_rule_showdown.md).

    For each target: benign draws strictly above the attack max always count. Benign draws
    EQUAL to it are tied with the `b` attack candidates that also achieve the max, and under
    exchangeability each such benign draw outranks all of them with probability 1/(b+1).

    `tie_multiplicity[j]` is that b — the number of FEASIBLE attack candidates at the
    maximum, recorded by the optimiser (`n_feasible_at_best`). It must be MEASURED, not
    estimated from benign data: b is precisely where the attack's strength shows up once
    the max value is pinned by the ceiling, so estimating it under H0 would erase the
    signal. b is clamped to >= 1 because the attack's own maximum is one of the tied values.

    Averaging over `n_rep` tie-break draws removes the dependence on a single coin flip
    (the counts become fractional; callers wanting integer counts should use the returned
    per-target means with a Monte-Carlo null rather than the exact convolution).
    Returns [(mean_k_j, m_j), ...]."""
    rng = np.random.default_rng(seed)
    out = []
    for a, bl, b in zip(attack_max, benign_lists, tie_multiplicity):
        if not bl:
            continue
        a = float(a)
        vals = np.asarray([float(x) for x in bl], dtype=float)
        strict = int((vals > a).sum())
        tied = int(np.isclose(vals, a).sum())
        b = max(1, int(b))
        if tied:
            extra = rng.binomial(tied, 1.0 / (b + 1), size=n_rep).mean()
        else:
            extra = 0.0
        out.append((strict + float(extra), len(vals)))
    return out


def exceedance_test(counts, n_attack_candidates: int) -> dict:
    """EXACT, distribution-free test that the attack beats random paraphrasing, with the
    attacker's larger search budget priced into the NULL rather than matched by brute force
    (critique_log 23).

    H0: the optimiser carries no signal, so a target's N attack candidates and its m benign
    draws are exchangeable draws from one distribution F_j. Then F_j(attack-max) ~ Beta(N,1)
    and, conditionally, the number of benign draws above it is Binomial(m, 1-p), so
        K_j ~ BetaBinomial(m; a=1, b=N),  E[K_j] = m/(N+1),
        P(attack-max beats ALL m benign) = N/(N+m).
    The budget asymmetry that biased the old percentile statistic is thus EXACTLY accounted
    for: a max-of-181 is *expected* to sit above m benign draws under H0, and the null says
    by precisely how much. FEWER exceedances than expected is evidence for the attack, so
    the one-sided p-value is P(S <= s_obs) for S = sum_j K_j.

    The null distribution of S is obtained by EXACT discrete convolution of the per-target
    beta-binomials (each has finite support 0..m_j) — no simulation, no asymptotics.

    `counts` is the [(K_j, m_j), ...] from exceedance_counts. Returns the observed and
    expected totals, the exact one-sided p-value, and the effective benign budget
    n_eff = m/Kbar - 1 ("the beam search is worth n_eff random paraphrases"), which is
    method-of-moments and upward-biased when Kbar is small — treat as indicative.

    ASSUMPTION TO CHECK, NOT ASSUME: exchangeability requires the beam's candidates to be
    drawn from the same distribution as single-step benign paraphrases under H0. Multi-hop
    beam paraphrases could drift further and be more dispersed even with a null objective —
    which is exactly what scripts/null_objective_ablation.py measures. Read that ablation
    before trusting this test."""
    from scipy.stats import betabinom
    counts = [(int(k), int(m)) for k, m in counts if m > 0]
    if not counts:
        return {"n_targets": 0, "p_value": float("nan"), "observed": 0,
                "expected": float("nan"), "n_eff": float("nan")}
    N = int(n_attack_candidates)
    obs = sum(k for k, _ in counts)
    exp = sum(m / (N + 1) for _, m in counts)

    # Exact null of S = sum_j K_j by convolving the per-target pmfs.
    dist = np.array([1.0])
    for _, m in counts:
        pmf = betabinom.pmf(np.arange(m + 1), m, 1, N)
        pmf = np.asarray(pmf, dtype=float)
        pmf = pmf / pmf.sum()
        dist = np.convolve(dist, pmf)
    p_le = float(dist[: obs + 1].sum()) if obs < len(dist) else 1.0

    m_tot = sum(m for _, m in counts)
    kbar = obs / len(counts)
    m_bar = m_tot / len(counts)
    n_eff = (m_bar / kbar - 1.0) if kbar > 0 else float("inf")
    return {
        "n_targets": len(counts),
        "observed": obs,
        "expected": float(exp),
        "p_value": min(1.0, max(0.0, p_le)),
        "n_eff": n_eff,
        "p_attack_beats_all_per_target": N / (N + m_bar),
    }


def paired_max_net(attack_max, benign_lists, *, n_boot: int = 3000, seed: int = 0) -> dict:
    """Budget-matched winner's-curse control (critique_log 21, B2). Compares each target's
    attack-max to its BENIGN-MAX (max over that target's benign draws), PAIRED per target —
    the only comparison immune to the selection-budget asymmetry that inflates
    attack-max-vs-benign-individual. Under H0 (optimiser guidance carries no signal and the
    benign budget matches the attack's), E[attack_max - benign_max] = 0.

    attack_max[i] = the attack's (max) move for target i; benign_lists[i] = that target's
    benign move list (take its max). Returns the paired net CI (bootstrap of mean
    attack_max_i - benign_max_i) and the sign-test rate (fraction of targets with
    attack_max > benign_max, CI). Reframe-(a) is supported iff the net CI is strictly > 0.
    NOTE: benign_lists must be generated at a budget comparable to the attack's (~180); a
    small K under-estimates benign_max and inflates this net (report the benign budget)."""
    pairs = [(a, max(b)) for a, b in zip(attack_max, benign_lists) if b]
    if not pairs:
        return {"n": 0, "net_ci": None, "sign_ci": None, "mean_benign_max": float("nan")}
    diffs = [a - bm for a, bm in pairs]
    wins = [a > bm for a, bm in pairs]
    return {
        "n": len(pairs),
        "net_ci": bootstrap_ci(diffs, np.mean, n_boot=n_boot, seed=seed),
        "sign_ci": rate_ci(wins, n_boot=n_boot, seed=seed),
        "mean_benign_max": float(np.mean([bm for _, bm in pairs])),
        "mean_attack_max": float(np.mean([a for a, _ in pairs])),
    }


def success_rate_over_cutoffs(intended_moves, feasible, cutoffs) -> list[tuple[float, float]]:
    """Success rate as a function of the entropy-move cutoff (§6 sensitivity).

    intended_moves[i] = signed entropy move in the ATTACK's intended direction
    (positive = helped the attacker). feasible[i] = passed the equivalence gate.
    Returns [(cutoff, success_rate)] so the 0.25 choice can be shown in context.
    """
    m = np.asarray(intended_moves, dtype=float)
    f = np.asarray(feasible, dtype=bool)
    out = []
    n = len(m)
    for c in cutoffs:
        succ = np.sum(f & (m >= c))
        out.append((float(c), succ / n if n else 0.0))
    return out


def operating_point(labels, clean_scores, *, target_fpr: float = 0.1):
    """Return the score threshold on CLEAN data achieving <= target_fpr.

    Positive class (label 1) = the hallucination case; the detector flags when
    score >= threshold. FPR is over the negatives (label 0, i.e. correct answers).
    """
    y = np.asarray(labels)
    s = np.asarray(clean_scores, dtype=float)
    neg = s[y == 0]
    if len(neg) == 0:
        return float("inf")
    # Smallest threshold whose FPR (fraction of negatives flagged) <= target.
    thr = float(np.quantile(neg, 1 - target_fpr))
    return thr


def flips_at_threshold(labels, clean_scores, attacked_scores, threshold):
    """At a fixed threshold, count operationally meaningful flips (§6).

    For hide targets (label 1): flagged -> unflagged is a successful hide.
    For false-alarm targets (label 0): unflagged -> flagged is a successful false alarm.
    Returns a dict of counts and rates.
    """
    y = np.asarray(labels)
    c = np.asarray(clean_scores, dtype=float)
    a = np.asarray(attacked_scores, dtype=float)
    clean_flag = c >= threshold
    att_flag = a >= threshold
    hide = (y == 1)
    fa = (y == 0)
    hide_flip = np.sum(hide & clean_flag & ~att_flag)      # was caught, now missed
    fa_flip = np.sum(fa & ~clean_flag & att_flag)          # was fine, now false-alarmed
    return {
        "threshold": float(threshold),
        "n_hide": int(hide.sum()),
        "hide_flagged_to_unflagged": int(hide_flip),
        "hide_flip_rate": float(hide_flip / hide.sum()) if hide.sum() else 0.0,
        "n_false_alarm": int(fa.sum()),
        "fa_unflagged_to_flagged": int(fa_flip),
        "fa_flip_rate": float(fa_flip / fa.sum()) if fa.sum() else 0.0,
    }
