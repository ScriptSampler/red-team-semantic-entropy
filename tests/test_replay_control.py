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
    # the numbers are the CURRENT headline fall (matched, section 2b), so that a retired
    # interval cannot survive here reading as though it were the live one
    down = RC.directional_verdict("the floor", -0.0998, -0.129, -0.072, pct=True)
    assert "rises" in up and "excludes zero" in up
    assert "falls" in down and "excludes zero" in down
    assert "-10.0 pts" in down and "[-12.9 pts, -7.2 pts]" in down


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


# ================= 6. an interval may not be attached to the wrong estimator
#
# 2026-08-19, second pass. The report quoted the SUBSET-AVERAGED replayed floor -- a point
# estimate with the k-subset draw averaged out -- and gave it an interval from a bootstrap
# that resamples targets AND redraws the subset, then argued in prose that a
# single-replicate Wilson interval was "too narrow rather than misplaced" because it
# omitted the subset draw. Wilson does not omit it. For a mean of independent indicators,
#
#       mean_i p_i(1-p_i)  +  var_i(p_i)  =  pbar(1-pbar)
#
# so the subset component is already inside the binomial standard error, and the published
# intervals were roughly twice too wide for the estimator printed beside them. Two agents
# had agreed the old argument was right, which is why the fix here is structural rather
# than a corrected sentence: `RC.quote` is now the only way a floor interval reaches the
# report, and it refuses a pair whose components do not match the estimand.
#
# Same shape as section 5: make the wrong statement unconstructible.

# ------------------------------------------------------- 6a. the estimand chokepoint
def test_the_subset_averaged_floor_refuses_an_interval_that_redraws_the_subset():
    """THE regression test. This is the exact call the defect made: the subset-averaged
    point estimate with the both-components bootstrap around it."""
    with pytest.raises(ValueError, match="interval/estimand mismatch"):
        RC.quote("subset-averaged replayed floor", 0.031, 0.005, 0.065,
                 ("questions", "subset"))


def test_the_single_replicate_floor_refuses_an_interval_that_drops_the_subset():
    """The mirror error, which would be just as wrong: a single replicate really does
    carry the subset draw, so a questions-only interval understates it."""
    with pytest.raises(ValueError, match="interval/estimand mismatch"):
        RC.quote("single-replicate replayed floor", 0.031, 0.018, 0.047, ("questions",))


@pytest.mark.parametrize("estimand", sorted(RC.ESTIMAND_RESAMPLES))
def test_every_estimand_accepts_exactly_one_component_set(estimand):
    """Over the whole registry x powerset grid, exactly the declared component set is
    accepted. An estimand added without deciding what its interval may resample fails
    here rather than in the report."""
    want = tuple(sorted(RC.ESTIMAND_RESAMPLES[estimand]))
    for r in ((), ("questions",), ("subset",), ("questions", "subset")):
        if tuple(sorted(r)) == want:
            q = RC.quote(estimand, 0.03, 0.01, 0.05, r)
            assert q.estimand == estimand and q.resampled == want
        else:
            with pytest.raises(ValueError):
                RC.quote(estimand, 0.03, 0.01, 0.05, r)


def test_an_unregistered_estimand_cannot_be_quoted_at_all():
    with pytest.raises(ValueError, match="unknown estimand"):
        RC.quote("the floor, roughly", 0.03, 0.01, 0.05, ("questions",))


def test_a_point_estimate_outside_its_own_interval_is_refused():
    with pytest.raises(ValueError, match="outside"):
        RC.quote("measured floor", 0.09, 0.01, 0.05, ("questions",))


# --------------------------------------------------- 6b. the identity, pinned numerically
@pytest.mark.parametrize("seed", range(6))
def test_the_two_components_sum_to_the_binomial_variance(seed):
    """The arithmetic that makes the old argument false, on random heterogeneous p_i plus
    the degenerate all-equal and all-zero cases. If this could fail, the subset draw
    really would sit outside Wilson and the retracted paragraph would have been right."""
    rng = np.random.default_rng(seed)
    p = rng.beta(0.3, 2.0, size=200)
    if seed == 4:
        p = np.full(200, 0.117)
    if seed == 5:
        p = np.zeros(200)
    d = RC.floor_variance_split(p)
    assert d["sd_rss"] == pytest.approx(d["sd_binomial"], abs=1e-15)
    assert abs(d["residual"]) < 1e-15
    if seed not in (4, 5):
        # a real split: neither component is the whole of it
        assert 0.0 < d["sd_questions"] < d["sd_binomial"]
        assert 0.0 < d["sd_subset"] < d["sd_binomial"]
    if seed == 4:
        assert d["sd_questions"] == pytest.approx(0.0, abs=1e-15)
    if seed == 5:
        assert d["sd_subset"] == pytest.approx(0.0, abs=1e-15)


