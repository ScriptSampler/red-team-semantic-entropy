"""Figures 1 and 2 of the paper: the ln(N) ceiling, and censoring of the attack's move.

POPULATION -- READ THIS BEFORE TOUCHING ANYTHING HERE.
------------------------------------------------------------------------------------
Everything in this file is computed on ONE population:

    the 80 CORRECT-ANSWER targets of the false-alarm arm of the attack campaign
    (TriviaQA, semantic entropy, N=10), definitive cell wk9_defb, complete at 80/80.

That is the correct-answer subset of the 97-target attacked pool. It is NOT the
200-correct + 200-hallucinating score-independent "fair pool" on which the detector's
AUROC (0.704) and class separation (0.463 nats) are measured. Binding a number to the
wrong one of those two populations is this project's most-repeated error -- found and
fixed at six separate sites. Every axis label, panel title, and emitted JSON record in
this script therefore names the pool explicitly, and scripts/check_population_labels.py
guards the .tex side. Do not "tidy" the population strings out of the labels.

WHY THESE PLOTS LOOK THE WAY THEY DO.
Semantic entropy at N=10 is a function of a partition of 10 sampled answers, so it is a
DISCRETE score: across these 80 clean baselines it takes 22 distinct values, one of which
is the ceiling ln(10) itself. Smoothing that into a KDE or a histogram with wide bins
would imply a continuum the estimator does not have, and the paper's central claim is
precisely that the continuum is absent. So Figure 1 is a stem (lollipop) plot drawn at
the exact attainable values, plus an explicit support ladder. No smoothing anywhere.

Run (Windows, reads the definitive JSONL over the WSL UNC share):
    .venv\\Scripts\\python.exe scripts\\make_ceiling_figures.py
Run (inside WSL):
    ./.venv-wsl/bin/python scripts/make_ceiling_figures.py

Writes figures/fig1_ceiling.pdf, figures/fig2_censoring.pdf and, beside each, the exact
numbers plotted (CSV for the per-point data, JSON for the summary statistics).

The script REFUSES to plot if the data no longer reproduces the verified numbers below;
a mismatch means the data or the verified list is wrong, which matters more than a figure.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "figures"

# ---------------------------------------------------------------------------------
# Population identity. Repeated verbatim into labels and into every emitted artefact.
# ---------------------------------------------------------------------------------
POOL_SHORT = "false-alarm attack pool (n=80 correct-answer targets)"
POOL_LONG = (
    "80 correct-answer targets of the false-alarm attack arm "
    "(TriviaQA, semantic entropy, N=10, definitive cell wk9_defb). "
    "NOT the 200+200 score-independent fair pool."
)

# ---------------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------------
CAP = math.log(10)          # 2.302585092994046 -- the ln(N) ceiling at the deployed N=10.

# "At the ceiling" tolerance. The saturated records land on the cap to within one ulp,
# so the counts (8 before, 42 after) are identical for every tolerance from 1e-12 to
# 1e-4; 1e-9 is the middle of that plateau, not a tuned choice.
CEIL_TOL = 1e-9

# Rounding used when counting DISTINCT attainable values. float64 accumulation makes
# three of the values differ from a twin in the last ulp (~2e-16), which inflates a raw
# np.unique count to 25. Any rounding from 3 to 12 decimals gives 22; 9 is well inside
# that plateau. 22 is the honest count of attainable values; 25 is float noise.
VALUE_DP = 9

TOP_TENTH_FRAC = 0.90       # "top tenth of the score's range" = [0.9*ln10, ln10].

# The numbers this script must reproduce before it is allowed to draw anything.
VERIFIED = {
    "n_targets": 80,
    "baseline_at_ceiling": 8,
    "after_at_ceiling": 42,
    "attack_induced_at_ceiling": 34,
    "baseline_in_top_tenth": 21,
    "distinct_baseline_values": 22,
}
# CORRELATIONS: the values in circulation were STALE. results/ceiling_saturation_finding.md
# and results/CORRECTIONS_2026-08-02.md quote corr(headroom, move) = +0.70, +0.67 within the
# uncensored subset. Those are the SUPERSEDED wk9_def cell (+0.703729 / +0.670386, uncensored
# n=41). The refresh banner at the top of that document recomputed only the five clean-baseline
# counts and left the correlations untouched. On the definitive wk9_defb cell the clean
# baselines are bit-identical (same 80 targets, same clean scores -- which is why all five
# counts are unchanged) but the attack moved further, so the uncensored subset shrank 41 -> 38
# and the correlations rose. Figures plot the DEFINITIVE values. The qualitative claim is
# unchanged and slightly strengthened: the relationship survives restriction to the uncensored
# subset, so it is not a censoring artefact.
VERIFIED_CORR = {           # (expected, tolerance) -- definitive wk9_defb
    "corr_headroom_move_all": (0.706985, 5e-6),
    "corr_headroom_move_uncensored": (0.676734, 5e-6),
}
SUPERSEDED_CORR = {         # wk9_def, for provenance only -- do not cite
    "corr_headroom_move_all": 0.703729,
    "corr_headroom_move_uncensored": 0.670386,
    "n_uncensored": 41,
    "cell": "wk9_def (superseded by wk9_defb)",
}

# Definitive input. The cell lives in the WSL home cache; on Windows it is reachable
# over the WSL UNC share. Order: --input, then $SE_FA_JSONL, then the known locations.
_REL = "samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl"
CANDIDATE_INPUTS = [
    Path(r"\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(r"\\wsl$\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(os.path.expanduser("~/.cache/se-research")) / _REL,
    Path("/home/abhi/.cache/se-research") / _REL,
    REPO / "results" / "wk9_defb" / "triviaqa_se_false_alarm.jsonl",
]


def resolve_input(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"--input does not exist: {p}")
        return p
    env = os.environ.get("SE_FA_JSONL")
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"SE_FA_JSONL does not exist: {p}")
        return p
    for p in CANDIDATE_INPUTS:
        try:
            if p.exists():
                return p
        except OSError:                      # UNC share unreachable on this host
            continue
    raise SystemExit(
        "could not locate the definitive false-alarm JSONL. Tried:\n  "
        + "\n  ".join(str(p) for p in CANDIDATE_INPUTS)
        + "\nPass --input /path/to/triviaqa_se_false_alarm.jsonl")


# ---------------------------------------------------------------------------------
# Load + derive.
# ---------------------------------------------------------------------------------
def load(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    qid = [r["question_id"] for r in rows]
    before = np.array([r["entropy_before"] for r in rows], dtype=float)
    after = np.array([r["entropy_after"] for r in rows], dtype=float)
    delta = np.array([r["delta"] for r in rows], dtype=float)

    # delta is stored, not recomputed; check the stored field agrees with the endpoints
    # so the two figures cannot silently disagree about what "the move" is.
    resid = float(np.abs(delta - (after - before)).max())
    if resid > 1e-12:
        raise SystemExit(f"delta != entropy_after - entropy_before (max err {resid:.3g})")
    if float(after.max()) > CAP + 1e-12 or float(before.max()) > CAP + 1e-12:
        raise SystemExit("an entropy exceeds the ln(10) ceiling -- data or CAP is wrong")

    pin_before = before >= CAP - CEIL_TOL
    pin_after = after >= CAP - CEIL_TOL
    return {
        "path": path,
        "qid": qid,
        "before": before,
        "after": after,
        "move": delta,
        "headroom": CAP - before,
        "pin_before": pin_before,
        "pin_after": pin_after,
        "success": np.array([bool(r["success"]) for r in rows]),
        "status_held": np.array([bool(r["status_held"]) for r in rows]),
    }


def stats(d: dict) -> dict:
    before, after, move, headroom = d["before"], d["after"], d["move"], d["headroom"]
    pin_b, pin_a = d["pin_before"], d["pin_after"]
    n = len(before)
    induced = (~pin_b) & pin_a
    top_tenth = before >= TOP_TENTH_FRAC * CAP
    uncens = ~pin_a                       # move not truncated by the ceiling

    def r(x, y):
        return float(np.corrcoef(x, y)[0, 1])

    return {
        "population": POOL_LONG,
        "source_file": str(d["path"]),
        "ceiling_nats": CAP,
        "ceiling_tolerance": CEIL_TOL,
        "distinct_value_rounding_dp": VALUE_DP,
        "n_targets": n,
        "baseline_at_ceiling": int(pin_b.sum()),
        "baseline_at_ceiling_pct": 100.0 * pin_b.sum() / n,
        "after_at_ceiling": int(pin_a.sum()),
        "after_at_ceiling_pct": 100.0 * pin_a.sum() / n,
        "attack_induced_at_ceiling": int(induced.sum()),
        "attack_induced_at_ceiling_pct": 100.0 * induced.sum() / n,
        "baseline_in_top_tenth": int(top_tenth.sum()),
        "baseline_in_top_tenth_pct": 100.0 * top_tenth.sum() / n,
        "top_tenth_threshold_nats": TOP_TENTH_FRAC * CAP,
        "distinct_baseline_values": len(set(np.round(before, VALUE_DP).tolist())),
        "distinct_after_values": len(set(np.round(after, VALUE_DP).tolist())),
        "distinct_union_values": len(set(np.round(np.concatenate([before, after]),
                                                  VALUE_DP).tolist())),
        "baseline_min_nats": float(before.min()),
        "baseline_max_nats": float(before.max()),
        "baseline_mean_nats": float(before.mean()),
        "baseline_median_nats": float(np.median(before)),
        "headroom_mean_nats": float(headroom.mean()),
        "headroom_median_nats": float(np.median(headroom)),
        "move_mean_nats": float(move.mean()),
        "move_median_nats": float(np.median(move)),
        "n_move_exactly_zero": int((move == 0).sum()),
        "n_move_negative": int((move < 0).sum()),
        "n_censored_at_ceiling": int(pin_a.sum()),
        "n_uncensored": int(uncens.sum()),
        "n_zero_headroom": int(pin_b.sum()),
        "corr_headroom_move_all": r(headroom, move),
        "corr_headroom_move_uncensored": r(headroom[uncens], move[uncens]),
        "n_success": int(d["success"].sum()),
        "n_status_held": int(d["status_held"].sum()),
    }


def verify(s: dict) -> list[str]:
    """Return a list of discrepancies against the pre-registered verified numbers."""
    bad = []
    for k, expected in VERIFIED.items():
        got = s[k]
        if got != expected:
            bad.append(f"{k}: expected {expected}, data gives {got}")
    for k, (expected, tol) in VERIFIED_CORR.items():
        got = s[k]
        if abs(got - expected) > tol:
            bad.append(f"{k}: expected {expected:+.2f} +/- {tol}, data gives {got:+.4f}")
    return bad


# ---------------------------------------------------------------------------------
# Shared style. Greyscale only -- no colour anywhere, so print and screen agree.
# ---------------------------------------------------------------------------------
INK = "0.0"
MID = "0.42"
PALE = "0.86"

plt.rcParams.update({
    "pdf.fonttype": 42,          # embed TrueType, keep text selectable/searchable
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def counts_at_values(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = Counter(np.round(x, VALUE_DP).tolist())
    vals = np.array(sorted(c), dtype=float)
    return vals, np.array([c[v] for v in vals], dtype=float)


# ---------------------------------------------------------------------------------
# FIGURE 1 -- the ceiling.
# ---------------------------------------------------------------------------------
def figure1(d: dict, s: dict) -> None:
    before, after = d["before"], d["after"]
    n = s["n_targets"]
    vb, cb = counts_at_values(before)
    va, ca = counts_at_values(after)

    # Both panels share one y-axis on purpose. The comparison IS the finding, and a
    # per-panel rescale would flatter the clean panel and hide how far the cap atom
    # towers over every other attainable value after the attack.
    ymax = max(cb.max(), ca.max())
    ylim = (0, ymax * 1.30)

    fig = plt.figure(figsize=(7.0, 3.95))
    gs = GridSpec(3, 1, height_ratios=[1.0, 1.0, 0.22], hspace=0.46,
                  left=0.068, right=0.995, top=0.945, bottom=0.135)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1], sharex=ax_a)
    ax_l = fig.add_subplot(gs[2], sharex=ax_a)

    def draw(ax, vals, cnts, marker):
        at_cap = vals >= CAP - CEIL_TOL
        # top-tenth band, drawn first so stems sit on top of it
        ax.axvspan(TOP_TENTH_FRAC * CAP, CAP, color=PALE, lw=0, zorder=0)
        ax.axvline(CAP, color=INK, ls=(0, (4, 2)), lw=0.9, zorder=1)
        ax.vlines(vals[~at_cap], 0, cnts[~at_cap], color=MID, lw=1.1, zorder=2)
        ax.plot(vals[~at_cap], cnts[~at_cap], marker, ms=3.4, color=MID,
                mec=INK, mew=0.5, ls="none", zorder=3)
        ax.vlines(vals[at_cap], 0, cnts[at_cap], color=INK, lw=2.4, zorder=4)
        ax.plot(vals[at_cap], cnts[at_cap], marker, ms=5.8, color=INK,
                mec=INK, mew=0.6, ls="none", zorder=5)
        ax.set_ylim(*ylim)
        ax.set_xlim(-0.06, 2.46)
        ax.set_yticks([0, 10, 20, 30, 40])
        ax.set_ylabel(f"targets\n(of {n})", linespacing=1.15)
        ax.spines["bottom"].set_position(("outward", 2))

    draw(ax_a, vb, cb, "o")
    draw(ax_b, va, ca, "s")

    # ---- panel (a) --------------------------------------------------------------
    ax_a.set_title(f"(a)  Clean semantic entropy, before any attack \u2014 {POOL_SHORT}",
                   loc="left", pad=3.5)
    # Band label: a bracket over the shaded region, text to its left. No arrow, so it
    # cannot cross the ceiling callout below it.
    y_br = ylim[1] * 0.86
    ax_a.plot([TOP_TENTH_FRAC * CAP, CAP], [y_br, y_br], color=INK, lw=0.7, zorder=6)
    for xb in (TOP_TENTH_FRAC * CAP, CAP):
        ax_a.plot([xb, xb], [y_br - ylim[1] * 0.035, y_br], color=INK, lw=0.7, zorder=6)
    ax_a.text(TOP_TENTH_FRAC * CAP - 0.05, y_br,
              f"top tenth of the range [{s['top_tenth_threshold_nats']:.2f}, {CAP:.2f}]:  "
              f"{s['baseline_in_top_tenth']}/{n} = {s['baseline_in_top_tenth_pct']:.1f}% "
              "of clean baselines",
              ha="right", va="center", fontsize=7)
    n_cap_b = s["baseline_at_ceiling"]
    ax_a.annotate(
        f"{n_cap_b}/{n} = {s['baseline_at_ceiling_pct']:.0f}% of these CORRECT answers "
        "are already pinned\nat the ceiling before any attack \u2014 the detector has no "
        "room left to score them",
        xy=(CAP, n_cap_b), xycoords="data",
        xytext=(CAP - 0.34, ylim[1] * 0.55), textcoords="data",
        ha="right", va="center", linespacing=1.3,
        arrowprops=dict(arrowstyle="-|>", lw=0.7, color=INK,
                        shrinkA=2.0, shrinkB=3.0,
                        connectionstyle="arc3,rad=-0.20"))
    ax_a.text(CAP + 0.075, ylim[1] * 0.99, r"ceiling  $\ln 10 = 2.303$",
              ha="right", va="top", rotation=90, fontsize=7)

    # ---- panel (b) --------------------------------------------------------------
    ax_b.set_title("(b)  After the optimised paraphrase attack \u2014 the same 80 targets",
                   loc="left", pad=3.5)
    n_cap_a = s["after_at_ceiling"]
    ax_b.annotate(
        f"{n_cap_a}/{n} = {s['after_at_ceiling_pct']:.1f}% now sit exactly at the ceiling; "
        f"{s['attack_induced_at_ceiling']}/{n} = "
        f"{s['attack_induced_at_ceiling_pct']:.1f}%\nof that is attack-induced "
        "(the other 8 were pinned already)",
        xy=(CAP, n_cap_a), xycoords="data",
        xytext=(CAP - 0.34, ylim[1] * 0.58), textcoords="data",
        ha="right", va="center", linespacing=1.3,
        arrowprops=dict(arrowstyle="-|>", lw=0.7, color=INK,
                        shrinkA=2.0, shrinkB=3.0,
                        connectionstyle="arc3,rad=0.16"))

    # ---- (c) support ladder ------------------------------------------------------
    ax_l.axvspan(TOP_TENTH_FRAC * CAP, CAP, color=PALE, lw=0, zorder=0)
    ax_l.axvline(CAP, color=INK, ls=(0, (4, 2)), lw=0.9, zorder=1)
    ax_l.vlines(vb[vb < CAP - CEIL_TOL], 0.06, 0.72, color=MID, lw=1.1, zorder=2)
    ax_l.vlines(vb[vb >= CAP - CEIL_TOL], 0.0, 0.86, color=INK, lw=2.4, zorder=3)
    ax_l.set_ylim(0, 1.55)
    ax_l.set_yticks([])
    ax_l.spines["left"].set_visible(False)
    ax_l.spines["bottom"].set_visible(False)
    ax_l.text(-0.06, 1.50,
              f"(c)  the estimator's entire support on these 80 clean baselines: "
              f"{s['distinct_baseline_values']} attainable values, the top one being the "
              "ceiling itself",
              ha="left", va="top", fontsize=7)
    ax_l.set_xlabel("semantic entropy (nats), N = 10 sampled answers "
                    f"\u2014 {POOL_SHORT}")
    ax_l.set_xticks(np.arange(0, 2.5, 0.25))

    for ax in (ax_a, ax_b):
        plt.setp(ax.get_xticklabels(), visible=False)
        ax.tick_params(axis="x", length=0)

    out = FIG_DIR / "fig1_ceiling.pdf"
    fig.savefig(out)
    fig.savefig(FIG_DIR / "fig1_ceiling.png", dpi=220)
    plt.close(fig)

    # ---- the exact numbers plotted ------------------------------------------------
    allv = sorted(set(vb.tolist()) | set(va.tolist()))
    cbm, cam = dict(zip(vb.tolist(), cb.tolist())), dict(zip(va.tolist(), ca.tolist()))
    with open(FIG_DIR / "fig1_ceiling_data.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["# population", POOL_LONG])
        w.writerow(["# source", str(d["path"])])
        w.writerow(["# ceiling_nats", repr(CAP)])
        w.writerow(["entropy_nats", "n_baseline", "n_after", "at_ceiling",
                    "in_top_tenth_of_range"])
        for v in allv:
            w.writerow([f"{v:.9f}", int(cbm.get(v, 0)), int(cam.get(v, 0)),
                        int(v >= CAP - CEIL_TOL), int(v >= TOP_TENTH_FRAC * CAP)])
    print(f"  wrote {out.name}, fig1_ceiling.png, fig1_ceiling_data.csv")


# ---------------------------------------------------------------------------------
# FIGURE 2 -- censoring.
# ---------------------------------------------------------------------------------
def figure2(d: dict, s: dict) -> None:
    hr, mv = d["headroom"], d["move"]
    pin_b, pin_a = d["pin_before"], d["pin_after"]
    n = s["n_targets"]

    zero_hr = pin_b                      # 8: no room at all, move is 0 by construction
    censored = pin_a & ~pin_b            # 34: room existed, attack consumed all of it
    uncens = ~pin_a                      # 38: move stopped short of the ceiling

    fig, ax = plt.subplots(figsize=(3.45, 4.30))
    fig.subplots_adjust(left=0.145, right=0.985, top=0.865, bottom=0.325)

    lim = 2.44
    # The censoring frontier. A target cannot move further than its own headroom, so
    # move <= headroom for every point: the region ABOVE y = x is structurally empty.
    # Shading it says so, and frees the only uncluttered space on the panel for labels.
    xs_fill = np.array([-0.08, lim])
    ax.fill_between(xs_fill, xs_fill, lim, color="0.945", lw=0, zorder=0)
    ax.plot([0, CAP], [0, CAP], color=INK, lw=0.9, ls=(0, (4, 2)), zorder=3)

    # OLS fits. Both are drawn because the paper's point is that the relationship
    # SURVIVES restriction to the uncensored subset, i.e. it is not a boundary artefact.
    xs = np.linspace(0, CAP, 50)
    ka, kb = np.polyfit(hr, mv, 1)
    ax.plot(xs, ka * xs + kb, color=INK, lw=1.3, zorder=2)
    ua, ub = np.polyfit(hr[uncens], mv[uncens], 1)
    ax.plot(xs, ua * xs + ub, color=MID, lw=1.3, ls=(0, (1.6, 1.4)), zorder=2)

    ax.plot(hr[uncens], mv[uncens], "o", ms=4.0, mfc="white", mec=INK, mew=0.7,
            ls="none", zorder=4)
    ax.plot(hr[censored], mv[censored], "^", ms=4.4, mfc=INK, mec=INK, mew=0.5,
            ls="none", zorder=5)
    ax.plot(hr[zero_hr], mv[zero_hr], "s", ms=6.2, mfc=INK, mec=INK, mew=0.5,
            ls="none", zorder=6)

    # Both callouts live in the empty triangle above the frontier.
    ax.text(0.10, lim - 0.05,
            "structurally empty:\nthe move cannot exceed\nthe target's headroom",
            ha="left", va="top", fontsize=6.5, linespacing=1.3, color="0.30")
    ax.annotate(f"{int(zero_hr.sum())} targets stacked here \u2014\n"
                "zero headroom, zero move,\nzero successes",
                xy=(0.02, 0.03), xycoords="data",
                xytext=(0.115, 1.02), textcoords="data",
                fontsize=6.5, ha="left", va="bottom", linespacing=1.3,
                arrowprops=dict(arrowstyle="-|>", lw=0.7, color=INK,
                                shrinkA=1.5, shrinkB=2.5))

    ax.set_xlim(-0.08, lim)
    ax.set_ylim(-0.08, lim)
    ax.set_aspect("equal")
    ax.set_xticks(np.arange(0, 2.5, 0.5))
    ax.set_yticks(np.arange(0, 2.5, 0.5))
    ax.set_xlabel("headroom before the attack:\n"
                  "$\\ln 10 -$ clean entropy  (nats)", linespacing=1.3)
    ax.set_ylabel("attack's move:  $\\Delta$ entropy  (nats)")
    ax.set_title("Where the ceiling censors the attack\n"
                 f"{POOL_SHORT}", loc="left", pad=4, linespacing=1.4)

    handles = [
        Line2D([], [], marker="o", ls="none", ms=4.0, mfc="white", mec=INK, mew=0.7,
               label=f"uncensored \u2014 below the ceiling after ({int(uncens.sum())})"),
        Line2D([], [], marker="^", ls="none", ms=4.4, mfc=INK, mec=INK,
               label=f"censored \u2014 attack drove it to the ceiling ({int(censored.sum())})"),
        Line2D([], [], marker="s", ls="none", ms=6.2, mfc=INK, mec=INK,
               label=f"zero headroom \u2014 pinned before the attack ({int(zero_hr.sum())})"),
        Line2D([], [], color=INK, lw=1.3,
               label=f"OLS, all {n}:  $r = {s['corr_headroom_move_all']:+.2f}$"),
        Line2D([], [], color=MID, lw=1.3, ls=(0, (1.6, 1.4)),
               label=f"OLS, uncensored {int(uncens.sum())}:  "
                     f"$r = {s['corr_headroom_move_uncensored']:+.2f}$"),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(-0.155, -0.235),
              frameon=False, handletextpad=0.5, labelspacing=0.34, borderpad=0.0)

    out = FIG_DIR / "fig2_censoring.pdf"
    fig.savefig(out)
    fig.savefig(FIG_DIR / "fig2_censoring.png", dpi=220)
    plt.close(fig)

    with open(FIG_DIR / "fig2_censoring_data.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["# population", POOL_LONG])
        w.writerow(["# source", str(d["path"])])
        w.writerow(["# ceiling_nats", repr(CAP)])
        w.writerow(["question_id", "entropy_before_nats", "entropy_after_nats",
                    "headroom_nats", "move_nats", "group", "success", "status_held"])
        for i, q in enumerate(d["qid"]):
            grp = ("zero_headroom" if zero_hr[i] else
                   "censored_at_ceiling" if censored[i] else "uncensored")
            w.writerow([q, f"{d['before'][i]:.9f}", f"{d['after'][i]:.9f}",
                        f"{hr[i]:.9f}", f"{mv[i]:.9f}", grp,
                        int(d["success"][i]), int(d["status_held"][i])])
    print(f"  wrote {out.name}, fig2_censoring.png, fig2_censoring_data.csv")

    return {"ols_all_slope": float(ka), "ols_all_intercept": float(kb),
            "ols_uncensored_slope": float(ua), "ols_uncensored_intercept": float(ub)}


# ---------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=None, help="path to the false-alarm JSONL")
    ap.add_argument("--check-only", action="store_true",
                    help="verify the numbers and print them, draw nothing")
    args = ap.parse_args()

    path = resolve_input(args.input)
    print(f"source: {path}")
    d = load(path)
    s = stats(d)

    print(f"population: {POOL_LONG}\n")
    width = max(len(k) for k in s)
    for k, v in s.items():
        if isinstance(v, float):
            print(f"  {k:<{width}}  {v:.6f}")
        elif isinstance(v, int):
            print(f"  {k:<{width}}  {v}")
    print()

    bad = verify(s)
    if bad:
        print("REFUSING TO PLOT -- data does not reproduce the verified numbers:",
              file=sys.stderr)
        for b in bad:
            print("  " + b, file=sys.stderr)
        print("\nEither the data changed or the verified list is wrong. Resolve that "
              "before drawing anything.", file=sys.stderr)
        return 2
    print(f"verified: all {len(VERIFIED) + len(VERIFIED_CORR)} pre-registered numbers "
          f"reproduce exactly.")
    if args.check_only:
        return 0

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    figure1(d, s)
    fits = figure2(d, s)
    s["figure2_fits"] = fits
    s["verified_against"] = {**VERIFIED,
                             **{k: v[0] for k, v in VERIFIED_CORR.items()}}
    s["superseded_wk9_def_correlations"] = SUPERSEDED_CORR
    (FIG_DIR / "ceiling_figures_stats.json").write_text(
        json.dumps(s, indent=2), encoding="utf-8")
    print(f"  wrote ceiling_figures_stats.json")
    print(f"\nfigures/ written under {FIG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
