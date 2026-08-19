"""Progress and time monitor for the live overnight null control.

WHY THIS EXISTS. Every cost estimate in this project has been wrong, several by more than
2x, and the failure is always the same shape: a small-scale probe extrapolated to a large
run. The 1191 s/target that scripts/overnight_2026_08_14.sh budgets with was measured by
timing targets 2-11 of the PREVIOUS run through filesystem anchors -- a defensible number
when it was made, and still an assumption tonight. This re-derives it continuously from the
run that is actually on the GPU, and refuses to quote a rate it cannot measure.

WHAT IT MEASURES AND HOW.

results/null_control_ckpt_defb.jsonl carries no per-record timestamp (its records are
detector/attack/question_id/cfg/baseline/attack_move/benign/seed and nothing else), so the
only clock available is the file's own mtime: null_control.py appends one line per completed
target and flushes, which makes mtime the completion time of the newest record. One reading
therefore yields one point and NO rate. The monitor keeps its own sample log
(dashboard/progress_samples.jsonl) of (wall clock, record count, mtime) so that successive
readings -- or one `--watch` session -- turn into measured intervals. If a future checkpoint
does carry timestamps, they are used directly and the mtime path is skipped; see
`record_completion_times`.

THE RESUME GAP. The checkpoint already held 11 records from a run that finished long before
tonight's resume. The interval between record 11 and record 12 therefore spans the whole
downtime, and averaging it in would report an ETA off by days. Intervals that start before
the session's start (read from the run log) are excluded and reported as the resume gap; the
pre-existing records are reported as "carried over" and are never timed.

WHY THE HEURISTIC GAP THRESHOLDS ARE LOOSE. A tight "anything over 30 min is a gap" rule
would silently eat the one signal an overnight monitor exists to catch: a target that got
slow. At ~1191 s/target nominal, a 3x-pathological target is 60 min. So the absolute
fallback threshold is 4 h and the relative one is 10x the median, and anything merely slower
than 1.5x the median is FLAGGED, not discarded. The session-start boundary, which is exact,
does the real work; the heuristics only cover a run whose log we could not read.

LAST-K VS ALL-TIME. A run that is slowing down -- thermal throttling, memory pressure, a
pathological target -- is invisible in an all-time mean, which is why both are reported and
why a disagreement above 20% is shouted rather than averaged away.

THE WATCHER CHECK OUTRANKS ALL OF IT. dashboard/session_status.json is rewritten every 15 s
by scripts/stop_watcher.sh. If it is more than 60 s stale the watcher is dead, which means
the user's STOP button no longer frees the GPU. That matters more than any progress number,
so it is checked and printed even when the progress side has nothing to say.

Read-only with respect to the run: it touches nothing but its own sample log and its own
JSON output under dashboard/.

    .venv\\Scripts\\python.exe scripts/progress_monitor.py
    .venv\\Scripts\\python.exe scripts/progress_monitor.py --watch 300
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEFAULT_CKPT = REPO / "results" / "null_control_ckpt_defb.jsonl"
DEFAULT_STATUS = REPO / "dashboard" / "session_status.json"
DEFAULT_SAMPLES = REPO / "dashboard" / "progress_samples.jsonl"
DEFAULT_OUT = REPO / "dashboard" / "progress_status.json"
DEFAULT_RUN_LOG_GLOB = "overnight_*.log"
DEFAULT_TARGETS = (REPO / "data" / "cache" / "attacks" / "wk9_defb_snap"
                   / "triviaqa_se_false_alarm.jsonl")

SCHEMA = "progress_monitor/1"

STALE_AFTER_S = 60.0        # matches the dashboard's own staleness rule
LAST_K = 5
MIN_TIMED_TARGETS = 2       # one point is not a rate
DISAGREE_FRAC = 0.20
GAP_ABS_S = 4 * 3600.0      # deliberately far above any plausible single target
GAP_FACTOR = 10.0           # ... and far above any plausible slow target
SLOW_FACTOR = 1.5           # flagged, never excluded
PRIOR_S_PER_TARGET = 1191.0  # the assumption under test; never mixed into a measurement

# Timestamp fields a future checkpoint might carry, most explicit first.
TS_KEYS = ("completed_epoch", "finished_epoch", "t_end", "end_time",
           "completed_at", "finished_at", "timestamp", "ts")

_LOG_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
_SESSION_MARKERS = ("START null-control", "null control, resumed")


# ---- pure helpers -------------------------------------------------------------------

def parse_epoch(value) -> float | None:
    """Epoch seconds from a float/int epoch or a common timestamp string, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v > 1e11:           # milliseconds
            v /= 1000.0
        return v if 1e8 < v < 4e9 else None
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(s).timestamp()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(value.strip(), fmt))
        except Exception:
            continue
    return None