def test_the_matched_sd_is_never_larger_than_the_single_replicate_sd():
    """The direction of the correction: averaging the subset draw out can only shrink the
    spread, so the matched interval is narrower than Wilson and never the reverse. The
    retracted paragraph asserted the reverse."""
    rng = np.random.default_rng(11)
    for _ in range(20):
        p = rng.beta(0.3, 2.0, size=200)
        d = RC.floor_variance_split(p)
        assert d["sd_questions"] <= d["sd_binomial"]


# ------------------------------------------------- 6c. saturation probabilities are right
def test_saturation_probability_matches_the_projects_own_replay():
    """`RC.saturation_probs` is a fast reimplementation of the event
    `n_scaling_grid.subset_ceiling_prob` scores, so it is pinned against that reference on
    graphs small enough for the reference to enumerate exactly."""
    from itertools import combinations

    import n_scaling_grid as NSG
    rng = np.random.default_rng(3)
    for _ in range(5):
        n, k = 6, 3
        A = np.zeros((n, n), bool)
        bits = []
        for i, j in combinations(range(n), 2):
            v = bool(rng.integers(0, 2))
            bits.append("1" if v else "0")
            A[i, j] = A[j, i] = v
        exact = NSG.subset_ceiling_prob("".join(bits), n, k, rng, n_mc=10 ** 6)
        mine = RC.saturation_probs([A], k, 40000, np.random.default_rng(5))[0]
        assert mine == pytest.approx(exact, abs=0.02)


def test_saturation_of_the_full_set_is_all_or_nothing():
    A = np.zeros((5, 5), bool)
    assert RC.saturation_probs([A], 5, 100, np.random.default_rng(0))[0] == 1.0
    A[0, 1] = A[1, 0] = True
    assert RC.saturation_probs([A], 5, 100, np.random.default_rng(0))[0] == 0.0


def test_floor_boot_refinds_the_top_score_in_each_resample():
    """Why the N=40 arm is bootstrapped and not treated as a fixed per-question indicator:
    drop the single top-scoring question and the floor becomes the mass at the NEXT
    value. That dependence is the reason the headline difference had to be derived."""
    scores = np.array([3.0, 2.0, 2.0, 1.0])
    all_four = RC.floor_boot(scores, np.array([[0, 1, 2, 3]]))
    without_top = RC.floor_boot(scores, np.array([[1, 2, 3, 3]]))
    assert all_four[0] == pytest.approx(1 / 4)          # one question at the top score
    assert without_top[0] == pytest.approx(2 / 4)       # the top moved; two now tie there
    # a fixed per-question indicator would have said 0/4 for the second resample
    assert without_top[0] != pytest.approx(0.0)


# ------------------------------------------- 6d. the generated report carries the fix
BANNED_INTERVAL_CLAIMS = (
    "too narrow rather than misplaced",
    "both variance components are inside",
)


@pytest.mark.parametrize("phrase", BANNED_INTERVAL_CLAIMS)
def test_the_generated_report_no_longer_widens_an_interval_for_the_subset_draw(phrase):
    assert phrase not in _report().lower(), (
        f"results/replay_control.md contains {phrase!r}: an interval is being widened for "
        f"a component its point estimate averages out. Fix scripts/replay_control.py and "
        f"regenerate -- editing the .md is reverted on the next run.")


def test_the_retracted_claim_appears_only_inside_its_retraction():
    """The report is allowed to quote the sentence it is withdrawing, and only that."""
    text = _report().lower()
    phrase = "carries target-sampling variance and not"
    idx = text.find(phrase)
    while idx >= 0:
        window = text[max(0, idx - 500):idx + 200]
        assert "retracted" in window, "the withdrawn claim appears without its retraction"
        idx = text.find(phrase, idx + 1)


def test_the_report_states_the_identity_and_shows_it_holding():
    text = _report()
    assert "mean_i p_i(1-p_i)" in text, "the identity is not stated in the report"
    assert "identity residual" in text, "the identity is asserted but never evaluated"


