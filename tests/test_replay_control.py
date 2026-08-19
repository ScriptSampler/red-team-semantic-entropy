"""The replay control's arithmetic, pinned.

`scripts/replay_control.py` decides whether two blocked paper claims survive, so the
statistics it computes have to be the ones it says they are. What is asserted here:

  1. THE FLOOR IS THE FIRST FIRING POINT, not the ceiling atom. This is the exact defect
     the report identifies in `results/n_scaling_grid.md`: the two agree while some
     negative sits at the ln N cap and diverge when none does, and the divergent case is
     the one the published table gets wrong.
  2. THE ROC PIECES. AUROC agrees with sklearn on tied, atomic scores (semantic entropy is
     mostly atoms, so a tie convention that drifts would move every number in the report);
     the band pAUC is the MEAN TPR in the band, so a chance detector scores the band
     midpoint and not 0.5 -- the mislabel section 4 of the report is about.
  3. THE RANDOMISED FRONTIER dominates the deterministic points and is concave, which is
     what licenses comparing budgets whose achievable grids do not line up.
  4. THE POISSON-BINOMIAL null: exact against a brute-force convolution, exact against the
     binomial when the probabilities are equal, and -- the property that makes it the
     sharp test rather than the forgiving one -- heterogeneity shrinks its variance.
  5. THE REPORT DOES NOT COMMIT THE ERROR IT EXISTS TO CORRECT. Section 5 below is the
     durable half of the 2026-08-19 fix: a directional claim may not be asserted on an
     interval that covers zero, and a BLOCKED claim may not be re-entered with its sign
     flipped. Both are checked mechanically -- the first as a property of
     `RC.directional_verdict` over the whole (d, lo, hi) plane, the second as a grep of
     the GENERATED report for the specific constructions that were caught in review.

CPU only: no GPU, no model, no sample cache, no network. Nothing here reads the Week-4
cache, so these run anywhere.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import replay_control as RC                                             # noqa: E402
from se.stats import attainable_fprs                                    # noqa: E402


# ----------------------------------------------------------------- 1. the floor column
def test_floor_is_the_ceiling_atom_when_the_cap_is_occupied():
    """N=10 case: 3 of 20 negatives sit at ln 10, so both readings give 15%."""
    neg = np.array([math.log(10)] * 3 + [1.0] * 17)
    assert RC.min_nonzero_fpr(neg) == pytest.approx(3 / 20)
    assert RC.ceiling_atom(neg, 10) == 3


def test_floor_diverges_from_the_ceiling_atom_when_the_cap_is_empty():
    """The N=40 case, and the defect in the published grid: no negative reaches ln 40, so
    the ceiling atom is 0 while the cheapest alarm an operator can buy is 4/200."""
    neg = np.array([2.5] * 4 + [1.0] * 196)
    assert RC.ceiling_atom(neg, 40) == 0
    assert RC.min_nonzero_fpr(neg) == pytest.approx(4 / 200)
    # ... and the "next FPR" is the SECOND firing point, not the second thing after zero
    fprs = sorted(RC.firing_fprs(neg))
    assert fprs[0] == pytest.approx(4 / 200)
    assert fprs[1] == pytest.approx(200 / 200)


def test_firing_fprs_agree_with_the_projects_attainable_grid():
    rng = np.random.default_rng(0)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=60), 9)
    vals, fprs = attainable_fprs(neg)
    theirs = sorted(float(f) for v, f in zip(vals, fprs) if np.isfinite(v))
    assert sorted(RC.firing_fprs(neg)) == pytest.approx(theirs)


# --------------------------------------------------------------------- 2. the ROC pieces
def test_auroc_matches_sklearn_on_heavily_tied_scores():
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(7)
    for _ in range(20):
        neg = rng.choice([0.0, 0.7, 1.1, 2.3], size=80)
        pos = rng.choice([0.0, 0.7, 1.1, 2.3], size=80)
        y = np.concatenate([np.zeros(80), np.ones(80)])
        assert RC.auroc(neg, pos) == pytest.approx(
            float(roc_auc_score(y, np.concatenate([neg, pos]))), abs=1e-12)


def test_auroc_is_one_half_when_the_score_is_constant():
    """Every pair is a tie, and ties count 0.5 -- the case a ceiling atom drives."""
    c = np.full(50, 2.3)
    assert RC.auroc(c, c.copy()) == pytest.approx(0.5)


def test_pauc_band_is_mean_tpr_so_chance_is_the_band_midpoint():
    """A chance detector scores (lo+hi)/2 in every band, NOT 0.5. The published claim
    review labels this quantity '0.5 = chance within the band'; it is not."""
    rng = np.random.default_rng(3)
    s = rng.normal(size=4000)
    fx, fy = RC.roc_curve_points(s[:2000], s[2000:])
    for lo, hi in ((0.0, 0.05), (0.0, 0.10), (0.20, 0.50), (0.50, 1.0)):
        assert RC.pauc_band(fx, fy, lo, hi) == pytest.approx((lo + hi) / 2, abs=0.03)


def test_pauc_over_the_whole_range_is_the_auroc():
    rng = np.random.default_rng(11)
    neg = rng.normal(size=300)
    pos = rng.normal(loc=0.8, size=300)
    fx, fy = RC.roc_curve_points(neg, pos)
    assert RC.pauc_band(fx, fy, 0.0, 1.0) == pytest.approx(RC.auroc(neg, pos), abs=2e-3)


# ------------------------------------------------------------ 3. the randomised frontier
def test_hull_dominates_every_deterministic_point_and_is_concave():
    rng = np.random.default_rng(5)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200), 9)
    pos = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200, p=[.1, .2, .3, .4]), 9)
    fx, fy = RC.deterministic_points(neg, pos)
    hull = RC.upper_hull(fx, fy)
    for x, y in zip(fx, fy):
        assert RC.tpr_matched(fx, fy, float(x)) >= y - 1e-12
    slopes = [(hull[i + 1][1] - hull[i][1]) / (hull[i + 1][0] - hull[i][0])
              for i in range(len(hull) - 1) if hull[i + 1][0] > hull[i][0]]
    assert all(a >= b - 1e-12 for a, b in zip(slopes, slopes[1:]))


def test_at_most_never_exceeds_its_budget_and_flags_nothing_when_it_cannot():
    """The degenerate case the whole floor finding is about: a 15% atom at the top means
    no firing threshold honours a 10% budget, and the honest answer is 0% and no alarms."""
    neg = np.array([math.log(10)] * 30 + [1.0] * 170)
    pos = np.array([math.log(10)] * 100 + [1.0] * 100)
    fx, fy = RC.deterministic_points(neg, pos)
    assert RC.achieved_at_most(fx, 0.10) == pytest.approx(0.0)
    assert RC.tpr_at_most(fx, fy, 0.10) == pytest.approx(0.0)
    assert RC.achieved_at_most(fx, 0.20) == pytest.approx(0.15)


# --------------------------------------------------------------- 4. the Poisson-binomial
def test_poisson_binomial_reduces_to_the_binomial_when_p_is_constant():
    from scipy.stats import binom
    ps = np.full(40, 0.3)
    got = RC.poisson_binomial_pmf(ps)
    assert got.sum() == pytest.approx(1.0)
    assert got == pytest.approx(binom.pmf(np.arange(41), 40, 0.3), abs=1e-12)


def test_poisson_binomial_matches_brute_force_enumeration():
    ps = np.array([0.05, 0.4, 0.9, 0.62, 0.11])
    exact = np.zeros(len(ps) + 1)
    for mask in range(1 << len(ps)):
        pr = 1.0
        k = 0
        for i, p in enumerate(ps):
            if mask >> i & 1:
                pr *= p
                k += 1
            else:
                pr *= 1 - p
        exact[k] += pr
    assert RC.poisson_binomial_pmf(ps) == pytest.approx(exact, abs=1e-12)


def test_heterogeneous_probabilities_shrink_the_variance():
    """Why the exact null is the SHARP test and a binomial on the mean would be lax: the
    per-question ceiling probabilities are spread from ~0 to ~1, and that spread cuts the
    variance of their sum."""
    spread = np.concatenate([np.full(100, 0.02), np.full(100, 0.22)])
    flat = np.full(200, spread.mean())
    v_spread = float((spread * (1 - spread)).sum())
    v_flat = float((flat * (1 - flat)).sum())
    assert v_spread < v_flat


# ----------------------------------------------------------------------- the stat pack
def test_stat_pack_is_internally_consistent():
    rng = np.random.default_rng(13)
    neg = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200), 9)
    pos = np.round(rng.choice([0.0, 0.7, 1.4, 2.3], size=200, p=[.1, .2, .3, .4]), 9)
    pk = RC.stat_pack(neg, pos)
    assert pk["floor"] == pytest.approx(RC.min_nonzero_fpr(neg))
    assert pk["auroc"] == pytest.approx(RC.auroc(neg, pos))
    # a deterministic point is always available on the frontier, so the randomised TPR at
    # a budget can never be below the deterministic one
    for f, dk, mk in ((0.05, "det05", "m05"), (0.10, "det10", "m10"), (0.20, "det20", "m20")):
        assert pk[mk] >= pk[dk] - 1e-12
        assert pk[f"ach{int(f * 100):02d}"] <= f + 1e-12


# ======================= 5. the report may not commit the error it exists to correct
#
# 2026-08-19. The report correctly refuted two overstated paper claims and then committed
# both error classes itself, in its own up-front summary -- the most liftable text in the
# file and one copy-paste from `paper/`:
#
#   * "the low-FPR pAUC does not fall with budget, it rises by +0.007", on a paired
#     interval of [-0.0677, +0.0768]. Accepting a null and then reading a direction off the
#     point estimate is exactly the error the report exists to correct, and it is the error
#     class that has already cost this project two withdrawn claims.
#   * "it buys almost nothing: TPR at a matched 5% is 12.3% vs 13.2%" -- a gate-BLOCKED
#     cross-budget TPR comparison, resurrected with the sign flipped and no interval. Its
#     sign turns on the pairing: deterministic-against-deterministic reverses it.
#
# The text edit alone is worth little, because the report is GENERATED: a fix applied to
# the .md is reverted on the next run. These tests are the durable half. They pin the
# property mechanically (5a) and grep the generated artifact for the exact constructions
# that were caught in review (5b-5f), so a regression fails the suite instead of reaching
# the paper.

REPORT = REPO / "results" / "replay_control.md"


def _report() -> str:
    if not REPORT.exists():
        pytest.skip("results/replay_control.md not generated in this tree")
    return REPORT.read_text(encoding="utf-8")


# ---------------------------------------------------------------- 5a. the chokepoint
@pytest.mark.parametrize("d", [-0.9, -0.0074, 0.0, 0.0074, 0.9])
@pytest.mark.parametrize("lo,hi", [(-1.0, 1.0), (-0.0677, 0.0768), (0.0, 0.5),
                                   (-0.5, 0.0), (0.0, 0.0), (-1e-9, 1e-9)])
def test_no_direction_can_be_named_when_the_interval_covers_zero(d, lo, hi):
    """THE regression test for defect 1. Over the whole (d, lo, hi) plane with zero inside
    the interval, `directional_verdict` cannot emit a direction: not for a large positive
    point estimate, not for a large negative one, not when the interval only touches zero
    at an endpoint. The property is checked against the same DIRECTIONAL_WORDS list the
    generator uses, so widening that vocabulary tightens this test automatically."""
    out = RC.directional_verdict("the like-for-like low-FPR pAUC", d, lo, hi)
    assert not RC.has_directional_word(out), out
    assert "covers zero" in out
    assert "not a result" in out
    assert f"{d:+.4f}" in out        # the point estimate is still reported, just not read


def test_a_direction_is_named_only_when_the_interval_excludes_zero():
    up = RC.directional_verdict("the floor", 0.05, 0.02, 0.08)
    down = RC.directional_verdict("the floor", -0.099, -0.155, -0.050, pct=True)
    assert "rises" in up and "excludes zero" in up
    assert "falls" in down and "excludes zero" in down
    assert "-9.9 pts" in down and "[-15.5 pts, -5.0 pts]" in down


def test_the_direction_follows_the_interval_and_not_the_point_estimate():
    """A point estimate whose sign disagrees with its own interval is a bug upstream, not
    a licence to report the estimate's sign."""
    out = RC.directional_verdict("x", -0.001, 0.02, 0.08)
    assert "rises" in out and "falls" not in out


