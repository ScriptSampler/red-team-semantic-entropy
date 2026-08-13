"""CPU-only tests for the defense DRIVER (scripts/wk_defense.py).

tests/test_defense.py covers src/se/defense.py -- the aggregation and variant
selection. It says nothing about the experiment built on top of it, which is
where both confounds lived: the estimators, the arm definitions, the cost
model, the cross-check, and the rejection branch. This module covers those.

The load-bearing tests are:

  * the strict-null calibration, which reproduces the audit's finding that a
    C-vs-B comparison books a double-digit "defense" with NO defense present;
  * the cross-check functional, which pins that signed and absolute retention
    differ by ~26 points on the project's own checkpoint (the round-1 bug);
  * the verdict branch, which must say NOT COMPUTABLE, not FAILED, on NaN;
  * the synthetic recovery, which is the end-to-end check that the analysis
    path reports the numbers it claims to.

    .venv\\Scripts\\python.exe -m pytest tests/test_wk_defense.py -q
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "scripts"))

import wk_defense as W
from wk_defense import (
    CheckpointMismatch,
    DefenseRecord,
    _ckpt_load,
    _paired_diff_ci,
    _paired_reduction,
    _ratio_reduction_ci,
    analyse_cell,
    compare_arms,
    cross_check_lines,
    expected_abs_normal,
    load_wc_reference,
    make_synthetic_records,
    matched_redraws,
    null_calibration,
    null_expected_abs_move,
    per_estimate_sigma,
    sec_per_defended_call,
    sec_per_noise_control,
    sec_per_outcome,
    sec_per_outcome_round0,
    sec_per_outcome_round1,
    variants_per_call,
    wc_checkpoint_path,
)

WC_CKPT = wc_checkpoint_path("false_alarm", "_def")
needs_wc = pytest.mark.skipif(not WC_CKPT.exists(),
                              reason=f"winner's-curse checkpoint missing: {WC_CKPT}")


# ===========================================================================
# _ratio_reduction_ci
# ===========================================================================

def test_ratio_reduction_recovers_a_planted_ratio_of_means():
    den = [1.0, 2.0, 3.0, 4.0]
    num = [0.4 * d for d in den]                     # 60% reduction, exactly
    pt, lo, hi, _ = _ratio_reduction_ci(num, den, n_boot=500)
    assert pt == pytest.approx(0.6)
    assert lo == pytest.approx(0.6)
    assert hi == pytest.approx(0.6)


def test_ratio_reduction_bootstrap_is_paired_not_independent():
    """The whole correctness argument for the ratio interval. If every target
    satisfies num = 0.4*den exactly, the reduction is 0.6 with NO uncertainty,
    and only a PAIRED resample recovers that. An unpaired resample would invent
    an interval out of the between-target spread."""
    den = [0.2, 0.9, 1.4, 2.8, 5.0]
    num = [0.4 * d for d in den]
    _, lo, hi, _ = _ratio_reduction_ci(num, den, n_boot=2000)
    assert hi - lo == pytest.approx(0.0, abs=1e-12)


def test_ratio_reduction_is_nan_below_two_targets():
    for pt in _ratio_reduction_ci([0.3], [0.6])[:3]:
        assert math.isnan(pt)


def test_ratio_reduction_is_nan_on_a_zero_denominator():
    pt, lo, hi, dz = _ratio_reduction_ci([0.3, 0.4], [0.0, 0.0])
    assert math.isnan(pt) and math.isnan(lo) and math.isnan(hi)
    assert dz == 0.0


def test_ratio_reduction_is_nan_on_non_finite_input():
    pt, *_ = _ratio_reduction_ci([0.3, float("nan")], [0.6, 0.6])
    assert math.isnan(pt)


def test_denominator_z_is_infinite_when_the_denominator_has_no_spread():
    """A denominator with zero variance is PERFECTLY conditioned. Reporting
    z = 0 there (the round-1 behaviour) reads as 'badly conditioned, do not
    quote' on the best-behaved possible input."""
    _, _, _, dz = _ratio_reduction_ci([0.3, 0.3, 0.3], [1.0, 1.0, 1.0], n_boot=200)
    assert math.isinf(dz)


def test_denominator_z_is_finite_and_large_on_a_well_separated_denominator():
    rng = np.random.default_rng(0)
    den = list(2.0 + 0.1 * rng.standard_normal(50))
    num = [0.5 * d for d in den]
    _, _, _, dz = _ratio_reduction_ci(num, den, n_boot=200)
    assert 10.0 < dz < 1e6


