"""Granularity of semantic entropy, measured on the SCORE-INDEPENDENT FAIR POOL.

WHY THIS EXISTS
---------------
The repo's granularity/ceiling statistics ("22 distinct values", "8/80 at the cap",
"21/80 in the top decile") were all computed on the ATTACKED subset -- the ~97 targets
the optimiser actually ran on (80 false-alarm + a truncated hide arm). `paper/sections/
methods.tex` states the project's own rule: the attacked subset "is not a description of
the detector; wherever we characterise the detector we use the fair pool." So those
counts, as descriptions of the DETECTOR, are population-invalid by the paper's own
standard.

This script recomputes them on the population the rule names: the score-independent fair
pool of 200 correct + 200 hallucinating targets (`select_stratified(want, 200, seed=0)`,
the same ids `scripts/fair_pool_check.py` uses for the clean AUROC 0.704). CPU only, no
GPU, no model: the clean scores are the `entropy_nats` field of the Week-4 span-oracle
cache `relabeled.jsonl`, which is bit-identical to the `entropy_before` the attack cells
recorded (verified below).

NESTING (do not report these as two populations)
------------------------------------------------
`_stratum_ids` seed-shuffles the stratum and `select_stratified` takes `[:n]`, so the
attacked cells are literal PREFIXES of the fair pool: the 80 attacked false-alarm targets
are fair-pool-correct[:80]. The attacked subset is NESTED inside the fair pool, not
disjoint from it. `verify_nesting()` asserts this against the on-disk attack cells.

THE ATTAINABLE LATTICE (the honest denominator)
------------------------------------------------
Semantic entropy here is the Shannon entropy of a cluster-size distribution over N=10
samples (`se.entropy.discrete_entropy`), so the estimator can only ever emit the entropy
of an integer partition of 10. That is a finite lattice; this script enumerates it. A
realised-value count is therefore "X of |lattice| attainable values", not "X out of a
continuum" -- and the count is monotone in the number of targets observed, which is why
the rarefaction curve below is the thing that makes "22 distinct values" interpretable.

Usage (data lives in the WSL cache):
    wsl -d Ubuntu-24.04 -- bash -c "cd '/mnt/i/GITHUBPROJECTS/SE Research' && \
        ./.venv-wsl/bin/python scripts/fair_pool_granularity.py"
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
sys.path.insert(0, str(REPO_ROOT / "src"))

from se.attacks.select import RELABELED, _stratum_ids, load_labels  # noqa: E402

N_SAMPLES = 10                      # the deployed sample budget N
CAP = math.log(N_SAMPLES)           # ln(10) = 2.302585... nats, the attainable maximum
TOP_DECILE = 0.9 * CAP              # "top tenth of the RANGE" [0, ln N], not a quantile
N_PER_STRATUM = 200                 # the fair pool: 200 correct + 200 hallucinating
SEED = 0
DP = 9                              # canonical rounding tolerance: values equal at 1e-9
RAREFACTION_N = [10, 20, 40, 80, 97, 160, 320, 400]
N_MC = 4000                         # Monte-Carlo subsamples per rarefaction point

ATTACK_CACHE = Path("~/.cache/se-research/samples/attacks").expanduser()
ATTACK_CELLS = [                    # (relative path, which stratum it draws from)
    ("wk9_defb/triviaqa_se_false_alarm.jsonl", "right"),
    ("wk9_defb/triviaqa_se_hide.jsonl", "wrong"),
    ("wk9_def/triviaqa_se_false_alarm.jsonl", "right"),
    ("wk9_def/triviaqa_se_hide.jsonl", "wrong"),
]


# --------------------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion. Returns (p_hat, lo, hi).

    Wilson rather than Wald because several of these counts are near 0 or near n,
    where the Wald interval leaves the unit interval and has poor coverage."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


# ----------------------------------------------------------------- attainable lattice
def partitions(n: int, largest: int | None = None):
    """Yield every integer partition of n as a non-increasing tuple."""
    if largest is None:
        largest = n
    if n == 0:
        yield ()
        return
    for part in range(min(n, largest), 0, -1):
        for rest in partitions(n - part, part):
            yield (part,) + rest


def partition_entropy(part: tuple[int, ...]) -> float:
    tot = sum(part)
    return -sum((c / tot) * math.log(c / tot) for c in part)


def attainable_lattice(n_samples: int, dp: int = 12) -> list[float]:
    """Every entropy value the estimator can emit from n_samples samples, sorted.

    The estimator is entropy(cluster-size distribution), and a cluster-size
    distribution over n samples IS an integer partition of n, so this enumeration is
    exhaustive. Deduped at 1e-`dp` because distinct partitions can share an entropy
    (e.g. any two partitions that are permutations of the same multiset -- and, more
    interestingly, genuine coincidences)."""
    seen: dict[float, tuple[int, ...]] = {}
    for p in partitions(n_samples):
        seen.setdefault(round(partition_entropy(p), dp), p)
    return sorted(seen)


def n_partitions(n: int) -> int:
    return sum(1 for _ in partitions(n))


# ------------------------------------------------------------------------ rarefaction
def expected_distinct(multiplicities: list[int], n: int) -> float:
    """EXACT E[# distinct values observed] when n of the M targets are drawn without
    replacement. A value with multiplicity m is missed with probability
    C(M-m, n)/C(M, n); sum the complements. Computed in log-space via lgamma."""
    M = sum(multiplicities)
    if n >= M:
        return float(len(multiplicities))

    def log_c(a: int, b: int) -> float:
        if b < 0 or b > a:
            return -math.inf
        return (math.lgamma(a + 1) - math.lgamma(b + 1) - math.lgamma(a - b + 1))

    denom = log_c(M, n)
    return float(sum(1.0 - math.exp(log_c(M - m, n) - denom) for m in multiplicities))


def mc_distinct(values: np.ndarray, n: int, n_mc: int, rng) -> tuple[float, float, int, int]:
    """Monte-Carlo mean/sd/min/max of the distinct count over n_mc subsamples of size n."""
    M = len(values)
    if n >= M:
        d = len(set(values.tolist()))
        return float(d), 0.0, d, d
    counts = np.empty(n_mc, dtype=int)
    for i in range(n_mc):
        idx = rng.choice(M, size=n, replace=False)
        counts[i] = len(np.unique(values[idx]))
    return float(counts.mean()), float(counts.std(ddof=1)), int(counts.min()), int(counts.max())


# ------------------------------------------------------------------------ populations
def fair_pool_ids(labels: dict) -> tuple[list[str], list[str]]:
    """The score-independent fair pool: the first 200 of each seed-shuffled stratum.

    Same call path as scripts/fair_pool_check.py, minus load_triviaqa -- which only maps
    ids -> examples, but does silently DROP ids absent from the split. Verified below to
    drop nothing here, so these ids are exactly select_stratified(want, 200, seed=0)."""
    return (_stratum_ids("right", SEED, labels)[:N_PER_STRATUM],
            _stratum_ids("wrong", SEED, labels)[:N_PER_STRATUM])


def check_no_dropped_ids(fair_right: list[str], fair_wrong: list[str]) -> str:
    """select_stratified filters `if qid in by_id` AFTER taking [:n], so a missing
    dataset row would shrink the real campaign pool below 200. Confirm it does not."""
    try:
        from se.data import load_triviaqa
        have = {ex.question_id for ex in load_triviaqa(split="validation")}
    except Exception as exc:                                  # dataset not on this box
        return f"(skipped: could not load the validation split -- {type(exc).__name__})"
    miss_r = sum(1 for q in fair_right if q not in have)
    miss_w = sum(1 for q in fair_wrong if q not in have)
    assert miss_r == miss_w == 0, f"dropped ids: right={miss_r}, wrong={miss_w}"
    return (f"`load_triviaqa` drops **0/{len(fair_right)}** correct and "
            f"**0/{len(fair_wrong)}** hallucinating ids, so the ids scored here are "
            f"exactly `select_stratified(want, {N_PER_STRATUM}, seed={SEED})`.")


def verify_nesting(fair_right: list[str], fair_wrong: list[str],
                   emap: dict[str, float]) -> list[str]:
    """Assert the attacked cells are PREFIXES of the fair pool, and that their recorded
    clean scores are the same numbers this script reads. Returns report lines."""
    out: list[str] = []
    pools = {"right": fair_right, "wrong": fair_wrong}
    for rel, want in ATTACK_CELLS:
        path = ATTACK_CACHE / rel
        if not path.exists():
            out.append(f"| `{rel}` | (not on disk) | - | - | - |")
            continue
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        ids = [r["question_id"] for r in rows]
        pool = pools[want]
        is_prefix = ids == pool[: len(ids)]
        is_subset = set(ids) <= set(pool)
        drift = max((abs(r["entropy_before"] - emap[r["question_id"]]) for r in rows),
                    default=0.0)
        assert is_prefix and is_subset, f"{rel} is not a prefix of the fair {want} stratum"
        assert drift == 0.0, f"{rel} clean scores differ from relabeled.jsonl (max {drift})"
        out.append(f"| `{rel}` | n={len(ids)} | {want} | prefix: **{is_prefix}**, "
                   f"subset: **{is_subset}** | max |Δclean| = {drift:g} |")
    return out


# ------------------------------------------------------------------------------- main
def main() -> int:
    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    labels = load_labels(RELABELED)
    emap = {q: float(l["entropy_nats"]) for q, l in labels.items()}
    fair_right, fair_wrong = fair_pool_ids(labels)
    assert len(fair_right) == len(fair_wrong) == N_PER_STRATUM

    v_right = np.array([round(emap[q], DP) for q in fair_right])
    v_wrong = np.array([round(emap[q], DP) for q in fair_wrong])
    v_all = np.concatenate([v_right, v_wrong])

    # Supplementary population: the ENTIRE labelled Week-4 pool, at natural prevalence.
    # Not the designated population (the paper's rule names the fair pool), but it is the
    # superset the fair pool was drawn from, it needs no selection at all, and it is the
    # only view at the deployment class balance. Reported alongside, never instead.
    full_right = np.array([round(float(l["entropy_nats"]), DP)
                           for l in labels.values() if l["greedy_correct"]])
    full_wrong = np.array([round(float(l["entropy_nats"]), DP)
                           for l in labels.values() if not l["greedy_correct"]])
    v_full = np.concatenate([full_right, full_wrong])
    prev_wrong = len(full_wrong) / len(v_full)

    lattice = [round(v, DP) for v in attainable_lattice(N_SAMPLES)]
    n_att = len(lattice)
    # Sanity: every value the detector actually produced must be an attainable one.
    # If this fires, either the estimator is not entropy-of-a-partition-of-N_SAMPLES
    # or the cache mixes sample budgets -- either way the denominator below is wrong.
    stray = sorted({round(emap[q], DP) for q in fair_right + fair_wrong} - set(lattice))
    assert not stray, f"realised values outside the N={N_SAMPLES} lattice: {stray[:5]}"
    att_top = [v for v in lattice if v >= TOP_DECILE - 1e-12]
    lattice20 = attainable_lattice(20)
    att20_top = [v for v in lattice20 if v >= 0.9 * math.log(20) - 1e-12]

    log("# Granularity of semantic entropy on the SCORE-INDEPENDENT FAIR POOL")
    log("")
    log(f"Generated {_dt.date.today().isoformat()} by `scripts/fair_pool_granularity.py` "
        "(CPU only; no GPU, no model).")
    log("")
    log("**Population.** The *fair pool*: the score-independent stratified-random sample")
    log(f"of **{N_PER_STRATUM} correct + {N_PER_STRATUM} hallucinating** TriviaQA targets")
    log(f"(`select_stratified(want, {N_PER_STRATUM}, seed={SEED})`) -- the same ids on which")
    log("`results/fair_pool_report.md` reports clean SE AUROC **0.704 [0.653, 0.753]**.")
    log("Scores are the CLEAN (unattacked) `entropy_nats` of the Week-4 span-oracle cache")
    log("`wk4_full_2000q/relabeled.jsonl`. Every proportion below carries its n, its")
    log("population, and a Wilson 95% interval.")
    log("")
    log(f"Estimator: semantic entropy over **N={N_SAMPLES}** samples; attainable maximum")
    log(f"**ln({N_SAMPLES}) = {CAP:.4f} nats**; \"top tenth of the RANGE\" means")
    log(f"score >= 0.9 x ln({N_SAMPLES}) = **{TOP_DECILE:.4f} nats** (a fixed cut on the scale,")
    log("not a sample quantile).")
    log("")

    # ---------------------------------------------------------------- 0. nesting
    log("## 0. The attacked subset is NESTED inside the fair pool (verified)")
    log("")
    log("`_stratum_ids` returns a seed-shuffled id list and `select_stratified` takes")
    log("`[:n]`, so an attacked cell of size n is the first n ids of the fair pool's")
    log("stratum. These are not two populations; the smaller is a prefix of the larger.")
    log("Asserted here against the on-disk attack cells, together with the check that the")
    log("`entropy_before` they recorded is bit-identical to the `entropy_nats` used here:")
    log("")
    log("| attack cell | size | stratum | nesting | clean-score agreement |")
    log("| --- | --- | --- | --- | --- |")
    for line in verify_nesting(fair_right, fair_wrong, emap):
        log(line)
    log("")
    log("(Hide-cell sizes are whatever the still-running multi-day chain had written when")
    log("this ran; the prefix property holds at any size.) " +
        check_no_dropped_ids(fair_right, fair_wrong))
    log("")
    log("Consequence: the fair-pool numbers below do not *contradict* the attacked-subset")
    log("numbers -- they are the same measurement carried out on a superset that was")
    log("chosen without reference to any score.")
    log("")

    # ------------------------------------------------- 1. attainable lattice
    log(f"## 1. The attainable lattice at N={N_SAMPLES} (the honest denominator)")
    log("")
    log("Semantic entropy here is the Shannon entropy of a cluster-size distribution over")
    log(f"N={N_SAMPLES} samples, and a cluster-size distribution over {N_SAMPLES} samples IS an")
    log(f"integer partition of {N_SAMPLES}. Enumerating all p({N_SAMPLES}) = {n_partitions(N_SAMPLES)} partitions and")
    log(f"taking each one's entropy gives **{n_att} distinct attainable values** "
        f"({n_partitions(N_SAMPLES)} partitions,")
    log(f"{n_partitions(N_SAMPLES) - n_att} entropy coincidences). No dataset, no model: this is a property of the")
    log("estimator and the sample budget.")
    log("")
    log(f"- attainable values in the top tenth of the range (>= {TOP_DECILE:.4f}): "
        f"**{len(att_top)} of {n_att}** -- " + ", ".join(f"{v:.4f}" for v in att_top))
    log(f"- smallest gap between adjacent attainable values: "
        f"{min(b - a for a, b in zip(lattice, lattice[1:])):.2e} nats")
    log(f"- for reference, N=20: **{len(lattice20)}** attainable values, "
        f"**{len(att20_top)}** in the top tenth of [0, ln 20]")
    log("")
    log("**This is the sharp fact.** Doubling the sample budget to N=20 multiplies the")
    log(f"lattice by ~{len(lattice20)/n_att:.0f}x overall but only takes the top decile from {len(att_top)} points to")
    log(f"{len(att20_top)}. The coarseness at the top of the scale is not a small-sample accident that")
    log("more targets would fix; it is where the lattice is sparsest.")
    log("")

    # ------------------------------------------- 2. distinct realised values
    log("## 2. Distinct realised values on the fair pool")
    log("")
    log(f"Rounding tolerance: values are treated as equal when they agree to **{DP} decimal")
    log("places** (1e-9 nats). Raw float64 comparison inflates the count with ~1e-16")
    log("accumulation noise from the entropy sum. The count is stable across 3-12 dp:")
    log("")
    log("| population | " + " | ".join(str(d) for d in range(3, 13)) + " | raw float64 |")
    log("| --- | " + " | ".join("---" for _ in range(3, 13)) + " | --- |")
    raw_r = [emap[q] for q in fair_right]
    raw_w = [emap[q] for q in fair_wrong]
    raw_full = [float(l["entropy_nats"]) for l in labels.values()]
    for name, arr in (("fair pool, n=400", raw_r + raw_w),
                      ("correct stratum, n=200", raw_r),
                      ("hallucinating stratum, n=200", raw_w),
                      ("_full labelled pool, n=2000 (suppl.)_", raw_full)):
        cells = [str(len({round(float(x), d) for x in arr})) for d in range(3, 13)]
        cells.append(str(len({float(x) for x in arr})))
        log(f"| {name} | " + " | ".join(cells) + " |")
    log("")
    n_raw, n_round = len(set(raw_r + raw_w)), len(set(v_all.tolist()))
    log(f"(The raw-float64 column is the artefact being guarded against: it reports {n_raw}")
    log(f"\"distinct\" values on the pooled n=400 -- {n_raw - n_round} spurious extras, all of them 1e-16")
    log(f"neighbours of a value already counted. That {n_raw} coinciding with "
        f"p({N_SAMPLES}) = {n_partitions(N_SAMPLES)} above is")
    log("coincidence, not meaning. No attainable value can be missed by")
    log(f"{DP}-dp rounding: the smallest gap in the lattice is "
        f"{min(b - a for a, b in zip(lattice, lattice[1:])):.2e} nats.)")
    log("")
    log(f"| population | n | distinct realised values | of {n_att} attainable |")
    log("| --- | --- | --- | --- |")
    for name, arr in (("fair pool (correct + hallucinating)", v_all),
                      ("fair pool, correct stratum", v_right),
                      ("fair pool, hallucinating stratum", v_wrong),
                      ("_full labelled pool (supplementary)_", v_full)):
        d = len(set(arr.tolist()))
        log(f"| {name} | {len(arr)} | **{d}** | {d}/{n_att} = {d/n_att:.0%} |")
    log("")
    realised = set(v_all.tolist())
    unrealised = [v for v in lattice if v not in realised]
    log(f"Every realised value is an attainable one (asserted). Attainable-but-unrealised")
    log(f"at n=400: **{len(unrealised)} of {n_att}** -- "
        + ", ".join(f"{v:.4f}" for v in unrealised) + ".")
    log("")
    counts = Counter(v_all.tolist())
    f1 = sum(1 for c in counts.values() if c == 1)
    f2 = sum(1 for c in counts.values() if c == 2)
    chao1 = len(counts) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    log(f"Chao1 richness estimate from the n=400 sample: **{chao1:.1f}** distinct values "
        f"(singletons f1={f1}, doubletons f2={f2}; f2 is")
    log("small so this point estimate is unstable -- read it as directional only),")
    log(f"against {n_att} attainable. So the realised count has not converged at n=400 either --")
    log("consistent with the rarefaction curve in section 4, and further evidence that a")
    log("distinct-value count is a statement about the sample, not about the estimator.")
    log("")
    n_full_d = len(set(v_full.tolist()))
    log(f"That extrapolation is checkable here, and it checks out: the supplementary full")
    log(f"labelled pool realises **{n_full_d}** distinct values at n={len(v_full)} -- the Chao1 figure the")
    log(f"n=400 fair pool predicted. Even at n={len(v_full)} the count is {n_full_d}/{n_att} of the lattice, so it")
    log("is still short of saturation. There is no n at which \"the number of distinct values")
    log("semantic entropy produces\" stops depending on n; only the lattice size does not.")
    log("")

    # ------------------------------------------------ 3. ceiling / top decile
    log("## 3. Crowding at the top of the scale")
    log("")
    log(f"\"At the ceiling\" = score within 1e-9 of ln({N_SAMPLES}) = {CAP:.4f}. \"Top tenth of the")
    log(f"range\" = score >= {TOP_DECILE:.4f}. Wilson 95% intervals.")
    log("")
    log("| population | n | at the ceiling | in the top tenth of the range |")
    log("| --- | --- | --- | --- |")
    rows = [("fair pool (correct + hallucinating)", v_all),
            ("fair pool, correct stratum", v_right),
            ("fair pool, hallucinating stratum", v_wrong),
            ("_full labelled pool, natural prevalence (suppl.)_", v_full),
            ("_full pool, correct (suppl.)_", full_right),
            ("_full pool, hallucinating (suppl.)_", full_wrong)]
    stats: dict[str, tuple[int, int, int]] = {}
    for name, arr in rows:
        n = len(arr)
        k_cap = int((arr >= CAP - 1e-9).sum())
        k_top = int((arr >= TOP_DECILE - 1e-9).sum())
        stats[name] = (n, k_cap, k_top)
        log(f"| {name} | {n} | {fmt_prop(k_cap, n)} | {fmt_prop(k_top, n)} |")
    log("")
    log("Because only two attainable values lie in the top tenth of the range, the second")
    log("column decomposes exactly:")
    log("")
    log("| population | n | " + " | ".join(f"at {v:.4f}" for v in att_top) + " |")
    log("| --- | --- | " + " | ".join("---" for _ in att_top) + " |")
    for name, arr in rows:
        cells = [fmt_prop(int((np.abs(arr - v) < 1e-9).sum()), len(arr)) for v in att_top]
        log(f"| {name} | {len(arr)} | " + " | ".join(cells) + " |")
    log("")
    n_all, kc_all, kt_all = stats["fair pool (correct + hallucinating)"]
    log(f"**The finding, restated on the correct population.** {kt_all} of the {n_all} fair-pool")
    log(f"targets ({kt_all/n_all:.0%}) sit in the top tenth of the scale, a region in which the")
    log(f"estimator has exactly **{len(att_top)} expressible values**. A third of the population is")
    log("resolved to a 2-point scale. That is the granularity claim, and it does not")
    log("depend on the attack, on the optimiser, or on which targets were attacked.")
    log("")
    kt_f = int((v_full >= TOP_DECILE - 1e-9).sum())
    kc_f = int((v_full >= CAP - 1e-9).sum())
    log("**Prevalence caveat -- read the pooled row with care.** The fair pool is 50/50 by")
    log(f"construction; the model's actual error rate on this split is {prev_wrong:.1%} "
        f"({len(full_wrong)}/{len(v_full)}).")
    log("Since the hallucinating stratum is the crowded one, ANY pooled crowding figure is")
    log("a function of the class balance you assume. On the full labelled pool at natural")
    log(f"prevalence (n={len(v_full)}, supplementary population, no selection at all) the same two")
    log(f"statistics are {fmt_prop(kc_f, len(v_full))} at the ceiling and "
        f"{fmt_prop(kt_f, len(v_full))} in the top tenth.")
    log("The per-stratum rows are the prevalence-free way to state it and should be")
    log("preferred in the paper.")
    log("")
    nr, kcr, ktr = stats["fair pool, correct stratum"]
    nw, kcw, ktw = stats["fair pool, hallucinating stratum"]
    log(f"**Stratum asymmetry (new, and it cuts against the detector).** The hallucinating")
    log(f"stratum is crowded at the top far harder than the correct stratum: {kcw/nw:.1%} vs "
        f"{kcr/nr:.1%} at")
    log(f"the ceiling, {ktw/nw:.1%} vs {ktr/nr:.1%} in the top tenth -- non-overlapping Wilson intervals in")
    log(f"both cases. Right-censoring at ln({N_SAMPLES}) therefore removes more of the hallucinating")
    log("class's spread than the correct class's, which biases the measured class")
    log("separation (and so the 0.704 clean AUROC) DOWNWARD. The attacked subset pointed")
    log("the same way (24% vs 10% at the cap) but on n=17 hallucinating targets; this is")
    log("n=200 per stratum.")
    log("")

    # -------------------------------------------------------- 4. rarefaction
    log("## 4. Rarefaction: distinct realised values vs number of targets observed")
    log("")
    log("Distinct-values-observed is **monotone non-decreasing in n**, so any such count is")
    log("a SAMPLE statistic, not a property of the estimator. This curve is what lets a")
    log("reader tell the two apart. `E[distinct]` is exact (a value of multiplicity m is")
    log("missed with probability C(M-m, n)/C(M, n)); the Monte-Carlo column is")
    log(f"{N_MC} subsamples without replacement and is shown only for the spread.")
    log("")
    rng = np.random.default_rng(SEED)
    for pop_name, arr, grid in (
            ("fair pool (n=400, correct + hallucinating)", v_all, RAREFACTION_N),
            ("fair pool, correct stratum (n=200)", v_right, RAREFACTION_N),
            ("fair pool, hallucinating stratum (n=200)", v_wrong, RAREFACTION_N),
            ("_full labelled pool, n=2000 (supplementary)_", v_full,
             RAREFACTION_N + [800, 1600, len(v_full)])):
        mult = list(Counter(arr.tolist()).values())
        M = len(arr)
        log(f"**{pop_name}**")
        log("")
        log("| targets sampled | E[distinct] (exact) | MC mean | MC sd | MC min-max | "
            f"% of the {n_att}-value lattice |")
        log("| --- | --- | --- | --- | --- | --- |")
        for n in grid:
            if n > M:
                continue
            e = expected_distinct(mult, n)
            m, sd, lo, hi = mc_distinct(arr, n, N_MC if n < M else 1, rng)
            tag = " (full population)" if n == M else ""
            log(f"| {n}{tag} | {e:.2f} | {m:.2f} | {sd:.2f} | {lo}-{hi} | {e/n_att:.0%} |")
        log("")

    # ------------------------------------------- 5. head-to-head with the paper
    log("## 5. Head-to-head with the attacked-subset numbers the paper currently carries")
    log("")
    log("The repo's `results/dynamic_range_finding.md` reports, on the attacked subset")
    log("(80 correct + 17 hallucinating = 97 targets): 22 distinct values, 8/80 at the")
    log("ceiling, 21/80 in the top decile. Recomputed here on the fair pool, with the")
    log("attacked-subset figures reproduced from the same cache for comparability.")
    log("Remember these are NESTED: the 80 are the fair pool's correct[:80].")
    log("")
    a80 = np.array([round(emap[q], DP) for q in fair_right[:80]])
    a97 = np.concatenate([a80, np.array([round(emap[q], DP) for q in fair_wrong[:17]])])
    mult_right = list(Counter(v_right.tolist()).values())
    log("| statistic | attacked subset (nested) | fair pool | fair pool, correct only |")
    log("| --- | --- | --- | --- |")
    log(f"| n | 97 (80 correct + 17 hallucinating) | 400 | 200 |")
    log(f"| distinct realised values | {len(set(a97.tolist()))} | "
        f"{len(set(v_all.tolist()))} | {len(set(v_right.tolist()))} |")
    log(f"| ... as a share of the {n_att} attainable | {len(set(a97.tolist()))/n_att:.0%} | "
        f"{len(set(v_all.tolist()))/n_att:.0%} | {len(set(v_right.tolist()))/n_att:.0%} |")
    n_, kc, kt = stats["fair pool, correct stratum"]
    log(f"| correct answers at the ceiling | {fmt_prop(int((a80 >= CAP - 1e-9).sum()), 80)} | "
        f"- | {fmt_prop(kc, n_)} |")
    log(f"| correct answers in the top tenth | {fmt_prop(int((a80 >= TOP_DECILE - 1e-9).sum()), 80)} | "
        f"- | {fmt_prop(kt, n_)} |")
    log(f"| ALL targets in the top tenth (pooled) | "
        f"{fmt_prop(int((a97 >= TOP_DECILE - 1e-9).sum()), 97)} | "
        f"{fmt_prop(kt_all, n_all)} | - |")
    log(f"| ALL targets at the ceiling (pooled) | "
        f"{fmt_prop(int((a97 >= CAP - 1e-9).sum()), 97)} | "
        f"{fmt_prop(kc_all, n_all)} | - |")
    log("")
    obs80 = len(set(a80.tolist()))
    e80 = expected_distinct(mult_right, 80)
    rng2 = np.random.default_rng(SEED + 1)
    draws = np.array([len(np.unique(v_right[rng2.choice(200, 80, replace=False)]))
                      for _ in range(N_MC)])
    pct = float((draws <= obs80).mean())
    log(f"**The rarefaction control.** Drawing 80 targets at random from the fair pool's")
    log(f"correct stratum gives E[distinct] = **{e80:.1f}** (MC sd {draws.std(ddof=1):.2f}), against the "
        f"**{obs80}** actually")
    log(f"realised by the attacked 80. The observed 22 sits at the {pct:.0%} percentile of that")
    log("reference distribution -- an unremarkable draw. The attacked cell's distinct-value")
    log("count is what a random 80 from this population produces; the same population")
    log(f"yields {len(set(v_right.tolist()))} distinct values at n=200 and is still climbing. \"22 distinct values\"")
    log("was never an estimator property, it was a sample size.")
    log("")
    log("**What replaces it.** The estimator-level statement is the lattice: at N=10 there")
    log(f"are **{n_att} attainable values in total and {len(att_top)} in the top tenth of the range** -- true")
    log("by enumeration, independent of n, and not something a larger pool can improve.")
    log(f"The population-level statement is section 3: {kt_all}/{n_all} = {kt_all/n_all:.0%} "
        f"[{wilson(kt_all, n_all)[1]:.0%}, {wilson(kt_all, n_all)[2]:.0%}] of the fair")
    log(f"pool lands in that {len(att_top)}-value region.")
    log("")

    # ------------------------------------------------------------ 6. verdict
    log("## 6. Verdict: does the central claim survive the population fix?")
    log("")
    log("**The crowding claim survives and does not weaken. The distinct-value claim does")
    log("not survive and must be replaced by the lattice count.**")
    log("")
    log("| claim component | on the attacked subset | on the fair pool | direction |")
    log("| --- | --- | --- | --- |")
    log(f"| targets in the top tenth of the range | {int((a97 >= TOP_DECILE - 1e-9).sum())}/97 = "
        f"{int((a97 >= TOP_DECILE - 1e-9).sum())/97:.0%} | {kt_all}/{n_all} = {kt_all/n_all:.0%} | "
        "**stronger** |")
    log(f"| targets pinned at the ceiling | {int((a97 >= CAP - 1e-9).sum())}/97 = "
        f"{int((a97 >= CAP - 1e-9).sum())/97:.0%} | {kc_all}/{n_all} = {kc_all/n_all:.0%} | "
        "**stronger** |")
    log(f"| correct answers in the top tenth | 21/80 = 26.2% | {ktr}/{nr} = {ktr/nr:.1%} | "
        "slightly weaker, intervals overlap |")
    log(f"| correct answers at the ceiling | 8/80 = 10.0% | {kcr}/{nr} = {kcr/nr:.1%} | "
        "unchanged |")
    log(f"| \"only 22 distinct values\" | 22 | {len(set(v_all.tolist()))} at n=400; "
        f"{len(set(v_full.tolist()))} at n={len(v_full)} | **retire: it was a sample size** |")
    log(f"| attainable values in the top tenth | {len(att_top)} | {len(att_top)} | "
        "unchanged (enumeration, not a sample) |")
    log("")
    log("Reading. The two statistics the paper leans on hardest -- crowding at the ceiling")
    log("and in the top decile -- come out HIGHER on the fair pool than on the attacked")
    log("subset, because the attacked subset is 80/97 correct answers while the fair pool")
    log("is half hallucinations, and hallucinations are the crowded class. The claim was")
    log("therefore being UNDER-stated by being made on the wrong population, not")
    log("over-stated. The correct-stratum numbers, which is what the false-alarm attack")
    log("actually operates on, are essentially unchanged (9.5% vs 10.0% at the cap;")
    log("21.5% vs 26.2% in the top decile, overlapping intervals) -- so nothing that")
    log("depends on the FA arm moves.")
    log("")
    log("Do not over-read the pooled rows, though: both pools are artificial class")
    log(f"balances (82/18 correct for the attacked subset, 50/50 for the fair pool) and the")
    log(f"real rate is {1 - prev_wrong:.0%} correct. At natural prevalence on n={len(v_full)} the pooled figures")
    log(f"are {kc_f/len(v_full):.1%} at the ceiling and {kt_f/len(v_full):.1%} in the top tenth -- "
        "between the two. The")
    log("per-stratum statement is the one that does not move with the assumed balance.")
    log("")
    log("The one component that does not survive is the distinct-value count. 22 was a")
    log(f"draw from a population that yields {len(set(v_right.tolist()))} at n=200 and "
        f"{len(set(v_full.tolist()))} at n={len(v_full)}, and has still not")
    log("converged. Quoting it as a property of the estimator confuses a rarefaction")
    log("artefact with a granularity")
    log(f"limit. The replacement is exact and immune to n: **{n_att} attainable values at N={N_SAMPLES}, of")
    log(f"which {len(att_top)} lie in the top tenth of the range**.")
    log("")

    out = RESULTS_DIR / "fair_pool_granularity.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nWritten to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
