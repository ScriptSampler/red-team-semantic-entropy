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
def _paper_text() -> str:
    """paper/ as one whitespace-normalised string, so a LaTeX reflow is not a revision.

    Read here rather than through `D` because the point of the tests below is to check the
    registry AGAINST the .tex, and a helper borrowed from the thing under test would let it
    agree with itself."""
    files = (sorted((ROOT / "paper").glob("*.tex"))
             + sorted((ROOT / "paper" / "sections").glob("*.tex")))
    assert files, "no .tex found under paper/"
    return " ".join(" ".join(f.read_text(encoding="utf-8").split()) for f in files)


@pytest.mark.parametrize("k,n,pt,lo,hi", [
    (0, 200, 0.0, 0.0, 1.9),      # at-cap mass at N=40: the structural zero
    (12, 200, 6.0, 3.5, 10.2),    # what the cheapest threshold catches, hallucinating
    (10, 200, 5.0, 2.7, 9.0),     # the achieved 5% operating point
    (19, 200, 9.5, 6.2, 14.4),    # the direct N=10 floor the paper keeps
    (55, 200, 27.5, 21.8, 34.1),  # hallucinating at the ln 10 cap
])
def test_wilson_reproduces_every_interval_the_paper_prints(k, n, pt, lo, hi):
    r"""The arithmetic AND the premise.

    THE DEFECT THIS SECOND HALF EXISTS FOR (2026-08-19). This list used to carry
    `(4, 200, 2.0, 0.8, 5.0)` with the comment "the cheapest firing threshold at N=40",
    and it went on asserting that Wilson [0.8, 5.0] is "an interval the paper prints" for a
    full round after `results/n40_floor_estimator_ruling.md` withdrew it and the paper
    stopped printing it. It could not have noticed: every assertion was arithmetic on
    `D.wilson()`, which is a property of the binomial and not of the paper, so the case was
    permanently green -- the withdrawn choice encoded as a numeric tuple rather than as a
    string, where none of the .tex-scanning guards could see it.

    So each case now has to be FOUND in paper/. A tuple that names a rendering the paper
    does not carry is the same defect whichever direction it points."""
    a, b = D.wilson(k, n)
    assert round(100 * k / n, 1) == pt
    assert (round(a, 1), round(b, 1)) == (lo, hi)
    lit = " ".join(("$%.1f\\%%$ [$%.1f$, $%.1f$]" % (pt, lo, hi)).split())
    assert lit in _paper_text(), (
        f"this case claims the paper prints {lit!r} for {k}/{n}, and it does not. Either "
        f"the paper was reworded -- update the literal -- or the number was withdrawn, in "
        f"which case the case belongs in the withdrawal test below and not in a list "
        f"headed 'every interval the paper prints'.")


def test_the_n40_floor_count_carries_no_interval_in_the_paper():
    r"""4/200: the case that was demoted out of the list above, and the reason it was.

    Both candidate intervals were withdrawn because the estimand is NOT IDENTIFIED at
    n=200: once the ceiling atom empties, whether the pool's top rung is the population's
    top rung cannot be decided from the sample, and the two readings are two orders of
    magnitude apart. That argument uses no population model. The coverage figures do --
    under the calibrated Ewens fit Wilson covers 53.67% and the question bootstrap 0.00%
    at nominal 95%; under the zero branch, 95.06% and 100% (ruling sec. 8.4) -- so neither
    pair may be quoted without naming its population. The paper prints the point and
    nothing else.

    The arithmetic is still pinned, at both precisions, for two reasons: a number withdrawn
    on evidence must stay re-examinable, and `scripts/check_population_labels.py` arms
    patterns against these exact digit strings, so if Wilson's endpoints on this count ever
    moved, those patterns would be guarding the wrong renderings."""
    lo, hi = D.wilson(4, 200)
    assert (round(lo, 1), round(hi, 1)) == (0.8, 5.0)
    assert (round(lo, 4), round(hi, 4)) == (0.7804, 5.0287)

    paper = _paper_text()
    assert " ".join(r"a measured $2.0\%$ at $N{=}40$".split()) in paper, (
        "the paper no longer prints the N=40 floor as a bare point; if the ruling changed, "
        "it changed in results/n40_floor_estimator_ruling.md first")
    for banned in (r"$2.0\%$ [$0.8$, $5.0$]", r"[$0.78$, $5.03$]", r"[$0.5$, $4.0$]",
                   "0.7804", "5.0287", "0.78037", "5.02866"):
        assert " ".join(banned.split()) not in paper, (
            f"paper/ has started printing {banned!r} again. That is a WITHDRAWN interval "
            f"for the N=40 floor -- see results/n40_floor_estimator_ruling.md. Both "
            f"candidates failed on coverage; the interval that survives at that budget is "
            f"the at-cap mass, 0/200 = 0.0% [0.0, 1.9].")


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


