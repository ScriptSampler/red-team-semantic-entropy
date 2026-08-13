"""Tests for the winner's-curse retention statistic and its confidence interval.

WHY THIS FILE EXISTS. The retention figure — "45% [25%, 65%]" — is the second-most-prominent
number in the Abstract, and for a while the INTERVAL had no code behind it at all: the script
computed retention as a bare ratio of means and bootstrapped only the shrinkage, so the
interval lived exclusively in hand-written prose attributed to a one-off computation. A
number in the Abstract with no generating code and no test is a reproducibility defect
regardless of whether it happens to be right. These tests pin the estimator, the paired
resampling it depends on, and the near-zero-denominator failure mode it must refuse to hide.

CPU-only, no models, no GPU.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "winners_curse_reeval", _ROOT / "scripts" / "winners_curse_reeval.py")
wc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wc)


# --------------------------------------------------------------------------------------
# the point estimate
# --------------------------------------------------------------------------------------

def test_retention_point_known_answer():
    # Ratio of MEANS, not mean of ratios — the two differ and only the first is the
    # statistic we report. mean(fresh) = 2.5, mean(sel) = 10.0 -> 0.25 exactly.
    # (The mean of the per-target ratios here is (0.1+0.2+0.3+0.4)/4 = 0.25 by coincidence
    #  of construction; the next test separates them.)
    sel = [10.0, 10.0, 10.0, 10.0]
    fresh = [1.0, 2.0, 3.0, 4.0]
    assert wc.retention_point(sel, fresh) == pytest.approx(0.25)


def test_retention_is_ratio_of_means_not_mean_of_ratios():
    sel = [1.0, 9.0]
    fresh = [1.0, 1.0]
    assert wc.retention_point(sel, fresh) == pytest.approx(2.0 / 10.0)      # 0.20
    mean_of_ratios = float(np.mean([1.0 / 1.0, 1.0 / 9.0]))                 # 0.5556
    assert not math.isclose(wc.retention_point(sel, fresh), mean_of_ratios)


def test_retention_point_zero_denominator_is_nan_not_an_exception():
    assert math.isnan(wc.retention_point([1.0, -1.0], [0.5, 0.5]))
    assert math.isnan(wc.retention_point([], []))


def test_summarize_retention_agrees_with_retention_point():
    recs = [{"move_selection": 1.0 + 0.1 * i, "move_fresh": 0.4 + 0.05 * i} for i in range(12)]
    s = wc.summarize(recs)
    assert s["retention"] == pytest.approx(
        wc.retention_point([r["move_selection"] for r in recs],
                           [r["move_fresh"] for r in recs]))
    assert s["retention_ci"]["point"] == pytest.approx(s["retention"])


# --------------------------------------------------------------------------------------
# the CI on a synthetic fixture with a known answer
# --------------------------------------------------------------------------------------

def test_ci_on_exactly_proportional_data_is_a_point():
    """Known answer: if fresh = 0.5 * sel for EVERY target, retention is 0.5 with no
    sampling uncertainty whatsoever — any resample of targets reproduces 0.5 exactly."""
    sel = [0.2, 0.5, 1.0, 1.5, 2.0, 0.7, 1.1, 0.9]
    fresh = [0.5 * x for x in sel]
    r = wc.retention_ci(sel, fresh, n_boot=500, seed=0)
    assert r["point"] == pytest.approx(0.5)
    assert r["lo"] == pytest.approx(0.5, abs=1e-12)
    assert r["hi"] == pytest.approx(0.5, abs=1e-12)
    assert r["stable"] is True


def test_ci_known_answer_brackets_the_point_and_is_finite():
    rng = np.random.default_rng(11)
    sel = rng.uniform(0.5, 2.0, size=200)
    fresh = 0.4 * sel + rng.normal(0.0, 0.05, size=200)      # retention ~ 0.40
    r = wc.retention_ci(sel, fresh, n_boot=2000, seed=0)
    assert r["point"] == pytest.approx(0.40, abs=0.03)
    assert r["lo"] < r["point"] < r["hi"]
    assert r["hi"] - r["lo"] < 0.15                          # tight at n=200, low noise
    assert r["lo"] < 0.40 < r["hi"]                          # covers the truth
    assert r["stable"] is True


def test_ci_widens_as_n_shrinks():
    rng = np.random.default_rng(3)
    big_sel = rng.uniform(0.5, 2.0, size=400)
    big_fresh = 0.5 * big_sel + rng.normal(0.0, 0.4, size=400)
    wide = wc.retention_ci(big_sel[:25], big_fresh[:25], n_boot=2000, seed=0)
    narrow = wc.retention_ci(big_sel, big_fresh, n_boot=2000, seed=0)
    assert (wide["hi"] - wide["lo"]) > 2 * (narrow["hi"] - narrow["lo"])


def test_ci_reproducible_under_a_fixed_seed():
    sel = [1.0 + 0.03 * i for i in range(40)]
    fresh = [0.45 * s + (0.1 if i % 3 else -0.1) for i, s in enumerate(sel)]
    a = wc.retention_ci(sel, fresh, n_boot=1500, seed=7)
    b = wc.retention_ci(sel, fresh, n_boot=1500, seed=7)
    assert (a["lo"], a["hi"]) == (b["lo"], b["hi"])


# --------------------------------------------------------------------------------------
# the paired-resampling property — the correctness core
# --------------------------------------------------------------------------------------

def test_replicates_share_one_index_vector():
    """THE paired property, stated so it cannot pass by accident.

    With fresh = 0.5 * sel exactly, every PAIRED replicate must return exactly 0.5, because
    numerator and denominator are resampled with the SAME index vector and the constant
    factors out. An implementation that drew two independent index vectors could not produce
    this: the between-target spread in `sel` would leak into the ratio."""
    sel = np.array([0.1, 0.4, 0.9, 1.6, 2.5, 3.6])           # deliberately wide spread
    fresh = 0.5 * sel
    reps, num, den = wc.retention_replicates(sel, fresh, n_boot=800, seed=0)
    assert reps.shape == (800,)
    assert np.allclose(reps, 0.5, atol=1e-12)
    assert np.allclose(num, 0.5 * den)                        # the pairing, elementwise
    assert den.min() >= sel.min() and den.max() <= sel.max()  # means of resampled sel


def test_unpaired_resampling_would_be_wrong_and_wider():
    """The contrast the pairing exists to avoid, computed explicitly here rather than
    asserted in a comment: resampling the two arms independently invents an interval out of
    between-target spread that the paired estimator correctly reports as zero."""
    sel = np.array([0.1, 0.4, 0.9, 1.6, 2.5, 3.6])
    fresh = 0.5 * sel
    paired = wc.retention_ci(sel, fresh, n_boot=2000, seed=0)
    rng = np.random.default_rng(0)
    n = len(sel)
    i1 = rng.integers(0, n, size=(2000, n))
    i2 = rng.integers(0, n, size=(2000, n))                   # WRONG: breaks the pairing
    unpaired = fresh[i1].mean(axis=1) / sel[i2].mean(axis=1)
    u_lo, u_hi = np.quantile(unpaired, [0.025, 0.975])
    assert (paired["hi"] - paired["lo"]) == pytest.approx(0.0, abs=1e-12)
    assert (u_hi - u_lo) > 0.3                                # fabricated uncertainty


def test_pairing_matters_on_correlated_data():
    """On realistic correlated data the unpaired interval is strictly wider — the paired one
    is the correct (narrower) answer, so getting this wrong is not merely conservative."""
    rng = np.random.default_rng(5)
    sel = rng.uniform(0.3, 1.8, size=60)
    fresh = 0.45 * sel + rng.normal(0.0, 0.35, size=60)       # r ~ +0.5, like the real data
    paired = wc.retention_ci(sel, fresh, n_boot=4000, seed=0)
    rng2 = np.random.default_rng(0)
    i1 = rng2.integers(0, 60, size=(4000, 60))
    i2 = rng2.integers(0, 60, size=(4000, 60))
    unpaired = fresh[i1].mean(axis=1) / sel[i2].mean(axis=1)
    u_lo, u_hi = np.quantile(unpaired, [0.025, 0.975])
    assert (u_hi - u_lo) > (paired["hi"] - paired["lo"])


def test_replicate_ordering_of_inputs_is_irrelevant():
    """Retention depends on the target SET, not on the order the targets were scored in;
    a permutation applied to both arms together must leave the point estimate identical."""
    rng = np.random.default_rng(2)
    sel = rng.uniform(0.4, 2.0, size=30)
    fresh = 0.5 * sel + rng.normal(0, 0.2, 30)
    perm = rng.permutation(30)
    assert wc.retention_point(sel, fresh) == pytest.approx(
        wc.retention_point(sel[perm], fresh[perm]))


# --------------------------------------------------------------------------------------
# the near-zero-denominator edge case
# --------------------------------------------------------------------------------------

def test_exactly_zero_denominator_is_flagged_not_crashed():
    sel = [1.0, -1.0, 2.0, -2.0]                              # mean exactly 0
    fresh = [0.5, 0.4, 0.3, 0.2]
    r = wc.retention_ci(sel, fresh, n_boot=500, seed=0)
    assert math.isnan(r["point"])
    assert r["stable"] is False
    assert "undefined" in r["warning"] or "zero" in r["warning"]


def test_near_zero_denominator_is_flagged_unstable():
    """The failure mode a naive percentile bootstrap hides. Here the mean selection move is
    a hair above zero relative to its own spread, so the ratio's confidence set is genuinely
    unbounded — Fieller's g >= 1 says so — and a finite-looking percentile interval would be
    a fabrication. The function must refuse to certify it."""
    rng = np.random.default_rng(0)
    sel = rng.normal(0.02, 1.0, size=40)                      # mean ~ 0, sd ~ 1
    fresh = 0.5 * sel + rng.normal(0.0, 0.2, size=40)
    r = wc.retention_ci(sel, fresh, n_boot=4000, seed=0)
    assert r["stable"] is False
    assert r["warning"]
    assert r["fieller_g"] >= 1.0                              # denominator indistinct from 0
    assert math.isnan(r["fieller_lo"])                        # honest: the set is unbounded
    assert r["denom_near_zero_frac"] > 0.0                    # replicates cross zero


def test_stable_data_is_not_falsely_flagged():
    """The guard must not cry wolf on the regime the paper is actually in: a denominator
    many standard errors from zero."""
    rng = np.random.default_rng(1)
    sel = rng.uniform(0.5, 2.0, size=60)                      # bounded away from 0
    fresh = 0.45 * sel + rng.normal(0.0, 0.3, size=60)
    r = wc.retention_ci(sel, fresh, n_boot=3000, seed=0)
    assert r["stable"] is True
    assert r["warning"] == ""
    assert r["fieller_g"] < 1.0
    assert np.isfinite(r["fieller_lo"]) and np.isfinite(r["fieller_hi"])
    assert r["denom_near_zero_frac"] == 0.0


def test_alternative_estimators_agree_when_the_denominator_is_safe():
    """Percentile, log-ratio and Fieller must land in the same place when the ratio is well
    conditioned. If they ever diverge on real data that is itself the finding, which is why
    all three are computed and printed rather than one being chosen silently."""
    rng = np.random.default_rng(4)
    sel = rng.uniform(0.5, 2.0, size=80)
    fresh = 0.45 * sel + rng.normal(0.0, 0.3, size=80)
    r = wc.retention_ci(sel, fresh, n_boot=5000, seed=0)
    assert r["lo"] == pytest.approx(r["log_lo"], abs=0.02)
    assert r["hi"] == pytest.approx(r["log_hi"], abs=0.02)
    assert r["fieller_lo"] == pytest.approx(r["lo"], abs=0.05)
    assert r["fieller_hi"] == pytest.approx(r["hi"], abs=0.05)


def test_empty_input_is_handled():
    r = wc.retention_ci([], [], n_boot=100, seed=0)
    assert r["n"] == 0 and r["stable"] is False
    reps, num, den = wc.retention_replicates([], [], n_boot=100, seed=0)
    assert reps.size == 0 and num.size == 0 and den.size == 0


# --------------------------------------------------------------------------------------
# regression: the actual number the Abstract quotes
# --------------------------------------------------------------------------------------

_CKPT = _ROOT / "results" / "winners_curse_ckpt_se_false_alarm_def.jsonl"


@pytest.mark.skipif(not _CKPT.exists(), reason="winner's-curse checkpoint not present")
def test_paper_retention_number_reproduces_from_the_checkpoint():
    """Pins the Abstract's number to the committed checkpoint. The prose figure that
    preceded any code was retention 45.2% CI [25.1%, 64.7%]; the code reproduces
    45.2% [25.0%, 64.9%] at 10k replicates, agreeing to within the bootstrap's own
    Monte-Carlo wobble (~0.4 percentage points on each endpoint across seeds). Both round
    to the published [25%, 65%]."""
    recs = [json.loads(x) for x in _CKPT.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(recs) == 60
    sel = [r["move_selection"] for r in recs]
    fresh = [r["move_fresh"] for r in recs]
    r = wc.retention_ci(sel, fresh)                            # documented defaults
    assert r["point"] == pytest.approx(0.4515, abs=5e-4)
    assert r["stable"] is True
    assert r["lo"] == pytest.approx(0.250, abs=0.008)          # covers the MC wobble
    assert r["hi"] == pytest.approx(0.649, abs=0.008)
    assert round(r["lo"] * 100) == 25 and round(r["hi"] * 100) == 65
    # and the shrinkage the Abstract quotes alongside it
    s = wc.summarize(recs)
    p, lo, hi = s["shrinkage_ci"]
    assert (p, lo, hi) == pytest.approx((-0.383, -0.529, -0.234), abs=0.003)
    assert hi < 0                                              # inflation is DEMONSTRATED


# --------------------------------------------------------------------------------------
# the checkpoint / fresh-seed collision
# --------------------------------------------------------------------------------------

def test_seed_mismatch_against_a_stamped_checkpoint_is_an_error():
    """The checkpoint filename does not encode --fresh_seed. Re-running at a new seed used
    to find every question_id already done, skip all re-scoring, and re-publish the OLD
    numbers under the NEW seed's headline."""
    done = {f"q{i}": {"question_id": f"q{i}", "fresh_seed": 1} for i in range(5)}
    err, warn, headline = wc.seed_provenance(done, fresh_seed=2)
    assert err and "does not encode the seed" in err
    err2, warn2, headline2 = wc.seed_provenance(done, fresh_seed=1)
    assert err2 is None and warn2 == "" and headline2 == 1