def read_jsonl_tolerant(path) -> tuple[list[dict], int]:
    """(records, n_unparseable). A read can land mid-append, so the trailing line is often
    a torn write; skip it rather than crash. Same rule as null_control.py::_ckpt_load,
    which skips corrupt lines so a crash mid-write costs one target and not the run."""
    p = Path(path)
    if not p.exists():
        return [], 0
    raw = b""
    for attempt in range(3):                     # the writer may hold it for an instant
        try:
            raw = p.read_bytes()
            break
        except (PermissionError, OSError):
            if attempt == 2:
                return [], 0
            time.sleep(0.2)
    text = raw.decode("utf-8", errors="replace")  # a torn multi-byte char must not raise
    out: list[dict] = []
    torn = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            torn += 1
            continue
        if isinstance(rec, dict):
            out.append(rec)
        else:
            torn += 1
    return out, torn


def record_completion_times(records: list[dict]) -> tuple[list[float] | None, str]:
    """Per-record completion times if EVERY record carries the same usable timestamp
    field, else (None, reason). Partial coverage is refused: timing a subset against a
    file mtime would silently mix two clocks."""
    if not records:
        return None, "no records"
    for key in TS_KEYS:
        if not all(key in r for r in records):
            continue
        vals = [parse_epoch(r.get(key)) for r in records]
        if any(v is None for v in vals):
            continue
        return sorted(float(v) for v in vals), f"record field {key!r}"
    return None, "records carry no timestamp field; falling back to file mtime"


@dataclass(frozen=True)
class Sample:
    t: float          # wall clock when this reading was taken
    n: int            # records in the checkpoint at that moment
    mtime: float      # checkpoint mtime == completion time of record n
    size: int = 0

    def as_json(self) -> dict:
        return {"t": self.t, "n": self.n, "mtime": self.mtime, "size": self.size}


@dataclass(frozen=True)
class Interval:
    """(t0, t1] during which `n` targets completed."""
    t0: float
    t1: float
    n: int

    @property
    def seconds(self) -> float:
        return self.t1 - self.t0

    @property
    def per_target(self) -> float:
        return self.seconds / self.n if self.n else float("inf")


def load_samples(path) -> list[Sample]:
    recs, _ = read_jsonl_tolerant(path)
    out = []
    for r in recs:
        try:
            out.append(Sample(float(r["t"]), int(r["n"]), float(r["mtime"]),
                              int(r.get("size", 0))))
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda s: s.t)
    return out


def append_sample(path, sample: Sample) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sample.as_json()) + "\n")
        fh.flush()


def knots_from_samples(samples: list[Sample]) -> list[tuple[float, int]]:
    """(mtime, n) for each count the checkpoint was first seen to reach. A DROP in n means
    the checkpoint was truncated or rotated, so the history before it describes a different
    file and is discarded rather than differenced across."""
    knots: list[tuple[float, int]] = []
    for s in sorted(samples, key=lambda s: s.t):
        if knots and s.n < knots[-1][1]:
            knots = []
        if not knots or s.n > knots[-1][1]:
            knots.append((s.mtime, s.n))
    return knots


def intervals_from_knots(knots: list[tuple[float, int]]) -> list[Interval]:
    out = []
    for (m0, n0), (m1, n1) in zip(knots, knots[1:]):
        if n1 > n0 and m1 > m0:
            out.append(Interval(m0, m1, n1 - n0))
    return out


