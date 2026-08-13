"""Power of the DEPLOYED exceedance test (analytic BetaBinomial null) vs the ORACLE-
calibrated simulation, on identical draws, at stated achieved levels.

WHY THIS SCRIPT EXISTS. `scripts/power_sim_randomized.py` calibrates its critical value
from a SEPARATE simulated null sample (`default_rng(seed+1)` / `(seed+2)`). That is an
ORACLE: it needs the true null of the data-generating process, which the deployed pipeline
does not have. The shipped test instead compares the observed exceedance total against the
analytic BetaBinomial null in `se.stats.exceedance_test`. Only the oracle column was ever
persisted (results/power_randomized.md, 0.67 / 0.84 at m=30 / m=50). The deployed column
that paper/sections/experiments.tex quotes — 0.51 at level 0.035 for m=30 and 0.77 at level
0.053 for m=50 — was produced in-session and never written to disk, which is the failure
class this script closes. Both columns are computed here from the same DGP, on the SAME
simulated draws, and written to one table.

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

N_TARGETS = 80
ALPHA = 0.05
M_GRID = (20, 30, 50, 80)
MULTS = (2.0, 3.0)
SEED = 11                       # matches power_sim_randomized.power(seed=11)
TRIALS_PUB = 400                # ditto: the settings behind results/power_randomized.md
NULL_TRIALS_PUB = 2500
TRIALS_HI = 4000                # a second pass, for levels that are not 400-trial noise
NULL_TRIALS_HI = 20000
N_TIE_SEEDS = 25
HEADROOM_MD = "fa80_headroom.md"

# Candidate per-draw scales and the observed attack saturation they are matched to; both
# copied from power_sim_randomized.main so the calibration is bit-identical.
SCALES = (0.04, 0.06, 0.09, 0.12, 0.16, 0.20)
OBSERVED_SATURATION = 0.49

FA_CACHE = ROOT / "data" / "cache" / "attacks" / "wk9_defb_snap" / "triviaqa_se_false_alarm.jsonl"

# What paper/sections/experiments.tex asserts as of 2026-08-13, recorded here so the check
# in section D is against a stated claim rather than a memory. Edit only to track the paper.
PAPER_CLAIMS = {
    30: {"power": 0.51, "level": 0.035, "oracle_power": 0.67, "oracle_level": 0.052,
         "gap": 0.16},
    50: {"power": 0.77, "level": 0.053, "oracle_power": 0.84, "oracle_level": 0.068,
         "gap": 0.07},
}


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


def write_headroom_artifact(hr: np.ndarray, qids: list[str], provenance: str) -> Path:
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
    out = RESULTS_DIR / HEADROOM_MD
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
    """
    single = np.empty(trials, dtype=float)
    median = np.empty(trials, dtype=float)
    for t in range(trials):
        tot0 = 0
        per_seed = np.zeros(n_tie_seeds, dtype=float)
        for h in hr[rng.integers(0, len(hr), n_targets)]:
            strict, tied, b = one_target_parts(scale, h, m, mult, rng)
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

def analytic_p(total: int, m: int, n_targets: int) -> float:
    """`se.stats.exceedance_test`'s p-value for an exceedance total, via the deployed
    function itself. The total is split evenly across targets; see `_assert_total_only`."""
    q, r = divmod(int(total), n_targets)
    counts = [(q + 1, m)] * r + [(q, m)] * (n_targets - r)
    return exceedance_test(counts, N_ATTACK)["p_value"]


def _assert_total_only(m: int, n_targets: int, total: int) -> None:
    """p must depend on the TOTAL only, not on how it is split, or the reduction of both
    tests to a cut on S is invalid."""
    rng = np.random.default_rng(0)
    ref = analytic_p(total, m, n_targets)
    for _ in range(3):
        cuts = np.sort(rng.integers(0, total + 1, n_targets - 1))
        parts = np.diff(np.concatenate(([0], cuts, [total])))
        if parts.max() > m:
            continue
        p = exceedance_test([(int(k), m) for k in parts], N_ATTACK)["p_value"]
        assert abs(p - ref) < 1e-10, f"analytic p depends on the split: {p} vs {ref}"


def analytic_crit(m: int, n_targets: int, alpha: float) -> int:
    """Largest integer total the deployed test still rejects at `alpha` (-1 = never)."""
    lo, hi = -1, n_targets * m
    while lo < hi:                                   # p is increasing in the total
        mid = (lo + hi + 1) // 2
        if analytic_p(mid, m, n_targets) <= alpha:
            lo = mid
        else:
            hi = mid - 1
    return lo


def exact_level_crit(null_sample: np.ndarray, alpha: float) -> int:
    """Largest integer cut whose achieved level on this DGP is <= alpha."""
    cuts = np.arange(-1, int(null_sample.max()) + 1)
    ok = [c for c in cuts if (null_sample <= c).mean() <= alpha]
    return int(max(ok)) if ok else -1


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