def test_unstamped_legacy_records_are_labelled_asserted_not_measured():
    """The committed n=60 checkpoint predates seed stamping, so it must not be rejected —
    but the headline must not launder the CLI flag into a claim about the data either."""
    done = {f"q{i}": {"question_id": f"q{i}"} for i in range(60)}
    err, warn, headline = wc.seed_provenance(done, fresh_seed=1)
    assert err is None
    assert "predate seed stamping" in warn
    assert "asserted by --fresh_seed" in str(headline)
    recs = [{"move_selection": 1.0 + 0.1 * i, "move_fresh": 0.5 + 0.02 * i} for i in range(6)]
    md = wc.build_report(recs, "se_false_alarm", headline)
    assert "asserted by --fresh_seed" in md.splitlines()[0]


def test_mixed_stamped_and_unstamped_at_the_same_seed_is_allowed():
    done = {"q0": {"question_id": "q0"}, "q1": {"question_id": "q1", "fresh_seed": 1}}
    err, warn, headline = wc.seed_provenance(done, fresh_seed=1)
    assert err is None and "1 checkpoint records" in warn


@pytest.mark.skipif(not _CKPT.exists(), reason="winner's-curse checkpoint not present")
def test_report_is_generated_from_code_and_carries_the_interval():
    """The defect this file was written for: the generated report used to print retention
    with NO interval, so the interval could only ever come from prose."""
    recs = [json.loads(x) for x in _CKPT.read_text(encoding="utf-8").splitlines() if x.strip()]
    md = wc.build_report(recs, "se_false_alarm", 1)
    assert "retention = 45.2%" in md
    assert "paired percentile bootstrap 95% CI" in md
    assert "Fieller" in md
    assert "Do not hand-edit" in md