def test_the_floor_row_is_labelled_wherever_it_is_the_only_matched_row():
    """The tables mix one correct interval with a column of conservative ones. A reader
    lifting the floor has to be able to see, in the row itself, which kind it is."""
    text = _report()
    rows = [ln for ln in text.splitlines()
            if "| floor (min non-zero achievable FPR)" in ln and "[" in ln]
    assert len(rows) >= 5, f"expected the floor to be quoted with an interval; got {rows}"
    for line in rows:
        assert "MATCHED" in line, f"unlabelled floor interval: {line[:90]}"


# =========== 7. a floor may not be quoted with an interval that is not its own
#
# 2026-08-19, third pass. `quote()` (section 6 above) was in place and was BYPASSED. The
# section 2 bullet "**What DOES survive like-for-like**" and the section 6 paragraph
# "**What is worth carrying instead**" -- the two blocks a reader lifts from, one of them
# literally titled what to carry -- built their floor trend from `point[nm]["floor"]` (the
# average over 200 whole replicates) and their headline fall from `diff_ci(..., "floor")`
# (the bootstrap that redraws the subset on top of resampling targets). Neither object
# passes through `quote()`, so the estimand/interval guard never saw them, and the file
# went on printing the superseded "11.9% -> 3.0% -> 2.0%, -9.9 points [-15.5, -5.0]"
# beside a section 2b that says 12.0 / 3.1 / 2.0 and -10.0 [-12.9, -7.2]. The retired fall
# reached three separate agent briefings from there.
#
# The lesson the project drew is that a chokepoint covering the tables and not the prose
# is not a chokepoint. So this section pins BOTH halves:
#   7a  the constructors -- `floor_trend` and `quote_diff` take Quoted objects, so a raw
#       float cannot be formatted into a trend or a difference at all;
#   7b  the artifact -- `RC.audit_report_floor_quotes` reads the generated report back and
#       refuses any floor quoted in prose that the report's own checked tables do not
#       support. The generator runs it on itself before writing; these tests run the
#       identical check on the committed `.md`, and then re-inject the defect to prove the
#       check is not vacuous.
#   7c  an independent re-derivation, done here rather than by calling the audit, so that
#       7b cannot pass by agreeing with itself.


# ------------------------------------------------------- 7a. the constructors refuse
def _q(estimand, point, lo, hi, resampled=("questions",)):
    return RC.quote(estimand, point, lo, hi, resampled)


def test_floor_trend_refuses_a_raw_float():
    """THE regression test for the bypass. `point[nm]["floor"]` is a float; feeding one to
    the trend is exactly what sections 2 and 6 did for a day."""
    a = _q("subset-averaged replayed floor", 0.1197, 0.089, 0.153)
    with pytest.raises(TypeError, match="Quoted"):
        RC.floor_trend(a, 0.0313, 0.02)


def test_floor_trend_refuses_the_direct_cache_row():
    """The banner's own rule -- 'the direct row ... must not be mixed into a budget trend'
    -- which until now lived only in the banner."""
    d = _q("direct-cache floor", 0.095, 0.062, 0.144)
    r = _q("subset-averaged replayed floor", 0.1197, 0.089, 0.153)
    with pytest.raises(ValueError, match="direct"):
        RC.floor_trend(d, r)


def test_floor_trend_refuses_arms_whose_intervals_resample_different_things():
    single = _q("single-replicate replayed floor", 0.1197, 0.07, 0.175,
                ("questions", "subset"))
    avg = _q("subset-averaged replayed floor", 0.0313, 0.018, 0.047)
    with pytest.raises(ValueError, match="different components"):
        RC.floor_trend(single, avg)


def test_floor_trend_refuses_a_non_floor_estimand():
    with pytest.raises(ValueError, match="not a floor"):
        RC.floor_trend(_q("subset-averaged replayed floor", 0.12, 0.09, 0.15),
                       RC.Quoted("AUROC", 0.72, 0.67, 0.78, ("questions",)))


def test_floor_trend_renders_exactly_what_the_tables_render():
    """One rendering of a floor point estimate in this file, not two: the trend prints
    `Quoted.pct_point()`, which is the same `:.1%` the section 2 table prints."""
    arms = [_q("subset-averaged replayed floor", 0.11974, 0.0888, 0.1533),
            _q("subset-averaged replayed floor", 0.03134, 0.0179, 0.0470),
            _q("measured floor", 0.02, 0.008, 0.050)]
    assert RC.floor_trend(*arms) == "12.0% -> 3.1% -> 2.0%"
    assert all(a.pct_point() in RC.floor_trend(*arms) for a in arms)