# ===========================================================================
# _paired_reduction -- and the selection effect it used to hide
# ===========================================================================

def test_paired_reduction_values_are_one_minus_the_ratio():
    pr = _paired_reduction([0.5, 0.2], [1.0, 1.0])
    assert pr.values == pytest.approx([0.5, 0.8])
    assert pr.n == 2 and pr.n_dropped == 0 and pr.n_total == 2
    assert math.isnan(pr.dropped_num_mean)


def test_paired_reduction_accounts_for_every_dropped_target():
    """The round-1 version silently dropped zero-denominator targets. Nothing
    may vanish without being counted: n + n_dropped == n_total."""
    pr = _paired_reduction([0.5, 0.9, 0.1], [1.0, 0.0, 1e-12])
    assert pr.n == 1
    assert pr.n_dropped == 2
    assert pr.n_total == 3
    assert pr.n + pr.n_dropped == pr.n_total


def test_paired_reduction_reports_the_numerator_of_what_it_dropped():
    """A dropped target with a LARGE numerator is a target where the defended
    arm moved a lot and the control moved nothing -- i.e. an infinitely negative
    reduction, deleted. The reader must be able to tell that case from the
    benign one where both arms are ~0."""
    pr = _paired_reduction([0.8, 0.0], [0.0, 0.0])
    assert pr.n == 0
    assert pr.dropped_num_mean == pytest.approx(0.4)
    assert math.isnan(pr.median) and math.isnan(pr.mean)


def test_dropping_zero_denominator_targets_is_a_selection_effect_on_the_outcome():
    """Quantifies why the headline is not this statistic. Targets whose control
    effect is ~0 are exactly the ones re-sampling already neutralised; keeping
    only the rest conditions on the outcome and inflates the surviving mean."""
    num = [0.5, 0.5, 0.5, 0.02]
    den = [1.0, 1.0, 1.0, 1e-12]
    pr = _paired_reduction(num, den)
    assert pr.mean == pytest.approx(0.5)          # what the round-1 code printed
    # the deleted target contributed a reduction of 1 - 0.02/1e-12, i.e. a
    # catastrophically negative one. The paired DIFFERENCE keeps it, unweighted:
    diff, _, _ = _paired_diff_ci(num, den, n_boot=200)
    assert diff == pytest.approx(((1.0 - 0.5) * 3 + (1e-12 - 0.02)) / 4)
    assert diff < pr.mean                          # the drop was not benign


# ===========================================================================
# _paired_diff_ci -- the primary estimand
# ===========================================================================

def test_paired_diff_recovers_the_planted_mean_difference():
    den = [1.0, 2.0, 3.0]
    num = [0.5, 1.0, 1.5]
    pt, lo, hi = _paired_diff_ci(num, den, n_boot=2000)
    assert pt == pytest.approx(1.0)               # mean(den - num) = (0.5+1+1.5)/3
    assert lo < pt < hi


def test_paired_diff_interval_is_degenerate_when_every_difference_is_equal():
    pt, lo, hi = _paired_diff_ci([0.5, 1.0, 1.5], [1.0, 1.5, 2.0], n_boot=1000)
    assert pt == pytest.approx(0.5)
    assert hi - lo == pytest.approx(0.0, abs=1e-12)


def test_paired_diff_is_nan_below_two_targets():
    assert all(math.isnan(v) for v in _paired_diff_ci([0.1], [0.2]))


def test_paired_diff_needs_no_denominator_so_zero_control_targets_survive():
    """The estimand's whole point: a target where the control effect is 0 is a
    perfectly informative target (the defense had nothing to reduce), and the
    difference keeps it while the ratio must throw it away."""
    num, den = [0.0, 0.5], [0.0, 1.0]
    pt, _, _ = _paired_diff_ci(num, den, n_boot=500)
    assert pt == pytest.approx(0.25)
    assert _paired_reduction(num, den).n == 1     # the ratio kept only one


# ===========================================================================
# DefenseRecord: arm scores and signed moves
# ===========================================================================

def _rec(**kw) -> DefenseRecord:
    base = dict(attack="false_alarm", question_id="q", aggregate="median",
                k_requested=4, cached_before=1.0, cached_after=2.0,
                redraws_before=[1.0, 1.2, 0.8], redraws_after=[1.6, 1.5, 1.4],
                defended_before=1.1, defended_after=1.3, d_before=2, d_after=2)
    base.update(kw)
    return DefenseRecord(**base)


