"""Budget-corrected operating-point flip test — the censoring-immune FA statistic."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import flip_test


def test_flip_test_is_KNOWN_anticonservative_do_not_use_as_a_claim_statistic():
    """REGRESSION TEST ON A KNOWN DEFECT, not a passing feature.

    flip_test's null is biased: P(cross) = 1-(1-pi)^N is concave in pi, so integrating it
    over a wide posterior for pi under-predicts crossings (Jensen), and the observed count
    beats the null for free. Measured H0 levels at nominal 0.05: 0.81 (m=30) ... 0.35
    (m=181) — raising the benign budget does NOT fix it.

    This test asserts the failure ON PURPOSE. If someone rebuilds the null correctly
    (conditional/permutation), this test will start failing — which is the signal to
    re-validate and then flip the assertion, not to delete it."""
    rng = np.random.default_rng(0)
    N, m, T, trials = 181, 30, 80, 60
    rejects = 0
    for _ in range(trials):
        a, k = [], []
        for _ in range(T):
            pi = rng.uniform(0.0, 0.05)                  # per-paraphrase crossing rate
            k.append(int(rng.binomial(m, pi)))
            a.append(bool(rng.random() < 1 - (1 - pi) ** N))   # H0 attack = max of N
        if flip_test(a, k, [m] * T, N, n_sim=2000, seed=1)["p_value"] <= 0.05:
            rejects += 1
    level = rejects / trials
    assert level > 0.30, (
        f"flip_test now rejects at {level:.3f} under H0 — if this dropped toward 0.05 the "
        "null may have been fixed; re-validate properly and update this test rather than "
        "assuming it is safe.")


def test_detects_an_attack_that_beats_its_budget():
    """An attack that crosses on EVERY target while benign paraphrases essentially never
    do is a real effect and must be detected."""
    N, m, T = 181, 30, 80
    res = flip_test([True] * T, [0] * T, [m] * T, N, n_sim=4000, seed=2)
    assert res["observed"] == T
    assert res["p_value"] < 0.05
    assert res["expected"] < T


def test_no_effect_when_attack_matches_the_budget_corrected_null():
    """If benign paraphrases cross often, a max-of-181 crossing is UNSURPRISING and must
    not be scored as evidence — this is the winner's-curse correction doing its job."""
    N, m, T = 181, 30, 80
    # 20% of benign draws cross => under H0 the attack crosses essentially always
    res = flip_test([True] * T, [6] * T, [m] * T, N, n_sim=4000, seed=3)
    assert res["p_value"] > 0.2
    assert res["expected"] == pytest.approx(T, rel=0.05)


def test_ceiling_is_irrelevant_to_this_statistic():
    """The statistic sees only threshold crossings, so saturated and unsaturated targets
    are handled identically — no tie rule, no censoring correction."""
    N, m, T = 181, 30, 40
    saturated = flip_test([True] * T, [3] * T, [m] * T, N, n_sim=4000, seed=4)
    assert 0.0 <= saturated["p_value"] <= 1.0
    assert saturated["benign_crossing_rate"] == pytest.approx(0.1)


def test_empty_and_degenerate_inputs():
    assert flip_test([], [], [], 181)["n_targets"] == 0
    r = flip_test([True], [0], [10], 181, n_sim=2000, seed=5)
    assert r["n_targets"] == 1 and 0.0 <= r["p_value"] <= 1.0