# ======================================================================================
# THE ANCHOR ON THE ABSENCE GUARDS (2026-08-31)
#
# `PaperClaim(..., "8.8", DISC, present=False)` failed the suite against a correct number:
# the paper gained a prevalence sentence printing a natural hallucination rate of
# $28.8\%$, and `8.8` is three characters inside `28.8`. The guard did what it was written
# to do, and what it was written to do could not tell a retired standalone value from a
# digit run inside another number.
#
# THESE TESTS ARE THE POINT OF THAT FIX, not a formality around it. An anchor is a claim
# about a regex, and this file's whole thesis is that a claim nothing mutates is
# decoration. So every anchored registration is probed in ten renderings, controlled
# against five near-misses, and then both lookarounds are deleted in turn and required to
# take a named test red with them.
# ======================================================================================
_ANCHORED = sorted(k for k, c in D.CLAIMS.items() if c.standalone)


def _against(tmp_path, monkeypatch, claim, body: str) -> list[str]:
    """Run ONE claim against a synthetic file holding exactly `body`, and return what it
    said. Synthetic because a probe has to control the text: paper/ is edited concurrently
    and cannot be made to contain `8.85` on demand."""
    p = tmp_path / claim.source
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    D.PROBLEMS.clear()
    claim.check()
    return list(D.PROBLEMS)


# The markups a retired number could come back in. Each is a real shape from this paper:
# bare in prose, in math mode, negated (the legs are printed as falls), as a percentage,
# emphasised, inside a bracketed interval, reflowed across a line break, and ending a
# sentence. The last is the one a naive right-hand guard of `(?![\d.])` would have lost.
_RENDERINGS = [
    "the retired leg was {v} points",
    "the retired leg was ${v}$ points",
    "a fall of $-{v}$ points",
    "a fall of -{v} points",
    "${v}\\%$ of the correct stratum",
    "\\textbf{{{v}}} points",
    "[$6.8$, ${v}$]",
    "a fall of\n{v}\npoints",
    "the retired leg was {v}.",
    "{v}~points",
]


@pytest.mark.parametrize("key", _ANCHORED)
@pytest.mark.parametrize("markup", _RENDERINGS)
def test_an_anchored_absence_claim_still_catches_its_value_in_any_markup(
        key, markup, tmp_path, monkeypatch):
    """THE PROBE. Anchoring must not have bought quiet by narrowing what counts as a
    return. Every one of these is the retired value standing alone, and the guard owes a
    finding on all of them."""
    c = D.CLAIMS[key]
    body = markup.format(v=c.literal)
    problems = _against(tmp_path, monkeypatch, c, body)
    assert problems, (
        f"claim '{key}' did not catch its own retired value {c.literal!r} in {body!r}. "
        f"The anchor has narrowed the guard past the renderings the paper actually uses.")
    assert "contains again" in problems[0], problems


# The near-misses. `2{v}` is the shape that fired the false positive (`28.8` inside the
# prevalence sentence); `1{v}` and `10{v}` are the same defect one and two digits over;
# `{v}5` and `{v}1` are the retired value with another significant figure after it, which
# is a different number and in one case -- 8.86, the EXACT 10 -> 20 leg -- is the LIVE
# number this very claim exists to protect.
#
# `0.{v}` IS HERE BECAUSE A MUTATION RUN SAID IT WAS MISSING. With the first five, deleting
# the `.` from ANCHOR_LEFT changed the behaviour of nothing in this file: every test still
# passed, so a character of the anchor was going unchecked, which is the exact shape of
# defect this module exists to refuse. The `.` earns its place on `1440` -- without it the
# guard fires on a probability of `0.1440`, and four-decimal renderings are everywhere in
# this repo -- and the case is now controlled for all nine.
_NEAR_MISSES = ["2{v}", "1{v}", "10{v}", "{v}5", "{v}1", "0.{v}"]


@pytest.mark.parametrize("key", _ANCHORED)
@pytest.mark.parametrize("near", _NEAR_MISSES)
def test_an_anchored_absence_claim_ignores_a_longer_number_containing_it(
        key, near, tmp_path, monkeypatch):
    """THE CONTROL. A digit string inside another number is not the retired value, and a
    guard that says otherwise blocks the paper from printing arithmetic."""
    c = D.CLAIMS[key]
    body = "the paper prints $" + near.format(v=c.literal) + "\\%$ here"
    assert not _against(tmp_path, monkeypatch, c, body), (
        f"claim '{key}' fired on {near.format(v=c.literal)!r}, which contains its literal "
        f"{c.literal!r} but is not that number. This is the 28.8-versus-8.8 defect.")


