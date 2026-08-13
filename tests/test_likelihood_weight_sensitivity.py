"""The likelihood re-weighting claim, asserted as arithmetic rather than as a data readout.

`results/likelihood_weight_sensitivity.md` is a reconstruction of a simulation whose code
was never committed, so its warrant has to be in the harness, not in the numbers. The
measured rows need the WSL sample cache; none of the load-bearing statements do, and all
of them are tested here on synthetic cluster structure:

  1. THE COLLAPSE. At s=0 the Eq. (5) re-weighting must be IDENTICALLY the discrete
     estimator, p(C_k) = n_k / N. This is the only thing that licenses reading the s>0
     rows as perturbations of the estimator the paper actually runs. It is checked
     against an independent entropy implementation, not against the script's own.
  2. THE HARNESS GATE ACTUALLY FIRES. `validate()` must raise on cached values that do
     not match. A validation step that cannot fail is decoration; this feeds it a
     corrupted cache and requires SystemExit.
  3. SHIFT INVARIANCE. Eq. (5) normalises, so adding a constant to every log-weight must
     leave the entropy unchanged. This is what makes "only the SPREAD s matters" true,
     and it is the reason a simulated l with arbitrary mean is legitimate.
  4. THE ATOM DIES. The report's central claim: at any spread large enough to exceed the
     comparison tolerance, no question sits exactly at log N and the achievable-FPR floor
     is exactly 1/n. Asserted on a population built to be ALL at-cap at s=0, which is the
     hardest case for the claim.
  5. rho=1 IS CONSTANT-WITHIN-CLUSTER, and still does not restore the atom -- the
     modelling axis added because i.i.d. weights were the reconstruction's weakest
     assumption.

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

from likelihood_weight_sensitivity import (                          # noqa: E402
    ATOM_TOL, CAP, Population, crossover, draw_logw, floor_stats, validate,
)

N = 10


def ref_entropy(counts) -> float:
    """Discrete semantic entropy from cluster COUNTS, written independently of the
    script under test so a shared bug cannot make test 1 pass."""
    p = np.asarray(counts, dtype=float)
    p = p[p > 0] / p.sum()
    return float(-(p * np.log(p)).sum())


def make_pop(partitions_, name="synthetic") -> Population:
    """Build a Population from integer partitions of N, with cached discrete entropies."""
    assign, cached = [], []
    for part in partitions_:
        assert sum(part) == N, "a cluster-size distribution must partition N"
        a = []
        for k, size in enumerate(part):
            a.extend([k] * size)
        assign.append(a)
        cached.append(ref_entropy(part))
    return Population(name, [f"q{i}" for i in range(len(assign))],
                      np.array(assign, dtype=np.int64), np.array(cached))


ALL_AT_CAP = [[1] * 10] * 40                       # every question saturated: worst case
MIXED = [[1] * 10, [2, 2, 2, 2, 2], [5, 5], [10], [3, 3, 2, 1, 1], [4, 3, 2, 1], [8, 2]]


# ------------------------------------------------------------------ 1. the collapse
def test_s0_is_exactly_the_discrete_estimator():
    pop = make_pop(MIXED)
    got = pop.entropies(np.zeros((pop.Q, pop.N)))
    for h, part in zip(got, MIXED):
        assert abs(h - ref_entropy(part)) < 1e-15
    assert validate(pop).startswith("max |H_eq5(s=0)")


def test_s0_matches_cap_for_the_uniform_partition():
    pop = make_pop([[1] * 10])
    assert abs(float(pop.entropies(np.zeros((1, N)))[0]) - CAP) < 1e-15


# ------------------------------------------------- 2. the gate is capable of failing
def test_validate_raises_when_the_cache_disagrees():
    pop = make_pop(MIXED)
    pop.cached = pop.cached + 1e-6                 # a cache that is not what we compute
    with pytest.raises(SystemExit, match="HARNESS CHECK FAILED"):
        validate(pop)


def test_validate_raises_on_a_shifted_at_cap_rate():
    """A perturbation too small for the 1e-12 value check but large enough to move a
    headline rate must still be caught by the second half of validate()."""
    pop = make_pop(ALL_AT_CAP[:4] + MIXED)
    pop.cached = pop.cached.copy()
    pop.cached[0] -= 1e-6                          # drops one question out of the atom
    with pytest.raises(SystemExit, match="HARNESS CHECK FAILED"):
        validate(pop)


# ------------------------------------------------------------- 3. shift invariance
def test_entropy_is_invariant_to_a_constant_added_to_every_log_weight():
    pop = make_pop(MIXED)
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 0.7, size=(pop.Q, pop.N))
    for shift in (-50.0, -1.0, 3.0, 200.0):
        assert np.allclose(pop.entropies(base), pop.entropies(base + shift), atol=1e-12)


def test_large_spread_does_not_overflow():
    """Raw (un-length-normalised) log-likelihoods span tens of nats; the per-question
    max-subtraction has to keep exp() finite there."""
    pop = make_pop(MIXED)
    rng = np.random.default_rng(1)
    h = pop.entropies(rng.normal(-400.0, 60.0, size=(pop.Q, pop.N)))
    assert np.all(np.isfinite(h)) and np.all(h >= -1e-12)


# ------------------------------------------------------------------ 4. the atom dies
def test_atom_and_floor_survive_at_s_zero():
    pop = make_pop(ALL_AT_CAP)
    h = np.round(pop.entropies(np.zeros((pop.Q, pop.N))), 9)
    assert float((h >= CAP - ATOM_TOL).mean()) == 1.0
    assert floor_stats(h)["floor"] == 1.0          # every negative tied at the maximum


@pytest.mark.parametrize("s", [0.01, 0.1, 0.5, 1.0])
def test_atom_and_floor_die_at_any_appreciable_spread(s):
    pop = make_pop(ALL_AT_CAP)
    rng = np.random.default_rng(7)
    h = np.round(pop.entropies(draw_logw(rng, pop, s, rho=0.0)), 9)
    assert float((h >= CAP - ATOM_TOL).mean()) == 0.0, "a real-valued weighting kept an atom"
    assert floor_stats(h)["floor"] == pytest.approx(1.0 / pop.Q), "floor is not 1/n"


def test_eq5_never_exceeds_the_log_n_ceiling():
    """The ceiling is the one claim that DOES transfer; if a weighting broke it the
    paper's shared-bound argument would be wrong."""
    pop = make_pop(MIXED + ALL_AT_CAP[:5])
    rng = np.random.default_rng(3)
    for s in (0.0, 0.1, 1.0, 5.0):
        h = pop.entropies(draw_logw(rng, pop, s, rho=0.0))
        assert np.all(h <= math.log(N) + 1e-12)


