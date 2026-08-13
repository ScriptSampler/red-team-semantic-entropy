"""The achievable-FPR-grid claim, asserted as arithmetic rather than as a data readout.

`results/achievable_fpr_grid.md` rests on four load-bearing statements. The measured
numbers in it need the WSL sample cache, but none of these four do, so all of them are
tested here on synthetic scores and pure enumeration:

  1. THE IDENTITY. On a score with a maximum M, the smallest NON-ZERO false-positive rate
     any threshold can realise is exactly the mass of the atom at M, because every
     threshold above M flags nothing. This is the whole result; if it is not an identity
     the report is an anecdote.
  2. THE CONTRACT. `operating_point(..., mode='at_most')` must degenerate to "flag
     nothing" whenever the target sits below that atom -- never fire at the atom's rate
     and call it a 5% operating point. (Regression on defect 1 of 2026-08-13, from the
     angle this report needs.)
  3. THE ROUNDING DIRECTION. Float noise can only ever ADD operating points, i.e. make the
     grid look FINER than it is. The report rounds to 9 dp first; this asserts the harm
     runs the way the report claims, so the mitigation is pointed at the real risk.
  4. THE N=20 MONOTONICITY. §7 argues the floor is non-increasing in N because
     {all 20 samples distinct} is contained in {the first 10 are distinct}. That is a
     containment, not a statistic, and it is checked as one.

Plus the lattice counts (39/2 at N=10, 455/7 at N=20) the report quotes as enumeration,
and a round-trip of the report's own `grid()` against a brute-force recomputation.

CPU only, no cache, no model, no network.
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

from se.stats import attainable_fprs, operating_point            # noqa: E402
from achievable_fpr_grid import grid, n_firing_below, _upper_hull  # noqa: E402
from fair_pool_granularity import attainable_lattice               # noqa: E402

CAP = math.log(10)


def _scores(rng, n, atom_frac, cap=CAP):
    """Clean correct-answer scores: a continuous body strictly below the cap, plus an atom
    ON the cap. `atom_frac` is exact, not a coin flip, so the expected grid is known."""
    k = int(round(n * atom_frac))
    body = rng.uniform(0.0, cap * 0.95, n - k)
    return np.concatenate([np.full(k, cap), body])


# ============================================================ 1. the identity
@pytest.mark.parametrize("n,k", [(200, 19), (200, 1), (200, 60), (1424, 150), (37, 4)])
def test_min_nonzero_attainable_fpr_is_exactly_the_ceiling_atom(n, k):
    """The report's headline, as arithmetic: min non-zero FPR == atom mass at the max."""
    rng = np.random.default_rng(n + k)
    neg = _scores(rng, n, k / n)
    vals, fprs = attainable_fprs(neg)

    nonzero = [f for f in fprs if f > 0]
    assert min(nonzero) == pytest.approx(k / n), \
        "the smallest firing FPR must be the mass sitting exactly at the maximum"

    # ...and it is realised at tau = max, with nothing between it and zero.
    top = float(np.max(neg))
    assert float(np.mean(neg >= top)) == pytest.approx(k / n)
    assert not any(0.0 < f < k / n - 1e-12 for f in fprs), \
        "an FPR strictly between 0 and the atom mass would falsify the whole report"


def test_two_atoms_leave_a_hole_in_the_grid_the_size_of_the_lower_one():
    """The fair pool's shape: atoms at ln 10 and at 2.163956, nothing between. The grid
    must jump 0 -> 19/200 -> 43/200 with no intermediate rate available."""
    second = 2.163956
    neg = np.concatenate([np.full(19, CAP), np.full(24, second),
                          np.linspace(0.0, 2.0, 157)])
    _, fprs = attainable_fprs(neg)
    achievable = sorted(set(round(float(f), 12) for f in fprs))
    assert achievable[0] == 0.0
    assert achievable[1] == pytest.approx(19 / 200)
    assert achievable[2] == pytest.approx(43 / 200)
    for target in (0.01, 0.05, 0.10, 0.20):
        assert not any(abs(f - target) < 1e-12 for f in achievable), \
            f"FPR {target:.0%} must not be on the grid"


# ============================================================ 2. the contract
@pytest.mark.parametrize("target", [0.0, 0.005, 0.01, 0.05, 0.09])
def test_at_most_flags_nothing_when_the_target_is_below_the_atom(target):
    """Below the atom there is no firing threshold, and `at_most` must say so rather than
    fire at the atom's rate. This is the operator-facing half of defect 1."""
    rng = np.random.default_rng(7)
    neg = _scores(rng, 200, 0.095)
    y = np.zeros(200, dtype=int)
    op = operating_point(y, neg, target_fpr=target, mode="at_most")
    assert op.flags_nothing and op.achieved_fpr == 0.0
    assert not np.isfinite(op.threshold)
    assert op.honours_contract
    # ...while still naming the nearest thing that does exist, so the caller is not stuck.
    assert op.closest_attainable_fpr == pytest.approx(0.095)


def test_closest_reports_being_over_budget_rather_than_hiding_it():
    rng = np.random.default_rng(8)
    neg = _scores(rng, 200, 0.095)
    op = operating_point(np.zeros(200, dtype=int), neg, target_fpr=0.05, mode="closest")
    assert op.achieved_fpr == pytest.approx(0.095)
    assert not op.honours_contract
    assert op.achieved_fpr == pytest.approx(float(np.mean(neg >= float(op))))


