"""Statistics for honest reporting: bootstrap CIs, operating-point effects, and
success-cutoff sensitivity. Pure functions, CPU, unit-tested.

Addresses external-review B4 (no uncertainty on any number), §6 (a detector is a
threshold, not a ranking; report operating-point effects), and §6 (the 0.25-nat
success cutoff is unmotivated -> report a sensitivity curve).
"""
from __future__ import annotations

import warnings
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


def _clamp_p(p) -> float:
    """Clamp a p-value to [0,1] WITHOUT laundering NaN into 0.0.

    `max(0.0, float("nan"))` returns 0.0 in Python, so the obvious clamp turns a
    degenerate/undefined computation into MAXIMUM significance. That is the silent
    false-positive class that already cost this project once (critique_log 28), so
    NaN propagates as NaN and the caller must deal with it.
    """
    p = float(p)
    if p != p:            # NaN
        return float("nan")
    return min(1.0, max(0.0, p))

def flip_test_conditional(attack_crossed, attack_n, benign_crossed, benign_n) -> dict:
    """EXACT stratified conditional test on operating-point crossings — censoring-immune
    and estimation-free. This is the correct replacement for `flip_test` below, whose null
    was biased by plugging an estimated crossing rate into a nonlinear transform.

    Per target we have a 2x2 table: {attack candidates, benign draws} x {crossed, did not}.
    Under H0 the attack's candidates and the benign draws are exchangeable, so CONDITIONAL
    ON THE MARGINS the number of attack crossings is hypergeometric:
        a_j ~ Hypergeometric(population = N_j + m_j, successes = a_j + k_j, draws = N_j).
    No rate is estimated, so there is no Jensen bias and no dependence on a posterior. The
    null for the total sum_j a_j is the exact convolution of the per-target hypergeometrics
    (each has finite support), giving a one-sided p-value with no simulation.

    This is the crossing analogue of a stratified Fisher / Cochran--Mantel--Haenszel test.
    Because a crossing is binary, the log(N) ceiling cannot censor it: past the operating
    point is past it, however far past.

    Requires the per-target count of ATTACK candidates that crossed, which needs the
    instrumented optimiser (`feasible_objs`); it is not recoverable from a run that stored
    only the selected paraphrase. Evidence for the attack is MORE attack crossings than the
    exchangeable null predicts, so the p-value is P(S >= observed)."""
    from scipy.stats import hypergeom
    # Length mismatch used to truncate SILENTLY via zip (3 attack values against 1 benign
    # list would quietly become n=1). Fail loudly instead.
    lens = {len(attack_crossed), len(attack_n), len(benign_crossed), len(benign_n)}
    if len(lens) > 1:
        raise ValueError(
            f"flip_test_conditional: arm lengths disagree {sorted(lens)}; zip would have "
            f"truncated to the shortest and silently shrunk n_targets.")
    rows = []
    for a, na, k, m in zip(attack_crossed, attack_n, benign_crossed, benign_n):
        a, na, k, m = int(a), int(na), int(k), int(m)
        # A count of crossings cannot exceed its arm size. Left unchecked, such a row makes
        # the hypergeometric support empty, the stratum is skipped while its count stays in
        # `obs`, and the p-value collapses to 0.0 -- maximum significance from impossible
        # input. That is the silent-false-positive class of critique_log 28.
        if not (0 <= a <= na) or not (0 <= k <= m):
            raise ValueError(
                f"flip_test_conditional: impossible 2x2 row (a={a}, n_attack={na}, "
                f"k={k}, n_benign={m}); crossings cannot exceed the arm size.")
        if na > 0 and m > 0:
            rows.append((a, na, k, m))
    if not rows:
        return {"n_targets": 0, "observed": 0, "expected": float("nan"),
                "p_value": float("nan")}

    obs = sum(a for a, _, _, _ in rows)
    exp = 0.0
    dist = np.array([1.0])
    for a, na, k, m in rows:
        pop, succ = na + m, a + k
        lo, hi = max(0, succ - m), min(succ, na)
        support = np.arange(lo, hi + 1)
        pmf = hypergeom.pmf(support, pop, succ, na)
        pmf = np.asarray(pmf, dtype=float)
        s = pmf.sum()
        if s <= 0:
            continue
        pmf = pmf / s
        exp += float((support * pmf).sum())
        # convolve, tracking the offset so indices stay aligned with the running total
        full = np.zeros(hi + 1)
        full[lo:hi + 1] = pmf
        dist = np.convolve(dist, full)
    p_ge = float(dist[obs:].sum()) if obs < len(dist) else 0.0
    return {
        "n_targets": len(rows),
        "observed": obs,
        "expected": exp,
        "p_value": _clamp_p(p_ge),
        "attack_crossing_rate": obs / max(1, sum(na for _, na, _, _ in rows)),
        "benign_crossing_rate": sum(k for _, _, k, _ in rows) / max(1, sum(m for _, _, _, m in rows)),
    }


