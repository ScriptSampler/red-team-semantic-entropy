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
    "**QUOTABLE.** The achievable-FPR floor trend taken entirely inside the replay family"
    " and labelled as such; the N=40 first firing point and the section 5 diagnosis of the"
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
    " section 2 covers zero except the floor. So no cross-budget difference reported here"
    " is a detectable effect in either direction, and the sign of any of those point"
    " estimates is not a finding. Two further mixing rules, from the 2026-08-19 gate:"
    " the direct N=10 row keeps its Wilson interval as everywhere else in the paper while"
    " replayed rows take the paired bootstrap, and the two are never put in one table"
    " without saying which is which; and the direct row is shown for contrast only and"
    " must not be mixed into a budget trend.",
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
    "ach05": "achieved FPR, 5% budget",
    "ach10": "achieved FPR, 10% budget",
    "ach20": "achieved FPR, 20% budget",
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", default=str(RESULTS_DIR / "n_scaling_ckpt.jsonl"))
    ap.add_argument("--cache", default=None, help="Week-4 cache dir (relabeled/entropy/samples)")
    ap.add_argument("--replicates", type=int, default=200, help="subset draws per replayed budget")
    ap.add_argument("--boot", type=int, default=4000, help="bootstrap resamples")
    ap.add_argument("--mc", type=int, default=4000, help="subset draws per question for the K profile")
    ap.add_argument("--out", default=None)
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
                 direct, ens, len_d, len_r, end_d, end_r)
    out_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out_path}", file=sys.stderr)
    return 0