def intervals_from_times(times: list[float]) -> list[Interval]:
    ts = sorted(times)
    return [Interval(a, b, 1) for a, b in zip(ts, ts[1:]) if b > a]


def classify_intervals(intervals: list[Interval], session_start: float | None = None,
                       gap_abs: float = GAP_ABS_S,
                       gap_factor: float = GAP_FACTOR) -> tuple[list[Interval], list[dict]]:
    """Split measured intervals into live ones and excluded gaps.

    An interval is a gap if it starts before the session did (the resume gap, exact), or if
    it is absurdly long in absolute terms, or absurdly long relative to the median of the
    others. The last two are fallbacks for a run whose start we could not read; both
    thresholds are set high on purpose so a genuinely slow target survives to be reported.
    """
    flagged: list[tuple[Interval, str | None]] = []
    for iv in intervals:
        reason = None
        if session_start is not None and iv.t0 < session_start:
            reason = "starts before the session resumed (resume gap)"
        elif iv.per_target >= gap_abs:
            reason = (f"{iv.per_target / 3600:.1f} h/target exceeds the "
                      f"{gap_abs / 3600:.0f} h gap cutoff")
        flagged.append((iv, reason))

    survivors = [iv for iv, r in flagged if r is None]
    if len(survivors) >= 3:
        med = statistics.median(iv.per_target for iv in survivors)
        if med > 0:
            flagged = [(iv, r if r is not None else
                        (f"{iv.per_target / med:.0f}x the median target time"
                         if iv.per_target >= gap_factor * med else None))
                       for iv, r in flagged]

    live = [iv for iv, r in flagged if r is None]
    gaps = [{"t0": iv.t0, "t1": iv.t1, "seconds": iv.seconds, "targets": iv.n,
             "per_target_s": iv.per_target, "reason": r} for iv, r in flagged if r is not None]
    return live, gaps


def window_rate(intervals: list[Interval], k: int) -> tuple[float | None, int, int]:
    """(s/target, targets covered, intervals used) over the last `k` targets. Walks back
    from the end until k targets are covered; the final interval is taken whole, so the
    covered count is reported rather than assumed."""
    if not intervals:
        return None, 0, 0
    secs = 0.0
    n = 0
    used = 0
    for iv in reversed(intervals):
        secs += iv.seconds
        n += iv.n
        used += 1
        if n >= k:
            break
    return (secs / n if n else None), n, used


def rate_stats(live: list[Interval], last_k: int = LAST_K,
               disagree_frac: float = DISAGREE_FRAC,
               min_targets: int = MIN_TIMED_TARGETS) -> dict:
    """All-time vs last-k per-target rates and whether they agree."""
    timed = sum(iv.n for iv in live)
    total_s = sum(iv.seconds for iv in live)
    out = {
        "targets_timed": timed,
        "intervals": len(live),
        "sufficient": timed >= min_targets,
        "min_targets": min_targets,
        "all_time_s_per_target": (total_s / timed) if timed else None,
        "last_k": last_k,
        "last_k_s_per_target": None,
        "last_k_targets": 0,
        "spread_s_per_target": None,
        "disagreement": None,
        "stable": None,
        "direction": None,
        "same_window": False,
        "slow_intervals": [],
    }
    if not timed:
        return out
    lk, lk_n, _ = window_rate(live, last_k)
    out["last_k_s_per_target"] = lk
    out["last_k_targets"] = lk_n
    out["same_window"] = lk_n >= timed
    per = [iv.per_target for iv in live]
    out["spread_s_per_target"] = [min(per), max(per)]
    if len(live) >= 3:
        med = statistics.median(per)
        out["slow_intervals"] = [
            {"t0": iv.t0, "t1": iv.t1, "targets": iv.n, "per_target_s": iv.per_target,
             "ratio_to_median": iv.per_target / med}
            for iv in live if med > 0 and iv.per_target >= SLOW_FACTOR * med]
    at = out["all_time_s_per_target"]
    if at and lk and not out["same_window"]:
        out["disagreement"] = abs(lk - at) / at
        out["stable"] = out["disagreement"] <= disagree_frac
        out["direction"] = "SLOWING DOWN" if lk > at else "speeding up"
    elif out["same_window"]:
        out["stable"] = None          # nothing to compare against yet
    return out