def test_quote_diff_refuses_the_both_components_interval_on_matched_arms():
    """THE regression test for the headline defect: two subset-averaged floors differenced,
    with `diff_ci`'s both-components bootstrap around the difference. That pair produced
    -9.9 points [-15.5, -5.0] where the matched pair gives -10.0 [-12.9, -7.2]."""
    a = _q("subset-averaged replayed floor", 0.11974, 0.0888, 0.1533)
    b = _q("measured floor", 0.02, 0.008, 0.050)
    with pytest.raises(ValueError, match="interval/estimand mismatch"):
        RC.quote_diff(a, b, -0.09974, -0.155, -0.050, ("questions", "subset"))
    ok = RC.quote_diff(a, b, -0.09974, -0.129, -0.072, ("questions",))
    assert ok.pts("points") == "-10.0 points [-12.9, -7.2]"
    assert ok.excludes_zero() and not ok.covers_zero()


def test_quote_diff_refuses_a_point_estimate_that_is_not_the_difference_of_its_arms():
    """The subtler half of the same defect: matched arms in the table, but the sentence
    beside them still printing the difference of the OLD point estimates."""
    a = _q("subset-averaged replayed floor", 0.11974, 0.0888, 0.1533)
    b = _q("measured floor", 0.02, 0.008, 0.050)
    with pytest.raises(ValueError, match="is not"):
        RC.quote_diff(a, b, -0.099, -0.129, -0.072, ("questions",))   # 11.9% - 2.0%


def test_quote_diff_refuses_arms_of_different_kinds():
    single = _q("single-replicate replayed floor", 0.1197, 0.07, 0.175,
                ("questions", "subset"))
    avg = _q("measured floor", 0.02, 0.008, 0.050)
    with pytest.raises(ValueError, match="not the same"):
        RC.quote_diff(single, avg, -0.0997, -0.129, -0.072, ("questions",))


def test_quote_diff_refuses_a_raw_float_arm():
    b = _q("measured floor", 0.02, 0.008, 0.050)
    with pytest.raises(TypeError, match="Quoted"):
        RC.quote_diff(0.11974, b, -0.09974, -0.129, -0.072, ("questions",))


# --------------------------------------------------- 7b. the artifact, audited
def test_the_generated_report_passes_the_floor_quote_audit():
    """The same function the generator runs on itself before writing. If this fails, some
    sentence in `results/replay_control.md` quotes a floor its own tables do not support --
    fix `scripts/replay_control.py` and regenerate; editing the `.md` is reverted."""
    assert RC.audit_report_floor_quotes(_report()) == []


def test_the_audit_catches_the_exact_defect_it_was_written_for():
    """Both directions. The clean artifact passes above; the artifact with the retired
    sentences put back must fail, or the test above is decoration."""
    text = _report()
    relapse = (text.replace("12.0% -> 3.1% -> 2.0%", "11.9% -> 3.0% -> 2.0%")
                   .replace("-10.0 points [-12.9, -7.2]", "-9.9 points [-15.5, -5.0]"))
    assert relapse != text, "the fixed renderings are absent, so nothing was re-injected"
    bad = RC.audit_report_floor_quotes(relapse)
    assert bad, "the audit passed a report carrying the retired floor trend and fall"
    assert any("11.9%" in b for b in bad) and any("-9.9" in b for b in bad)


def test_the_audit_catches_a_relapse_that_is_worded_differently():
    """The retired-value list alone would be a spot check. Rule 1 is structural: ANY trend
    that disagrees with the section 2 MATCHED floor row is caught, including one built from
    numbers that have never been printed before."""
    reworded = _report().replace("12.0% -> 3.1% -> 2.0%", "12.4% -> 3.6% -> 2.1%")
    bad = RC.audit_report_floor_quotes(reworded)
    assert any("disagrees with the MATCHED floor row" in b for b in bad), bad
    assert not any(t in " ".join(bad) for t in ("11.9%", "-9.9")), \
        "this relapse must be caught structurally, not by the retired-value list"


def test_the_audit_catches_a_prose_difference_with_no_table_behind_it():
    """Rule 2. A fall quoted in prose that no differences-table row supports is the shape
    of the defect: a number that was current when the sentence was written and was not
    updated when the table was."""
    invented = _report().replace("-10.0 points [-12.9, -7.2]",
                                 "-9.4 points [-11.8, -6.6]")
    bad = RC.audit_report_floor_quotes(invented)
    assert any("appears in no table" in b for b in bad), bad


