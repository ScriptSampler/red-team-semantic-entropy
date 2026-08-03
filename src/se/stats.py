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
