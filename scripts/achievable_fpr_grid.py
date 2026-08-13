"""The ACHIEVABLE FALSE-POSITIVE-RATE GRID of semantic entropy at N=10.

WHY THIS EXISTS
---------------
The paper currently states its granularity finding as "the top tenth of the score's RANGE
contains only two attainable values". That cut -- 0.9 x ln N -- is arbitrary: it is a cut on
the scale, no operator uses it, and the paper never connects it to an operating point. A
false alarm does not have to reach the top decile of the range; it has to cross the DEPLOYED
THRESHOLD.

This script states the same fact in the currency an operator actually uses. The detector
flags when score >= tau, so its false-positive rate is a step function of tau that can only
change at a value some clean correct answer actually took. Semantic entropy at N=10 has a
large ATOM at the ceiling ln(10) and another at 2.163956, so the set of FPRs the detector can
be operated at is a short, coarse, FINITE list. In particular:

    the smallest NON-ZERO FPR any threshold can realise
      == the fraction of clean CORRECT answers sitting exactly at ln(N).

There is no threshold below it: every tau above ln(10) flags nothing at all. So an operator
who wants a 5% false-alarm rate cannot have one -- not because the detector is badly
calibrated, but because that operating point does not exist. This is
`sun2026granularity`'s thesis ("so few distinct values that an operator has only a handful of
usable thresholds") instantiated with measured numbers on a named population, and it makes
the top-decile framing unnecessary.

WHAT IS COMPUTED, AND ON WHICH POPULATION
-----------------------------------------
A false positive is a CORRECT answer that gets flagged, so the negatives are the correct
stratum. FPR conditions on the negatives, so it is PREVALENCE-FREE: the "400-item fair pool"
and the "fair pool's correct stratum" have the SAME FPR grid, and class balance changes only
the alert volume and the precision, both of which are reported separately in section 5.

  * headline  -- fair pool, correct stratum, n=200 negatives (positives: the fair pool's
                 hallucinating stratum, n=200). This is the population the paper's own rule
                 in `paper/sections/methods.tex` names for anything that characterises the
                 detector, and the one carrying clean AUROC 0.704 [0.653, 0.753].
  * precision -- full labelled Week-4 pool, correct stratum, n=1424 negatives (positives:
                 n=576). The fair pool's correct stratum is a strict SUBSET of this, so it
                 estimates the same parameter with 7x the negatives; it is the control that
                 shows the coarseness at the top is a property of the SCORE and not of the
                 n=200 sampling resolution.

Everything is CPU-only: the clean scores are the `entropy_nats` field of the Week-4
span-oracle cache `relabeled.jsonl`. No GPU, no model, no attack data.

USES THE FIXED OPERATING-POINT CODE
-----------------------------------
`se.stats.attainable_fprs` and `se.stats.operating_point` were corrected on 2026-08-13
(defect 1: the old quantile rule's achieved FPR was up to 6x its target on an atomic score).
Nothing here reimplements the threshold rule; the achieved FPR reported for every operating
point is the one `operating_point` returns, and it is cross-checked against a direct
`mean(neg >= tau)` recomputation.

Run (Windows, reads the cache over the WSL UNC share):
    .venv\\Scripts\\python.exe scripts\\achievable_fpr_grid.py
Run (inside WSL):
    ./.venv-wsl/bin/python scripts/achievable_fpr_grid.py

Writes results/achievable_fpr_grid.md, figures/fig_achievable_roc.{pdf,png} and
figures/fig_achievable_roc_data.csv (the exact plotted points).
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import math
import os
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = REPO_ROOT / "figures"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Reuse, do not reimplement: the fair-pool id selection, the Wilson interval and the
# attainable-lattice enumeration all already exist and are already reviewed.
from fair_pool_granularity import (                                     # noqa: E402
    DP, N_PER_STRATUM, SEED, attainable_lattice, fair_pool_ids, wilson,
)
from se.attacks.select import load_labels                               # noqa: E402
from se.stats import attainable_fprs, operating_point                   # noqa: E402

N_SAMPLES = 10
CAP = math.log(N_SAMPLES)                 # ln(10) = 2.302585..., the attainable maximum
TOP_DECILE = 0.9 * CAP                    # the framing this file is arguing should be retired
NOMINAL_TARGETS = (0.01, 0.05, 0.10, 0.20)
TOL = 1e-9                                # "equal score" tolerance, == 10**-DP

_REL = "samples/wk4_full_2000q/relabeled.jsonl"
CANDIDATE_LABELS = [
    Path(r"\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(r"\\wsl$\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(os.path.expanduser("~/.cache/se-research")) / _REL,
    Path("/home/abhi/.cache/se-research") / _REL,
]


def resolve_labels(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"--labels does not exist: {p}")
        return p
    env = os.environ.get("SE_RELABELED_JSONL")
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"SE_RELABELED_JSONL does not exist: {p}")
        return p
    for p in CANDIDATE_LABELS:
        try:
            if p.exists():
                return p
        except OSError:
            continue
    raise SystemExit(
        "relabeled.jsonl not found. Tried:\n  " + "\n  ".join(str(p) for p in CANDIDATE_LABELS)
        + "\nPass --labels or set SE_RELABELED_JSONL.")


def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


# ---------------------------------------------------------------------------- the grid
def grid(neg: np.ndarray, pos: np.ndarray) -> list[dict]:
    """Every operating point the detector can be run at, ascending threshold.

    `se.stats.attainable_fprs` supplies the (threshold, FPR) pairs -- the detector flags at
    `score >= tau`, so the FPR only changes at an observed negative value, and the trailing
    (+inf, 0) sentinel is the always-available "never fire" policy. We add the TPR each
    threshold realises on the positives, and cross-check the FPR against a direct
    recomputation so a reported rate can never drift from the realised one.
    """
    vals, fprs = attainable_fprs(neg)
    rows = []
    for tau, fpr in zip(vals, fprs):
        k_fp = int((neg >= tau).sum())
        k_tp = int((pos >= tau).sum())
        assert abs(k_fp / len(neg) - fpr) < 1e-12, "attainable_fprs disagrees with `>=`"
        rows.append({
            "threshold": float(tau),
            "k_fp": k_fp, "n_neg": len(neg), "fpr": k_fp / len(neg),
            "k_tp": k_tp, "n_pos": len(pos), "tpr": k_tp / len(pos),
            "fires": bool(np.isfinite(tau)),
        })
    rows.reverse()                       # descending threshold == ascending FPR: reading order
    return rows


def n_firing_below(rows: list[dict], t: float) -> int:
    return sum(1 for r in rows if r["fires"] and r["fpr"] <= t + 1e-12)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=None)
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()

    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    labels_path = resolve_labels(args.labels)
    labels = load_labels(labels_path)
    emap = {q: float(l["entropy_nats"]) for q, l in labels.items()}
    fair_right, fair_wrong = fair_pool_ids(labels)
    assert len(fair_right) == len(fair_wrong) == N_PER_STRATUM

    # Round to DP places BEFORE anything touches the grid. This is not cosmetic: see §6.
    neg_fair = np.array([round(emap[q], DP) for q in fair_right])
    pos_fair = np.array([round(emap[q], DP) for q in fair_wrong])
    neg_fair_raw = np.array([emap[q] for q in fair_right])
    neg_full = np.array([round(float(l["entropy_nats"]), DP)
                         for l in labels.values() if l["greedy_correct"]])
    pos_full = np.array([round(float(l["entropy_nats"]), DP)
                         for l in labels.values() if not l["greedy_correct"]])
    n_total = len(neg_full) + len(pos_full)
    prevalence = len(pos_full) / n_total

    lattice = [round(v, DP) for v in attainable_lattice(N_SAMPLES)]
    assert not (set(neg_fair.tolist()) | set(pos_fair.tolist())) - set(lattice), \
        "a realised score is not on the N=10 attainable lattice"
    att_top = [v for v in lattice if v >= TOP_DECILE - 1e-12]
    lat20 = attainable_lattice(20)
    att20_top = [v for v in lat20 if v >= 0.9 * math.log(20) - 1e-12]

    g_fair = grid(neg_fair, pos_fair)
    g_full = grid(neg_full, pos_full)
    fire_fair = [r for r in g_fair if r["fires"]]
    fire_full = [r for r in g_full if r["fires"]]
    # The lowest non-zero attainable FPR: the ceiling atom, by construction.
    lo_fair, lo_full = fire_fair[0], fire_full[0]
    second_fair = fire_fair[1]

    # =================================================================== header
    log("# The achievable false-positive-rate grid of semantic entropy at N=10")
    log("")
    log(f"Generated {_dt.date.today().isoformat()} by `scripts/achievable_fpr_grid.py` "
        "(CPU only; no GPU, no model, no attack data).")
    log(f"Clean scores: `entropy_nats` of the Week-4 span-oracle cache `{_REL}`.")
    log("Threshold rule and achieved FPRs come from `se.stats.attainable_fprs` /")
    log("`se.stats.operating_point` (the versions FIXED on 2026-08-13); nothing here")
    log("reimplements the quantile rule they replaced.")
    log("")
    log("## The claim in one line")
    log("")
    log("> A detector that flags when `score >= tau` can only change its false-positive rate")
    log("> at a value some clean correct answer actually took. Semantic entropy at N=10 takes")
    log(f"> **{len(lattice)}** values in total and **{len(att_top)}** above 0.9 x ln 10, and it")
    log("> puts an ATOM on the top one. So the false-alarm rates an operator can select from")
    log(f"> are a short finite list, and its smallest non-zero entry is "
        f"**{lo_fair['fpr']:.1%}** "
        f"[{wilson(lo_fair['k_fp'], lo_fair['n_neg'])[1]:.1%}, "
        f"{wilson(lo_fair['k_fp'], lo_fair['n_neg'])[2]:.1%}]")
    log(f"> (fair pool, correct stratum, n={lo_fair['n_neg']}). **An operator who wants a 5%")
    log("> false-alarm rate cannot have one.** The next rate up is "
        f"**{second_fair['fpr']:.1%}**; between them there is nothing.")
    log("")
    log("Why the smallest non-zero FPR is exactly the ceiling atom, by construction: the")
    log(f"largest value the estimator can emit is ln({N_SAMPLES}) = {CAP:.4f}, so every")
    log("threshold above it flags nothing, and the first threshold that fires at all is")
    log(f"tau = ln({N_SAMPLES}) itself, which flags EVERY negative at the ceiling and no other.")
    log("The minimum non-zero attainable FPR is therefore not a tuning choice; it is")
    log("P(a clean correct answer produces N mutually distinct meanings).")
    log("")

    # =================================================================== 1. the grid
    log(f"## 1. The full grid, fair pool correct stratum (n={len(neg_fair)} negatives)")
    log("")
    log("Every operating point the detector can be run at, ascending FPR. FPR is measured on")
    log(f"the fair pool's **correct** stratum (n={len(neg_fair)}); TPR on its **hallucinating**")
    log(f"stratum (n={len(pos_fair)}). Wilson 95% intervals. `tau = inf` is the always-available")
    log("\"never fire\" policy; it is a real operating point and it is the only one below")
    log(f"{lo_fair['fpr']:.1%}.")
    log("")
    log("| # | threshold tau (nats) | FPR (false alarms on correct answers) | "
        "TPR (hallucinations caught) | in top tenth of range? |")
    log("| --- | --- | --- | --- | --- |")
    for i, r in enumerate(g_fair):
        tau = "inf (never fire)" if not r["fires"] else f"{r['threshold']:.6f}"
        top = ("yes" if r["fires"] and r["threshold"] >= TOP_DECILE - 1e-12 else "-")
        log(f"| {i} | {tau} | {fmt_prop(r['k_fp'], r['n_neg'])} | "
            f"{fmt_prop(r['k_tp'], r['n_pos'])} | {top} |")
    log("")
    log(f"**{len(g_fair)} operating points in total, {len(fire_fair)} of which fire.** The two")
    log("that matter for any realistic false-alarm budget are rows 0-2:")
    log("")
    log(f"- `tau > {CAP:.4f}` -> FPR **0%**, TPR **0%** (flags nothing);")
    log(f"- `tau = {lo_fair['threshold']:.4f}` (= ln 10) -> FPR "
        f"**{lo_fair['fpr']:.1%}**, TPR **{lo_fair['tpr']:.1%}**;")
    log(f"- `tau = {second_fair['threshold']:.4f}` -> FPR "
        f"**{second_fair['fpr']:.1%}**, TPR **{second_fair['tpr']:.1%}**.")
    log("")
    log("How many FIRING operating points exist below a given false-alarm budget -- this is")
    log("`sun2026granularity`'s \"handful of usable thresholds\", counted:")
    log("")
    log("| false-alarm budget | firing operating points at or below it "
        f"(fair pool, n={len(neg_fair)}) | (full pool, n={len(neg_full)}) |")
    log("| --- | --- | --- |")
    for t in (0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.50, 1.00):
        log(f"| FPR <= {t:.0%} | **{n_firing_below(g_fair, t)}** | "
            f"{n_firing_below(g_full, t)} |")
    log("")

    # ============================================== 2. what the nominal targets get
    log("## 2. Which nominal operating points are ACHIEVABLE (and what asking for one costs)")
    log("")
    log("`operating_point(..., mode=...)` on the fair pool's correct stratum. `at_most` is the")
    log("contract an operator states (\"my false-alarm budget is X\"); `closest` is what a")
    log("measurement wants (the nearest real operating point, which may be above budget);")
    log("`nominal_quantile` is the historical rule, kept only to show what it did.")
    log("")
    log("Two different questions hide under the word \"achievable\" and the table keeps them")
    log("apart. *Budget honourable*: is there any firing threshold at or below the target")
    log("(what `at_most` answers)? *Rate achievable*: is the target itself one of the rates on")
    log("the grid? The second is the granularity question; the first is what an operator")
    log("actually gets told.")
    log("")
    log("| target FPR | `at_most`: tau | achieved FPR | TPR | `closest`: achieved FPR | TPR | "
        "`nominal_quantile`: achieved FPR | budget honourable? | rate achievable? |")
    log("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    y = np.concatenate([np.zeros(len(neg_fair), int), np.ones(len(pos_fair), int)])
    s = np.concatenate([neg_fair, pos_fair])
    target_rows = []
    for t in NOMINAL_TARGETS:
        op_a = operating_point(y, s, target_fpr=t, mode="at_most")
        op_c = operating_point(y, s, target_fpr=t, mode="closest")
        op_q = operating_point(y, s, target_fpr=t, mode="nominal_quantile")
        tpr_a = float((pos_fair >= float(op_a)).mean())
        tpr_c = float((pos_fair >= float(op_c)).mean())
        # cross-check: the FPR the object reports IS the one the `>=` rule realises
        for op in (op_a, op_c, op_q):
            assert abs(op.achieved_fpr - float((neg_fair >= float(op)).mean())) < 1e-12
        exact = any(abs(r["fpr"] - t) < 1e-12 for r in g_fair)
        tau_a = "inf" if not np.isfinite(op_a.threshold) else f"{op_a.threshold:.4f}"
        log(f"| {t:.0%} | {tau_a} | **{op_a.achieved_fpr:.1%}**"
            f"{' (flags nothing)' if op_a.flags_nothing else ''} | {tpr_a:.1%} | "
            f"{op_c.achieved_fpr:.1%}"
            f"{'' if op_c.honours_contract else ' **over budget**'} | {tpr_c:.1%} | "
            f"{op_q.achieved_fpr:.1%}"
            f"{'' if op_q.honours_contract else ' **over budget**'} | "
            f"{'no -- flags nothing' if op_a.flags_nothing else 'yes, at ' + format(op_a.achieved_fpr, '.1%')} | "
            f"{'YES' if exact else '**NO**'} |")
        target_rows.append((t, op_a, op_c, op_q, tpr_a, tpr_c))
    log("")
    p_lo, lo_lo, lo_hi = wilson(lo_fair["k_fp"], lo_fair["n_neg"])
    log("**Reading the `rate achievable?` column.** No threshold realises 1%, 5%, 10% or 20% on")
    log("this population. For 1% and 5% that is not a sampling accident and can be stated with")
    log("confidence: every firing threshold has FPR at least the ceiling-atom mass, estimated")
    log(f"{lo_fair['k_fp']}/{lo_fair['n_neg']} = {p_lo:.1%} with a Wilson 95% lower bound of "
        f"**{lo_lo:.1%}**, so at 95% confidence")
    log("*no operating point of any kind exists at or below a 5% false-alarm rate except the")
    log("degenerate one that flags nothing*. For 10% and 20% the honest statement is weaker:")
    log(f"they fall strictly BETWEEN adjacent attainable points ({lo_fair['fpr']:.1%} and "
        f"{second_fair['fpr']:.1%}, and {second_fair['fpr']:.1%} and")
    log(f"{fire_fair[2]['fpr']:.1%}), and the Wilson intervals of those points "
        f"[{lo_lo:.1%}, {lo_hi:.1%}] and "
        f"[{wilson(second_fair['k_fp'], second_fair['n_neg'])[1]:.1%}, "
        f"{wilson(second_fair['k_fp'], second_fair['n_neg'])[2]:.1%}] cover them, so the data")
    log("cannot rule out that one of those two thresholds runs at exactly 10% or 20% in the")
    log("population. That is itself an operational cost and section 4 gives it a name.")
    log("")
    log("**What asking for 5% costs.** `at_most` at a 5% budget returns `tau = inf`: the only")
    log("way to honour a 5% false-alarm budget is to flag nothing, catching **0%** of")
    log("hallucinations. Accept the nearest real point instead and the budget is blown by a")
    log(f"factor of {lo_fair['fpr']/0.05:.1f}x -- {lo_fair['fpr']:.1%} FPR -- for a TPR of "
        f"{lo_fair['tpr']:.1%}. There is no third option, and")
    log("that is the whole of the operator's menu below a 21.5% false-alarm rate.")
    log("")
    log("(The `nominal_quantile` column is the defect this file's tooling was fixed for: the")
    log("old rule, asked for 10%, returned a threshold that runs at "
        f"{[r[3].achieved_fpr for r in target_rows if r[0] == 0.10][0]:.1%}. It did not fail")
    log("because 10% is hard to hit -- it failed because 10% does not exist, and interpolating")
    log("between order statistics hides that by landing inside an atom.)")
    log("")

    # ========================================= 3. the atom is indivisible
    log("## 3. Why there is nothing in between: the ceiling atom is indivisible")
    log("")
    n_cap_neg = int((neg_fair >= CAP - TOL).sum())
    n_cap_pos = int((pos_fair >= CAP - TOL).sum())
    n_cap = n_cap_neg + n_cap_pos
    log(f"At `tau = ln 10` the detector flags every item at the ceiling: "
        f"**{n_cap_neg} correct + {n_cap_pos} hallucinating = {n_cap}** of the")
    log(f"{len(neg_fair) + len(pos_fair)} fair-pool targets. Those {n_cap} items carry the SAME SCORE. "
        "No threshold can")
    log(f"separate them, so the {n_cap_neg} false alarms are not a tuning failure -- they are the price")
    log(f"of the {n_cap_pos} detections, fixed, take it or leave it. Within the atom the precision is")
    log(f"{fmt_prop(n_cap_pos, n_cap)} at the fair pool's 50/50 balance.")
    log("")
    log("The same holds one point down. The second attainable value in the top tenth,")
    log(f"{att_top[0]:.6f}, carries {int((np.abs(neg_fair - att_top[0]) < TOL).sum())} correct and "
        f"{int((np.abs(pos_fair - att_top[0]) < TOL).sum())} hallucinating answers; adding it to")
    log(f"the flagged set is the single jump from {lo_fair['fpr']:.1%} to "
        f"{second_fair['fpr']:.1%} FPR (and {lo_fair['tpr']:.1%} to {second_fair['tpr']:.1%} TPR).")
    log("")
    log("This is the mechanism the top-decile framing was gesturing at, stated without an")
    log("arbitrary cut: the two values above 0.9 x ln 10 are not \"a small region of the")
    log("range\", they are **two indivisible blocks of population**, and an operator's entire")
    log("low-false-alarm menu consists of taking neither, one, or both.")
    log("")

    # ========================================= 4. the achievable ROC as POINTS
    log("## 4. The achievable ROC is a set of POINTS")
    log("")
    log("Plotted in `figures/fig_achievable_roc.pdf` (exact values in")
    log("`figures/fig_achievable_roc_data.csv`). Below, the low-FPR end in full.")
    log("")
    log("| tau | FPR [95% CI] | TPR [95% CI] | slope to the next point |")
    log("| --- | --- | --- | --- |")
    for i, r in enumerate(g_fair[:8]):
        tau = "inf" if not r["fires"] else f"{r['threshold']:.4f}"
        if i + 1 < len(g_fair):
            nxt = g_fair[i + 1]
            d_f, d_t = nxt["fpr"] - r["fpr"], nxt["tpr"] - r["tpr"]
            slope = f"{d_t / d_f:.2f}" if d_f > 0 else "-"
        else:
            slope = "-"
        pf, lof, hif = wilson(r["k_fp"], r["n_neg"])
        pt, lot, hit = wilson(r["k_tp"], r["n_pos"])
        log(f"| {tau} | {pf:.1%} [{lof:.1%}, {hif:.1%}] | {pt:.1%} [{lot:.1%}, {hit:.1%}] | "
            f"{slope} |")
    log("")
    log("**The randomisation caveat, stated before a reviewer states it.** A randomised rule")
    log("-- flag a ceiling item with probability p, otherwise never fire -- does reach any FPR")
    log(f"on the CHORD between two adjacent points. At a 5% budget that means p = "
        f"{0.05 / lo_fair['fpr']:.3f} and a TPR of")
    log(f"{0.05 / lo_fair['fpr'] * lo_fair['tpr']:.1%}. So the interpolated ROC curve is not")
    log("*unachievable*; the claim is narrower and survives:")
    log("")
    log("1. Every **deterministic** operating point -- the only kind anyone deploys, and the")
    log("   only kind under which the same input reliably gets the same decision -- is one of")
    log(f"   the {len(g_fair)} rows in section 1. A hallucination guard that flags a")
    log("   response on a coin flip is not a policy an operator can be held to, cannot be")
    log("   audited, and is not what any deployment of this detector does.")
    log("2. On the chord the operator pays the *average* of an indivisible block. The chord")
    log(f"   from (0, 0) to ({lo_fair['fpr']:.3f}, {lo_fair['tpr']:.3f}) has slope "
        f"{lo_fair['tpr'] / lo_fair['fpr']:.2f}; a score that resolved the ceiling atom would")
    log("   let the operator spend that budget on its most informative members instead. The")
    log("   lost area is exactly what granularity costs.")
    log("3. Randomisation cannot invent a point below the chord's left end either: at any FPR")
    log(f"   the achievable TPR is capped by the upper convex hull of these {len(fire_fair) + 1}")
    log("   points, and below 9.5% FPR that hull is a single straight line out of the origin.")
    log("")

    # ========================================= 5. the other two populations
    log("## 5. The other two populations, and which one to report")
    log("")
    log("**The 400-item fair pool has the SAME grid.** FPR is defined conditionally on the")
    log("negatives, so pooling the 200 hallucinating targets back in changes nothing about it;")
    log("the correct stratum IS the FPR population. What the other 200 supply is the TPR")
    log("column, which is already in section 1. There is no separate \"n=400 FPR grid\" to")
    log("report, and a paper that reported one would be reporting a prevalence-weighted")
    log("quantity under an FPR label.")
    log("")
    log(f"**The full labelled pool (n={n_total}) at natural prevalence.** Its negatives are the")
    log(f"{len(neg_full)} correct answers (prevalence of hallucination {prevalence:.1%}, "
        f"{len(pos_full)}/{n_total}).")
    log("The fair pool's correct stratum is a strict subset of these, so this estimates the")
    log("SAME parameter with 7x the negatives -- which is what makes it the control that")
    log("matters here: at n=200 the empirical grid cannot resolve FPR steps below 0.5%, so a")
    log("sceptic can ask whether the coarseness at the top is just the sampling resolution.")
    log(f"It is not. At n={len(neg_full)} the resolution is {1/len(neg_full):.2%} and the gap is")
    log("unchanged:")
    log("")
    log(f"| population | n negatives | resolution 1/n | lowest firing FPR | next FPR | "
        f"gap | gap / resolution |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    for nm, gg, nn in (("fair pool, correct stratum", fire_fair, len(neg_fair)),
                       ("full labelled pool, correct stratum", fire_full, len(neg_full))):
        gap = gg[1]["fpr"] - gg[0]["fpr"]
        log(f"| {nm} | {nn} | {1/nn:.2%} | **{gg[0]['fpr']:.2%}** "
            f"[{wilson(gg[0]['k_fp'], nn)[1]:.1%}, {wilson(gg[0]['k_fp'], nn)[2]:.1%}] | "
            f"{gg[1]['fpr']:.2%} | {gap:.2%} | {gap * nn:.0f}x |")
    log("")
    log("The lowest firing operating point sits at "
        f"{fmt_prop(lo_full['k_fp'], lo_full['n_neg'])} on the n={len(neg_full)} negatives, against")
    log(f"{fmt_prop(lo_fair['k_fp'], lo_fair['n_neg'])} on the nested n={len(neg_fair)}. The two agree; the")
    log(f"n={len(neg_full)} interval is the one that pins the parameter, and its lower bound")
    log(f"**{wilson(lo_full['k_fp'], lo_full['n_neg'])[1]:.1%}** rules out a 5% operating point")
    log("decisively.")
    log("")
    log("It also **moves the 10% verdict**, which is the one place the two populations")
    log("disagree operationally and the reason the superset is worth carrying:")
    log("")
    log("| target FPR | fair pool, n=200: budget honourable? | "
        f"full pool, n={len(neg_full)}: budget honourable? | rate achievable on either? |")
    log("| --- | --- | --- | --- |")
    y_full = np.concatenate([np.zeros(len(neg_full), int), np.ones(len(pos_full), int)])
    s_full = np.concatenate([neg_full, pos_full])
    for t in NOMINAL_TARGETS:
        a_fair = operating_point(y, s, target_fpr=t, mode="at_most")
        a_full = operating_point(y_full, s_full, target_fpr=t, mode="at_most")
        ex = (any(abs(r["fpr"] - t) < 1e-12 for r in g_fair)
              or any(abs(r["fpr"] - t) < 1e-12 for r in g_full))
        def _cell(op):
            return ("no -- flags nothing" if op.flags_nothing
                    else f"yes, at {op.achieved_fpr:.2%}")
        log(f"| {t:.0%} | {_cell(a_fair)} | {_cell(a_full)} | "
            f"{'yes' if ex else '**no**'} |")
    log("")
    log("At n=200 a 10% budget scrapes in at 9.5%; at n=1424 the floor is 10.53% and the same")
    log("budget cannot be honoured at all. The 95% intervals overlap, so this is not a")
    log("contradiction -- it is the parameter sitting within half a point of 10% and the")
    log("smaller sample landing on the lucky side. Report it that way: **the floor is about")
    log("one correct answer in ten, and a 10% budget is on the boundary of feasibility.** The")
    log("5% claim needs no such hedging on either population.")
    log("")
    log("**Prevalence changes the consequences, not the grid.** At the natural rate the")
    log("operator's experience of the same operating point is:")
    log("")
    log("| operating point | FPR | TPR | alerts per 1000 questions | precision (PPV) | "
        "hallucinations missed per 1000 |")
    log("| --- | --- | --- | --- | --- | --- |")
    for r in fire_full[:3]:
        n_alert = r["k_fp"] + r["k_tp"]
        ppv = r["k_tp"] / n_alert if n_alert else float("nan")
        per_k = 1000.0 * n_alert / n_total
        missed = 1000.0 * (len(pos_full) - r["k_tp"]) / n_total
        log(f"| tau = {r['threshold']:.4f} | {r['fpr']:.1%} | {r['tpr']:.1%} | {per_k:.0f} | "
            f"{fmt_prop(r['k_tp'], n_alert)} | {missed:.0f} |")
    log("| tau = inf (never fire) | 0.0% | 0.0% | 0 | - | "
        f"{1000.0 * len(pos_full) / n_total:.0f} |")
    log("")
    log("**Which to report.** The fair pool's correct stratum, n=200, as the headline: it is")
    log("the population `paper/sections/methods.tex` already commits to for any statement")
    log("about the detector, it is the population of the clean AUROC 0.704, and the false-alarm")
    log("arm's 80 targets are a prefix of it. Carry the n=1424 superset in a footnote as the")
    log("precision check, because it is what turns \"5% is unavailable on our sample\" into")
    log("\"5% is unavailable, full stop\". Do NOT report an FPR grid for the pooled n=400 or")
    log("the pooled n=2000: FPR is a within-negatives quantity and pooling only invites the")
    log("reader to read a prevalence-weighted number as a false-alarm rate.")
    log("")

    # ========================================= 6. rounding
    log("## 6. Rounding control (the one knob that could have manufactured this result)")
    log("")
    vals_raw, fprs_raw = attainable_fprs(neg_fair_raw)
    vals_rnd, _ = attainable_fprs(neg_fair)
    n_raw, n_rnd = len(vals_raw) - 1, len(vals_rnd) - 1
    top_raw = int(sum(1 for v in vals_raw[:-1] if v >= TOP_DECILE - 1e-12))
    top_rnd = int(sum(1 for v in vals_rnd[:-1] if v >= TOP_DECILE - 1e-12))
    # Which attainable values got split into several float64 neighbours, and at what FPR.
    split: dict[float, list[float]] = {}
    for v in sorted({float(v) for v in neg_fair_raw}):
        split.setdefault(round(v, DP), []).append(v)
    splits = [(k, len(vs)) for k, vs in split.items() if len(vs) > 1]
    lo_split = min((float((neg_fair >= k).mean()) for k, _ in splits), default=float("nan"))
    log("The entropy sum accumulates ~1e-16 of float noise, so two scores that are the SAME")
    log("attainable value can compare unequal. `attainable_fprs` deduplicates EXACTLY and by")
    log("design -- its reported rate has to be the rate the `>=` rule realises -- so raw")
    log("float64 input **fabricates operating points**, each 1/n of FPR apart. That is the one")
    log(f"direction that could make this grid look usably fine, so scores are rounded to {DP} dp")
    log("(1e-9 nats) before anything touches them; the smallest gap in the N=10 lattice is")
    log(f"{min(b - a for a, b in zip(lattice, lattice[1:])):.2e} nats, so rounding cannot merge two real values either.")
    log("")
    log("| | distinct firing thresholds | of them above 0.9 x ln 10 | "
        "distinct float values at the ceiling |")
    log("| --- | --- | --- | --- |")
    log(f"| raw float64 | {n_raw} | **{top_raw}** | "
        f"{len(sorted({float(v) for v in neg_fair_raw if v >= CAP - TOL}))} |")
    log(f"| rounded to {DP} dp | {n_rnd} | **{top_rnd}** | 1 |")
    log("")
    log(f"**The headline is not a rounding artefact, and the check says so in the awkward")
    log(f"direction.** Raw float64 does fabricate {n_raw - n_rnd} extra operating points on this stratum --")
    log(f"but none of them is near the top: it splits {len(splits)} attainable values, the highest at an")
    log(f"FPR of {lo_split:.1%}, and the two top-decile values are each bit-identical across every")
    log("item that carries them (the ceiling is `-10 x (0.1 ln 0.1)`, evaluated the same way")
    log(f"every time). So the grid `0% -> {lo_fair['fpr']:.1%} -> {second_fair['fpr']:.1%}` is what "
        "you get with or without rounding, and")
    log("the rounding choice only affects the middle of the scale, which no claim rests on.")
    log(f"Every number in this file is nonetheless on the rounded column; the {n_raw - n_rnd} extra points")
    log("are noise, and reporting them would overstate the detector's resolution.")
    log("")

    # ========================================= 7. N=20
    log("## 7. Does N=20 fix it? What the lattice settles, and what only data can")
    log("")
    gaps20 = [b - a for a, b in zip(lat20, lat20[1:])]
    log(f"**Settled by enumeration, no data needed.** The lattice grows from {len(lattice)}")
    log(f"attainable values at N=10 to **{len(lat20)}** at N=20 ({len(lat20)/len(lattice):.0f}x), but the top tenth of the")
    log(f"range goes only from **{len(att_top)}** points to **{len(att20_top)}**. The top of the")
    log("scale is where the lattice is sparsest at either budget. In absolute nats the gap")
    log(f"below the cap shrinks from {CAP - att_top[0]:.4f} (N=10) to "
        f"{math.log(20) - lat20[-2]:.4f} (N=20); as a share of the range,")
    log(f"from {(CAP - att_top[0]) / CAP:.1%} to {(math.log(20) - lat20[-2]) / math.log(20):.1%}. The seven top-decile values at N=20 are "
        + ", ".join(f"{v:.4f}" for v in att20_top) + ".")
    log("")
    log("**Also settled, and it is the useful half.** The minimum non-zero achievable FPR is")
    log("P(a clean correct answer yields N mutually distinct meanings), and that probability is")
    log("**non-increasing in N**: couple the two budgets by taking the N=10 sample to be the")
    log("first 10 of the N=20 draw. If all 20 are pairwise inequivalent then so are any 10 of")
    log("them (greedy bidirectional-entailment clustering assigns singletons to a subset")
    log("whenever it does to the superset, in the same order), so {saturate at 20} is contained")
    log("in {saturate at 10}. Marginally, the first 10 of an i.i.d. draw of 20 have the law of an")
    log("i.i.d. draw of 10, hence")
    log("")
    log("        min non-zero FPR at N=20  <=  min non-zero FPR at N=10  "
        f"= {lo_full['fpr']:.1%} [{wilson(lo_full['k_fp'], lo_full['n_neg'])[1]:.1%}, "
        f"{wilson(lo_full['k_fp'], lo_full['n_neg'])[2]:.1%}].")
    log("")
    log("So raising N can only help, and the floor on the operator's false-alarm rate is a")
    log("statement about how often the model answers a question 20 different ways -- a property")
    log("of the LM and the question distribution, not of the estimator's arithmetic.")
    log("")
    log("**NOT settled, and no reasoning substitutes for the data.** Whether the grid becomes")
    log("*usably* fine near the operating region depends entirely on how negative mass")
    log("distributes over those seven top-decile values, and that is unmeasured. The lattice")
    log("bounds the number of thresholds in the top decile at seven; it says nothing about")
    log("their FPRs. The two extremes are both consistent with everything above: mass could")
    log("spread evenly (a usable ~1-2% grid) or stay concentrated on the cap (a 5% floor and a")
    log("single jump, i.e. the same pathology one budget along). We have no N=20 fair-pool")
    log("scores, so we cannot choose between them.")
    log("")
    log("**The one N=20 clean measurement in the repo, and why it is not admissible here.**")
    log("`results/pilot_n20_ckpt_def.jsonl` re-scored 15 targets at N=20 and recorded their")
    log("clean `entropy_before_new`; 1 of 15 sits at ln 20 = 2.9957. Three reasons that is not")
    log("an estimate of the N=20 ceiling atom: (a) the 15 were selected because their")
    log("*attacked* N=10 score hit the cap -- selection on a score, on the attacked side, which")
    log("is exactly the selection the fair pool exists to avoid; (b) n=15 gives a Wilson")
    log("interval of "
        f"[{wilson(1, 15)[1]:.1%}, {wilson(1, 15)[2]:.1%}] around {wilson(1, 15)[0]:.1%}, "
        "which contains almost everything that matters, including")
    log("both 1% and 10%; (c) it is a single seed. Directionally it is consistent with the")
    log("monotonicity above and with the atom not vanishing. It settles nothing.")
    log("")
    log("**What would settle it:** clean N=20 scores on the fair pool's 200-target correct")
    log("stratum -- the same ids, the same seed discipline, nothing else changed. That is one")
    log("GPU pass over 200 questions at twice the sample budget, and it converts every")
    log("\"cannot conclude\" in this section into a number. Until then the honest claim is the")
    log("N=10 one, plus \"N=20 can only lower the floor, by an amount we have not measured\".")
    log("")

    # ========================================= 8. wording
    log("## 8. Recommended paper wording")
    log("")
    log("Replaces the top-decile sentence wherever it appears (abstract, introduction")
    log("contribution (1), discussion, conclusion). Numbers are the fair pool, correct")
    log(f"stratum, n={len(neg_fair)}; the parenthetical is the n={len(neg_full)} superset.")
    log("")
    log("> Semantic entropy over $N$ sampled answers is the entropy of a partition of $N$, so")
    log(f"> at the standard $N{{=}}10$ it lives on a lattice of {len(lattice)} attainable values")
    log("> with an atom at the maximum $\\ln 10$. A detector that flags when the score exceeds")
    log("> a threshold can therefore only be operated at a finite list of false-alarm rates,")
    log("> and the list is short where it matters: on a score-independent pool of 200 correct")
    log("> answers scored clean, the only achievable clean false-positive rates below one in")
    log(f"> four are $0\\%$, ${lo_fair['fpr']*100:.1f}\\%$ "
        f"[{lo_lo*100:.1f}, {lo_hi*100:.1f}] and ${second_fair['fpr']*100:.1f}\\%$ "
        f"[{wilson(second_fair['k_fp'], second_fair['n_neg'])[1]*100:.1f}, "
        f"{wilson(second_fair['k_fp'], second_fair['n_neg'])[2]*100:.1f}]. An operator who")
    log("> specifies a $5\\%$ false-alarm budget cannot have one: the only threshold honouring")
    log(f"> it flags nothing. The nearest operating point that fires runs at "
        f"{lo_fair['fpr']:.1%} and catches")
    log(f"> {lo_fair['tpr']:.1%} [{wilson(lo_fair['k_tp'], lo_fair['n_pos'])[1]:.1%}, "
        f"{wilson(lo_fair['k_tp'], lo_fair['n_pos'])[2]:.1%}] of hallucinations; the next runs at "
        f"{second_fair['fpr']:.1%} for {second_fair['tpr']:.1%}. The")
    log("> minimum non-zero false-positive rate is not a tuning choice but the mass of the")
    log("> ceiling atom itself, since every threshold above $\\ln N$ flags nothing")
    log(f"> ({fmt_prop(lo_full['k_fp'], lo_full['n_neg'])} on the {len(neg_full)}-answer superset). "
        "This is the score-granularity")
    log("> gap of \\citet{sun2026granularity} -- a score that ranks acceptably while offering")
    log("> an operator only a handful of usable thresholds -- instantiated for a")
    log("> sampling-based detector, where the lattice is set by the sample budget. Raising the")
    log(f"> budget can only lower the floor (the event ``all $N$ distinct'' shrinks with $N$),")
    log(f"> and $N{{=}}20$ affords {len(lat20)} attainable values, {len(att20_top)} of them in the")
    log("> top tenth of the range; whether that makes the achievable grid usably fine near the")
    log("> operating region we have not measured.")
    log("")
    log("Notes for whoever edits the .tex:")
    log("")
    log("- The top-decile cut can go entirely. Everything it was carrying is carried better by")
    log("  the grid, in units an operator uses, with no arbitrary constant.")
    log("- Keep the lattice counts (39, 455, and 2 vs 7 in the top decile): they are")
    log("  enumeration, they need no population, and section 7 leans on them.")
    log("- Do not write \"the ROC curve is a lie\". Write \"the achievable operating points are")
    log("  a finite set\"; the chords between them are reachable by randomisation and a")
    log("  reviewer will say so (section 4).")
    log("- Do not write that the detector cannot be operated at 10%. The data excludes 5%")
    log("  [Wilson lower bound "
        f"{wilson(lo_full['k_fp'], lo_full['n_neg'])[1]:.1%} on n={len(neg_full)}]; it does not")
    log("  exclude 10%.")
    log("- `sun2026granularity`'s own phrase (\"only a handful of usable thresholds\") is worth")
    log("  quoting at the point where the count table in section 1 lands.")
    log("")

    # ========================================= appendix: the superset's grid in full
    log("## Appendix A. The full grid on the n=1424 superset")
    log("")
    log("The same enumeration on the full labelled pool's correct stratum, with TPR on its")
    log(f"{len(pos_full)} hallucinating answers. Reported in full so the coarseness at the top can be")
    log("checked against a population where the sampling resolution is 0.07%, not 0.5%.")
    log("")
    log("| # | threshold tau (nats) | FPR | TPR |")
    log("| --- | --- | --- | --- |")
    for i, r in enumerate(g_full):
        tau = "inf (never fire)" if not r["fires"] else f"{r['threshold']:.6f}"
        log(f"| {i} | {tau} | {fmt_prop(r['k_fp'], r['n_neg'])} | "
            f"{fmt_prop(r['k_tp'], r['n_pos'])} |")
    log("")
    log("## Appendix B. Provenance and reproduction")
    log("")
    log(f"- labels: `{labels_path}`")
    log(f"- fair pool ids: `select_stratified(want, {N_PER_STRATUM}, seed={SEED})`, via")
    log("  `scripts/fair_pool_granularity.fair_pool_ids` (the same ids as the clean AUROC)")
    log("- threshold rule: `se.stats.attainable_fprs`, `se.stats.operating_point` "
        "(fixed 2026-08-13)")
    log("- every reported achieved FPR is asserted equal to `mean(negatives >= tau)` at "
        "runtime")
    log("- intervals: Wilson score, 95%, from `scripts/fair_pool_granularity.wilson`")
    log("- regenerate: `.venv\\Scripts\\python.exe scripts\\achievable_fpr_grid.py` (Windows, "
        "reads the")
    log("  cache over the WSL UNC share) or `./.venv-wsl/bin/python "
        "scripts/achievable_fpr_grid.py`")
    log("- unit tests: `tests/test_achievable_fpr_grid.py` (cache-free; asserts the "
        "minimum-non-zero-FPR")
    log("  identity, grid monotonicity, and the `at_most` contract under a ceiling atom)")
    log("")

    out = RESULTS_DIR / "achievable_fpr_grid.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)

    if not args.no_figure:
        write_figure(g_fair, g_full, len(neg_fair), len(pos_fair))
    return 0


# ------------------------------------------------------------------------------- figure
def write_figure(g_fair, g_full, n_neg, n_pos) -> None:
    """The achievable ROC as POINTS. No connecting curve through the deterministic points:
    a line implies thresholds that do not exist. The convex hull IS drawn, dashed, because
    it is the honest statement of what randomisation can reach and a reviewer will ask."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    with (FIGURES_DIR / "fig_achievable_roc_data.csv").open("w", newline="",
                                                            encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["population", "threshold_nats", "k_fp", "n_neg", "fpr",
                    "k_tp", "n_pos", "tpr", "fires"])
        for name, rows in (("fair_pool_correct_stratum", g_fair),
                           ("full_labelled_pool_correct_stratum", g_full)):
            for r in rows:
                w.writerow([name, r["threshold"], r["k_fp"], r["n_neg"], f"{r['fpr']:.6f}",
                            r["k_tp"], r["n_pos"], f"{r['tpr']:.6f}", int(r["fires"])])

    fx = [r["fpr"] for r in g_fair]
    fy = [r["tpr"] for r in g_fair]
    fire = [r for r in g_fair if r["fires"]]
    floor = fire[0]["fpr"]                      # the lowest FPR any threshold can realise
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for ax, xlim in zip(axes, [1.0, 0.30]):
        ax.plot([0, 1], [0, 1], color="0.75", lw=0.9, ls=":", zorder=1)
        ax.axvspan(0, floor, color="tab:red", alpha=0.07, lw=0, zorder=0)
        hx, hy = _upper_hull(fx, fy)
        ax.plot(hx, hy, ls="--", lw=1.1, color="tab:orange", zorder=2,
                label="reachable only by a randomised rule (upper hull)")
        ax.scatter(fx, fy, s=34, color="tab:blue", zorder=3,
                   label=f"attainable deterministic operating points ({len(fx)})")
        ax.set_xlim(-0.01 * xlim, xlim)
        ax.set_ylim(-0.02, 1.02 if xlim > 0.5 else 0.62)
        ax.set_xlabel("clean false-positive rate\n(fair pool, correct stratum, "
                      f"n={n_neg})")
        ax.grid(alpha=0.25, lw=0.5)
    axes[0].set_ylabel("true-positive rate\n(fair pool, hallucinating stratum, "
                       f"n={n_pos})")
    axes[0].set_title("Achievable ROC: a finite point set, not a curve", fontsize=10)
    axes[1].set_title(f"No threshold exists below FPR {floor:.1%}", fontsize=10)
    for t, lab in ((0.05, "5% budget"), (0.10, "10% budget")):
        axes[1].axvline(t, color="tab:red", lw=0.9, ls="-.")
        axes[1].annotate(lab, (t - 0.004, 0.60), fontsize=7, color="tab:red",
                         rotation=90, va="top", ha="right")
    axes[1].annotate("no deterministic\noperating point\nanywhere in here",
                     (floor / 2, 0.42), fontsize=7.5, color="tab:red",
                     ha="center", va="center")
    for r, off in zip(fire[:2], [(9, -16), (-6, 14)]):
        axes[1].annotate(f"tau={r['threshold']:.3f}\nFPR {r['fpr']:.1%}, TPR {r['tpr']:.1%}",
                         (r["fpr"], r["tpr"]), textcoords="offset points", xytext=off,
                         fontsize=7, ha="left" if off[0] > 0 else "right")
    axes[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES_DIR / f"fig_achievable_roc.{ext}", dpi=200)
    plt.close(fig)
    print(f"[figure] wrote {FIGURES_DIR / 'fig_achievable_roc.pdf'}", file=sys.stderr)


def _upper_hull(xs, ys):
    """Upper-left convex hull of the ROC points -- the randomisation frontier."""
    pts = sorted(set(zip(xs, ys)))
    hull: list[tuple[float, float]] = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return [p[0] for p in hull], [p[1] for p in hull]


if __name__ == "__main__":
    sys.exit(main())
