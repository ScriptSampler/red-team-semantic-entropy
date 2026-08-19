"""REPLAY CONTROL: is the direct-vs-replay gap a property of the method, or noise in the
direct measurement? And what survives when every budget comes from one source?

WHY THIS EXISTS
---------------
`results/n_scaling_grid.md` compares sample budgets, but its N=10 row is the DIRECT Week-4
cache while N=20 and N=40 come from the N=40 pairwise-verdict checkpoint. One claim has
already died on that mismatch: "TPR does not improve with budget" (27.5 -> 25.5 -> 24.0)
collapsed when N=10 was replayed out of the same checkpoint and gave 22.6% -- the
direct-vs-replay step (-4.9 pts) was larger than the budget effect being claimed (-3.5).

A second claim rests on the same mismatch: AUROC 0.704 (direct Week-4) versus 0.746 (N=40),
reported as "the budget makes it a better ranker". You cannot repair a claim broken by a
provenance mismatch with another statistic computed across the same mismatch, so this file
does three things and nothing else:

  1. characterises the replay-vs-direct gap on the floor, AUROC, low-FPR pAUC and TPR at a
     matched false-alarm rate, with enough replicates to say something about its SIGN and
     MAGNITUDE, and with the right null (the published control used 20 replicates and a
     sign test whose null is wrong -- see section 1 of the report);
  2. recomputes N=10 / N=20 / N=40 ALL by replay from the one checkpoint, which is the only
     internally consistent budget comparison this project owns;
  3. asks where a systematic gap could come from at all, given that a uniformly random
     k-subset of an exchangeable N-tuple is distributed exactly as k i.i.d. draws.

A STANDARD THIS FILE HAS TO MEET ITSELF
---------------------------------------
The error it corrects is "the interval covers zero, therefore the point estimate's sign is
the finding". The first draft committed that error twice, in its own summary bullets --
the most liftable text in the report and one copy-paste from `paper/`. Both were the
BLOCKED claims restated with the sign flipped, which is not a repair. So:

  * every directional statement about a difference goes through `directional_verdict()`,
    which physically cannot name a direction when the interval covers zero;
  * the report opens with a quotability banner (`_PROVENANCE`) naming which numbers are
    liftable and which are quarantined, on the precedent of `scripts/wk_seps_transfer.py`;
  * `tests/test_replay_control.py` greps the GENERATED report for the specific
    constructions, so a regression fails the suite rather than reaching the paper.

CPU-ONLY. No model is loaded, no GPU is touched: every score is replayed from the recorded
pairwise verdict matrix through the project's own clusterer. The replay machinery is
IMPORTED from `scripts/n_scaling_grid.py` rather than reimplemented, so a replayed score
here is bit-identical to the one in that report.

Run (Windows):
    .venv\\Scripts\\python.exe scripts\\replay_control.py
Run (inside WSL):
    ./.venv-wsl/bin/python scripts/replay_control.py

Writes results/replay_control.md.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Reuse, do not reimplement. `budget_scores` IS the subset-selection RNG and the replay
# path `scripts/n_scaling_grid.py` uses, so nothing below can drift from that report.
import n_scaling_grid as NSG                                            # noqa: E402
from fair_pool_granularity import wilson                                # noqa: E402
from se.attacks.select import _stratum_ids, load_labels                 # noqa: E402

DP = NSG.DP
SEED = NSG.SEED

# The date the report header carries. Pinned, not read from the clock -- see --generated
# in main(). Bump this when the underlying data changes, not when the script is rerun.
GENERATED_DATE = "2026-08-19"

# --------------------------------------------- the exact-p values, and why they live here
# `scripts/make_floor_budget_figure.py` computes the saturation quantities EXACTLY: "all
# singletons" is "the subset is an independent set of the verdict graph", so the probability
# is a ratio of independent-set counts and needs no sampling at all. THIS file computes them
# by Monte Carlo (40,000 subset draws per question), and on the 10 -> 20 paired leg the two
# disagree in the first decimal: MC says -8.8, exact says -8.8630, which is -8.9. The exact
# value is the right one, the paper prints 8.9, and an unmarked -8.8 in a table here is the
# evidence a reader uses to "correct" the paper downward -- which has been attempted once and
# was correctly refused.
#
# ONE DEFINITION, TWO RENDERINGS. Section 2c's prose and the mark on the differences table
# used to be independent literals; they are now the same constants, because two hand-typed
# copies of one number in one file is the defect this whole report exists to document.
EXACT_FLOOR_PCT = {10: 11.9921, 20: 3.1291}
EXACT_LEG_10_20_PTS = -8.8630
# The exact-p bootstrap endpoints for that leg, from figures/fig_floor_budget_stats.json
# ("matched paired difference N=10 -> N=20": rederived [-8.86, -11.06, -6.78]).
EXACT_LEG_10_20_CI = (-11.06, -6.78)
EXACT_FLOOR_LEG = {
    ("replay10", "replay20"):
        f" -- the point and the endpoints are MC; exact: {EXACT_LEG_10_20_PTS:.4f} "
        f"[{EXACT_LEG_10_20_CI[0]:.2f}, {EXACT_LEG_10_20_CI[1]:.2f}], i.e. "
        f"{EXACT_LEG_10_20_PTS:.1f} at one decimal, which is what the paper quotes",
}
NPS = NSG.N_PER_STRATUM
BUDGETS = (10, 20, 40)
TOL = 1e-12
BANDS = ((0.0, 0.05), (0.0, 0.10), (0.0, 0.20), (0.20, 0.50), (0.50, 1.0))
MATCHED = (0.05, 0.095, 0.10, 0.20)

# ===================================================================== quotability banner
# Stated where the report is produced rather than left for a reader to infer, on the
# precedent of `scripts/wk_seps_transfer.py` and `results/null_control_3arm_judge_n6.md`.
#
# WHY THIS FILE NEEDS ONE. Section 2 puts the ENTIRE blocked cross-budget set into a single
# pair of tables -- it has to, because refuting the two blocked claims means recomputing
# them like-for-like. That makes this the most dangerous file in `results/` to open for the
# floor trend: the blocked numbers sit in the adjacent column of the same table, which is
# exactly how `results/n_scaling_grid.md` section 3 nearly leaked TPR 11.0% into the paper.
QUARANTINED = ("0.746", "0.738", "11.0", "14.5", "12.75", "13.2", "12.3", "0.145", "0.126")
_PROVENANCE_PARAS = (
    "**PROVENANCE AND QUOTABILITY -- read before lifting any number out of this file.**"
    " Generated by `scripts/replay_control.py`; regenerate it, never edit it, or the fix"
    " you apply here is reverted the next time anyone reruns the script.",
    "**WITHDRAWN, 2026-08-19.** The N=40 floor's interval -- BOTH candidates. Wilson on"
    " 4/200 and the question bootstrap cover the true floor 53.7% and 0.00% of the time"
    " respectively at nominal 95%, because the estimand stops existing when the ceiling"
    " atom empties. Quote the point, 2.0%, with no interval, and quote the at-cap mass"
    " 0/200 = 0.0% [0.0%, 1.9%] beside it. Section 2c, and"
    " `results/n40_floor_estimator_ruling.md`. The `achieved FPR, B% budget` brackets are"
    " the range of the estimator and not confidence intervals; the paper takes Wilson on"
    " the count for those rows.",
    "**QUOTABLE.** The achievable-FPR floor trend taken entirely inside the replay family"
    " and labelled as such, WITH the matched intervals of section 2b and no others (the"
    " N=40 floor being a point without one); the"
    " section 2b variance decomposition itself; the N=40 first firing point and the"
    " section 5 diagnosis of the"
    " floor/ceiling-atom mix-up in `results/n_scaling_grid.md`; the unbiasedness argument"
    " and the replicate-correlation argument in section 3; the at-cap counts with their"
    " exact Poisson-binomial p-values; the cluster-count goodness-of-fit; and the"
    " generation-drift diagnostics (answer length, terminal punctuation, duplicate rate).",
    "**QUARANTINED -- do NOT lift into `paper/`.** Every cross-budget AUROC, pAUC and TPR"
    " cell in the section 2 tables, and every restatement of one in sections 4 and 6:"
    f" {', '.join(QUARANTINED)}, and ANY claim about the DIRECTION in which the low-FPR"
    " pAUC moves with budget. These are the two claims an earlier gate BLOCKED. This file"
    " refutes them; it does not license their negations, and a blocked directional claim"
    " does not become admissible by being restated with the sign flipped.",
    "**The rule that makes the quarantine checkable.** Every cross-budget interval in"
    " section 2 covers zero except the floor, so no cross-budget difference reported here"
    " may be quoted as a detectable effect, and the sign of any of those point estimates"
    " is not a finding. Note the asymmetry, added 2026-08-19: outside the floor row those"
    " intervals are TOO WIDE for the point estimates beside them (they resample the"
    " subset draw a second time), so their covering zero is a reason to claim nothing,"
    " NOT evidence that nothing is there. Two further mixing rules: the direct N=10 row"
    " keeps its Wilson interval as everywhere else in the paper while the replayed floor"
    " takes the matched question bootstrap of section 2b, and the two are never put in"
    " one table without saying which is which; and the direct row is shown for contrast"
    " only and must not be mixed into a budget trend.",
)
_PROVENANCE = "\n>\n".join(
    "\n".join("> " + ln for ln in textwrap.wrap(p, width=86)) for p in _PROVENANCE_PARAS
)


# ============================================================================ ROC pieces
def roc_curve_points(neg: np.ndarray, pos: np.ndarray):
    """(fpr, tpr) at every threshold either class can move, ascending, with (0,0) and (1,1).

    This is the curve pAUC integrates. It uses thresholds from BOTH classes because a pAUC
    is an area under the realised curve, not a statement about attainable operating points.
    """
    vals = np.unique(np.concatenate([neg, pos]))[::-1]
    fx = (neg[None, :] >= vals[:, None] - TOL).sum(1) / len(neg)
    fy = (pos[None, :] >= vals[:, None] - TOL).sum(1) / len(pos)
    fx = np.concatenate([[0.0], fx])
    fy = np.concatenate([[0.0], fy])
    if fx[-1] < 1.0 or fy[-1] < 1.0:
        fx = np.concatenate([fx, [1.0]])
        fy = np.concatenate([fy, [1.0]])
    return fx, fy


def deterministic_points(neg: np.ndarray, pos: np.ndarray):
    """(fpr, tpr) at the points an operator can actually deploy.

    The detector fires at `score >= tau`, so the FPR only changes at a value some NEGATIVE
    took: thresholds strictly between two observed negative values are the same policy.
    Includes the (0,0) "never fire" policy, which is always available."""
    vals = np.unique(neg)[::-1]
    fx = (neg[None, :] >= vals[:, None] - TOL).sum(1) / len(neg)
    fy = (pos[None, :] >= vals[:, None] - TOL).sum(1) / len(pos)
    return np.concatenate([[0.0], fx]), np.concatenate([[0.0], fy])


def auroc(neg: np.ndarray, pos: np.ndarray) -> float:
    """Mann-Whitney with mid-ranks, i.e. ties counted at 0.5. Identical to
    `sklearn.metrics.roc_auc_score` (checked to 1e-16) but ~7x faster, which matters
    because the bootstrap below evaluates it tens of thousands of times."""
    a = np.concatenate([neg, pos])
    order = np.argsort(a, kind="mergesort")
    s = a[order]
    ranks = np.empty(len(a), float)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    n_neg, n_pos = len(neg), len(pos)
    return float((ranks[n_neg:].sum() - n_pos * (n_pos + 1) / 2.0) / (n_neg * n_pos))


def pauc_band(fx: np.ndarray, fy: np.ndarray, lo: float, hi: float, n_grid: int = 2001):
    """MEAN TPR over the false-alarm band [lo, hi] -- i.e. pAUC divided by the band width.

    Chance inside the band is (lo + hi) / 2, NOT 0.5: a chance ROC has TPR = FPR, so its
    mean TPR over [0, 0.10] is 0.05. (`results/post_overnight_claim_review.md` labels this
    quantity "0.5 = chance within the band", which is wrong and makes a 3x-chance number
    read as a catastrophic one. See section 4 of the report.)"""
    gx = np.linspace(lo, hi, n_grid)
    return float(np.trapezoid(np.interp(gx, fx, fy), gx) / (hi - lo))


def upper_hull(fx: np.ndarray, fy: np.ndarray):
    """Upper convex hull of the achievable points: the randomised-rule frontier.

    An operator who can flip a coin between two deterministic thresholds can reach every
    point on the segment joining them, so this is the honest way to compare budgets whose
    deterministic grids do not line up."""
    pts = sorted(set(zip(fx.tolist(), fy.tolist())))
    hull: list[tuple[float, float]] = []
    for q in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            x3, y3 = q
            if (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1) >= 0:
                hull.pop()
            else:
                break
        hull.append(q)
    return hull


def tpr_matched(fx: np.ndarray, fy: np.ndarray, f: float) -> float:
    """TPR at EXACTLY false-alarm rate f, off the randomised frontier."""
    h = upper_hull(fx, fy)
    return float(np.interp(f, [x for x, _ in h], [y for _, y in h]))


def tpr_at_most(fx: np.ndarray, fy: np.ndarray, f: float) -> float:
    """Deterministic `at_most` rule: best TPR among deployable points with FPR <= f."""
    ok = fy[fx <= f + TOL]
    return float(ok.max()) if len(ok) else 0.0


def achieved_at_most(fx: np.ndarray, f: float) -> float:
    ok = fx[fx <= f + TOL]
    return float(ok.max()) if len(ok) else 0.0


def min_nonzero_fpr(neg: np.ndarray) -> float:
    """The smallest false-alarm rate a FIRING threshold can realise.

    This is the operator-facing floor. It equals the ceiling-atom mass whenever some
    negative sits at the ln N cap, and DIVERGES from it when none does -- which is exactly
    the case at N=40 and exactly the defect in `results/n_scaling_grid.md` section 1."""
    return 1.0 / len(neg) * int((neg >= neg.max() - TOL).sum())


def firing_fprs(neg: np.ndarray) -> list[float]:
    vals = np.unique(neg)[::-1]
    return [float((neg >= t - TOL).sum()) / len(neg) for t in vals]


def ceiling_atom(neg: np.ndarray, budget: int) -> int:
    """How many negatives sit exactly at the attainable maximum ln(budget)."""
    return int((neg >= math.log(budget) - 1e-9).sum())


def poisson_binomial_pmf(ps: np.ndarray) -> np.ndarray:
    """Exact distribution of a sum of independent, NON-identical Bernoullis.

    The right null for "the direct count of ceiling ties is 19 while the replay says each
    question i had probability p_i of tying": binomial is wrong because the p_i are wildly
    heterogeneous (most near 0, some near 1), and that heterogeneity SHRINKS the variance,
    which makes this the sharpest available test rather than the most forgiving one."""
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return dist


# ========================================================================= the stat pack
STATS = ["floor", "auroc", "pauc05", "pauc10", "pauc20", "pauc2050", "pauc50",
         "m05", "m095", "m10", "m20", "det05", "det10", "det20", "ach05", "ach10", "ach20"]
LABEL = {
    "floor": "floor (min non-zero achievable FPR)",
    "auroc": "AUROC",
    "pauc05": "pAUC, FPR <= 5% (mean TPR in band)",
    "pauc10": "pAUC, FPR <= 10% (mean TPR in band)",
    "pauc20": "pAUC, FPR <= 20% (mean TPR in band)",
    "pauc2050": "pAUC, FPR 20-50%",
    "pauc50": "pAUC, FPR 50-100%",
    "m05": "TPR at a matched 5.0% FPR",
    "m095": "TPR at a matched 9.5% FPR",
    "m10": "TPR at a matched 10.0% FPR",
    "m20": "TPR at a matched 20.0% FPR",
    "det05": "deterministic TPR, 5% budget",
    "det10": "deterministic TPR, 10% budget",
    "det20": "deterministic TPR, 20% budget",
    # The `ach*` brackets are the RANGE OF THE ESTIMATOR, not confidence intervals, and
    # the label says so wherever they are printed. "The largest achievable FPR at or below
    # B%" cannot exceed B by construction, so the upper endpoint is pinned at the budget
    # in essentially every resample; at N=10, where no threshold fires under 5%, both
    # endpoints are structurally 0 and the cell reads `0.0% [0.0%, 0.0%]`. Quoting one of
    # these as a 95% interval asserts a fact about the estimator's arithmetic as though it
    # were a fact about the world. The paper quotes Wilson on the count instead
    # (10/200 = 5.0% [2.7%, 9.0%]); see section 2c.
    "ach05": "achieved FPR, 5% budget (estimator range, NOT a CI)",
    "ach10": "achieved FPR, 10% budget (estimator range, NOT a CI)",
    "ach20": "achieved FPR, 20% budget (estimator range, NOT a CI)",
}


def stat_pack(neg: np.ndarray, pos: np.ndarray) -> dict:
    dx, dy = deterministic_points(neg, pos)
    rx, ry = roc_curve_points(neg, pos)
    out = {
        "floor": min_nonzero_fpr(neg),
        "auroc": auroc(neg, pos),
        "pauc05": pauc_band(rx, ry, 0.0, 0.05),
        "pauc10": pauc_band(rx, ry, 0.0, 0.10),
        "pauc20": pauc_band(rx, ry, 0.0, 0.20),
        "pauc2050": pauc_band(rx, ry, 0.20, 0.50),
        "pauc50": pauc_band(rx, ry, 0.50, 1.0),
    }
    for f, key in zip(MATCHED, ("m05", "m095", "m10", "m20")):
        out[key] = tpr_matched(dx, dy, f)
    for f, key in ((0.05, "05"), (0.10, "10"), (0.20, "20")):
        out["det" + key] = tpr_at_most(dx, dy, f)
        out["ach" + key] = achieved_at_most(dx, f)
    return out


# ============================================================================== the data
def read_checkpoint(path: Path) -> list[dict]:
    recs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not recs:
        raise SystemExit(f"no records in {path}")
    return recs


def adjacency(rec: dict) -> np.ndarray:
    n = int(rec["n_samples"])
    bits = rec["verdict_bits"]
    A = np.zeros((n, n), bool)
    for p, (i, j) in enumerate(combinations(range(n), 2)):
        if bits[p] == "1":
            A[i, j] = A[j, i] = True
    return A


def n_components_bits(rows: list[int], k: int) -> int:
    """Connected components of a k-node graph given as neighbour bitmasks. Same partition
    union-find would produce; bitmask BFS is ~10x faster and this runs ~10^6 times."""
    unseen = (1 << k) - 1
    count = 0
    while unseen:
        count += 1
        seed = unseen & -unseen
        comp = seed
        frontier = seed
        while frontier:
            nxt = 0
            f = frontier
            while f:
                b = f & -f
                nxt |= rows[b.bit_length() - 1]
                f ^= b
            frontier = nxt & ~comp
            comp |= frontier
        unseen &= ~comp
    return count


def subset_k_profile(A: np.ndarray, k: int, n_mc: int, rng) -> tuple[float, np.ndarray, float]:
    """(P(all k distinct), distribution of the cluster count, mean same-cluster pair rate)
    over uniformly random k-subsets of the recorded N-sample verdict matrix."""
    n = A.shape[0]
    hist = np.zeros(k + 1)
    all_singleton = 0
    same_pairs = 0.0
    pw = (1 << np.arange(k)).astype(np.int64)
    for _ in range(n_mc):
        s = rng.permutation(n)[:k]
        sub = A[np.ix_(s, s)]
        if not sub.any():
            all_singleton += 1
            hist[k] += 1
            continue
        rows = (sub * pw[None, :]).sum(1).tolist()
        labels = []
        # component ids via the same BFS, but recorded per node for the pair rate
        unseen = (1 << k) - 1
        cid = 0
        assign = [0] * k
        while unseen:
            seedbit = unseen & -unseen
            comp = seedbit
            frontier = seedbit
            while frontier:
                nxt = 0
                f = frontier
                while f:
                    b = f & -f
                    nxt |= rows[b.bit_length() - 1]
                    f ^= b
                frontier = nxt & ~comp
                comp |= frontier
            c = comp
            while c:
                b = c & -c
                assign[b.bit_length() - 1] = cid
                c ^= b
            unseen &= ~comp
            cid += 1
        hist[cid] += 1
        labels = assign
        same_pairs += sum(v * (v - 1) / 2 for v in Counter(labels).values()) / (k * (k - 1) / 2)
    return all_singleton / n_mc, hist / n_mc, same_pairs / n_mc


def saturation_probs(A_list, k: int, n_mc: int, rng) -> np.ndarray:
    """P(a uniformly random k-subset of a question's recorded samples is all-singletons).

    All-singletons happens iff no recorded pair INSIDE the subset is equivalent -- the
    subset is an independent set of the equivalence graph -- so this needs no clusterer,
    only the adjacency matrix. Same event as `n_scaling_grid.subset_ceiling_prob`, which
    the test suite pins this against; vectorised here because the matched interval wants
    an order of magnitude more draws per question than the profile section does.

    These p_i are the whole basis of the matched interval: the single-replicate floor is
    (1/n) sum_i Bernoulli(p_i), so `floor_variance_split` can split its variance exactly
    and the subset-averaged floor is just their mean."""
    out = np.empty(len(A_list))
    for t, A in enumerate(A_list):
        n = A.shape[0]
        if k > n:
            raise ValueError(f"budget {k} exceeds the recorded {n} samples")
        Au = A.astype(np.uint8)
        hits = done = 0
        while done < n_mc:
            b = min(4096, n_mc - done)
            idx = np.argsort(rng.random((b, n)), axis=1)[:, :k]
            sub = Au[idx[:, :, None], idx[:, None, :]].reshape(b, -1)
            hits += int((sub.sum(axis=1) == 0).sum())
            done += b
        out[t] = hits / n_mc
    return out


def floor_boot(scores: np.ndarray, qidx: np.ndarray) -> np.ndarray:
    """`min_nonzero_fpr` under a question bootstrap, re-finding the top score each time.

    Not the same as resampling a per-question indicator: at N=40 no negative reaches the
    cap, so which score IS the top can change from resample to resample. That dependence
    is the reason the headline difference has to be bootstrapped rather than adjusted."""
    M = scores[qidx]
    return (M >= M.max(axis=1, keepdims=True) - TOL).sum(axis=1) / M.shape[1]


# ================================================================================ report
def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


def ci(a) -> tuple[float, float]:
    a = np.asarray(a, float)
    return float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


# ------------------------------------------------ the un-liftability chokepoint
# Every word this report is not allowed to use about a difference whose interval covers
# zero. Kept as data so `tests/test_replay_control.py` can assert against the same list.
DIRECTIONAL_WORDS = (
    "rises", "rise", "risen", "rising", "falls", "fall", "fallen", "falling",
    "improves", "improve", "improvement", "worsens", "worsen", "increases", "increase",
    "decreases", "decrease", "gains", "grows", "shrinks", "drops", "climbs",
    "higher", "lower", "better", "worse", "buys almost nothing", "buys little",
    "buys nothing", "buys a lot",
)


def has_directional_word(s: str) -> bool:
    """True if `s` names a direction. Whole-word for single tokens, so "low-FPR" is not a
    hit on "lower" and "fallback" is not a hit on "fall"."""
    low = s.lower()
    return any(w in low if " " in w else re.search(rf"\b{re.escape(w)}\b", low)
               for w in DIRECTIONAL_WORDS)


def directional_verdict(label: str, d: float, lo: float, hi: float,
                        pct: bool = False) -> str:
    """The ONLY place this report is permitted to say which way a difference went.

    WHY THIS IS A FUNCTION AND NOT JUST A SENTENCE. This report exists because two paper
    claims asserted directions their intervals do not support. The first draft of the
    report then committed the same error twice, in its own summary, which is the most
    liftable text in the file: "the low-FPR pAUC does not fall with budget, it rises by
    +0.007" -- on an interval of [-0.0677, +0.0768] -- and "it buys almost nothing: TPR at
    a matched 5% is 12.3% against 13.2%", which is a gate-BLOCKED cross-budget comparison
    resurrected with the sign flipped and no interval at all.

    Two rules follow, and this function enforces the first mechanically:

      1. A point estimate's sign is not a finding when the interval covers zero. When it
         does, this function CANNOT emit a direction: the string it returns contains no
         word from DIRECTIONAL_WORDS, and the test suite asserts that over the whole
         (d, lo, hi) plane. To assert a direction here you must produce an interval that
         excludes zero.
      2. A blocked claim does not become admissible by being restated in the opposite
         direction. That one cannot be enforced by arithmetic, so it is enforced by the
         quarantine banner and by a test that greps the generated report for the specific
         constructions ("does not fall ... it rises", "buys almost nothing").
    """
    if has_directional_word(label):
        # otherwise a direction could be smuggled past the covers-zero branch in the noun
        # phrase, which is how the two defects this function exists to prevent were worded.
        raise ValueError(f"the label may not name a direction; got {label!r}")
    fmt = (lambda v: f"{v * 100:+.1f} pts") if pct else (lambda v: f"{v:+.4f}")
    span = f"point estimate {fmt(d)}, 95% [{fmt(lo)}, {fmt(hi)}]"
    if lo > 0 or hi < 0:
        way = "rises" if lo > 0 else "falls"       # the INTERVAL's sign, not the estimate's
        return f"{label} {way}: {span}, which excludes zero"
    return (f"{label}: no change is detectable in either direction ({span}, which covers "
            f"zero -- so the sign of the point estimate is not a result and must not be "
            f"quoted as one)")


# ------------------------------------- the interval/estimand chokepoint (2026-08-19, II)
# THE DEFECT THIS EXISTS TO PREVENT. The first version of this report quoted the
# SUBSET-AVERAGED replayed floor -- a point estimate from which the k-subset draw has been
# averaged out -- and attached to it an interval from a bootstrap that resamples targets
# AND redraws the subset. It then argued in prose that the wider interval was the honest
# one and that a single-replicate Wilson interval was "too narrow". That argument is
# false. Write the single-replicate floor as a mean of independent indicators X_i with
# P(X_i = 1) = p_i, where p_i is question i's probability that a random k-subset of its 40
# recorded samples comes out all-singletons. Then
#
#     mean_i p_i(1 - p_i)   +   var_i(p_i)     =   pbar(1 - pbar)
#     \___ subset draw ___/     \_ questions _/     \_ what Wilson/binomial already is _/
#
# identically. The subset-draw component is ALREADY INSIDE a single-replicate Wilson
# interval; it cannot be added to it a second time. And the estimator the report actually
# quotes has that component averaged away, so its interval must not contain it at all.
#
# HOW THIS IS ENFORCED. Every floor interval printed in this report is built by `quote()`,
# which takes the name of the estimand AND the list of things the interval resampled, and
# refuses the pair unless they match the registry below. Attaching the both-components
# bootstrap to the subset-averaged floor -- the exact defect above -- raises. This is the
# same shape as `directional_verdict`: a wrong statement is made unconstructible rather
# than merely proof-read out.
ESTIMAND_RESAMPLES = {
    # estimand printed  ->  what an interval for it MUST resample, and nothing else
    "single-replicate replayed floor": ("questions", "subset"),
    "subset-averaged replayed floor": ("questions",),
    "measured floor": ("questions",),
    "direct-cache floor": ("questions",),
}


@dataclass(frozen=True)
class Quoted:
    """A point estimate carrying the estimand it belongs to and the interval built for it.

    Constructed only through `quote()`, so an interval cannot reach the report without
    having been checked against its estimand."""
    estimand: str
    point: float
    lo: float
    hi: float
    resampled: tuple[str, ...]

    def pct(self) -> str:
        return f"{self.point:.1%} [{self.lo:.1%}, {self.hi:.1%}]"

    def pct_point(self) -> str:
        """The point estimate alone, as the tables render it. The only rendering
        `floor_trend` is allowed to chain."""
        return f"{self.point:.1%}"

    def pts(self) -> str:
        return f"{self.point * 100:+.1f} pts [{self.lo * 100:+.1f}, {self.hi * 100:+.1f}]"

    def covers_zero(self) -> bool:
        return self.lo <= 0.0 <= self.hi


def quote(estimand: str, point: float, lo: float, hi: float,
          resampled) -> Quoted:
    """Bind an interval to the estimand it is an interval FOR. Raise if they disagree."""
    want = ESTIMAND_RESAMPLES.get(estimand)
    if want is None:
        raise ValueError(f"unknown estimand {estimand!r}; add it to ESTIMAND_RESAMPLES "
                         f"together with the components its interval must resample")
    got = tuple(sorted(resampled))
    if got != tuple(sorted(want)):
        raise ValueError(
            f"interval/estimand mismatch: {estimand!r} needs an interval that resamples "
            f"exactly {tuple(sorted(want))}, but this one resampled {got}. "
            f"A component the point estimate averages over must not be resampled in its "
            f"interval, and a component it does not average over must not be omitted.")
    if not (lo <= point <= hi):
        raise ValueError(f"{estimand!r}: point {point} is outside [{lo}, {hi}]")
    return Quoted(estimand, float(point), float(lo), float(hi), got)


# ------------------------------------ the same chokepoint, for DIFFERENCES and TRENDS
# 2026-08-19, third pass. `quote()` was already in place and was BYPASSED. Sections 2 and
# 6 built their floor trend from `point[nm]["floor"]` -- the average over 200 whole
# replicates -- and their headline fall from `diff_ci(..., "floor")` -- the bootstrap that
# resamples targets AND redraws the subset. Neither object goes through `quote()`, so the
# estimand/interval check never ran, and the two sentences a reader lifts from went on
# printing the superseded "11.9% -> 3.0% -> 2.0%" and "-9.9 points [-15.5, -5.0]" for a
# day after section 2b superseded them. Three agent briefings carried the retired fall.
#
# A guard that only covers the table and not the prose is not a guard. So the two shapes
# the prose actually prints -- a TREND across budgets and a paired DIFFERENCE -- get
# constructors of their own, and both take `Quoted` objects rather than floats. A raw
# `point[nm]["floor"]` can no longer be formatted into either.
FLOOR_ESTIMANDS = ("single-replicate replayed floor", "subset-averaged replayed floor",
                   "measured floor", "direct-cache floor")


@dataclass(frozen=True)
class QuotedDiff:
    """A paired difference of two `Quoted` estimates, with the components ITS OWN interval
    resampled. Constructed only through `quote_diff()`."""
    a: Quoted
    b: Quoted
    point: float
    lo: float
    hi: float
    resampled: tuple[str, ...]

    def pts(self, unit: str = "pts") -> str:
        return (f"{self.point * 100:+.1f} {unit} "
                f"[{self.lo * 100:+.1f}, {self.hi * 100:+.1f}]")

    def covers_zero(self) -> bool:
        return self.lo <= 0.0 <= self.hi

    def excludes_zero(self) -> bool:
        return not self.covers_zero()


def quote_diff(a: Quoted, b: Quoted, point: float, lo: float, hi: float,
               resampled) -> QuotedDiff:
    """Bind a paired difference to the two estimates it is a difference OF.

    Refuses, in order: an arm that never went through `quote()`; two arms whose intervals
    resample different components (differencing a subset-averaged floor against a
    single-replicate one and calling the result matched); an interval that resamples
    something the arms' own intervals do not -- which is exactly the `diff_ci` bypass this
    was written for; and a point estimate that is not b - a, so a difference of
    UNMATCHED point estimates cannot be smuggled in beside two matched arms."""
    for nm, q in (("a", a), ("b", b)):
        if not isinstance(q, Quoted):
            raise TypeError(f"quote_diff arm {nm} must be a Quoted built by quote(); got "
                            f"{type(q).__name__}. A raw float here is the bypass this "
                            f"function exists to close.")
    if a.resampled != b.resampled:
        raise ValueError(
            f"cannot difference {a.estimand!r} (interval over {a.resampled}) against "
            f"{b.estimand!r} (interval over {b.resampled}): the two arms are not the same "
            f"kind of estimator, so their difference has no single matched interval.")
    got = tuple(sorted(resampled))
    if got != a.resampled:
        raise ValueError(
            f"interval/estimand mismatch on a difference: {a.estimand!r} -> {b.estimand!r} "
            f"needs an interval that resamples exactly {a.resampled}, but this one "
            f"resampled {got}. A component both point estimates average over must not be "
            f"re-added when they are differenced.")
    if abs((b.point - a.point) - point) > 1e-9:
        raise ValueError(
            f"the difference {point} is not {b.estimand!r} minus {a.estimand!r} "
            f"({b.point} - {a.point} = {b.point - a.point}). The point estimate and the "
            f"interval must come off the same pair of arms.")
    if not (lo <= point <= hi):
        raise ValueError(f"difference {point} is outside [{lo}, {hi}]")
    return QuotedDiff(a, b, float(point), float(lo), float(hi), got)


def floor_trend(*qs: Quoted) -> str:
    """The ONLY place this report may print the floor as a trend across budgets.

    The analogue of `directional_verdict`: the wrong sentence is made unconstructible
    rather than proof-read out. Three refusals, each of them a rule the report already
    states in prose and could not previously enforce:

      1. a raw float is not a trend term -- it has no estimand, so nothing checked its
         interval, and that is precisely how the retired 11.9%/3.0% pair survived;
      2. the arms must all be floors, and all the same KIND of floor, because a trend
         reads as one estimator measured at several budgets;
      3. the direct Week-4 cache may not appear in a trend at all. That is this file's own
         banner rule ("the direct row is shown for contrast only and must not be mixed
         into a budget trend"), which until now lived only in the banner.
    """
    if len(qs) < 2:
        raise ValueError("a trend needs at least two budgets")
    for q in qs:
        if not isinstance(q, Quoted):
            raise TypeError(f"floor_trend takes Quoted floors, not raw numbers; got "
                            f"{type(q).__name__}. A trend built from a float bypasses "
                            f"quote() -- see the comment above this function.")
        if q.estimand not in FLOOR_ESTIMANDS:
            raise ValueError(f"{q.estimand!r} is not a floor, so it is not a term in the "
                             f"floor trend")
        if q.estimand == "direct-cache floor":
            raise ValueError("the direct Week-4 cache may not be a term in a budget "
                             "trend: it is a different generation run, which is the "
                             "provenance step this whole report exists to remove")
    if any(q.resampled != qs[0].resampled for q in qs):
        raise ValueError("a trend may not mix estimators whose intervals resample "
                         "different components")
    return " -> ".join(q.pct_point() for q in qs)


# --------------------------------------------- the artifact audit (2026-08-19, third)
# Recorded so it cannot come back, on the precedent of `results/derived_paper_quantities.md`
# ("9.9 is superseded"). These are the renderings the retired single-replicate floor and
# the retired both-components fall produce. They are checked for ABSENCE in the generated
# report; the two structural rules below catch a relapse that is worded differently.
RETIRED_QUOTES = (
    "11.9% -> 3.0% -> 2.0%",
    "11.9% -> 3.0%",
    "-9.9 points [-15.5, -5.0]",
    "-9.9 pts [-15.5, -5.0]",
    # Withdrawn 2026-08-19 by results/n40_floor_estimator_ruling.md: BOTH candidate
    # intervals for the measured N=40 floor. Section 2c may name them (that is where the
    # withdrawal is argued); nowhere else may print one as the floor's interval, so these
    # are the renderings that pair an interval with the 2.0% point.
    "2.0% [0.8%, 5.0%]",
    "2.0% [0.5%, 4.0%]",
    "2.0% [0.78%, 5.03%]",
)

# A trend chain of percentages. In this report the only quantity written that way is the
# floor, so every match is a floor trend and must equal the one the section 2 table holds.
_TREND_RE = re.compile(r"\d+(?:\.\d+)?% *-> *\d+(?:\.\d+)?%(?: *-> *\d+(?:\.\d+)?%)*")
# A difference quoted in PROSE: "<d> pts [<lo>, <hi>]". The table form puts a cell wall
# between the point and its interval ("| +2.5 pts | [-0.7 pts, +5.5 pts] |"), so this
# matches prose only -- which is the surface that gets lifted.
_PROSE_DIFF_RE = re.compile(
    r"([+-]?\d+(?:\.\d+)?) *(?:pts|points) *"
    r"\[ *([+-]?\d+(?:\.\d+)?)[^],]*, *([+-]?\d+(?:\.\d+)?)[^]]*\]")
# The same triple as a table row, which is where the checked objects are rendered.
_TABLE_DIFF_RE = re.compile(
    r"\| *([+-]?\d+(?:\.\d+)?) pts *\| *"
    r"\[ *([+-]?\d+(?:\.\d+)?) pts *, *([+-]?\d+(?:\.\d+)?) pts *\] *\|")
# The section 2 floor row, which is built from `matched[...]` and is therefore the one
# rendering of the floor in this file that `quote()` has vouched for.
# Each of the four cells is a rate followed EITHER by an interval OR by an explicit
# no-interval marker. The second form was added 2026-08-19 for the measured N=40 cell,
# whose interval was withdrawn; the alternation is deliberately narrow so that any OTHER
# reshaping of the row still trips the audit, and `_MEASURED_FLOOR_CELL_RE` below then
# insists that the last cell really is the no-interval form.
_FLOOR_CELL = r"(\d+(?:\.\d+)?%) (?:\[[^\]]*\]|\(no interval[^)]*\))"
_MATCHED_FLOOR_ROW_RE = re.compile(
    r"^\| floor \(min non-zero achievable FPR\) -- MATCHED[^|]*\|"
    r"(?: *" + _FLOOR_CELL + r" *\|){4}$", re.M)
_FLOOR_ROW_CELL_RE = re.compile(_FLOOR_CELL)
# The measured budget is the LAST cell of that row, and it must carry no interval.
_MEASURED_FLOOR_CELL_RE = re.compile(r"\|\s*(\d+(?:\.\d+)?%) \(no interval[^)]*\)\s*\|$")

# ------------------------------------------- rule 3: the two tables must tell one story
# THE DEFECT THIS IS WRITTEN FOR (2026-08-19, fourth round). The "Which interval goes with
# which estimator" table -- the one table in this repo whose entire job is to state that
# mapping -- went on saying the measured N=40 floor takes "Wilson on the count" for a whole
# round after the floor table thirteen lines below it had been changed to "none --
# withdrawn". Nothing caught it. It is prose in a table cell and not an `X% [a, b]`
# rendering, so every check above looks straight past it; it is hard-coded in this
# generator, so regenerating reprinted it; and it contradicted the banner 340 lines above
# it, section 2c, and the paper, all at once.
#
# WHY THIS IS NOT A STRING MATCH. Pinning the corrected sentence would pin TODAY'S ruling
# into the checker, and the next time the ruling moves the checker becomes the thing that
# has to be argued with rather than the thing that catches the drift. What is actually
# wrong is DISAGREEMENT: three cells in this file answer the single question "does the
# measured floor carry an interval?", and they may differ only if someone stopped reading.
# So the rule reads a stance off each cell with one shared predicate and requires the
# stances to match, whatever they are. Overturn the ruling in the floor table and this rule
# demands the estimator table follow; it never demands a particular answer.
_STANCE_NONE_RE = re.compile(r"\bnone\b|\bno interval\b|\bwithdrawn\b", re.I)
# `\binterval\b` is safe here ONLY because the no-interval predicate is consulted
# first: "no interval" and "none -- withdrawn" both contain it. The column is headed
# "the interval it takes", so a cell that gets this far and still names an interval is
# assigning one -- including one this repo has never used, which is the case that
# exposed the gap.
_STANCE_ESTIMATOR_RE = re.compile(
    r"\bWilson\b|\bbootstrap\b|\binterval\b|\[[^\]]*\]", re.I)

# The measured-budget row of the estimator table: "| the measured N=40 floor | ... | ... |"
_ESTIMATOR_TABLE_ROW_RE = re.compile(
    r"^\| the measured N=\d+ floor \|[^|]*\|([^|]*)\|$", re.M)
# The measured-budget row of the "floor, quoted correctly" table. Its SECOND value column
# -- the third cell -- is "95%, questions only", which is where that table states a stance.
_FLOOR_QUOTED_ROW_RE = re.compile(
    r"^\| measured N=\d+ \|[^|]*\|([^|]*)\|", re.M)


def _interval_stance(cell: str) -> str:
    """Does this cell say the measured floor HAS an interval, or that it has none?

    Order matters and is deliberate: a cell that declares a withdrawal is declaring one
    even while it names the candidates it withdrew ("none -- both candidates withdrawn ...
    Wilson would give ..."). Only a cell that names an estimator, or prints a bracket, with
    no withdrawal language anywhere in it, is assigning an interval."""
    if _STANCE_NONE_RE.search(cell):
        return "no interval"
    if _STANCE_ESTIMATOR_RE.search(cell):
        return "an interval"
    return "unreadable"


def audit_estimator_table_agrees_with_the_floor_table(text: str) -> list[str]:
    """Three cells, one question, one answer. Empty list means clean.

    Kept separate from `audit_report_floor_quotes` only so that a failure names itself.
    Both run in the generator before it writes, and both run in the test suite against the
    committed `.md`."""
    bad: list[str] = []
    sites: dict[str, str] = {}

    row = _MATCHED_FLOOR_ROW_RE.search(text)
    if row is None:
        bad.append("the section 2 MATCHED floor row is missing or reshaped, so the "
                   "estimator table has nothing to be checked against")
    else:
        sites["the section 2 MATCHED floor row's measured cell"] = _interval_stance(
            row.group(0).rsplit("|", 2)[1])

    m = _ESTIMATOR_TABLE_ROW_RE.search(text)
    if m is None:
        bad.append("the measured-budget row of the 'which interval goes with which "
                   "estimator' table is missing or reshaped. That table's whole job is to "
                   "state the estimator/interval mapping, so it may not quietly drop the "
                   "one row the mapping was got wrong on")
    else:
        sites["the estimator table's measured row"] = _interval_stance(m.group(1))

    m = _FLOOR_QUOTED_ROW_RE.search(text)
    if m is None:
        bad.append("the measured-budget row of the 'floor, quoted correctly' table is "
                   "missing or reshaped")
    else:
        sites["the 'floor, quoted correctly' table's measured row"] = _interval_stance(
            m.group(1))

    for where, stance in sites.items():
        if stance == "unreadable":
            bad.append(f"{where} states no position on whether the measured floor carries "
                       f"an interval. It must say one or the other: silence in that cell "
                       f"is how the withdrawn position survived a consolidating pass")
    stances = {v for v in sites.values() if v != "unreadable"}
    if len(stances) > 1:
        detail = "; ".join(f"{w} says {v}" for w, v in sorted(sites.items()))
        bad.append(
            f"this file disagrees with itself about whether the measured N=40 floor "
            f"carries an interval -- {detail}. One of them is a leftover from before "
            f"results/n40_floor_estimator_ruling.md withdrew both candidates. Fix the one "
            f"that is wrong; if the RULING has changed, change it there first, then all "
            f"three of these together.")
    return bad


def audit_report_floor_quotes(text: str) -> list[str]:
    """Read the generated report back and return every place it quotes a floor that its
    own checked tables do not support. Empty list means clean.

    This is the half of the fix that survives the next edit. `quote()` guards the objects;
    this guards the ARTIFACT, so a site that formats its own floats -- the bypass that
    happened -- is caught in the output even though it never touched `quote()`. Written as
    a pure function of the text so that the generator can run it on itself before writing
    and the test suite can run the identical check on the committed `.md`.

    Three rules:
      0. no retired rendering appears anywhere;
      1. every trend chain equals the replay-family trend of the section 2 MATCHED floor
         row -- and by construction that row excludes the direct cache;
      2. every difference quoted in prose appears as a row of one of this report's own
         difference tables. A prose figure with no table behind it is the shape of the
         defect: a number that was current when the sentence was written and was not
         updated when the table was.
    """
    flat = re.sub(r"\s+", " ", text)
    bad: list[str] = []

    for r in RETIRED_QUOTES:
        if r in flat:
            bad.append(f"retired rendering {r!r} is printed in the report; it was "
                       f"superseded by the matched floor of section 2b")

    row = _MATCHED_FLOOR_ROW_RE.search(text)
    if row is None:
        bad.append("the section 2 MATCHED floor row is missing or reshaped, so no trend "
                   "in this file can be checked against it")
    else:
        if not _MEASURED_FLOOR_CELL_RE.search(row.group(0)):
            bad.append(
                "the measured-budget cell of the section 2 MATCHED floor row carries an "
                "interval again. Both candidates were withdrawn on measured coverage "
                "(Wilson 53.7%, question bootstrap 0.00%, nominal 95%) -- see section 2c "
                "and results/n40_floor_estimator_ruling.md. If that ruling has been "
                "overturned, overturn it there first.")
        cells = _FLOOR_ROW_CELL_RE.findall(row.group(0))
        want = " -> ".join(cells[1:])          # cells[0] is the direct cache: never in a trend
        for m in _TREND_RE.finditer(flat):
            got = " ".join(m.group(0).split())
            if got != want:
                bad.append(f"floor trend {got!r} disagrees with the MATCHED floor row of "
                           f"section 2, which says {want!r}")

    table = {m.groups() for m in _TABLE_DIFF_RE.finditer(flat)}
    for m in _PROSE_DIFF_RE.finditer(flat):
        if m.groups() not in table:
            bad.append(f"the prose quotes a difference {m.group(0)!r} that appears in no "
                       f"table of this report; every quotable difference here is a row of "
                       f"the section 1 step table or the section 2 differences table")
    return bad


def floor_variance_split(p: np.ndarray) -> dict:
    """The identity above, evaluated on the per-question saturation probabilities.

    Returns standard deviations, in rate units, of the SINGLE-REPLICATE floor:
      sd_questions  -- what survives when the subset draw is averaged out (the matched sd)
      sd_subset     -- what the subset draw alone contributes
      sd_rss        -- the two combined
      sd_binomial   -- sqrt(pbar(1-pbar)/n), i.e. what Wilson already reports
    `sd_rss` and `sd_binomial` are equal by construction; the report prints both so that a
    reader can see the identity hold rather than take it on trust."""
    n = len(p)
    pbar = float(p.mean())
    v_q = float(p.var(ddof=0)) / n
    v_s = float((p * (1.0 - p)).mean()) / n
    return {"pbar": pbar, "n": n,
            "sd_questions": math.sqrt(v_q), "sd_subset": math.sqrt(v_s),
            "sd_rss": math.sqrt(v_q + v_s),
            "sd_binomial": math.sqrt(pbar * (1.0 - pbar) / n),
            "residual": v_s + v_q - pbar * (1.0 - pbar) / n}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", default=str(RESULTS_DIR / "n_scaling_ckpt.jsonl"))
    ap.add_argument("--cache", default=None, help="Week-4 cache dir (relabeled/entropy/samples)")
    ap.add_argument("--replicates", type=int, default=200, help="subset draws per replayed budget")
    ap.add_argument("--boot", type=int, default=4000, help="bootstrap resamples")
    ap.add_argument("--mc", type=int, default=4000, help="subset draws per question for the K profile")
    ap.add_argument("--sat-mc", type=int, default=40000, dest="sat_mc",
                    help="subset draws per question for the per-question saturation "
                         "probabilities that carry the matched floor interval")
    ap.add_argument("--boot-matched", type=int, default=400000, dest="boot_matched",
                    help="question-bootstrap resamples for the matched floor intervals. "
                         "Large on purpose: at 20000 the 2.5%% percentile still moved 0.13 "
                         "points across resample seeds, which is more than the first "
                         "decimal place the paper quotes")
    ap.add_argument("--out", default=None)
    # NOT date.today(). A wall-clock stamp means a regenerated report always byte-differs
    # from the committed one, which destroys "the file is unchanged" as a check -- the
    # cheapest check there is, and the one you want most after editing a 1800-line
    # generator. The date is an INPUT: it records the run the report describes, not the
    # moment someone happened to rerun the script. Bump it when the DATA changes.
    ap.add_argument("--generated", default=GENERATED_DATE,
                    help="date stamped in the report header (default: the pinned "
                         f"{GENERATED_DATE}). Regenerating without changing the data "
                         "must reproduce the file byte for byte.")
    args = ap.parse_args(argv)

    recs = read_checkpoint(Path(args.checkpoint))
    if any(r.get("scorer") == "fake" for r in recs):
        raise SystemExit("this checkpoint was written by the FAKE scorer -- refusing to "
                         "write a finding into results/")
    top = max(int(r["n_samples"]) for r in recs)
    cache = NSG.resolve_cache(args.cache)

    labels = load_labels(cache / "relabeled.jsonl")
    fp_c = _stratum_ids("right", SEED, labels)[:NPS]
    fp_h = _stratum_ids("wrong", SEED, labels)[:NPS]
    ck_c = sorted(r["question_id"] for r in recs if r["stratum"] == "correct")
    ck_h = sorted(r["question_id"] for r in recs if r["stratum"] == "hallucinating")
    ids_match = (sorted(fp_c) == ck_c and sorted(fp_h) == ck_h)
    if not ids_match:
        raise SystemExit("the checkpoint's targets are NOT the fair pool -- every paired "
                         "comparison in this report would be invalid")

    ent = {q: round(float(r["entropy_nats"]), DP) for q, r in labels.items()}
    direct = (np.array([ent[q] for q in fp_c]), np.array([ent[q] for q in fp_h]))

    byq = {r["question_id"]: r for r in recs}
    assign10 = {}
    for line in (cache / "entropy.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if "assignments" in d:
                assign10[d["question_id"]] = d["assignments"]
    samples10 = {}
    for line in (cache / "samples.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            samples10[d["question_id"]] = d["samples"]

    # ---------------------------------------------------------------- replay ensembles
    print(f"[replay] {args.replicates} subset draws per replayed budget ...", file=sys.stderr)
    ens: dict[int, list[tuple[np.ndarray, np.ndarray]]] = {}
    for b in BUDGETS:
        reps = []
        for r in range(1 if b == top else args.replicates):
            sn = NSG.budget_scores(recs, b, "correct", replicate=r)
            sp = NSG.budget_scores(recs, b, "hallucinating", replicate=r)
            reps.append((np.array([round(sn[q], DP) for q in fp_c]),
                         np.array([round(sp[q], DP) for q in fp_h])))
        ens[b] = reps
        print(f"[replay]   N={b}: {len(reps)} realisation(s)", file=sys.stderr)

    SRC = {"direct10": [direct], "replay10": ens[10], "replay20": ens[20],
           f"measured{top}": ens[top]}
    NAMES = list(SRC)
    packs = {nm: [stat_pack(n, p) for n, p in reps] for nm, reps in SRC.items()}
    point = {nm: {k: float(np.mean([q[k] for q in pk])) for k in STATS}
             for nm, pk in packs.items()}

    # ------------------------------------------------------------------- the bootstrap
    print(f"[boot] {args.boot} resamples over targets x subset draw ...", file=sys.stderr)
    rng = np.random.default_rng(SEED)
    boot = {nm: {k: np.empty(args.boot) for k in STATS} for nm in NAMES}
    for t in range(args.boot):
        i_c = rng.integers(0, NPS, NPS)
        i_h = rng.integers(0, NPS, NPS)
        for nm in NAMES:
            reps = SRC[nm]
            neg, pos = reps[rng.integers(0, len(reps))]
            pk = stat_pack(neg[i_c], pos[i_h])
            for k in STATS:
                boot[nm][k][t] = pk[k]

    # ------------------------------------------------------ mechanism: subset profiles
    print(f"[mech] per-question subset profiles, {args.mc} draws ...", file=sys.stderr)
    mrng = np.random.default_rng(12345)
    mech = {}
    for stratum, ids in (("correct", fp_c), ("hallucinating", fp_h)):
        p_all, k_hist, sc_replay, sc_direct, k_direct = [], [], [], [], []
        dup_d, dup_r = [], []
        for q in ids:
            A = adjacency(byq[q])
            pa, hist, scr = subset_k_profile(A, 10, args.mc, mrng)
            p_all.append(pa)
            k_hist.append(hist)
            sc_replay.append(scr)
            a = assign10[q]
            k_direct.append(len(set(a)))
            sc_direct.append(sum(v * (v - 1) / 2 for v in Counter(a).values()) / 45.0)
            sd = samples10[q]
            dup_d.append(1 - len(set(sd)) / len(sd))
            sr = byq[q]["samples"]
            n = len(sr)
            dup_r.append(float(np.mean([1 - len({sr[i] for i in mrng.permutation(n)[:10]}) / 10.0
                                        for _ in range(200)])))
        mech[stratum] = dict(
            p_all=np.array(p_all), k_hist=np.array(k_hist), k_direct=np.array(k_direct),
            sc_replay=np.array(sc_replay), sc_direct=np.array(sc_direct),
            dup_d=np.array(dup_d), dup_r=np.array(dup_r))

    # ------------------------------------------- the matched floor: point AND interval
    # Separate from `boot` above on purpose. `boot` resamples targets and redraws the
    # subset, which is the sampling distribution of a SINGLE-REPLICATE statistic. The
    # floor this report quotes is the subset-averaged one, and its interval may not
    # re-add a component the point estimate has averaged out -- see `quote()`.
    print(f"[matched] per-question saturation probabilities, {args.sat_mc} draws ...",
          file=sys.stderr)
    srng = np.random.default_rng((SEED, 20260819))
    A_c = [adjacency(byq[q]) for q in fp_c]
    sat = {b: saturation_probs(A_c, b, args.sat_mc, srng) for b in BUDGETS if b < top}
    sat_mc_sd = {b: math.sqrt(float((p * (1 - p)).mean()) / (NPS * args.sat_mc))
                 for b, p in sat.items()}
    split = {b: floor_variance_split(p) for b, p in sat.items()}
    # P(not one of the 200 negatives saturates), i.e. P(the floor is NOT the ceiling atom)
    p_no_atom = {b: float(np.prod(1.0 - p)) for b, p in sat.items()}

    # Chunked, because the resample count has to be large -- the 2.5%% percentile of a
    # bootstrap is itself a Monte-Carlo estimate, and at 20000 resamples its own spread
    # across seeds (0.13 points on the N=10 lower endpoint) exceeded the precision the
    # paper prints. All arms are evaluated on the SAME index block so the differences
    # below stay paired.
    print(f"[matched] {args.boot_matched} question-bootstrap resamples ...", file=sys.stderr)
    qrng = np.random.default_rng((SEED, 2))
    meas_name = f"measured{top}"
    _arms = [f"replay{b}" for b in sat] + [meas_name, "direct10"]
    mboot = {nm: np.empty(args.boot_matched) for nm in _arms}
    _CHUNK = 5000
    for _a in range(0, args.boot_matched, _CHUNK):
        _n = min(_CHUNK, args.boot_matched - _a)
        QIDX = qrng.integers(0, NPS, (_n, NPS))
        for b in sat:
            mboot[f"replay{b}"][_a:_a + _n] = sat[b][QIDX].mean(axis=1)
        mboot[meas_name][_a:_a + _n] = floor_boot(ens[top][0][0], QIDX)
        mboot["direct10"][_a:_a + _n] = floor_boot(direct[0], QIDX)
    mpoint = {f"replay{b}": float(p.mean()) for b, p in sat.items()}
    mpoint[meas_name] = min_nonzero_fpr(ens[top][0][0])
    mpoint["direct10"] = min_nonzero_fpr(direct[0])
    # Both interval kinds below resample the questions and nothing else, which is what
    # `quote()` checks. Which of the two is used is a separate, disclosed convention: a
    # row that is a plain count of 200 targets takes Wilson, as everywhere else in the
    # paper, and only the replayed rows -- where the point estimate is an average over
    # subset draws and no count exists -- take the bootstrap. `mboot` is still built for
    # every row, because a PAIRED difference has to come off shared resamples.
    matched: dict[str, Quoted] = {}
    for nm, draws in mboot.items():
        if nm.startswith("replay"):
            lo, hi = ci(draws)
            matched[nm] = quote("subset-averaged replayed floor", mpoint[nm], lo, hi,
                                ("questions",))
        else:
            cnt = int(round(mpoint[nm] * NPS))
            _, lo, hi = wilson(cnt, NPS)
            estimand = "direct-cache floor" if nm == "direct10" else "measured floor"
            matched[nm] = quote(estimand, mpoint[nm], lo, hi, ("questions",))

    # sample-level provenance diagnostics, paired per question
    term = ('.', '!', '?', '"', '”', ')')
    len_d, len_r, end_d, end_r = [], [], [], []
    for q in fp_c + fp_h:
        sd, sr = samples10[q], byq[q]["samples"]
        len_d.append(float(np.mean([len(x) for x in sd])))
        len_r.append(float(np.mean([len(x) for x in sr])))
        end_d.append(float(np.mean([x.rstrip().endswith(term) for x in sd])))
        end_r.append(float(np.mean([x.rstrip().endswith(term) for x in sr])))
    len_d, len_r = np.array(len_d), np.array(len_r)
    end_d, end_r = np.array(end_d), np.array(end_r)

    out_path = Path(args.out) if args.out else RESULTS_DIR / "replay_control.md"
    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    write_report(log, args, recs, top, cache, SRC, NAMES, packs, point, boot, mech,
                 direct, ens, len_d, len_r, end_d, end_r,
                 matched=matched, mboot=mboot, sat=sat, split=split,
                 sat_mc_sd=sat_mc_sd, p_no_atom=p_no_atom)
    # Audit the artifact before it is written, not after. `quote()` guards the objects; a
    # site that formats its own floats never touches it, which is how sections 2 and 6
    # kept printing a superseded floor. This reads the finished text back and refuses to
    # write a report whose prose disagrees with its own checked tables.
    _report_text = "\n".join(report)
    violations = (audit_report_floor_quotes(_report_text)
                  + audit_estimator_table_agrees_with_the_floor_table(_report_text))
    if violations:
        raise SystemExit(
            "[audit] refusing to write " + str(out_path) + ": the report quotes a floor "
            "its own tables do not support.\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n  Build the sentence from `matched[...]` via floor_trend()/matched_diff()."
        )
    out_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out_path}", file=sys.stderr)
    return 0


def write_report(log, args, recs, top, cache, SRC, NAMES, packs, point, boot, mech,
                 direct, ens, len_d, len_r, end_d, end_r, *,
                 matched, mboot, sat, split, sat_mc_sd, p_no_atom) -> None:
    R = len(SRC["replay10"])
    meas = f"measured{top}"

    def spread(nm, k):
        v = np.array([q[k] for q in packs[nm]])
        return v.mean(), (v.std(ddof=1) if len(v) > 1 else 0.0), v.min(), v.max()

    def diff_ci(a, b, k):
        d = boot[b][k] - boot[a][k]
        lo, hi = ci(d)
        return point[b][k] - point[a][k], lo, hi

    def matched_diff(a, b) -> QuotedDiff:
        """Paired floor difference b - a on the SAME question-bootstrap resamples.

        Paired because both arms are read off one resampled set of 200 questions, and the
        two floors are strongly dependent (at N=10 and N=20 they are means of indicators
        for the same questions; at N=40 the top score can move to a different question in
        a resample, which is why this is bootstrapped and not adjusted by hand).

        Returns a `QuotedDiff` and not a bare triple, so that a caller cannot print the
        difference of two matched arms with somebody else's interval around it."""
        d = mboot[b] - mboot[a]
        lo, hi = ci(d)
        return quote_diff(matched[a], matched[b],
                          matched[b].point - matched[a].point, lo, hi, ("questions",))

    def wrap(s: str, indent: str = "") -> None:
        """Emit a generated sentence at the file's hard-wrap width.

        `directional_verdict` returns one long string whose length depends on the numbers
        in it, so it cannot be hand-wrapped in the source without the wrapping going stale
        the first time the checkpoint changes."""
        for ln in textwrap.wrap(s, width=88 - len(indent)):
            log(indent + ln)

    # ------------------------------------------------------------------------------
    # Everything the prose asserts is computed HERE and interpolated. No number in this
    # report is typed by hand: a report that hard-codes its own findings goes stale the
    # first time the checkpoint grows, and this project has been bitten by that before.
    F: dict[str, float] = {}
    for k in ("floor", "auroc", "pauc05", "pauc10", "m05", "m095", "m10"):
        F[f"step_{k}"] = point["replay10"][k] - point["direct10"][k]
    # the floor's step is taken from the matched pair, so the prose cannot disagree with
    # the table above it; every other step stays on the replicate-average point estimates
    F["step_floor"] = matched["replay10"].point - matched["direct10"].point
    F["step_floor_rel"] = F["step_floor"] / matched["direct10"].point
    reps_floor = np.array([q["floor"] for q in packs["replay10"]])
    F["n_below"] = float((reps_floor < point["direct10"]["floor"]).sum())
    F["frac_below"] = F["n_below"] / R
    F["p_unanimous"] = (1.0 - F["frac_below"]) ** 20
    F["gain_direct"] = point[meas]["auroc"] - point["direct10"]["auroc"]
    F["gain_ll"] = point[meas]["auroc"] - point["replay10"]["auroc"]
    F["gain_ll_lo"], F["gain_ll_hi"] = ci(boot[meas]["auroc"] - boot["replay10"]["auroc"])
    F["share_source"] = 1.0 - F["gain_ll"] / F["gain_direct"]
    F["pauc10_direct_step"] = point[meas]["pauc10"] - point["direct10"]["pauc10"]
    F["pauc10_ll"] = point[meas]["pauc10"] - point["replay10"]["pauc10"]
    F["pauc10_ll_lo"], F["pauc10_ll_hi"] = ci(boot[meas]["pauc10"] - boot["replay10"]["pauc10"])
    F["pauc10_ratio"] = abs(F["pauc10_direct_step"] / F["pauc10_ll"])
    # the one verdict the summary is allowed to state about the low-FPR pAUC
    PAUC10_LL = directional_verdict("the like-for-like low-FPR pAUC (replay N=10 -> "
                                    f"measured N={top})", F["pauc10_ll"],
                                    F["pauc10_ll_lo"], F["pauc10_ll_hi"])
    a10 = np.array([q["auroc"] for q in packs["replay10"]])
    F["n_ties_40"] = float((a10 >= point[meas]["auroc"]).sum())

    # the redundancy decomposition: how much of each "bias" is just the floor
    COND = ("auroc", "m095", "m10", "pauc05", "pauc10")
    X = np.array([[q[k] for k in ("floor",) + COND] for q in packs["replay10"]])
    resid_z: dict[str, tuple[float, float, float]] = {}
    for i, k in enumerate(COND, 1):
        r = float(np.corrcoef(X[:, 0], X[:, i])[0, 1]) if R > 2 else float("nan")
        coef = np.polyfit(X[:, 0], X[:, i], 1) if R > 2 else np.array([0.0, X[0, i]])
        pred = float(np.polyval(coef, point["direct10"]["floor"]))
        res = X[:, i] - np.polyval(coef, X[:, 0])
        sd = res.std(ddof=1) if R > 2 else float("nan")
        resid_z[k] = (r, pred, (point["direct10"][k] - pred) / sd if sd else float("nan"))
    F["max_resid_z"] = max(abs(resid_z[k][2]) for k in ("m095", "m10", "pauc05", "pauc10"))

    # the one count that carries the whole step, on the negatives
    _m = mech["correct"]
    F["cap_obs"] = float((_m["k_direct"] >= 10).sum())
    F["cap_exp"] = float(_m["p_all"].sum())
    _pmf = poisson_binomial_pmf(_m["p_all"])
    F["cap_p_lo"] = float(_pmf[:int(F["cap_obs"]) + 1].sum())
    # The honest interval on the step, against one built from the replicate spread alone.
    # `_lo/_hi` come from the MATCHED bootstrap: the step compares two subset-averaged /
    # single-measurement floors, so its interval may not re-add the subset draw either.
    _sd = reps_floor.std(ddof=1) if R > 1 else float("nan")
    _step = matched_diff("direct10", "replay10")
    F["step_floor_matched"] = _step.point
    F["ci_halfwidth"] = (_step.hi - _step.lo) / 2.0
    F["rep_halfwidth"] = 1.959963985 * _sd
    F["ci_width_ratio"] = F["ci_halfwidth"] / F["rep_halfwidth"] if _sd else float("nan")
    F["step_lo"], F["step_hi"] = _step.lo, _step.hi

    for _line in _PROVENANCE.split("\n"):
        log(_line)
    log("")
    log("# The replay control: what the subsetting does, and what survives without it")
    log("")
    log(f"Generated {args.generated} by `scripts/replay_control.py`. CPU-only:")
    log("no model is loaded and no GPU is touched. Every score below is replayed from the")
    log("recorded pairwise verdicts through `se.entropy.cluster_and_score` via the replay")
    log("machinery imported from `scripts/n_scaling_grid.py`, so replayed numbers here are")
    log("bit-identical to that report's.")
    log("")
    log("**The question.** `results/n_scaling_grid.md` compares budgets across two sources:")
    log(f"N=10 is the direct Week-4 cache, N=20 and N={top} come from the N={top} checkpoint. One")
    log("claim already died on that mismatch. A second one -- *AUROC 0.704 -> 0.746, so the")
    log("budget makes it a better ranker* -- rests on the same step. This file measures the")
    log("step, explains it, and then redoes the comparison with the step removed.")
    log("")
    log("**The three answers, up front.**")
    log("")
    log("1. The published control's evidence for a bias is not evidence. It read 20 subset")
    log("   draws landing above the direct point estimate as a sign test at 2^-20. The")
    log("   replicates are not coin flips around the direct value: they are draws from a")
    log(f"   distribution whose centre is elsewhere. Over {R} draws, {int(F['n_below'])}/{R} "
        f"({F['frac_below']:.1%}) fall BELOW")
    log(f"   the direct floor, so \"20 of 20 above\" has probability {F['p_unanimous']:.2f} even treating")
    log("   the draws as independent -- which they are not, and the dependence pushes it")
    log("   higher still.")
    log("2. Every apparent bias in that table is one difference wearing four hats: the")
    log(f"   direct cache has {int(F['cap_obs'])} clean answers at the ln 10 cap where the replay predicts")
    log(f"   {F['cap_exp']:.1f}. Condition on the floor and the TPR and pAUC gaps vanish (residual")
    log(f"   |z| <= {F['max_resid_z']:.2f}). The one count that carries it all is not significant: exact")
    log(f"   Poisson-binomial p = {F['cap_p_lo']:.3f} one-sided, and the whole cluster-count")
    log("   distribution passes a goodness-of-fit test.")
    log("3. Like-for-like, **neither blocked claim survives in the form it was written --")
    log("   and neither does its mirror image.** The AUROC gain shrinks from "
        f"+{F['gain_direct']:.3f} to")
    log(f"   +{F['gain_ll']:.3f} [{F['gain_ll_lo']:+.3f}, {F['gain_ll_hi']:+.3f}], an interval "
        "that covers zero. The claimed FALL in the")
    log("   low-FPR pAUC is unsupported, and so is any restatement of it as a rise --")
    log("")
    wrap(PAUC10_LL, "   > ")
    log("")
    log("   The blocked sentence, quoted in full in section 4, measures which cache the")
    log("   N=10 row came from and not what the budget did. That refutes it. It does not")
    log("   entitle anyone to assert the opposite.")
    log("")
    log("---")
    log("")

    # ------------------------------------------------------------------------ section 1
    log("## 1. The replay-vs-direct step, characterised")
    log("")
    log(f"{R} independent 10-subset draws of the N={top} run, against the one direct Week-4")
    log("N=10 measurement, on the identical 200 correct + 200 hallucinating fair-pool")
    log("targets (id match verified at load; the run aborts otherwise).")
    log("")
    log("| statistic | direct N=10 | replay N=10: mean | sd over draws | range | step (replay - direct) | paired 95% |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    for k in ("floor", "auroc", "pauc05", "pauc10", "m095", "m10", "m20"):
        m, sd, lo, hi = spread("replay10", k)
        if k == "floor":
            # the subset-averaged point and its matched interval, so this row agrees with
            # section 2b instead of quoting a coarser replicate average beside it
            m = matched["replay10"].point
            _qd = matched_diff("direct10", "replay10")
            d, dlo, dhi = _qd.point, _qd.lo, _qd.hi
            dv = matched["direct10"].point
        else:
            d, dlo, dhi = diff_ci("direct10", "replay10", k)
            dv = point["direct10"][k]
        pct = k in ("floor", "m095", "m10", "m20")
        fmt = (lambda v: f"{v:.1%}") if pct else (lambda v: f"{v:.4f}")
        dfm = (lambda v: f"{v * 100:+.1f} pts") if pct else (lambda v: f"{v:+.4f}")
        label = LABEL[k] + (" -- MATCHED, see 2b" if k == "floor" else "")
        log(f"| {label} | {fmt(dv)} | {fmt(m)} | {fmt(sd)} | {fmt(lo)}-{fmt(hi)} | "
            f"{dfm(d)} | [{dfm(dlo)}, {dfm(dhi)}] |")
    log("")
    log("The `sd over draws` and `range` columns are the SUBSET DRAW alone, with the")
    log("questions held fixed; they are a description of the replay, not an uncertainty on")
    log("anything, and section 2b is where they are accounted for properly. On the floor")
    log("row the mean, the step and the 95% are the matched ones; on every other row the")
    log("95% is the both-components bootstrap and so is wider than the point estimate")
    log("beside it deserves.")
    log("")
    log("**Sign and magnitude of the POINT ESTIMATES -- no step here is quotable as a")
    log("difference.** The replay's point estimate reads higher than the direct cache on the")
    log(f"floor ({F['step_floor'] * 100:+.1f} points, {F['step_floor_rel']:+.0%} relative) and on "
        f"AUROC ({F['step_auroc']:+.3f}), and lower on")
    log("everything that prices detection near the operating region: TPR at a matched 9.5%")
    log(f"false-alarm rate ({F['step_m095'] * 100:+.1f} points) and partial AUROC below 10% "
        f"({F['step_pauc10']:+.3f}). Every")
    log("one of those intervals covers zero, so the signs in this paragraph describe the")
    log("point estimates only and no step here may be quoted as a direction. On the")
    log("non-floor rows that is a refusal to claim and not a demonstration of absence:")
    log("those intervals are too wide for their own point estimates, so their covering")
    log("zero is uninformative in the direction of a null. What the")
    log("magnitudes do establish is a bound on relevance rather than an effect: none of")
    log("them is a small effect on the scale of")
    log("the claims they would be used to license -- the TPR step alone is larger than the")
    log("entire budget effect that was proposed as a finding.")
    log("")
    log("**Why the published sign test is the wrong test.** The control in")
    log("`results/n_scaling_grid.md` drew 20 replicates, found all 20 above 9.5%, and that")
    log("was read as 2^-20 evidence of bias. The null behind that arithmetic is \"each")
    log("replicate is independently above or below the direct value with probability 1/2\",")
    log("which is true only if the replicate distribution is CENTRED on the direct value.")
    log("It is not centred there, and it does not have to be: the direct value is one draw")
    log("of a 10-sample run, and the replicate distribution is centred on the conditional")
    log(f"mean given the N={top} draw. Measured over {R} replicates:")
    log("")
    log("| statistic | direct | percentile of the direct value in the replicate distribution | P(20 of 20 on one side), if independent |")
    log("| --- | --- | --- | --- |")
    for k in ("floor", "auroc", "m095", "pauc10"):
        v = np.array([q[k] for q in packs["replay10"]])
        d = point["direct10"][k]
        below = float((v < d).mean())
        one_side = max(below, 1 - below)
        fmt = (lambda x: f"{x:.1%}") if k in ("floor", "m095") else (lambda x: f"{x:.4f}")
        log(f"| {LABEL[k]} | {fmt(d)} | {below:.1%} of draws below | {one_side ** 20:.3f} |")
    log("")
    log("So the observation that licensed the sentence \"if those disagree beyond the Wilson")
    log(f"interval, the subsetting is unsound\" has probability {F['p_unanimous']:.2f} under the replay's")
    log("own distribution. Two further reasons the sign test cannot be rescued: the")
    log(f"replicates share one {top}-sample realisation per question and one set of 200")
    log("questions, so they are positively correlated, which pushes the probability of a")
    log("unanimous run UP and not down; and the replicate spread is ONE component of the")
    log("uncertainty on the floor, not an uncertainty on the STEP, which also carries the")
    log("direct arm's own sampling noise and the draw of the 200 questions. The honest")
    log(f"interval on the step is the matched paired one of section 2b: {F['step_floor_matched'] * 100:+.1f} points")
    log(f"[{F['step_lo'] * 100:+.1f}, {F['step_hi'] * 100:+.1f}], i.e. +/-{F['ci_halfwidth'] * 100:.1f}, against "
        f"+/-{F['rep_halfwidth'] * 100:.1f} points from the replicate")
    log(f"spread alone -- {F['ci_width_ratio']:.1f}x. Those two half-widths are close, and the coincidence is")
    log("worth naming: they are not the same quantity, they are two different quantities")
    log("that happen to come out the same size on this data. Width is not the argument.")
    log("")

    # ------------------------------------------------------------------------ section 2
    log("## 2. The like-for-like budget comparison")
    log("")
    log(f"All three budgets from the one N={top} checkpoint. N=10 and N=20 are means over {R}")
    log(f"subset draws; N={top} is the single realisation there is. The direct row is shown for")
    log("contrast only -- it is the row that must not be mixed into a trend.")
    log("")
    log("**Two kinds of interval in this table, and the difference is not cosmetic.**")
    log("")
    log(f"- The FLOOR row takes the matched interval of section 2b: a question bootstrap")
    log(f"  ({args.boot_matched} resamples) and nothing else, because the point estimate beside it has the")
    log("  subset draw averaged out. An interval for it may not re-add that component.")
    log(f"- Every OTHER row takes the older paired bootstrap ({args.boot} resamples) that resamples")
    log("  the 200+200 targets AND redraws the subset. Those cells therefore carry the")
    log("  subset-draw component twice -- once inside the target resample, which already")
    log("  contains it, and once more from the redraw -- so they are TOO WIDE for the")
    log("  subset-averaged point estimates printed beside them. They are left that way")
    log("  because every one of them is quarantined and no claim rests on them; but see")
    log("  the warning under the differences table before reading any of them as a null.")
    log("")
    log("**QUARANTINE, restated at the table because this is where it gets breached.** The")
    log("AUROC, pAUC and TPR rows below are the two BLOCKED claims recomputed like-for-like")
    log("in order to refute them. Every one of their cross-budget intervals covers zero. The")
    log("floor row is the only quotable trend here; the rest is not liftable in either")
    log("direction, and the adjacent-column hazard is real -- see the banner at the top.")
    log("")
    hdr = "| statistic | direct N=10 (do not mix) | replay N=10 | replay N=20 | "
    log(hdr + f"measured N={top} |")
    log("| --- | --- | --- | --- | --- |")
    for k in ("floor", "auroc", "pauc05", "pauc10", "pauc20", "pauc2050", "pauc50",
              "m05", "m095", "m10", "m20", "ach05", "det05", "ach10", "det10",
              "ach20", "det20"):
        fmt = (lambda v: f"{v:.3f}") if (k == "auroc" or k.startswith("pauc"))             else (lambda v: f"{v:.1%}")
        cells = []
        for nm in NAMES:
            if k == "floor":
                q = matched[nm]                     # built by `quote()`, estimand-checked
                if nm == meas:
                    # No interval, by the ruling in section 2c. Both candidates were
                    # withdrawn on measured coverage; printing either here is what put
                    # this file and the paper on opposite sides of the same question.
                    cells.append(f"{fmt(q.point)} (no interval -- see 2c)")
                else:
                    cells.append(f"{fmt(q.point)} [{fmt(q.lo)}, {fmt(q.hi)}]")
                continue
            lo, hi = ci(boot[nm][k])
            cells.append(f"{fmt(point[nm][k])} [{fmt(lo)}, {fmt(hi)}]")
        label = LABEL[k] + (" -- MATCHED, see 2b" if k == "floor" else "")
        log(f"| {label} | " + " | ".join(cells) + " |")
    log("")
    log("**The paired differences that matter.**")
    log("")
    log("| comparison | statistic | difference | 95% | verdict |")
    log("| --- | --- | --- | --- | --- |")
    for a, b in (("replay10", "replay20"), ("replay20", meas), ("replay10", meas),
                 ("direct10", meas)):
        for k in ("floor", "auroc", "pauc10", "m095", "m10"):
            if k == "floor":
                _qd = matched_diff(a, b)
                d, lo, hi = _qd.point, _qd.lo, _qd.hi
            else:
                d, lo, hi = diff_ci(a, b, k)
            pct = k in ("m095", "m10", "floor")
            fmt = (lambda v: f"{v * 100:+.1f} pts") if pct else (lambda v: f"{v:+.4f}")
            verdict = "excludes zero" if (lo > 0 or hi < 0) else "covers zero"
            label = LABEL[k] + (" -- MATCHED" if k == "floor" else "")
            # MC-ERROR MARK (2026-08-19). The floor legs here are a 40,000-draw Monte Carlo
            # over subsets; `scripts/make_floor_budget_figure.py` computes the same legs
            # EXACTLY, by counting independent sets of the verdict graph. On the 10 -> 20 leg
            # the two disagree in the first decimal -- this file prints -8.8, the exact value
            # is -8.8630, i.e. -8.9 -- and the paper quotes the exact one. An unmarked -8.8
            # sitting in a table is how a reader "corrects" the paper's 8.9 downward, which
            # has been attempted once. So the rows the exact computation covers say which
            # number is theirs and which is the artifact of sampling.
            verdict += EXACT_FLOOR_LEG.get((a, b), "") if k == "floor" else ""
            log(f"| {a} -> {b} | {label} | {fmt(d)} | [{fmt(lo)}, {fmt(hi)}] | {verdict} |")
    log("")
    log("**Read the non-floor rows as no-claims, not as nulls.** Their intervals are the")
    log("both-components bootstrap described above, which is too wide for the point")
    log("estimate beside it. An interval that is too wide cannot manufacture an effect,")
    log("but it CAN manufacture a null, and \"the interval covers zero\" is exactly the")
    log("inference this project has been burned by. So the quarantined rows license")
    log("nothing in either direction -- neither the blocked claims nor their negations --")
    log("and re-deriving them matched, the way the floor row now is, is owed work. The")
    log("floor row is the only row in this table whose interval belongs to the estimator")
    log("printed beside it.")
    log("")
    a10 = np.array([q["auroc"] for q in packs["replay10"]])
    a40 = point[meas]["auroc"]
    log("**Does the AUROC gain survive?** No, not as a claim.")
    log("")
    log(f"- claimed, across the provenance step: {point['direct10']['auroc']:.3f} -> {a40:.3f} "
        f"= **+{F['gain_direct']:.3f}**")
    log(f"- like-for-like, replay N=10 -> measured N={top}: {point['replay10']['auroc']:.3f} -> "
        f"{a40:.3f} = **+{F['gain_ll']:.3f}** "
        f"[{F['gain_ll_lo']:+.3f}, {F['gain_ll_hi']:+.3f}]")
    log(f"- so **{F['share_source']:.0%} of the advertised gain is the change of source**, not the")
    log("  change of budget.")
    log("- the residue is not separable from zero on 200 questions: the paired interval")
    log(f"  covers it, and the only comparison in this report that DOES clear zero "
        f"(+{F['gain_direct']:.3f})")
    log("  is the confounded one, where the provenance step and the budget effect happen")
    log("  to add.")
    log("")
    log("The N=10 replay and the N=40 run are nested -- same questions, same generations,")
    log("the smaller budget is literally a subset of the larger -- so the paired comparison")
    log("is as favourable as a design can be to detecting a real budget effect. It still")
    log("covers zero.")
    log("")
    log("**Be precise about what that means.** This is an underpowered comparison, not a")
    log("demonstration that the budget does nothing. Holding the 200 questions and their")
    log(f"generations fixed and varying only the subset draw, the {top}-sample budget has the")
    log(f"larger AUROC in the large majority of draws -- {R - int(F['n_ties_40'])} of {R} under "
        "this script's")
    log("subset RNG, but that count is NOT a stable statistic and must not be quoted as one:")
    log("the")
    log("2026-08-19 gate reimplemented the same replay independently and got 190/200 from a")
    log("replay-10 AUROC mean 0.003 higher (`results/gate_paper_edits_2026_08_19.md` A1),")
    log("so it is seed- and implementation-sensitive at about +/-7. Consistency of the point")
    log("estimates across draws is not evidence of a detectable effect in any case: it holds")
    log("the sample draw fixed, which is the variance component that matters. What the")
    log(f"interval says is that 200 questions cannot separate +{F['gain_ll']:.3f} from zero -- and a")
    log("paper claim needs the interval, because it is a claim about the detector and not")
    log("about these 200 questions. The right sentence is \"rises by a fraction of the")
    log("advertised amount, and not distinguishable from flat at this sample size\"; the")
    log("wrong ones are \"makes it a better ranker\" and \"is flat\".")
    log("")
    log("**What DOES survive like-for-like** is the granularity result, which is what the")
    log("paper actually needs:")
    log("")
    # THE TWO SENTENCES A READER LIFTS FROM. Until 2026-08-19 this line and its twin in
    # section 6 were built from `point[nm]["floor"]` -- the average over 200 whole
    # replicates -- and from `diff_ci(..., "floor")` -- the bootstrap that redraws the
    # subset on top of resampling the targets. Both are the objects section 2b superseded,
    # and neither passes through `quote()`, so the estimand/interval guard added earlier
    # that same night never saw them. The file went on printing "11.9% -> 3.0% -> 2.0%"
    # and "-9.9 points [-15.5, -5.0]" under a heading that says "what is worth carrying
    # instead", and three separate briefings carried the retired fall. They now take the
    # matched objects, through constructors that will not accept a float.
    trend = floor_trend(matched["replay10"], matched["replay20"], matched[meas])
    mfall = matched_diff("replay10", meas)
    if not mfall.excludes_zero():
        raise ValueError(
            f"the matched floor fall {mfall.pts()} no longer clears zero, so the sentence "
            f"below may not assert a direction. Rewrite it -- do not reprint it.")
    log(f"- the floor falls {trend} on one source, and the")
    log(f"  N=10 -> N={top} difference clears zero by a wide margin ({mfall.pts('points')});")
    log(f"  the N=20 -> N={top} step on its own does not;")
    log("- a 5% false-alarm budget is unbuyable at N=10 (deterministic rule flags nothing)")
    log(f"  and buyable at N={top};")
    log("- **what that operating point is worth in true positives is NOT reportable from")
    log("  this file, in either direction.** The cross-budget TPR comparison at a matched 5%")
    log("  false-alarm rate was BLOCKED by an earlier gate and stays blocked, because the")
    log("  comparison is not well posed. Its MAGNITUDE turns on which decision rule is")
    log("  paired and its SIGN turns on which N=10 cache is paired:")
    log(f"    - deterministic rule against deterministic rule: {point['replay10']['det05']:.1%} "
        f"at replay N=10 against")
    log(f"      {point[meas]['det05']:.1%} at N={top} -- a large apparent gain, but only because at "
        "N=10 no")
    log("      threshold honours a 5% budget at all, which is the granularity result again")
    log("      and not a discrimination result;")
    log(f"    - randomised frontier against randomised frontier, replayed N=10: "
        f"{point['replay10']['m05']:.1%} against")
    log(f"      {point[meas]['m05']:.1%} -- same direction, trivial size;")
    log(f"    - randomised frontier against randomised frontier, DIRECT N=10: "
        f"{point['direct10']['m05']:.1%} against")
    log(f"      {point[meas]['m05']:.1%} -- the OPPOSITE sign. This pairing crosses the "
        "provenance step, which")
    log("      this report's own rule forbids; it is shown to demonstrate that the sign of")
    log("      the comparison is not robust, not to be used.")
    log("  No pairing has an interval that separates the budgets: the neighbouring")
    log(f"  matched-9.5% difference is {diff_ci('replay10', meas, 'm095')[0] * 100:+.1f} pts "
        f"[{diff_ci('replay10', meas, 'm095')[1] * 100:+.1f}, "
        f"{diff_ci('replay10', meas, 'm095')[2] * 100:+.1f}], which covers zero. The cells are in")
    log("  the section 2 table under the quarantine named in the banner at the top of this")
    log("  file. The granularity result above does not need them, and neither \"the budget")
    log("  buys little\" nor \"the budget buys a lot\" follows from them.")
    log("")

    # ----------------------------------------------------------------------- section 2b
    log("## 2b. The floor, and the interval that belongs to it")
    log("")
    log("**This section replaces an argument that was wrong.** The previous version of")
    log("this report quoted the subset-averaged replayed floor and attached to it an")
    log("interval from the both-components bootstrap, on the stated grounds that a")
    log("single-replicate Wilson interval would be \"too narrow\" because it omits the")
    log("subset draw. It does not omit it. The correction is arithmetic, and it is here in")
    log("full so that nobody has to take it on trust.")
    log("")
    log("**The identity.** Let p_i be question i's probability that a uniformly random")
    log("k-subset of its recorded 40 samples comes out all-singletons -- i.e. that the")
    log("subset is an independent set of that question's equivalence graph, which is")
    log("exactly the event that its replayed score hits the ln k cap. A single replicate")
    log("draws one subset per question, so the floor it reports is a mean of n independent")
    log("indicators X_i with P(X_i = 1) = p_i, and")
    log("")
    log("```")
    log("    mean_i p_i(1-p_i)   +   var_i(p_i)      =   pbar(1-pbar)")
    log(r"    \___ subset draw __/     \_ questions _/      \_ the binomial/Wilson SE _/")
    log("```")
    log("")
    log("identically, for any set of p_i. The subset-draw component is ALREADY INSIDE the")
    log("Wilson interval a single replicate would report. It cannot be added a second")
    log("time. And the floor this report quotes is not a single replicate at all: it is")
    log("the subset-AVERAGED floor, from which that component has been averaged away, so")
    log("its interval must contain only the question component.")
    log("")
    log(f"Evaluated on the {NPS} correct answers of the fair pool, {args.sat_mc} subset draws per")
    log("question (standard deviations in rate points, on the floor at that budget):")
    log("")
    log("| budget | pbar (subset-averaged floor) | question component | subset-draw component | root-sum-square | sqrt(pbar(1-pbar)/n) | identity residual |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    for b in sorted(split):
        d = split[b]
        log(f"| N={b} | {d['pbar']:.3%} | {d['sd_questions'] * 100:.4f} | "
            f"{d['sd_subset'] * 100:.4f} | {d['sd_rss'] * 100:.4f} | "
            f"{d['sd_binomial'] * 100:.4f} | {d['residual']:.1e} |")
    log("")
    log("The last two columns agree to the width of a rounding error, which is the")
    log("identity, not a coincidence -- and it is the whole of the correction. Reading the")
    log("row for N=20: of the single-replicate floor's total spread, the subset draw")
    log("supplies the larger share and the draw of questions the smaller, and Wilson on")
    log("that single replicate already reports their sum.")
    log("")
    log("**Which interval goes with which estimator.** Three different numbers, three")
    log("different intervals, and they are not interchangeable:")
    log("")
    log("| estimator | what varies | the interval it takes |")
    log("| --- | --- | --- |")
    log("| one replicate's replayed floor | the questions AND that one subset draw | Wilson on the count -- which is already both components |")
    log("| the subset-averaged replayed floor (**what this report and the paper quote**) | the questions only | a bootstrap over questions only |")
    log(f"| the measured N={top} floor | the questions only, but the ESTIMAND moves with them | **none -- both candidates withdrawn, see 2c.** The question bootstrap is still the interval for PAIRED differences, which are a different estimand |")
    log("")
    log("The middle row is the one that was got wrong. Note also that the two replayed")
    log("intervals are honest about different things and are NOT nested claims: a")
    log("single-replicate Wilson interval is correct for a number nobody quotes. The last")
    log("row said \"Wilson on the count\" until 2026-08-19 and was the last statement of the")
    log("withdrawn position left in this file. "
        "`audit_estimator_table_agrees_with_the_floor_table`")
    log("now requires this cell, the floor table below, and the section 2 floor row to")
    log("state the same position, so the three cannot drift apart again.")
    log("")
    log("**The floor, quoted correctly.**")
    log("")
    log("| budget | floor | 95%, questions only | how | the interval previously printed here | Monte-Carlo error on the point |")
    log("| --- | --- | --- | --- | --- | --- |")
    for nm, lbl in (("direct10", "direct N=10 (do not mix)"), ("replay10", "replay N=10"),
                    ("replay20", "replay N=20"), (meas, f"measured N={top}")):
        q = matched[nm]
        olo, ohi = ci(boot[nm]["floor"])
        b = int(nm.replace("replay", "")) if nm.startswith("replay") else None
        mcs = f"+/-{sat_mc_sd[b] * 100:.3f} pts" if b in sat_mc_sd else "none -- a count"
        how = ("question bootstrap" if nm.startswith("replay")
               else f"Wilson on {int(round(q.point * NPS))}/{NPS}")
        if nm == meas:
            k40 = int(round(q.point * NPS))
            _wp, wlo, whi = wilson(k40, NPS)
            log(f"| {lbl} | {q.point:.1%} | **none -- withdrawn, see 2c** | "
                f"Wilson on {k40}/{NPS} would give [{wlo:.1%}, {whi:.1%}]; "
                f"the question bootstrap would give [{olo:.1%}, {ohi:.1%}]; "
                f"neither is quotable | [{olo:.1%}, {ohi:.1%}] | {mcs} |")
        else:
            log(f"| {lbl} | {q.point:.1%} | [{q.lo:.1%}, {q.hi:.1%}] | {how} | "
                f"[{olo:.1%}, {ohi:.1%}] | {mcs} |")
    log("")
    log("The replayed point estimates moved as well as the intervals, and by less than")
    log("they look: they are now the mean of the per-question probabilities rather than an")
    log(f"average over {R} whole replicates, whose own Monte-Carlo error was about ten times")
    log("larger and straddled the first decimal place. The internal check is that the")
    log("replayed N=10 floor and the expected at-cap count of section 3 are the same")
    log(f"quantity: {matched['replay10'].point * 100:.2f}% against "
        f"{100 * F['cap_exp'] / NPS:.2f}%, computed by two independent Monte-Carlos.")
    log("")
    log(f"The bootstrap runs {args.boot_matched} resamples, which is more than it looks like it")
    log("needs. A percentile is itself a Monte-Carlo estimate: at 20,000 resamples the")
    log("N=10 lower endpoint moved 0.13 points across resample seeds, which is larger than")
    log("the decimal place the paper prints, and a number that moves while you read it is")
    log("the thing this project keeps getting caught by. At the count above the endpoints")
    log("are stable to about 0.01 points across seeds.")
    log("")
    log("### 2c. The measured N=40 floor has NO interval, and the achieved-FPR brackets")
    log("### are not confidence intervals")
    log("")
    log("Settled by coverage simulation in `results/n40_floor_estimator_ruling.md`")
    log("(2026-08-19): 40,000 simulated pools of 200 per cell, three seeds, against a")
    log("population model fitted at N=40 and validated OUT OF SAMPLE on the two ceiling")
    log("atoms this report measures (it predicts the N=10 atom at 11.86% against a")
    log("measured 12.00%, having been tuned only on N=20).")
    log("")
    log("EVERY NUMBER IN THE TABLE BELOW IS MODEL-DEPENDENT, including the column headed")
    log("\"true floor\": there is no measurement of a population floor anywhere in this")
    log("project. The model is the one named in the paragraph above -- fitted at N=40,")
    log("tuned on N=20, validated out of sample on the N=10 atom -- and it is specified")
    log("in `results/n40_floor_estimator_ruling.md` and nowhere else. The coverages are")
    log("frequencies over 40,000 pools simulated FROM that model, three seeds. Read them")
    log("as properties of the model, not as measurements of this pool.")
    log("")
    log("| budget | true floor (MODEL) | Wilson coverage (MODEL) | question-bootstrap coverage (MODEL) |")
    log("| --- | --- | --- | --- |")
    log("| N=10 (atom full) | 11.86% | 95.1% | 94.9% |")
    log("| N=20 (atom full) | 3.13% | 96.2% | 98.4% |")
    log("| **N=40 (atom EMPTY)** | **0.27%** | **53.7%** | **0.00%** |")
    log("")
    log("**The three significant figures are the model's, not a measurement's, and the")
    log("N=40 row is the one to distrust the precision of.** A verifier reduced the 53.7%")
    log("to an identity: under this model Wilson on a count of 2 has a lower endpoint")
    log("0.0012 points ABOVE the asserted true floor of 0.2735% (0.2747 against 0.2735),")
    log("and the floor count is at least 1 by construction -- the floor IS the smallest")
    log("non-zero achievable rate -- so a pool covers the floor exactly when its floor")
    log("count is 1, and 53.7% is P(floor count = 1) and nothing else. Move the model's")
    log("floor by a thousandth of a point and that figure steps to a different value; it")
    log("does not degrade gracefully. The bootstrap's 0.00%")
    log("is robust for the opposite reason -- its lower endpoint is 1/200 = 0.5% by")
    log("construction, which exceeds any plausible true floor at this budget, so it misses")
    log("for a structural reason and not a numerical one.")
    log("")
    log("WHAT THE PRECISION DOES NOT TOUCH IS THE RULING. Both candidates fail and the")
    log("estimand dissolves when the ceiling atom empties: that follows from the estimator")
    log("being an extreme order statistic whose target moves with the pool, and it is")
    log("argued below without reference to any coverage figure. A reader who rejects the")
    log("model should reject the 53.7%, keep the withdrawal, and quote the point alone.")
    log("")
    log("Neither estimator is broken. THE ESTIMAND BREAKS, and it breaks exactly when the")
    log("ceiling atom empties. While the atom carries mass the floor is a fixed population")
    log("proportion at a fixed threshold and both methods price it. Once it empties, the")
    log("floor is the multiplicity of whichever rung THIS pool happened to reach -- a pool")
    log("of 200 reaches the population's true top rung only 42% of the time, and the")
    log("statistic falls like c/m as the pool grows, so an m-out-of-n bootstrap cannot")
    log("repair it either: the target moves with the resizing.")
    log("")
    log("Each candidate also has an endpoint placed by construction. The bootstrap's lower")
    log("end is 0.5% because the estimator cannot return less than 1/200; it exceeds the")
    log("true floor in 100.00% of simulated pools. Wilson's upper end counts a rung the")
    log("population may not have. So this report quotes the point, 2.0%, and no interval.")
    log("")
    log("The row that DOES carry an interval at N=40 is the at-cap mass, 0/200, Wilson")
    log("[0.0%, 1.9%]: its threshold is ln 40, fixed before the data, and its one-sided")
    log("upper bound has 100% coverage across the whole plausible range. That is also the")
    log("quantity `results/n_scaling_plan.md` pre-registered its 5% criterion on.")
    log("")
    log("**The opposite ruling for the achieved-FPR-at-budget rows, for a stated reason.**")
    log("Those take Wilson, not the bootstrap: measured coverage is 94.4% against 54.8%,")
    log("and the bootstrap's upper endpoint sits exactly at the budget in 100.00% of")
    log("pools. The floor is an EXTREME ORDER STATISTIC at the edge of the support; the")
    log("achieved point is an INTERIOR quantile with ~10 answers above the threshold and")
    log("~190 below. Data selection is not what breaks Wilson -- being at the boundary of")
    log("the support is. The `ach*` brackets in the table above are therefore labelled as")
    log("estimator ranges, and the paper quotes Wilson on the count: 10/200 = 5.0%")
    log("[2.7%, 9.0%].")
    log("")
    log("**A second-decimal disagreement with the paper, recorded rather than resolved.**")
    log("The per-question saturation probabilities here are a Monte Carlo over random")
    log(f"subsets ({args.sat_mc} draws per question). `scripts/make_floor_budget_figure.py`")
    log("computes the same quantities EXACTLY -- 'all singletons' is 'the subset is an")
    log("independent set of the verdict graph', so the probability is a ratio of")
    log(f"independent-set counts and needs no sampling. Exact: N=10 floor "
        f"{EXACT_FLOOR_PCT[10]:.4f}%, N=20")
    log(f"floor {EXACT_FLOOR_PCT[20]:.4f}%, and a 10 -> 20 paired leg of "
        f"{EXACT_LEG_10_20_PTS:.4f}, which is {EXACT_LEG_10_20_PTS:.1f} at one decimal.")
    log("This report's Monte Carlo gives -8.8. THE EXACT VALUE IS THE RIGHT ONE and the")
    log("paper's 8.9 is correct; the figure and its sidecars now carry the exact numbers.")
    log("Do not 'correct' the paper down to 8.8 to match this file -- that has been")
    log("attempted once, on the strength of this file and the figure agreeing while both")
    log("were reading the same Monte-Carlo error.")
    log("")
    log("**Two caveats on the construction, neither of which changes the numbers.**")
    log("")
    log("1. The subset-averaged floor is treated as the mean of the p_i, which assumes")
    log("   some negative reaches the cap so that the floor IS the ceiling atom. The")
    log("   probability that none does is")
    log("   " + ", ".join(f"{v:.1e} at N={b}" for b, v in sorted(p_no_atom.items())) + ",")
    log(f"   so the approximation is worth well under 0.01 points. At N={top} it fails")
    log("   completely -- no negative reaches ln 40 -- which is why that row is a")
    log("   bootstrap over the scores themselves, re-finding the top score in every")
    log("   resample, and not a mean of indicators.")
    log("2. The question bootstrap is the right interval for the population quantity and")
    log("   not merely a narrower one. Each question's 40 generations are drawn")
    log("   independently of every other question's, so p_i is an i.i.d. draw from the")
    log("   marginal distribution of \"this question's saturation probability\" -- the")
    log("   generation noise is inside the between-question spread, not missing from it.")
    log("   What no interval here covers is a second draw of the 40 samples for a FIXED")
    log("   question, which no estimator in this report is conditioning away.")
    log("")

    # ------------------------------------------------------------------------ section 3
    log("## 3. Where a step could come from -- and where this one comes from")
    log("")
    log("**The estimator is exactly unbiased, and that is a theorem, not a hope.** The 40")
    log("samples for a question are i.i.d. draws, hence exchangeable. A uniformly random")
    log("10-subset of an exchangeable 40-tuple has exactly the distribution of 10 i.i.d.")
    log("draws. The clusterer is union-find over PAIRWISE verdicts, so the clustering of a")
    log("subset depends only on the verdicts inside it and is exactly what a direct 10-run")
    log("with those samples would have produced. Therefore, for every question i,")
    log("E[replayed score] = E[direct score], and the floor -- a mean of indicators -- is")
    log("unbiased term by term. Nothing about reusing one verdict matrix changes this: the")
    log("expectation is over the subset draw AND the sample draw, and both are honest.")
    log("")
    log("**What reusing one matrix DOES do is destroy the independence of replicates.**")
    log("Every replicate conditions on the same 40 samples and the same 200 questions, so")
    log("the spread ACROSS replicates is subset-draw noise around a conditional mean. That")
    log("is the actual defect in the published control's sign test: its null treats the")
    log("replicates as independent coin flips about the direct value, and they are neither")
    log("independent nor centred there.")
    log("")
    log("**It is NOT a reason to widen an interval -- and this report previously said")
    log("that it was.** The retracted sentence claimed that a Wilson interval on one replicate")
    log("is \"understated\" because it carries target-sampling variance and not")
    log("subset-choice variance. It carries both, by the identity in section 2b:")
    log(f"mean_i p_i(1-p_i) + var_i(p_i) = pbar(1-pbar), which at N=20 reads")
    log(f"{split[20]['sd_subset'] * 100:.4f}^2 + {split[20]['sd_questions'] * 100:.4f}^2 = "
        f"{split[20]['sd_rss'] * 100:.4f}^2 against a binomial "
        f"{split[20]['sd_binomial'] * 100:.4f}, in rate points.")
    log("A single-replicate Wilson interval is the CORRECT interval for a single-replicate")
    log("floor. What was wrong was quoting it -- or a wider one -- next to the")
    log("subset-averaged floor, which is a different estimator with a smaller variance.")
    log("Section 2b carries the corrected numbers and the estimator each one belongs to.")
    log("")
    log("**So the gap has to be explained by the data, and the data explains it as one")
    log("number.** The four rows of the published control are not four findings:")
    log("")
    log("| statistic | correlation with the floor across subset draws | direct value, predicted from its own floor | observed | residual z |")
    log("| --- | --- | --- | --- | --- |")
    for k in COND:
        r, pred, z = resid_z[k]
        pct = k in ("m095", "m10")
        fmt = (lambda v: f"{v:.1%}") if pct else (lambda v: f"{v:.4f}")
        log(f"| {LABEL[k]} | {r:+.2f} | {fmt(pred)} | {fmt(point['direct10'][k])} | {z:+.2f} |")
    log("")
    log("The TPR and pAUC \"biases\" are not independent of the floor -- they ARE the floor.")
    log("Give the replay the direct cache's floor and it predicts the direct cache's TPR at")
    log(f"a matched rate to within {F['max_resid_z']:.2f} of a standard deviation. The AUROC residual is the")
    log(f"one that does not vanish ({resid_z['auroc'][2]:+.2f} subset-draw sd, i.e. "
        f"{resid_z['auroc'][1] - point['direct10']['auroc']:+.3f} in AUROC units), and")
    log("even that sits inside the paired interval on the AUROC step in section 1.")
    log("(This is a redundancy")
    log("decomposition, not a significance test: the yardstick is the subset-draw spread,")
    log("which omits the direct arm's own sampling noise. The honest interval on each step")
    log("is the paired one in section 1, and all of them cover zero.)")
    log("")
    log("**Is the one number itself out of line?** No.")
    log("")
    for stratum in ("correct", "hallucinating"):
        m = mech[stratum]
        obs = int((m["k_direct"] >= 10).sum())
        pmf = poisson_binomial_pmf(m["p_all"])
        exp = float(m["p_all"].sum())
        sd = float(math.sqrt((m["p_all"] * (1 - m["p_all"])).sum()))
        p_lo = float(pmf[:obs + 1].sum())
        p_hi = float(pmf[obs:].sum())
        mc_sd = float(math.sqrt((m["p_all"] * (1 - m["p_all"])).sum() / args.mc))
        log(f"- **{stratum} stratum:** direct cache has {obs}/200 answers at the ln 10 cap; the")
        log(f"  replay says the expected count is {exp:.1f} (+/-{mc_sd:.2f} Monte-Carlo, sd {sd:.2f} under")
        log("  the exact Poisson-binomial null over the 200 per-question probabilities). "
            f"P(X <= {obs}) = {p_lo:.3f},")
        log(f"  P(X >= {obs}) = {p_hi:.3f}.")
    log("")
    log("And the discrepancy does not extend past that one cell. The full distribution of")
    log("the cluster count at k=10 -- the thing the whole score is a function of -- matches:")
    log("")
    log("| stratum | K=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | chi-square | df | p |")
    log("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    from scipy import stats as _st
    for stratum in ("correct", "hallucinating"):
        m = mech[stratum]
        obs = np.array([int((m["k_direct"] == k).sum()) for k in range(1, 11)], float)
        exp = m["k_hist"].sum(0)[1:]
        # pool the sparse low-K cells forward until every expected count clears 5, so the
        # chi-square reference distribution is the one being quoted
        po, pe = [], []
        acc_o = acc_e = 0.0
        for o, e in zip(obs, exp):
            acc_o += o
            acc_e += e
            if acc_e >= 5.0:
                po.append(acc_o)
                pe.append(acc_e)
                acc_o = acc_e = 0.0
        if acc_e > 0:
            po[-1] += acc_o
            pe[-1] += acc_e
        po, pe = np.array(po), np.array(pe)
        chi = float(np.sum((po - pe) ** 2 / pe))
        dof = len(po) - 1
        pval = float(_st.chi2.sf(chi, dof))
        log(f"| {stratum}, direct | " + " | ".join(f"{int(v)}" for v in obs) +
            f" | {chi:.2f} | {dof} | {pval:.2f} |")
        log(f"| {stratum}, replay expected | " + " | ".join(f"{v:.1f}" for v in exp) + " | | | |")
    log("")
    log("**One provenance difference IS real, and it is not the subsetting.** The two")
    log("sample sets were generated at different times (Week 4 in June, the checkpoint on")
    log("2026-08-13) under an identical config -- same model, 4-bit, T=1.0, top_p=1.0,")
    log("max_new_tokens=48, seed 0 -- and they still differ measurably in the text:")
    log("")
    log(f"- mean answer length: {len_d.mean():.1f} chars direct vs {len_r.mean():.1f} in the checkpoint, "
        f"paired difference **{(len_r - len_d).mean():+.2f} +/- {(len_r - len_d).std(ddof=1) / math.sqrt(len(len_d)):.2f}** "
        f"(z = {(len_r - len_d).mean() / ((len_r - len_d).std(ddof=1) / math.sqrt(len(len_d))):+.1f});")
    log(f"- fraction of answers ending in terminal punctuation (a truncation proxy): "
        f"{end_d.mean():.3f} vs {end_r.mean():.3f}, paired "
        f"{(end_r - end_d).mean():+.4f} +/- {(end_r - end_d).std(ddof=1) / math.sqrt(len(end_d)):.4f};")
    dd = mech["correct"]["dup_d"] - mech["correct"]["dup_r"]
    log(f"- but exact-duplicate rate among 10 answers -- a pure generation statistic with no")
    log(f"  NLI in it -- is indistinguishable: {mech['correct']['dup_d'].mean():.4f} direct vs "
        f"{mech['correct']['dup_r'].mean():.4f} replayed on the correct stratum, paired "
        f"{dd.mean():+.4f} +/- {dd.std(ddof=1) / math.sqrt(len(dd)):.4f}.")
    log("")
    log(f"So the checkpoint's answers run about {(len_r.mean() / len_d.mean() - 1):.0%} longer and are "
        "slightly more often cut off")
    log("at the token cap. That is a genuine run-to-run difference of unknown cause, its")
    log("sign is the right one to nudge the ceiling atom upward (longer, more truncated")
    log("answers entail each other less often), and it is small enough to leave the")
    log("cluster-count distribution statistically indistinguishable.")
    log("")
    log("**Verdict on mechanism.** The bias is not a property of the estimator (unbiased by")
    log("exchangeability), not a property of the finite verdict matrix (which affects the")
    log("correlation between replicates, not their mean), and not a property of the")
    log("subsetting scheme (uniform, independent per question, and it reproduces the whole")
    log("cluster-count marginal). The remaining candidates are (a) sampling noise in the")
    log(f"direct measurement -- {int(F['cap_obs'])} versus {F['cap_exp']:.0f} questions in one tail cell, "
        f"one-sided p = {F['cap_p_lo']:.3f}")
    log("-- and (b) a small real generation-run difference between June and August.")
    log("")
    log("**Neither of those makes one arm the sounder measurement, and an earlier draft of")
    log("this file said it did.** The exchangeability theorem establishes that the replay is")
    log("unbiased for the AUGUST generation run; the direct cache is an unbiased single")
    log("realisation of the JUNE one. The length and truncation diagnostics just above show")
    log("those two runs differ. So the two estimators are not one good and one bad: **they")
    log("estimate different parameters**, and \"which is sounder\" stops being a statistical")
    log("question at that point. They also agree within sampling error on the one cell where")
    log("they differ, so nothing else in the paper is destabilised by the gap.")
    log("")
    log("What follows is a rule, not a ranking: report the budget trend entirely inside the")
    log("replay family and label it as such; keep the direct N=10 row on its June provenance")
    log("wherever the paper already quotes it, since every other N=10 number in the paper --")
    log("and the attack campaign's recorded `entropy_before` -- is welded to that cache; and")
    log("drop the language of bias in either direction. The direct row remains the only row")
    log("in the budget table that cannot be reproduced from the checkpoint, which is a")
    log("statement about reproducibility and not about which number is right.")
    log("")
    log("The clean way to close this is unchanged and cheap: re-measure N=10 directly on the")
    log("current box (about a quarter of the N=40 cost) and the drift component separates")
    log("from the subsetting component by subtraction.")
    log("")

    # ------------------------------------------------------------------------ section 4
    log("## 4. The pAUC question")
    log("")
    log("The blocked claim reads: *AUROC rises 0.704 -> 0.746, but the entire improvement")
    log("lies above 20% false alarms; partial AUROC below 10% is 0.145 at N=10 and 0.126 at")
    log("N=40.* Two things are wrong with it and one thing is right.")
    log("")
    log("**Wrong 1: the fall it cites is the provenance step, not the budget.** Like-for-like")
    log("the claimed fall is not there. What replaces it is not a rise either, and the")
    log("temptation to write one is the whole reason this section exists: the like-for-like")
    log("interval covers zero in both directions, so the correct replacement for a")
    log("directional claim is no directional claim. The bands:")
    log("")
    log("| band | direct N=10 | replay N=10 | replay N=20 | measured N=40 | chance in band |")
    log("| --- | --- | --- | --- | --- | --- |")
    for (lo, hi), k in zip(BANDS, ("pauc05", "pauc10", "pauc20", "pauc2050", "pauc50")):
        cells = " | ".join(f"{point[nm][k]:.3f}" for nm in NAMES)
        log(f"| FPR {lo:.0%}-{hi:.0%} | {cells} | {(lo + hi) / 2:.3f} |")
    log("")
    d10 = point["replay10"]
    d40 = point[meas]
    log(f"Direct -> N={top} on the pAUC below 10% is {F['pauc10_direct_step']:+.4f} -- the claim's "
        "quoted -0.019. Replay")
    log(f"N=10 -> N={top} is {F['pauc10_ll']:+.4f}, a point estimate of the opposite sign and "
        f"{F['pauc10_ratio']:.1f}x smaller,")
    log("carrying an interval about ten times its own size:")
    log("")
    wrap(PAUC10_LL, "> ")
    log("")
    log("So the quoted fall measures which cache the N=10 row came from, and what the budget")
    log("does to the low-FPR pAUC is not resolved by these 200 questions in either")
    log("direction. **The claim is refuted; its negation is not established.**")
    log("")
    log("**Wrong 2: the units are mislabelled in the source document.**")
    log("`results/post_overnight_claim_review.md` heads this table \"standardised partial AUC")
    log("... (0.5 = chance within the band)\". These numbers are the MEAN TPR inside the")
    log("band, for which chance is the band midpoint: 0.05 for FPR <= 10%, not 0.5. So the")
    log(f"direct row's {point['direct10']['pauc10']:.3f} is not a near-catastrophic 0.145-against-0.5, it is "
        f"{point['direct10']['pauc10'] / 0.05:.1f}x")
    log("chance. Any prose built on the mislabel will overstate how bad the operating")
    log("region looks.")
    log("")
    log("**Right: the point-estimate decomposition really does put the gain up top.**")
    log(f"Splitting the like-for-like AUROC gain (replay N=10 -> N={top}, "
        f"+{d40['auroc'] - d10['auroc']:.4f}) into")
    log("contributions by false-alarm band (each band's mean-TPR change times its width;")
    log("the three contributions sum to the AUROC change):")
    log("")
    log("| band | width | replay N=10 | measured N=40 | contribution to the AUROC gain | share |")
    log("| --- | --- | --- | --- | --- | --- |")
    total = d40["auroc"] - d10["auroc"]
    for (lo, hi), k in ((( 0.0, 0.20), "pauc20"), ((0.20, 0.50), "pauc2050"), ((0.50, 1.0), "pauc50")):
        c = (d40[k] - d10[k]) * (hi - lo)
        log(f"| FPR {lo:.0%}-{hi:.0%} | {hi - lo:.2f} | {d10[k]:.3f} | {d40[k]:.3f} | "
            f"{c:+.5f} | {100 * c / total:.0f}% |")
    log("")
    log("**What can honestly be said.** Only this: *no improvement in discrimination is")
    log("detectable in any false-alarm band, and what improvement the point estimates show")
    log("is concentrated above a 20% false-alarm rate.* The gate's objection is correct on its own terms -- overlapping")
    log("intervals mean undetectable, not absent -- but the repair is not to assert absence")
    log("more carefully. It is to notice that, like-for-like, the low-FPR point estimates")
    log("move the SAME way as the overall AUROC and by a trivial amount, so there is no")
    log("longer any tension to explain and no \"where the gain lives\" story to tell. The")
    log("sentence that fits the data is \"not detectably concentrated at low FPR\", and it is")
    log("a weaker sentence than the one the paper wanted.")
    log("")

    # ------------------------------------------------------------------------ section 5
    log("## 5. A defect in `results/n_scaling_grid.md`, and the correct value")
    log("")
    log("Section 1 of that report gives N=40 a \"next FPR\" of 2.5%; section 3's operator")
    log("menu says the closest achievable point to a 1% target is 2.0%. Both cells are")
    log("computing what their own code says, and the report is still wrong, because the")
    log("**floor** column is computing a third thing.")
    log("")
    neg40 = ens[top][0][0]
    fir = sorted(firing_fprs(neg40))[:6]
    log("From the checkpoint, the achievable false-alarm rates at N=40 in ascending order")
    log("are " + ", ".join(f"{v:.1%}" for v in fir) + ", ...")
    log("")
    log("- the smallest false-alarm rate a firing threshold can realise at N=40 is")
    log(f"  **{fir[0]:.1%}** -- {int(round(fir[0] * 200))}/200 answers tied at the top "
        f"score, quoted with no interval (section 2c);")
    log(f"- the next one after it is **{fir[1]:.1%}**, which is what the \"next FPR\" column reports;")
    log("- the floor column reports the CEILING-ATOM mass instead -- the share of negatives")
    log(f"  sitting exactly at ln {top} -- which is {ceiling_atom(neg40, top)}/{len(neg40)} = "
        f"{ceiling_atom(neg40, top) / len(neg40):.1%}, under a header that reads")
    log("  \"floor = min non-zero FPR\".")
    log("")
    log("At N=10 and N=20 the two coincide, because some negative does sit at the cap, and")
    log(f"the column has been read as the floor ever since. At N={top} no negative reaches ln {top}")
    log(f"and they part company. The published row therefore says the N={top} floor is 0.0%")
    log("[0.0%, 1.9%], which invites exactly the wrong inference -- that a sub-1% operating")
    log(f"point might exist at N={top} with more data. It does not: the smallest one that exists")
    log(f"is {fir[0]:.1%}, and 0.0% is the structural zero of the never-fire policy.")
    log("")
    log(f"**The correct value for the N={top} floor is {fir[0]:.1%} "
        f"({int(round(fir[0] * len(neg40)))}/{len(neg40)} negatives, no interval), and the next")
    log(f"achievable rate above it is {fir[1]:.1%}.** Section 2's claim that the `correct` row of the")
    log("ceiling-atom table \"IS the achievable-FPR floor as a function of the sample")
    log("budget\" inherits the same defect: it is the floor only while the atom is non-empty.")
    log("")
    log("**The fix, not applied here** (`scripts/n_scaling_grid.py` is owned by another")
    log("task): in `write_grid_report`, the floor cell should be the first FIRING point,")
    log("`firing[0]['fpr']`, with the ceiling-atom mass reported as its own separate column")
    log("(it is a real and different quantity -- it is what section 2 predicts), and the")
    log("\"next FPR\" column should stay `firing[1]['fpr']`. The one-line version is that")
    log("`ceiling_atom()` answers \"how much mass is at ln N\" and the column header promises")
    log("\"what is the cheapest alarm an operator can buy\"; those are the same question only")
    log("when the answer is non-zero.")
    log("")

    # ------------------------------------------------------------------------ section 6
    log("## 6. The two blocked claims")
    log("")
    log("**Claim 1 -- \"a larger sample budget makes semantic entropy a better ranker,")
    log("AUROC 0.704 -> 0.746 (+0.042)\": DOES NOT SURVIVE.** Both ends must come from one")
    log(f"source. They do here, and the gain is +{F['gain_ll']:.3f} "
        f"[{F['gain_ll_lo']:+.3f}, {F['gain_ll_hi']:+.3f}], which covers zero, on")
    log(f"the most favourable (fully nested, fully paired) design available. {F['share_source']:.0%} of the")
    log(f"advertised +{F['gain_direct']:.3f} is the change of cache. The paper may say the point")
    log("estimate rises and is not distinguishable from flat on 200 questions; it may not")
    log("say the budget makes it a better ranker, and it may not say the ranker is flat")
    log("either -- an interval that covers zero is not a demonstration of no effect.")
    log("")
    log("**Claim 2 -- \"the entire AUROC gain sits above 20% FPR, low-FPR pAUC 0.145 -> 0.126\":")
    log("DOES NOT SURVIVE AS WRITTEN.** The fall it cites is not a like-for-like measurement:")
    log("swap the direct N=10 row for the replayed one and the fall is gone, but nothing")
    log("takes its place, because the paired interval covers zero from both sides.")
    log("")
    wrap(PAUC10_LL, "> ")
    log("")
    log("So the claim is refuted and its negation is NOT established, and the paper may state")
    log("neither direction. What is left is a decomposition of an undetectable gain, which is")
    log("not a finding. If the paper wants a")
    log("sentence here, it is: *no budget effect on discrimination is detectable at any")
    log("false-alarm rate; the point estimates rise slightly and almost entirely above a 20%")
    log("false-alarm rate, where no operator runs.* That is honest and it is thin.")
    log("")
    log("**What is worth carrying instead** is the result that does survive uniform")
    log("provenance and does not need an AUROC at all: inside the replay family the floor")
    # same objects as section 2, so the two cannot drift apart -- see the note there
    log(f"falls monotonically with budget ({trend}), the N=10 -> N={top} fall clears")
    log(f"zero ({mfall.pts('points')}), and a 5% false-alarm budget goes from "
        "unbuyable to")
    log("buyable. **Stop there.** What the operator then gets for that budget in true")
    log("positives is the BLOCKED cross-budget TPR comparison; it is quarantined at the top")
    log("of this file, its sign and its magnitude both turn on which pairing is used (the")
    log("three pairings are set out in section 2), and no pairing separates the budgets at")
    log("200 questions. The rebuttal \"just raise N\" is answered by granularity --")
    log("by which operating points exist at all -- and not by discrimination, which is the")
    log("paper's thesis anyway.")
    log("")
    log("## 7. Provenance and reproduction")
    log("")
    log(f"- checkpoint: `{args.checkpoint}` ({len(recs)} evaluations, N={top}, full pairwise")
    log("  verdict matrices)")
    log(f"- Week-4 direct cache: `{cache}` (relabeled.jsonl, entropy.jsonl, samples.jsonl)")
    log(f"- population: fair pool, `_stratum_ids('right'/'wrong', seed={SEED})[:{NPS}]`; the ids in")
    log("  the checkpoint are verified identical to it at load, so every comparison above is")
    log("  paired on the same targets")
    log("- generation, both sources: Llama-3.1-8B-Instruct 4-bit, T=1.0, top_p=1.0,")
    log("  max_new_tokens=48, seed 0 (Week-4 `manifest.json` and the checkpoint records agree)")
    log(f"- subset draws per replayed budget: {R}; bootstrap resamples: {args.boot}; per-question")
    log(f"  subset draws for the cluster-count profiles: {args.mc}")
    log(f"- matched floor (section 2b): {args.sat_mc} subset draws per question for the")
    log(f"  per-question saturation probabilities, {args.boot_matched} question-bootstrap resamples;")
    log("  `--sat-mc` and `--boot-matched` change them. The matched machinery is")
    log("  `saturation_probs` / `floor_variance_split` / `quote` in the generator, and")
    log("  `quote` is what refuses an interval whose components do not match its estimand")
    log("- replay path: `budget_scores` / `score_subset` imported from")
    log("  `scripts/n_scaling_grid.py`, which drive the project's own")
    log("  `se.entropy.cluster_and_score` from the recorded verdicts")
    log("- regenerate: `.venv\\Scripts\\python.exe scripts\\replay_control.py`")
    log("- nothing here loads a model or uses the GPU")


if __name__ == "__main__":
    raise SystemExit(main())
