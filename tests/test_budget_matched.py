"""B2 budget-matched winner's-curse control (critique_log 21). Pure CPU."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import analytic_max_percentile, paired_max_net


def test_analytic_max_percentile_closed_form():
    assert analytic_max_percentile(1) == 0.5
    assert analytic_max_percentile(180) == pytest.approx(180 / 181)
    assert analytic_max_percentile(180) > 0.99          # a max-of-180 sits ~99th, not 50th
    with pytest.raises(ValueError):
        analytic_max_percentile(0)


def test_analytic_matches_monte_carlo():
    # E[fraction of k iid draws below the max of m iid draws] should equal m/(m+1).
    rng = np.random.default_rng(0)
    m, k, trials = 20, 8, 20000
    fracs = []
    for _ in range(trials):
        cand = rng.standard_normal(m)
        ref = rng.standard_normal(k)
        fracs.append(np.mean(ref < cand.max()))
    assert np.mean(fracs) == pytest.approx(m / (m + 1), abs=0.01)


def test_paired_max_net_uses_benign_MAX_not_mean():
    # benign list [0.1, 0.9]: mean 0.5, MAX 0.9. Attack 0.5 beats the mean but LOSES to max.
    d = paired_max_net([0.5], [[0.1, 0.9]], n_boot=200)
    assert d["mean_benign_max"] == pytest.approx(0.9)
    assert d["net_ci"].point == pytest.approx(0.5 - 0.9)     # paired vs MAX, negative
    assert d["sign_ci"].point == 0.0                          # attack did NOT beat benign-max


def test_paired_max_net_attack_wins_and_loses():
    win = paired_max_net([0.9, 0.8, 0.85], [[0.1, 0.2], [0.0, 0.1], [0.2, 0.3]], n_boot=500)
    assert win["net_ci"].point > 0 and win["net_ci"].lo > 0   # attack clears budget-matched max
    assert win["sign_ci"].point == 1.0
    lose = paired_max_net([0.1, 0.2], [[0.5, 0.9], [0.4, 0.8]], n_boot=500)
    assert lose["net_ci"].point < 0
    assert lose["sign_ci"].point == 0.0


def test_paired_max_net_empty():
    d = paired_max_net([], [], n_boot=100)
    assert d["n"] == 0 and d["net_ci"] is None
    # targets with empty benign lists are skipped, not crashed
    d2 = paired_max_net([0.5, 0.6], [[], [0.1]], n_boot=100)
    assert d2["n"] == 1
