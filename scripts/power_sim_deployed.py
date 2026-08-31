"""Power of the DEPLOYED exceedance test (analytic BetaBinomial null) vs the ORACLE-
calibrated simulation, on identical draws, at stated achieved levels.

WHY THIS SCRIPT EXISTS. `scripts/power_sim_randomized.py` calibrates its critical value
from a SEPARATE simulated null sample (`default_rng(seed+1)` / `(seed+2)`). That is an
ORACLE: it needs the true null of the data-generating process, which the deployed pipeline
does not have. The shipped test instead compares the observed exceedance total against the
analytic BetaBinomial null in `se.stats.exceedance_test`. Only the oracle column was ever
persisted (results/power_randomized.md, 0.67 / 0.84 at m=30 / m=50). The deployed column
that paper/sections/experiments.tex quotes — 0.51 at an achieved level of 0.025 for m=30
and 0.77 at 0.041 for m=50 — was produced in-session and never written to disk, which is the
failure class this script closes. Both columns are computed here from the same DGP, on the
SAME simulated draws, and written to one table.

THE COMPARISON IS LEVEL-MATCHED, DELIBERATELY. Comparing powers across tests at different
achieved levels is an error this project has already made once. It is avoidable here for a
structural reason worth stating: with a common benign budget m the analytic p-value is
p = F_BB(S), a strictly increasing function of the exceedance total S alone (the null is the
convolution of 80 identical BetaBinomial(m; 1, N) pmfs and does not otherwise depend on how
S is split across targets). So the deployed test rejects iff S <= c_analytic, and the oracle
test rejects iff S <= c_oracle. BOTH ARE THE SAME RULE ON THE SAME STATISTIC AT DIFFERENT CUT
POINTS. Everything separating their powers is therefore the critical value, i.e. the achieved
level, and the report gives the level-matched row that makes that explicit: read at equal
achieved level the two are identical, so "the shipped test is less powerful" is a statement
about its conservatism, not about a weaker statistic.

RULES REPORTED
  deployed        reject iff exceedance_test(counts, N).p_value <= alpha, ONE tie-break draw.
  deployed-median reject iff the MEDIAN p over `n_tie_seeds` tie-break draws <= alpha. This
                  is what the pipeline actually ships (`exceedance_test_over_seeds`); by the
                  monotonicity above it is exactly "median S over tie realisations <= c".
  oracle          reject iff S <= quantile(separate simulated null, alpha). Not deployable.
  exact-level     the largest integer cut whose ACHIEVED level is <= alpha on this DGP. The
                  best any threshold rule on S could do while honouring the level; the gap
                  between it and `deployed` is the price of the analytic null's conservatism,
                  and the gap between it and `oracle` is the oracle's level overspend.

TWO DESIGNS, BECAUSE THE RUN DID NOT DELIVER THE ONE THAT WAS PLANNED. `N_TARGETS` and
`M_GRID` describe the PLANNED experiment: 80 targets, one benign budget m shared by every
one of them. The confirmatory null control closed at 77 usable targets with SIX short arms
— m_j in {1, 26, 27, 27, 35, 38} and 50 on the remaining 71, 3,704 draws, identical across
the NLI, exact-match and judge arms. That heterogeneity moves the cut, because the analytic
null is the convolution of per-target BetaBinomial(m_j; 1, N) pmfs: the whole vector sets
the null, and the null's INTEGER GRANULARITY then decides which rung the cut lands on. Until
2026-08-31 this script could only express a uniform m, so the design that actually shipped
could not be run through it at all, and the paper quoted the planned design's 0.77 through
six review rounds while the realized design's figure was 0.67. Every function that took a
scalar `m` now takes a per-target VECTOR too (`m_vector` normalises either form), and
section E puts the two designs side by side against what the paper says about each. The
realized vector is pinned in `REALIZED_M_VECTOR` because its checkpoint is gitignored, and
`realized_m_vector` re-reads that checkpoint and stops the run if the two have parted.

COMPARE AT A LEVEL, NEVER AT A CUT. The two designs have different null distributions, so
one integer cut puts them at different SIZES — at S<=13 the realized design runs at nominal
0.0793 against the planned design's 0.0437 — and the more permissive test is more powerful
for free. That is the error section C already warns about for the deployed-vs-oracle pair
("the difference between the two columns is a level, not a statistic"), and it is just as
wrong across designs. Section E therefore compares them at a common ACHIEVED level, via a
randomised cut that attains the level exactly, and reports the fixed-cut row only with both
levels beside both powers. Read that way the realized design is the WEAKER of the two at
every level, and the drop from 0.77 to 0.67 splits into a granularity part and a
smaller-experiment part rather than being granularity alone.

CONDITIONING NOBODY SHOULD HAVE TO FIND. Every number here is computed at the attacker
budget A = N_ATTACK = 181, which experiments.tex declares an UPPER bound on a parameter it
says is not identified below 41. The cut is very sensitive to it: the planned design's cut
runs 13 -> 21 -> 72 and the realized design's 11 -> 19 -> 66 as A falls 181 -> 121 -> 41.
The power figures are therefore conditional on the top of the admissible range, and the
paper states them without that condition.

WHAT FAILURE LOOKS LIKE. Sections D and E check every pinned claim against what this run
computes, collect the disagreements, and `main` returns 1 with the list printed. A stale
claim, or a design that has moved under a claim, is an exit code rather than a line of
prose somebody has to notice — which is the specific way this script failed before.

DGP. Imported verbatim from `scripts/power_sim_randomized.py` (`one_target`) so the two
scripts cannot drift: per-target headroom from the empirical n=80 false-alarm cell, every
draw censored at that headroom (this is what creates the log(N) ceiling atom), attack = max
of N*mult draws with b = how many land on the cap, benign = m draws, K = strict exceedances
+ Binomial(ties, 1/(b+1)). `one_target_parts` below is the same code split so the tie credit
can be redrawn for the median rule; it is asserted stream-identical to the imported function.

HEADROOM PROVENANCE. `power_sim_randomized.py` reads the headroom from a session-scoped
temp file that will not survive, so this script resolves it from the attack cache and writes
the vector to `results/fa80_headroom.md`, which is committed. That file is then a valid
input on its own, so the simulation reproduces on a fresh clone with no cache.

    .venv/Scripts/python.exe scripts/power_sim_deployed.py
    .venv/Scripts/python.exe scripts/power_sim_deployed.py --out-dir <dir>

`--out-dir` redirects both artifacts (the report and the headroom mirror) somewhere other
than results/, so the checks can be re-run without rewriting a committed file.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from se.config import RESULTS_DIR                              # noqa: E402
from se.stats import exceedance_test                           # noqa: E402
from power_sim_randomized import N_ATTACK, CAP10, one_target   # noqa: E402

N_TARGETS = 80                  # the PLANNED design's target count (see TWO DESIGNS above)
ALPHA = 0.05
M_GRID = (20, 30, 50, 80)       # the PLANNED design's uniform benign budgets
MULTS = (2.0, 3.0)
SEED = 11                       # matches power_sim_randomized.power(seed=11)
TRIALS_PUB = 400                # ditto: the settings behind results/power_randomized.md
NULL_TRIALS_PUB = 2500
TRIALS_HI = 4000                # a second pass, for levels that are not 400-trial noise
NULL_TRIALS_HI = 20000
N_TIE_SEEDS = 25
HEADROOM_MD = "fa80_headroom.md"

# ------------------------------------------------------------------- the realized design
# The per-target benign budgets the confirmatory null control actually produced, sorted
# ascending. Three further targets carry m_j = 0; they are the three that take n from 80 to
# 77, and `exceedance_test` drops them itself. Pinned rather than only read, because
# results/null_control_ckpt_defb.jsonl is gitignored and this script has to reproduce on a
# bare clone; `realized_m_vector` re-reads the checkpoint wherever it exists and refuses to
# continue if the run on disk has parted from this constant.
REALIZED_M_VECTOR = (1, 26, 27, 27, 35, 38) + (50,) * 71
REALIZED_CKPT = "null_control_ckpt_defb.jsonl"
REALIZED_ARMS = ("nli", "exact", "judge")   # the three arms the run scored; embed was not
PLANNED_M = 50                              # the pre-registered uniform benign budget
TRIALS_DESIGN = 12000                       # per seed, per cell, in section E
DESIGN_SEEDS = (11, 12, 13)                 # section E pools these
CURVE_CMAX = 60                             # integer cuts the level/power ladders span
LEVEL_GRID = (0.025, 0.030, 0.040, 0.050)   # levels the two designs are matched at

# Candidate per-draw scales and the observed attack saturation they are matched to; both
# copied from power_sim_randomized.main so the calibration is bit-identical.
SCALES = (0.04, 0.06, 0.09, 0.12, 0.16, 0.20)
OBSERVED_SATURATION = 0.49

FA_CACHE = ROOT / "data" / "cache" / "attacks" / "wk9_defb_snap" / "triviaqa_se_false_alarm.jsonl"

# What paper/sections/experiments.tex asserts about the PLANNED (uniform-m) design, as of
# commit 88ff54d, recorded here so the check in section D is against a stated claim rather
# than a memory. "level" is the ACHIEVED level on this DGP and "nominal" the analytic null's
# own tail at the cut; the paper now states both and they are not the same number.
# Edit only to track the paper — and when you edit, re-run this script.
PAPER_CLAIMS = {
    30: {"power": 0.51, "level": 0.025, "nominal": 0.031,
         "oracle_power": 0.66, "oracle_level": 0.056},
    50: {"power": 0.77, "level": 0.041, "nominal": 0.044,
         "oracle_power": 0.84, "oracle_level": 0.064},
}

# What paper/sections/experiments.tex asserts about the two DESIGNS, as of commit 88ff54d.
# The realized row is the one the paper tells a reader to read a non-rejection against, so
# it is the row a future drift most needs to trip. Same rule: edit only to track the paper,
# and re-run.
#
# One thing here is NOT tracked to a source, deliberately.
# results/heavy_review_2_2026_08_31.md §3.1 concluded from a fixed cut of 13 that "the
# realized design is *stronger*... the loss is granularity, not the three missing targets".
# That inference is retracted: a fixed cut is not a fixed level, and at S<=13 the realized
# design runs at 1.8 times the planned design's size. See `fixed_cut` and `level_matched`
# below. The review's exact quantities (the cuts, the nominal levels, E[S]) all reproduce;
# it is only the comparison built on top of them that does not.
DESIGN_CLAIMS = {
    "planned": {
        "label": "planned (n=80, uniform m=50)",
        # "level" here and PAPER_CLAIMS[50]["level"] are the same quantity at different
        # precisions: 0.041 is the paper's own 4,000-trial figure, quoted in section D
        # because that is what the paper prints; 0.039 is the 36,000-trial estimate of it.
        "cut": 13, "nominal": 0.0437, "expected_h0": 21.98, "level": 0.039,
        "power": {2.0: 0.769, 3.0: 0.978},
    },
    "realized": {
        "label": "realized (n=77, shipped m-vector)",
        "cut": 11, "nominal": 0.0296, "expected_h0": 20.35, "level": 0.026,
        "power": {2.0: 0.670, 3.0: 0.952},
        # The substance of the correction: the cut one step up is already over alpha, so no
        # cut exists between these two levels and the realized design is forced down to 11.
        "next_cut": 12, "next_nominal": 0.0501,
    },
    # A FIXED cut is NOT a like-for-like comparison and nothing here may be read as one.
    # The two designs have different null distributions, so one integer cut puts them at
    # different SIZES: at S<=13 the realized design runs at nominal 0.0793 against the
    # planned design's 0.0437, a ratio of 1.8. A test operating at nearly twice the
    # type-I error rate is more powerful for free. Only the two LEVELS are pinned here,
    # because it was recording the two powers WITHOUT them that made the error invisible;
    # both are exact, and their ratio is the fact that disqualifies the comparison.
    "fixed_cut": {"cut": 13, "nominal_planned": 0.0437, "nominal_realized": 0.0793,
                  "ratio": 1.82},
    # The comparison that IS meaningful: power against a two-fold effect at a common
    # ACHIEVED level, reached by a randomised cut so the level is hit exactly. The
    # realized design is the weaker of the two at every level. Values from this script's
    # own DGP at 60,000 trials per cell; the SIGN of the gap is the robust claim and the
    # magnitudes carry Monte-Carlo error, so they are checked with a loose tolerance.
    # 0.025 and 0.050 are the two cells experiments.tex states (0.669 vs 0.699 and 0.783
    # vs 0.809); 0.030 and 0.040 the paper does not state and are this script's own. The
    # realized column reproduces to three decimals. The planned column does not quite: this
    # script measures 0.689 to 0.692 at level 0.025 against the paper's 0.699, so the
    # paper's figure for that one cell sits about 0.01 high. It is inside the tolerance and
    # inside plausible Monte-Carlo error for an unstated trial count, so it is tracked
    # rather than flagged, and recorded here so a later widening of that gap is visible.
    "level_matched": {
        0.025: {"planned": 0.699, "realized": 0.669},
        0.030: {"planned": 0.722, "realized": 0.696},
        0.040: {"planned": 0.775, "realized": 0.747},
        0.050: {"planned": 0.809, "realized": 0.783},
    },
    # Splitting the 0.098 drop into "the cut moved" and "the experiment shrank". The split
    # is PATH-DEPENDENT: doing the level first charges more to granularity than doing the
    # design first, and neither order is privileged, so the symmetric (Shapley) average is
    # what is pinned and both orders are printed. What is robust, and checked separately,
    # is that granularity is the larger of the two.
    "decomposition": {"total": 0.098, "granularity": 0.071, "design": 0.027},
    # And the design term split again, at a matched level, by an intermediate design of 77
    # targets at a uniform m=50, averaged over `LEVEL_GRID`. These are what this script
    # measures at 60,000 trials per cell, not what the paper states: experiments.tex says
    # "the three untested targets cost about 0.02 and the short arms about 0.02", whose sum
    # of 0.04 is larger than the level-matched gap it decomposes (0.030 at level 0.025 by
    # the paper's own figures, 0.025 by this script's). The two sub-terms must sum to that
    # gap, and here they do. A disagreement with the paper is reported, not reconciled, so
    # the measured pair is pinned and the paper's is named in this comment.
    # Each term is individually noisy - the per-level spread runs 0.006 to 0.020 - so the
    # robust facts, checked separately below, are that BOTH are positive and that they sum
    # to the level-matched gap.
    "design_split": {"lost_targets": 0.010, "short_arms": 0.015},
}


# ------------------------------------------------------------------ per-target budgets

def m_vector(m, n_targets=None) -> tuple[int, ...]:
    """Normalise a benign budget to a PER-TARGET vector.

    `m` is either a scalar budget shared by `n_targets` targets (the planned design, and
    what every caller in this repository passed before 2026-08-31) or a sequence of
    per-target budgets, in which case `n_targets` is redundant and only checked. The
    inability to say the second thing is what kept the deployed design out of this script.
    """
    if isinstance(m, (int, np.integer)):
        if n_targets is None:
            raise ValueError("a scalar benign budget needs n_targets")
        if int(n_targets) < 1:
            raise ValueError(f"n_targets must be >= 1, got {n_targets}")
        return (int(m),) * int(n_targets)
    v = tuple(int(x) for x in m)
    if not v:
        raise ValueError("empty m-vector")
    if n_targets is not None and int(n_targets) != len(v):
        raise ValueError(
            f"n_targets={n_targets} contradicts an m-vector of length {len(v)}")
    return v


def _runs(v) -> str:
    """`(1, 26, 26, 50, 50, 50)` -> `1x1, 26x2, 50x3`: an m-vector a human can read."""
    out, prev, k = [], None, 0
    for x in list(v) + [None]:
        if x == prev:
            k += 1
            continue
        if prev is not None:
            out.append(f"{prev}x{k}")
        prev, k = x, 1
    return ", ".join(out)


def realized_m_vector() -> tuple[tuple[int, ...], str]:
    """(the per-target budgets of the design that RAN, provenance string).

    Read out of the null control's own checkpoint whenever it is present, and checked
    against `REALIZED_M_VECTOR`; a constant that has gone stale against the run is exactly
    the failure this script exists to catch, so a mismatch stops the run rather than being
    reported at the bottom of a table. Falls back to the constant on a clone that does not
    carry the (gitignored) checkpoint.
    """
    ckpt = RESULTS_DIR / REALIZED_CKPT
    if not ckpt.exists():
        return REALIZED_M_VECTOR, f"pinned REALIZED_M_VECTOR ({REALIZED_CKPT} not present)"
    rows = [json.loads(l) for l in ckpt.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    per_arm = {arm: [len(r["benign"][arm]) for r in rows] for arm in REALIZED_ARMS}
    ref_arm = REALIZED_ARMS[0]
    for arm, lens in per_arm.items():
        if lens != per_arm[ref_arm]:
            raise SystemExit(
                f"{REALIZED_CKPT}: arm '{arm}' has a different per-target benign budget "
                f"from '{ref_arm}' ({sum(lens)} draws vs {sum(per_arm[ref_arm])}). Section "
                f"E assumes ONE m-vector shared by all three arms, which is no longer true; "
                f"the design section has to be split per arm before it can be trusted.")
    found = tuple(sorted(x for x in per_arm[ref_arm] if x > 0))
    if found != REALIZED_M_VECTOR:
        raise SystemExit(
            f"the run on disk has parted from REALIZED_M_VECTOR.\n"
            f"  pinned : n={len(REALIZED_M_VECTOR)} draws={sum(REALIZED_M_VECTOR)} "
            f"[{_runs(REALIZED_M_VECTOR)}]\n"
            f"  on disk: n={len(found)} draws={sum(found)} [{_runs(found)}]\n"
            f"Update REALIZED_M_VECTOR and DESIGN_CLAIMS['realized'] together, re-run, and "
            f"check the power figure in paper/sections/experiments.tex against the result. "
            f"The last time these parted, the paper was wrong by 0.10 for six rounds.")
    return found, (f"`{ckpt.relative_to(ROOT)}` ({len(rows)} records, "
                   f"{len(rows) - len(found)} of them with m=0)")


# --------------------------------------------------------------------------- headroom

def resolve_headroom() -> tuple[np.ndarray, list[str], str]:
    """(headroom vector, question ids, provenance string), preferring the raw cache."""
    if FA_CACHE.exists():
        rows = [json.loads(l) for l in FA_CACHE.read_text(encoding="utf-8").splitlines()
                if l.strip()]
        hr = np.array([CAP10 - r["entropy_before"] for r in rows], dtype=float)
        return hr, [r["question_id"] for r in rows], str(FA_CACHE.relative_to(ROOT))
    committed = RESULTS_DIR / HEADROOM_MD
    if committed.exists():
        qids, vals = [], []
        for line in committed.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and "|" in line[2:]:
                parts = [p.strip() for p in line.strip().strip("|").split("|")]
                if len(parts) == 3 and parts[0] not in ("question_id", "---"):
                    try:
                        vals.append(CAP10 - float(parts[1]))
                    except ValueError:
                        continue
                    qids.append(parts[0])
        if vals:
            return np.array(vals, dtype=float), qids, str(committed.relative_to(ROOT))
    raise SystemExit(
        f"no headroom source: neither {FA_CACHE} nor {RESULTS_DIR / HEADROOM_MD} exists. "
        f"Rebuild the false-alarm cell (scripts/recompute_fair.py --only se_false_alarm) "
        f"or restore results/{HEADROOM_MD}.")


def write_headroom_artifact(hr: np.ndarray, qids: list[str], provenance: str,
                            out_dir: Path | None = None) -> Path:
    L = ["# Empirical per-target headroom, n=80 false-alarm cell",
         "",
         "The input to `scripts/power_sim_deployed.py` and (via the same DGP) to",
         "`scripts/power_sim_randomized.py`. headroom = log(10) - entropy_before, i.e. how far",
         "the clean score sits below the semantic-entropy ceiling; a target with zero headroom",
         "is already saturated and can only produce ties. Committed because the simulation that",
         "sets the definitive run's benign budget must not depend on a scratch file.",
         "",
         f"source: `{provenance}`",
         f"n = {len(hr)}; mean headroom {hr.mean():.6f} nats; "
         f"zero-headroom targets {int((hr <= 1e-9).sum())}; ceiling log(10) = {CAP10:.6f}",
         "",
         "| question_id | entropy_before | headroom |",
         "| --- | --- | --- |"]
    # Full float precision: the DGP censors with a 1e-12 tolerance, so a rounded mirror
    # would not be an exact substitute for the cache.
    for q, h in zip(qids, hr):
        L.append(f"| {q} | {CAP10 - h:.17g} | {h:.17g} |")
    out = (out_dir or RESULTS_DIR) / HEADROOM_MD
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def calibrate_scale(hr: np.ndarray) -> tuple[float, float]:
    """Bit-identical copy of power_sim_randomized.main's scale search."""
    best = None
    for s in SCALES:
        rng = np.random.default_rng(3)
        sat = np.mean([1.0 if one_target(s, h, 5, 1.0, rng) is not None and
                       (np.minimum(rng.exponential(s, N_ATTACK), h).max() >= h - 1e-12)
                       else 0.0 for h in hr])
        if best is None or abs(sat - OBSERVED_SATURATION) < abs(best[1] - OBSERVED_SATURATION):
            best = (s, float(sat))
    return best


