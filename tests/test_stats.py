"""Tests for the reporting statistics (CIs, operating point, cutoff curve)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import (
    bootstrap_ci, auroc_ci, rate_ci, success_rate_over_cutoffs,
    operating_point, flips_at_threshold,
)


def test_bootstrap_ci_constant():
    ci = bootstrap_ci([5.0] * 20, np.mean)
    assert ci.point == 5.0 and ci.lo == 5.0 and ci.hi == 5.0


def test_bootstrap_ci_brackets_point():
    rng = np.random.default_rng(0)
    x = rng.normal(10, 2, size=500)
    ci = bootstrap_ci(x, np.mean)
    assert ci.lo < ci.point < ci.hi
    assert abs(ci.point - 10) < 0.5


def test_auroc_ci_perfect_separation():
    labels = [0, 0, 0, 1, 1, 1]
    scores = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    ci = auroc_ci(labels, scores, n_boot=500)
    assert abs(ci.point - 1.0) < 1e-9
    assert ci.hi <= 1.0 + 1e-9


def test_rate_ci_all_true():
    ci = rate_ci([True] * 10)
    assert ci.point == 1.0


def test_cutoff_curve_is_monotone_non_increasing():
    moves = [0.1, 0.3, 0.6, 1.0, 2.0]
    feas = [True] * 5
    curve = success_rate_over_cutoffs(moves, feas, [0.0, 0.25, 0.5, 1.0, 1.5, 2.5])
    rates = [r for _, r in curve]
    assert all(rates[i] >= rates[i + 1] for i in range(len(rates) - 1))
    assert rates[0] == 1.0        # cutoff 0 -> all feasible succeed
    assert rates[-1] == 0.0       # cutoff 2.5 -> none reach it


def test_cutoff_curve_respects_feasibility():
    moves = [2.0, 2.0]
    feas = [True, False]
    curve = success_rate_over_cutoffs(moves, feas, [0.25])
    assert curve[0][1] == 0.5     # only the feasible one counts


def test_operating_point_and_flips():
    # negatives (label 0) clean scores; threshold at 90th pct of negatives.
    labels =        [0,   0,   0,   0,   1,   1,   1,   1]
    clean =         [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    thr = operating_point(labels, clean, target_fpr=0.25)   # ~0.325
    # A hide target (label 1) flagged clean but pushed below thr = hide flip.
    # A false-alarm target (label 0) UNflagged clean but pushed above thr = fa flip.
    # idx2 (label0, clean 0.3 < thr, unflagged) -> 0.95 (flagged) : fa flip.
    # idx4 (label1, clean 0.6 >= thr, flagged)  -> 0.2  (unflagged): hide flip.
    attacked =      [0.1, 0.2, 0.95, 0.4, 0.2, 0.7, 0.8, 0.9]
    f = flips_at_threshold(labels, clean, attacked, thr)
    assert f["n_hide"] == 4 and f["n_false_alarm"] == 4
    assert f["hide_flagged_to_unflagged"] >= 1
    assert f["fa_unflagged_to_flagged"] >= 1
