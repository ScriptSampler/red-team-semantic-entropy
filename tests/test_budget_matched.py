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


def test_attack_move_at_budget_prefix_semantics():
    from se.stats import attack_move_at_budget as amb
    # traj[0]=baseline objective; each iteration adds top_N*M = 9 candidates.
    traj = [1.00, 1.20, 1.35, 1.35, 1.60]      # best-so-far after iters 0..4
    assert amb(traj, 1) == pytest.approx(0.0)          # only the original scored
    assert amb(traj, 10) == pytest.approx(0.20)        # 1 + 1*9 -> iteration 1
    assert amb(traj, 19) == pytest.approx(0.35)        # 1 + 2*9 -> iteration 2
    assert amb(traj, 28) == pytest.approx(0.35)        # plateau preserved
    assert amb(traj, 181) == pytest.approx(0.60)       # clamps to the full run
    assert amb(traj, 100000) == pytest.approx(0.60)    # past the end clamps
    assert amb([], 50) is None
    assert amb(None, 50) is None


def test_attack_move_at_budget_is_monotone_nondecreasing():
    from se.stats import attack_move_at_budget as amb
    traj = [0.5, 0.7, 0.7, 0.9, 1.4, 1.4]
    moves = [amb(traj, b) for b in range(1, 200, 7)]
    assert all(b >= a for a, b in zip(moves, moves[1:]))   # running max never decreases
    assert min(moves) >= 0.0                                # never below the baseline


def test_attack_move_at_budget_respects_beam_shape():
    from se.stats import attack_move_at_budget as amb
    traj = [0.0, 0.3, 0.6]
    # with a 2x2 beam only 4 candidates per iteration, so budget 5 reaches iteration 1
    assert amb(traj, 5, top_N=2, candidate_size_M=2) == pytest.approx(0.3)
    assert amb(traj, 9, top_N=2, candidate_size_M=2) == pytest.approx(0.6)