def test_the_exact_case_that_failed_the_suite(tmp_path, monkeypatch):
    """Named, because a regression here is not an abstraction. The prevalence sentence and
    the retired leg, in one file, which is the situation in discussion.tex today."""
    c = D.CLAIMS["leg_10_20_mc_retired"]
    live = (r"its natural hallucination rate of $28.8\%$ and the exact leg of $8.86$ "
            r"and a floor of $18.8\%$")
    assert not _against(tmp_path, monkeypatch, c, live)
    assert _against(tmp_path, monkeypatch, c, live + r" and a retired $8.8$ points"), (
        "the retired 8.8 came back beside the numbers it collides with and was not caught")


def test_a_retired_count_is_caught_when_it_returns_as_a_denominator(tmp_path, monkeypatch):
    """Why the left lookbehind is `(?<![\\d.])` and not the `(?<![/\\d.])` that
    `scripts/check_population_labels.py` uses for most of its numeric rules.

    That file's `/` is deliberate and correct THERE: its rules match a numerator and must
    not let a denominator pose as a standalone count. This guard has the opposite job, and
    the retired substring-oracle count is live as a denominator in three artifacts:
    `436/1440`, `437/1440` (results/cluster_count_bound.md) and `151/1440`
    (results/likelihood_weight_sensitivity.md), against the paper's own `150/1424`. A
    `150/1440` reaching limitations.tex is the likeliest way that number comes back, and
    with `/` in the lookbehind it would read as silence."""
    c = D.CLAIMS["substring_oracle_count_absent"]
    assert _against(tmp_path, monkeypatch, c, "the floor is $150/1440 = 10.4\\%$")
    # ...and the thing the anchor was added for is still refused: 14,400 is the scored-
    # children count of the budget argument, and unseparated it contains 1440.
    assert not _against(tmp_path, monkeypatch, c,
                        "only $4703$ of $14400$ scored children were ever checked")


def test_a_four_decimal_probability_is_not_a_retired_count(tmp_path, monkeypatch):
    """Why the left lookbehind carries `.` as well as `\\d`, on the one claim where the
    difference is reachable.

    `0.1440` contains `1440` and is preceded by a decimal point rather than by a digit, so
    only the `.` in `(?<![\\d.])` keeps this guard off it. That matters here specifically:
    this repo prints four-decimal probabilities everywhere (`0.7804`, `0.2726`, `0.0163`),
    so a `0.1440` is an ordinary thing for a paper sentence to acquire. A mutation run is
    what found this missing -- deleting the `.` broke no test at all until this case and
    the `0.{v}` control above were added."""
    c = D.CLAIMS["substring_oracle_count_absent"]
    assert not _against(tmp_path, monkeypatch, c, "a weight of $0.1440$ on that term")


# ======================================================================================
# MUTATION: break the anchor, and a NAMED test must go red.
# ======================================================================================
def test_deleting_the_left_lookaround_reopens_the_false_positive(monkeypatch):
    """Mutation on ANCHOR_LEFT, run against the REAL paper, because the collision is real:
    discussion.tex prints $28.8\\%$ today, so an unanchored `8.8` fails the whole run. If
    this test ever passes, the left guard has stopped doing anything."""
    monkeypatch.setattr(D, "ANCHOR_LEFT", "")
    assert run() == 1, "ANCHOR_LEFT is not load-bearing; the anchor is decoration"
    assert any("leg_10_20_mc_retired" in p and "contains again" in p for p in D.PROBLEMS), (
        D.PROBLEMS)


def test_deleting_the_right_lookaround_reopens_the_live_number(tmp_path, monkeypatch):
    """Mutation on ANCHOR_RIGHT, on the case that matters most: without it the guard on the
    retired 8.8 fires on 8.86, which is the EXACT leg the claim exists to defend."""
    c = D.CLAIMS["leg_10_20_mc_retired"]
    body = r"the exact leg is $-8.86$ points"
    assert not _against(tmp_path, monkeypatch, c, body)
    monkeypatch.setattr(D, "ANCHOR_RIGHT", "")
    assert _against(tmp_path, monkeypatch, c, body), (
        "ANCHOR_RIGHT is not load-bearing; it is the only thing keeping the guard off the "
        "live 8.86 that replaced the retired 8.8")