def test_a_direction_cannot_be_smuggled_in_through_the_label():
    with pytest.raises(ValueError):
        RC.directional_verdict("the low-FPR pAUC rises", 0.0074, -0.0677, 0.0768)


def test_has_directional_word_is_whole_word():
    assert not RC.has_directional_word("the like-for-like low-FPR pAUC (replay N=10)")
    assert not RC.has_directional_word("a fallback estimate")
    assert RC.has_directional_word("the floor falls")
    assert RC.has_directional_word("it buys almost nothing")


# ------------------------------------------- 5b. the generated report, grepped for both
BANNED_IN_THE_REPORT = (
    # defect 1: accept a null, then read a direction off the point estimate
    "does not fall",
    "does not rise",
    "it rises by",
    "it falls by",
    # defect 2: the BLOCKED cross-budget TPR claim, re-entered with the sign flipped
    "buys almost nothing",
    "buys nothing",
)


@pytest.mark.parametrize("phrase", BANNED_IN_THE_REPORT)
def test_the_generated_report_contains_no_banned_construction(phrase):
    assert phrase not in _report().lower(), (
        f"results/replay_control.md contains {phrase!r}. That is the error class this "
        f"report exists to correct. Fix scripts/replay_control.py and regenerate -- "
        f"editing the .md is reverted on the next run.")