def project(remaining: int, rates: dict, now: float) -> dict:
    """Completion projection with an explicit basis and spread -- never a bare ETA.

    The headline uses the last-k rate because current conditions predict the next hours
    better than a mean over conditions that may no longer hold; the all-time rate is carried
    alongside as the other end of the envelope.
    """
    out = {"remaining": remaining, "available": False, "basis": None,
           "eta_epoch": None, "eta_low_epoch": None, "eta_high_epoch": None,
           "hours_remaining": None, "candidates": {}}
    if not rates.get("sufficient"):
        out["why"] = (f"only {rates.get('targets_timed', 0)} target(s) timed this session; "
                      f"need >= {rates.get('min_targets', MIN_TIMED_TARGETS)} before a rate "
                      f"means anything")
        return out
    cands = {}
    if rates.get("last_k_s_per_target"):
        cands[f"last-{rates['last_k_targets']} targets"] = rates["last_k_s_per_target"]
    if rates.get("all_time_s_per_target"):
        cands["all timed targets this session"] = rates["all_time_s_per_target"]
    if not cands:
        out["why"] = "no usable rate"
        return out
    headline_key = (f"last-{rates['last_k_targets']} targets"
                    if rates.get("last_k_s_per_target") else "all timed targets this session")
    headline = cands[headline_key]
    lo, hi = min(cands.values()), max(cands.values())
    out.update({
        "available": True,
        "basis": (f"{headline:.0f} s/target from the {headline_key} "
                  f"({rates['targets_timed']} timed this session)"),
        "basis_key": headline_key,
        "s_per_target": headline,
        "eta_epoch": now + remaining * headline,
        "eta_low_epoch": now + remaining * lo,
        "eta_high_epoch": now + remaining * hi,
        "hours_remaining": remaining * headline / 3600.0,
        "candidates": {k: v for k, v in cands.items()},
    })
    return out


def watcher_health(status: dict | None, now: float,
                   stale_after: float = STALE_AFTER_S) -> dict:
    """The stop watcher's liveness. A stale status file means the STOP button is dead."""
    if status is None:
        return {"present": False, "healthy": False, "age_s": None, "state": None,
                "gpu_processes": None, "stale_after_s": stale_after,
                "message": "NO STATUS FILE -- the stop watcher is not running; "
                           "the dashboard STOP button will not free the GPU"}
    upd = parse_epoch(status.get("updated_epoch"))
    if upd is None:
        upd = parse_epoch(status.get("updated"))
    if upd is None:
        return {"present": True, "healthy": False, "age_s": None,
                "state": status.get("state"), "gpu_processes": status.get("gpu_processes"),
                "stale_after_s": stale_after,
                "message": "status file has no readable timestamp -- cannot verify the "
                           "watcher is alive; treat STOP as unproven"}
    age = now - upd
    out = {"present": True, "age_s": age, "state": status.get("state"),
           "detail": status.get("detail"), "gpu_processes": status.get("gpu_processes"),
           "updated": status.get("updated"), "updated_epoch": upd,
           "stale_after_s": stale_after}
    if age < -stale_after:
        out["healthy"] = False
        out["message"] = (f"status timestamp is {-age:.0f}s in the FUTURE -- clock skew "
                          f"between WSL and Windows; watcher age cannot be trusted")
    elif age > stale_after:
        out["healthy"] = False
        out["message"] = (f"WATCHER NOT REPORTING for {age:.0f}s (limit {stale_after:.0f}s) "
                          f"-- the STOP button no longer frees the GPU. Fix this before "
                          f"caring about any progress number below.")
    else:
        out["healthy"] = True
        out["message"] = f"watcher alive, last wrote {age:.0f}s ago"
    return out


