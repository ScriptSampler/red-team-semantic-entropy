"""EXACT stratified conditional crossing test — the correct replacement for flip_test."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import flip_test_conditional


def test_null_is_calibrated_the_check_flip_test_failed():
    """THE load-bearing test. Simulate H0 — attack candidates and benign draws exchangeable,
    every target with its own crossing rate — and confirm the rejection rate is at most
    nominal. flip_test rejected 81% here; this must not."""
    rng = np.random.default_rng(0)
    N, m, T, trials = 181, 50, 80, 200
    rejects = 0
    for _ in range(trials):
        ac, an, bc, bn = [], [], [], []
        for _ in range(T):
            pi = rng.uniform(0.0, 0.08)          # per-paraphrase crossing rate, varies by target
            ac.append(int(rng.binomial(N, pi)))  # attack candidates that crossed
            an.append(N)
            bc.append(int(rng.binomial(m, pi)))
            bn.append(m)
        if flip_test_conditional(ac, an, bc, bn)["p_value"] <= 0.05:
            rejects += 1
    level = rejects / trials
    assert level <= 0.10, f"anti-conservative under H0: {level:.3f}"


def test_detects_a_real_crossing_advantage():
    """Attack crosses at 3x the benign rate across many targets -> must reject."""
    N, m, T = 181, 50, 40
    ac = [30] * T          # ~17% of attack candidates cross
    bc = [3] * T           # ~6% of benign draws cross
    res = flip_test_conditional(ac, [N] * T, bc, [m] * T)
    assert res["p_value"] < 0.01
    assert res["observed"] > res["expected"]
    assert res["attack_crossing_rate"] > res["benign_crossing_rate"]


def test_matched_rates_give_no_evidence():
    N, m, T = 181, 50, 40
    res = flip_test_conditional([18] * T, [N] * T, [5] * T, [m] * T)   # ~10% both
    assert res["p_value"] > 0.2
    assert res["observed"] == pytest.approx(res["expected"], rel=0.1)


def test_ceiling_cannot_censor_a_binary_crossing():
    """Saturation is irrelevant: the statistic only asks whether the threshold was crossed."""
    N, m, T = 181, 50, 30
    res = flip_test_conditional([181] * T, [N] * T, [50] * T, [m] * T)  # everything crosses
    assert res["n_targets"] == T
    assert res["p_value"] == pytest.approx(1.0, abs=0.05)   # no contrast, no evidence


def test_degenerate_inputs():
    assert flip_test_conditional([], [], [], [])["n_targets"] == 0
    assert flip_test_conditional([5], [0], [1], [10])["n_targets"] == 0   # zero-size arm dropped