# ------------------------------------------------------------------- DGP, split for ties

def one_target_parts(scale, h, m, mult, rng):
    """`power_sim_randomized.one_target` up to the tie-credit draw: (strict, tied, b).

    Consumes exactly the same two exponential draws, in the same order, so drawing the
    binomial credit immediately afterwards reproduces that function's RNG stream exactly.
    """
    n_att = int(round(N_ATTACK * mult))
    att = np.minimum(rng.exponential(scale, n_att), h)
    A = att.max()
    b = max(1, int((att >= h - 1e-12).sum())) if A >= h - 1e-12 else 1
    ben = np.minimum(rng.exponential(scale, m), h)
    strict = int((ben > A + 1e-12).sum())
    tied = int(np.isclose(ben, A).sum())
    return strict, tied, b


def run_totals(scale, hr, m, n_targets, mult, trials, rng, *, tie_rng=None,
               n_tie_seeds=1):
    """Per-trial exceedance totals: (S_single, S_median_over_tie_seeds).

    S_single is the total under ONE tie-break realisation and is stream-identical to
    `power_sim_randomized.run`. S_median re-draws the tie credit `n_tie_seeds` times from an
    INDEPENDENT rng (the first realisation is the same one S_single used) and takes the
    median total, which is what `exceedance_test_over_seeds` reports via the median p-value.

    `m` is a scalar budget shared by `n_targets` targets, or a per-target vector (in which
    case `n_targets` may be None). The scalar path consumes the rng in exactly the order it
    always did — headroom indices for the whole trial, then per target the attack draws, the
    benign draws and the tie credit — so it stays stream-identical to the imported DGP.
    """
    mv = m_vector(m, n_targets)
    n_targets = len(mv)
    single = np.empty(trials, dtype=float)
    median = np.empty(trials, dtype=float)
    for t in range(trials):
        tot0 = 0
        per_seed = np.zeros(n_tie_seeds, dtype=float)
        for h, m_j in zip(hr[rng.integers(0, len(hr), n_targets)], mv):
            strict, tied, b = one_target_parts(scale, h, m_j, mult, rng)
            c0 = int(rng.binomial(tied, 1.0 / (b + 1))) if tied else 0
            tot0 += strict + c0
            if n_tie_seeds > 1:
                per_seed[0] += strict + c0
                if tied:
                    per_seed[1:] += strict + tie_rng.binomial(
                        tied, 1.0 / (b + 1), n_tie_seeds - 1)
                else:
                    per_seed[1:] += strict
        single[t] = tot0
        median[t] = float(np.median(per_seed)) if n_tie_seeds > 1 else tot0
    return single, median


