"""The weighting-invariant cluster-count bound. CPU only, no data, no model.

`results/cluster_count_bound.md` proposes K >= ceil(N^0.9) as the one ceiling-derived
claim that survives a change of semantic-entropy estimator, and quotes K >= 8 at N=10.
The margin at N=10 is 7.1e-3 nats, so the arithmetic is pinned here rather than trusted:
a float comparison that tips the wrong way turns the paper's number from 8 into 7.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


C = _load("cluster_count_bound")


def test_the_inequality_that_makes_the_bound_eight_at_n10():
    """log 8 clears 0.9 log 10 and log 7 does not. Everything else follows from this."""
    assert math.log(8) > 0.9 * math.log(10) > math.log(7)
    assert math.log(8) - 0.9 * math.log(10) == pytest.approx(0.0071149, abs=1e-6)


def test_k_min_is_eight_at_n10_and_fifteen_at_n20():
    assert C.k_min_exact(10) == 8
    assert C.k_min_exact(20) == 15


def test_exact_integer_and_closed_forms_agree_over_a_wide_range():
    """K^10 >= N^9 is the exact integer restatement of K >= ceil(N^0.9). They must not
    diverge anywhere -- including at N where N^0.9 is very nearly an integer."""
    for n in range(1, 400):
        assert C.k_min_exact(n) == C.k_min_float(n), n


def test_k_min_never_exceeds_n_and_is_monotone():
    prev = 0
    for n in range(1, 200):
        km = C.k_min_exact(n)
        assert 1 <= km <= n
        assert km >= prev
        prev = km


def test_the_required_fraction_decays_as_n_to_the_minus_tenth():
    """The claim that a bigger budget barely loosens the CONSTRAINT: the required share
    of samples in distinct clusters is N^(-0.1), which needs N=1024 to reach one half."""
    assert 10 ** -0.1 == pytest.approx(0.7943, abs=1e-4)
    assert 20 ** -0.1 == pytest.approx(0.7411, abs=1e-4)
    assert 1024 ** -0.1 == pytest.approx(0.5, abs=1e-12)
    assert C.k_min_exact(1024) == 512


def test_a_lower_threshold_than_the_top_decile_relaxes_the_bound():
    """Generality check: the bound is parameterised by the fraction of the range, and
    K^den >= N^num must track it."""
    assert C.k_min_exact(10, num=1, den=2) == 4        # half the range: K >= sqrt(10)
    assert C.k_min_exact(10, num=1, den=1) == 10       # the full cap needs all singletons


def test_the_discrete_estimator_binds_at_k_nine_not_k_eight():
    """No integer partition of 10 into 8 parts clears 0.9 log 10 -- the best is
    (2,2,1,1,1,1,1,1) at 2.0253 -- so the discrete-specific requirement is K >= 9. The
    paper must quote 8 (variant-proof) and not 9 (ours)."""
    kmin, best = C.discrete_k_min(10, C.TOP_DECILE)
    assert kmin == 9
    assert best[8] == pytest.approx(2.0253, abs=1e-4)
    assert best[8] < C.TOP_DECILE < best[9]
    assert best[9] == pytest.approx(2.1640, abs=1e-4)
    assert best[10] == pytest.approx(math.log(10), abs=1e-12)


def test_the_two_top_decile_lattice_points_are_the_k9_and_k10_partitions():
    lattice = sorted({round(C.partition_entropy(p), 9) for p in C.partitions(10)})
    top = [v for v in lattice if v >= C.TOP_DECILE - 1e-12]
    assert len(lattice) == 39
    assert top == [pytest.approx(2.163956, abs=1e-6), pytest.approx(2.302585, abs=1e-6)]


def test_partition_enumeration_is_exhaustive():
    assert sum(1 for _ in C.partitions(10)) == 42      # p(10)
    assert all(sum(p) == 10 for p in C.partitions(10))


# ----------------------------------------------------------- sufficiency-volume tools
def test_quadratic_radius_matches_the_entropy_deficit_it_encodes():
    """H(u + d) = log K - (K/2)||d||^2 + O(||d||^3): a point at exactly the quadratic
    radius should sit at the threshold to second order."""
    import numpy as np
    k = 8
    r = C.quadratic_radius(k, C.TOP_DECILE)
    d = np.zeros(k)
    d[0], d[1] = r / math.sqrt(2), -r / math.sqrt(2)
    p = np.full(k, 1.0 / k) + d
    h = -float((p * np.log(p)).sum())
    assert h == pytest.approx(C.TOP_DECILE, abs=2e-4)


def test_quadratic_radius_is_zero_when_the_threshold_is_unreachable():
    assert C.quadratic_radius(7, C.TOP_DECILE) == 0.0


def test_ball_over_simplex_ratio_is_one_for_the_whole_simplex_scale():
    """Sanity on the closed form: the ratio must be dimensionless, monotone in the
    radius, and scale as R^(K-1)."""
    a = C.log_ball_over_simplex(8, 0.05)
    b = C.log_ball_over_simplex(8, 0.10)
    assert b - a == pytest.approx(7 * math.log(2), abs=1e-12)


def test_ball_ratio_estimator_reproduces_the_crude_rate_where_both_work():
    """K=10 is measurable by plain uniform sampling, so the ball estimator has a
    reference. Agreement there is what licenses the K=8 number, which has none."""
    import numpy as np
    rng = np.random.default_rng(7)
    hits, draws = C.simplex_topdecile_volume(10, C.TOP_DECILE, 40_000, rng)
    crude = hits / draws
    r = C.quadratic_radius(10, C.TOP_DECILE)
    ball, se, _, _ = C.simplex_topdecile_volume_ball(
        10, C.TOP_DECILE, 1.5 * r, 40_000, rng)
    assert abs(ball - crude) < 6 * max(se, 1e-3)


def test_k8_admissible_volume_is_of_order_two_in_a_million():
    """The 'necessary but nowhere near sufficient' number the write-up quotes."""
    import numpy as np
    rng = np.random.default_rng(0)
    r = C.quadratic_radius(8, C.TOP_DECILE)
    v, se, hits, maxr = C.simplex_topdecile_volume_ball(
        8, C.TOP_DECILE, 1.5 * r, 100_000, rng)
    assert 1.0e-6 < v < 3.0e-6
    assert hits > 1000
    assert maxr < 1.5 * r          # the admissible set really is inside the ball


# ------------------------------------------------------------------------- intervals
def test_wilson_interval_brackets_the_point_estimate():
    p, lo, hi = C.wilson(58, 200)
    assert lo < p < hi
    assert p == pytest.approx(0.29)
    assert (lo, hi) == (pytest.approx(0.2325, abs=1e-3), pytest.approx(0.3556, abs=1e-3))


def test_wilson_stays_inside_the_unit_interval_at_the_boundaries():
    for k, n in ((0, 80), (80, 80), (1, 2000)):
        _, lo, hi = C.wilson(k, n)
        assert 0.0 <= lo <= hi <= 1.0


def test_newcombe_difference_excludes_zero_for_the_headline_contrast():
    """29.0% vs 57.5% on 200 + 200: the correct/hallucinating gap in K >= 8."""
    d, lo, hi = C.newcombe_diff(115, 200, 58, 200)
    assert d == pytest.approx(0.285)
    assert lo > 0.15 and hi < 0.40


def test_newcombe_difference_is_antisymmetric():
    d1, lo1, hi1 = C.newcombe_diff(115, 200, 58, 200)
    d2, lo2, hi2 = C.newcombe_diff(58, 200, 115, 200)
    assert d2 == pytest.approx(-d1)
    assert lo2 == pytest.approx(-hi1)
    assert hi2 == pytest.approx(-lo1)