def infer_carried_over(n_done: int, ckpt_mtime: float | None, samples: list[Sample],
                       session_start: float | None,
                       times: list[float] | None = None,
                       explicit: int | None = None) -> tuple[int | None, str]:
    """How many of the records on disk predate this session, and how we know."""
    if explicit is not None:
        return explicit, "given on the command line"
    if session_start is None:
        return None, "session start unknown, so old and new records cannot be separated"
    if times is not None:
        return sum(1 for t in times if t < session_start), "record timestamps"
    if ckpt_mtime is not None and ckpt_mtime < session_start:
        return n_done, "checkpoint has not been written since the run resumed"
    for s in sorted(samples, key=lambda s: s.t):
        if s.mtime < session_start:
            return s.n, "first sample was taken before the resumed run wrote anything"
    return None, ("monitoring started after the run had already written; pass "
                  "--carried-over to separate them")


def find_session_start(run_log) -> tuple[float | None, str]:
    """Epoch of the most recent run start, from the overnight wrapper's own log."""
    p = Path(run_log) if run_log else None
    if p is None or not p.exists():
        return None, f"run log not found ({run_log})"
    best = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not any(m in line for m in _SESSION_MARKERS):
            continue
        m = _LOG_TS.match(line)
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        best = ts if best is None else max(best, ts)
    if best is None:
        return None, f"no start marker in {p.name}"
    return best, f"{p.name} start marker"


def fmt_dur(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    s = abs(float(seconds))
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{int(d)}d {int(h)}h {int(m)}m"
    if h:
        return f"{int(h)}h {int(m)}m"
    if m:
        return f"{int(m)}m {int(s % 60)}s"
    return f"{int(s)}s"


def fmt_ts(epoch: float | None) -> str:
    if epoch is None:
        return "n/a"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))


# ---- snapshot -----------------------------------------------------------------------

def build_snapshot(*, now: float, ckpt_path: Path, records: list[dict], torn: int,
                   ckpt_mtime: float | None, ckpt_size: int, samples: list[Sample],
                   status: dict | None, total: int, total_basis: str,
                   session_start: float | None, session_basis: str,
                   carried_over: int | None, carried_basis: str,
                   last_k: int, stale_after: float,
                   gap_abs: float, gap_factor: float) -> dict:
    """Everything the text and JSON reports are rendered from. Pure: no IO."""
    n_done = len(records)
    times, times_basis = record_completion_times(records)

    if times is not None:
        intervals = intervals_from_times(times)
        clock = "record timestamps"
    else:
        intervals = intervals_from_knots(knots_from_samples(samples))
        clock = "checkpoint mtime deltas across the monitor's sample window"

    live, gaps = classify_intervals(intervals, session_start, gap_abs, gap_factor)

    # Fallback for a first reading with no sample history: if we know how many targets this
    # session produced and when it started, the span from start to the newest record is a
    # real (if startup-inflated) measurement. Labelled as such, never silently blended.
    anchored = False
    produced = None if carried_over is None else n_done - carried_over
    if (not live and session_start is not None and ckpt_mtime is not None
            and produced is not None and produced >= 1 and ckpt_mtime > session_start):
        live = [Interval(session_start, ckpt_mtime, produced)]
        anchored = True

    rates = rate_stats(live, last_k=last_k)
    if anchored:
        rates["anchored_at_session_start"] = True
        rates["anchor_note"] = ("measured from the run's start, so it includes model load "
                                "and is an UPPER bound on the steady-state s/target")

    remaining = max(0, total - n_done)
    proj = project(remaining, rates, now)
    health = watcher_health(status, now, stale_after)

    cfgs = {}
    for r in records:
        cfgs[json.dumps(r.get("cfg"), sort_keys=True)] = cfgs.get(
            json.dumps(r.get("cfg"), sort_keys=True), 0) + 1

    return {
        "schema": SCHEMA,
        "generated_epoch": now,
        "generated": fmt_ts(now),
        "checkpoint": str(ckpt_path),
        "checkpoint_mtime_epoch": ckpt_mtime,
        "checkpoint_mtime": fmt_ts(ckpt_mtime),
        "checkpoint_age_s": (now - ckpt_mtime) if ckpt_mtime else None,
        "checkpoint_bytes": ckpt_size,
        "torn_lines": torn,
        "progress": {
            "done": n_done,
            "total": total,
            "total_basis": total_basis,
            "remaining": remaining,
            "carried_over": carried_over,
            "carried_over_basis": carried_basis,
            "produced_this_session": produced,
            "fraction": (n_done / total) if total else None,
            "distinct_cfgs": len(cfgs),
        },
        "session": {"start_epoch": session_start, "start": fmt_ts(session_start),
                    "basis": session_basis,
                    "elapsed_s": (now - session_start) if session_start else None},
        "clock": {"source": clock, "detail": times_basis, "samples": len(samples)},
        "rate": rates,
        "gaps": gaps,
        "projection": proj,
        "watcher": health,
        "prior_s_per_target": PRIOR_S_PER_TARGET,
    }