def test_reported_achieved_fpr_is_the_realised_one_in_every_mode():
    rng = np.random.default_rng(9)
    for atom in (0.0, 0.05, 0.095, 0.3):
        neg = _scores(rng, 200, atom)
        for mode in ("at_most", "closest", "nominal_quantile"):
            for t in (0.01, 0.05, 0.10, 0.20):
                op = operating_point(np.zeros(200, dtype=int), neg,
                                     target_fpr=t, mode=mode)
                assert op.achieved_fpr == pytest.approx(
                    float(np.mean(neg >= float(op))), abs=1e-12), \
                    f"{mode} at {t}: reported FPR is not the one `>=` realises"


# ============================================================ 3. rounding direction
def test_float_noise_can_only_ADD_operating_points():
    """The report rounds scores to 9 dp before building the grid. The risk that mitigates
    runs in one direction only: unrounded, ~1e-16 noise splits one attainable value into
    several thresholds and the grid looks FINER than the estimator can be. Rounding can
    never invent a rate (the smallest gap in the N=10 lattice is ~2.9e-3 nats)."""
    lattice = attainable_lattice(10)
    rng = np.random.default_rng(11)
    exact = np.array([lattice[i % len(lattice)] for i in range(200)])
    noisy = exact * (1.0 + rng.normal(0.0, 1e-16, 200))     # same values, float noise

    n_exact = len(attainable_fprs(exact)[0])
    n_noisy = len(attainable_fprs(noisy)[0])
    n_rounded = len(attainable_fprs(np.round(noisy, 9))[0])

    assert n_noisy >= n_exact, "noise must not remove operating points"
    assert n_noisy > n_exact, "this fixture is supposed to demonstrate the inflation"
    assert n_rounded == n_exact, "9-dp rounding must recover exactly the real grid"


def test_rounding_to_9dp_never_merges_two_attainable_values():
    for n in (10, 20):
        lat = attainable_lattice(n)
        assert len({round(v, 9) for v in lat}) == len(lat)


# ============================================================ 4. N=20 monotonicity
def test_all_N_distinct_is_nested_so_the_fpr_floor_cannot_rise_with_N():
    """§7's only claim about N=20 that needs no data. If all 20 sampled answers are
    pairwise inequivalent then so are any 10 of them, so {saturate at 20} is a SUBSET of
    {saturate at 10} under the coupling "the N=10 draw is the first 10 of the N=20 draw".
    Checked per realisation, which is stronger than checking the two rates."""
    rng = np.random.default_rng(3)
    n_sat10 = n_sat20 = 0
    for _ in range(3000):
        p = rng.dirichlet(np.full(14, 0.6))          # a per-question answer distribution
        draw = rng.choice(len(p), size=20, p=p)
        sat20 = len(set(draw.tolist())) == 20
        sat10 = len(set(draw[:10].tolist())) == 10
        assert not (sat20 and not sat10), "containment violated on a single realisation"
        n_sat10 += sat10
        n_sat20 += sat20
    assert n_sat20 <= n_sat10


# ============================================================ enumeration + round-trip
def test_lattice_counts_quoted_by_the_report():
    lat10, lat20 = attainable_lattice(10), attainable_lattice(20)
    assert len(lat10) == 39 and len(lat20) == 455
    assert sum(1 for v in lat10 if v >= 0.9 * math.log(10) - 1e-12) == 2
    assert sum(1 for v in lat20 if v >= 0.9 * math.log(20) - 1e-12) == 7
    assert lat10[-1] == pytest.approx(math.log(10))
    assert lat10[-2] == pytest.approx(2.163956, abs=1e-6)


def test_grid_matches_a_brute_force_recomputation():
    rng = np.random.default_rng(5)
    neg = np.round(_scores(rng, 150, 0.12), 9)
    pos = np.round(_scores(rng, 90, 0.30), 9)
    rows = grid(neg, pos)

    assert rows[0]["fires"] is False and rows[0]["fpr"] == 0.0     # ascending FPR
    assert [r["fpr"] for r in rows] == sorted(r["fpr"] for r in rows)
    for r in rows:
        tau = r["threshold"]
        assert r["fpr"] == pytest.approx(float(np.mean(neg >= tau)))
        assert r["tpr"] == pytest.approx(float(np.mean(pos >= tau)))
    assert rows[-1]["fpr"] == 1.0
    # every distinct negative value contributes exactly one firing operating point
    assert sum(1 for r in rows if r["fires"]) == len(np.unique(neg))


def test_n_firing_below_counts_the_operators_menu():
    rng = np.random.default_rng(6)
    rows = grid(np.round(_scores(rng, 200, 0.095), 9),
                np.round(_scores(rng, 200, 0.275), 9))
    assert n_firing_below(rows, 0.05) == 0        # nothing at or below a 5% budget
    assert n_firing_below(rows, 0.095) == 1       # exactly the ceiling atom
    assert n_firing_below(rows, 1.0) == sum(1 for r in rows if r["fires"])


def test_upper_hull_is_concave_and_keeps_the_endpoints():
    xs = [0.0, 0.095, 0.215, 0.265, 1.0]
    ys = [0.0, 0.275, 0.445, 0.520, 1.0]
    hx, hy = _upper_hull(xs, ys)
    assert (hx[0], hy[0]) == (0.0, 0.0) and (hx[-1], hy[-1]) == (1.0, 1.0)
    slopes = [(hy[i + 1] - hy[i]) / (hx[i + 1] - hx[i]) for i in range(len(hx) - 1)]
    assert all(a >= b - 1e-12 for a, b in zip(slopes, slopes[1:])), \
        "the randomisation frontier must be concave"
    for x, y in zip(xs, ys):                       # no attainable point above the hull
        assert y <= np.interp(x, hx, hy) + 1e-12