def test_arm_b_is_redraw_zero_and_arm_b_prime_is_the_aggregate():
    r = _rec()
    assert r.fresh_before == 1.0 and r.fresh_after == 1.6
    assert r.noise_before == pytest.approx(1.0)    # median of [1.0, 1.2, 0.8]
    assert r.noise_after == pytest.approx(1.5)     # median of [1.6, 1.5, 1.4]
    assert r.effect_control == pytest.approx(0.6)
    assert r.effect_noise == pytest.approx(0.5)
    assert r.effect_cached == pytest.approx(1.0)
    assert r.effect_defended == pytest.approx(0.2)
    assert r.m_before == 3 and r.m_after == 3


def test_arm_b_prime_follows_the_records_own_aggregate_not_a_hardcoded_median():
    r = _rec(aggregate="mean")
    assert r.noise_before == pytest.approx(1.0)            # mean of [1.0,1.2,0.8]
    assert r.noise_after == pytest.approx(1.5)             # mean of [1.6,1.5,1.4]
    r_min = _rec(aggregate="min")
    assert r_min.noise_before == pytest.approx(0.8)
    assert r_min.noise_after == pytest.approx(1.4)


def test_signed_moves_carry_the_attacks_direction():
    fa = _rec(attack="false_alarm")
    assert fa.sign == 1.0
    assert fa.move_cached == pytest.approx(1.0)            # +1 * (2.0 - 1.0)
    hide = _rec(attack="hide")
    assert hide.sign == -1.0
    assert hide.move_cached == pytest.approx(-1.0)         # -1 * (2.0 - 1.0)
    # ... while the ABSOLUTE effect is blind to direction:
    assert fa.effect_cached == hide.effect_cached


def test_absolute_and_signed_moves_disagree_exactly_when_a_target_flips():
    r = _rec(attack="false_alarm", redraws_before=[1.0], redraws_after=[0.4])
    assert r.move_control == pytest.approx(-0.6)           # flipped: wrong way
    assert r.effect_control == pytest.approx(0.6)          # abs folds it back


# ===========================================================================
# matched_redraws: arm B' is sized to arm C, per target and per side
# ===========================================================================

class _FakeDefended:
    def __init__(self, per_variant):
        self.per_variant_entropy = list(per_variant)
        self.n_variants = len(per_variant)


def test_matched_redraws_pays_exactly_m_minus_one_extra_evaluations():
    calls = []
    res = _FakeDefended([1.0, 2.0, 3.0, 4.0])        # C aggregated m = 4
    out = matched_redraws("Q", res, lambda t: calls.append(t) or 0.5)
    assert len(out) == 4                              # same m as arm C
    assert out[0] == 1.0                              # C's own original-input score
    assert out[1:] == [0.5, 0.5, 0.5]
    assert calls == ["Q", "Q", "Q"]                   # the IDENTICAL input, never a paraphrase


def test_matched_redraws_degenerates_with_the_defense():
    """When the gate rejects every paraphrase, C is vanilla SE on one draw. B'
    must degenerate to the same single draw, so C vs B' reports exactly 0 for
    that target rather than a spurious reduction."""
    calls = []
    res = _FakeDefended([1.75])
    out = matched_redraws("Q", res, lambda t: calls.append(t) or 9.9)
    assert out == [1.75]
    assert calls == []


def test_matched_redraws_never_scores_a_different_string():
    res = _FakeDefended([1.0, 2.0, 3.0])
    seen = []
    matched_redraws("the identical input", res, lambda t: seen.append(t) or 0.0)
    assert set(seen) == {"the identical input"}


# ===========================================================================
# the verdict branch -- NaN is not a failure
# ===========================================================================

def test_verdict_survives_when_the_interval_excludes_zero_above():
    c = compare_arms([0.2, 0.25, 0.3, 0.22], [0.9, 1.0, 1.1, 0.95], "C vs B'",
                     n_boot=1000)
    assert c.computable
    assert c.diff_lo > 0
    assert c.verdict == "SURVIVES"


def test_verdict_fails_when_the_two_arms_are_identical():
    x = [0.4, 0.9, 1.3, 0.7]
    c = compare_arms(x, list(x), "C vs B'", n_boot=1000)
    assert c.diff == pytest.approx(0.0)
    assert c.verdict == "FAILED"