def flip_test(attack_crossed, benign_crossed, benign_n, n_attack_candidates: int,
              *, n_sim: int = 20000, seed: int = 0,
              _documented_defect_opt_in: bool = False) -> dict:
    """⚠ NOT CALIBRATED — SUPERSEDED. Use `flip_test_conditional` above, which is exact,
    estimation-free, and measured at or below its nominal level on the same simulation this
    function fails. This one is retained only so its documented failure stays visible.

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

    RETIRED 2026-08-12. Calling this raises unless `_documented_defect_opt_in=True`. The
    docstring warning above was the only guard, and a docstring is easy to skip when the
    function name reads as though it works. The body is preserved, not deleted, because the
    measured failure is itself a finding worth keeping reproducible.
    """
    if not _documented_defect_opt_in:
        raise RuntimeError(
            "flip_test is RETIRED: its null is anti-conservative (H0 rejection 0.81 at m=30 "
            "through 0.35 at m=181, nominal 0.05) because P(cross)=1-(1-pi)^N is concave in "
            "pi and integrating an estimated pi over a wide posterior under-predicts "
            "crossings by Jensen. Use flip_test_conditional, which conditions on the margins, "
            "estimates no rate, and is exact. Pass _documented_defect_opt_in=True only to "
            "reproduce the documented failure (see tests/test_flip_test.py).")
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


class TieCounts(list):
    """The [(k_j, m_j), ...] list `exceedance_test` consumes, carrying its tie audit.

    A plain `list` subclass on purpose: every existing caller (and `exceedance_test` itself)
    keeps working unchanged, while `counts.tie_audit` lets the test cross-check the tie
    multiplicity it was never previously shown. See `exceedance_counts_randomized`.
    """
    __slots__ = ("tie_audit",)

    def __init__(self, rows, tie_audit: dict):
        super().__init__(rows)
        self.tie_audit = tie_audit


def _per_target_budget(n_attack_candidates, n_targets):
    """Normalise the candidate-count argument to (list or None, is_per_target)."""
    if n_attack_candidates is None:
        return None, False
    if np.isscalar(n_attack_candidates):
        return [int(n_attack_candidates)] * n_targets, False
    caps = [int(x) for x in n_attack_candidates]
    if len(caps) != n_targets:
        raise ValueError(
            f"n_attack_candidates has {len(caps)} entries but there are {n_targets} "
            f"targets; a per-target budget must line up with the targets or zip would "
            f"silently truncate.")
    return caps, True