def _assert_dgp_identity(scale, hr, m):
    """The split DGP must reproduce the imported one bit for bit, or the whole point of
    importing it is lost."""
    a = np.array([one_target(scale, h, m, 2.0, np.random.default_rng(99))
                  for h in hr[:20]])
    b = []
    for h in hr[:20]:
        r = np.random.default_rng(99)
        strict, tied, bb = one_target_parts(scale, h, m, 2.0, r)
        b.append(strict + (int(r.binomial(tied, 1.0 / (bb + 1))) if tied else 0))
    assert np.array_equal(a, np.array(b)), "one_target_parts drifted from one_target"


# ------------------------------------------------------------- the deployed critical value

def analytic_p(total: int, m, n_targets=None) -> float:
    """`se.stats.exceedance_test`'s p-value for an exceedance total, via the deployed
    function itself. `m` is a scalar budget with `n_targets`, or a per-target vector.

    The total is packed into the targets greedily rather than split evenly, because a
    greedy pack is the split that stays feasible when the budgets differ: a target cannot
    carry more exceedances than it has benign draws. The p-value is unchanged by the
    choice. The null is the convolution of the per-target pmfs, so it depends on the
    m-VECTOR and on the total and never on how the total is distributed across targets;
    `_assert_total_only` checks that on every run, and at a uniform m the greedy pack and
    the old even split hand `exceedance_test` the same m-sequence and the same observed
    total, hence a bit-identical p.
    """
    mv = m_vector(m, n_targets)
    total = int(total)
    if not 0 <= total <= sum(mv):
        raise ValueError(f"total {total} outside [0, {sum(mv)}] for this m-vector")
    counts, rem = [], total
    for m_j in mv:
        k = min(m_j, rem)
        counts.append((k, m_j))
        rem -= k
    return exceedance_test(counts, N_ATTACK)["p_value"]


def _assert_total_only(m, n_targets, total: int) -> None:
    """p must depend on the TOTAL only, not on how it is split, or the reduction of both
    tests to a cut on S is invalid."""
    mv = m_vector(m, n_targets)
    rng = np.random.default_rng(0)
    ref = analytic_p(total, mv)
    for _ in range(3):
        cuts = np.sort(rng.integers(0, total + 1, len(mv) - 1))
        parts = np.diff(np.concatenate(([0], cuts, [total])))
        if any(int(k) > m_j for k, m_j in zip(parts, mv)):
            continue
        p = exceedance_test([(int(k), int(m_j)) for k, m_j in zip(parts, mv)],
                            N_ATTACK)["p_value"]
        assert abs(p - ref) < 1e-10, f"analytic p depends on the split: {p} vs {ref}"


def analytic_crit(m, n_targets=None, alpha: float = ALPHA) -> int:
    """Largest integer total the deployed test still rejects at `alpha` (-1 = never).

    This is the function the whole 0.77-to-0.67 correction turns on. The cut is an
    INTEGER, so the achievable levels are a ladder and a design lands on a rung rather
    than on alpha: the planned design's rung is S<=13 at 0.0437, the realized design's is
    S<=11 at 0.0296, and there is nothing in between because the next rung up is already
    0.0501. Section E prints both ladders.
    """
    mv = m_vector(m, n_targets)
    lo, hi = -1, sum(mv)
    while lo < hi:                                   # p is increasing in the total
        mid = (lo + hi + 1) // 2
        if analytic_p(mid, mv) <= alpha:
            lo = mid
        else:
            hi = mid - 1
    return lo