# --------------------------------------------------------------- 5. the rho axis
def test_rho_one_makes_weights_constant_within_a_cluster():
    pop = make_pop(MIXED)
    rng = np.random.default_rng(11)
    logw = draw_logw(rng, pop, s=0.8, rho=1.0)
    for q in range(pop.Q):
        for k in np.unique(pop.assign[q]):
            vals = logw[q][pop.assign[q] == k]
            assert np.allclose(vals, vals[0])


def test_rho_one_still_kills_the_atom():
    """Constant-within-cluster weights give p(C_k) proportional to n_k * w_k, which is
    still not n_k / N -- correlation is not a route back to the atom."""
    pop = make_pop(ALL_AT_CAP)
    rng = np.random.default_rng(13)
    h = np.round(pop.entropies(draw_logw(rng, pop, s=0.3, rho=1.0)), 9)
    assert float((h >= CAP - ATOM_TOL).mean()) == 0.0


def test_rho_zero_leaves_weights_independent_within_a_cluster():
    pop = make_pop([[10]])                         # one cluster: rho=0 must NOT tie them
    rng = np.random.default_rng(17)
    logw = draw_logw(rng, pop, s=0.8, rho=0.0)
    assert len(np.unique(np.round(logw[0], 9))) == N


# ------------------------------------------------------------------ report helpers
def test_crossover_interpolates_the_half_life():
    rows = [{"s": 0.0, "x": 1.0}, {"s": 1.0, "x": 1.0}, {"s": 2.0, "x": 0.0}]
    assert crossover(rows, "x", 1.0) == pytest.approx(1.5)


def test_crossover_returns_none_when_the_statistic_never_halves():
    rows = [{"s": 0.0, "x": 1.0}, {"s": 1.0, "x": 0.9}]
    assert crossover(rows, "x", 1.0) is None


def test_floor_stats_reports_the_grid_and_the_eps_floors():
    neg = np.array([2.0, 2.0, 2.0, 1.0, 0.5])
    fs = floor_stats(neg)
    assert fs["floor"] == pytest.approx(0.6)       # three of five tied at the maximum
    assert fs["grid"] == 3                         # three distinct thresholds that fire
    assert fs["eps0.01"] == pytest.approx(0.6)
    assert fs["eps0.139"] == pytest.approx(0.6)