def test_verdict_fails_when_the_defended_arm_moved_more():
    c = compare_arms([1.0, 1.1, 1.2], [0.5, 0.6, 0.7], "C vs B'", n_boot=1000)
    assert c.diff < 0
    assert c.verdict == "FAILED"


def test_nan_interval_is_not_computable_rather_than_failed():
    """The round-1 bug: the branch was `if not (lo > 0)`, and NaN > 0 is False,
    so a cell with n < 2 or a degenerate denominator printed a confident
    'The prediction FAILED'. Absence of evidence is not evidence of absence."""
    c = compare_arms([0.5], [1.0], "C vs B'", n_boot=100)
    assert not c.computable
    assert c.verdict == "NOT COMPUTABLE"
    assert c.verdict != "FAILED"


def test_not_computable_propagates_into_the_report_text():
    rec = make_synthetic_records(1, r_cb=0.5)[0]
    lines, cmps = analyse_cell([rec], "false_alarm", k=4, aggregate="median",
                               n_boot=200)
    body = "\n".join(lines)
    assert cmps["C vs B'"].verdict == "NOT COMPUTABLE"
    assert "NOT COMPUTABLE" in body
    assert "prediction FAILED" not in body


# ===========================================================================
# synthetic recovery -- the claim the round-1 commit made without a fixture
# ===========================================================================

def test_synthetic_records_plant_the_reductions_exactly():
    recs = make_synthetic_records(30, r_cb=0.50, r_bb=0.40, r_ba=0.70)
    a = [r.effect_cached for r in recs]
    b = [r.effect_control for r in recs]
    bp = [r.effect_noise for r in recs]
    c = [r.effect_defended for r in recs]
    assert _ratio_reduction_ci(c, bp, n_boot=200)[0] == pytest.approx(0.50)
    assert _ratio_reduction_ci(bp, b, n_boot=200)[0] == pytest.approx(0.40)
    assert _ratio_reduction_ci(b, a, n_boot=200)[0] == pytest.approx(0.70)
    # per-question too, since the plant is per target
    assert _paired_reduction(c, bp).median == pytest.approx(0.50)
    assert _paired_reduction(bp, b).median == pytest.approx(0.40)
    assert _paired_reduction(b, a).median == pytest.approx(0.70)


def test_synthetic_signed_retention_recovers_the_planted_winners_curse():
    for attack in ("hide", "false_alarm"):
        recs = make_synthetic_records(20, attack=attack, r_ba=0.70)
        sel = np.mean([r.move_cached for r in recs])
        fresh = np.mean([r.move_control for r in recs])
        assert fresh / sel == pytest.approx(0.30)      # retention = 1 - 0.70


def test_synthetic_null_plant_makes_the_analysis_print_failed():
    recs = make_synthetic_records(30, r_cb=0.0, r_bb=0.40, r_ba=0.70)
    lines, cmps = analyse_cell(recs, "false_alarm", k=4, aggregate="median",
                               n_boot=500)
    assert cmps["C vs B'"].verdict == "FAILED"
    assert "The prediction FAILED for this cell" in "\n".join(lines)
    # ... while the confounded round-1 comparison still shows a fat "reduction"
    assert cmps["C vs B"].ratio == pytest.approx(0.40)


def test_a_failed_verdict_is_printed_with_the_resolution_that_qualifies_it():
    """A FAILED verdict without a stated resolution is unreadable: it cannot be
    distinguished from an underpowered cell. The half-width must be printed."""
    recs = make_synthetic_records(30, r_cb=0.0, r_bb=0.40, r_ba=0.70)
    lines, _ = analyse_cell(recs, "false_alarm", k=4, aggregate="median",
                            n_boot=500)
    body = "\n".join(lines)
    assert "RESOLUTION" in body
    assert "no effect larger" in body


def test_the_paired_difference_is_unbiased_under_the_strict_null():
    """The property that makes the estimand legitimate. Two arms with the SAME
    aggregate size and no defense in either: the mean paired difference must sit
    at 0, unlike the ratio of E|.| which the round-1 design used."""
    rng = np.random.default_rng(0)
    sigma, m, n = 0.34, 4, 400
    effects = rng.standard_normal(n) * 0.5
    agg = lambda z: np.median(z, axis=-1)
    c = np.abs(effects + agg(rng.standard_normal((n, m))) * sigma
               - agg(rng.standard_normal((n, m))) * sigma)
    bp = np.abs(effects + agg(rng.standard_normal((n, m))) * sigma
                - agg(rng.standard_normal((n, m))) * sigma)
    pt, lo, hi = _paired_diff_ci(list(c), list(bp), n_boot=2000)
    assert lo < 0.0 < hi                       # the null is not rejected
    assert abs(pt) < 0.05