def exact_level_crit(null_sample: np.ndarray, alpha: float) -> int:
    """Largest integer cut whose achieved level on this DGP is <= alpha."""
    cuts = np.arange(-1, int(null_sample.max()) + 1)
    ok = [c for c in cuts if (null_sample <= c).mean() <= alpha]
    return int(max(ok)) if ok else -1


# ----------------------------------------------------- claims, checked and not narrated

def _mc_tol(p: float, n: int, floor: float) -> float:
    """Three binomial standard errors on a Monte-Carlo rate, never tighter than `floor`."""
    p = min(max(float(p), 0.0), 1.0)
    return max(3.0 * math.sqrt(max(p * (1.0 - p), 1e-12) / max(int(n), 1)), float(floor))


class Checks:
    """Every pinned claim, compared against what this run computes.

    This exists rather than a bare verdict column because the previous version of this
    script printed `**DIFFERS**` beside two stale levels for six review rounds and still
    exited 0, so nothing downstream ever went red. A disagreement is now the exit code.
    """

    def __init__(self) -> None:
        self.failures: list[str] = []

    def verdict(self, label: str, value: float, claimed: float, tol: float) -> str:
        ok = abs(float(value) - float(claimed)) <= float(tol)
        if not ok:
            self.failures.append(
                f"{label}: this run gives {float(value):.4f}, the pinned claim is "
                f"{float(claimed):.4f} (tolerance {float(tol):.4f})")
        return "MATCHES" if ok else "**DIFFERS**"

    def verdict_int(self, label: str, value: int, claimed: int) -> str:
        ok = int(value) == int(claimed)
        if not ok:
            self.failures.append(
                f"{label}: this run gives {int(value)}, the pinned claim is {int(claimed)}")
        return "MATCHES" if ok else "**DIFFERS**"


def one_design(scale, hr, mv, *, trials, seeds, mults=MULTS):
    """The whole level/power ladder of the deployed rule for ONE design's m-vector.

    The uniform-grid driver `one_m` answers "what does budget m buy?" across a grid and
    carries the oracle and exact-level comparators with it. This answers the narrower
    question the paper actually needs and `one_m` cannot pose: given the per-target benign
    budgets of a NAMED design, where does the deployed cut land and what does it detect.

    It keeps the achieved level and the power at EVERY integer cut, not just at the
    deployed one, because comparing two designs at their own cuts compares two sizes and
    the only honest cross-design reading is at a matched level (see `power_at_level`).
    Averaged over `seeds` because one 12,000-trial power carries about half a point of
    Monte-Carlo error and the differences this section reports are two to ten points.
    """
    mv = m_vector(mv)
    total = sum(mv)
    cut = analytic_crit(mv)
    out = {
        "m_vector": mv, "n_targets": len(mv), "draws": total, "cut": cut,
        "nominal": analytic_p(cut, mv),
        "nominal_next": analytic_p(cut + 1, mv) if cut + 1 <= total else float("nan"),
        "nominal_prev": analytic_p(cut - 1, mv) if cut >= 1 else float("nan"),
        "expected_h0": total / (N_ATTACK + 1),
        "trials": int(trials), "seeds": tuple(seeds),
        "level_by_seed": [], "null_mean_by_seed": [],
        "power_by_seed": {mult: [] for mult in mults},
    }
    h0_parts, h1_parts = [], {mult: [] for mult in mults}
    for sd in seeds:
        lvl, _ = run_totals(scale, hr, mv, None, 1.0, trials,
                            np.random.default_rng(sd + 2))
        h0_parts.append(lvl)
        out["level_by_seed"].append(float((lvl <= cut).mean()))
        out["null_mean_by_seed"].append(float(lvl.mean()))
        for mult in mults:
            obs, _ = run_totals(scale, hr, mv, None, mult, trials,
                                np.random.default_rng(sd + 1))
            h1_parts[mult].append(obs)
            out["power_by_seed"][mult].append(float((obs <= cut).mean()))
    h0 = np.concatenate(h0_parts)
    h1 = {mult: np.concatenate(v) for mult, v in h1_parts.items()}
    cuts = np.arange(CURVE_CMAX + 1)
    out["cuts"] = cuts
    out["level_curve"] = np.array([float((h0 <= c).mean()) for c in cuts])
    out["power_curve"] = {mult: np.array([float((v <= c).mean()) for c in cuts])
                          for mult, v in h1.items()}
    out["level"] = float(np.mean(out["level_by_seed"]))
    out["null_mean"] = float(np.mean(out["null_mean_by_seed"]))
    out["power"] = {mult: float(np.mean(v)) for mult, v in out["power_by_seed"].items()}
    out["n_mc"] = int(trials) * len(out["seeds"])
    return out


def _crit_at_budget(mv, budget: int, alpha: float = ALPHA) -> tuple[int, float]:
    """(cut, nominal level) if the attacker budget A were `budget` rather than N_ATTACK.

    Only for the scope note in section E6: the whole simulation is run at A = N_ATTACK,
    the top of the range experiments.tex declares admissible, and the cut moves a long way
    down that range. `exceedance_test` takes A as an argument, so this needs no new null.
    """
    mv = m_vector(mv)
    lo, hi = -1, sum(mv)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        rem, counts = mid, []
        for m_j in mv:
            k = min(m_j, rem)
            counts.append((k, m_j))
            rem -= k
        if exceedance_test(counts, int(budget))["p_value"] <= alpha:
            lo = mid
        else:
            hi = mid - 1
    rem, counts = max(lo, 0), []
    for m_j in mv:
        k = min(m_j, rem)
        counts.append((k, m_j))
        rem -= k
    return lo, float(exceedance_test(counts, int(budget))["p_value"])


def power_at_level(design, alpha: float, mult: float = 2.0) -> float:
    """Power of a RANDOMISED cut whose achieved level is exactly `alpha`.

    Two designs cannot be compared at a common integer cut, because their null
    distributions differ and one cut therefore means two different sizes. They can be
    compared at a common LEVEL. The achievable (level, power) pairs of a cut rule are the
    ladder's vertices plus everything on the segments between them: mixing cuts c and
    c+1 with probability g gives level (1-g)L(c) + g L(c+1) and power (1-g)W(c) + g W(c+1),
    so the attainable set is the linear interpolation of the ladder and this function
    reads it off. That is the standard randomised test that attains a level exactly, and
    it is the only device here that makes the two designs commensurable.
    """
    L, W = design["level_curve"], design["power_curve"][mult]
    alpha = float(alpha)
    if alpha <= L[0]:
        return float(W[0] * (alpha / L[0])) if L[0] > 0 else 0.0
    for c in range(len(L) - 1):
        if L[c] <= alpha <= L[c + 1]:
            if L[c + 1] == L[c]:
                return float(W[c])
            g = (alpha - L[c]) / (L[c + 1] - L[c])
            return float((1.0 - g) * W[c] + g * W[c + 1])
    return float(W[-1])


def decompose_drop(planned, realized, mult: float = 2.0) -> dict:
    """Split the power drop into "the cut moved" and "the experiment shrank".

    The drop runs from the planned design at its own operating point to the realized
    design at its own. Two things changed at once, so the split is PATH-DEPENDENT and
    both orders are returned rather than one being passed off as the answer:

      order A  move the level first, on the planned design, then swap the design;
      order B  swap the design first, at the planned level, then move the level.

    Their symmetric average is the Shapley value of the two-factor decomposition. What
    survives the path dependence, and is what the report checks, is the ordering: the
    granularity term is the larger of the two under either order.
    """
    Lp, Lr = planned["level"], realized["level"]
    Wp, Wr = planned["power"][mult], realized["power"][mult]
    a_gran = Wp - power_at_level(planned, Lr, mult)
    a_design = power_at_level(planned, Lr, mult) - Wr
    b_design = Wp - power_at_level(realized, Lp, mult)
    b_gran = power_at_level(realized, Lp, mult) - Wr
    return {
        "total": Wp - Wr,
        "A": {"granularity": a_gran, "design": a_design},
        "B": {"granularity": b_gran, "design": b_design},
        "granularity": 0.5 * (a_gran + b_gran),
        "design": 0.5 * (a_design + b_design),
    }


# ------------------------------------------------------------------------------- driver