def write_report(log, args, recs, top, cache, SRC, NAMES, packs, point, boot, mech,
                 direct, ens, len_d, len_r, end_d, end_r) -> None:
    R = len(SRC["replay10"])
    meas = f"measured{top}"

    def spread(nm, k):
        v = np.array([q[k] for q in packs[nm]])
        return v.mean(), (v.std(ddof=1) if len(v) > 1 else 0.0), v.min(), v.max()

    def diff_ci(a, b, k):
        d = boot[b][k] - boot[a][k]
        lo, hi = ci(d)
        return point[b][k] - point[a][k], lo, hi

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
    F["step_floor_rel"] = F["step_floor"] / point["direct10"]["floor"]
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
    # how much wider the honest interval is than one built from the replicate spread alone
    _sd = reps_floor.std(ddof=1) if R > 1 else float("nan")
    _lo, _hi = ci(boot["replay10"]["floor"] - boot["direct10"]["floor"])
    F["ci_halfwidth"] = (_hi - _lo) / 2.0
    F["rep_halfwidth"] = 1.959963985 * _sd
    F["ci_width_ratio"] = F["ci_halfwidth"] / F["rep_halfwidth"] if _sd else float("nan")

    for _line in _PROVENANCE.split("\n"):
        log(_line)
    log("")
    log("# The replay control: what the subsetting does, and what survives without it")
    log("")
    log(f"Generated {_dt.date.today().isoformat()} by `scripts/replay_control.py`. CPU-only:")
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
        d, dlo, dhi = diff_ci("direct10", "replay10", k)
        dv = point["direct10"][k]
        pct = k in ("floor", "m095", "m10", "m20")
        fmt = (lambda v: f"{v:.1%}") if pct else (lambda v: f"{v:.4f}")
        dfm = (lambda v: f"{v * 100:+.1f} pts") if pct else (lambda v: f"{v:+.4f}")
        log(f"| {LABEL[k]} | {fmt(dv)} | {fmt(m)} | {fmt(sd)} | {fmt(lo)}-{fmt(hi)} | "
            f"{dfm(d)} | [{dfm(dlo)}, {dfm(dhi)}] |")
    log("")
    log("**Sign and magnitude of the POINT ESTIMATES -- none of these steps is a detectable")
    log("difference.** The replay's point estimate reads higher than the direct cache on the")
    log(f"floor ({F['step_floor'] * 100:+.1f} points, {F['step_floor_rel']:+.0%} relative) and on "
        f"AUROC ({F['step_auroc']:+.3f}), and lower on")
    log("everything that prices detection near the operating region: TPR at a matched 9.5%")
    log(f"false-alarm rate ({F['step_m095'] * 100:+.1f} points) and partial AUROC below 10% "
        f"({F['step_pauc10']:+.3f}). Every")
    log("one of those intervals covers zero, so the signs in this paragraph describe the")
    log("point estimates only and no step here may be quoted as a direction. What the")
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
    log("unanimous run UP and not down; and the replicate spread measures only the subset")
    log("draw, so it is not an uncertainty on the step at all. The uncertainty on the step")
    log(f"is the paired interval in the table above: +/-{F['ci_halfwidth'] * 100:.1f} points on the floor, where")
    log(f"an interval built from the subset-draw spread alone would be +/-{F['rep_halfwidth'] * 100:.1f} points, "
        f"{F['ci_width_ratio']:.1f}x")
    log("narrower.")
    log("")

    # ------------------------------------------------------------------------ section 2
    log("## 2. The like-for-like budget comparison")
    log("")
    log(f"All three budgets from the one N={top} checkpoint. N=10 and N=20 are means over {R}")
    log(f"subset draws; N={top} is the single realisation there is. Intervals are a paired")
    log(f"bootstrap ({args.boot} resamples) that resamples the 200+200 targets jointly across")
    log("budgets AND resamples the subset draw, so both variance components are inside")
    log("every replayed cell. The direct row is shown for contrast only -- it is the row")
    log("that must not be mixed into a trend.")
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
            lo, hi = ci(boot[nm][k])
            cells.append(f"{fmt(point[nm][k])} [{fmt(lo)}, {fmt(hi)}]")
        log(f"| {LABEL[k]} | " + " | ".join(cells) + " |")
    log("")
    log("**The paired differences that matter.**")
    log("")
    log("| comparison | statistic | difference | 95% | verdict |")
    log("| --- | --- | --- | --- | --- |")
    for a, b in (("replay10", "replay20"), ("replay20", meas), ("replay10", meas),
                 ("direct10", meas)):
        for k in ("floor", "auroc", "pauc10", "m095", "m10"):
            d, lo, hi = diff_ci(a, b, k)
            pct = k in ("m095", "m10", "floor")
            fmt = (lambda v: f"{v * 100:+.1f} pts") if pct else (lambda v: f"{v:+.4f}")
            verdict = "excludes zero" if (lo > 0 or hi < 0) else "covers zero"
            log(f"| {a} -> {b} | {LABEL[k]} | {fmt(d)} | [{fmt(lo)}, {fmt(hi)}] | {verdict} |")
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
    fl = {nm: point[nm]["floor"] for nm in NAMES}
    log(f"- the floor falls {fl['replay10']:.1%} -> {fl['replay20']:.1%} -> {fl[meas]:.1%} on one source, and the")
    log(f"  N=10 -> N={top} difference clears zero by a wide margin "
        f"({diff_ci('replay10', meas, 'floor')[0] * 100:+.1f} points")
    log(f"  [{diff_ci('replay10', meas, 'floor')[1] * 100:+.1f}, "
        f"{diff_ci('replay10', meas, 'floor')[2] * 100:+.1f}]); the N=20 -> N={top} step on its own does not;")
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
    log("the replicate spread is subset-draw noise around a conditional mean, and it")
    log("understates the true uncertainty by construction. That is the actual defect in the")
    log("published control -- not bias, but an interval that is too narrow and a test whose")
    log("null does not hold. It is also why the report's replayed Wilson intervals (e.g.")
    log("N=20 floor \"3.0% [1.4%, 6.4%]\", computed on replicate 0) are understated.")
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
    log(f"  **{fir[0]:.1%}** ({fmt_prop(int(round(fir[0] * 200)), 200)});")
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
        f"({int(round(fir[0] * len(neg40)))}/{len(neg40)} negatives), and the next")
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
    log(f"falls monotonically with budget ({fl['replay10']:.1%} -> {fl['replay20']:.1%} -> "
        f"{fl[meas]:.1%}), the N=10 -> N={top} fall clears")
    log(f"zero ({diff_ci('replay10', meas, 'floor')[0] * 100:+.1f} points "
        f"[{diff_ci('replay10', meas, 'floor')[1] * 100:+.1f}, "
        f"{diff_ci('replay10', meas, 'floor')[2] * 100:+.1f}]), and a 5% false-alarm budget goes from "
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
    log("- replay path: `budget_scores` / `score_subset` imported from")
    log("  `scripts/n_scaling_grid.py`, which drive the project's own")
    log("  `se.entropy.cluster_and_score` from the recorded verdicts")
    log("- regenerate: `.venv\\Scripts\\python.exe scripts\\replay_control.py`")
    log("- nothing here loads a model or uses the GPU")


if __name__ == "__main__":
    raise SystemExit(main())