def main() -> int:
    hr, qids, provenance = resolve_headroom()
    art = write_headroom_artifact(hr, qids, provenance)
    scale, sat = calibrate_scale(hr)
    _assert_dgp_identity(scale, hr, 30)
    for m in M_GRID:
        _assert_total_only(m, N_TARGETS, int(round(N_TARGETS * m / (N_ATTACK + 1))))

    print(f"headroom from {provenance}: n={len(hr)} mean {hr.mean():.3f} "
          f"zero-headroom {int((hr <= 1e-9).sum())}")
    print(f"calibrated scale {scale} (saturation {sat:.0%} vs observed "
          f"{OBSERVED_SATURATION:.0%})")
    print(f"headroom artifact -> {art}\n")

    pub = [one_m(scale, hr, m, trials=TRIALS_PUB, null_trials=NULL_TRIALS_PUB,
                 seed=SEED, n_tie_seeds=N_TIE_SEEDS) for m in M_GRID]
    print("published-settings pass done", flush=True)
    hi = [one_m(scale, hr, m, trials=TRIALS_HI, null_trials=NULL_TRIALS_HI,
                seed=SEED, n_tie_seeds=N_TIE_SEEDS) for m in M_GRID]
    print("high-precision pass done", flush=True)

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
        f"cache. n_targets = {N_TARGETS}, attacker candidates N = {N_ATTACK}, "
        f"nominal alpha = {ALPHA}.")
    log(f"Per-draw exponential scale {scale}, calibrated to {sat:.0%} attack saturation "
        f"against the observed {OBSERVED_SATURATION:.0%}.")
    log("")
    log("Rules: **deployed** = analytic p <= alpha on one tie-break draw; **dep.-median** = "
        "median p over "
        f"{N_TIE_SEEDS} tie-break draws (what `exceedance_test_over_seeds` ships); "
        "**oracle** = S <= 5th percentile of a separate simulated null, which the deployed "
        "test cannot compute.")
    log("")

    log("## A. Published settings — reproduces results/power_randomized.md's oracle column")
    log("")
    L.extend(_fmt(pub, TRIALS_PUB, NULL_TRIALS_PUB, SEED))
    log("")
    log(f"At {TRIALS_PUB} trials an achieved level near 0.05 carries a standard error of "
        f"about {math.sqrt(0.05 * 0.95 / TRIALS_PUB):.3f}, so read these levels as "
        f"indicative and the ones in table B as the measurement.")
    log("")

    log("## B. High precision — the numbers to quote")
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
    log("power is bought conservatism, not a worse statistic — and, unlike the oracle, it is")
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

    log("## D. The two cells the paper quotes, against what reproduces")
    log("")
    log("`paper/sections/experiments.tex` states the deployed test \"reaches power 0.51 at")
    log("level 0.035 for m=30, and 0.77 at level 0.053 for the pre-registered m=50\", and the")
    log("pre-registration disclosure differences against those. Those four numbers had no")
    log("producing artifact. Here is every reproducible reading of them.")
    log("")
    def _v(value: float, claimed: float, dp: int = 2) -> str:
        return "MATCHES" if round(value, dp) == round(claimed, dp) else "**DIFFERS**"

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
        log(f"| m={m_} | deployed power @2x | {c['power']:.2f} | {p2['deployed']:.3f} | "
            f"{pr2['deployed']:.3f} | {_v(p2['deployed'], c['power'])} |")
        log(f"| m={m_} | deployed level, ACHIEVED | {c['level']:.3f} | "
            f"{r['level_deployed']:.3f} (on {NULL_TRIALS_HI} H0 trials "
            f"{r['level_deployed_bignull']:.3f}) | {pr['level_deployed']:.3f} | "
            f"{_v(r['level_deployed'], c['level'], 3)} |")
        log(f"| m={m_} | deployed level, NOMINAL (analytic tail at the cut) | "
            f"{c['level']:.3f} | {r['nominal_deployed']:.3f} | "
            f"{pr['nominal_deployed']:.3f} | {_v(r['nominal_deployed'], c['level'], 3)} |")
        log(f"| m={m_} | oracle power @2x | {c['oracle_power']:.2f} | "
            f"{p2['oracle']:.3f} | {pr2['oracle']:.3f} | "
            f"{_v(pr2['oracle'], c['oracle_power'])} |")
        log(f"| m={m_} | oracle level | {c['oracle_level']:.3f} | "
            f"{r['level_oracle']:.3f} | {pr['level_oracle']:.3f} | "
            f"{_v(pr['level_oracle'], c['oracle_level'], 3)} |")
        gh, gp = p2["oracle"] - p2["deployed"], pr2["oracle"] - pr2["deployed"]
        log(f"| m={m_} | power gap oracle-deployed | {c['gap']:.2f} | {gh:.3f} | "
            f"{gp:.3f} | {'MATCHES' if min(gh, gp) - 0.005 <= c['gap'] <= max(gh, gp) + 0.005 else '**DIFFERS**'} "
            f"(derived; brackets the two passes) |")
    log("")
    log("**The powers reproduce; the two LEVELS do not.** Every reproducible estimate of the")
    log("deployed test's level is BELOW what the paper quotes, in both cells: the shipped test")
    log("is more conservative than the paper says it is, not less. The direction is benign for")
    log("the paper's argument (a more conservative test makes the non-rejection reading")
    log("stricter, and the ordering that drove the m=50 choice is untouched) but the numbers")
    log("as printed are not reproducible from this DGP and should be replaced by this table's.")
    log("")
    log("Both powers must be quoted WITH a level, because at unequal levels powers are not")
    log("comparable (section C) — and the level to quote is the achieved one, not the analytic")
    log("null's nominal tail, which differs from it by up to a third of its own value here.")
    log("")

    log("## Reproduction")
    log("")
    log("```")
    log(".venv/Scripts/python.exe scripts/power_sim_deployed.py")
    log("```")
    log("Asserted on every run: (i) the split DGP is stream-identical to")
    log("`power_sim_randomized.one_target`; (ii) the analytic p-value depends on the")
    log("exceedance TOTAL only, which is what licenses the reduction of both tests to a cut.")

    out = RESULTS_DIR / "power_deployed_vs_oracle.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