def test_the_ratio_of_absolute_moves_is_biased_where_the_difference_is_not():
    """The round-1 confound, in a fixture. Same true effects, no defense, but
    arm C aggregates m draws and arm B one: the RATIO reports a fat 'defense'
    while the paired difference of two EQUALLY-noisy arms reports zero."""
    e = [0.3, 0.5, -0.2, 0.8, 0.1, 0.6]
    e_b = null_expected_abs_move(e, 0.34, 1)
    e_c = null_expected_abs_move(e, 0.34, 4, aggregate="median", n_reps=8_000)
    assert 1.0 - e_c / e_b > 0.08              # phantom "defense" from noise alone
    e_bprime = null_expected_abs_move(e, 0.34, 4, aggregate="median",
                                      n_reps=8_000, seed=11)
    assert abs(e_bprime - e_c) < 0.01          # ... and it vanishes once m matches


def test_synthetic_positive_plant_makes_the_analysis_print_survives():
    recs = make_synthetic_records(30, r_cb=0.50, r_bb=0.40, r_ba=0.70)
    lines, cmps = analyse_cell(recs, "false_alarm", k=4, aggregate="median",
                               n_boot=500)
    assert cmps["C vs B'"].verdict == "SURVIVES"
    assert "The prediction SURVIVES for this cell" in "\n".join(lines)


def test_synthetic_end_to_end_through_main(tmp_path):
    out = tmp_path / "syn.md"
    rc = W.main(["--synthetic", "--synthetic-n", "30", "--out", str(out)])
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "reduction 50.0%" in body          # C vs B'
    assert "reduction 40.0%" in body          # B' vs B
    assert "SYNTHETIC MODE" in body
    assert "SURVIVES" in body


def test_synthetic_main_rejects_a_malformed_plant(tmp_path):
    assert W.main(["--synthetic", "--synthetic-plant", "0.5",
                   "--out", str(tmp_path / "x.md")]) == 2


# ===========================================================================
# the strict-null calibration -- the reason arm B' exists
# ===========================================================================

def test_expected_abs_normal_matches_the_known_half_normal_mean():
    # E|X| for X ~ N(0, s^2) is s * sqrt(2/pi)
    assert expected_abs_normal([0.0], 1.0) == pytest.approx(math.sqrt(2 / math.pi))
    assert expected_abs_normal([0.0], 0.5) == pytest.approx(0.5 * math.sqrt(2 / math.pi))
    # and reduces to |mu| as the noise vanishes
    assert expected_abs_normal([-2.0, 3.0], 0.0) == pytest.approx(2.5)


def test_expected_abs_normal_is_strictly_increasing_in_the_noise():
    """The one-line reason the round-1 design could not fail: the arm carrying
    less noise posts a smaller E|.| with no effect difference at all."""
    prev = -1.0
    for s in (0.0, 0.1, 0.2, 0.4, 0.8):
        v = expected_abs_normal([0.3, -0.1, 0.7], s)
        assert v > prev
        prev = v


def test_null_expected_abs_move_m1_monte_carlo_matches_the_closed_form():
    e = [0.1, -0.4, 0.9, 0.0]
    exact = null_expected_abs_move(e, 0.34, 1)
    assert exact == pytest.approx(expected_abs_normal(e, 0.34 * math.sqrt(2)))
    # the m=2 MC path must land near a hand-checkable value: for the mean
    # aggregate the noise on each side is sigma/sqrt(2), so the difference is
    # N(effect, sigma^2) exactly.
    mc = null_expected_abs_move(e, 0.34, 2, aggregate="mean", n_reps=40_000, seed=3)
    assert mc == pytest.approx(expected_abs_normal(e, 0.34), abs=0.005)


def test_null_apparent_defense_is_positive_with_no_defense_present():
    e = [0.3, 0.5, -0.2, 0.8, 0.1]
    cal = null_calibration(e, 0.34, ms=(1, 3, 4), aggregate="median", n_reps=8_000)
    assert cal[1]["apparent_reduction"] == pytest.approx(0.0)
    assert cal[3]["apparent_reduction"] > 0.0
    assert cal[4]["apparent_reduction"] > cal[3]["apparent_reduction"]