# ---------------------------------- 5c. the up-front bullets carry no quarantined number
def _summary_bullets(text: str) -> str:
    """The three numbered answers at the top -- the block a reader copies."""
    start = text.index("**The three answers, up front.**")
    return text[start:text.index("\n## ", start)]


def test_the_up_front_summary_is_free_of_every_quarantined_number():
    """The summary is the liftable surface. The blocked cross-budget cells may live in the
    section 2 tables under the banner; they may not live in the bullets."""
    block = _summary_bullets(_report())
    for tok in RC.QUARANTINED:
        assert tok not in block, f"quarantined {tok} appears in the up-front summary"


def test_every_interval_in_the_up_front_summary_is_read_correctly():
    """Any bracketed interval in the bullets that covers zero must be accompanied, in the
    same bullet, by language saying so. This is the SHAPE of defect 1 rather than its
    literal wording, so a differently-phrased relapse is still caught."""
    block = _summary_bullets(_report())
    pat = re.compile(r"\[\s*([+-]?\d*\.?\d+)[^\]]*?,\s*([+-]?\d*\.?\d+)[^\]]*?\]")
    seen = 0
    for bullet in re.split(r"\n(?=\d\. )", block):
        for m in pat.finditer(bullet):
            lo, hi = float(m.group(1)), float(m.group(2))
            if lo <= 0.0 <= hi:
                seen += 1
                assert "covers zero" in bullet, (
                    f"interval [{lo}, {hi}] covers zero but its bullet never says so:\n"
                    f"{bullet}")
    assert seen >= 2, "expected the AUROC and pAUC intervals to be present in the summary"