def one_m(scale, hr, m, *, trials, null_trials, seed, n_tie_seeds):
    """All four rules for one benign budget, on one shared set of simulated draws."""
    rng = np.random.default_rng(seed)
    null, _ = run_totals(scale, hr, m, N_TARGETS, 1.0, null_trials, rng)
    crit_oracle = float(np.quantile(null, ALPHA))

    tie_rng = np.random.default_rng(seed + 500)
    lvl_single, lvl_median = run_totals(scale, hr, m, N_TARGETS, 1.0, trials,
                                        np.random.default_rng(seed + 2),
                                        tie_rng=tie_rng, n_tie_seeds=n_tie_seeds)
    c_dep = analytic_crit(m, N_TARGETS, ALPHA)
    c_exact = exact_level_crit(lvl_single, ALPHA)

    out = {
        "m": m,
        "null_mean": float(null.mean()),
        "expected_h0": N_TARGETS * m / (N_ATTACK + 1),
        "crit_deployed": c_dep,
        "crit_oracle": crit_oracle,
        "crit_exact_level": c_exact,
        # The analytic null's OWN tail probability at the deployed cut: what the test
        # believes its level is. It is not the level it achieves on this DGP, and the two
        # must never be conflated (same discipline as operating_point's achieved FPR).
        "nominal_deployed": analytic_p(c_dep, m, N_TARGETS) if c_dep >= 0 else float("nan"),
        # Level measured on the big H0 sample used for the oracle cut: the most precise
        # estimate available in this run, and an independent one from lvl_single.
        "level_deployed_bignull": float((null <= c_dep).mean()),
        "level_deployed": float((lvl_single <= c_dep).mean()),
        "level_deployed_median": float((lvl_median <= c_dep).mean()),
        "level_oracle": float((lvl_single <= crit_oracle).mean()),
        "level_exact": float((lvl_single <= c_exact).mean()),
        "power": {},
    }
    for mult in MULTS:
        obs_single, obs_median = run_totals(scale, hr, m, N_TARGETS, mult, trials,
                                            np.random.default_rng(seed + 1),
                                            tie_rng=np.random.default_rng(seed + 501),
                                            n_tie_seeds=n_tie_seeds)
        out["power"][mult] = {
            "deployed": float((obs_single <= c_dep).mean()),
            "deployed_median": float((obs_median <= c_dep).mean()),
            "oracle": float((obs_single <= crit_oracle).mean()),
            "exact_level": float((obs_single <= c_exact).mean()),
        }
        # level-matched: power of a cut whose achieved level equals the ORACLE's, read off
        # the same H0/H1 samples. Both tests are cuts on S, so this is the honest way to ask
        # whether the deployed STATISTIC is weaker (it is not) rather than merely stricter.
        target_lvl = out["level_oracle"]
        cuts = np.arange(-1, int(max(lvl_single.max(), obs_single.max())) + 1)
        j = int(min(range(len(cuts)),
                    key=lambda i: abs((lvl_single <= cuts[i]).mean() - target_lvl)))
        out["power"][mult]["at_oracle_level"] = float((obs_single <= cuts[j]).mean())
        out["power"][mult]["cut_at_oracle_level"] = int(cuts[j])
    return out