def test_dropping_the_anchor_from_a_claim_reopens_the_false_positive(monkeypatch):
    """Mutation on the REGISTRATION rather than on the regex: the flag itself must be what
    switches the behaviour, not something that merely correlates with it."""
    broken = dict(D.CLAIMS)
    broken["leg_10_20_mc_retired"] = replace(
        D.CLAIMS["leg_10_20_mc_retired"], standalone=False)
    monkeypatch.setattr(D, "CLAIMS", broken)
    assert run() == 1
    assert any("leg_10_20_mc_retired" in p for p in D.PROBLEMS), D.PROBLEMS


# ======================================================================================
# Registration hygiene: the flag must not be something anyone has to remember.
# ======================================================================================
def test_every_bare_numeric_absence_claim_is_anchored():
    """THE RULE THAT MAKES THE FIX PERMANENT.

    A bare-substring absence guard on a short numeric string is a defect CLASS, not a
    single instance: `8.8` is inside `28.8`, `3.0` inside `13.0`, `1440` inside `14400`,
    and the paper gains numbers every week. Fixing the one that fired and leaving eight
    others armed would just move the failure to the next sentence someone writes. So the
    requirement is checked over the whole registry rather than remembered claim by claim.

    A literal that carries its own delimiters (`[$0.78$, $5.03$]`) needs no anchor and does
    not have to take one; only a literal that is nothing but digits does."""
    unanchored = sorted(
        f"{c.name} ({c.literal!r} in {c.source})"
        for c in D.CLAIMS.values()
        if not c.present and D._is_bare_numeric(c.literal) and not c.standalone)
    assert not unanchored, (
        "these absence claims hold down a bare numeric literal by SUBSTRING, so each one "
        "fires on the next number the paper gains that happens to contain those digits:\n  "
        + "\n  ".join(unanchored)
        + "\nPass standalone=True; see the ANCHORING block in "
          "scripts/derived_paper_quantities.py.")


def test_the_anchor_is_only_used_where_the_literal_is_a_whole_number():
    """The other direction. `standalone=True` on a literal with prose in it would be a
    registration that reads as stricter than it is."""
    for c in D.CLAIMS.values():
        if c.standalone:
            assert D._is_bare_numeric(c.literal), (
                f"{c.name} is anchored as a whole number but its literal {c.literal!r} is "
                f"not one")


def test_the_anchored_claims_are_the_nine_the_sweep_found():
    """The census, pinned. Eight of these nine were LATENT: only `leg_10_20_mc_retired` had
    actually fired, and the other eight were each one new paper number away from firing.
    Pinning the set means a tenth cannot join it without somebody reading this list."""
    assert _ANCHORED == sorted([
        "fall_ci_lo_retired",
        "fall_points_retired",
        "leg_10_20_mc_retired",
        "n40_floor_503_retired_concl",
        "n40_floor_503_retired_disc",
        "n40_floor_503_retired_main",
        "replay10_floor_retired",
        "replay20_floor_retired",
        "substring_oracle_count_absent",
    ])


def test_the_report_says_which_claims_are_matched_as_whole_numbers(tmp_path):
    """A report that printed each literal without saying how it is matched would let a
    reader believe every absence guard is the same strength. They are not, and the split is
    the kind of thing this file already reports for derived-versus-pinned."""
    D.main(write=True, quiet=True)
    report = (tmp_path / "derived_paper_quantities.md").read_text(encoding="utf-8")
    assert "| matched as |" in report
    for key in _ANCHORED:
        row = next(ln for ln in report.splitlines() if ln.startswith(f"| {key} |"))
        assert "whole number" in row, row
    subs = next(ln for ln in report.splitlines()
                if ln.startswith("| n40_floor_wilson_retired_disc |"))
    assert "substring" in subs, subs


@pytest.mark.parametrize("key", _ANCHORED)
def test_a_zero_padded_rendering_is_not_caught_and_that_is_recorded(
        key, tmp_path, monkeypatch):
    """NOT A PASSING GRADE: the honest boundary of the anchor, written down so that it is a
    known limit rather than a surprise.

    `8.80` is the retired 8.8 carrying a decimal place the paper does not use, and `(?!\\d)`
    declines it. The trade is forced: tolerating a trailing zero is exactly what would let
    `1440` match `14400` again, which is the collision this anchor exists for. The other
    file met the same boundary on `\\b0\\.78(?!\\d)` and closed it by arming the fuller
    rendering as a rule of its own, which is the route open here if a padded rendering ever
    turns up in paper/. If this test starts FAILING, that has happened; read it as news and
    not as a break."""
    c = D.CLAIMS[key]
    assert not _against(tmp_path, monkeypatch, c, f"the value is ${c.literal}0$ here")
