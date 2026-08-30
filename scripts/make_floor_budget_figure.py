"""Figure: the achievable false-alarm floor as a function of the sample budget.

WHY THIS IS A NEW SCRIPT AND NOT A PANEL IN `make_ceiling_figures.py`.
------------------------------------------------------------------------------------
That script opens by binding itself to ONE population -- the 80 correct-answer targets
of the false-alarm attack arm -- and says in its own header that binding a number to the
wrong population is this project's most-repeated error. Everything here is on a
DIFFERENT population: the fair pool's 200-answer correct stratum (score-independent,
`_stratum_ids("right", seed=0)[:200]`), with true-positive context from its 200
hallucinating answers. Adding a fair-pool panel to a file whose contract is "one pool"
would break the guarantee that makes that file safe. Hence a sibling.

POPULATION -- READ THIS BEFORE TOUCHING ANYTHING HERE.
------------------------------------------------------------------------------------
Every false-alarm rate plotted here is measured on

    the 200 CORRECT answers of the score-independent fair pool
    (`src/se/attacks/select.py`, `_stratum_ids("right", seed=0)[:200]`).

It is NOT the 80-target attacked pool, NOT the 1424-answer superset of this stratum,
and NOT the 2000-question replication pass. The axis label says so; do not tidy it out.

THREE KINDS OF NUMBER, AND WHY THE FIGURE REFUSES TO DRAW ONE LINE THROUGH THEM.
------------------------------------------------------------------------------------
  * direct N=10  -- a direct measurement on the Week-4 (June) cache. A DIFFERENT
                    GENERATION RUN from everything else here: the August answers are
                    measurably longer (+3.63 chars, z = +4.0). It is drawn detached and
                    is never joined to the budget sequence, because the replay control
                    (`results/replay_control.md` sec. 3) concludes the two arms estimate
                    DIFFERENT PARAMETERS -- neither is the odd one out, so a line from
                    this point to any other would assert a step that has not been
                    measured.
  * replay N=10, N=20 -- REPLAYS of the August N=40 checkpoint's recorded pairwise
                    verdicts on uniformly random subsets. Unbiased for the August run by
                    exchangeability, but not direct measurements.
  * measured N=40 -- the one direct measurement of the August run.
The last three share one source, so the trend among them is like-for-like; marker fill
and segment style say which is a replay and which is measured, and panel (b) carries
every cross-budget comparison with the interval that belongs to it.

THE FLOOR IS NOT THE AT-CAP MASS, AND THE FIGURE PLOTS BOTH.
------------------------------------------------------------------------------------
The floor is the smallest NON-ZERO false-alarm rate a firing threshold can realise. The
at-cap (ceiling-atom) mass is the share of correct answers sitting exactly at ln N. They
coincide while the atom is non-empty -- at N=10 and N=20 they are the same number, and
the figure shows them equal rather than nudging them apart -- and they part company at
N=40, where no correct answer reaches ln 40: the at-cap mass is 0.0% but the cheapest
alarm that exists still costs 2.0%. Conflating the two is the defect diagnosed in
`results/replay_control.md` sec. 5 and it is why both series are drawn.

INTERVALS. Each estimator gets the interval that belongs to it and no other
(`results/replay_control.md` sec. 2b, `results/n40_floor_estimator_ruling.md`):

  * Wilson on the count for the rows that really are a count at a threshold fixed
    BEFORE the data -- the direct N=10 floor (19/200 at ln 10) and the N=40 at-cap
    mass (0/200 at ln 40).
  * a bootstrap over the 200 QUESTIONS ONLY for the subset-averaged replayed rows --
    which may not also resample the subset draw, because the subset-draw component has
    been averaged out of the point estimate.
  * NEITHER for the measured N=40 floor. It is a count at no threshold fixed in
    advance, and once the atom is empty NOTHING IN THE SAMPLE SETTLES whether that
    threshold is the top of the population's support. If it is not, a larger pool
    reaches a higher rung and reports a smaller floor; if it is, 2.0% is an ordinary
    population proportion and the count estimates it. n=200 cannot decide, and the two
    readings are more than two orders of magnitude apart, so the quantity is not
    identified and no interval prices it. It is plotted as a point -- see FLOOR[40]
    below, whose interval entries are None, and the refusal check that enforces it.

    The coverage figures are branch-conditional and must never travel without the
    population they were measured under (ruling sec. 8.4, nominal 95%):
      calibrated Ewens (tau_top = 0.2726%): Wilson 53.67%, question bootstrap 0.00%
      zero branch      (tau*     = 2.0%):   Wilson 95.06%, question bootstrap 100%
    This docstring said "the estimand itself moves with the pool, so both candidates
    were withdrawn on measured coverage (Wilson 53.7%, bootstrap 0.00%)" until
    2026-08-26. Both halves were the first row stated as though it were the data;
    ruling sec. 13 retracts that framing while leaving the plotted output unchanged.

This paragraph said "Wilson on the count for the two directly measured rows" until
2026-08-26, which named the measured N=40 floor as taking Wilson. The CODE below never
did -- it has plotted that row as a bare point since the ruling -- so this was a
generator's prose disagreeing with the generator's own behaviour, which is the harder
kind to notice: nothing it produces is wrong, and a reader reaches for the docstring
precisely when they want to know what the figure means.

Panel (b)'s differences are matched paired bootstraps over the questions, not end
intervals subtracted.

GREYSCALE. No colour carries meaning: series are separated by marker shape, fill, and
line style alone.

Run (Windows):  .venv\\Scripts\\python.exe scripts\\make_floor_budget_figure.py
Run (WSL):      ./.venv-wsl/bin/python scripts/make_floor_budget_figure.py
CPU only -- no model is loaded and no GPU is touched.

Writes figures/fig_floor_budget.{pdf,png} and, beside them, the exact numbers plotted
(CSV) and the verification record (JSON).

The script REFUSES to plot unless it can re-derive every plotted number from the primary
artifacts. A mismatch means the data, or the verified list below, is wrong -- which
matters more than a figure.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "figures"
CKPT = REPO / "results" / "n_scaling_ckpt.jsonl"
JUNE_DIR = Path(
    "//wsl.localhost/Ubuntu-24.04/home/abhi/.cache/se-research/samples/wk4_full_2000q")

POOL_SHORT = "fair pool, correct stratum (n=200)"
POOL_LONG = (
    "200 correct answers of the score-independent fair pool "
    "(_stratum_ids('right', seed=0)[:200]). NOT the 80-target attacked pool, "
    "NOT the 1424-answer superset, NOT the 2000-question replication pass."
)

# ---------------------------------------------------------------------------------
# VERIFIED VALUES. Source of record: `results/replay_control.md` sec. 2b (the corrected
# matched table) and `paper/sections/discussion.tex`, which agree with each other. These
# are what gets PLOTTED; `rederive()` below is the guard that they are still true.
#
# NOT USED, DELIBERATELY: the "11.9% -> 3.0% -> 2.0% ... -9.9 points [-15.5, -5.0]"
# summary bullets in sections 2 and 6 of that same report. Those are emitted from the
# SUPERSEDED estimator (`point[nm]["floor"]`, an average over 200 whole replicates) and
# the SUPERSEDED both-components bootstrap (`diff_ci`), while the report's own tables use
# the matched ones (`matched_diff`). The report's quotability banner requires the floor be
# quoted "WITH the matched intervals of section 2b and no others", so those bullets breach
# their own file's rule. The matched values are the ones re-derived below.
# ---------------------------------------------------------------------------------
MC_TOL_PTS = 0.05      # tolerance on a point estimate, in rate points
CI_TOL_PTS = 0.15      # tolerance on a bootstrap percentile, in rate points

# `None` means the row is plotted as a POINT with no interval. That is the ruling of
# `results/n40_floor_estimator_ruling.md` for the N=40 floor, not an omission: once the
# ceiling atom empties, "the floor" is the multiplicity of whichever rung this pool
# happened to reach, and whether that rung is the top of the population's support is not
# determinable at n=200 -- so the estimand is NOT IDENTIFIED (ruling sec. 13). Coverage
# of the two candidates depends on which branch holds and must be quoted with its
# population: under the calibrated Ewens fit, 53.67% (Wilson on 4/200) and 0.00%
# (question bootstrap); under the zero branch, 95.06% and 100% (ruling sec. 8.4). The
# withdrawal rests on the non-identification, which needs no model, and not on the
# first pair -- do not restate that pair alone as "both candidates fail".
FLOOR = {                        # budget -> (point %, lo %, hi %) or (point %, None, None)
    10: (12.0, 8.9, 15.3),       # replay,   question bootstrap
    20: (3.1, 1.8, 4.7),         # replay,   question bootstrap
    40: (2.0, None, None),       # measured, NO INTERVAL -- see above
}
ATCAP = {
    10: (12.0, 8.9, 15.3),       # identical estimator to the floor: the atom IS the floor
    20: (3.1, 1.8, 4.7),
    40: (0.0, 0.0, 1.9),         # Wilson on 0/200 -- the atom is empty at ln 40
}
DIRECT10 = (9.5, 6.2, 14.4)      # June cache, Wilson on 19/200
DIRECT10_COUNT = 19              # of 200, at ln 10 -- floor and at-cap coincide there
N40_FLOOR_COUNT = 4              # of 200, tied at the top score
N40_ATCAP_COUNT = 0              # of 200, at ln 40
N40_NEXT_FPR = 2.5               # the next achievable rate above the floor

# Matched paired differences over the 200 questions.
#
# THESE NO LONGER COME FROM `replay_control.md`, AND THE FIRST ONE CHANGED BECAUSE OF IT.
# `p_at_cap` below used to estimate each question's saturation probability by Monte Carlo
# over random k-subsets. It is now computed EXACTLY (see the docstring there), which
# removes the subset-draw error entirely. The 10 -> 20 leg is -8.863 exactly, not the
# -8.84 a 20,000-draw Monte Carlo gives and not the -8.8 `replay_control.md` prints at
# 40,000 draws; at one decimal that is 8.9, which is what `paper/sections/discussion.tex`
# prints and what this figure now plots. The paper was right and the artifacts were not.
#
# STABILITY OF THE PRINTED DIGITS, measured over 12 independent bootstrap streams at
# 400,000 resamples each (the point estimates are exact and do not move at all):
#   10 -> 20   lo  -11.0507 +/- 0.0028   STRADDLES the 11.05 rounding boundary
#              hi   -6.7900 +/- 0.0036   stable at 6.8
#   20 -> 40   lo   -2.4272 +/- 0.0026   stable at 2.4
#              hi   +0.2204 +/- 0.0030   stable at 0.2
#   10 -> 40   lo  -12.9342 +/- 0.0061   stable at 12.9
#              hi   -7.2170 +/- 0.0074   stable at 7.2
# So one printed digit -- the 10 -> 20 lower endpoint -- is a coin flip at one decimal
# place, and is quoted from the pinned seed below. Do not "correct" it to 11.0 on the
# strength of one rerun at a different seed; that is noise, and chasing it is how this
# leg acquired a wrong value in the first place.
DIFFS = [
    ("$10 \\rightarrow 20$", "replay-replay",    -8.9, -11.1, -6.8),
    ("$20 \\rightarrow 40$", "replay-measured",  -1.1,  -2.4,   0.2),
    ("$10 \\rightarrow 40$", "replay-measured", -10.0, -12.9,  -7.2),
]

Z = 1.959963985


def wilson(x: int, n: int) -> tuple[float, float]:
    c = (x + Z * Z / 2) / (n + Z * Z)
    h = (Z / (n + Z * Z)) * math.sqrt(x * (n - x) / n + Z * Z / 4)
    return max(0.0, c - h) * 100, min(1.0, c + h) * 100


# ---------------------------------------------------------------------------------
# Re-derivation from the primary artifacts.
# ---------------------------------------------------------------------------------
def _agree(what: str, got: float, want: float, tol: float) -> None:
    if not math.isfinite(got) or abs(got - want) > tol:
        sys.exit(f"REFUSING TO PLOT: {what} re-derives to {got:.4f}, "
                 f"but the figure plots {want:.4f} (tolerance {tol}).")


def _agree_int(what: str, got: int, want: int) -> None:
    if got != want:
        sys.exit(f"REFUSING TO PLOT: {what} re-derives to {got}, "
                 f"but the figure assumes {want}.")


def load_checkpoint() -> tuple[list[dict], list[dict]]:
    if not CKPT.exists():
        sys.exit(f"REFUSING TO PLOT: no checkpoint at {CKPT}")
    recs = [json.loads(l) for l in CKPT.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    correct = [r for r in recs if r["stratum"] == "correct"]
    halluc = [r for r in recs if r["stratum"] == "hallucinating"]
    if len(correct) != 200 or len(halluc) != 200:
        sys.exit(f"REFUSING TO PLOT: expected 200+200, got {len(correct)}+{len(halluc)}")
    if any(r["n_samples"] != 40 for r in recs):
        sys.exit("REFUSING TO PLOT: checkpoint is not all N=40")
    return correct, halluc


_PAIRS = list(combinations(range(40), 2))
_IU = np.array([p[0] for p in _PAIRS])
_JU = np.array([p[1] for p in _PAIRS])


def adjacency(bits: str, n: int = 40) -> np.ndarray:
    """The recorded pairwise equivalence graph. Pair order is `combinations(range(n), 2)`,
    matching `scripts/n_scaling_grid.py::verdict_bits`."""
    if len(bits) != math.comb(n, 2):
        sys.exit(f"REFUSING TO PLOT: verdict string has {len(bits)} bits, "
                 f"expected {math.comb(n, 2)}")
    v = np.frombuffer(bits.encode(), dtype=np.uint8) == ord("1")
    a = np.zeros((n, n), dtype=bool)
    a[_IU, _JU] = v
    a[_JU, _IU] = v
    return a


def p_at_cap(a: np.ndarray, k: int) -> float:
    """P(a uniformly random k-subset of the recorded 40 samples is all-singletons), EXACTLY.

    All-singletons iff the subset contains no equivalent pair: the clusterer is union-find
    over PAIRWISE verdicts, so a subset's clustering uses only the verdicts inside it.
    That event is exactly "the replayed score hits the ln k cap".

    "No equivalent pair inside the subset" is "the subset is an independent set of the
    recorded verdict graph", so the probability is (number of independent sets of size k)
    / C(40, k) and needs no sampling at all. The count comes from the standard recursion
    I(G) = I(G - v) + x * I(G - N[v]) on a max-degree vertex, memoised on the vertex
    bitmask and closed out in binomial form once the remaining subgraph is edgeless.
    These graphs are sparse -- a correct answer at N=40 typically has 38 of 40 clusters --
    so this is fast, and unlike the Monte Carlo it returns the same number every run.

    This REPLACED a 20,000-draw Monte Carlo on 2026-08-19. The estimates agreed to about
    0.01 rate points, which was enough to move the 10 -> 20 paired leg across a rounding
    boundary and put this figure into conflict with the paper. See DIFFS above."""
    n = a.shape[0]
    adj = [0] * n
    for i in range(n):
        for j in range(n):
            if i != j and a[i, j]:
                adj[i] |= 1 << j
    memo: dict[int, tuple] = {}

    def rec(mask: int) -> tuple:
        if mask == 0:
            return (1,)
        hit = memo.get(mask)
        if hit is not None:
            return hit
        best, bd, mm = -1, -1, mask
        while mm:
            b = (mm & -mm).bit_length() - 1
            d = bin(adj[b] & mask).count("1")
            if d > bd:
                bd, best = d, b
            mm &= mm - 1
        if bd == 0:                       # edgeless remainder: every subset qualifies
            c = bin(mask).count("1")
            out = tuple(math.comb(c, i) for i in range(c + 1))
        else:
            ex = rec(mask & ~(1 << best))                       # best excluded
            inc = rec(mask & ~((1 << best) | adj[best]))        # best included
            acc = [0] * max(len(ex), len(inc) + 1)
            for i, v in enumerate(ex):
                acc[i] += v
            for i, v in enumerate(inc):
                acc[i + 1] += v
            out = tuple(acc)
        memo[mask] = out
        return out

    poly = rec((1 << n) - 1)
    return (poly[k] if k < len(poly) else 0) / math.comb(n, k)


def rederive(boot: int, seed: int) -> dict:
    correct, halluc = load_checkpoint()
    rng = np.random.default_rng(seed)
    adjs = [adjacency(r["verdict_bits"]) for r in correct]

    out: dict = {"population": POOL_LONG,
                 "subset_draws_per_question": "none -- computed exactly, see p_at_cap()",
                 "bootstrap_resamples": boot, "seed": seed,
                 "source_of_record": [
                     "results/n_scaling_ckpt.jsonl (primary; every point re-derived here)",
                     "results/n40_floor_estimator_ruling.md (why the N=40 floor has no "
                     "interval)"],
                 "not_the_source_of_record": [
                     "results/replay_control.md sec. 2b -- its floors and paired legs are "
                     "a 40,000-draw Monte Carlo where this file counts independent sets "
                     "exactly, so they differ: the floors in the 2nd decimal, and the "
                     "N=10 -> N=20 leg in the FIRST (-8.8 there against -8.86 here, i.e. "
                     "-8.9 at one decimal, which is what the paper quotes). On the N=40 "
                     "floor the two files AGREE -- point only, no interval, both citing "
                     "results/n40_floor_estimator_ruling.md",
                     "paper/sections/discussion.tex -- the paper is checked AGAINST this "
                     "figure, not the other way round"],
                 "checks": []}
    ps = {}
    for k in (10, 20):
        p = np.array([p_at_cap(a, k) for a in adjs])
        ps[k] = p
        n = len(p)
        pbar = float(p.mean()) * 100
        idx = rng.integers(0, n, size=(boot, n))
        means = p[idx].mean(axis=1) * 100
        lo, hi = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
        # The sec. 2b identity: mean_i p_i(1-p_i) + var_i(p_i) = pbar(1-pbar). The
        # subset-draw component is ALREADY inside a single-replicate Wilson interval and
        # may not be added to it a second time.
        v_sub = float((p * (1 - p)).mean())
        v_q = float(p.var(ddof=0))
        resid = (v_sub + v_q) / n - (p.mean() * (1 - p.mean())) / n
        out["checks"].append({
            "what": f"replay N={k} floor (= at-cap mass), subset-averaged",
            "rederived": [round(pbar, 3), round(lo, 3), round(hi, 3)],
            "plotted": list(FLOOR[k]),
            "variance_identity_residual": resid,
        })
        _agree(f"replay N={k} floor point", pbar, FLOOR[k][0], MC_TOL_PTS)
        _agree(f"replay N={k} floor CI lo", lo, FLOOR[k][1], CI_TOL_PTS)
        _agree(f"replay N={k} floor CI hi", hi, FLOOR[k][2], CI_TOL_PTS)
        if abs(resid) > 1e-12:
            sys.exit(f"REFUSING TO PLOT: the sec. 2b variance identity fails at N={k} "
                     f"(residual {resid:.3e})")

    # N=40: the floor is an order statistic; the at-cap mass is a count at ln 40.
    ent = np.array([r["entropy_nats"] for r in correct])
    ent_h = np.array([r["entropy_nats"] for r in halluc])
    nclu = np.array([r["n_clusters"] for r in correct])
    atcap = int((nclu == 40).sum())
    tied = int((ent >= ent.max() - 1e-12).sum())
    rates = sorted({float((ent >= t - 1e-12).mean()) * 100 for t in np.unique(ent)})
    nxt = rates[1] if len(rates) > 1 else float("nan")
    tpr_at_floor = float((ent_h >= ent.max() - 1e-12).mean()) * 100
    out["checks"].append({
        "what": "measured N=40",
        "at_cap_count": atcap, "floor_count": tied,
        "max_entropy_nats": float(ent.max()), "ln40": math.log(40),
        "ascending_achievable_fprs_pct": [round(r, 2) for r in rates[:6]],
        "tpr_at_the_floor_threshold_pct": round(tpr_at_floor, 2),
        "plotted_floor": list(FLOOR[40]),
        "plotted_floor_interval": "none -- withdrawn by results/n40_floor_estimator_ruling.md",
        "withdrawn_wilson_on_the_floor_count": [round(v, 4) for v in wilson(tied, 200)],
        "withdrawn_question_bootstrap_on_the_floor": [0.5, 4.0],
        "plotted_at_cap": list(ATCAP[40]),
    })
    _agree_int("N=40 at-cap count", atcap, N40_ATCAP_COUNT)
    _agree_int("N=40 floor count", tied, N40_FLOOR_COUNT)
    _agree("N=40 next achievable FPR", nxt, N40_NEXT_FPR, 1e-6)
    if ent.max() >= math.log(40) - 1e-12:
        sys.exit("REFUSING TO PLOT: a correct answer reaches ln 40; the atom is not empty "
                 "and the figure's central contrast is void.")
    _agree("N=40 floor point", tied / 2, FLOOR[40][0], 1e-9)
    if FLOOR[40][1] is not None or FLOOR[40][2] is not None:
        sys.exit("REFUSING TO PLOT: the N=40 floor has been given an interval again. "
                 "results/n40_floor_estimator_ruling.md withdrew both candidates because "
                 "the estimand is NOT IDENTIFIED at n=200 -- whether the pool's top rung "
                 "is the population's is undecidable here, and the two readings differ by "
                 "two orders of magnitude. (Coverage figures are branch-conditional: "
                 "under the calibrated Ewens fit Wilson covers 53.67% and the question "
                 "bootstrap 0.00%; under the zero branch, 95.06% and 100%. Quote neither "
                 "pair without its population.) If that ruling has been overturned, "
                 "change it there first and say so here.")
    lo, hi = wilson(atcap, 200)
    _agree("N=40 at-cap Wilson hi", hi, ATCAP[40][2], 0.05)

    # Matched paired differences: ONE bootstrap draw of questions drives every budget, and
    # the N=40 floor is re-found inside each resample (the top score can move question).
    idx = rng.integers(0, 200, size=(boot, 200))
    b10, b20 = ps[10][idx].mean(axis=1) * 100, ps[20][idx].mean(axis=1) * 100
    e = ent[idx]
    b40 = (e >= e.max(axis=1, keepdims=True) - 1e-12).mean(axis=1) * 100
    pt = {10: float(ps[10].mean()) * 100, 20: float(ps[20].mean()) * 100, 40: tied / 2}
    for (lbl, _kind, d, dlo, dhi), (a, b, ba, bb) in zip(
            DIFFS, [(10, 20, b10, b20), (20, 40, b20, b40), (10, 40, b10, b40)]):
        dd = bb - ba
        rd = pt[b] - pt[a]
        rlo, rhi = float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))
        out["checks"].append({"what": f"matched paired difference N={a} -> N={b}",
                              "rederived": [round(rd, 2), round(rlo, 2), round(rhi, 2)],
                              "plotted": [d, dlo, dhi]})
        _agree(f"diff {a}->{b} point", rd, d, MC_TOL_PTS + 0.05)
        _agree(f"diff {a}->{b} lo", rlo, dlo, CI_TOL_PTS)
        _agree(f"diff {a}->{b} hi", rhi, dhi, CI_TOL_PTS)

    out["checks"].append(rederive_june())
    return out


def rederive_june() -> dict:
    """The June point, checked against its own primary artifact -- not taken on trust.

    The whole argument of this figure is that this point has a different provenance, so it
    is the last point that may be drawn from a number someone typed in."""
    rel, entf = JUNE_DIR / "relabeled.jsonl", JUNE_DIR / "entropy.jsonl"
    if not (rel.exists() and entf.exists()):
        sys.exit(
            f"REFUSING TO PLOT: the Week-4 (June) cache is not reachable at {JUNE_DIR}.\n"
            "The direct N=10 point cannot be verified, and this figure exists to say that "
            "that point has a different provenance -- so it may not be drawn on trust.\n"
            "Start the WSL distro (wsl -d Ubuntu-24.04) so the UNC share resolves, "
            "then rerun.")
    sys.path.insert(0, str(REPO / "src"))
    from se.attacks.select import _stratum_ids, load_labels          # noqa: E402
    labels = load_labels(rel)
    right = _stratum_ids("right", 0, labels)[:200]
    ent, ncl = {}, {}
    for line in entf.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            ent[d["question_id"]] = d["entropy_nats"]
            ncl[d["question_id"]] = d["n_clusters"]
    er = np.array([ent[q] for q in right])
    at = sum(1 for q in right if ncl[q] == 10)
    tied = int((er >= er.max() - 1e-12).sum())
    rates = sorted({float((er >= t - 1e-12).mean()) * 100 for t in np.unique(er)})
    _agree_int("direct N=10 at-cap count", at, DIRECT10_COUNT)
    _agree_int("direct N=10 floor count", tied, DIRECT10_COUNT)
    _agree("direct N=10 floor point", tied / 2, DIRECT10[0], 1e-9)
    lo, hi = wilson(tied, 200)
    _agree("direct N=10 Wilson lo", lo, DIRECT10[1], 0.05)
    _agree("direct N=10 Wilson hi", hi, DIRECT10[2], 0.05)
    return {"what": "direct N=10 (Week-4 June cache) -- a DIFFERENT generation run",
            "at_cap_count": at, "floor_count": tied,
            "ascending_achievable_fprs_pct": [round(r, 2) for r in rates[:4]],
            "plotted": list(DIRECT10)}


# ---------------------------------------------------------------------------------
# The figure.
# ---------------------------------------------------------------------------------
def draw(stem: Path) -> None:
    plt.rcParams.update({
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 6.5,
        "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    # WIDTH IS 6.5 in BECAUSE THAT IS WHAT REACHES THE PAGE. MEASURE BEFORE CHANGING IT.
    #
    # This block said "Sized to be ONE COLUMN natively (3.4 in) ... \includegraphics
    # [width=\linewidth] neither enlarges nor shrinks it -- the annotation point sizes below
    # are the ones that reach the page" until 2026-08-30. Every clause of that was false,
    # and it is the same defect the docstring above names: a generator's prose disagreeing
    # with the generator's own behaviour. paper/main.tex is a SINGLE-COLUMN article with
    # geometry margin=1in, so \linewidth is 469.755 pt = 6.500 in and \textheight is
    # 650.430 pt = 9.000 in (both measured with \typeout, not assumed). A 3.4 in figure
    # included at \linewidth is therefore MAGNIFIED 6.500/3.400 = 1.9118x, and every point
    # size in this function reached the page at nearly twice its nominal value.
    #
    # That magnification was also the float bug. At 1.9118x the old 3.4 x 4.6 in canvas
    # drew 6.50 x 8.79 in = 635.6 pt tall, leaving 14.8 pt of the 650.4 pt textheight for a
    # caption that sets to about 134.6 pt. LaTeX reported exactly that shortfall --
    # "Float too large for page by 119.72202pt" (635.6 + 134.6 - 650.4 = 119.8, to the
    # rounding of the caption measurement) -- and a float that cannot be placed is deferred,
    # which is how Figure 2 came to be stranded on a page of its own with its caption
    # overrunning the page number.
    #
    # So the canvas is now authored at the width it is displayed at: 1 pt here is 1 pt on
    # the page, and the font sizes above are honest. Saved without bbox_inches="tight" so
    # the PDF is exactly this size. If the surrounding document ever becomes two-column,
    # re-measure \linewidth and change this figsize; do not scale the fonts to compensate.
    #
    # The two panels are now SIDE BY SIDE rather than stacked. That is what the caption in
    # paper/sections/discussion.tex has always said ("Left: the floor ... Right: the three
    # matched paired differences"); the stacked layout contradicted it.
    fig = plt.figure(figsize=(6.5, 2.75))
    # left=0.105 is the measured width of panel (a)'s two-line y label plus its tick
    # labels, not a guess: at 0.088 the y label overran the canvas by 7.3 px.
    gs = GridSpec(1, 2, width_ratios=[1.0, 1.06], wspace=0.42,
                  left=0.105, right=0.995, top=0.845, bottom=0.165)
    ax, bx = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    budgets = (10, 20, 40)
    xs = [math.log2(n) for n in budgets]
    fl = [FLOOR[n][0] for n in budgets]
    # A row with no interval draws no bar. Zero-length caps would read as a zero-width
    # confidence interval, which is the opposite of what the missing interval means.
    fl_lo = [0.0 if FLOOR[n][1] is None else FLOOR[n][0] - FLOOR[n][1] for n in budgets]
    fl_hi = [0.0 if FLOOR[n][2] is None else FLOOR[n][2] - FLOOR[n][0] for n in budgets]
    ac = [ATCAP[n][0] for n in budgets]

    # --- panel (a): levels -------------------------------------------------------
    # No single line through the sequence. The replay-to-replay step is dashed; the step
    # that crosses from a replay into the one direct measurement is dash-dotted; and the
    # June point is joined to nothing at all.
    ax.plot(xs[:2], fl[:2], ls="--", lw=1.0, color="0.35", zorder=1)
    ax.plot(xs[1:], fl[1:], ls="-.", lw=1.0, color="0.35", zorder=1)
    ax.plot(xs, ac, ls=":", lw=1.0, color="0.55", zorder=1)

    ax.errorbar(xs, fl, yerr=[fl_lo, fl_hi], fmt="none", ecolor="black",
                elinewidth=0.9, capsize=2.4, capthick=0.9, zorder=3)
    # At-cap: only N=40 gets its own bar. At N=10 and N=20 the at-cap mass and the floor
    # are the SAME estimator, so they share one interval; a second bar would imply two
    # measurements where there is one.
    ax.errorbar([xs[2]], [ac[2]], yerr=[[0.0], [ATCAP[40][2] - ATCAP[40][0]]],
                fmt="none", ecolor="0.45", elinewidth=0.9, capsize=2.4, capthick=0.9,
                zorder=3)

    # Marker FILL carries one rule across both series: open = replayed from the N=40
    # run, filled = directly measured. The N=40 at-cap mass is a count (0/200), so its
    # square is filled -- drawing it open would present a measurement as a replay.
    ax.plot(xs[:2], ac[:2], ls="none", marker="s", ms=6.4, mfc="white", mec="0.35",
            mew=0.9, zorder=4)
    ax.plot([xs[2]], [ac[2]], ls="none", marker="s", ms=6.4, mfc="0.45", mec="0.25",
            mew=0.9, zorder=4)
    ax.plot(xs[:2], fl[:2], ls="none", marker="o", ms=3.4, mfc="white", mec="black",
            mew=1.0, zorder=5)
    ax.plot([xs[2]], [fl[2]], ls="none", marker="o", ms=3.7, mfc="black", mec="black",
            zorder=5)
    ax.errorbar([xs[0]], [DIRECT10[0]],
                yerr=[[DIRECT10[0] - DIRECT10[1]], [DIRECT10[2] - DIRECT10[0]]],
                fmt="D", ms=3.7, mfc="0.35", mec="0.15", mew=0.8,
                ecolor="0.45", elinewidth=0.9, capsize=2.4, capthick=0.9, zorder=6)

    # WHAT IS NO LONGER PAINTED ON THE AXES, AND WHERE IT WENT (2026-08-30).
    # Four blocks of explanatory prose used to sit inside this panel. Three of them ran
    # through the plotted lines and markers; all four were there doing the caption's job.
    # Each was checked against the caption and the body BEFORE it was removed, and three of
    # the four were found to be restating text that already exists elsewhere verbatim:
    #
    #  1. "cheapest alarm that exists: 2.0%, and no interval: its threshold is the top score
    #     this sample reached, not a value fixed in advance" -- crossed the dash-dot segment
    #     and the N=20 marker. Already in the caption at discussion.tex, near-verbatim:
    #     "the cheapest alarm the pool can exhibit costs 2.0% and is drawn without an
    #     interval, its threshold being the top score this sample reached rather than a
    #     value fixed in advance". Pure duplication; deleted.
    #  2. "at-cap 0.0%: the never-fire policy" -- sat on the bottom spine and touched the
    #     grey square. Already in the BODY one paragraph above the float (discussion.tex):
    #     "0.0% is the never-fire policy, and the cheapest alarm that exists at N=40 costs
    #     2.0%". Deleted.
    #  3. "direct measurement, June cache: a different generation run, so it is joined to
    #     nothing" -- its leader crowded the point. Already in the caption: "the direct
    #     N=10 point from the June cache is shown separately because it is a different
    #     generation run". The legend entry keeps the identity and the absence of any
    #     connecting segment keeps "joined to nothing". Deleted.
    #  4. "open marker = replayed from the N=40 run; filled = directly measured" -- competed
    #     with the legend for the upper right. This one is NOT stated anywhere else, and it
    #     is the key that decodes both series, so it is KEPT -- moved into the legend title
    #     below, where it cannot collide with data by construction.
    #
    # THE NUMERALS DID NOT MOVE OUT WITH THE PROSE. 2.0% and 0.0% stay in the panel as the
    # short data labels below, beside the marks they belong to. Deleting a numeral from a
    # figure because its sentence went to the caption is how a figure and its caption start
    # disagreeing, and nothing here is quoted from prose that is not also plotted.
    ax.text(xs[2] + 0.12, fl[2], "$2.0\\%$", fontsize=7, color="0.05",
            ha="left", va="center")
    # 0.30, not the 0.45 of the at-cap series it belongs to: it is a plotted value, not a
    # de-emphasised note, and it has to survive a greyscale print at 7 pt.
    ax.text(xs[2] + 0.12, ac[2], "$0.0\\%$", fontsize=7, color="0.30",
            ha="left", va="center")

    ax.set_xticks(xs)
    ax.set_xticklabels(["10", "20", "40"])
    # The right limit is opened from +0.24 to +0.62 to make room for those two labels
    # OUTSIDE the data. The ticks are set explicitly above, so widening the view adds white
    # space and changes no tick, no label and no plotted coordinate.
    ax.set_xlim(xs[0] - 0.30, xs[2] + 0.62)
    ax.set_ylim(-1.9, 18.2)
    # Pinned rather than left to the locator: these are the same eight tick values the old
    # layout produced, and a layout pass may not change a number on an axis either.
    ax.set_yticks([0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5])
    ax.set_xlabel("sample budget $N$ (log scale)")
    ax.set_ylabel("false-alarm rate (%)\nfair pool, correct stratum ($n{=}200$)")
    ax.set_title("(a)  the floor and the at-cap mass are the\n"
                 "     same number until the atom empties",
                 loc="left", fontsize=8)
    ax.grid(axis="y", lw=0.5, color="0.88", zorder=0)
    ax.set_axisbelow(True)

    handles = [
        Line2D([], [], ls="--", lw=1.0, color="0.35", marker="o", ms=3.4,
               mfc="white", mec="black", mew=1.0, label="floor (min non-zero FPR)"),
        Line2D([], [], ls=":", lw=1.0, color="0.55", marker="s", ms=6.4,
               mfc="white", mec="0.35", mew=0.9, label="at-cap (ceiling-atom) mass"),
        Line2D([], [], ls="none", marker="D", ms=3.7, mfc="0.35", mec="0.15",
               mew=0.8, label="direct $N{=}10$, June cache"),
    ]
    # The fill rule is the legend's TITLE, not a floating note. It used to be free text at
    # axes coordinates (0.988, 0.735), immediately under the legend box and competing with
    # it for the upper right. As a title it is inside the same frame as the swatches it
    # explains, it can never drift onto the data, and it stays adjacent to the open and
    # filled markers that demonstrate it. The whole upper-right quadrant right of N=20 and
    # above y=10 is empty of data -- every point right of N=20 lies at or below 4.7 -- so
    # the box has somewhere to sit; the verifier at the foot of this file re-checks that
    # rather than trusting the sentence.
    leg = ax.legend(handles=handles, loc="upper right", frameon=True, framealpha=1.0,
                    edgecolor="0.8", handlelength=2.2, borderpad=0.42,
                    labelspacing=0.34, borderaxespad=0.35,
                    title="open marker = replayed\nfrom the $N{=}40$ run;\n"
                          "filled = directly measured",
                    title_fontsize=6.5)
    leg.get_title().set_color("0.25")
    leg.get_title().set_multialignment("left")
    leg.set_zorder(9)

    # --- panel (b): the matched paired differences -------------------------------
    # Limits and ticks are set BEFORE anything is placed, because `_clamped` reads them.
    bx.axvline(0.0, ls="--", lw=0.8, color="0.4", zorder=1)
    ys = [2, 1, 0]
    bx.set_yticks(ys)
    bx.set_yticklabels([f"{l}\n{k}" for l, k, *_ in DIFFS], fontsize=7)
    bx.set_ylim(-0.65, 2.65)
    bx.set_xlim(-14.8, 12.2)
    # Pinned for the same reason as panel (a)'s y ticks: same five values as before.
    bx.set_xticks([-10, -5, 0, 5, 10])

    def _clamped(x, y, s, gap=0.6, pad=0.25, **kw):
        """Centre `s` on x, then move it clear of the zero line and inside the axes.

        The zero line here IS the null hypothesis, and these labels carry an opaque white
        box so they stay readable over the grid. Centred on their own point, both labels
        of the 20 -> 40 row are wide enough to span x=0, and the box then punches a hole
        in the very line the row is being compared against -- measured, not guessed: they
        ran -5.213..+3.013 and -7.865..+5.665 before this was added. So a label that would
        lie across zero is shifted bodily to the side its own point is on, and every label
        is then clamped inside the axes.

        Deterministic. The shift comes from the rendered text extent, which depends only
        on the font, the font size and the figure geometry -- all fixed above -- and not on
        any random draw. `main()` is expected to reproduce this file byte for byte.
        """
        t = bx.text(x, y, s, ha="center", va="center", **kw)
        bx.figure.canvas.draw()
        inv = bx.transData.inverted()
        bb = t.get_window_extent(bx.figure.canvas.get_renderer())
        (x0, _), (x1, _) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        w = x1 - x0
        lo_x, hi_x = bx.get_xlim()
        cx = x if not (x0 < 0.0 < x1) else (
            (-gap - w / 2) if x < 0 else (gap + w / 2))
        t.set_position((min(max(cx, lo_x + pad + w / 2), hi_x - pad - w / 2), y))
        return t

    for y, (lbl, kind, d, lo, hi) in zip(ys, DIFFS):
        clears = hi < 0 or lo > 0
        col = "black" if clears else "0.55"
        bx.plot([lo, hi], [y, y], lw=1.0, color=col, solid_capstyle="butt", zorder=3)
        for e in (lo, hi):
            bx.plot([e, e], [y - 0.14, y + 0.14], lw=1.0, color=col, zorder=3)
        bx.plot([d], [y], marker="o", ms=3.6, mfc="black" if clears else "white",
                mec="black", mew=1.0, zorder=4)
        bb = dict(facecolor="white", edgecolor="none", pad=0.7)
        _clamped(d, y + 0.33, f"{d:+.1f} [{lo:+.1f}, {hi:+.1f}]", fontsize=6.8,
                 color="0.1", bbox=bb, zorder=5)
        _clamped(d, y - 0.34, "excludes zero" if clears else "covers zero: no step claimed",
                 fontsize=6.3, color="0.1" if clears else "0.4",
                 style="normal" if clears else "italic", bbox=bb, zorder=5)

    bx.set_xlabel("change in the floor (percentage points)")
    bx.set_title("(b)  matched paired differences,\n      same 200 questions",
                 loc="left", fontsize=8)
    bx.grid(axis="x", lw=0.5, color="0.9", zorder=0)
    bx.set_axisbelow(True)
    for a_ in (ax, bx):
        for s in ("top", "right"):
            a_.spines[s].set_visible(False)

    for ext in ("pdf", "png"):
        # NO WALL-CLOCK STAMP. Matplotlib writes /CreationDate into the PDF, so rebuilding
        # this figure without changing a single number still produced a modified file --
        # which destroys "the artifact is unchanged" as a check, the cheapest check there
        # is and the one you want most after editing a generator. `CreationDate: None`
        # omits the field; the PNG backend takes different keys and never carried one.
        meta = {"CreationDate": None} if ext == "pdf" else None
        fig.savefig(f"{stem}.{ext}", dpi=400, metadata=meta)
    plt.close(fig)


def write_sidecars(stem: Path, checks: dict) -> None:
    with open(f"{stem}_data.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["series", "budget_N", "provenance", "estimator", "value_pct",
                    "ci_lo_pct", "ci_hi_pct", "interval_kind", "population"])
        for n in (10, 20, 40):
            prov = ("replay of the N=40 checkpoint" if n < 40
                    else "direct measurement (August run)")
            ik = ("question bootstrap (questions only)" if n < 40 else
                  "none -- withdrawn, see results/n40_floor_estimator_ruling.md")
            row = [FLOOR[n][0],
                   "" if FLOOR[n][1] is None else FLOOR[n][1],
                   "" if FLOOR[n][2] is None else FLOOR[n][2]]
            w.writerow(["floor", n, prov, "min non-zero achievable FPR",
                        *row, ik, POOL_LONG])
        for n in (10, 20, 40):
            prov = ("replay of the N=40 checkpoint" if n < 40
                    else "direct measurement (August run)")
            ik = ("question bootstrap (questions only); same estimator as the floor"
                  if n < 40 else "Wilson on 0/200")
            w.writerow(["at_cap_mass", n, prov, "share of correct answers at ln N",
                        *ATCAP[n], ik, POOL_LONG])
        w.writerow(["floor", 10, "direct measurement (Week-4 June cache)",
                    "min non-zero achievable FPR", *DIRECT10, "Wilson on 19/200",
                    POOL_LONG])
        w.writerow(["at_cap_mass", 10, "direct measurement (Week-4 June cache)",
                    "share of correct answers at ln N", *DIRECT10, "Wilson on 19/200",
                    POOL_LONG])
        for lbl, kind, d, lo, hi in DIFFS:
            w.writerow(["paired_difference",
                        lbl.replace("$", "").replace("{=}", "=").replace("\\rightarrow", "->"),
                        kind, "matched paired bootstrap over the 200 questions",
                        d, lo, hi, "questions only", POOL_LONG])
    with open(f"{stem}_stats.json", "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild figures/fig_floor_budget.")
    # No --draws flag: the per-question saturation probabilities are computed exactly
    # (see p_at_cap), so there is nothing to sample and no knob that could change them.
    ap.add_argument("--boot", type=int, default=200000, help="bootstrap resamples")
    ap.add_argument("--seed", type=int, default=20260819)
    a = ap.parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    checks = rederive(a.boot, a.seed)
    stem = FIG_DIR / "fig_floor_budget"
    draw(stem)
    write_sidecars(stem, checks)
    print(f"wrote {stem}.pdf / .png plus sidecars; every plotted number re-derived from "
          f"{CKPT.name} and the Week-4 cache.")


if __name__ == "__main__":
    main()