@needs_wc
def test_per_estimate_sigma_on_the_real_checkpoint_is_about_a_third_of_a_nat():
    recs = [json.loads(l) for l in WC_CKPT.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    assert len(recs) == 60
    assert per_estimate_sigma(recs) == pytest.approx(0.340, abs=0.005)


@needs_wc
def test_the_audit_simulation_reproduces_from_the_real_checkpoint():
    """THE REPRODUCTION. Strict null on this project's own data: paraphrases
    carry the true entropy of their input, true effects are the empirical fresh
    moves, median aggregate, sigma = 0.34 nats. A C-vs-B comparison then books
    a double-digit 'defense' that is entirely variance reduction."""
    ref = load_wc_reference(WC_CKPT)
    cal = null_calibration(ref.effects, 0.34, ms=(1, 3, 4), aggregate="median",
                           n_reps=8_000)
    assert cal[1]["e_abs"] == pytest.approx(0.6575, abs=0.004)
    assert cal[3]["e_abs"] == pytest.approx(0.5834, abs=0.006)
    assert cal[4]["e_abs"] == pytest.approx(0.5599, abs=0.006)
    assert cal[3]["apparent_reduction"] == pytest.approx(0.113, abs=0.012)
    assert cal[4]["apparent_reduction"] == pytest.approx(0.148, abs=0.012)


@needs_wc
def test_the_artefact_scales_with_the_aggregate_size_the_defense_would_use():
    ref = load_wc_reference(WC_CKPT)
    m = int(round(variants_per_call(4)))               # 4 at k=4, gate 0.67
    cal = null_calibration(ref.effects, ref.sigma, ms=(1, m), aggregate="median",
                           n_reps=8_000)
    assert cal[m]["apparent_reduction"] > 0.10


# ===========================================================================
# the cross-check -- signed vs absolute retention
# ===========================================================================

@needs_wc
def test_signed_and_absolute_retention_differ_on_the_projects_own_checkpoint():
    """The round-1 cross-check compared its own ABSOLUTE ratio against the
    published SIGNED 45.2%. Here is the gap that guaranteed a false alarm."""
    ref = load_wc_reference(WC_CKPT)
    assert ref.n == 60
    assert ref.signed_retention == pytest.approx(0.452, abs=0.002)
    assert ref.absolute_retention == pytest.approx(0.712, abs=0.002)
    assert ref.absolute_retention - ref.signed_retention > 0.25
    assert ref.n_sign_flips == 16


def test_load_wc_reference_returns_none_when_the_checkpoint_is_absent(tmp_path):
    assert load_wc_reference(tmp_path / "nope.jsonl") is None


def test_cross_check_skips_rather_than_borrowing_another_cells_number():
    recs = make_synthetic_records(10, attack="hide")
    body = "\n".join(cross_check_lines(recs, None, "hide"))
    assert "unavailable" in body
    assert "SKIPPED" in body
    assert "45.2" not in body


@needs_wc
def test_cross_check_does_not_claim_a_present_checkpoint_is_missing():
    """`ref=None` means 'not supplied', which is not the same as 'not on disk'.
    Saying the wrong one sends the reader hunting for a file that is there."""
    recs = make_synthetic_records(6, attack="false_alarm")
    body = "\n".join(cross_check_lines(recs, None, "false_alarm"))
    assert "exists but was not supplied" in body
    assert "no winner's-curse checkpoint" not in body


def test_cross_check_reports_a_caller_supplied_reason_verbatim():
    recs = make_synthetic_records(6, attack="false_alarm")
    body = "\n".join(cross_check_lines(recs, None, "false_alarm",
                                       unavailable_reason="these are SYNTHETIC records"))
    assert "these are SYNTHETIC records" in body


def test_cross_check_reports_the_signed_functional_as_the_comparable_one():
    recs = make_synthetic_records(12, attack="false_alarm", r_ba=0.70)
    body = "\n".join(cross_check_lines(recs, None, "false_alarm"))
    assert "SIGNED retention" in body
    assert "30.0%" in body                       # 1 - 0.70, recovered
    assert "ABSOLUTE retention" in body
    assert "NOT the comparable functional" in body


def test_cross_check_absolute_and_signed_diverge_when_targets_flip():
    """Constructed so half the fresh moves go the wrong way: the signed
    retention collapses while the absolute one does not. This is the mechanism
    behind the 45.2% / 71.2% gap, in miniature."""
    recs = []
    for i in range(8):
        flip = -1.0 if i % 2 else 1.0
        recs.append(DefenseRecord(
            attack="false_alarm", question_id=f"q{i}", aggregate="median",
            k_requested=4, cached_before=0.0, cached_after=1.0,
            redraws_before=[0.0], redraws_after=[flip * 0.5],
            defended_before=0.0, defended_after=0.4, d_before=0, d_after=0))
    signed = np.mean([r.move_control for r in recs]) / np.mean([r.move_cached for r in recs])
    absolute = (np.mean([r.effect_control for r in recs])
                / np.mean([r.effect_cached for r in recs]))
    assert signed == pytest.approx(0.0)
    assert absolute == pytest.approx(0.5)
    body = "\n".join(cross_check_lines(recs, None, "false_alarm"))
    assert "0.0%" in body and "50.0%" in body


# ===========================================================================
# checkpoint schema
# ===========================================================================

def _write(path: Path, recs) -> None:
    path.write_text("\n".join(json.dumps(asdict(r)) for r in recs) + "\n",
                    encoding="utf-8")


def test_checkpoint_round_trips(tmp_path):
    p = tmp_path / "ck.jsonl"
    recs = make_synthetic_records(4)
    _write(p, recs)
    got = _ckpt_load(p, aggregate="median", k=4)
    assert len(got) == 4
    assert got["false_alarm::syn_0000"].effect_defended == pytest.approx(
        recs[0].effect_defended)


def test_missing_checkpoint_is_empty_not_an_error(tmp_path):
    assert _ckpt_load(tmp_path / "absent.jsonl") == {}


def test_round1_schema_records_are_rejected_by_name(tmp_path):
    """Round-1 records store fresh_before/fresh_after scalars and no per-draw
    list, so arm B' cannot be reconstructed from them. Silently skipping them
    (the old `except: continue`) would have re-rendered a report over a subset
    nobody chose."""
    p = tmp_path / "old.jsonl"
    p.write_text(json.dumps({
        "attack": "hide", "question_id": "q1", "cached_before": 1.0,
        "cached_after": 0.4, "fresh_before": 1.0, "fresh_after": 0.7,
        "defended_before": 1.0, "defended_after": 0.8, "d_before": 3,
        "d_after": 3}) + "\n", encoding="utf-8")
    with pytest.raises(CheckpointMismatch, match="schema 1"):
        _ckpt_load(p)


def test_a_checkpoint_at_a_different_aggregate_is_rejected(tmp_path):
    p = tmp_path / "ck.jsonl"
    _write(p, make_synthetic_records(2, aggregate="median"))
    with pytest.raises(CheckpointMismatch, match="aggregat"):
        _ckpt_load(p, aggregate="mean")


def test_a_checkpoint_at_a_different_k_is_rejected(tmp_path):
    p = tmp_path / "ck.jsonl"
    _write(p, make_synthetic_records(2, k=4))
    with pytest.raises(CheckpointMismatch, match="k="):
        _ckpt_load(p, k=6)


def test_a_record_with_empty_redraws_is_rejected(tmp_path):
    p = tmp_path / "ck.jsonl"
    r = asdict(make_synthetic_records(1)[0])
    r["redraws_after"] = []
    p.write_text(json.dumps(r) + "\n", encoding="utf-8")
    with pytest.raises(CheckpointMismatch, match="redraws"):
        _ckpt_load(p)


# ===========================================================================
# cost model
# ===========================================================================

def test_arm_b_prime_costs_exactly_the_extra_evaluations_it_aggregates():
    m = variants_per_call(4)
    assert sec_per_noise_control(4) == pytest.approx((m - 1) * W.SEC_PER_SE_EVAL)
    # ... and the total is the two defended calls plus the two B' top-ups
    assert sec_per_outcome(4) == pytest.approx(
        2 * sec_per_defended_call(4) + 2 * sec_per_noise_control(4))


def test_the_round1_cost_delta_was_23_percent_not_19(tmp_path):
    """The round-1 commit message said '+19% GPU'. From this file's own
    constants it is +23%. Pinned so the arithmetic is in the tests, not in a
    commit message nobody re-derives."""
    r0 = sec_per_outcome_round0(4)
    r1 = sec_per_outcome_round1(4)
    assert r0 == pytest.approx(110.86, abs=0.01)
    assert r1 == pytest.approx(136.34, abs=0.01)
    assert r1 / r0 - 1 == pytest.approx(0.23, abs=0.005)


def test_the_round2_cost_is_derived_and_printed_not_asserted():
    r1 = sec_per_outcome_round1(4)
    r2 = sec_per_outcome(4)
    assert r2 == pytest.approx(179.15, abs=0.01)
    assert r2 > r1
    assert r2 / r1 - 1 == pytest.approx(0.314, abs=0.005)


def test_round2_is_cheaper_than_an_unshared_b_prime_would_be():
    """Reusing arm C's original-input variant as B' draw 0 (and arm B) saves two
    SE evaluations per outcome versus drawing all of B' fresh plus a separate B."""
    unshared = (2 * sec_per_defended_call(4)
                + 2 * variants_per_call(4) * W.SEC_PER_SE_EVAL
                + 2 * W.SEC_PER_SE_EVAL)
    assert sec_per_outcome(4) == pytest.approx(unshared - 4 * W.SEC_PER_SE_EVAL)


def test_cost_is_monotone_in_k_and_degenerates_sanely_at_k_zero():
    vals = [sec_per_outcome(k) for k in (0, 1, 2, 4, 8)]
    assert vals == sorted(vals)
    # k=0: one SE eval per side for arm C, nothing extra for B'
    assert sec_per_outcome(0) == pytest.approx(2 * W.SEC_PER_SE_EVAL)


def test_estimate_prints_the_n_it_used_so_the_hours_cannot_go_stale():
    lines = W.estimate(4, {"hide": 38, "false_alarm": 40},
                       campaign="/x/wk9_defb", filt="entropy_and_feasible", cap=40)
    body = "\n".join(lines)
    assert "n = 78 outcomes" in body
    assert "hide 38" in body and "false_alarm 40" in body
    assert "/x/wk9_defb" in body
    expected_h = (78 * sec_per_outcome(4) + W.SEC_MODEL_LOAD) / 3600
    assert f"{expected_h:.2f} GPU-h" in body
    # the round-0/1/2 arithmetic is in the output, not in a commit message
    assert "round 0" in body and "round 1" in body and "round 2" in body


def test_estimate_handles_an_empty_campaign_without_dividing_by_anything():
    body = "\n".join(W.estimate(4, {}, campaign="/x", filt="success", cap=40))
    assert "n = 0 outcomes" in body
    assert "no cells" in body


# ===========================================================================
# the claim and the code must name the same estimand
# ===========================================================================

def test_the_falsifiable_claim_names_the_comparison_the_code_makes():
    claim = W.FALSIFIABLE_CLAIM
    assert "arm C against arm B'" in claim
    assert "paired difference" in claim
    assert "nats" in claim
    assert "95% CI" in claim
    # and it must NOT promise an interval on the per-question ratio, which is
    # what the round-1 claim named while the code computed a ratio of means
    assert "per-question paired reduction" not in claim


def test_the_report_labels_the_confounded_comparison_as_confounded():
    recs = make_synthetic_records(20, r_cb=0.30, r_bb=0.40, r_ba=0.70)
    lines, _ = analyse_cell(recs, "false_alarm", k=4, aggregate="median", n_boot=300)
    body = "\n".join(lines)
    assert "CONFOUNDED -- do not quote" in body
    assert "THE DEFENSE" in body
    assert "noise-averaging artefact, MEASURED" in body


def test_the_report_warns_when_the_gate_degenerated_most_calls():
    recs = make_synthetic_records(20, r_cb=0.30)
    for r in recs:
        r.d_before = 0
        r.d_after = 0
        r.redraws_before = [r.redraws_before[0]]
        r.redraws_after = [r.redraws_after[0]]
    lines, _ = analyse_cell(recs, "false_alarm", k=4, aggregate="median", n_boot=300)
    assert "WARNING" in "\n".join(lines)


def test_the_report_is_ascii_only():
    """It is printed to a Windows cp1252 console as well as written to UTF-8."""
    recs = make_synthetic_records(12)
    lines, _ = analyse_cell(recs, "false_alarm", k=4, aggregate="median", n_boot=200)
    body = "\n".join(lines) + W.FALSIFIABLE_CLAIM + "\n".join(
        W.estimate(4, {"hide": 3}, campaign="/x", filt="success", cap=40))
    body.encode("ascii")
