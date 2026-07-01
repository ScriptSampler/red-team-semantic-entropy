"""Statistics for honest reporting: bootstrap CIs, operating-point effects, and
success-cutoff sensitivity. Pure functions, CPU, unit-tested.

Addresses external-review B4 (no uncertainty on any number), §6 (a detector is a
threshold, not a ranking; report operating-point effects), and §6 (the 0.25-nat
success cutoff is unmotivated -> report a sensitivity curve).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import roc_auc_score


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


def rate_ci(flags, *, n_boot: int = 2000, alpha: float = 0.05, seed: int = 0) -> CI:
    """Bootstrap CI for a success/proportion (list of bools/0-1)."""
    return bootstrap_ci([1.0 if f else 0.0 for f in flags], np.mean,
                        n_boot=n_boot, alpha=alpha, seed=seed)


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
