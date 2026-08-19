"""The overnight progress monitor's pure parts.

WHAT THIS FILE HAS TO ANSWER FOR. The monitor exists because every cost estimate in this
project has been wrong, several by more than 2x, always by extrapolating a small probe. A
monitor that makes the same mistake -- averaging a multi-day resume gap into a rate, or
quoting an ETA off one target -- would be worse than no monitor, because it would carry the
authority of a measurement. So each behaviour below is paired with a CONTROL: the resume-gap
test has a counterpart proving a merely SLOW target is not swallowed by the same rule, and
the stale-watcher test has a counterpart at the other side of the threshold. A gap detector
that discards everything unusual is not a gap detector; it is a way of never seeing a
slowdown.

No GPU, no network, no clock dependence beyond explicit epochs passed in.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from progress_monitor import (  # noqa: E402
    GAP_ABS_S,
    Interval,
    Sample,
    build_snapshot,
    classify_intervals,
    find_session_start,
    infer_carried_over,
    intervals_from_knots,
    intervals_from_times,
    knots_from_samples,
    parse_epoch,
    project,
    rate_stats,
    read_jsonl_tolerant,
    record_completion_times,
    watcher_health,
    window_rate,
)

T0 = 1787098800.0          # an arbitrary but fixed "now"
HOUR = 3600.0


def _rec(qid: str, **extra) -> dict:
    r = {"detector": "se", "attack": "false_alarm", "question_id": qid,
         "cfg": {"K": 50, "n_seeds": 3}, "attack_move": {"nli": 0.1, "exact": 0.2}}
    r.update(extra)
    return r


# ---- torn-line tolerance ------------------------------------------------------------

def test_a_truncated_trailing_line_is_skipped_not_fatal(tmp_path):
    # The live checkpoint is appended under us; a read can land between the write and the
    # newline. null_control.py::_ckpt_load skips such a line, and so must the monitor.
    p = tmp_path / "ckpt.jsonl"
    good = json.dumps(_rec("qb_1")) + "\n" + json.dumps(_rec("qb_2")) + "\n"
    p.write_text(good + '{"detector": "se", "attack": "false_al', encoding="utf-8")
    recs, torn = read_jsonl_tolerant(p)
    assert [r["question_id"] for r in recs] == ["qb_1", "qb_2"]
    assert torn == 1


def test_a_torn_multibyte_character_does_not_raise(tmp_path):
    # Truncating mid-UTF-8 would make a strict decode throw before any line is parsed,
    # losing the whole reading over one partial byte.
    p = tmp_path / "ckpt.jsonl"
    payload = (json.dumps(_rec("qb_1")) + "\n").encode("utf-8")
    p.write_bytes(payload + '{"question_id": "café'.encode("utf-8")[:-1])
    recs, torn = read_jsonl_tolerant(p)
    assert [r["question_id"] for r in recs] == ["qb_1"]
    assert torn == 1


def test_blank_lines_and_non_objects_are_not_counted_as_records(tmp_path):
    p = tmp_path / "ckpt.jsonl"
    p.write_text("\n" + json.dumps(_rec("qb_1")) + "\n\n  \n[1,2,3]\n", encoding="utf-8")
    recs, torn = read_jsonl_tolerant(p)
    assert len(recs) == 1          # a bare list is not a target record
    assert torn == 1               # ... and is reported, not silently dropped


def test_a_missing_checkpoint_reads_empty_rather_than_exploding(tmp_path):
    assert read_jsonl_tolerant(tmp_path / "nope.jsonl") == ([], 0)


def test_intact_file_reports_zero_torn_lines(tmp_path):
    # CONTROL for the three above: the tolerance must not manufacture phantom torn lines.
    p = tmp_path / "ckpt.jsonl"
    p.write_text("".join(json.dumps(_rec(f"q{i}")) + "\n" for i in range(11)),
                 encoding="utf-8")
    recs, torn = read_jsonl_tolerant(p)
    assert (len(recs), torn) == (11, 0)


# ---- which clock the rate comes from ------------------------------------------------

def test_record_timestamps_are_used_when_every_record_carries_one():
    recs = [_rec("a", completed_epoch=T0), _rec("b", completed_epoch=T0 + 1200)]
    times, basis = record_completion_times(recs)
    assert times == [T0, T0 + 1200]
    assert "completed_epoch" in basis


def test_partial_timestamp_coverage_is_refused_rather_than_mixed():
    # Timing two timestamped records against a file mtime would silently blend two clocks.
    recs = [_rec("a", completed_epoch=T0), _rec("b")]
    times, basis = record_completion_times(recs)
    assert times is None
    assert "mtime" in basis


def test_todays_real_checkpoint_shape_falls_back_to_mtime():
    # The live records are detector/attack/question_id/cfg/... and carry no clock at all.
    times, basis = record_completion_times([_rec("a"), _rec("b")])
    assert times is None and "no timestamp" in basis


def test_iso_and_epoch_and_millisecond_stamps_all_parse():
    assert parse_epoch(T0) == pytest.approx(T0)
    assert parse_epoch(T0 * 1000) == pytest.approx(T0)
    assert parse_epoch("2026-08-19 01:16:10") == pytest.approx(
        time.mktime(time.strptime("2026-08-19 01:16:10", "%Y-%m-%d %H:%M:%S")))
    assert parse_epoch("not a time") is None
    assert parse_epoch(12) is None            # too small to be an epoch: reject, not accept
    assert parse_epoch(True) is None          # bool is an int in Python; must not slip through


# ---- rate from mtime samples --------------------------------------------------------

def test_knots_take_the_mtime_at_which_each_count_was_first_seen():
    # Repeated readings with no new record must not create zero-length intervals.
    samples = [Sample(t=T0, n=11, mtime=T0 - 10), Sample(t=T0 + 60, n=11, mtime=T0 - 10),
               Sample(t=T0 + 120, n=12, mtime=T0 + 100)]
    assert knots_from_samples(samples) == [(T0 - 10, 11), (T0 + 100, 12)]


def test_a_count_that_drops_discards_the_earlier_history():
    # A truncated or rotated checkpoint describes a different file; differencing across it
    # would invent a negative-duration target.
    samples = [Sample(t=T0, n=40, mtime=T0), Sample(t=T0 + 60, n=2, mtime=T0 + 60),
               Sample(t=T0 + 120, n=3, mtime=T0 + 120)]
    assert knots_from_samples(samples) == [(T0 + 60, 2), (T0 + 120, 3)]


def test_rate_is_the_mtime_delta_divided_by_targets_completed():
    knots = [(T0, 11), (T0 + 1000, 12), (T0 + 3000, 14)]
    ivs = intervals_from_knots(knots)
    assert [(iv.n, iv.seconds) for iv in ivs] == [(1, 1000.0), (2, 2000.0)]
    assert ivs[1].per_target == pytest.approx(1000.0)
    st = rate_stats(ivs, last_k=5)
    assert st["targets_timed"] == 3
    assert st["all_time_s_per_target"] == pytest.approx(3000 / 3)


def test_one_completed_target_is_not_a_rate():
    # The headline guard: n=1 must refuse, because a confident ETA off one point is the
    # exact failure this project keeps repeating.
    st = rate_stats(intervals_from_times([T0, T0 + 1200]), last_k=5)
    assert st["targets_timed"] == 1
    assert st["sufficient"] is False
    proj = project(69, st, T0 + 1200)
    assert proj["available"] is False
    assert proj["eta_epoch"] is None
    assert "need >=" in proj["why"]


def test_two_completed_targets_are_enough_to_measure():
    # CONTROL for the guard above: it must not be a permanent refusal.
    st = rate_stats(intervals_from_times([T0, T0 + 1200, T0 + 2400]), last_k=5)
    assert st["sufficient"] is True
    assert st["all_time_s_per_target"] == pytest.approx(1200)


def test_window_rate_reports_the_targets_it_actually_covered():
    ivs = [Interval(T0, T0 + 1000, 1), Interval(T0 + 1000, T0 + 7000, 6)]
    rate, covered, used = window_rate(ivs, 5)
    assert (covered, used) == (6, 1)          # the last interval is taken whole, and said so
    assert rate == pytest.approx(1000.0)


# ---- gap detection ------------------------------------------------------------------

def test_the_resume_gap_is_excluded_and_named():
    # THE TRAP. 11 records finished long ago; target 12 lands minutes after the resume.
    # Averaged naively that is a ~6-day "target" and the ETA is off by days.
    old, resumed = T0 - 6 * 86400, T0
    knots = [(old, 11), (resumed + 1200, 12), (resumed + 2400, 13), (resumed + 3600, 14)]
    live, gaps = classify_intervals(intervals_from_knots(knots), session_start=resumed)
    assert len(gaps) == 1 and "resume gap" in gaps[0]["reason"]
    assert gaps[0]["seconds"] == pytest.approx(6 * 86400 + 1200)
    st = rate_stats(live, last_k=5)
    assert st["targets_timed"] == 2
    assert st["all_time_s_per_target"] == pytest.approx(1200)   # not 250000


def test_a_merely_slow_target_survives_and_is_flagged():
    # CONTROL for the test above, and the whole point of the monitor. A 3x-pathological
    # target must reach the report; a gap rule tight enough to eat it would hide exactly
    # the thermal-throttle / memory-pressure signal an overnight monitor exists to catch.
    knots = [(T0, 0), (T0 + 1200, 1), (T0 + 2400, 2), (T0 + 6000, 3), (T0 + 7200, 4)]
    live, gaps = classify_intervals(intervals_from_knots(knots), session_start=T0 - 1)
    assert gaps == []
    st = rate_stats(live, last_k=5)
    assert [round(s["ratio_to_median"], 1) for s in st["slow_intervals"]] == [3.0]


def test_an_absurd_interval_is_caught_even_without_a_session_start():
    # Fallback for a run whose log we could not read.
    knots = [(T0, 11), (T0 + 6 * 86400, 12)]
    live, gaps = classify_intervals(intervals_from_knots(knots), session_start=None)
    assert live == [] and len(gaps) == 1
    assert "gap cutoff" in gaps[0]["reason"]


def test_the_absolute_cutoff_sits_far_above_a_plausible_target():
    # Nominal is ~1191 s/target; a 3x-pathological target is ~1 h. The cutoff must not be
    # anywhere near that, or the fallback would quietly delete real slowdowns.
    assert GAP_ABS_S >= 4 * HOUR


def test_the_relative_rule_needs_several_survivors_before_it_fires():
    # With two intervals the "median" is meaningless and either one could be called the
    # outlier, so the relative rule must stay silent.
    knots = [(T0, 0), (T0 + 100, 1), (T0 + 100 + 100_000, 2)]
    live, gaps = classify_intervals(intervals_from_knots(knots), session_start=None,
                                    gap_abs=1e9)
    assert gaps == [] and len(live) == 2


# ---- stable vs slowing --------------------------------------------------------------

def test_a_slowdown_beyond_twenty_percent_is_reported_as_disagreement():
    fast = [Interval(T0 + i * 1000, T0 + (i + 1) * 1000, 1) for i in range(8)]
    slow_start = T0 + 8000
    slow = [Interval(slow_start + i * 2000, slow_start + (i + 1) * 2000, 1)
            for i in range(5)]
    st = rate_stats(fast + slow, last_k=5)
    assert st["last_k_s_per_target"] == pytest.approx(2000)
    assert st["all_time_s_per_target"] == pytest.approx(18000 / 13)
    assert st["stable"] is False
    assert st["direction"] == "SLOWING DOWN"
    assert st["disagreement"] > 0.20


def test_a_steady_run_is_reported_stable():
    # CONTROL: the alarm must not fire on an ordinary run.
    ivs = [Interval(T0 + i * 1200, T0 + (i + 1) * 1200, 1) for i in range(12)]
    st = rate_stats(ivs, last_k=5)
    assert st["stable"] is True and st["disagreement"] == pytest.approx(0.0)


def test_no_stability_claim_while_the_two_windows_are_the_same_data():
    # With 3 timed targets, "last 5" IS "all", so agreeing with itself proves nothing.
    st = rate_stats([Interval(T0 + i * 1200, T0 + (i + 1) * 1200, 1) for i in range(3)],
                    last_k=5)
    assert st["same_window"] is True
    assert st["stable"] is None and st["disagreement"] is None


def test_the_projection_carries_a_basis_and_a_spread_not_a_bare_eta():
    fast = [Interval(T0 + i * 1000, T0 + (i + 1) * 1000, 1) for i in range(8)]
    slow = [Interval(T0 + 8000 + i * 2000, T0 + 8000 + (i + 1) * 2000, 1) for i in range(5)]
    st = rate_stats(fast + slow, last_k=5)
    pr = project(10, st, T0)
    assert pr["available"] is True
    assert "last-5 targets" in pr["basis_key"]                 # current conditions lead
    assert pr["eta_epoch"] == pytest.approx(T0 + 10 * 2000)    # ... not the flattering mean
    assert pr["eta_high_epoch"] > pr["eta_low_epoch"]
    assert len(pr["candidates"]) == 2


# ---- the watcher ---------------------------------------------------------------------

def test_a_watcher_older_than_sixty_seconds_is_dead():
    h = watcher_health({"state": "running", "updated_epoch": T0 - 61}, now=T0)
    assert h["healthy"] is False
    assert "WATCHER NOT REPORTING" in h["message"]


def test_a_watcher_inside_the_threshold_is_alive():
    # CONTROL, and the boundary: the watcher writes every 15 s, so 59 s must not alarm.
    assert watcher_health({"state": "running", "updated_epoch": T0 - 59}, now=T0)["healthy"]
    assert watcher_health({"state": "running", "updated_epoch": T0 - 60},
                          now=T0)["healthy"] is True          # exactly at the limit: alive


def test_the_threshold_is_configurable_and_actually_applied():
    s = {"state": "running", "updated_epoch": T0 - 30}
    assert watcher_health(s, now=T0, stale_after=20)["healthy"] is False
    assert watcher_health(s, now=T0, stale_after=45)["healthy"] is True


def test_a_missing_status_file_means_the_stop_button_is_dead():
    h = watcher_health(None, now=T0)
    assert h["healthy"] is False and h["present"] is False
    assert "STOP button" in h["message"]


def test_a_status_file_without_a_timestamp_is_not_treated_as_fresh():
    h = watcher_health({"state": "running"}, now=T0)
    assert h["healthy"] is False and "cannot verify" in h["message"]


def test_a_future_timestamp_is_called_clock_skew_not_freshness():
    # WSL and Windows can disagree; a status stamped in the future would otherwise read as
    # eternally fresh.
    h = watcher_health({"state": "running", "updated_epoch": T0 + 600}, now=T0)
    assert h["healthy"] is False and "FUTURE" in h["message"]


def test_the_string_updated_field_is_a_usable_fallback():
    h = watcher_health({"state": "running", "updated": "2026-08-19 01:17:53"},
                       now=parse_epoch("2026-08-19 01:17:58"))
    assert h["healthy"] is True


# ---- carried-over inference -----------------------------------------------------------

def test_records_older_than_the_resume_are_carried_over_not_this_sessions_work():
    n, basis = infer_carried_over(11, ckpt_mtime=T0 - 6 * 86400, samples=[],
                                  session_start=T0)
    assert n == 11 and "not been written" in basis


def test_the_first_sample_pins_the_carried_over_count_for_later_readings():
    samples = [Sample(t=T0 + 1, n=11, mtime=T0 - 6 * 86400),
               Sample(t=T0 + 4000, n=13, mtime=T0 + 3900)]
    n, basis = infer_carried_over(13, ckpt_mtime=T0 + 3900, samples=samples,
                                  session_start=T0)
    assert n == 11 and "first sample" in basis


def test_starting_the_monitor_too_late_admits_it_cannot_tell():
    # Refusing to guess matters: a wrong split would misreport how much the session has done.
    n, basis = infer_carried_over(13, ckpt_mtime=T0 + 3900, samples=[], session_start=T0)
    assert n is None and "--carried-over" in basis


def test_record_timestamps_split_old_from_new_exactly():
    times = [T0 - 6 * 86400, T0 - 6 * 86400 + 60, T0 + 1200]
    n, basis = infer_carried_over(3, ckpt_mtime=T0 + 1200, samples=[], session_start=T0,
                                  times=times)
    assert n == 2 and basis == "record timestamps"


def test_the_session_start_comes_from_the_wrappers_own_log(tmp_path):
    log = tmp_path / "overnight_20260814.log"
    log.write_text(
        "[2026-08-13 22:00:00] START null-control (attempt 1)\n"
        "[2026-08-13 23:00:00] FAIL rc=1 -- resuming from checkpoint in 60s\n"
        "[2026-08-19 01:16:10] START null-control (attempt 2)\n", encoding="utf-8")
    ts, basis = find_session_start(log)
    assert ts == pytest.approx(parse_epoch("2026-08-19 01:16:10"))   # the LATEST attempt
    assert "overnight_20260814.log" in basis
    assert find_session_start(tmp_path / "absent.log")[0] is None


# ---- the whole snapshot, on tonight's actual situation ---------------------------------

def _snapshot(**over):
    kw = dict(now=T0, ckpt_path=Path("results/null_control_ckpt_defb.jsonl"),
              records=[_rec(f"q{i}") for i in range(11)], torn=0,
              ckpt_mtime=T0 - 6 * 86400, ckpt_size=30088, samples=[],
              status={"state": "running", "gpu_processes": 2, "updated_epoch": T0 - 12},
              total=80, total_basis="test", session_start=T0 - 300,
              session_basis="test", carried_over=11, carried_basis="test",
              last_k=5, stale_after=60.0, gap_abs=GAP_ABS_S, gap_factor=10.0)
    kw.update(over)
    return build_snapshot(**kw)


def test_the_first_reading_of_the_night_reports_progress_but_refuses_a_rate():
    s = _snapshot()
    assert (s["progress"]["done"], s["progress"]["remaining"]) == (11, 69)
    assert s["progress"]["carried_over"] == 11
    assert s["progress"]["produced_this_session"] == 0
    assert s["rate"]["sufficient"] is False
    assert s["projection"]["available"] is False
    assert s["watcher"]["healthy"] is True


def test_a_dead_watcher_is_reported_even_when_progress_looks_fine():
    s = _snapshot(status={"state": "running", "gpu_processes": 2, "updated_epoch": T0 - 900})
    assert s["watcher"]["healthy"] is False
    assert s["progress"]["done"] == 11          # progress still reported, not suppressed


def test_the_session_start_anchor_is_labelled_as_including_startup():
    # With no sample history but a known start and a known carried-over count, the span
    # from start to the newest record IS a measurement -- of a window containing model
    # load, so it must never be passed off as a steady-state rate.
    s = _snapshot(records=[_rec(f"q{i}") for i in range(14)],
                  ckpt_mtime=T0 - 300 + 4200, session_start=T0 - 300, carried_over=11)
    assert s["rate"]["anchored_at_session_start"] is True
    assert "UPPER bound" in s["rate"]["anchor_note"]
    assert s["rate"]["all_time_s_per_target"] == pytest.approx(1400)


def test_one_target_is_shown_as_an_observation_and_denied_the_word_rate():
    # The night's real first data point. It must appear -- hiding it would waste the only
    # evidence there is -- but the report must not let it become an ETA.
    from progress_monitor import render_text
    s = _snapshot(records=[_rec(f"q{i}") for i in range(12)],
                  ckpt_mtime=T0 - 300 + 1430, session_start=T0 - 300, carried_over=11)
    assert s["rate"]["targets_timed"] == 1 and s["rate"]["sufficient"] is False
    assert s["projection"]["available"] is False
    txt = render_text(s)
    assert "single observation, NOT a rate" in txt
    assert "UPPER bound" in txt
    assert "PROJECTION none" in txt


def test_a_second_cfg_in_the_checkpoint_is_surfaced():
    # The run only reuses records whose cfg matches its own, so a mixed checkpoint means
    # "done" overstates what this run will skip.
    recs = [_rec("a"), _rec("b")]
    recs[1]["cfg"] = {"K": 180, "n_seeds": 3}
    assert _snapshot(records=recs)["progress"]["distinct_cfgs"] == 2


def test_the_json_snapshot_is_serialisable_for_the_dashboard():
    json.dumps(_snapshot())      # the dashboard fetches this; a non-serialisable value
                                 # would break the page rather than the monitor