def render_text(s: dict) -> str:
    W = 84
    L: list[str] = []
    p, r, pr, w = s["progress"], s["rate"], s["projection"], s["watcher"]

    L.append("=" * W)
    L.append(f"NULL CONTROL -- progress monitor        {s['generated']}")
    L.append(f"checkpoint  {Path(s['checkpoint']).name}  "
             f"(last written {fmt_ts(s['checkpoint_mtime_epoch'])}, "
             f"{fmt_dur(s['checkpoint_age_s'])} ago)")
    L.append("=" * W)

    # The watcher first: a dead watcher outranks every number below it.
    L.append("")
    tag = "OK  " if w.get("healthy") else "DEAD"
    L.append(f"WATCHER    [{tag}] {w.get('message')}")
    if w.get("present"):
        L.append(f"           state={w.get('state')}  gpu_processes={w.get('gpu_processes')}  "
                 f"stale-after={w.get('stale_after_s'):.0f}s")
    if not w.get("healthy"):
        L.append("           *** the dashboard STOP button cannot free the GPU right now.  ***")
        L.append("           *** restart scripts/stop_watcher.sh inside WSL before leaving. ***")

    L.append("")
    L.append(f"PROGRESS   {p['done']} / {p['total']} targets done, {p['remaining']} remaining"
             + (f"  ({p['fraction']:.0%})" if p["fraction"] is not None else ""))
    L.append(f"           total basis: {p['total_basis']}")
    if p["carried_over"] is None:
        L.append(f"           carried over: UNKNOWN -- {p['carried_over_basis']}")
    else:
        L.append(f"           carried over from an earlier run: {p['carried_over']}  "
                 f"({p['carried_over_basis']})")
        L.append(f"           produced since this session resumed: {p['produced_this_session']}")
    if s["torn_lines"]:
        L.append(f"           {s['torn_lines']} unparseable line(s) skipped "
                 f"(a torn append is normal on a live file)")
    if p["distinct_cfgs"] > 1:
        L.append(f"           *** {p['distinct_cfgs']} DISTINCT cfgs in the checkpoint -- the "
                 f"run only reuses records matching its own cfg, so 'done' overstates it ***")

    L.append("")
    L.append(f"SESSION    resumed {s['session']['start']}  ({s['session']['basis']})"
             + (f", running {fmt_dur(s['session']['elapsed_s'])}"
                if s["session"]["elapsed_s"] else ""))
    L.append(f"           clock: {s['clock']['source']}")
    L.append(f"           {s['clock']['detail']}; {s['clock']['samples']} sample(s) on file")

    L.append("")
    if not r["sufficient"]:
        L.append(f"RATE       NOT MEASURABLE YET -- {r['targets_timed']} target(s) timed since "
                 f"the resume")
        L.append(f"           A rate needs >= {r['min_targets']}. This project's cost estimates "
                 f"have been wrong by")
        L.append(f"           more than 2x from exactly this move, so no rate is quoted here.")
        if r["targets_timed"] >= 1 and r["all_time_s_per_target"]:
            obs = r["all_time_s_per_target"]
            L.append("")
            L.append(f"           single observation, NOT a rate: {obs:.0f} s/target "
                     f"({fmt_dur(obs)}) over {r['targets_timed']} target(s)")
            if r.get("anchored_at_session_start"):
                L.append(f"           measured from the run's start, so it also contains model "
                         f"load and is an")
                L.append(f"           UPPER bound. One point has no spread and cannot show a "
                         f"trend; it is")
                L.append(f"           reported so the next reading has something to move "
                         f"against, and for")
                L.append(f"           no other purpose.")
        L.append(f"           (prior assumption, NOT a measurement: "
                 f"{s['prior_s_per_target']:.0f} s/target)")
        if s["clock"]["samples"] < 2:
            L.append(f"           Run with --watch to accumulate samples; one reading of an "
                     f"mtime cannot")
            L.append(f"           measure a rate.")
    else:
        lk = r["last_k_s_per_target"]
        at = r["all_time_s_per_target"]
        lab = f"last-{r['last_k_targets']} targets"
        L.append(f"RATE       {lab:<18}{lk:7.0f} s/target  ({fmt_dur(lk)}/target)")
        L.append(f"           {'all this session':<18}{at:7.0f} s/target  "
                 f"({r['targets_timed']} targets timed in {r['intervals']} interval(s))")
        if r.get("anchored_at_session_start"):
            L.append(f"           NOTE: {r['anchor_note']}")
        if r["spread_s_per_target"]:
            lo, hi = r["spread_s_per_target"]
            L.append(f"           per-interval spread {lo:.0f} - {hi:.0f} s/target")
        L.append(f"           vs the {s['prior_s_per_target']:.0f} s/target the run was "
                 f"budgeted with: "
                 f"{(at / s['prior_s_per_target'] - 1) * 100:+.0f}%")
        if r["same_window"]:
            L.append("           last-k and all-session are the same window so far -- no "
                     "stability claim yet.")
        elif r["stable"] is False:
            L.append("           " + "*" * (W - 11))
            L.append(f"           *** RATE DISAGREEMENT {r['disagreement']:.0%} -- the run is "
                     f"{r['direction']}.")
            L.append(f"           *** last-{r['last_k_targets']} {lk:.0f} s/target vs "
                     f"all-session {at:.0f} s/target. NOT averaged.")
            L.append(f"           *** Trust the last-{r['last_k_targets']} figure and watch "
                     f"the next reading; thermal throttling,")
            L.append(f"           *** memory pressure and a pathological target all look "
                     f"like this.")
            L.append("           " + "*" * (W - 11))
        else:
            L.append(f"           STABLE: last-{r['last_k_targets']} and all-session agree to "
                     f"{r['disagreement']:.0%} (limit {DISAGREE_FRAC:.0%}).")
        slow = r.get("slow_intervals", [])
        for sl in slow[-3:]:              # the most recent are the ones that still apply
            L.append(f"           slow stretch {fmt_ts(sl['t0'])} -> {fmt_ts(sl['t1'])}: "
                     f"{sl['per_target_s']:.0f} s/target "
                     f"({sl['ratio_to_median']:.1f}x median)")
        if len(slow) > 3:
            L.append(f"           ... and {len(slow) - 3} earlier slow stretch(es); the full "
                     f"list is in the JSON")

    L.append("")
    if pr["available"]:
        L.append(f"PROJECTION finish ~{fmt_ts(pr['eta_epoch'])}  "
                 f"(in {fmt_dur(pr['hours_remaining'] * 3600)})")
        L.append(f"           basis: {pr['basis']}")
        lo, hi = sorted([pr["eta_low_epoch"], pr["eta_high_epoch"]])
        if hi - lo > 60:
            L.append(f"           spread: {fmt_ts(lo)} .. {fmt_ts(hi)} "
                     f"({fmt_dur(hi - lo)} wide) across the rates below")
        else:
            L.append("           spread: the two rates agree to within a minute of ETA")
        for k, v in pr["candidates"].items():
            L.append(f"             {v:7.0f} s/target ({k}) -> "
                     f"{fmt_ts(pr['remaining'] * v + s['generated_epoch'])}")
    else:
        L.append(f"PROJECTION none. {pr.get('why', 'no rate')}")
        L.append(f"           A confident ETA off one data point is the exact failure this "
                 f"monitor exists to stop.")

    if s["gaps"]:
        L.append("")
        L.append("EXCLUDED   intervals not counted toward any rate:")
        for g in s["gaps"]:
            L.append(f"           {fmt_ts(g['t0'])} -> {fmt_ts(g['t1'])}  "
                     f"{fmt_dur(g['seconds'])} for {g['targets']} target(s) -- {g['reason']}")

    L.append("")
    return "\n".join(L)