def _fmt(rows, trials, null_trials, seed):
    L = [f"Simulated draws: {null_trials} H0 trials for the oracle critical value, "
         f"{trials} trials each for the achieved level and for every power cell; "
         f"seed {seed}. Level and power are measured on the SAME draws for every rule, so "
         f"the columns are paired and differ only in the cut applied. `nominal dep.` is the "
         f"analytic null's own tail at the deployed cut — what the test BELIEVES its level "
         f"is; `level dep.` is what it achieves on this DGP, from the "
         f"{trials}-trial sample, and `(big null)` repeats it on the "
         f"{null_trials}-trial one.", "",
         "| m | crit (deployed) | crit (oracle) | nominal dep. | level dep. | "
         "level dep. (big null) | level dep.-median | level oracle | pow 2x dep. | "
         "pow 2x dep.-med | pow 2x oracle | pow 3x dep. | pow 3x oracle |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        p2, p3 = r["power"][2.0], r["power"][3.0]
        L.append(
            f"| {r['m']} | {r['crit_deployed']} | {r['crit_oracle']:.1f} | "
            f"{r['nominal_deployed']:.3f} | "
            f"{r['level_deployed']:.3f} | {r['level_deployed_bignull']:.3f} | "
            f"{r['level_deployed_median']:.3f} | "
            f"{r['level_oracle']:.3f} | **{p2['deployed']:.2f}** | "
            f"{p2['deployed_median']:.2f} | {p2['oracle']:.2f} | "
            f"{p3['deployed']:.2f} | {p3['oracle']:.2f} |")
    return L


def _parse_out_dir(argv) -> Path:
    """`--out-dir DIR` sends both artifacts somewhere other than `results/`, so the checks
    below can be re-run without rewriting a committed file."""
    argv = list(argv)
    for i, a in enumerate(argv):
        if a == "--out-dir":
            if i + 1 >= len(argv):
                raise SystemExit("--out-dir needs a directory")
            return Path(argv[i + 1]).expanduser().resolve()
        if a.startswith("--out-dir="):
            return Path(a.split("=", 1)[1]).expanduser().resolve()
        raise SystemExit(f"unknown argument {a!r}; the only option is --out-dir DIR")
    return RESULTS_DIR


def main(argv=None) -> int:
    out_dir = _parse_out_dir(sys.argv[1:] if argv is None else argv)
    out_dir.mkdir(parents=True, exist_ok=True)
    ck = Checks()

    hr, qids, provenance = resolve_headroom()
    art = write_headroom_artifact(hr, qids, provenance, out_dir)
    scale, sat = calibrate_scale(hr)
    _assert_dgp_identity(scale, hr, 30)
    for m in M_GRID:
        _assert_total_only(m, N_TARGETS, int(round(N_TARGETS * m / (N_ATTACK + 1))))

    # The two designs. `realized_m_vector` stops the run if the checkpoint has parted from
    # the pinned vector, which is the drift that produced the 0.77 the paper carried.
    realized_mv, realized_prov = realized_m_vector()
    planned_mv = m_vector(PLANNED_M, N_TARGETS)
    _assert_total_only(realized_mv, None, int(round(sum(realized_mv) / (N_ATTACK + 1))))

    print(f"headroom from {provenance}: n={len(hr)} mean {hr.mean():.3f} "
          f"zero-headroom {int((hr <= 1e-9).sum())}")
    print(f"calibrated scale {scale} (saturation {sat:.0%} vs observed "
          f"{OBSERVED_SATURATION:.0%})")
    print(f"headroom artifact -> {art}")
    print(f"realized m-vector from {realized_prov}: n={len(realized_mv)} "
          f"draws={sum(realized_mv)} [{_runs(realized_mv)}]\n")

    pub = [one_m(scale, hr, m, trials=TRIALS_PUB, null_trials=NULL_TRIALS_PUB,
                 seed=SEED, n_tie_seeds=N_TIE_SEEDS) for m in M_GRID]
    print("published-settings pass done", flush=True)
    hi = [one_m(scale, hr, m, trials=TRIALS_HI, null_trials=NULL_TRIALS_HI,
                seed=SEED, n_tie_seeds=N_TIE_SEEDS) for m in M_GRID]
    print("high-precision pass done", flush=True)

    # The intermediate design isolates the two halves of the "the experiment shrank" term:
    # planned -> n77_uniform is the three targets the run could not test, and
    # n77_uniform -> realized is the six short arms. Only the two-fold cell is needed.
    n77_uniform_mv = m_vector(PLANNED_M, len(realized_mv))
    designs = {
        "planned": one_design(scale, hr, planned_mv, trials=TRIALS_DESIGN,
                              seeds=DESIGN_SEEDS),
        "realized": one_design(scale, hr, realized_mv, trials=TRIALS_DESIGN,
                               seeds=DESIGN_SEEDS),
        "n77_uniform": one_design(scale, hr, n77_uniform_mv, trials=TRIALS_DESIGN,
                                  seeds=DESIGN_SEEDS, mults=(2.0,)),
    }
    print("planned-vs-realized design pass done", flush=True)

    L: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); L.append(s)

    log("# Deployed (analytic-null) vs oracle-calibrated power, same draws, stated levels")
    log("")
    log("Producing script: `scripts/power_sim_deployed.py`. Companion to")
    log("`results/power_randomized.md`, which reported the ORACLE column only. The deployed")
    log("column is the test the pipeline actually runs: `se.stats.exceedance_test`'s analytic")
    log("BetaBinomial null, no access to the true simulated null.")
    log("")
    log(f"DGP imported verbatim from `scripts/power_sim_randomized.py`. Headroom from "
        f"`{provenance}`, mirrored to `results/{HEADROOM_MD}` so this reproduces without the "
        f"cache. Attacker candidates N = {N_ATTACK}, nominal alpha = {ALPHA}.")
    log(f"Per-draw exponential scale {scale}, calibrated to {sat:.0%} attack saturation "
        f"against the observed {OBSERVED_SATURATION:.0%}.")
    log("")
    log(f"**Sections A-D are the PLANNED design** ({N_TARGETS} targets, one benign budget m "
        f"shared by all of them). **Section E is the design that ran**, whose per-target "
        f"budgets differ, and it is section E the paper's non-rejection has to be read "
        f"against.")
    log("")
    log("Rules: **deployed** = analytic p <= alpha on one tie-break draw; **dep.-median** = "
        "median p over "
        f"{N_TIE_SEEDS} tie-break draws (what `exceedance_test_over_seeds` ships); "
        "**oracle** = S <= 5th percentile of a separate simulated null, which the deployed "
        "test cannot compute.")
    log("")

    log("## A. Published settings - reproduces results/power_randomized.md's oracle column")
    log("")
    L.extend(_fmt(pub, TRIALS_PUB, NULL_TRIALS_PUB, SEED))
    log("")
    log(f"At {TRIALS_PUB} trials an achieved level near 0.05 carries a standard error of "
        f"about {math.sqrt(0.05 * 0.95 / TRIALS_PUB):.3f}, so read these levels as "
        f"indicative and the ones in table B as the measurement.")
    log("")

    log("## B. High precision - the numbers to quote")
    log("")
    L.extend(_fmt(hi, TRIALS_HI, NULL_TRIALS_HI, SEED))
    log("")
    log(f"Standard error on a level near 0.05 at {TRIALS_HI} trials: "
        f"{math.sqrt(0.05 * 0.95 / TRIALS_HI):.4f}.")
    log("")

    log("## C. Level-matched: is the deployed STATISTIC weaker, or just stricter?")
    log("")
    log("With a common benign budget the analytic p-value is a strictly increasing function")
    log("of the exceedance total S alone, so the deployed test rejects iff S <= c_analytic and")
    log("the oracle test iff S <= c_oracle: the same rule on the same statistic at different")
    log("cut points. Comparing their powers at face value therefore compares two levels, not")
    log("two tests. The columns below read both at the ORACLE's achieved level.")
    log("")
    log("| m | level oracle | pow 2x oracle | pow 2x deployed, re-cut to that level | "
        "cut | delta |")
    log("|---|---|---|---|---|---|")
    for r in hi:
        p2 = r["power"][2.0]
        log(f"| {r['m']} | {r['level_oracle']:.3f} | {p2['oracle']:.3f} | "
            f"{p2['at_oracle_level']:.3f} | {p2['cut_at_oracle_level']} | "
            f"{p2['at_oracle_level'] - p2['oracle']:+.3f} |")
    log("")
    log("A delta of zero is the expected and correct result: it says the analytic null costs")
    log("nothing in discriminating power and everything in level. The deployed test's lower")
    log("power is bought conservatism, not a worse statistic - and, unlike the oracle, it is")
    log("a level the pipeline can actually claim without knowing the truth it is testing.")
    log("")
    log("The `exact-level` rule below is the best a cut on S can do while honouring alpha on")
    log("this DGP; it brackets how much of the deployed/oracle gap is discreteness.")
    log("")
    log("| m | crit dep. | level dep. | pow 2x dep. | crit exact | level exact | "
        "pow 2x exact | crit oracle | level oracle | pow 2x oracle |")
    log("|---|---|---|---|---|---|---|---|---|---|")
    for r in hi:
        p2 = r["power"][2.0]
        log(f"| {r['m']} | {r['crit_deployed']} | {r['level_deployed']:.3f} | "
            f"{p2['deployed']:.3f} | {r['crit_exact_level']} | {r['level_exact']:.3f} | "
            f"{p2['exact_level']:.3f} | {r['crit_oracle']:.1f} | {r['level_oracle']:.3f} | "
            f"{p2['oracle']:.3f} |")
    log("")

    log("## D. The two cells the paper quotes for the PLANNED design, against what reproduces")
    log("")
    log("`paper/sections/experiments.tex` states that the randomised rule against the analytic")
    log("null \"reaches power 0.51 at an achieved level of 0.025 for m=30, and 0.77 at 0.041")
    log("for the pre-registered m=50\", with nominal tails of 0.031 and 0.044 at those cut")
    log("points, against an oracle's 0.66 at level 0.056 and 0.84 at 0.064. Those numbers had")
    log("no producing artifact before this table. They are the PLANNED design's; section E is")
    log("the design that ran.")
    log("")
    log("| cell | quantity | paper | this run (high precision) | published settings | "
        "verdict |")
    log("|---|---|---|---|---|---|")
    for r in hi:
        if r["m"] not in PAPER_CLAIMS:
            continue
        c, m_ = PAPER_CLAIMS[r["m"]], r["m"]
        p2 = r["power"][2.0]
        pr = next(x for x in pub if x["m"] == m_)
        pr2 = pr["power"][2.0]
        gap_hi, gap_pub = (p2["oracle"] - p2["deployed"],
                           pr2["oracle"] - pr2["deployed"])
        gap_claim = c["oracle_power"] - c["power"]
        vd = {
            "power": ck.verdict(f"D m={m_} deployed power @2x", p2["deployed"],
                                c["power"], _mc_tol(c["power"], TRIALS_HI, 0.02)),
            "level": ck.verdict(f"D m={m_} achieved level", r["level_deployed"],
                                c["level"], _mc_tol(c["level"], TRIALS_HI, 0.005)),
            "nominal": ck.verdict(f"D m={m_} nominal level", r["nominal_deployed"],
                                  c["nominal"], 0.001),
            "opower": ck.verdict(f"D m={m_} oracle power @2x", p2["oracle"],
                                 c["oracle_power"],
                                 _mc_tol(c["oracle_power"], TRIALS_HI, 0.02)),
            "olevel": ck.verdict(f"D m={m_} oracle level", r["level_oracle"],
                                 c["oracle_level"], 0.010),
            "gap": ck.verdict(f"D m={m_} oracle-deployed gap", gap_hi, gap_claim, 0.03),
        }
        log(f"| m={m_} | deployed power @2x | {c['power']:.2f} | {p2['deployed']:.3f} | "
            f"{pr2['deployed']:.3f} | {vd['power']} |")
        log(f"| m={m_} | deployed level, ACHIEVED | {c['level']:.3f} | "
            f"{r['level_deployed']:.3f} (on {NULL_TRIALS_HI} H0 trials "
            f"{r['level_deployed_bignull']:.3f}) | {pr['level_deployed']:.3f} | "
            f"{vd['level']} |")
        log(f"| m={m_} | deployed level, NOMINAL (analytic tail at the cut) | "
            f"{c['nominal']:.3f} | {r['nominal_deployed']:.4f} | "
            f"{pr['nominal_deployed']:.4f} | {vd['nominal']} |")
        log(f"| m={m_} | oracle power @2x | {c['oracle_power']:.2f} | "
            f"{p2['oracle']:.3f} | {pr2['oracle']:.3f} | {vd['opower']} |")
        log(f"| m={m_} | oracle level | {c['oracle_level']:.3f} | "
            f"{r['level_oracle']:.3f} | {pr['level_oracle']:.3f} | {vd['olevel']} |")
        log(f"| m={m_} | power gap oracle-deployed (derived) | {gap_claim:.2f} | "
            f"{gap_hi:.3f} | {gap_pub:.3f} | {vd['gap']} |")
    log("")
    log("Both powers must be quoted WITH a level, because at unequal levels powers are not")
    log("comparable (section C) - and the level to quote is the achieved one, not the analytic")
    log("null's nominal tail, which differs from it by up to a quarter of its own value here.")
    log("")

    # ------------------------------------------------------------------- section E
    pl, rz = designs["planned"], designs["realized"]
    cp, cr = DESIGN_CLAIMS["planned"], DESIGN_CLAIMS["realized"]
    cf, clm = DESIGN_CLAIMS["fixed_cut"], DESIGN_CLAIMS["level_matched"]
    cdec = DESIGN_CLAIMS["decomposition"]
    fc0 = int(cf["cut"])
    log("## E. The design that was planned, and the design that ran")
    log("")
    log("Sections A-D vary one uniform benign budget over 80 targets, which is the experiment")
    log("that was DESIGNED. The confirmatory null control closed at 77 usable targets with six")
    log("short arms, and the analytic null is the convolution of per-target")
    log("BetaBinomial(m_j; 1, N) pmfs, so the cut moves with the whole m-VECTOR and not with n")
    log("alone. Until this section existed the shipped design could not be expressed in this")
    log("script at all, and the paper quoted the planned design's power for six review rounds.")
    log("")
    log(f"Realized m-vector, read from {realized_prov}: n = {len(realized_mv)}, "
        f"{sum(realized_mv)} benign draws, [{_runs(realized_mv)}]. Identical across the "
        f"{', '.join(REALIZED_ARMS)} arms.")
    log(f"Monte-Carlo cells are {TRIALS_DESIGN} trials at each of the seeds "
        f"{', '.join(str(x) for x in DESIGN_SEEDS)}, pooled; the analytic rows are exact.")
    log("")
    log(f"| quantity | {cp['label']} | {cr['label']} |")
    log("|---|---|---|")
    log(f"| targets | {pl['n_targets']} | {rz['n_targets']} |")
    log(f"| benign draws | {pl['draws']:,} | {rz['draws']:,} |")
    log(f"| **deployed cut** | **S <= {pl['cut']}** | **S <= {rz['cut']}** |")
    log(f"| nominal level at the cut | {pl['nominal']:.4f} | {rz['nominal']:.4f} |")
    log(f"| the next cut up | S <= {pl['cut'] + 1} at {pl['nominal_next']:.4f} | "
        f"S <= {rz['cut'] + 1} at {rz['nominal_next']:.4f} |")
    log(f"| E[S] under H0 (analytic) | {pl['expected_h0']:.2f} | {rz['expected_h0']:.2f} |")
    log(f"| mean S under H0 (simulated) | {pl['null_mean']:.2f} | {rz['null_mean']:.2f} |")
    log(f"| achieved level | {pl['level']:.3f} | {rz['level']:.3f} |")
    log(f"| **power vs a two-fold effect** | **{pl['power'][2.0]:.3f}** | "
        f"**{rz['power'][2.0]:.3f}** |")
    log(f"| power vs a three-fold effect | {pl['power'][3.0]:.3f} | {rz['power'][3.0]:.3f} |")
    log("")
    log("Per-seed spread, so the ten-point gap is not read as Monte-Carlo noise:")
    log("")
    log("| design | level by seed | power @2x by seed | power @3x by seed |")
    log("|---|---|---|---|")
    for key in ("planned", "realized"):
        d = designs[key]
        log(f"| {DESIGN_CLAIMS[key]['label']} | "
            + " / ".join(f"{x:.4f}" for x in d["level_by_seed"]) + " | "
            + " / ".join(f"{x:.4f}" for x in d["power_by_seed"][2.0]) + " | "
            + " / ".join(f"{x:.4f}" for x in d["power_by_seed"][3.0]) + " |")
    log("")
    log("### E1. The granularity fact, which is exact")
    log("")
    log("The achievable levels are a ladder on an integer cut, so a design lands on a rung")
    log("rather than on alpha. The realized design's ladder steps from")
    log(f"S <= {rz['cut']} at {rz['nominal']:.4f} straight to S <= {rz['cut'] + 1} at "
        f"{rz['nominal_next']:.4f}, which is already over alpha = {ALPHA}. Nothing")
    log(f"lands between them, so its cut is {rz['cut']} where the planned design's is "
        f"{pl['cut']}. That much is")
    log("exact arithmetic on the analytic null and carries no simulation error.")
    log("")
    log("| design | S <= cut-1 | S <= cut | S <= cut+1 |")
    log("|---|---|---|---|")
    for key in ("planned", "realized"):
        d = designs[key]
        log(f"| {DESIGN_CLAIMS[key]['label']} | {d['cut'] - 1}: {d['nominal_prev']:.4f} | "
            f"**{d['cut']}: {d['nominal']:.4f}** | {d['cut'] + 1}: {d['nominal_next']:.4f} |")
    log("")
    log("### E2. Why a FIXED cut is not a comparison")
    log("")
    log("An earlier version of this section read the two designs at a common cut of "
        f"{fc0} and")
    log("concluded from it that the realized design is the stronger of the two and that the")
    log("whole shortfall is granularity. **That inference was wrong and is retracted here.**")
    log("One integer cut does not mean one test: the two designs have different null")
    log(f"distributions, so at S <= {fc0} they run at different SIZES, and the more permissive")
    log("one is more powerful for free. This is the same error section C exists to warn about")
    log("for the deployed-versus-oracle pair, made across designs instead of across rules.")
    log("")
    log(f"| at a fixed cut of {fc0} | {cp['label']} | {cr['label']} |")
    log("|---|---|---|")
    log(f"| nominal level | {analytic_p(fc0, pl['m_vector']):.4f} | "
        f"{analytic_p(fc0, rz['m_vector']):.4f} |")
    log(f"| achieved level | {pl['level_curve'][fc0]:.4f} | {rz['level_curve'][fc0]:.4f} |")
    log(f"| power vs two-fold | {pl['power_curve'][2.0][fc0]:.3f} | "
        f"{rz['power_curve'][2.0][fc0]:.3f} |")
    log("")
    log(f"The realized design's size at that cut is "
        f"{analytic_p(fc0, rz['m_vector']) / analytic_p(fc0, pl['m_vector']):.2f} times the")
    log("planned design's. The two powers in the last row are measurements and are recorded,")
    log("but no comparison between them is asserted, and the two levels are printed beside")
    log("them because omitting the levels is exactly what made the bad inference invisible.")
    log("")
    log("### E3. Level-matched, which is the comparison that means something")
    log("")
    log("Both designs are cut rules on S, so their attainable (level, power) pairs are the")
    log("vertices of their ladders and the segments between them: a randomised cut mixing")
    log("c and c+1 attains any level in between, with the correspondingly mixed power. Read")
    log("at a COMMON achieved level the two become commensurable, and the realized design is")
    log("the weaker of the two everywhere.")
    log("")
    log("| achieved level | realized power @2x | planned power @2x | planned - realized |")
    log("|---|---|---|---|")
    lm_gaps = []
    for a in LEVEL_GRID:
        prz, ppl = power_at_level(rz, a), power_at_level(pl, a)
        lm_gaps.append(ppl - prz)
        log(f"| {a:.3f} | {prz:.3f} | {ppl:.3f} | {ppl - prz:+.3f} |")
    log("")
    log("### E4. Splitting the drop, and how much of the split survives the ordering")
    log("")
    dec = decompose_drop(pl, rz)
    log(f"The drop runs from {pl['power'][2.0]:.3f} at the planned design's operating point "
        f"(level {pl['level']:.4f})")
    log(f"to {rz['power'][2.0]:.3f} at the realized design's (level {rz['level']:.4f}), a "
        f"total of {dec['total']:.3f}. Two")
    log("things changed at once - the level moved and the experiment shrank - so the split")
    log("between them is path-dependent and both orders are given rather than one being")
    log("passed off as the answer.")
    log("")
    log("| order | granularity (the cut moved) | design (fewer targets, short arms) |")
    log("|---|---|---|")
    log(f"| A: level first, on the planned design | {dec['A']['granularity']:.3f} "
        f"({dec['A']['granularity'] / dec['total']:.0%}) | {dec['A']['design']:.3f} "
        f"({dec['A']['design'] / dec['total']:.0%}) |")
    log(f"| B: design first, at the planned level | {dec['B']['granularity']:.3f} "
        f"({dec['B']['granularity'] / dec['total']:.0%}) | {dec['B']['design']:.3f} "
        f"({dec['B']['design'] / dec['total']:.0%}) |")
    log(f"| symmetric (Shapley) | {dec['granularity']:.3f} "
        f"({dec['granularity'] / dec['total']:.0%}) | {dec['design']:.3f} "
        f"({dec['design'] / dec['total']:.0%}) |")
    log("")
    gran_wins = min(dec["A"]["granularity"] - dec["A"]["design"],
                    dec["B"]["granularity"] - dec["B"]["design"])
    bigger = "granularity" if gran_wins > 0 else "the design change"
    log(f"The larger term under BOTH orders is {bigger}. What is not true is that the other")
    log("term is nothing: the sentence \"the shortfall is not the three missing targets or")
    log("the six short arms\" is false as stated. Fewer targets and shorter arms cost real")
    log(f"power - {dec['B']['design']:.3f} of it at the planned design's own level - and they")
    log("are the smaller share of the drop, not a null share of it.")
    log("")
    mid = designs["n77_uniform"]
    log(f"The design term splits again. An intermediate design of {mid['n_targets']} targets "
        f"at a uniform")
    log(f"m = {PLANNED_M} ({mid['draws']:,} draws, cut S <= {mid['cut']} at "
        f"{mid['nominal']:.4f}) separates the three targets")
    log("the run could not test from the six arms that came up short. Read at each matched")
    log("level:")
    log("")
    log("| achieved level | three lost targets | six short arms | total (planned - realized) |")
    log("|---|---|---|---|")
    lost_terms, short_terms = [], []
    for a in LEVEL_GRID:
        p_pl, p_mid, p_rz = (power_at_level(pl, a), power_at_level(mid, a),
                             power_at_level(rz, a))
        lost_terms.append(p_pl - p_mid)
        short_terms.append(p_mid - p_rz)
        log(f"| {a:.3f} | {p_pl - p_mid:+.3f} | {p_mid - p_rz:+.3f} | {p_pl - p_rz:+.3f} |")
    lost_mean, short_mean = float(np.mean(lost_terms)), float(np.mean(short_terms))
    log("")
    log(f"Averaged over the four levels: {lost_mean:+.3f} for the lost targets and "
        f"{short_mean:+.3f} for the")
    log("short arms. The two sum to the level-matched gap by construction, which is the")
    log("check worth making on any statement of this split: `experiments.tex` currently puts")
    log("both at about 0.02, and 0.02 + 0.02 exceeds the gap it is decomposing. Each term")
    log("here is individually noisy - per level they run 0.006 to 0.020 - so what should be")
    log("read off this table is that both are positive and neither is the whole of it.")
    log("")
    log("A note on E[S]. The realized design's null expects fewer exceedances "
        f"({rz['expected_h0']:.2f} against")
    log(f"{pl['expected_h0']:.2f}) only because {rz['draws']:,} < {pl['draws']:,} benign "
        f"draws, since E[S] = sum_j m_j / (A+1).")
    log("That is less data, not more power, and it must not be offered as a reason the")
    log("realized design is strong.")
    log("")
    log("### E5. Against what the paper and the review record assert")
    log("")
    log("| design | quantity | claim | this run | verdict |")
    log("|---|---|---|---|---|")
    for key in ("planned", "realized"):
        d, c = designs[key], DESIGN_CLAIMS[key]
        lbl = c["label"]
        v_cut = ck.verdict_int(f"E {key} cut", d["cut"], c["cut"])
        v_nom = ck.verdict(f"E {key} nominal level", d["nominal"], c["nominal"], 0.0002)
        v_exp = ck.verdict(f"E {key} E[S]", d["expected_h0"], c["expected_h0"], 0.005)
        v_lvl = ck.verdict(f"E {key} achieved level", d["level"], c["level"],
                           _mc_tol(c["level"], d["n_mc"], 0.005))
        log(f"| {lbl} | deployed cut | S <= {c['cut']} | S <= {d['cut']} | {v_cut} |")
        log(f"| {lbl} | nominal level | {c['nominal']:.4f} | {d['nominal']:.4f} | "
            f"{v_nom} |")
        log(f"| {lbl} | E[S] under H0 | {c['expected_h0']:.2f} | {d['expected_h0']:.2f} | "
            f"{v_exp} |")
        log(f"| {lbl} | achieved level | {c['level']:.3f} | {d['level']:.3f} | "
            f"{v_lvl} |")
        for mult in MULTS:
            v_pow = ck.verdict(f"E {key} power @{mult:g}x", d["power"][mult],
                               c["power"][mult],
                               _mc_tol(c["power"][mult], d["n_mc"], 0.01))
            log(f"| {lbl} | power vs {int(mult)}-fold | {c['power'][mult]:.3f} | "
                f"{d['power'][mult]:.3f} | {v_pow} |")
    v_next_cut = ck.verdict_int("E realized next cut", rz["cut"] + 1, cr["next_cut"])
    v_next_nom = ck.verdict("E realized next nominal level", rz["nominal_next"],
                            cr["next_nominal"], 0.0002)
    log(f"| {cr['label']} | the next cut up | S <= {cr['next_cut']} at "
        f"{cr['next_nominal']:.4f} | S <= {rz['cut'] + 1} at {rz['nominal_next']:.4f} | "
        f"{v_next_cut}, {v_next_nom} |")
    for key, mvk in (("planned", pl["m_vector"]), ("realized", rz["m_vector"])):
        got = analytic_p(fc0, mvk)
        v = ck.verdict(f"E {key} nominal level at the fixed cut {fc0}", got,
                       cf[f"nominal_{key}"], 0.0002)
        log(f"| {DESIGN_CLAIMS[key]['label']} | nominal level at a fixed cut of {fc0} | "
            f"{cf[f'nominal_{key}']:.4f} | {got:.4f} | {v} |")
    ratio = analytic_p(fc0, rz["m_vector"]) / analytic_p(fc0, pl["m_vector"])
    log(f"| both | size ratio at a fixed cut of {fc0} | {cf['ratio']:.2f} | {ratio:.2f} | "
        f"{ck.verdict(f'E size ratio at the fixed cut {fc0}', ratio, cf['ratio'], 0.01)} |")
    for a in LEVEL_GRID:
        for key, d in (("realized", rz), ("planned", pl)):
            got = power_at_level(d, a)
            v = ck.verdict(f"E {key} level-matched power @2x at level {a:.3f}", got,
                           clm[a][key], _mc_tol(clm[a][key], designs[key]["n_mc"], 0.015))
            log(f"| {DESIGN_CLAIMS[key]['label']} | level-matched power @2x at "
                f"{a:.3f} | {clm[a][key]:.3f} | {got:.3f} | {v} |")
    v_sign = ck.verdict_int("E realized weaker at every matched level",
                            1 if min(lm_gaps) > 0 else 0, 1)
    log(f"| both | level-matched gap positive at all {len(LEVEL_GRID)} levels | yes | "
        f"{'yes' if min(lm_gaps) > 0 else 'NO'} | {v_sign} |")
    log(f"| both | drop, planned op point to realized op point | {cdec['total']:.3f} | "
        f"{dec['total']:.3f} | "
        f"{ck.verdict('E total drop', dec['total'], cdec['total'], 0.02)} |")
    v_gran = ck.verdict("E granularity term (symmetric)", dec["granularity"],
                        cdec["granularity"], 0.020)
    log(f"| both | granularity share (symmetric) | {cdec['granularity']:.3f} | "
        f"{dec['granularity']:.3f} | {v_gran} |")
    v_des = ck.verdict("E design term (symmetric)", dec["design"], cdec["design"], 0.020)
    log(f"| both | design share (symmetric) | {cdec['design']:.3f} | {dec['design']:.3f} | "
        f"{v_des} |")
    csp = DESIGN_CLAIMS["design_split"]
    v_lost = ck.verdict("E lost-targets term, level-matched mean", lost_mean,
                        csp["lost_targets"], 0.015)
    v_short = ck.verdict("E short-arms term, level-matched mean", short_mean,
                         csp["short_arms"], 0.015)
    v_pos = ck.verdict_int("E both design sub-terms cost power",
                           1 if min(lost_mean, short_mean) > 0 else 0, 1)
    log(f"| both | three lost targets, level-matched mean | {csp['lost_targets']:.3f} | "
        f"{lost_mean:.3f} | {v_lost} |")
    log(f"| both | six short arms, level-matched mean | {csp['short_arms']:.3f} | "
        f"{short_mean:.3f} | {v_short} |")
    log("| both | both sub-terms cost power (each > 0) | yes | "
        f"{'yes' if min(lost_mean, short_mean) > 0 else 'NO'} | {v_pos} |")
    v_order = ck.verdict_int("E granularity larger than design under both orders",
                             1 if gran_wins > 0 else 0, 1)
    log("| both | granularity is the larger term under BOTH orders | yes | "
        f"{'yes' if gran_wins > 0 else 'NO'} | {v_order} |")
    log("")
    log("A non-rejection in this campaign has to be read against the realized column. The")
    log("planned column is what the design promised and is quoted in sections A-D because the")
    log("paper still states it as the design's figure; it is not what the run can see.")
    log("")
    log("### E6. What every number above is conditional on")
    log("")
    log(f"All of it is computed at the attacker budget A = {N_ATTACK}, which")
    log("`experiments.tex` calls an *upper* bound on a parameter it says is not identified")
    log("below 41 and reports the verdict across. The cut is very sensitive to it:")
    log("")
    log("| A | planned cut | nominal | realized cut | nominal |")
    log("|---|---|---|---|---|")
    for a_budget in (181, 121, 90, 41):
        cpl = _crit_at_budget(planned_mv, a_budget)
        crz = _crit_at_budget(realized_mv, a_budget)
        log(f"| {a_budget} | {cpl[0]} | {cpl[1]:.4f} | {crz[0]} | {crz[1]:.4f} |")
    log("")
    log("The power figures are therefore conditional on the top of the admissible range, and")
    log("the paper states them without that condition. This is a scope statement, not a")
    log("finding against any number above: nothing in this script inherits a constant from a")
    log(f"derivation whose other outputs were refuted. In particular A={N_ATTACK} is a")
    log("recorded evaluation count, not the A=41 scalar that heavy review 2 section 3.3")
    log("showed to be a Jensen error, and 41 appears nowhere in this script's inputs.")
    log("")

    log("## F. What this script fails on")
    log("")
    if ck.failures:
        log(f"**{len(ck.failures)} pinned claim(s) disagree with this run.** Each is either a")
        log("stale constant here or an error in the committed paper, and the two are told")
        log("apart by re-deriving the quantity, never by widening the tolerance:")
        log("")
        for f in ck.failures:
            log(f"  - {f}")
    else:
        log("Nothing. Every claim pinned in `PAPER_CLAIMS` and `DESIGN_CLAIMS` reproduces")
        log("within tolerance, and the realized m-vector on disk still matches")
        log("`REALIZED_M_VECTOR`.")
    log("")
    log("The checks that run on every invocation, any of which returns a non-zero exit:")
    log("")
    log("  1. the split DGP is stream-identical to `power_sim_randomized.one_target`;")
    log("  2. the analytic p-value depends on the exceedance TOTAL only, at a uniform m and")
    log("     at the realized m-vector, which is what licenses reducing both tests to a cut;")
    log("  3. the realized m-vector on disk matches `REALIZED_M_VECTOR`, and is the same in")
    log("     all three scored arms (a hard stop, not a table row);")
    log("  4. every number in `PAPER_CLAIMS` (section D) and `DESIGN_CLAIMS` (section E),")
    log("     including the level-matched comparison, the sign of its gap at every level,")
    log("     and both terms of the decomposition.")
    log("")

    log("## Reproduction")
    log("")
    log("```")
    log(".venv/Scripts/python.exe scripts/power_sim_deployed.py")
    log(".venv/Scripts/python.exe scripts/power_sim_deployed.py --out-dir <dir>")
    log("```")
    log("`--out-dir` writes this report and the headroom mirror somewhere other than")
    log("`results/`, for re-running the checks without touching a committed artifact.")

    out = out_dir / "power_deployed_vs_oracle.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    if ck.failures:
        print(f"\n[FAIL] {len(ck.failures)} pinned claim(s) disagree with this run:",
              file=sys.stderr)
        for f in ck.failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("[ok] every pinned claim reproduces", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