def exceedance_counts_randomized(attack_max, benign_lists, tie_multiplicity, *,
                                 n_attack_candidates=None, on_violation: str = "auto",
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

    ⚠ b MUST ALSO BE CLAMPED FROM ABOVE — added 2026-08-13 (defect 2). b_j counts attack
    candidates at the max, so it cannot exceed N_j, that target's candidate count. Until now
    nothing enforced that and `exceedance_test` never saw b at all, so no cross-check was
    even possible. OVER-STATING b IS THE 99%-FALSE-POSITIVE DIRECTION: each tied benign draw
    earns credit 1/(b+1), so an inflated b shrinks K, shrinks S, and shrinks p = P(S <= s).
    Measured H0 rejection at nominal 0.05 (N=181, 80 targets, m=80 benign draws, 5% ceiling
    atom) with b scaled by f: f=1 -> 0.023, f=2 -> **0.851**, f=4 -> **1.000**. At a 20% atom
    f=2 gives 0.901. This is the same failure mode that already cost this project a 99.6%
    false-positive rate (critique_log 28).

    The realistic trigger is live in the repo: `scripts/null_control.py` uses ONE
    `attack_budget = median(n_objective_calls)` as N for every target while b_j is that
    target's own `n_feasible_at_best`. b and N are then sourced from different places, and
    any target that ran longer than the median can report b_j > N. (The N mis-match itself
    is conservative — 1/(N+1) is convex, so a heterogeneous truth produces MORE benign
    exceedances than a null at the median, measured level 0.000-0.028 vs nominal 0.05 —
    but the b it lets through is not.) Pass `n_attack_candidates` to make the check real:
      * a per-target sequence — authoritative, so b_j > N_j is an impossible input and
        RAISES (this mirrors `flip_test_conditional`'s impossible-2x2 guard);
      * a scalar (e.g. the null's own N) — this may be a summary rather than the true count,
        so b_j > N is CLAMPED to N, which is the conservative direction (more tie credit ->
        larger K -> larger p), warned via `warnings.warn`, and recorded in the audit;
      * omitted — no clamp is possible and the audit says `checked=False`. `exceedance_test`
        will then compare `max_b_used` against its own N and flag the result.
    `on_violation` overrides the choice: 'auto' (default, as above), 'clamp', or 'raise'.
    A hard raise is deliberately NOT the default for the scalar case: a multi-day chain
    should degrade to a conservative p-value with a loud warning, not crash at its reporting
    step. It is never a SILENT degradation — the audit rides on the returned object and
    surfaces in `exceedance_test`'s dict.

    ⚠ THE CLAMP IS AN INTEGRITY GUARD, NOT A CALIBRATION GUARANTEE — measure it before you
    trust it. b <= N is the only bound derivable from inside the statistic, and it is far
    looser than the accuracy the level needs. On saturated targets b ~ Binomial(N, q), so at
    a 5% ceiling atom the honest b is ~9 against N=181: an inflation of 2x (level 0.87) or
    even 8x (level 1.00) never reaches the clamp. Measured H0 level, 600 trials, m=80,
    80 targets, unclamped vs clamped:
        q=0.05  f=2  0.870 -> 0.870   (clamp fires on 0% of targets)
        q=0.05  f=4  1.000 -> 1.000   (0%)
        q=0.20  f=8  1.000 -> 1.000   (99.6% of targets clamped)
        q=0.50  f=4  1.000 -> 0.918   (100% clamped)
    Clamping to N leaves the level at ~0.92 because b=N drives the tie credit 1/(b+1) to
    ~0, which is the STRICT tie rule — already disqualified at H0 level 0.995 under a
    ceiling. What the clamp buys is: impossible input is refused or bounded, and clamping can
    only ever RAISE the p-value. What restores the level is b being CORRECT. Use
    `exceedance_test_over_tie_scales` to show whether the verdict survives a plausible error
    in b before quoting any p-value from this path.

    ⚠ USE A SINGLE DRAW, NOT AN AVERAGE. Returns INTEGER counts from ONE tie-break
    realisation, because the exact convolution null is the distribution of a single
    realisation. Averaging the tie credit over many draws (an earlier version of this
    function did) removes the tie-break variance that the null still assumes is present, so
    the averaged statistic is systematically less extreme than the null expects and the test
    becomes wildly anti-conservative: measured H0 level 0.034 / 0.372 / 0.996 at ceiling-atom
    mass q = 0 / 0.01 / 0.05, against a single draw's 0.041 / 0.037 / 0.024
    (`scripts/tie_level_probe.py`). Averaging a statistic whose null was derived for one
    realisation is the bug; do not reintroduce it.

    Because the result depends on one random tie-break, report the test across several
    `seed` values (see `exceedance_test_over_seeds`) rather than quoting a single p-value.
    Returns a `TieCounts` (a list of integer (k_j, m_j)) carrying `.tie_audit`."""
    if on_violation not in ("auto", "clamp", "raise"):
        raise ValueError("on_violation must be 'auto', 'clamp' or 'raise'")
    b_req_all = [int(x) for x in tie_multiplicity]
    caps, per_target = _per_target_budget(n_attack_candidates, len(b_req_all))
    do_raise = on_violation == "raise" or (on_violation == "auto" and per_target)

    rng = np.random.default_rng(seed)
    out = []
    n_high = n_low = 0
    max_req = max_used = 0
    worst = 1.0
    examples: list[tuple[int, int, int]] = []
    for j, (a, bl, b_req) in enumerate(zip(attack_max, benign_lists, b_req_all)):
        b = max(1, b_req)
        n_low += b_req < 1
        cap = caps[j] if caps is not None else None
        if cap is not None:
            cap = max(1, cap)
            if b > cap:
                n_high += 1
                worst = max(worst, b / cap)
                if len(examples) < 5:
                    examples.append((j, b_req, cap))
                if do_raise:
                    raise ValueError(
                        f"exceedance_counts_randomized: target {j} reports tie multiplicity "
                        f"b={b_req} but only N={cap} attack candidates. b counts candidates "
                        f"AT the maximum, so b <= N by construction; b > N shrinks the tie "
                        f"credit 1/(b+1) and drives the test anti-conservative (H0 level "
                        f"0.85 at 2x, 1.00 at 4x). Fix the candidate count or pass a scalar "
                        f"n_attack_candidates to clamp conservatively instead.")
                b = cap
        max_req = max(max_req, b_req)
        max_used = max(max_used, b)
        if not bl:
            continue
        a = float(a)
        vals = np.asarray([float(x) for x in bl], dtype=float)
        strict = int((vals > a).sum())
        tied = int(np.isclose(vals, a).sum())
        extra = int(rng.binomial(tied, 1.0 / (b + 1))) if tied else 0
        out.append((strict + extra, len(vals)))

    audit = {
        "checked": caps is not None,
        "budget_is_per_target": per_target,
        "n_targets": len(b_req_all),
        "n_clamped_high": n_high,
        "n_clamped_low": n_low,
        "max_b_requested": max_req,
        "max_b_used": max_used,
        "worst_b_over_n": float(worst),
        "examples_b_gt_n": examples,
    }
    if n_high:
        warnings.warn(
            f"exceedance_counts_randomized: {n_high}/{len(b_req_all)} targets reported a tie "
            f"multiplicity above their candidate count (worst {worst:.1f}x). b was CLAMPED "
            f"to N, which is conservative (more tie credit -> larger p). An unclamped b is "
            f"the anti-conservative direction that produced this project's 99.6% "
            f"false-positive rate; examples (target, b, N): {examples}",
            UserWarning, stacklevel=2)
    return TieCounts(out, audit)


def exceedance_test_over_seeds(attack_max, benign_lists, tie_multiplicity,
                               n_attack_candidates: int, *, n_seeds: int = 101):
    """Run the randomised-tie exceedance test across `n_seeds` tie-break realisations and
    summarise the resulting p-values. A randomised test's verdict should not hinge on one
    coin flip, so we report the median p-value together with its spread; if the range
    straddles the decision threshold, the data do not settle the question and that fact is
    the result. Each individual run uses a single draw, so each is correctly calibrated.

    This function KNOWS the null's N, so it hands it to `exceedance_counts_randomized` and
    the b <= N clamp is live here without the caller doing anything (defect 2, 2026-08-13).
    `n_tie_clamped` in the returned dict says how many targets it caught."""
    ps = []
    audit = None
    for s in range(int(n_seeds)):
        counts = exceedance_counts_randomized(attack_max, benign_lists, tie_multiplicity,
                                              n_attack_candidates=n_attack_candidates,
                                              seed=s)
        audit = counts.tie_audit
        r = exceedance_test(counts, n_attack_candidates)
        if r.get("n_targets"):
            ps.append(r["p_value"])
    if not ps:
        return {"n_seeds": 0, "p_median": float("nan"), "n_tie_clamped": 0,
                "tie_audit": audit}
    ps = np.sort(np.asarray(ps, dtype=float))
    return {
        "n_seeds": len(ps),
        "p_median": float(np.median(ps)),
        "p_lo": float(ps[0]),
        "p_hi": float(ps[-1]),
        "frac_below_05": float((ps <= 0.05).mean()),
        "n_tie_clamped": int((audit or {}).get("n_clamped_high", 0)),
        "tie_audit": audit,
    }


def exceedance_test_over_tie_scales(attack_max, benign_lists, tie_multiplicity,
                                    n_attack_candidates, *, scales=(0.25, 0.5, 1.0, 2.0),
                                    n_seeds: int = 25, alpha: float = 0.05) -> dict:
    """How much of the verdict is the TIE MULTIPLICITY rather than the data? (defect 2)

    The b <= N clamp bounds impossible input but cannot detect a b that is merely wrong: at a
    5% ceiling atom the honest b is ~9 against N=181, so a 2x over-statement — enough to take
    the H0 level from 0.023 to 0.870 — sits nowhere near the clamp. Since b is a MEASURED
    quantity from the instrumented optimiser, the reader's question is not "is b <= N" but
    "would this p-value survive a plausible error in b". This answers that directly by
    re-running the test with b scaled, and it is one-sided in a known direction: scaling b UP
    shrinks the tie credit 1/(b+1) and so shrinks p. A verdict that only holds at scale 1.0
    is a verdict about the optimiser's bookkeeping, not about the attack.

    Companion to `exceedance_test_over_seeds` (which varies the tie-break coin, not b).
    Returns the per-scale median p-value and `survives_half_b` — whether the test still
    rejects when b is HALVED, the honest robustness bar."""
    rows = []
    for s in scales:
        scaled = [max(1, int(round(float(b) * float(s)))) for b in tie_multiplicity]
        r = exceedance_test_over_seeds(attack_max, benign_lists, scaled,
                                       n_attack_candidates, n_seeds=n_seeds)
        rows.append({"scale": float(s), "p_median": r.get("p_median", float("nan")),
                     "p_lo": r.get("p_lo", float("nan")),
                     "p_hi": r.get("p_hi", float("nan")),
                     "n_tie_clamped": r.get("n_tie_clamped", 0)})
    at = {r["scale"]: r["p_median"] for r in rows}
    half, one = at.get(0.5, float("nan")), at.get(1.0, float("nan"))
    return {
        "scales": rows,
        "p_at_measured_b": one,
        "p_at_half_b": half,
        "survives_half_b": bool(half == half and half <= alpha),
        "verdict_hinges_on_b": bool(one == one and half == half
                                    and one <= alpha < half),
    }


def _tie_audit_report(counts, N: int) -> tuple[dict, list[str]]:
    """Cross-validate the tie multiplicity that produced `counts` against the null's N.

    `exceedance_test` used to be blind to b, which is why an inflated b could not be caught
    anywhere (defect 2, 2026-08-13). `exceedance_counts_randomized` now attaches a
    `tie_audit`; here we check it against the N this test is actually using — which is the
    check that matters, because `scripts/null_control.py` builds b from each target's own
    record but uses a single MEDIAN budget as N, so a long-running target can report b > N.

    We cannot recompute the counts at this point, so an uncaught violation is reported, not
    repaired: `tie_multiplicity_valid=False` plus a warning. Returns (fields, warnings).
    """
    audit = getattr(counts, "tie_audit", None)
    msgs: list[str] = []
    if audit is None:
        return {"tie_multiplicity_checked": False, "tie_multiplicity_valid": None,
                "tie_audit": None}, msgs
    valid = True
    if audit["n_clamped_high"]:
        msgs.append(
            f"{audit['n_clamped_high']}/{audit['n_targets']} targets had b > N and were "
            f"CLAMPED to N (conservative; worst {audit['worst_b_over_n']:.1f}x).")
    if audit["max_b_used"] > N:
        valid = False
        msgs.append(
            f"TIE MULTIPLICITY EXCEEDS THIS TEST'S N: max b = {audit['max_b_used']} but the "
            f"null uses N = {N}. b counts attack candidates at the maximum, so b <= N by "
            f"construction; b > N shrinks the tie credit 1/(b+1) and makes this p-value "
            f"ANTI-CONSERVATIVE (measured H0 level 0.85 at 2x, 1.00 at 4x). The counts "
            f"cannot be repaired here — pass n_attack_candidates={N} to "
            f"exceedance_counts_randomized so b is clamped before the counts are drawn.")
        warnings.warn("exceedance_test: " + msgs[-1], UserWarning, stacklevel=3)
    return {"tie_multiplicity_checked": bool(audit["checked"]),
            "tie_multiplicity_valid": valid,
            "tie_audit": audit}, msgs


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
    before trusting this test.

    TIE CROSS-VALIDATION (added 2026-08-13, defect 2). When `counts` came from
    `exceedance_counts_randomized` it carries a `tie_audit`, and this function checks the tie
    multiplicity against the N it is using here. The returned dict gains
    `tie_multiplicity_checked`, `tie_multiplicity_valid`, `tie_audit` and a `warnings` list.
    `tie_multiplicity_valid is False` means max b > N, i.e. this p-value is
    ANTI-CONSERVATIVE and must not be quoted; `None` means the counts carried no audit
    (a hand-built list) so nothing could be checked."""
    from scipy.stats import betabinom
    N = int(n_attack_candidates)
    tie_fields, tie_msgs = _tie_audit_report(counts, N)
    counts = [(int(k), int(m)) for k, m in counts if m > 0]
    if not counts:
        return {"n_targets": 0, "p_value": float("nan"), "observed": 0,
                "expected": float("nan"), "n_eff": float("nan"),
                "warnings": tie_msgs, **tie_fields}
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
        "p_value": _clamp_p(p_le),
        "n_eff": n_eff,
        "p_attack_beats_all_per_target": N / (N + m_bar),
        "warnings": tie_msgs,
        **tie_fields,
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


@dataclass(frozen=True)
class OperatingPoint:
    """A threshold together with the FPR it ACTUALLY achieves. Never quote the target.

    `float(op)` gives the threshold, so `float(operating_point(...))` still works, but the
    object is deliberately NOT a float: passing it where a number is expected raises rather
    than silently reinstating a threshold whose realised FPR nobody checked. `str(op)` is the
    honest one-line label.
    """
    threshold: float
    achieved_fpr: float
    target_fpr: float
    mode: str
    n_negatives: int
    n_distinct_negatives: int
    honours_contract: bool
    flags_nothing: bool
    # The nearest attainable FIRING operating point, whatever mode was asked for. This is
    # what makes a degenerate 'at_most' row readable: "no operating point at 5%; the
    # nearest one the score can actually produce is 11.2%".
    closest_attainable_fpr: float
    closest_attainable_threshold: float

    def __float__(self) -> float:
        return float(self.threshold)

    def __str__(self) -> str:
        if self.n_negatives == 0:
            return f"thr=inf (no negatives; FPR undefined, target {self.target_fpr:.1%})"
        tail = "" if self.honours_contract else "  ** EXCEEDS TARGET **"
        deg = "  (flags nothing)" if self.flags_nothing else ""
        return (f"thr={self.threshold:.4f}, achieved FPR {self.achieved_fpr:.1%} "
                f"(target {self.target_fpr:.1%}, rule '{self.mode}'){deg}{tail}")


def attainable_fprs(negatives):
    """Every FPR the detector can actually realise on `negatives`, with its threshold.

    The detector flags at `score >= thr`, so FPR only changes at an observed negative
    value: the attainable set is {(v, mean(neg >= v)) : v distinct} plus the sentinel
    (+inf, 0.0) = "never fire". Ascending threshold, so FPR is non-increasing.

    On a discrete/atomic score this grid is COARSE — on the fair pool semantic entropy at
    N=10 takes ~28 values and the grid steps 26.5% -> 21.5% -> 9.5%. There is generally no
    threshold at a nominal 10%, and pretending otherwise is defect (1) of 2026-08-13.
    Values are deduplicated EXACTLY (no tolerance): the achieved FPR is computed with the
    same `>=` comparison the detector uses, so float-noise duplicates cannot make the
    reported FPR disagree with the realised one.
    """
    v = np.sort(np.asarray(negatives, dtype=float))
    n = len(v)
    if n == 0:
        return np.array([np.inf]), np.array([float("nan")])
    vals = np.unique(v)
    fprs = (n - np.searchsorted(v, vals, side="left")) / n
    return np.append(vals, np.inf), np.append(fprs, 0.0)


def operating_point(labels, clean_scores, *, target_fpr: float = 0.1,
                    mode: str = "at_most") -> OperatingPoint:
    """Threshold on CLEAN data, returned WITH the FPR it actually achieves.

    Positive class (label 1) = the hallucination case; the detector flags when
    score >= threshold. FPR is over the negatives (label 0, i.e. correct answers).

    ⚠ FIXED 2026-08-13 — this function used to return `np.quantile(neg, 1 - target_fpr)`
    and promise "<= target_fpr". It did not deliver that, and the failure is not a corner
    case. Semantic entropy has a large ATOM at the log(N) ceiling (10% of clean correct
    answers, up to 52% of attacked ones); when the atom straddles the target quantile the
    quantile IS the ceiling and `>=` flags every tied item. Measured over 2000 trials at
    target 0.10, n=200: achieved FPR 0.100 with no atom, **0.200** at a 20% atom, **0.299**
    at 30%, **0.600** at 60% — and it also missed on CONTINUOUS scores whenever the
    interpolation index (1-t)(n-1) is integral (n=61 -> 0.1148, n=41 -> 0.1220, n=5 -> 0.2).
    Independently, a tau pre-registered as "10% FPR on the fair pool" realised **21.5%**.

    Two things changed:
      1. the threshold is chosen from the ATTAINABLE grid (see `attainable_fprs`), not by
         interpolating between order statistics — an interpolated threshold sits between two
         observed values and its realised FPR is whatever the `>=` rule then produces;
      2. the ACHIEVED FPR is returned alongside it, so no caller can quote the nominal
         number. `flips_at_threshold` and `se.attacks.report.matrix_operating_point` report
         `achieved_fpr`, and the two never disagree because both recompute it from the same
         negatives with the same comparison.

    Modes:
      'at_most' (default) — smallest threshold whose achieved FPR is <= target_fpr. This is
          the documented contract, and it is honoured EXACTLY, including the degenerate case:
          if the top atom's mass alone exceeds the target (30% of negatives at the ceiling,
          target 10%) then no firing threshold qualifies and the honest answer is +inf,
          achieved FPR 0, `flags_nothing=True`. A detector that cannot operate at the
          requested FPR should say so, not fire at 3x the rate it advertised.
      'closest' — the attainable FIRING threshold whose achieved FPR is nearest the target
          (ties broken toward the LOWER FPR). Never degenerates, so it always yields a usable
          operating point, but it can come in ABOVE the target — `honours_contract` says
          whether it did, and `achieved_fpr` says by how much. This is the right mode when
          the job is to measure detector behaviour AT a realistic operating point (see
          `se.attacks.report.matrix_operating_point`): it keeps the threshold the quantile
          rule was reaching for while replacing the nominal label with the true rate.
      'nominal_quantile' — the historical quantile rule, retained ONLY so a pre-registered
          threshold (docs/critique_log.md entry 32) stays reproducible. It does not honour
          the contract and `honours_contract` will say so. Do not use it for new work.

    Returns an `OperatingPoint`. `float(op)` is the threshold.
    """
    if mode not in ("at_most", "closest", "nominal_quantile"):
        raise ValueError(f"mode must be 'at_most', 'closest' or 'nominal_quantile', "
                         f"got {mode!r}")
    t = float(target_fpr)
    if not (0.0 <= t <= 1.0) or t != t:
        raise ValueError(f"target_fpr must be in [0, 1], got {target_fpr!r}")

    y = np.asarray(labels)
    s = np.asarray(clean_scores, dtype=float)
    neg = s[y == 0]
    n = len(neg)
    if n == 0:
        # No negatives: the FPR is undefined, not zero. Flag nothing and say so.
        return OperatingPoint(float("inf"), float("nan"), t, mode, 0, 0,
                              False, True, float("nan"), float("inf"))

    vals, fprs = attainable_fprs(neg)
    # Nearest attainable FIRING FPR to the target, ties toward the conservative (lower) one.
    # The trailing (inf, 0) sentinel is excluded here: "never fire" is always available and
    # would win every low target, which is the 'at_most' answer, not the nearest one.
    j = int(min(range(len(vals) - 1), key=lambda i: (abs(fprs[i] - t), fprs[i])))
    closest_thr, closest_fpr = float(vals[j]), float(fprs[j])

    if mode == "nominal_quantile":
        thr = float(np.quantile(neg, 1.0 - t))
    elif mode == "closest":
        thr = closest_thr
    else:                                            # 'at_most'
        ok = np.flatnonzero(fprs <= t + 1e-12)       # fprs is non-increasing
        thr = float(vals[ok[0]])                     # the sentinel guarantees ok is non-empty

    achieved = float(np.mean(neg >= thr))            # the number that is true, by construction
    return OperatingPoint(
        threshold=thr,
        achieved_fpr=achieved,
        target_fpr=t,
        mode=mode,
        n_negatives=n,
        n_distinct_negatives=int(len(vals) - 1),
        honours_contract=bool(achieved <= t + 1e-12),
        flags_nothing=bool(achieved == 0.0),
        closest_attainable_fpr=closest_fpr,
        closest_attainable_threshold=closest_thr,
    )


def flips_at_threshold(labels, clean_scores, attacked_scores, threshold):
    """At a fixed threshold, count operationally meaningful flips (§6).

    For hide targets (label 1): flagged -> unflagged is a successful hide.
    For false-alarm targets (label 0): unflagged -> flagged is a successful false alarm.
    Returns a dict of counts and rates.

    `threshold` may be a float or an `OperatingPoint`. Either way the returned dict carries
    `achieved_fpr` — recomputed HERE from the negatives actually passed in, with the same
    `>=` rule the flip counts use. It is therefore the realised false-positive rate of this
    exact table, not a nominal target carried along from wherever the threshold came from.
    """
    op = threshold if isinstance(threshold, OperatingPoint) else None
    thr = float(threshold)
    y = np.asarray(labels)
    c = np.asarray(clean_scores, dtype=float)
    a = np.asarray(attacked_scores, dtype=float)
    clean_flag = c >= thr
    att_flag = a >= thr
    hide = (y == 1)
    fa = (y == 0)
    hide_flip = np.sum(hide & clean_flag & ~att_flag)      # was caught, now missed
    fa_flip = np.sum(fa & ~clean_flag & att_flag)          # was fine, now false-alarmed
    n_neg = int(fa.sum())
    n_flagged_clean = int(np.sum(fa & clean_flag))
    out = {
        "threshold": thr,
        "n_hide": int(hide.sum()),
        "hide_flagged_to_unflagged": int(hide_flip),
        "hide_flip_rate": float(hide_flip / hide.sum()) if hide.sum() else 0.0,
        "n_false_alarm": n_neg,
        "fa_unflagged_to_flagged": int(fa_flip),
        "fa_flip_rate": float(fa_flip / fa.sum()) if fa.sum() else 0.0,
        # The honest operating-point label (defect 1, 2026-08-13).
        "achieved_fpr": (n_flagged_clean / n_neg) if n_neg else float("nan"),
        "n_negatives_flagged_clean": n_flagged_clean,
    }
    if op is not None:
        out["target_fpr"] = op.target_fpr
        out["threshold_rule"] = op.mode
        out["fpr_contract_honoured"] = op.honours_contract
        out["operating_point_flags_nothing"] = op.flags_nothing
        out["closest_attainable_fpr"] = op.closest_attainable_fpr
        out["closest_attainable_threshold"] = op.closest_attainable_threshold
        out["n_distinct_negative_scores"] = op.n_distinct_negatives
        out["operating_point_label"] = str(op)
    return out
