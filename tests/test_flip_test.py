"""RETIRED statistic. `flip_test`'s null is anti-conservative; `flip_test_conditional` is
the exact replacement and carries the real coverage (see tests/test_flip_conditional.py).

Only two things are tested here, deliberately:
  1. the retirement guard fires, so the function cannot be used by accident;
  2. the measured defect still reproduces, so the finding stays alive rather than becoming
     a claim in a changelog nobody re-runs.

Tests asserting that flip_test *detects* effects correctly were removed on 2026-08-12: they
exercised a function whose null is known-broken, and a green suite next to a broken statistic
reads as validation. The equivalent assertions live against the conditional version.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import flip_test


def test_retirement_guard_blocks_accidental_use():
    """The docstring warning was the only thing standing between a future session and a
    known-invalid p-value. Now it raises."""
    with pytest.raises(RuntimeError, match="RETIRED"):
        flip_test([True], [0], [10], 181)


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
        res = flip_test(a, k, [m] * T, N, n_sim=2000, seed=1,
                        _documented_defect_opt_in=True)
        if res["p_value"] <= 0.05:
            rejects += 1
    level = rejects / trials
    assert level > 0.30, (
        f"flip_test now rejects at {level:.3f} under H0 — if this dropped toward 0.05 the "
        "null may have been fixed; re-validate properly and update this test rather than "
        "assuming it is safe.")