# ---- IO shell -----------------------------------------------------------------------

def read_status(path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {"state": None, "detail": "status file unparseable (torn write?)"}


def resolve_total(explicit: int | None, targets_file) -> tuple[int, str]:
    if explicit:
        return explicit, "given on the command line"
    p = Path(targets_file)
    if p.exists():
        recs, _ = read_jsonl_tolerant(p)
        if recs:
            return len(recs), f"{p.name} ({len(recs)} false-alarm targets)"
    return 80, "default (80 false-alarm targets); target file not found"


def resolve_run_log(explicit) -> Path | None:
    if explicit:
        return Path(explicit)
    cands = sorted((REPO / "dashboard").glob(DEFAULT_RUN_LOG_GLOB),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def take_reading(args) -> dict:
    now = time.time()
    ckpt = Path(args.checkpoint)
    records, torn = read_jsonl_tolerant(ckpt)
    st = ckpt.stat() if ckpt.exists() else None
    mtime = st.st_mtime if st else None
    size = st.st_size if st else 0

    samples = load_samples(args.samples)
    sample = Sample(t=now, n=len(records), mtime=mtime or 0.0, size=size)
    if not args.no_record and mtime is not None:
        append_sample(args.samples, sample)
        samples = samples + [sample]

    session_start, session_basis = (
        (parse_epoch(args.session_start), "given on the command line")
        if args.session_start else find_session_start(resolve_run_log(args.run_log)))

    total, total_basis = resolve_total(args.total, args.targets_file)
    times, _ = record_completion_times(records)
    carried, carried_basis = infer_carried_over(
        len(records), mtime, [s for s in samples if s.t < now] or samples,
        session_start, times, args.carried_over)

    snap = build_snapshot(
        now=now, ckpt_path=ckpt, records=records, torn=torn, ckpt_mtime=mtime,
        ckpt_size=size, samples=samples, status=read_status(args.status),
        total=total, total_basis=total_basis, session_start=session_start,
        session_basis=session_basis, carried_over=carried, carried_basis=carried_basis,
        last_k=args.last_k, stale_after=args.stale_after,
        gap_abs=args.gap_seconds, gap_factor=args.gap_factor)

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        tmp = outp.with_suffix(outp.suffix + ".tmp")
        tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        tmp.replace(outp)          # the dashboard polls this; never let it read a half file
    return snap


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--status", default=str(DEFAULT_STATUS),
                    help="stop watcher's status file")
    ap.add_argument("--samples", default=str(DEFAULT_SAMPLES),
                    help="the monitor's own sample log; this is what makes a rate possible")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="JSON snapshot for the dashboard ('' to skip)")
    ap.add_argument("--targets-file", default=str(DEFAULT_TARGETS))
    ap.add_argument("--total", type=int, default=0, help="override the target count")
    ap.add_argument("--run-log", default="", help="overnight wrapper log (auto: newest)")
    ap.add_argument("--session-start", default="",
                    help="epoch or 'YYYY-MM-DD HH:MM:SS' if the log cannot be read")
    ap.add_argument("--carried-over", type=int, default=None,
                    help="records that predate this session, if the monitor cannot tell")
    ap.add_argument("--last-k", type=int, default=LAST_K)
    ap.add_argument("--stale-after", type=float, default=STALE_AFTER_S)
    ap.add_argument("--gap-seconds", type=float, default=GAP_ABS_S)
    ap.add_argument("--gap-factor", type=float, default=GAP_FACTOR)
    ap.add_argument("--no-record", action="store_true",
                    help="take a reading without appending to the sample log")
    ap.add_argument("--json", action="store_true", help="print the JSON snapshot only")
    ap.add_argument("--watch", type=float, default=0.0,
                    help="loop every N seconds (a rate needs at least two readings)")
    args = ap.parse_args(argv)

    while True:
        snap = take_reading(args)
        if args.json:
            print(json.dumps(snap, indent=2))
        else:
            print(render_text(snap))
        if not args.watch:
            return 0
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
