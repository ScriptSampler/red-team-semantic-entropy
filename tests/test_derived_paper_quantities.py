"""Tests for the derived-quantity registry -- most of which exist to prove it BITES.

The registry's whole value is that a green run means something. This repo has already been
caught once by a checker that reported OK on numbers it could not see (`check_population_labels.py`
was "silent on 5.0%, 2.0%, 3.0%, 14.8%, 20.0% and 27.8%, none of which are guarded ... It caught
nothing here and could not have"), and once by THIS script, which spent five days verifying that
`experiments.tex` says "roughly nine GPU-days" -- a phrase that file did not contain -- because
the paper side was a hard-coded dict compared against nothing.

So the central test here is mutation: perturb each registered number by one unit in the last
place the paper prints, and the run must go red. A registration that survives its own mutation
is decoration.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "derived_paper_quantities", ROOT / "scripts" / "derived_paper_quantities.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


D = _load()


@pytest.fixture(autouse=True)
def _no_writes(tmp_path, monkeypatch):
    """Never let a test overwrite the committed report."""
    monkeypatch.setattr(D, "RESULTS_DIR", tmp_path)


def run() -> int:
    return D.main(write=False, quiet=True)


# ======================================================================================
# The arithmetic itself.
# ======================================================================================
@pytest.mark.parametrize("k,n,pt,lo,hi", [
    (0, 200, 0.0, 0.0, 1.9),      # at-cap mass at N=40: the structural zero
    (4, 200, 2.0, 0.8, 5.0),      # the cheapest firing threshold at N=40
    (12, 200, 6.0, 3.5, 10.2),    # what that threshold catches, hallucinating stratum
    (10, 200, 5.0, 2.7, 9.0),     # the achieved 5% operating point
    (19, 200, 9.5, 6.2, 14.4),    # the direct N=10 floor the paper keeps
    (55, 200, 27.5, 21.8, 34.1),  # hallucinating at the ln 10 cap
])
def test_wilson_reproduces_every_interval_the_paper_prints(k, n, pt, lo, hi):
    a, b = D.wilson(k, n)
    assert round(100 * k / n, 1) == pt
    assert (round(a, 1), round(b, 1)) == (lo, hi)


def test_wilson_is_not_the_normal_approximation():
    """The distinguishing case: a zero count. The normal interval collapses to [0, 0] and
    would have let `0.0\\% [0.0, 1.9]` through as `[0, 0]`."""
    lo, hi = D.wilson(0, 200)
    assert lo == 0.0
    assert 1.5 < hi < 2.5


@pytest.mark.parametrize("x,df,p", [
    (7.39, 9, 0.5966), (3.57, 7, 0.8276), (1.0, 1, 0.3173),
    (2.0, 2, 0.3679), (50.0, 30, 0.0122), (0.5, 4, 0.9735),
])
def test_chisq_sf_matches_a_reference(x, df, p):
    assert D.chisq_sf(x, df) == pytest.approx(p, abs=5e-4)


def test_chisq_sf_agrees_with_scipy_where_scipy_is_available():
    scipy_stats = pytest.importorskip("scipy.stats")
    for x, df in ((7.39, 9), (0.1, 3), (25.0, 12), (100.0, 60), (2.5, 5)):
        assert D.chisq_sf(x, df) == pytest.approx(scipy_stats.chi2.sf(x, df), rel=1e-9)


# ======================================================================================
# The guards bite.
# ======================================================================================
def test_the_repo_is_green_today():
    """Not the point of the file, but it pins today's state: if this goes red, a registered
    number moved, and the report says which."""
    assert run() == 0, "\n".join(D.PROBLEMS)


@pytest.mark.parametrize("key", sorted(D.CLAIMS))
def test_every_paper_claim_fails_when_its_literal_stops_appearing(key, monkeypatch):
    """A number that is silently reworded in the .tex must not survive as 'verified'."""
    c = D.CLAIMS[key]
    if not c.present:
        pytest.skip("absence claims are mutated the other way, below")
    broken = dict(D.CLAIMS)
    broken[key] = replace(c, literal=c.literal + " — NOT IN THE PAPER")
    monkeypatch.setattr(D, "CLAIMS", broken)
    assert run() == 1
    assert any(key in p and "PAPER" in p for p in D.PROBLEMS), D.PROBLEMS


@pytest.mark.parametrize("key", sorted(k for k, c in D.CLAIMS.items() if not c.present))
def test_every_absence_claim_fails_when_the_retired_literal_returns(key, monkeypatch):
    """The 1440 oracle count, the 9.9-point fall and the 'roughly nine GPU-days' phrase are
    held down by absence. Point them at a literal that IS present and they must fire."""
    broken = dict(D.CLAIMS)
    broken[key] = replace(D.CLAIMS[key], literal="the")
    monkeypatch.setattr(D, "CLAIMS", broken)
    assert run() == 1
    assert any(key in p and "contains again" in p for p in D.PROBLEMS), D.PROBLEMS


@pytest.mark.parametrize("i", range(len(D.INPUTS)))
def test_every_input_fails_when_its_artifact_stops_containing_the_literal(i, monkeypatch):
    broken = list(D.INPUTS)
    broken[i] = replace(broken[i], literal=broken[i].literal + " — NOT IN THE ARTIFACT")
    monkeypatch.setattr(D, "INPUTS", broken)
    assert run() == 1
    assert any("INPUT" in p for p in D.PROBLEMS), D.PROBLEMS


def test_a_missing_source_file_is_a_failure_not_a_skip():
    broken = list(D.INPUTS)
    broken[0] = replace(broken[0], source="results/does_not_exist.md")
    import unittest.mock as m
    with m.patch.object(D, "INPUTS", broken):
        assert run() == 1
    assert any("missing source" in p for p in D.PROBLEMS), D.PROBLEMS


# ======================================================================================
# THE MUTATION TEST. This is the one that says the registry is not decoration.
# ======================================================================================
def _derived() -> list[tuple[str, int]]:
    """(claim key, decimal places it is compared to). Recovered by running once."""
    D.main(write=False, quiet=True)
    return sorted(D.EXERCISED.items())


@pytest.mark.parametrize("key,dp", _derived())
def test_perturbing_any_derived_claim_turns_the_run_red(key, dp, monkeypatch):
    """One unit in the last place the check looks at. If the run stays green, the derivation
    for `key` is not actually comparing anything and its MATCHES is worthless.

    The perturbation must be tied to `dp`: an earlier version of this test nudged every claim
    by 1% of its value and passed thirteen claims that are compared to one decimal place,
    because 3.5 -> 3.535 still rounds to 3.5. A mutation smaller than the comparison's own
    precision proves nothing, and looked like proof."""
    c = D.CLAIMS[key]
    broken = dict(D.CLAIMS)
    broken[key] = replace(c, value=c.value + 1.5 * 10 ** (-dp))
    monkeypatch.setattr(D, "CLAIMS", broken)
    assert run() == 1, f"claim '{key}' can be moved by 1.5e-{dp} without the check noticing"
    assert any("DERIVATION" in p for p in D.PROBLEMS), D.PROBLEMS


# ======================================================================================
# Normalisation: tolerant of a reflow, intolerant of a rewording.
# ======================================================================================
def test_a_reflowed_paragraph_is_not_a_revision(tmp_path, monkeypatch):
    f = tmp_path / "x.tex"
    f.write_text("the floor is $2.0\\%$\n[$0.8$, $5.0$] at the top budget", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    D.PROBLEMS.clear()
    D.PaperClaim("t", 2.0, r"$2.0\%$ [$0.8$, $5.0$]", "x.tex").check()
    assert D.PROBLEMS == []


def test_a_reworded_number_is_a_revision(tmp_path, monkeypatch):
    f = tmp_path / "x.tex"
    f.write_text("the floor is $2.1\\%$ [$0.8$, $5.0$] at the top budget", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    D.PROBLEMS.clear()
    D.PaperClaim("t", 2.0, r"$2.0\%$ [$0.8$, $5.0$]", "x.tex").check()
    assert len(D.PROBLEMS) == 1 and "no longer contains" in D.PROBLEMS[0]


# ======================================================================================
# Registration hygiene.
# ======================================================================================
def test_every_paper_claim_points_at_paper():
    for c in D.CLAIMS.values():
        assert c.source.startswith("paper/"), f"{c.name} is not a paper claim"


def test_no_input_is_sourced_to_a_log_rather_than_an_artifact():
    """The repaired defect, held down. The old 228 GPU-h input named `docs/critique_log.md`
    -- a running log, not a produced artifact -- which is how a dead anchor kept a green
    guard for five days. Inputs come from results/."""
    for i in D.INPUTS:
        assert i.source.startswith("results/"), (
            f"input '{i.name}' is sourced to {i.source}; a log entry is not an artifact")


def test_the_retired_gpu_anchor_is_not_an_input_any_more():
    assert not any("228" in str(i.value) or "228 GPU-h" in i.literal for i in D.INPUTS)


def test_every_claim_name_is_unique_and_every_input_name_is_unique():
    assert len({i.name for i in D.INPUTS}) == len(D.INPUTS)
    assert len({c.name for c in D.CLAIMS.values()}) == len(D.CLAIMS)


def test_the_coverage_split_is_reported_not_hidden():
    """A registry that quietly counts pinned-only claims as checked would overstate itself.
    The report must say how many of each there are."""
    D.main(write=False, quiet=True)
    assert 0 < len(D.EXERCISED) < len(D.CLAIMS)


def test_the_gpu_cost_chain_is_the_measured_one_and_reproduces_the_paper():
    src = {i.name: i.value for i in D.INPUTS}
    repriced = (src["judge evaluations per target at K=180"]
                * src["measured seconds per clustering, deployed run"]
                * D.N_JUDGE_TARGETS / 3600.0)
    assert round(repriced) == 99, repriced
    assert round(228 / repriced, 1) == 2.3
    assert round(repriced / 24, 1) == 4.1


def test_the_fall_is_the_current_value_and_not_the_retired_one():
    src = {i.name: i.value for i in D.INPUTS}
    fall = src["subset-averaged replay floor at N=10 (percent)"] - 2.0
    assert round(fall, 1) == 10.0, "the -9.9 fall is superseded; see replay_control.md 2b"


def test_the_variance_identity_closes_at_both_budgets():
    src = {i.name: i.value for i in D.INPUTS}
    for tag in ("N=10", "N=20"):
        q = src[f"{tag} question component, sd in rate points"]
        s = src[f"{tag} subset-draw component, sd in rate points"]
        pbar = src[f"subset-averaged replay floor at {tag} (percent)"] / 100
        binom = 100 * math.sqrt(pbar * (1 - pbar) / D.N_STRATUM)
        assert math.hypot(s, q) == pytest.approx(binom, abs=1e-3), tag