def test_the_audit_notices_if_the_row_it_checks_against_disappears():
    """A guard that silently passes when its reference vanishes is worse than none."""
    gutted = _report().replace(" -- MATCHED, see 2b", "")
    bad = RC.audit_report_floor_quotes(gutted)
    assert any("MATCHED floor row is missing" in b for b in bad), bad


# ------------------------------- 7c. the two lift blocks, re-derived independently
def _matched_floor_row_cells(text: str) -> list[str]:
    """The four point estimates of the section 2 floor row -- direct, replay10, replay20,
    measured -- read straight out of the artifact. That row is built from `matched[...]`,
    so it is the one rendering of the floor in this file that `quote()` has vouched for.

    Each cell is a rate followed EITHER by an interval OR, for the measured budget since
    2026-08-19, by an explicit `(no interval ...)` marker: `n40_floor_estimator_ruling.md`
    withdrew both candidates for that row. Deliberately re-implemented here rather than
    imported from the generator, so the generator's own audit cannot pass by agreeing
    with itself -- which is why this widening is spelled out twice."""
    pat = re.compile(r"(\d+(?:\.\d+)?%) (?:\[|\(no interval)")
    for line in text.splitlines():
        if line.startswith("| floor (min non-zero achievable FPR) -- MATCHED"):
            cells = pat.findall(line)
            if len(cells) == 4:
                assert re.search(r"\|\s*\d+(?:\.\d+)?% \(no interval[^)]*\)\s*\|$", line), (
                    "the measured-budget cell of the MATCHED floor row carries an "
                    "interval again; both candidates were withdrawn on measured coverage "
                    "(Wilson 53.7%, question bootstrap 0.00%, nominal 95%). See "
                    "results/n40_floor_estimator_ruling.md.")
                return cells
    raise AssertionError("the section 2 MATCHED floor row is missing from the report")


def _matched_fall_row(text: str):
    """The replay N=10 -> measured N=40 floor row of the section 2 differences table."""
    for line in text.splitlines():
        if line.startswith("| replay10 -> measured40 | floor") and "MATCHED" in line:
            nums = re.findall(r"([+-]\d+\.\d+) pts", line)
            assert len(nums) == 3, line
            return tuple(nums)
    raise AssertionError("the matched replay10 -> measured40 floor row is missing")


LIFT_BLOCKS = ("**What DOES survive like-for-like**", "**What is worth carrying instead**")


@pytest.mark.parametrize("heading", LIFT_BLOCKS)
def test_the_blocks_a_reader_lifts_from_quote_the_matched_floor(heading):
    """Derived here from the artifact's own tables rather than by calling the audit, so
    that the audit cannot pass by agreeing with itself. These two blocks are where the
    superseded trend and fall lived; section 6's is titled what to carry."""
    text = _report()
    trend = " -> ".join(_matched_floor_row_cells(text)[1:])       # replay family only
    d, lo, hi = _matched_fall_row(text)
    fall = f"{d} points [{lo}, {hi}]"
    start = text.index(heading)
    block = re.sub(r"\s+", " ", text[start:text.index("\n## ", start)])

    chains = re.findall(r"\d+(?:\.\d+)?% *-> *\d+(?:\.\d+)?% *-> *\d+(?:\.\d+)?%", block)
    assert chains, f"{heading} no longer states the floor trend at all"
    for c in chains:
        assert " ".join(c.split()) == trend, (
            f"{heading} quotes the floor trend as {c!r}; the section 2 MATCHED row says "
            f"{trend!r}. Fix scripts/replay_control.py and regenerate.")

    falls = re.findall(r"[+-]\d+(?:\.\d+)? *points *\[[^\]]*\]", block)
    assert falls, f"{heading} no longer states the floor fall at all"
    for f in falls:
        assert " ".join(f.split()) == fall, (
            f"{heading} quotes the fall as {f!r}; the section 2 matched differences table "
            f"says {fall!r}. Fix scripts/replay_control.py and regenerate.")


def test_the_floor_trend_never_starts_at_the_direct_cache():
    """The trend is a replay-family statement. Starting it at 9.5% would put the June
    provenance step back inside the one result this file says survives."""
    text = _report()
    direct = _matched_floor_row_cells(text)[0]
    flat = re.sub(r"\s+", " ", text)
    for c in re.finditer(r"\d+(?:\.\d+)?% *->", flat):
        assert not c.group(0).startswith(direct + " "), (
            f"a budget trend starts at the direct cache value {direct}: "
            f"{flat[c.start():c.start() + 60]!r}")