# --------------------------------------------------- 5d. the blocked TPR claim is scoped
def test_the_cross_budget_tpr_comparison_is_labelled_blocked_wherever_it_appears():
    """Defect 2 is not arithmetic, so it is pinned structurally: the report's own
    'what survives' list is where the claim was resurrected, and that list must name the
    comparison as blocked and quarantined rather than state a verdict on it."""
    text = _report()
    start = text.index("**What DOES survive like-for-like**")
    block = text[start:text.index("\n## ", start)]
    assert "BLOCKED" in block
    assert "quarantine" in block.lower()
    assert "pairing" in block, "the sign-flip-under-pairing reason must be stated in place"


# ----------------------------------------------- 5e. the seed-sensitive count is labelled
def test_the_ranks_better_count_is_never_printed_as_a_hard_number():
    """The report said '197 of 200 draws favour N=40'. An independent reimplementation of
    the same replay got 190/200 from a replay-10 AUROC mean 0.003 higher, so the count is
    seed- and implementation-sensitive at about +/-7 and must not read as a fixed fact."""
    text = _report()
    for m in re.finditer(r"\b\d{2,3} of 200\b", text):
        window = text[m.start():m.start() + 600].lower()
        assert "sensitiv" in window and "190/200" in window, (
            f"{text[m.start():m.start() + 60]!r} is printed without its sensitivity")


# --------------------------------------------------- 5f. the banner, bound to its source
def test_the_report_opens_with_the_generators_quotability_banner():
    """Binds the artifact to RC._PROVENANCE, so hand-editing either one fails the suite.
    The banner must precede the H1: a quarantine below the fold is not a quarantine."""
    text = _report()
    assert text.startswith(RC._PROVENANCE), "the banner is missing, edited, or not first"
    assert text.index(RC._PROVENANCE) < text.index("\n# ")
    for tok in RC.QUARANTINED:
        assert tok in RC._PROVENANCE, f"{tok} is quarantined but the banner omits it"
