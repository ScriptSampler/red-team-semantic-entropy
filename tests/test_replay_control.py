"""The replay control's arithmetic, pinned.

`scripts/replay_control.py` decides whether two blocked paper claims survive, so the
statistics it computes have to be the ones it says they are. What is asserted here:

  1. THE FLOOR IS THE FIRST FIRING POINT, not the ceiling atom. This is the exact defect
     the report identifies in `results/n_scaling_grid.md`: the two agree while some
     negative sits at the ln N cap and diverge when none does, and the divergent case is
     the one the published table gets wrong.
  2. THE ROC PIECES. AUROC agrees with sklearn on tied, atomic scores (semantic entropy is
     mostly atoms, so a tie convention that drifts would move every number in the report);
     the band pAUC is the MEAN TPR in the band, so a chance detector scores the band
     midpoint and not 0.5 -- the mislabel section 4 of the report is about.
  3. THE RANDOMISED FRONTIER dominates the deterministic points and is concave, which is
     what licenses comparing budgets whose achievable grids do not line up.
  4. THE POISSON-BINOMIAL null: exact against a brute-force convolution, exact against the
     binomial when the probabilities are equal, and -- the property that makes it the
     sharp test rather than the forgiving one -- heterogeneity shrinks its variance.

CPU only: no GPU, no model, no sample cache, no network. Nothing here reads the Week-4
cache, so these run anywhere.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import replay_control as RC                                             # noqa: E402
from se.stats import attainable_fprs                                    # noqa: E402


# ----------------------------------------------------------------- 1. the floor column
def test_floor_is_the_ceiling_atom_when_the_cap_is_occupied():
    """N=10 case: 3 of 20 negatives sit at ln 10, so both readings give 15%."""
    neg = np.array([math.log(10)] * 3 + [1.0] * 17)
    assert RC.min_nonzero_fpr(neg) == pytest.approx(3 / 20)
    assert RC.ceiling_atom(neg, 10) == 3


def test_floor_diverges_from_the_ceiling_atom_when_the_cap_is_empty():
    """The N=40 case, and the defect in the published grid: no negative reaches ln 40, so
    the ceiling atom is 0 while the cheapest alarm an operator can buy is 4/200."""
    neg = np.array([2.5] * 4 + [1.0] * 196)
    assert RC.ceiling_atom(neg, 40) == 0
    assert RC.min_nonzero_fpr(neg) == pytest.approx(4 / 200)
    # ... and the "next FPR" is the SECOND firing point, not the second thing after zero
    fprs = sorted(RC.firing_fprs(neg))
    assert fprs[0] == pytest.approx(4 / 200)
    assert fprs[1] == pytest.approx(200 / 200)


def test_firing_fprs_agree_with_the_projects_attainable_grid():
    rng = np.random.default_rng(0)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=60), 9)
    vals, fprs = attainable_fprs(neg)
    theirs = sorted(float(f) for v, f in zip(vals, fprs) if np.isfinite(v))
    assert sorted(RC.firing_fprs(neg)) == pytest.approx(theirs)


# --------------------------------------------------------------------- 2. the ROC pieces
def test_auroc_matches_sklearn_on_heavily_tied_scores():
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(7)
    for _ in range(20):
        neg = rng.choice([0.0, 0.7, 1.1, 2.3], size=80)
        pos = rng.choice([0.0, 0.7, 1.1, 2.3], size=80)
        y = np.concatenate([np.zeros(80), np.ones(80)])
        assert RC.auroc(neg, pos) == pytest.approx(
            float(roc_auc_score(y, np.concatenate([neg, pos]))), abs=1e-12)


def test_auroc_is_one_half_when_the_score_is_constant():
    """Every pair is a tie, and ties count 0.5 -- the case a ceiling atom drives."""
    c = np.full(50, 2.3)
    assert RC.auroc(c, c.copy()) == pytest.approx(0.5)


def test_pauc_band_is_mean_tpr_so_chance_is_the_band_midpoint():
    """A chance detector scores (lo+hi)/2 in every band, NOT 0.5. The published claim
    review labels this quantity '0.5 = chance within the band'; it is not."""
    rng = np.random.default_rng(3)
    s = rng.normal(size=4000)
    fx, fy = RC.roc_curve_points(s[:2000], s[2000:])
    for lo, hi in ((0.0, 0.05), (0.0, 0.10), (0.20, 0.50), (0.50, 1.0)):
        assert RC.pauc_band(fx, fy, lo, hi) == pytest.approx((lo + hi) / 2, abs=0.03)


def test_pauc_over_the_whole_range_is_the_auroc():
    rng = np.random.default_rng(11)
    neg = rng.normal(size=300)
    pos = rng.normal(loc=0.8, size=300)
    fx, fy = RC.roc_curve_points(neg, pos)
    assert RC.pauc_band(fx, fy, 0.0, 1.0) == pytest.approx(RC.auroc(neg, pos), abs=2e-3)


# ------------------------------------------------------------ 3. the randomised frontier
def test_hull_dominates_every_deterministic_point_and_is_concave():
    rng = np.random.default_rng(5)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200), 9)
    pos = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200, p=[.1, .2, .3, .4]), 9)
    fx, fy = RC.deterministic_points(neg, pos)
    hull = RC.upper_hull(fx, fy)
    for x, y in zip(fx, fy):
        assert RC.tpr_matched(fx, fy, float(x)) >= y - 1e-12
    slopes = [(hull[i + 1][1] - hull[i][1]) / (hull[i + 1][0] - hull[i][0])
              for i in range(len(hull) - 1) if hull[i + 1][0] > hull[i][0]]
    assert all(a >= b - 1e-12 for a, b in zip(slopes, slopes[1:]))


def test_at_most_never_exceeds_its_budget_and_flags_nothing_when_it_cannot():
    """The degenerate case the whole floor finding is about: a 15% atom at the top means
    no firing threshold honours a 10% budget, and the honest answer is 0% and no alarms."""
    neg = np.array([math.log(10)] * 30 + [1.0] * 170)
    pos = np.array([math.log(10)] * 100 + [1.0] * 100)
    fx, fy = RC.deterministic_points(neg, pos)
    assert RC.achieved_at_most(fx, 0.10) == pytest.approx(0.0)
    assert RC.tpr_at_most(fx, fy, 0.10) == pytest.approx(0.0)
    assert RC.achieved_at_most(fx, 0.20) == pytest.approx(0.15)


# --------------------------------------------------------------- 4. the Poisson-binomial
def test_poisson_binomial_reduces_to_the_binomial_when_p_is_constant():
    from scipy.stats import binom
    ps = np.full(40, 0.3)
    got = RC.poisson_binomial_pmf(ps)
    assert got.sum() == pytest.approx(1.0)
    assert got == pytest.approx(binom.pmf(np.arange(41), 40, 0.3), abs=1e-12)


def test_poisson_binomial_matches_brute_force_enumeration():
    ps = np.array([0.05, 0.4, 0.9, 0.62, 0.11])
    exact = np.zeros(len(ps) + 1)
    for mask in range(1 << len(ps)):
        pr = 1.0
        k = 0
        for i, p in enumerate(ps):
            if mask >> i & 1:
                pr *= p
                k += 1
            else:
                pr *= 1 - p
        exact[k] += pr
    assert RC.poisson_binomial_pmf(ps) == pytest.approx(exact, abs=1e-12)


def test_heterogeneous_probabilities_shrink_the_variance():
    """Why the exact null is the SHARP test and a binomial on the mean would be lax: the
    per-question ceiling probabilities are spread from ~0 to ~1, and that spread cuts the
    variance of their sum."""
    spread = np.concatenate([np.full(100, 0.02), np.full(100, 0.22)])
    flat = np.full(200, spread.mean())
    v_spread = float((spread * (1 - spread)).sum())
    v_flat = float((flat * (1 - flat)).sum())
    assert v_spread < v_flat


# ----------------------------------------------------------------------- the stat pack
def test_stat_pack_is_internally_consistent():
    rng = np.random.default_rng(13)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200), 9)
    pos = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200, p=[.1, .2, .3, .4]), 9)
    pk = RC.stat_pack(neg, pos)
    assert pk["floor"] == pytest.approx(RC.min_nonzero_fpr(neg))
    assert pk["auroc"] == pytest.approx(RC.auroc(neg, pos))
    # a deterministic point is always available on the frontier, so the randomised TPR at
    # a budget can never be below the deterministic one
    for f, dk, mk in ((0.05, "det05", "m05"), (0.10, "det10", "m10"), (0.20, "det20", "m20")):
        assert pk[mk] >= pk[dk] - 1e-12
        assert pk[f"ach{int(f * 100):02d}"] <= f + 1e-12
