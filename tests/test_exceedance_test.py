"""Exact budget-corrected exceedance test (critique_log 23). Pure CPU."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import exceedance_counts, exceedance_test


def test_exceedance_counts_basic():
    c = exceedance_counts([0.5, 0.9], [[0.1, 0.6, 0.7], [0.1, 0.2]])
    assert c == [(2, 3), (0, 2)]
    assert exceedance_counts([0.5], [[]]) == []          # empty benign skipped


def test_null_is_calibrated_by_simulation():
    """THE load-bearing check: simulate H0 (attack candidates and benign draws iid from one
    distribution) and confirm the test rejects at ~the nominal rate, not more."""
    rng = np.random.default_rng(0)
    N, m, T, trials = 181, 30, 40, 300
    rejects = 0
    for _ in range(trials):
        counts = []
        for _ in range(T):
            # one shared distribution per target => H0 true by construction
            scale = rng.uniform(0.5, 2.0)
            attack = rng.gamma(2.0, scale, N).max()       # attack-max over N candidates
            benign = rng.gamma(2.0, scale, m)             # m benign draws, SAME F
            counts.append((int((benign > attack).sum()), m))
        if exceedance_test(counts, N)["p_value"] <= 0.05:
            rejects += 1
    level = rejects / trials
    assert level < 0.12, f"test is anti-conservative under H0: level={level:.3f}"


def test_expected_count_matches_theory():
    N, m, T = 181, 30, 50
    res = exceedance_test([(0, m)] * T, N)
    assert res["expected"] == pytest.approx(T * m / (N + 1))
    # P(attack beats ALL m benign) = N/(N+m)
    assert res["p_attack_beats_all_per_target"] == pytest.approx(N / (N + m))


def test_detects_a_real_effect():
    """A genuinely superior attack (zero benign exceedances everywhere) must be significant,
    and materially fewer-than-expected exceedances should also reject."""
    N, m, T = 181, 30, 40
    strong = exceedance_test([(0, m)] * T, N)
    assert strong["p_value"] < 0.05
    assert strong["n_eff"] == float("inf")               # never beaten -> unbounded
    # expected total is T*m/(N+1) ~ 6.6; observing 0-1 is a real signal
    mild = exceedance_test([(0, m)] * (T - 1) + [(1, m)], N)
    assert mild["p_value"] < 0.10


def test_no_effect_gives_large_p_and_finite_n_eff():
    N, m, T = 181, 30, 40
    # exceedances at ~10x the H0 expectation: no evidence the attack beats chance
    res = exceedance_test([(2, m)] * T, N)
    assert res["p_value"] > 0.5
    assert res["n_eff"] == pytest.approx(m / 2 - 1)      # 30/2 - 1 = 14 random paraphrases
    assert exceedance_test([], N)["n_targets"] == 0
