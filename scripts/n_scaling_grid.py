"""BUDGET SCALING of the achievable false-positive-rate grid: N = 10 -> 20 -> 40.

WHY THIS EXISTS
---------------
`results/achievable_fpr_grid.md` is the paper's operating-point finding: on the fair
pool's correct stratum the achievable clean FPRs below one in four are 0% -> 9.5%
[6.2, 14.4] -> 21.5% [16.4, 27.7], so an operator who states a 5% false-alarm budget
cannot have one. Its section 7 then concedes the obvious rebuttal -- **"just raise N"** --
and admits the concession is unmeasured: the lattice grows 39 -> 455 attainable values
from N=10 to N=20, the floor is provably non-increasing in N, and *how much* it falls is
unknown. That is exactly the shape of the "non-relaxability" claim this project withdrew
on 2026-08-13 (`results/n20_verdict.md`), and a granularity claim made at ONE sample
budget is one rebuttal deep unless the budget-scaling curve exists.

Every outcome is publishable, which is why this is worth GPU:
  * floor still operationally coarse at N=40  -> the finding is general, not an artefact
    of the cheapest budget anyone runs;
  * floor resolves at N=20 or N=40            -> the finding becomes "at the N this
    literature uses you cannot buy a 5% false-alarm rate, and here is the budget that
    buys it", which is MORE useful to a practitioner.

WHAT IT MEASURES, AND THE ONE DESIGN CHOICE THAT MATTERS
--------------------------------------------------------
Clean side only: no attack, no judge, no null control, no hide arm. The population is the
one `paper/sections/methods.tex` commits to -- the score-independent fair pool
(`select_stratified(want, 200, seed=0)`), correct stratum as the negatives, hallucinating
stratum as the positives that supply TPR at each achievable point.

**One pass at the largest budget yields every smaller budget, exactly.** The clusterer is
union-find over PAIRWISE bidirectional entailment, so the clustering of any subset of the
samples is determined by the pairwise verdicts within that subset. This run records the
full C(N,2) verdict matrix per target, so the score at any budget k <= N is recomputable
offline with **zero GPU** by replaying the verdicts through the very same
`se.entropy.cluster_samples`. And a k-subset of an i.i.d. N-draw IS an i.i.d. k-draw, so
the subset-derived grid at budget k is an estimate of the same thing a direct k-run would
estimate. Consequence: buy N=40 once, and N=20, N=10 and everything between come free --
with the cached N=10 grid available as the control that the subsetting is sound.

    per-target record  =  entropy at N, cluster count, C(N,2) verdict bits, stage timings
    replay             =  cluster_samples(index-sentinels, ReplayNLI(bits)) -- reused, not
                          reimplemented; the full-set replay is asserted to reproduce the
                          recorded entropy bit-for-bit.

REUSE, NOT REIMPLEMENTATION
---------------------------
  * ids and Wilson intervals      `scripts/fair_pool_granularity.fair_pool_ids`, `.wilson`
  * attainable lattice            `scripts/fair_pool_granularity.attainable_lattice`
  * the grid and the budget count `scripts/achievable_fpr_grid.grid`, `.n_firing_below`
  * threshold rule                `se.stats.attainable_fprs`, `se.stats.operating_point`
    (the versions FIXED on 2026-08-13; the old quantile rule overshot its target FPR by up
    to 6x on an atomic score -- nothing here reimplements it)
  * the detector itself           `se.se_pipeline.semantic_entropy`, called exactly as
    `scripts/pilot_n20_ceiling.py` calls it, with the Week-4 generation settings
    (max_new_tokens=48, T=1.0, top_p=1.0, seed=0) so N is the only thing that changes.

MODES
-----
    --estimate-only   cost from measured throughput. No model load, no cache, no torch.
                      Every hours figure prints the n it used ON THE SAME LINE.
    --derive-only     everything that needs no new data -- the attainable lattice at
                      N=10/20/40, the coupling bound, the ceiling-atom decay curve read
                      out of the EXISTING N=10 cache, the pre-registered prediction, the
                      averaging-k comparison, the precision-vs-n table, the cost table.
                      Writes results/n_scaling_plan.md. CPU only.
    --smoke           drives the whole measurement loop, checkpointing and reporting with
                      a deterministic FAKE scorer. No GPU, no model. Proves resume works.
    (default)         the GPU pass. Per-target checkpointing, resumable, safe to kill.
                      Writes results/n_scaling_grid.md.

RUN
---
    # cost only, from this repo's measured throughput (or from a live checkpoint)
    .venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --estimate-only

    # everything that needs no GPU
    .venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --derive-only

    # the measurement (inside WSL, where the GPU is)
    ./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 40 --strata both

Killing the run costs one target. Re-invoking with the same arguments resumes.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
import zlib
from collections import Counter
from dataclasses import dataclass
from itertools import combinations, combinations_with_replacement
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

DP = 9                      # canonical rounding tolerance, same as the N=10 grid report
SEED = 0                    # the fair pool's seed, and the generation seed
N_PER_STRATUM = 200         # the fair pool: 200 correct + 200 hallucinating
MAX_NEW_TOKENS = 48         # PINNED across every condition in this project (se.config)
DEFAULT_BUDGETS = (10, 20, 40)
NOMINAL_TARGETS = (0.01, 0.05, 0.10, 0.20)


# =============================================================================== cost
# Measured anchors, with provenance. Every number below is READ OUT of an artifact in
# this repo; none is a guess. A cost figure that cannot name its source has no business
# deciding how a GPU-month is spent.
#
#   T_Q_N10_WITH_GREEDY  results/run_all.log -- wk4_sample.py, 1907 questions sustained,
#                        12.51-12.80 s/Q across the whole run. That loop does ONE greedy
#                        generation plus the N=10 sample batch plus a flush+fsync.
#   T_GREEDY_1SEQ        results/pipeline_check.md -- mean 1.49 s over 10 greedy answers.
#   T_NLI_N10            results/run_all_status.txt -- the cluster stage did 2000
#                        questions in 05:19:48 - 04:21:19 = 3509 s = 1.75 s/Q.
#                        Cross-check: results/wk3_fri_entropy.md, 50 questions at
#                        1.84 s/Q. The two agree to 5%.
T_Q_N10_WITH_GREEDY = 12.70
T_GREEDY_1SEQ = 1.49
T_GEN_N10 = T_Q_N10_WITH_GREEDY - T_GREEDY_1SEQ      # 11.21 s for the 10-sample batch
T_NLI_N10 = 1.75
NLI_PASSES_N10 = 90                                   # N(N-1): C(10,2) pairs, 2 directions

COST_PROVENANCE = [
    f"T_Q_N10_WITH_GREEDY = {T_Q_N10_WITH_GREEDY:.2f} s/question -- results/run_all.log, "
    "wk4_sample.py sustained over 1907 questions (12.51-12.80 s/Q); includes one greedy "
    "generation and an fsync per question",
    f"T_GREEDY_1SEQ       = {T_GREEDY_1SEQ:.2f} s -- results/pipeline_check.md, mean over "
    "10 greedy answers (batch of 1)",
    f"T_GEN_N10           = {T_GEN_N10:.2f} s -- the N=10 sample batch alone, by "
    "subtraction",
    f"T_NLI_N10           = {T_NLI_N10:.2f} s/question -- results/run_all_status.txt, "
    "wk4_cluster.py did 2000 questions in 3509 s; cross-checked at 1.84 s/Q on 50 "
    "questions in results/wk3_fri_entropy.md",
]

# Three named generation-scaling scenarios. Generation is ONE `model.generate` call with
# num_return_sequences=N, so the N sequences share the prompt forward pass and decode as a
# batch; how batch size maps to wall clock on bnb-nf4 is not something this repo has
# measured above N=20, so it is bracketed rather than asserted.
#   linear      (CENTRAL) affine through the two anchors we have: a batch of 1 costs
#               1.49 s and a batch of 10 costs 11.21 s, i.e. 1.08 s per extra sequence on
#               top of 0.41 s of fixed cost. Batching buys only ~1.2x at N=10, so the
#               marginal cost per sample is close to flat -- take it as flat.
#   amortised   (OPTIMISTIC) the decode step is memory-bandwidth-bound and the 4-bit
#               dequant cost is per-matmul, not per-row, so a wider batch is nearly free;
#               only the batch's max sequence length grows (a max over more draws).
#   loaded      (PESSIMISTIC) linear PLUS 20% per doubling for the longer max-length of a
#               wider batch and for KV-cache pressure.
GEN_SLOPE = (T_GEN_N10 - T_GREEDY_1SEQ) / 9.0         # 1.080 s per additional sequence
GEN_FIXED = T_GEN_N10 - 10.0 * GEN_SLOPE              # 0.41 s
SCENARIOS = ("amortised", "linear", "loaded")
CENTRAL_SCENARIO = "linear"


def nli_passes(n: int) -> int:
    """DeBERTa forward passes to cluster n samples: C(n,2) pairs, both directions.

    This is the term that makes N=40 more than four times N=10. It is exactly quadratic:
    the clusterer scores every pair and union-find has no early exit."""
    return n * (n - 1)


def t_nli(n: int) -> float:
    return T_NLI_N10 * nli_passes(n) / NLI_PASSES_N10


def t_gen(n: int, scenario: str = CENTRAL_SCENARIO) -> float:
    if scenario == "linear":
        return GEN_FIXED + GEN_SLOPE * n
    if scenario == "amortised":
        return T_GEN_N10 * (1.0 + 0.10 * math.log2(max(n, 1) / 10.0))
    if scenario == "loaded":
        return (GEN_FIXED + GEN_SLOPE * n) * 1.2 ** math.log2(max(n, 1) / 10.0)
    raise ValueError(f"unknown scenario {scenario!r}; expected one of {SCENARIOS}")


def t_eval(n: int, scenario: str = CENTRAL_SCENARIO) -> float:
    """Seconds for ONE clean semantic-entropy evaluation at sample budget n."""
    return t_gen(n, scenario) + t_nli(n)


def cost_line(label: str, n_targets: int, seconds: float, note: str = "") -> str:
    """A cost line ALWAYS carries the n it was computed on.

    A sibling script's cost figure went stale three times in one session because the hours
    were quoted without the n they assumed. `test_n_scaling_grid.py` asserts that every
    line this module emits containing "GPU-h" also contains "n=" -- so the two cannot be
    separated by a copy-paste."""
    hours = seconds / 3600.0
    tail = f"  ({note})" if note else ""
    return (f"{label}: n={n_targets} evals -> {hours:.2f} GPU-h "
            f"[{seconds / max(n_targets, 1):.1f} s/eval]{tail}")


def measured_throughput(records: list[dict]) -> dict[int, dict]:
    """Per-budget measured seconds, read back out of a checkpoint. Empty if none."""
    by_n: dict[int, list[dict]] = {}
    for r in records:
        by_n.setdefault(int(r["n_samples"]), []).append(r)
    out = {}
    for n, rs in sorted(by_n.items()):
        tot = [float(r["seconds_total"]) for r in rs]
        nli = [float(r.get("seconds_nli", "nan")) for r in rs]
        out[n] = {
            "n_evals": len(rs),
            "s_total": float(np.median(tot)),
            "s_nli": float(np.nanmedian(nli)) if nli else float("nan"),
            "s_total_mean": float(np.mean(tot)),
        }
    return out


# ============================================================================ lattice
_LATTICE_CACHE: dict[int, list[float]] = {}


def lattice(n: int) -> list[float]:
    """Every entropy value the estimator can emit from n samples (reused enumeration)."""
    if n not in _LATTICE_CACHE:
        from fair_pool_granularity import attainable_lattice
        _LATTICE_CACHE[n] = attainable_lattice(n)
    return _LATTICE_CACHE[n]


def lattice_stats(n: int) -> dict:
    """What the lattice PERMITS at budget n, before any data exists.

    `top_gap` has a closed form worth stating in the paper: the highest attainable value
    below the cap is the partition (2,1,1,...,1), whose entropy is ln n - (2 ln 2)/n, so
    the last step of the scale is ALWAYS 2 ln 2 / n nats wide -- 0.139 at N=10, 0.069 at
    N=20, 0.035 at N=40. It shrinks like 1/n, while the lattice as a whole grows
    superpolynomially; that asymmetry is the whole "sparsest exactly at the top" story."""
    lat = lattice(n)
    cap = math.log(n)
    top10 = [v for v in lat if v >= 0.9 * cap - 1e-12]
    top5 = [v for v in lat if v >= 0.95 * cap - 1e-12]
    top1 = [v for v in lat if v >= 0.99 * cap - 1e-12]
    gaps_top = [b - a for a, b in zip(top10, top10[1:])]
    return {
        "n": n,
        "cap": cap,
        "size": len(lat),
        "n_top10": len(top10),
        "n_top5": len(top5),
        "n_top1": len(top1),
        "top_values": top10,
        "top_gap": cap - lat[-2],
        "top_gap_closed_form": 2.0 * math.log(2) / n,
        "min_gap_all": min(b - a for a, b in zip(lat, lat[1:])),
        "min_gap_top10": min(gaps_top) if gaps_top else float("nan"),
        "merged_at_9dp": len(lat) - len({round(v, DP) for v in lat}),
        "merged_at_9dp_in_top10": len(top10) - len({round(v, DP) for v in top10}),
    }


def permitted_fpr_spacing(n_samples: int, n_negatives: int) -> dict:
    """The finest FPR spacing the LATTICE permits -- an upper bound on how good the grid
    could possibly get, free of any data.

    Two things bound the number of distinct false-alarm rates a threshold rule can offer:
      1. the lattice -- FPR can only change at an attainable score, so there are at most
         |lattice| firing operating points;
      2. the sample -- every realised FPR is a multiple of 1/n_negatives.
    So the count of distinct achievable FPRs is at most min(|lattice|, n_negatives), and
    the finest spacing achievable ANYWHERE on [0, 1] is 1 / that. The same argument inside
    the top tenth of the range bounds the operator's low-false-alarm menu, which is the
    region every deployment lives in."""
    st = lattice_stats(n_samples)
    binding = "lattice" if st["size"] < n_negatives else "sample size"
    binding_top = "lattice" if st["n_top10"] < n_negatives else "sample size"
    return {
        **st,
        "n_negatives": n_negatives,
        "max_operating_points": min(st["size"], n_negatives),
        "finest_spacing": 1.0 / min(st["size"], n_negatives),
        "binding_constraint": binding,
        "max_points_in_top10": min(st["n_top10"], n_negatives),
        "finest_spacing_top10": 1.0 / min(st["n_top10"], n_negatives),
        "binding_constraint_top10": binding_top,
    }


# ======================================================== ceiling atom, subsets, replay
def esp_transversal_prob(sizes: list[int], k: int) -> float:
    """P(a uniformly random k-subset hits k DISTINCT clusters), exactly.

    A k-subset of the n samples lands on k distinct clusters iff it picks one element from
    each of k different clusters, so the count is the elementary symmetric polynomial
    e_k(sizes) and the probability is e_k / C(n, k).

    Direction of the bound, which matters: this is the *induced-partition* event. The
    clustering computed from scratch on the subset is FINER than the restriction of the
    full clustering (a merge can travel through a sample outside the subset), so
    {k distinct clusters in the restriction} is contained in {all k pairwise
    inequivalent}. This therefore UNDER-estimates the ceiling-atom mass at budget k, and
    any decay curve built from it decays too fast."""
    n = sum(sizes)
    if k > len(sizes) or k > n:
        return 0.0
    e = [1.0] + [0.0] * k
    for s in sizes:
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * s
    return e[k] / math.comb(n, k)


def _pair_index(n: int) -> dict[tuple[int, int], int]:
    return {(i, j): p for p, (i, j) in enumerate(combinations(range(n), 2))}


def _stable_hash(s: str) -> int:
    """A hash that does not move between processes.

    `hash()` on a str is salted per interpreter (PYTHONHASHSEED), so seeding an RNG with
    it would make the subset draws -- and therefore every replayed grid -- irreproducible
    across runs. This project has been bitten enough times by numbers that move while you
    read them."""
    return zlib.crc32(s.encode("utf-8"))


def verdict_bits(verdicts: list[bool]) -> str:
    return "".join("1" if v else "0" for v in verdicts)


def _sentinel(i: int) -> str:
    return f"\x00sample{i}\x00"


def _sentinel_index(s: str) -> int:
    return int(s.strip("\x00")[6:])


class ReplayNLI:
    """Answers equivalence queries from a RECORDED verdict matrix. No model, no GPU.

    Samples are passed in as index sentinels, never as their text, so two identical answer
    strings cannot collide into one another's verdicts. Duck-types the one method
    `se.entropy.cluster_samples` calls, which is why the replay uses the project's real
    clusterer rather than a second copy of union-find."""

    def __init__(self, bits: str, n: int):
        if len(bits) != math.comb(n, 2):
            raise ValueError(f"verdict string has {len(bits)} bits, expected "
                             f"{math.comb(n, 2)} for n={n}")
        self._n = n
        self._idx = _pair_index(n)
        self._bits = bits

    def lookup(self, i: int, j: int) -> bool:
        a, b = (i, j) if i < j else (j, i)
        return self._bits[self._idx[(a, b)]] == "1"

    def bidirectional_equivalent_batch(self, pairs, batch_size: int = 64) -> list[bool]:
        return [self.lookup(_sentinel_index(a), _sentinel_index(b)) for a, b in pairs]


def score_subset(bits: str, n: int, subset: list[int]):
    """The ClusterResult the detector WOULD have produced from just `subset`.

    Exact, not approximate: the clusterer is union-find over pairwise verdicts, so the
    clustering of a subset depends only on the verdicts inside it. Reuses
    `se.entropy.cluster_and_score` -- the same code path the GPU run takes, so this is a
    replay of the detector and not a second implementation of it."""
    from se.entropy import cluster_and_score
    full = ReplayNLI(bits, n)
    idx = list(subset)
    sub_bits = verdict_bits([full.lookup(idx[a], idx[b])
                             for a, b in combinations(range(len(idx)), 2)])
    return cluster_and_score([_sentinel(i) for i in range(len(idx))],
                             ReplayNLI(sub_bits, len(idx)))


def subset_ceiling_prob(bits: str, n: int, k: int, rng, n_mc: int = 500) -> float:
    """P(a random k-subset is all-singletons) under the TRUE subset clustering.

    All-singletons happens iff no pair inside the subset is equivalent -- i.e. the subset
    is an independent set of the equivalence graph -- so this needs no union-find, only
    the recorded verdicts. Exact by enumeration when C(n,k) is small, Monte-Carlo
    otherwise. Unlike `esp_transversal_prob` this is the real event, not a lower bound."""
    if k > n:
        return 0.0
    replay = ReplayNLI(bits, n)

    def independent(idx) -> bool:
        return not any(replay.lookup(a, b) for a, b in combinations(idx, 2))

    if math.comb(n, k) <= n_mc:
        subs = list(combinations(range(n), k))
        return sum(1 for s in subs if independent(s)) / len(subs)
    hits = 0
    for _ in range(n_mc):
        hits += independent(rng.permutation(n)[:k].tolist())
    return hits / n_mc


# ========================================================================== averaging k
def averaging_lattice_size(n_samples: int, k: int, cap_combos: int = 400_000) -> int | None:
    """How many distinct values the MEAN of k independent budget-n scores can take.

    The operator's other move: run the detector k times and average. Returns None if the
    multiset count would exceed `cap_combos` (the enumeration is C(L+k-1, k))."""
    lat = [round(v, DP) for v in lattice(n_samples)]
    total = math.comb(len(lat) + k - 1, k)
    if total > cap_combos:
        return None
    vals = {round(sum(c) / k, DP) for c in combinations_with_replacement(lat, k)}
    return len(vals)


def averaging_comparison(n_base: int, ks: tuple[int, ...],
                         scenario: str = CENTRAL_SCENARIO) -> list[dict]:
    """Averaging k runs at budget n_base vs one run at the budget of equal top-of-scale
    resolution, N = k * n_base.

    The two moves buy DIFFERENT things and a reviewer will conflate them:
      * both divide the last step of the scale: averaging k runs at budget n puts the
        finest step at (2 ln 2 / n) / k; a single run at N = k*n puts it at 2 ln 2 / (k n).
        Identical -- and averaging is CHEAPER, because clustering is quadratic in the
        sample count and averaging keeps k separate n-sized clusterings (k * n(n-1)
        passes) where the single big run needs kn(kn-1).
      * only raising N raises the CAP (ln N vs ln n) and only raising N attacks the
        ceiling atom's cause. Averaging leaves the maximum at ln n, and an item pinned
        there in every run stays pinned: the residual atom is E_q[p(q)^k], which is
        bounded below by the mass of questions the model answers n different ways EVERY
        time. By Jensen it is also >= (E p)^k, so the atom never shrinks as fast as
        independence would suggest.
      * only raising N reduces the plug-in estimator's negative bias. Averaging is a
        variance reduction of the SAME biased functional E[H_n]; it converges to the
        wrong number faster."""
    out = []
    for k in ks:
        n_equiv = k * n_base
        c_avg = k * t_eval(n_base, scenario)
        c_big = t_eval(n_equiv, scenario)
        out.append({
            "k": k,
            "n_base": n_base,
            "n_equivalent": n_equiv,
            "top_step_nats": 2.0 * math.log(2) / (n_base * k),
            "cost_averaging_s": c_avg,
            "cost_single_run_s": c_big,
            "ratio": c_big / c_avg,
            "cap_averaging": math.log(n_base),
            "cap_single_run": math.log(n_equiv),
            "attainable_values_averaging": averaging_lattice_size(n_base, k),
            "attainable_values_single_run": len(lattice(n_equiv))
            if n_equiv <= 40 else None,
        })
    return out


# ============================================================================ the data
def _read_jsonl(path) -> list[dict]:
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue                      # a torn trailing line from a killed run
    return out


_REL = "samples/wk4_full_2000q"
CANDIDATE_CACHES = [
    Path(r"\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(r"\\wsl$\Ubuntu-24.04\home\abhi\.cache\se-research") / _REL,
    Path(os.path.expanduser("~/.cache/se-research")) / _REL,
    Path("/home/abhi/.cache/se-research") / _REL,
]


def resolve_cache(explicit: str | None) -> Path:
    """The Week-4 cache directory holding relabeled.jsonl / entropy.jsonl / samples.jsonl."""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"--cache does not exist: {p}")
        return p
    env = os.environ.get("SE_WK4_CACHE_DIR")
    if env and Path(env).exists():
        return Path(env)
    for p in CANDIDATE_CACHES:
        try:
            if (p / "relabeled.jsonl").exists():
                return p
        except OSError:
            continue
    raise SystemExit("Week-4 cache not found. Tried:\n  "
                     + "\n  ".join(str(p) for p in CANDIDATE_CACHES)
                     + "\nPass --cache or set SE_WK4_CACHE_DIR.")


@dataclass
class Pool:
    """The fair pool, plus everything the CPU-only derivations need from the N=10 cache."""
    correct_ids: list[str]
    wrong_ids: list[str]
    entropy10: dict[str, float]                  # id -> cached clean N=10 entropy
    assignments10: dict[str, list[int]]          # id -> cached N=10 cluster assignment
    questions: dict[str, str]                    # id -> question text
    n_correct_available: int = 0                 # size of the whole correct stratum


def load_pool(cache: Path, n_per_stratum: int = N_PER_STRATUM) -> Pool:
    from se.attacks.select import _stratum_ids
    labels = {r["question_id"]: r for r in _read_jsonl(cache / "relabeled.jsonl")}
    if not labels:
        raise SystemExit(f"no labels in {cache / 'relabeled.jsonl'}")
    right = _stratum_ids("right", SEED, labels)
    wrong = _stratum_ids("wrong", SEED, labels)
    ent = {r["question_id"]: r for r in _read_jsonl(cache / "entropy.jsonl")}
    qs = {r["question_id"]: r["question"] for r in _read_jsonl(cache / "samples.jsonl")}
    return Pool(
        correct_ids=right[:n_per_stratum],
        wrong_ids=wrong[:n_per_stratum],
        entropy10={q: float(r["entropy_nats"]) for q, r in labels.items()},
        assignments10={q: list(r["assignments"]) for q, r in ent.items()
                       if "assignments" in r},
        questions=qs,
        n_correct_available=len(right),
    )


# ======================================================================== measurement
@dataclass
class ScoreOut:
    entropy_nats: float
    n_clusters: int
    bits: str
    samples: list[str]
    seconds_total: float
    seconds_nli: float


class _RecordingNLI:
    """Wraps the real NLI: times it, and keeps the verdicts so the run is replayable.

    Deliberately a proxy rather than a fork of the pipeline -- `semantic_entropy` is
    called exactly as `scripts/pilot_n20_ceiling.py` calls it, so the measured score is
    the detector's score and not this script's imitation of it."""

    def __init__(self, nli):
        self._nli = nli
        self.seconds = 0.0
        self.verdicts: list[bool] = []

    def bidirectional_equivalent_batch(self, pairs, batch_size: int = 64):
        t0 = time.perf_counter()
        try:
            out = self._nli.bidirectional_equivalent_batch(pairs, batch_size=batch_size)
        finally:
            self.seconds += time.perf_counter() - t0
        self.verdicts = list(out)
        return out

    def __getattr__(self, name):
        return getattr(self._nli, name)


def make_gpu_scorer(max_new_tokens: int = MAX_NEW_TOKENS):
    """Load Llama-4bit + DeBERTa once and return `score(question, n, seed) -> ScoreOut`."""
    from se.attacks.harness import load_pair
    from se.config import GenConfig
    from se.se_pipeline import semantic_entropy

    pair = load_pair()

    def score(question: str, n_samples: int, seed: int) -> ScoreOut:
        rec = _RecordingNLI(pair.nli)
        gen = GenConfig(max_new_tokens=max_new_tokens, n_samples=n_samples,
                        temperature=1.0, top_p=1.0, seed=seed)
        t0 = time.perf_counter()
        res = semantic_entropy(question, pair.lm, rec, gen)
        dt = time.perf_counter() - t0
        expected = math.comb(n_samples, 2)
        if len(rec.verdicts) != expected:
            raise RuntimeError(f"recorded {len(rec.verdicts)} verdicts, expected {expected}"
                               f" -- se.entropy.cluster_samples changed its pair order?")
        return ScoreOut(entropy_nats=float(res.entropy_nats), n_clusters=int(res.n_clusters),
                        bits=verdict_bits(rec.verdicts), samples=list(res.samples),
                        seconds_total=dt, seconds_nli=rec.seconds)

    return score


def make_fake_scorer(seed: int = 0):
    """A deterministic CPU stand-in for --smoke and for the tests.

    Draws a latent 'meaning' per sample from a per-question Dirichlet, calls two samples
    equivalent iff they share a meaning, and runs them through the REAL clusterer. So the
    smoke path exercises entropy, verdict recording, replay and the grid -- everything
    except the two model loads."""
    from se.entropy import cluster_and_score

    def score(question: str, n_samples: int, s: int) -> ScoreOut:
        rng = np.random.default_rng(_stable_hash(f"{question}|{s}|{seed}"))
        p = rng.dirichlet(np.full(6, 0.7))
        draw = rng.choice(len(p), size=n_samples, p=p).tolist()
        verdicts = [draw[i] == draw[j] for i, j in combinations(range(n_samples), 2)]
        bits = verdict_bits(verdicts)
        cs = cluster_and_score([_sentinel(i) for i in range(n_samples)],
                               ReplayNLI(bits, n_samples))
        return ScoreOut(entropy_nats=float(cs.entropy_nats), n_clusters=int(cs.n_clusters),
                        bits=bits, samples=[f"fake-{d}" for d in draw],
                        seconds_total=0.001 * n_samples, seconds_nli=0.0002 * n_samples)

    return score


def ckpt_key(rec: dict) -> tuple:
    return (rec["question_id"], int(rec["n_samples"]), int(rec["seed"]),
            int(rec["max_new_tokens"]))


def run_measurement(targets: list[tuple[str, str, str]], n_samples: int, seed: int,
                    ckpt_path: Path, score_fn, *, store_samples: bool = True,
                    max_new_tokens: int = MAX_NEW_TOKENS, log=print,
                    progress_every: int = 5, scorer: str = "gpu") -> list[dict]:
    """Score every (stratum, question_id, question) at `n_samples`, resumably.

    One appended+flushed JSONL line per completed evaluation. Killing the process costs
    the target in flight and nothing else; re-invoking skips everything already recorded.
    The machine is shared, so this is not optional."""
    done = {ckpt_key(r): r for r in _read_jsonl(ckpt_path)}
    todo = [t for t in targets
            if (t[1], n_samples, seed, max_new_tokens) not in done]
    log(f"[run] N={n_samples} seed={seed}: {len(targets)} targets, "
        f"{len(targets) - len(todo)} already done, {len(todo)} to do")
    if todo:
        est = len(todo) * t_eval(n_samples)
        log("[run] " + cost_line(f"remaining at N={n_samples}", len(todo), est,
                                 "model estimate, refined below from measured time"))
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    for i, (stratum, qid, question) in enumerate(todo):
        out = score_fn(question, n_samples, seed)
        rec = {
            "question_id": qid, "stratum": stratum, "n_samples": n_samples, "seed": seed,
            "max_new_tokens": max_new_tokens, "entropy_nats": out.entropy_nats,
            "n_clusters": out.n_clusters, "verdict_bits": out.bits,
            "seconds_total": out.seconds_total, "seconds_nli": out.seconds_nli,
            # Provenance travels WITH the data: a later --report-only has no other way to
            # know a checkpoint came from the fake scorer, and a fake-data report landing
            # in results/ under the real filename is exactly the failure to prevent.
            "scorer": scorer,
            # THIS CLOCK CALL STAYS, unlike the three report stamps above. A checkpoint
            # line is an append-only record of when a target was actually scored, not a
            # derived artifact anyone regenerates, so there is no byte-comparison to
            # protect -- and `scripts/progress_monitor.py` reads `ts` as one of its
            # timestamp keys. Pinning it would turn real provenance into a constant and
            # cost the monitor its only in-record clock (it already falls back to file
            # mtimes on checkpoints that lack one).
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        }
        if store_samples:
            rec["samples"] = out.samples
        with ckpt_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=float) + "\n")
            f.flush()
            os.fsync(f.fileno())
        done[ckpt_key(rec)] = rec
        if (i + 1) % progress_every == 0 or i + 1 == len(todo):
            el = time.perf_counter() - t_start
            per = el / (i + 1)
            log(f"  {i+1}/{len(todo)} at N={n_samples} in {el:.0f}s ({per:.1f}s/eval), "
                f"ETA {per * (len(todo) - i - 1) / 60:.1f} min")
    return list(done.values())


# ============================================================================= grids
def budget_scores(records: list[dict], budget: int, stratum: str, *, replicate: int = 0,
                  rng_seed: int = 0) -> dict[str, float]:
    """Score at sample budget `budget` for every target, from records at budget >= it.

    budget == the record's own N  -> the measured score, untouched.
    budget <  the record's own N  -> replay a uniformly random `budget`-subset of the
                                     recorded samples through the real clusterer. A
                                     k-subset of an i.i.d. N-draw IS an i.i.d. k-draw, so
                                     this estimates the same quantity a direct run would.
                                     `replicate` selects which random subset, so the whole
                                     experiment can be repeated at zero GPU cost."""
    out: dict[str, float] = {}
    for r in records:
        if r["stratum"] != stratum:
            continue
        n = int(r["n_samples"])
        if n < budget:
            continue
        if n == budget:
            out[r["question_id"]] = float(r["entropy_nats"])
            continue
        rng = np.random.default_rng((rng_seed, replicate,
                                     _stable_hash(r["question_id"]), budget))
        idx = sorted(rng.choice(n, size=budget, replace=False).tolist())
        out[r["question_id"]] = float(score_subset(r["verdict_bits"], n, idx).entropy_nats)
    return out


def grid_for(neg: np.ndarray, pos: np.ndarray) -> list[dict]:
    from achievable_fpr_grid import grid
    return grid(neg, pos)


def ceiling_atom(neg: np.ndarray, budget: int, tol: float = 1e-9) -> tuple[int, int]:
    return int((neg >= math.log(budget) - tol).sum()), len(neg)


# =========================================================================== reporting
def _wilson(k: int, n: int):
    from fair_pool_granularity import wilson
    return wilson(k, n)


def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = _wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


# ------------------------------------- the replayed floor the PAPER quotes (not computed here)
# Every replayed row in this report is ONE subset draw (`replicate=0`). That is a legitimate
# estimator with a legitimate interval -- Wilson on its own count, which by the variance
# identity in `results/replay_control.md` section 2b already contains the subset draw -- but
# it is not the number the paper quotes. The paper quotes the subset-AVERAGED floor: the mean
# of the 200 per-question saturation probabilities, intervalled by a bootstrap over questions
# only, because the subset draw has been averaged out of the point estimate and may not be put
# back into its interval.
#
# That quantity is NOT recomputed here on purpose. `scripts/replay_control.py` owns it, and a
# second implementation of a number the paper prints is how two files come to disagree without
# anyone noticing. What is recorded below is a POINTER plus the value as of the stamp, so that
# a stale copy is self-identifying rather than silently current-looking, and
# `tests/test_n_scaling_grid.py::test_the_quoted_subset_averaged_floor_still_matches_replay_control`
# fails the moment `results/replay_control.md` stops printing it. If the two ever disagree,
# THAT FILE WINS and this constant is the thing to fix.
SUBSET_AVERAGED_FLOOR = {10: ("12.0%", "[8.9%, 15.3%]"), 20: ("3.1%", "[1.8%, 4.7%]")}
SUBSET_AVERAGED_FLOOR_FILE = "results/replay_control.md"
SUBSET_AVERAGED_FLOOR_SEC = "section 2b"
SUBSET_AVERAGED_FLOOR_ASOF = "2026-08-19"


def floor_cells(neg: np.ndarray, rows: list[dict], budget: int) -> dict:
    """The three false-alarm cells of the section-1 row, computed in one place.

    THE FLOOR AND THE CEILING ATOM ARE TWO DIFFERENT QUANTITIES and this function exists
    so that they cannot be swapped again:

    * `floor` is the smallest false-alarm rate a firing threshold can actually realise --
      the first row of the ascending-FPR grid that fires. It is what an operator can buy.
    * `at_cap` is the ceiling-atom mass, the negatives sitting exactly at ln N.

    They are EQUAL exactly while the atom is non-empty, because the first threshold that
    fires is then ln N itself and it flags precisely the at-cap targets. That held at
    every budget this report was originally written against (N=10, N=20), so the floor
    column carried the atom for a long time and agreed with its own header by coincidence.
    Once the atom empties the two part company: `at_cap` is 0 while the floor is not, and
    printing the atom under a "floor" header reports the cheapest reachable operating
    point as 0.0%, which invites the reader to infer a sub-1% operating point that does
    not exist. Report both, in separate and clearly-headed columns.
    """
    firing = [r for r in rows if r["fires"]]
    k_cap, n_cap = ceiling_atom(neg, budget)
    atom_empty = bool(firing) and k_cap == 0

    # THE FLOOR LOSES ITS INTERVAL EXACTLY WHEN THE ATOM EMPTIES (2026-08-19).
    # While the atom carries mass the floor is a binomial proportion at ln N -- a
    # threshold fixed before the data -- and Wilson prices it. Once the atom empties the
    # threshold is the top score THIS pool happened to reach, and whether that rung is the
    # top of the population's support is NOT DETERMINABLE from n=200. That is the reason
    # for dropping the interval, and it is model-free.
    #
    # REVISED 2026-08-26. This comment used to say the rung "is not the top of the
    # population's support: a bigger pool reaches a higher rung and reports a smaller
    # floor". `results/n40_floor_estimator_ruling.md` section 13 retracts that sentence:
    # it is true only in the branch where P(K >= 39) > 0. In the OTHER branch -- which the
    # data does not exclude, p=0.1175 for the fitted model against 0/200 -- the pool max
    # IS the population's top rung 98% of the time, no larger pool reports a smaller
    # floor, and the floor is an ordinary binomial proportion. Do not restate the old
    # sentence, and do not restate its cousin "the estimand dissolves"; both are
    # branch-conditional claims worn as unconditional ones.
    #
    # The coverage pair is branch-conditional TOO, and must never be quoted without the
    # population beside it (ruling section 8.4, at nominal 95%):
    #   calibrated Ewens (tau_top = 0.2726%): Wilson 53.67%, question bootstrap 0.00%
    #   zero branch      (tau*     = 2.0%):   Wilson 95.06%, question bootstrap 100%
    # So "both estimators fail" is a statement about the first row, not about the data.
    # What holds unconditionally is that quoting either interval commits to a branch this
    # sample cannot decide -- so the cell prints the count and the rate and no interval.
    # The interval that survives at such a budget is the at-cap column beside it, whose
    # threshold ln N really is fixed a priori.
    if not firing:
        floor_cell = "-"
    elif atom_empty:
        floor_cell = (f"{firing[0]['k_fp']}/{firing[0]['n_neg']} = "
                      f"{firing[0]['fpr']:.1%}, no interval (see below)")
    else:
        floor_cell = fmt_prop(firing[0]["k_fp"], firing[0]["n_neg"])

    return {
        "floor": floor_cell,
        "floor_k": firing[0]["k_fp"] if firing else None,
        "floor_fpr": firing[0]["fpr"] if firing else None,
        "at_cap": fmt_prop(k_cap, n_cap),
        "at_cap_k": k_cap,
        "next": f"{firing[1]['fpr']:.1%}" if len(firing) > 1 else "-",
        "atom_is_empty_so_floor_differs": atom_empty,
    }


def n_needed_to_certify(p: float, target: float = 0.05, n_max: int = 5000) -> int | None:
    """Smallest n whose Wilson upper bound at a true rate p clears `target`.

    The operator-facing question is not "what is the floor" but "can we say there is no
    operating point at or below 5%". That is a one-sided statement about the floor's
    UPPER confidence bound, and it needs a specific n. Returns None if even n_max is not
    enough (i.e. p is too close to the target to separate)."""
    if p >= target:
        return None
    for n in range(20, n_max + 1, 10):
        if _wilson(int(round(p * n)), n)[2] < target:
            return n
    return None


def cost_section(log, budgets, n_per_stratum: int, both_strata: bool,
                 measured: dict[int, dict] | None = None) -> None:
    """The per-N cost table. Every hours figure names the n it used, on its own line."""
    n_targets = n_per_stratum * (2 if both_strata else 1)
    log("### Per-evaluation cost, by sample budget")
    log("")
    log("Semantic entropy at budget N costs one batched generation of N sequences plus")
    log("N(N-1) DeBERTa forward passes (C(N,2) pairs, both directions). The second term is")
    log("**exactly quadratic**, so N=40 is not four times N=10 -- the clustering alone is")
    log(f"{nli_passes(40) / nli_passes(10):.1f}x.")
    log("")
    log("| N | generation (s) | NLI passes | NLI (s) | total per eval (s) | x N=10 | "
        "linear-in-N would be |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    base = t_eval(10)
    for n in budgets:
        log(f"| {n} | {t_gen(n):.1f} | {nli_passes(n)} | {t_nli(n):.1f} | "
            f"**{t_eval(n):.1f}** | {t_eval(n) / base:.2f}x | {n / 10:.1f}x |")
    log("")
    log("Generation scaling is bracketed, because this repo has never measured a batch")
    log("wider than 20. The bracket is named and both ends are stated:")
    log("")
    log("| N | amortised (optimistic) | linear (central) | loaded (pessimistic) |")
    log("| --- | --- | --- | --- |")
    for n in budgets:
        log(f"| {n} | {t_eval(n, 'amortised'):.1f} s | **{t_eval(n, 'linear'):.1f} s** | "
            f"{t_eval(n, 'loaded'):.1f} s |")
    log("")
    if measured:
        log("**Measured, from the live checkpoint** (this table replaces the model above as")
        log("soon as the run has any targets; it is why the cost figure here cannot go")
        log("stale):")
        log("")
        log("| N | evals measured | median s/eval | median s in NLI | model said |")
        log("| --- | --- | --- | --- | --- |")
        for n, m in measured.items():
            log(f"| {n} | {m['n_evals']} | **{m['s_total']:.1f}** | {m['s_nli']:.1f} | "
                f"{t_eval(n):.1f} |")
        log("")
    log("### What a configuration costs")
    log("")
    for n in budgets:
        if n == 10:
            log(f"- N=10: **free** -- re-derived from the Week-4 cache "
                f"(`{_REL}/entropy.jsonl`), which was produced at exactly these generation "
                f"settings. n={n_per_stratum} negatives, 0.00 GPU-h.")
            continue
        log("- " + cost_line(f"N={n}, correct stratum only (the FPR grid and the floor)",
                             n_per_stratum, n_per_stratum * t_eval(n)))
        log("- " + cost_line(f"N={n}, both strata (adds TPR at every achievable point)",
                             2 * n_per_stratum, 2 * n_per_stratum * t_eval(n)))
    log("")
    total_direct = sum(2 * n_per_stratum * t_eval(n) for n in budgets if n != 10)
    top = max(b for b in budgets)
    log("- " + cost_line("ALL budgets measured directly, both strata",
                         2 * n_per_stratum * len([b for b in budgets if b != 10]),
                         total_direct, "one pass per budget"))
    log("- " + cost_line(f"the recommended buy: ONE pass at N={top}, both strata",
                         2 * n_per_stratum, 2 * n_per_stratum * t_eval(top),
                         f"every budget k <= {top} then comes free by replay"))
    log("")
    log(f"Saving from buying only the top budget: "
        f"**{(total_direct - 2 * n_per_stratum * t_eval(top)) / 3600:.1f} GPU-h** "
        f"(n={n_targets} evals avoided), and the replay gives every k in between rather "
        "than three isolated points.")
    log("")


# ------------------------------------------------------------------------- the plan
def write_plan(args) -> int:
    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    cache = resolve_cache(args.cache)
    pool = load_pool(cache, args.n_per_stratum)
    budgets = tuple(args.budgets)
    n_neg = len(pool.correct_ids)
    both = args.strata == "both"

    log("# Budget scaling of the achievable-FPR grid: the plan, the cost, and everything")
    log("# that needs no new data")
    log("")
    log(f"Generated {generated_date('n_scaling_plan.md', args)} by "
        "`scripts/n_scaling_grid.py "
        "--derive-only` (CPU only; no GPU, no model, no attack data).")
    log("")
    log("`results/achievable_fpr_grid.md` measures the operator's menu at ONE sample")
    log("budget: at N=10 the achievable clean false-alarm rates below one in four are")
    log("0% -> 9.5% -> 21.5%, so a 5% budget cannot be honoured by any firing threshold.")
    log("Its section 7 concedes the rebuttal -- *just raise N* -- and admits the concession")
    log("is unmeasured. This file is the design, the price and the free half of the")
    log("answer.")
    log("")

    # ------------------------------------------------------------------ 1. the design
    log("## 1. The design, and the one thing that makes it cheap")
    log("")
    log("Clean side only: no attack, no judge, no null control, no hide arm. Population:")
    log(f"the score-independent fair pool, `select_stratified(want, {args.n_per_stratum}, "
        f"seed={SEED})` -- correct stratum as the negatives (n={n_neg}),")
    log(f"hallucinating stratum as the positives (n={len(pool.wrong_ids)}) that supply TPR "
        "at each achievable point.")
    log("Generation settings are the Week-4 ones and are PINNED: max_new_tokens=48,")
    log(f"T=1.0, top_p=1.0, seed={SEED}. **N is the only thing that changes.**")
    log("")
    log("**One pass at the largest budget yields every smaller budget, exactly.** The")
    log("clusterer is union-find over PAIRWISE bidirectional entailment, so the clustering")
    log("of a subset of the samples is fixed by the verdicts inside that subset. The run")
    log("records the full C(N,2) verdict matrix per target, so the score at any k <= N is")
    log("recomputable with zero GPU by replaying those verdicts through the very same")
    log("`se.entropy.cluster_samples`. And a k-subset of an i.i.d. N-draw is an i.i.d.")
    log("k-draw, so the subset-derived grid at budget k estimates exactly what a direct")
    log("k-run would estimate.")
    log("")
    log("Three consequences, and the third is the reason to trust the first two:")
    log("")
    log("1. Buy N=40 once and the whole curve k = 2..40 comes free, not three points.")
    log("2. Repeating the subset draw re-runs the entire experiment at zero cost, so the")
    log("   grid comes with a subset-choice spread as well as a Wilson interval.")
    log("3. **The N=10 cache is the control.** The subset-derived N=10 grid must reproduce")
    log("   the cached one within sampling error. If it does not, the subsetting is")
    log("   unsound and the run says so before any N=20/40 number is quoted.")
    log("")
    log("Residual caveats, stated up front: subset replicates share one underlying draw, so")
    log("their spread understates fresh-sampling variance (the Wilson interval over targets")
    log("stays the headline uncertainty); and per-target resolution degrades as k")
    log("approaches N (at k=N/2 a target supplies only two disjoint subsets). Neither")
    log("biases the population estimate.")
    log("")

    # ------------------------------------------------------------------ 2. the cost
    log("## 2. Cost, honestly")
    log("")
    log("Measured anchors, every one of them read out of an artifact in this repo:")
    log("")
    for line in COST_PROVENANCE:
        log(f"- `{line}`")
    log("")
    log("Two reconciliations, because three different per-eval figures are quotable from")
    log("this repo and they are not the same number:")
    log("")
    log("- **\"12.7 s\" is the SAMPLING LOOP, not an SE evaluation.** `wk4_sample.py` also")
    log("  generates one greedy answer per question and fsyncs a JSONL line. A clean SE")
    log(f"  evaluation at N=10 is the 10-sample batch plus the clustering: "
        f"**{t_eval(10):.1f} s**. The two")
    log("  differ by about 5%, but only one of them is the unit this experiment buys.")
    log("- **`results/null_objective_ablation_plan.md` section 6 implies ~2.8 s per SE")
    log("  eval**, by splitting a 3.26 s objective call across its generated tokens. That")
    log("  cannot be reconciled with a directly measured 11.2 s for the same 480 generated")
    log(f"  tokens, and the live hide cell's 568-607 s/target divides by "
        f"{t_eval(10):.1f} s into "
        f"{568 / t_eval(10):.0f}-{607 / t_eval(10):.0f}")
    log("  SE evals per target -- inside that same file's own estimate of 22-58 distinct")
    log("  feasible strings. So the direct measurement is the one used here. If the 2.8 s")
    log("  attribution were right instead, every figure below is ~4x too high and the buy")
    log("  gets cheaper; the error runs in the safe direction, and the run measures its own")
    log("  throughput from the first target anyway. (Flagged, not edited: that file belongs")
    log("  to another workstream.)")
    log("")
    ck = _read_jsonl(args.checkpoint)
    cost_section(log, budgets, args.n_per_stratum, both,
                 measured_throughput(ck) if ck else None)
    log("VRAM is not a constraint. The KV cache for Llama-3.1-8B is ~131 kB/token")
    log("(32 layers x 8 KV heads x 128 dims x 2 tensors x 2 bytes), so a batch of 40")
    log("sequences over a ~40-token prompt plus 48 new tokens holds ~0.46 GB against")
    log("~0.12 GB at N=10 -- an extra ~0.35 GB on a 16 GB card that peaked at 5.8 GB")
    log("during the Week-4 N=10 run (`results/pipeline_check.md`).")
    log("")
    log("**Against the queue.** 33 days remain to the 2026-09-15 target, and the")
    log("outstanding GPU commitment is the ~67 GPU-h definitive null control plus the")
    log("remainder of the hide cell (`docs/START_HERE_overnight.md`).")
    top = max(budgets)
    rec_h = 2 * args.n_per_stratum * t_eval(top) / 3600.0
    log(f"The recommended buy is {rec_h:.1f} GPU-h at n={2 * args.n_per_stratum} evals, "
        f"i.e. **{100 * rec_h / 67:.0f}% of the null control** and about "
        f"{rec_h / 24:.2f} of one day.")
    log("It is affordable. The honest risk is not the hours, it is the device: the card is")
    log("shared with a multi-day chain, so this must be queued, not raced -- hence")
    log("per-target checkpointing and a resume that costs at most one target.")
    log("")

    # ------------------------------------------------- 3. what the lattice permits
    log("## 3. What the lattice PERMITS, with no data at all")
    log("")
    log("Semantic entropy at budget N is the entropy of a partition of N, so the estimator")
    log("can only emit the entropy of an integer partition. That set is finite and")
    log("enumerable, and it bounds how good the achievable grid could possibly get.")
    log("")
    log("| N | partitions p(N) | attainable values | in the top tenth of the range | "
        "in the top 5% | in the top 1% | last step below the cap (nats) |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    from fair_pool_granularity import partitions as _partitions
    for n in budgets:
        st = lattice_stats(n)
        npart = sum(1 for _ in _partitions(n))
        log(f"| {n} | {npart} | **{st['size']}** | **{st['n_top10']}** | {st['n_top5']} | "
            f"{st['n_top1']} | {st['top_gap']:.4f} |")
    log("")
    log("**A closed form worth putting in the paper.** The highest attainable value below")
    log("the cap is the partition (2,1,...,1), whose entropy is ln N - (2 ln 2)/N. So the")
    log("last step of the scale is ALWAYS exactly `2 ln 2 / N` nats wide:")
    log("0.1386 at N=10, 0.0693 at N=20, 0.0347 at N=40 -- it shrinks like 1/N while the")
    log("lattice as a whole grows superpolynomially. That asymmetry IS the surviving form")
    log("of the granularity claim: the scale is sparsest exactly where the false-alarm")
    log("claim lives, at every budget.")
    log("")
    log("**The finest FPR spacing the lattice permits** -- an upper bound on the grid's")
    log("quality that costs nothing to compute. Two things bound the number of distinct")
    log("achievable false-alarm rates: the lattice (FPR can only change at an attainable")
    log("score) and the sample (every realised FPR is a multiple of 1/n). The tighter one")
    log("binds.")
    log("")
    log(f"| N | attainable values | n negatives | max distinct FPRs | finest spacing | "
        f"binding constraint | in the top tenth: max points | finest spacing there |")
    log("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for n in budgets:
        pm = permitted_fpr_spacing(n, n_neg)
        log(f"| {n} | {pm['size']} | {n_neg} | {pm['max_operating_points']} | "
            f"{pm['finest_spacing']:.2%} | **{pm['binding_constraint']}** | "
            f"{pm['max_points_in_top10']} | {pm['finest_spacing_top10']:.2%} "
            f"({pm['binding_constraint_top10']}) |")
    log("")
    log("Read that table as the ceiling on what the measurement can find:")
    log("")
    st10, st20, st40 = (lattice_stats(n) for n in (10, 20, 40))
    log(f"- At **N=10** the lattice binds everywhere: {st10['size']} values against "
        f"{n_neg} negatives, so the grid can be no finer than "
        f"{1 / st10['size']:.1%}, and in the top tenth no finer than "
        f"{1 / st10['n_top10']:.0%} of whatever mass lands there. The measured grid "
        f"(0% -> 9.5% -> 21.5%) is at that limit, not far from it.")
    log(f"- At **N=20** the lattice stops binding globally ({st20['size']} values > "
        f"{n_neg} negatives) but still binds at the top: only {st20['n_top10']} points in "
        f"the top tenth, and only {st20['n_top5']} in the top twentieth.")
    log(f"- At **N=40** the lattice has stopped binding anywhere that matters: "
        f"{st40['size']} values, {st40['n_top10']} of them in the top tenth. **From N=40 on, "
        f"the coarseness of the grid can no longer be blamed on the estimator's "
        f"arithmetic** -- if it is still coarse it is because the population is piled on "
        f"one value, which is a fact about the language model, not about entropy of a "
        f"partition.")
    log("")
    log("That is the sharpest thing enumeration alone can say, and it is what makes the")
    log("N=40 arm the decisive one: it separates *the estimator cannot express a 5% rate*")
    log("from *this model's answers cannot produce one*.")
    log("")
    log("Rounding control, per budget (the N=10 report rounds scores to 9 dp before the")
    log("grid is built; that mitigation has to be re-checked at each N because the lattice")
    log("gets denser):")
    log("")
    log("| N | smallest gap in the lattice | smallest gap in the top tenth | "
        "values merged by 9-dp rounding | of those, in the top tenth |")
    log("| --- | --- | --- | --- | --- |")
    for n in budgets:
        st = lattice_stats(n)
        log(f"| {n} | {st['min_gap_all']:.2e} | {st['min_gap_top10']:.2e} | "
            f"{st['merged_at_9dp']} | {st['merged_at_9dp_in_top10']} |")
    log("")
    log("At N=40 two pairs of attainable values fall within 1e-9 of each other and 9-dp")
    log("rounding merges them -- but none is in the top tenth, where the smallest gap is")
    log(f"{lattice_stats(40)['min_gap_top10']:.1e} nats, seven orders of magnitude clear. "
        "The mitigation still")
    log("points at the real risk (float noise fabricating operating points) and still")
    log("cannot destroy a real one anywhere a claim is made.")
    log("")

    # --------------------------------------------------------------- 4. the coupling
    log("## 4. The coupling bound: the floor is provably non-increasing in N")
    log("")
    log("The minimum non-zero achievable FPR is the mass of the ceiling atom -- the")
    log("probability that a clean correct answer yields N pairwise-inequivalent meanings --")
    log("because every threshold above ln N flags nothing and the first one that fires")
    log("flags exactly the atom. That probability is non-increasing in N:")
    log("")
    log("> A set of samples is all-singletons iff NO pair inside it is equivalent. A subset")
    log("> of a set with no equivalent pair has no equivalent pair. So {all 20 distinct} is")
    log("> contained in {the first 10 are distinct}, realisation by realisation. Coupling")
    log("> the budgets by \"the N=10 draw is the first 10 of the N=20 draw\", and using that")
    log("> the first 10 of an i.i.d. 20-draw have the law of an i.i.d. 10-draw:")
    log(">")
    log(">     min non-zero FPR at N=20  <=  min non-zero FPR at N=10.")
    log("")
    log("The containment is exact for ANY clusterer that is union-find over a pairwise")
    log("relation -- the deployed NLI one, `cluster_samples_exact`,")
    log("`cluster_samples_embedding` and `cluster_samples_judge` all qualify, because each")
    log("scores a pair without reference to the rest of the sample set. It would fail for")
    log("a clusterer with global structure (k-means, or any rule that reads all N samples")
    log("at once), which is worth one sentence in the paper: the bound is a property of")
    log("the clustering rule, not a law of nature.")
    log("")
    neg10 = np.array([round(pool.entropy10[q], DP) for q in pool.correct_ids])
    k_cap10, n10 = ceiling_atom(neg10, 10)
    p10, lo10, hi10 = _wilson(k_cap10, n10)
    log("Putting the numbers in, from the N=10 data alone and with no new measurement:")
    log("")
    log(f"- fair pool, correct stratum: floor(N=20) <= floor(N=40) <= "
        f"floor(N=10) = {fmt_prop(k_cap10, n10)}")
    log(f"- and therefore, at 95% confidence, the floor at every budget above 10 is at most "
        f"**{hi10:.1%}** on this population.")
    log("")
    log("That is the whole of what reasoning buys. It is one-directional: it says the floor")
    log("cannot rise, and says NOTHING about whether it falls to 5%, to 1% or to 9.4%. The")
    log("measurement is the only thing that can, which is exactly the position the")
    log("withdrawn non-relaxability claim was in (`results/n20_verdict.md`) -- asserted")
    log("from a mechanism instead of measured.")
    log("")

    # ---------------------------------------------- 5. the free prediction (pre-reg)
    log("## 5. A pre-registered prediction, free, out of the EXISTING N=10 cache")
    log("")
    log("The N=10 cache stores each target's cluster assignment, and that is enough to")
    log("read off how the ceiling atom decays with the sample budget *below* 10 -- which")
    log("pins the shape of the curve before a single new sample is drawn.")
    log("")
    log("For a target whose 10 samples fall into clusters of sizes c, the probability that")
    log("a uniformly random k-subset lands on k DISTINCT clusters is e_k(c) / C(10, k),")
    log("where e_k is the elementary symmetric polynomial -- exact, no Monte Carlo. A")
    log("k-subset of an i.i.d. 10-draw is an i.i.d. k-draw, so averaging that over targets")
    log("estimates the ceiling-atom mass at budget k.")
    log("")
    log("**Direction of the error, stated before the numbers.** The subset's own clustering")
    log("is FINER than the restriction of the full clustering (a merge can travel through a")
    log("sample outside the subset), so this counts fewer all-distinct subsets than the")
    log("detector would actually produce. Every entry below is a LOWER bound on the atom at")
    log("that budget, and any curve fitted to it decays too fast. Both extrapolations")
    log("underneath inherit that bias, so they are optimistic about relaxation -- which is")
    log("the direction that makes a measured *failure* to relax the more interesting")
    log("outcome, not the more suspicious one.")
    log("")
    strata = [("correct (the negatives -- this is the FPR floor)", pool.correct_ids),
              ("hallucinating (the positives)", pool.wrong_ids)]
    curves: dict[str, dict[int, float]] = {}
    for name, ids in strata:
        sizes = []
        for q in ids:
            a = pool.assignments10.get(q)
            if a is None:
                continue
            sizes.append(sorted(Counter(a).values(), reverse=True))
        curve = {k: sum(esp_transversal_prob(s, k) for s in sizes) / len(sizes)
                 for k in range(2, 11)}
        curves[name] = curve
        log(f"**{name} stratum, n={len(sizes)}**")
        log("")
        log("| budget k | " + " | ".join(str(k) for k in range(2, 11)) + " |")
        log("| --- | " + " | ".join("---" for _ in range(2, 11)) + " |")
        log("| P(all k distinct) | " + " | ".join(f"{curve[k]:.3f}" for k in range(2, 11))
            + " |")
        log("")
    log("The k=10 column is not an estimate -- it is the measured ceiling-atom mass")
    log(f"({fmt_prop(k_cap10, n10)} on the correct stratum), so the curve is anchored at")
    log("the right-hand end by the number the paper already quotes.")
    log("")
    log("**Two extrapolations, both stated in advance, neither trusted alone.**")
    log("")
    log("1. *Power law in k.* The measured curve is close to a straight line in log P vs")
    log("   log k over k = 5..10, which is a much slower decay than independence would")
    log("   give. Fit there and extend.")
    log("2. *Pairwise Beta-Binomial.* Model each target as having its own per-pair")
    log("   equivalence probability q, estimate q from the pairs the clustering merged")
    log("   (sum C(c_i,2) of C(10,2)) under a Jeffreys prior, and take the predictive")
    log("   E[(1-q)^C(N,2)] per target, averaged over targets. This is the model that says")
    log("   'a question that gave 10 distinct answers still has a real chance of giving 20'.")
    log("")
    log("| stratum | budget | power law in k | pairwise Beta-Binomial | coupling upper "
        "bound |")
    log("| --- | --- | --- | --- | --- |")
    preds: dict[tuple[str, int], tuple[float, float]] = {}
    slopes: dict[str, float] = {}
    for name, ids in strata:
        curve = curves[name]
        ks = list(range(5, 11))
        xs = [math.log(k) for k in ks]
        ys = [math.log(curve[k]) for k in ks]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                 / sum((x - mx) ** 2 for x in xs))
        inter = my - slope * mx
        slopes[name] = slope
        sizes = [sorted(Counter(pool.assignments10[q]).values(), reverse=True)
                 for q in ids if q in pool.assignments10]
        for N in [b for b in budgets if b > 10]:
            pl = math.exp(inter + slope * math.log(N))
            bb = _beta_binomial_predictive(sizes, N)
            preds[(name, N)] = (pl, bb)
            log(f"| {name.split(' ')[0]} | N={N} | {pl:.1%} | {bb:.1%} | "
                f"<= {curve[10]:.1%} |")
    log("")
    neg_name = strata[0][0]
    log(f"(The power-law exponent on the correct stratum is {slopes[neg_name]:.2f}: the atom")
    log(f"falls only like k^{slopes[neg_name]:.2f}, so a doubling of the budget buys a factor")
    log(f"of {2 ** slopes[neg_name]:.2f}, not the collapse that pairwise independence would")
    log("give -- under independence the decay would be exponential in C(k,2), which the data")
    log("flatly rejects. The atom is carried by a subpopulation of questions the model")
    log("answers differently every single time, not by independent coin flips, and THAT is")
    log("the thing a larger budget has to break.)")
    log("")
    log("**The pre-registered prediction, written before the GPU is touched:** on the fair")
    log("pool's correct stratum the ceiling-atom mass -- and therefore the minimum non-zero")
    log("achievable FPR -- will land at roughly")
    log("")
    for N in [b for b in budgets if b > 10]:
        pl, bb = preds[(neg_name, N)]
        log(f"    N={N}:  {min(pl, bb):.1%} to {max(pl, bb):.1%}"
            f"   (hard upper bound from the coupling: {curves[neg_name][10]:.1%})")
    log("")
    straddlers = [N for N in [b for b in budgets if b > 10]
                  if min(preds[(neg_name, N)]) <= 0.05 <= max(preds[(neg_name, N)])
                  or abs(max(preds[(neg_name, N)]) - 0.05) < 0.02]
    below = [N for N in [b for b in budgets if b > 10]
             if max(preds[(neg_name, N)]) < 0.03]
    if straddlers:
        log(f"Note what that says: the predicted floor at **N={straddlers[0]}** sits ON the "
            "5% boundary the")
        log("paper's claim turns on -- the least decidable place it could land, and at n=200")
        log("an interval around it would cover 5% either way (section 6).")
    if below:
        log(f"**N={below[0]}** is the budget predicted to clear it, which is why the buy is "
            f"the larger one.")
    log("If the measurement comes in far above this band the prediction is simply wrong and")
    log("the paper's claim gets stronger; if it comes in far below, the finding becomes")
    log("'here is the budget that buys a 5% false-alarm rate'. Both are results. This")
    log("paragraph exists so that neither can be written after the fact.")
    log("")

    # ------------------------------------------------------------ 6. precision vs n
    log("## 6. What n buys: the precision of the answer, before it is bought")
    log("")
    log("The floor is a proportion, so its Wilson interval is fixed by n and by where the")
    log("floor lands. At the predicted values, here is what each pool size can conclude:")
    log("")
    log("| true floor | n=200 (fair pool) | n=400 | n=1424 (full correct stratum) | "
        "can n=200 certify 'no 5% operating point'? |")
    log("| --- | --- | --- | --- | --- |")
    for p in (0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.07, 0.095):
        cells = []
        for n in (200, 400, 1424):
            k = int(round(p * n))
            _, lo, hi = _wilson(k, n)
            cells.append(f"{lo:.1%}-{hi:.1%}")
        k200 = int(round(p * 200))
        _, _, hi200 = _wilson(k200, 200)
        verdict = ("**yes**, upper bound below 5%" if hi200 < 0.05
                   else "no -- interval covers 5%")
        log(f"| {p:.1%} | {cells[0]} | {cells[1]} | {cells[2]} | {verdict} |")
    log("")
    k_max_certify = max((k for k in range(0, 40) if _wilson(k, 200)[2] < 0.05), default=0)
    log(f"The crossover is sharp and worth knowing before the run: at n=200 the Wilson upper")
    log(f"bound clears 5% only when at most **{k_max_certify} of the 200** negatives sit at "
        f"the cap, i.e. a floor")
    log(f"of **{k_max_certify / 200:.1%}** or less. Above that the honest report is an "
        f"interval that covers 5%.")
    log("")
    log("Read this honestly: **n=200 answers the granularity question but not always the")
    log("sharp feasibility question.** If the floor lands near 4%, n=200 gives an interval")
    log("that still covers 5% and the claim 'a 5% budget is now purchasable' cannot be")
    log("made -- while the claim it replaces ('the achievable grid below 25% has more than")
    log("three points') is perfectly well resolved at 0.5% steps. Three consequences for")
    log("the buy:")
    log("")
    log("- The headline population stays the fair pool's correct stratum, n=200, because")
    log("  that is the population `paper/sections/methods.tex` commits to.")
    log("- **How many negatives each predicted floor would need**, if the paper wants to")
    log("  say 'no operating point at or below 5% exists' rather than quote an interval:")
    log("")
    log("  | budget | predicted floor | n needed to certify (pessimistic end) | "
        "n needed (optimistic end) |")
    log("  | --- | --- | --- | --- |")
    for N in [b for b in budgets if b > 10]:
        pl, bb = preds[(neg_name, N)]
        lo_p, hi_p = min(pl, bb), max(pl, bb)
        n_hi = n_needed_to_certify(hi_p)
        n_lo = n_needed_to_certify(lo_p)
        log(f"  | N={N} | {lo_p:.1%}-{hi_p:.1%} | "
            f"{n_hi if n_hi else 'unreachable -- too close to 5%'} | "
            f"{n_lo if n_lo else 'unreachable'} |")
    log("")
    log("  Read that as the honest limit of the n=200 headline: even at the budget whose")
    log("  floor is predicted lowest, certifying the 5% statement can need more negatives")
    log("  than the fair pool has. Quoting the interval is still a complete answer to the")
    log("  granularity question; it is the *feasibility* sentence that needs the extension.")
    log(f"- The extension, if triggered, runs along the SAME seed-0 shuffle")
    log(f"  (`_stratum_ids('right', {SEED})[:n]`), so it is a strict superset and the fair")
    log(f"  pool stays a prefix of it -- the same nesting discipline")
    log(f"  `results/achievable_fpr_grid.md` uses for its n=1424 companion. The full correct")
    log(f"  stratum has {pool.n_correct_available} members, so there is room. Sample costs:")
    for extra in (100, 200, 400):
        log(f"  - " + cost_line(f"{extra} further negatives at N={max(budgets)} "
                                f"(n={args.n_per_stratum + extra} in total)",
                                extra, extra * t_eval(max(budgets))))
    log("")

    # ------------------------------------------------------------ 7. averaging k
    log("## 7. The move an operator actually has: average k runs")
    log("")
    log("A reviewer will say it, so it goes in the paper: nobody needs a bigger N to")
    log("subdivide the grid. Run the N=10 detector k times and average, at k times the")
    log("cost. Worked out, and it does not rescue the detector:")
    log("")
    comp = averaging_comparison(10, (2, 3, 4), CENTRAL_SCENARIO)
    log("| k | average k runs at N=10 | equal-resolution single run | finest step at the "
        "top (nats) | cost of averaging | cost of the single run | single run / averaging |")
    log("| --- | --- | --- | --- | --- | --- | --- |")
    for c in comp:
        av = c["attainable_values_averaging"]
        sv = c["attainable_values_single_run"]
        log(f"| {c['k']} | {av if av is not None else '-'} attainable values | N="
            f"{c['n_equivalent']}, {sv if sv is not None else '-'} attainable values | "
            f"{c['top_step_nats']:.4f} | {c['cost_averaging_s']:.0f} s | "
            f"{c['cost_single_run_s']:.0f} s | **{c['ratio']:.2f}x** |")
    log("")
    log("**Averaging wins on price and loses on substance.** Both moves divide the last")
    log("step of the scale by the same factor -- averaging k runs at budget n gives steps of")
    log("(2 ln 2 / n)/k, one run at N = kn gives 2 ln 2/(kn) -- but clustering is quadratic")
    log("in the sample count, so k separate n-sized clusterings cost k*n(n-1) NLI passes")
    log("against kn(kn-1) for the single wide run. At k=4 that is the difference between")
    log(f"{comp[-1]['cost_averaging_s']:.0f} s and {comp[-1]['cost_single_run_s']:.0f} s per "
        f"target. Say so in the paper; do not let a reviewer")
    log("discover it.")
    log("")
    log("Three things averaging does not buy, and they are the ones the finding rests on:")
    log("")
    log("1. **It does not move the cap.** The maximum stays ln 10 = 2.3026 however many")
    log("   runs are averaged. Raising N raises it to ln N. Right-censoring of the")
    log("   hallucinating class -- the asymmetry that biases the clean AUROC downward -- is")
    log("   untouched by averaging.")
    log("2. **It does not dissolve the atom, it only shrinks it toward a hard floor.** The")
    log("   averaged score sits at the cap iff EVERY run saturates, so the residual atom is")
    log("   E_q[p(q)^k] over the question distribution. By Jensen that is at least (E p)^k,")
    log("   and more to the point it converges to the mass of questions the model answers")
    log("   10 different ways EVERY time -- a subpopulation averaging can never split,")
    log("   because those items are deterministic, not noisy. Section 5's decay curve says")
    log("   that subpopulation is exactly what carries the atom.")
    log("3. **It does not reduce the estimator's bias.** The plug-in entropy of N samples")
    log("   is biased low, and averaging k of them is a variance reduction of the SAME")
    log("   biased functional: it converges to E[H_10], not to the semantic entropy.")
    log("   Raising N is the only one of the two that attacks the bias, which is the")
    log("   mechanism `mccabe2025alphabet` / `pan2026shade` describe.")
    log("")
    log("So the honest paper sentence is: *the grid can be subdivided cheaply by averaging")
    log("repeated runs, which is cheaper than raising N and is what an operator should do;")
    log("but averaging cannot lower the floor below the mass of questions that saturate")
    log("every time, and only a larger N attacks that mass.* Whether it does is section 5's")
    log("prediction and this run's measurement.")
    log("")

    # ------------------------------------------------------------ 8. recommendation
    log("## 8. Recommendation")
    log("")
    top = max(budgets)
    log(f"1. **Buy one pass at N={top}, both strata** -- "
        + cost_line("the buy", 2 * args.n_per_stratum,
                    2 * args.n_per_stratum * t_eval(top)).split(': ', 1)[1] + ".")
    log("   Every budget k <= 40 then comes free by replay, including N=20 and the N=10")
    log("   control, and the deliverable is a curve rather than three points.")
    log("2. **Do not buy a separate N=20 pass for the headline.** It is the least decidable")
    log("   budget (section 5 predicts it lands on the 5% boundary) and it is recoverable")
    log("   from the N=40 pass anyway. Buy instead a **60-target direct N=20 cell** ("
        + cost_line("validation cell", 60, 60 * t_eval(20)).split(': ', 1)[1] + ")")
    log("   purely to confirm that the subset-derived N=20 grid matches a directly measured")
    log("   one. That is the only thing a direct N=20 run tells you that replay cannot.")
    log("3. **Re-derive N=10 from the cache as the control** (free) and additionally")
    log("   re-score 40 correct-stratum targets fresh at N=10 ("
        + cost_line("drift control", 40, 40 * t_eval(10)).split(': ', 1)[1] + ")")
    log("   to bound cache-vs-today drift, which no analysis currently rules out.")
    n_ext = 0
    if (neg_name, top) in preds:
        need = n_needed_to_certify(max(preds[(neg_name, top)]))
        n_ext = max(0, (need or 0) - args.n_per_stratum)
    log("4. **Hold the negative-stratum extension in reserve, and pre-commit its trigger.**")
    log("   Section 6: quoting the floor as an interval needs nothing extra, but SAYING")
    log("   'no operating point at or below 5% exists' needs the Wilson upper bound under")
    log(f"   5%, which at n={args.n_per_stratum} requires at most {k_max_certify} negatives "
        f"at the cap ({k_max_certify / args.n_per_stratum:.1%}).")
    if n_ext:
        log(f"   If the floor lands at the pessimistic end of the N={top} prediction "
            f"({max(preds[(neg_name, top)]):.1%}), the")
        log(f"   certifying n is ~{args.n_per_stratum + n_ext}, so the extension is "
            f"{n_ext} further negatives along the")
        log("   same seed-0 shuffle: " + cost_line("the extension", n_ext,
                                                   n_ext * t_eval(top)).split(': ', 1)[1]
            + ".")
    log("   Trigger it on the measured floor, not on a hunch, and write the trigger down")
    log("   before the run so the extension cannot be a reaction to an unwelcome interval.")
    total_s = (2 * args.n_per_stratum * t_eval(top) + 60 * t_eval(20) + 40 * t_eval(10))
    log("5. **Queue it behind the null control, not against it.** Total for items 1-3 is "
        + f"~{total_s / 3600:.1f} "
        + f"GPU-h at n={2 * args.n_per_stratum + 100} evals "
        + f"(worst case {(total_s * t_eval(top, 'loaded') / t_eval(top)) / 3600:.1f} GPU-h "
        + f"at the same n), against ~67 GPU-h for the")
    log("   null control and 33 days remaining. It is affordable; it is not free of the")
    log(f"   device. With item 4 triggered it is at most "
        f"~{(total_s + n_ext * t_eval(top)) / 3600:.1f} GPU-h at "
        f"n={2 * args.n_per_stratum + 100 + n_ext} evals.")
    log("")
    log("What each outcome licenses, written before the data:")
    log("")
    log("| measured floor at N=40 | what the paper says |")
    log("| --- | --- |")
    log("| still >= ~9% | the floor is a property of the model's answer distribution, not "
        "of the sample budget. The operating-point finding generalises across a 4x budget "
        "range and the granularity framing is at its strongest. |")
    log("| ~2-5% | the floor is relaxable and the paper reports the budget-response curve: "
        "'at the N this literature uses you cannot buy a 5% false-alarm rate; here is what "
        "it costs to buy one'. More useful to a practitioner, and it retires the last of "
        "the non-relaxability framing cleanly. |")
    log("| < ~1% | granularity is not the operator's problem at N=40; the paper's "
        "contribution narrows to the measurement protocol plus the cost curve, and the "
        "abstract must say so. |")
    log("")
    log("None of the three is a failure, and the run is worth buying precisely because the")
    log("three bands ARE separable at n=200: a 9.5% floor and a 2% floor have disjoint")
    log("Wilson intervals there. What n=200 cannot always do is the narrower thing -- put a")
    log("one-sided certificate under 5% -- and section 6 prices that separately rather than")
    log("letting it quietly become a reason to call the whole run underpowered.")
    log("")

    # ------------------------------------------------------------ 9. reproduction
    log("## 9. Reproduction, resume and provenance")
    log("")
    log("```")
    log("# cost only, no model load, no cache (prints n on every hours line)")
    log(".venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --estimate-only")
    log("")
    log("# this file")
    log(".venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --derive-only")
    log("")
    log("# the measurement, inside WSL where the GPU is")
    log("./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 40 --strata both")
    log("")
    log("# the same, resumed after a kill: identical command, skips completed targets")
    log("./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 40 --strata both")
    log("")
    log("# the N=20 validation cell (does replay match a direct measurement?)")
    log("./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 20 --strata correct "
        "--limit 60")
    log("")
    log("# the N=10 drift control (is the Week-4 cache still what this box produces?)")
    log("./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 10 --strata correct "
        "--limit 40")
    log("")
    log("# rebuild every table from the checkpoint, scoring nothing")
    log(".venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --report-only")
    log("")
    log("# a dry run of the whole loop with a fake scorer, no GPU and no model")
    log(".venv\\Scripts\\python.exe scripts\\n_scaling_grid.py --smoke --limit 25 "
        "--checkpoint /tmp/smoke.jsonl")
    log("```")
    log("")
    log(f"- checkpoint: `{args.checkpoint}` -- one appended, flushed, fsync'd line per")
    log("  completed evaluation, keyed by (question_id, N, seed, max_new_tokens). Killing")
    log("  the run costs the target in flight and nothing else.")
    log("- the checkpoint carries the C(N,2) verdict matrix, so every smaller budget is")
    log("  recomputable offline and the run never has to be repeated to answer a question")
    log("  about a budget nobody thought to ask for.")
    log("- ids: `fair_pool_granularity.fair_pool_ids` (the same ids as the clean AUROC and")
    log("  the same ids as `results/achievable_fpr_grid.md`)")
    log("- threshold rule: `se.stats.attainable_fprs` / `operating_point` (fixed")
    log("  2026-08-13); the grid table itself is `achievable_fpr_grid.grid`, imported, not")
    log("  reimplemented")
    log("- intervals: Wilson score, 95%, `fair_pool_granularity.wilson`")
    log(f"- Week-4 cache read for the N=10 control: `{cache}`")
    log("- tests: `tests/test_n_scaling_grid.py` (CPU only, no cache, no model): the")
    log("  lattice counts and the 2 ln 2 / N identity, the subset-replay round trip, the")
    log("  coupling containment per realisation, the grid construction at N=20/40, the")
    log("  quadratic cost term, checkpoint resume, and the rule that every hours figure")
    log("  carries its n")
    log("")

    out = RESULTS_DIR / "n_scaling_plan.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


def _beta_binomial_predictive(sizes_list: list[list[int]], N: int) -> float:
    """Mean over targets of E[(1-q)^C(N,2)] with q ~ Beta(Jeffreys | merged pairs).

    Per target: of the C(10,2) pairs, sum C(c_i,2) landed in the same cluster. Treating
    those as Binomial(C(10,2), q) with a Jeffreys prior gives q ~ Beta(0.5+m, 0.5+M-m),
    and the probability that all N samples are pairwise inequivalent is E[(1-q)^C(N,2)],
    which is a ratio of Beta functions. Deliberately generous to relaxation: the merged
    pair count includes pairs merged only by transitive closure, so q is over-estimated
    and the predicted atom comes out too small."""
    from math import lgamma

    def logbeta(x: float, y: float) -> float:
        return lgamma(x) + lgamma(y) - lgamma(x + y)

    if not sizes_list:
        return float("nan")
    tot = 0.0
    for sizes in sizes_list:
        n = sum(sizes)
        m = sum(c * (c - 1) // 2 for c in sizes)
        M = math.comb(n, 2)
        a, b = 0.5 + m, 0.5 + (M - m)
        tot += math.exp(logbeta(a, b + math.comb(N, 2)) - logbeta(a, b))
    return tot / len(sizes_list)


# ------------------------------------------------------------------- the run report
def write_grid_report(args, records: list[dict], pool: Pool) -> int:
    from achievable_fpr_grid import n_firing_below
    from se.stats import operating_point

    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    measured_budgets = sorted({int(r["n_samples"]) for r in records})
    top = max(measured_budgets) if measured_budgets else 0
    budgets = [b for b in sorted(set(list(args.budgets) + measured_budgets)) if b <= top]
    n_neg = len(pool.correct_ids)

    # A checkpoint written by the fake scorer says so in every record, so `--report-only`
    # on a smoke checkpoint cannot launder fake numbers into the real report.
    smoke = (bool(getattr(args, "smoke", False))
             or any(r.get("scorer") == "fake" for r in records))
    log("# Budget scaling of the achievable-FPR grid: measured")
    log("")
    if smoke:
        log("> **SMOKE RUN -- THE NUMBERS BELOW ARE FROM A FAKE SCORER AND MEAN NOTHING.**")
        log("> No model was loaded. This file exists only to show that the loop, the")
        log("> checkpoint, the replay and the report all work. Do not cite it, do not")
        log("> copy a number out of it.")
        log("")
    log(f"Generated {generated_date('n_scaling_grid.md', args)} by "
        "`scripts/n_scaling_grid.py`.")
    log(f"Budgets measured directly: {measured_budgets}. Budgets derived by replaying the")
    log("recorded pairwise verdicts on random subsets: everything else below.")
    log("")

    # N=10 control, from the cache
    neg10_cache = np.array([round(pool.entropy10[q], DP) for q in pool.correct_ids
                            if q in pool.entropy10])
    pos10_cache = np.array([round(pool.entropy10[q], DP) for q in pool.wrong_ids
                            if q in pool.entropy10])

    # -------------------------------------------------- assemble the scores per budget
    def scores_at(b: int) -> tuple[np.ndarray, np.ndarray, str]:
        """(negatives, positives, provenance) at budget b."""
        if b == 10 and 10 not in measured_budgets:
            return neg10_cache, pos10_cache, "Week-4 cache"
        sneg = budget_scores(records, b, "correct", replicate=0)
        spos = budget_scores(records, b, "hallucinating", replicate=0)
        neg = np.array([round(v, DP) for v in sneg.values()])
        pos = np.array([round(v, DP) for v in spos.values()])
        src = "measured" if b in measured_budgets else f"replay of N={top}, replicate 0"
        return neg, pos, src

    has_positives = any(r["stratum"] == "hallucinating" for r in records) or len(
        pos10_cache) > 0

    log("## 1. Floor and grid, by budget")
    log("")
    log("**The floor is the first firing point, which is not always the ceiling atom.**")
    log("Every threshold above ln N flags nothing, so while targets remain AT the cap the")
    log("first threshold that fires flags exactly those targets and the floor equals the")
    log("at-cap mass. Once the atom empties, that identity breaks: the floor is then set by")
    log("the largest score strictly below the cap and is strictly LARGER than the at-cap")
    log("mass, which is 0. The two are reported in separate columns for that reason -- read")
    log("the floor column, not the at-cap column, for the smallest false-alarm rate an")
    log("operator can actually buy at this budget.")
    log("")
    log("| budget N | source | n negatives | floor = min non-zero FPR (1st firing point) | "
        "at-cap mass (targets at the ln N ceiling) | next FPR (2nd firing point) | "
        "firing points at or below 5% | at or below 10% | at or below 25% |")
    log("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    rows_by_budget: dict[int, list[dict]] = {}
    scores_by_budget: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    src_by_budget: dict[int, str] = {}
    atom_breaks: list[tuple[int, str, str]] = []
    for b in budgets:
        neg, pos, src = scores_at(b)
        if len(neg) == 0:
            continue
        scores_by_budget[b] = (neg, pos)
        src_by_budget[b] = src
        rows = grid_for(neg, pos if len(pos) else np.array([0.0]))
        rows_by_budget[b] = rows
        c = floor_cells(neg, rows, b)
        if c["atom_is_empty_so_floor_differs"]:
            # n and the at-cap count travel WITH the row rather than being read off the
            # leaked loop variables below: `neg` would hold the LAST budget's negatives,
            # which is right today only because every row has the same n.
            atom_breaks.append((b, f"{c['floor_fpr']:.1%}", c["at_cap"], len(neg),
                                f"{c['at_cap_k']}/{len(neg)}"))
        log(f"| {b} | {src} | {len(neg)} | {c['floor']} | {c['at_cap']} | "
            f"{c['next']} | "
            f"{n_firing_below(rows, 0.05)} | {n_firing_below(rows, 0.10)} | "
            f"{n_firing_below(rows, 0.25)} |")
    log("")
    for b, fl, cap, n_neg, at_cap_count in atom_breaks:
        log(f"At N={b} the ceiling atom is empty ({cap}), so the floor and the at-cap mass")
        log(f"come apart: the smallest purchasable false-alarm rate is {fl}, NOT 0. There is")
        log(f"no sub-{fl} operating point at this budget.")
        log("")
        log(f"**And the floor at N={b} is printed WITHOUT an interval, which is a finding")
        log("rather than an omission.** The same event that separates these two columns --")
        log("the empty atom -- also stops the floor being IDENTIFIED. Its threshold is no")
        log("longer ln N, fixed in advance, but the top score this pool happened to reach,")
        log("and whether that rung is the top of the population's support is a question")
        log(f"{n_neg} answers cannot settle. The two answers differ by more than two")
        log("orders of magnitude: if the population can never produce 39 mutually")
        log(f"inequivalent answers out of {b}, then {fl} IS the population quantity and no")
        log("larger pool reports a smaller floor; if it can, the true floor sits")
        log(f"arbitrarily far below {fl}. Nothing in this data chooses between them --")
        log(f"{at_cap_count} is a p=0.1175 outcome under the fitted model, and the")
        log("model-free bound on the rate, [0%, 1.88%], contains both zero and the")
        log("model's 1.065%. An estimand whose value moves by two orders of magnitude")
        log("across a hypothesis the sample cannot test does not have a confidence")
        log("interval, and that argument needs no population model at all.")
        log("")
        log("**Coverage depends on which branch holds, so never quote it without naming")
        log("the population it was measured under.** At a nominal 95%:")
        log("")
        log("| population | Wilson on the first-firing count | question bootstrap |")
        log("| --- | --- | --- |")
        log("| calibrated Ewens (tau_top = 0.2726%) | 53.67% | 0.00% |")
        log(f"| zero branch (tau* = {fl}) | 95.06% | 100% |")
        log("")
        log("\"Both estimators fail\" is a statement about the first row only, and the")
        log("data does not exclude the second. What is true in BOTH rows is that quoting")
        log("either interval means committing to a branch this sample cannot decide.")
        log("Each also has an endpoint placed by construction -- the bootstrap cannot")
        log("return less than 1 negative in n, and Wilson counts a rung the population")
        log("may not have. So the cell prints the count and the rate and no interval.")
        log(f"`results/n40_floor_estimator_ruling.md` sections 2, 8.4 and 13 settle this;")
        log("the at-cap column is the one that keeps an interval, because ln N really is")
        log("fixed a priori.")
        log("")

    # The replayed rows are one subset draw. The paper quotes a different estimator, and the
    # two are close enough to be mistaken for each other -- which is the whole reason for
    # spelling it out at the table rather than in a footnote.
    replayed = [b for b in scores_by_budget if src_by_budget[b].startswith("replay")]
    if replayed:
        log("**The replayed rows are ONE subset draw, and the paper quotes a different")
        log("estimator.** Every row above marked `replicate 0` is a single uniformly random")
        log("subset per question. Its Wilson interval is the correct interval FOR THAT")
        log("estimator, and not a narrow one: by the variance identity in")
        log(f"`{SUBSET_AVERAGED_FLOOR_FILE}` {SUBSET_AVERAGED_FLOOR_SEC}, a single "
            f"replicate's binomial")
        log("spread already contains the subset draw as well as the draw of questions, so")
        log("nothing is missing from it and nothing may be added to it. But a single")
        log("replicate is not what the paper reports. The paper reports the subset-AVERAGED")
        log("floor -- the mean of the 200 per-question saturation probabilities -- whose")
        log("interval is a bootstrap over questions ONLY, because the subset draw has been")
        log("averaged out of the point estimate and putting it back would count it twice.")
        log("")
        for b in replayed:
            pt, ci = SUBSET_AVERAGED_FLOOR.get(b, (None, None))
            c = floor_cells(scores_by_budget[b][0], rows_by_budget[b], b)
            if pt is None:
                log(f"- N={b}: replicate 0 above reads {c['floor']}. The subset-averaged")
                log(f"  floor for this budget is not tabulated in "
                    f"`{SUBSET_AVERAGED_FLOOR_FILE}`,")
                log("  so this row has no quotable counterpart -- do not lift it.")
                continue
            log(f"- N={b}: this report's replicate 0 reads {c['floor']}. The quotable")
            log(f"  subset-averaged floor is **{pt} {ci}**, by question bootstrap, from")
            log(f"  `{SUBSET_AVERAGED_FLOOR_FILE}` {SUBSET_AVERAGED_FLOOR_SEC} as of "
                f"{SUBSET_AVERAGED_FLOOR_ASOF}.")
            log("  Quote that one, from that file. The two point estimates are")
            log("  near-identical and their intervals are not, so a row lifted from here")
            log("  would carry the wrong width for the wrong estimator.")
        log("")

    if not has_positives:
        log("(`--strata correct` was used, so there is no TPR column anywhere in this")
        log("report. The FPR grid and the floor are unaffected -- FPR is a within-negatives")
        log("quantity -- but no achievable point can be priced in detections.)")
        log("")

    # -------------------------------------------------------------- the drift control
    if 10 in measured_budgets and len(neg10_cache):
        fresh = np.array([round(v, DP) for v in
                          budget_scores(records, 10, "correct").values()])
        kc, nc = ceiling_atom(neg10_cache, 10)
        kf, nf = ceiling_atom(fresh, 10)
        log("**The drift control.** N=10 was re-scored fresh on this box and compared")
        log("against the Week-4 cache, which nothing else in the project currently checks.")
        log("")
        log(f"- Week-4 cache, n={nc}: floor = {fmt_prop(kc, nc)}")
        log(f"- re-scored today, n={nf}: floor = {fmt_prop(kf, nf)}")
        log("")
        log("A gap here would mean the cached N=10 baseline and any new budget were")
        log("produced by materially different machines or library versions, and the")
        log("budget-scaling comparison would be confounded by that rather than by N.")
        log("")

    # ----------------------------------------------------------- the subsetting control
    if 10 in scores_by_budget and 10 not in measured_budgets and len(neg10_cache):
        log("**The subsetting control.** Everything at a budget below the one actually run")
        log("is a replay of random subsets, so the method has to be checked against a")
        log("directly measured grid at the same budget. The Week-4 cache is exactly that at")
        log("N=10.")
        log("")
        # The floor here is the FIRST FIRING POINT, the same quantity the section-1 column
        # reports -- not `ceiling_atom`, which is what this block used to call. At N=10 the
        # atom is non-empty on both arms so the two definitions coincide and the printed
        # numbers do not move; the point is that this block may no longer print the at-cap
        # mass under the word "floor", which is precisely the swap `floor_cells` exists to
        # prevent and the one that put a 0.0% floor in the N=40 row.
        def _floor_of(arr: np.ndarray) -> float | None:
            return floor_cells(arr, grid_for(arr, np.array([0.0])), 10)["floor_fpr"]

        floors = []
        for r in range(20):
            arr = np.array([round(v, DP) for v in
                            budget_scores(records, 10, "correct", replicate=r).values()])
            f = _floor_of(arr) if len(arr) else None
            if f is not None:
                floors.append(f)
        c10 = floor_cells(neg10_cache, grid_for(neg10_cache, np.array([0.0])), 10)
        log(f"- Week-4 cache, direct N=10 (June generation run): floor = {c10['floor']}")
        if floors:
            log(f"- replay of 10-subsets of the N={top} run (August), 20 replicates: floor "
                f"median {np.median(floors):.1%}, range "
                f"{min(floors):.1%}-{max(floors):.1%}")
            log("")
            log("**These two arms do not disagree -- and a gap between them would not have")
            log("condemned the replay.** This block used to close with a decision rule: if the")
            log("arms disagree beyond the Wilson interval the subsetting is unsound and no")
            log("replayed budget in this report may be quoted. That rule is WITHDRAWN. It was")
            log("applied, it read 20 replicates all landing above the direct value as a sign")
            log("test at 2^-20, and the inference does not hold. `results/replay_control.md`")
            log("sections 1 and 3 redo this control at 200 draws and give the account that")
            log("replaces it:")
            log("")
            log("1. **The replay estimator is unbiased, and that is a theorem rather than a")
            log("   hope.** A question's samples are i.i.d. and therefore exchangeable, so a")
            log("   uniformly random 10-subset of the recorded 40 has exactly the distribution")
            log("   of 10 i.i.d. draws; and the clusterer is union-find over PAIRWISE")
            log("   verdicts, so a subset's clustering depends only on the verdicts inside it")
            log("   and is exactly what a direct 10-sample run on those samples would have")
            log("   produced. E[replayed score] = E[direct score], question by question.")
            log("2. **Reusing one verdict matrix correlates the replicates; it does not bias")
            log("   their mean.** Every replicate conditions on the same 40 samples and the")
            log("   same 200 questions, so the spread across replicates is subset-draw noise")
            log("   about a CONDITIONAL MEAN. The retired sign test's null was that each")
            log("   replicate is an independent coin flip about the direct value. They are")
            log("   neither independent nor centred there, and they do not have to be: the")
            log("   direct value is itself one draw of a 10-sample run. It sits in the LOWER")
            log("   TAIL of the replicate distribution and well inside it, so a unanimous run")
            log("   of 20 is unremarkable: a probability of a few tenths, which")
            log("   `results/replay_control.md` section 1 measures at 0.36 -- not 2^-20. And")
            log("   the correlation between replicates pushes that number UP, not down.")
            log("3. **The two arms estimate different parameters, so neither is the odd one")
            log("   out.** The replay is unbiased for the generation run recorded in THIS")
            log("   checkpoint (August); the direct cache is one unbiased realisation of the")
            log("   run that produced it (June). Those two runs differ measurably in the text")
            log("   they emitted under an identical config -- mean answer length +3.6 chars")
            log("   paired, z = +4.0. Two unbiased estimators of two different parameters is")
            log("   not one sound arm and one unsound arm, and which of them is \"sounder\"")
            log("   stops being a statistical question at that point.")
            log("")
            log("So what this control licenses is a LABELLING rule, not a gate: report a")
            log("budget trend entirely inside one family and say which family, and keep the")
            log("direct N=10 row on its June provenance wherever the paper quotes it -- every")
            log("other N=10 number in the paper is welded to that cache. Read")
            log("`results/replay_control.md` before quoting any comparison ACROSS the two")
            log("arms; the step between them, its interval and its two candidate causes are")
            log("that file's subject and not this one's.")
        log("")

    # ------------------------------------------------------------ the decay of the atom
    if top >= 4:
        log("## 2. The ceiling atom against the sample budget (the curve the paper needs)")
        log("")
        log("Exact per target, not an extrapolation: a set of samples is all-singletons iff")
        log("no pair inside it is equivalent, so the recorded verdict matrix answers it for")
        log("every subset size directly.")
        log("")
        rng = np.random.default_rng(SEED)
        ks = [k for k in (2, 3, 5, 10, 15, 20, 30, 40) if k <= top]
        log("| budget k | " + " | ".join(str(k) for k in ks) + " |")
        log("| --- | " + " | ".join("---" for _ in ks) + " |")
        for stratum in (["correct", "hallucinating"] if has_positives else ["correct"]):
            rs = [r for r in records if r["stratum"] == stratum
                  and int(r["n_samples"]) == top]
            if not rs:
                continue
            cells = []
            for k in ks:
                v = sum(subset_ceiling_prob(r["verdict_bits"], top, k, rng) for r in rs)
                cells.append(f"{v / len(rs):.3f}")
            log(f"| {stratum} (n={len(rs)}) | " + " | ".join(cells) + " |")
        log("")
        log("The `correct` row is the AT-CAP MASS as a function of the sample budget, which")
        log("is the achievable-FPR floor only while the atom is non-empty. Where the row")
        log("reads 0.000 the atom has emptied and the floor is strictly larger -- take the")
        log("floor from the floor column of section 1, never from this row. Compare it")
        log("against the pre-registered prediction in `results/n_scaling_plan.md` section 5")
        log("before writing any prose about it.")
        log("")

    log("## 3. The operator's menu at each budget")
    log("")
    log("| budget | target FPR | `at_most` achieved | TPR | `closest` achieved | TPR |")
    log("| --- | --- | --- | --- | --- | --- |")
    for b, (nn, pp) in scores_by_budget.items():
        y = np.concatenate([np.zeros(len(nn), int), np.ones(len(pp), int)])
        s = np.concatenate([nn, pp])
        for t in NOMINAL_TARGETS:
            a = operating_point(y, s, target_fpr=t, mode="at_most")
            c = operating_point(y, s, target_fpr=t, mode="closest")
            tpr_a = f"{float((pp >= float(a)).mean()):.1%}" if len(pp) else "-"
            tpr_c = f"{float((pp >= float(c)).mean()):.1%}" if len(pp) else "-"
            log(f"| {b} | {t:.0%} | {a.achieved_fpr:.1%}"
                f"{' (flags nothing)' if a.flags_nothing else ''} | {tpr_a} | "
                f"{c.achieved_fpr:.1%}"
                f"{'' if c.honours_contract else ' **over budget**'} | {tpr_c} |")
    log("")

    log("## 4. Measured throughput (this replaces every cost estimate that preceded it)")
    log("")
    m = measured_throughput(records)
    log("| N | evals | median s/eval | median s in NLI | model predicted | ratio |")
    log("| --- | --- | --- | --- | --- | --- |")
    for n, mm in m.items():
        log(f"| {n} | {mm['n_evals']} | {mm['s_total']:.1f} | {mm['s_nli']:.1f} | "
            f"{t_eval(n):.1f} | {mm['s_total'] / t_eval(n):.2f}x |")
    log("")
    for n, mm in m.items():
        log("- " + cost_line(f"measured, N={n}", mm["n_evals"],
                             mm["n_evals"] * mm["s_total"]))
    log("")
    log("## 5. Provenance")
    log("")
    log(f"- checkpoint: `{args.checkpoint}` ({len(records)} evaluations)")
    log(f"- ids: fair pool, `select_stratified(want, {args.n_per_stratum}, seed={SEED})`")
    log(f"- generation: max_new_tokens={args.max_new_tokens}, T=1.0, top_p=1.0, "
        f"seed={args.seed}")
    log("- plan, cost model and the derivations that need no data: "
        "`results/n_scaling_plan.md`")
    log("- the replay control -- what the subsetting does, which interval belongs to which")
    log("  estimator, and the subset-averaged floors the paper actually quotes: "
        "`results/replay_control.md`")
    log("")

    # A fake-scorer report must never be able to be mistaken for the real one: it gets a
    # different name AND is written beside its checkpoint rather than into results/, which
    # is a tracked directory whose .md files are read as findings.
    out = (Path(args.checkpoint).with_name("n_scaling_grid_SMOKE.md") if smoke
           else RESULTS_DIR / "n_scaling_grid.md")
    # newline="\n" explicitly: without it the default translation writes CRLF on Windows and
    # LF under WSL, so the same checkpoint regenerated on the two boxes yields a file that
    # differs on every line. `.gitattributes` normalises `*.md` to LF at commit, which hides
    # that churn in `git diff` but not in a byte-level determinism check.
    out.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


# =============================================================================== main
def build_targets(pool: Pool, strata: str, limit: int | None) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    groups = [("correct", pool.correct_ids)]
    if strata == "both":
        groups.append(("hallucinating", pool.wrong_ids))
    for name, ids in groups:
        chosen = ids[:limit] if limit else ids
        for q in chosen:
            question = pool.questions.get(q)
            if question is None:
                raise SystemExit(f"no question text cached for {q}; the Week-4 "
                                 f"samples.jsonl is required to re-score it")
            out.append((name, q, question))
    return out


# ----------------------------------------------------- the report date stamps, pinned
# NOT date.today(). A wall-clock stamp means a regenerated report always byte-differs from
# the committed one, which destroys "the file is unchanged" as a check -- the cheapest
# check there is, and the one you want most after editing a 1900-line generator. The date
# is an INPUT: it records the run the report describes, not the moment someone reran the
# script. Bump it when the DATA changes. This is the fix `scripts/replay_control.py`
# already carries; it was scoped to that one file.
#
# PER REPORT, not one constant. These two reports describe runs on different days -- the
# plan was derived on 2026-08-13 and the measured grid on 2026-08-19 -- and a single stamp
# would silently re-date one of them, which is worse than the defect being fixed.
GENERATED_DATES = {
    "n_scaling_plan.md": "2026-08-13",       # --derive-only: design and cost, no new data
    "n_scaling_grid.md": "2026-08-19",       # the measured grid
    "cost-estimate": "2026-08-19",           # --estimate-only: stdout, not an artifact
}


def generated_date(key: str, args=None) -> str:
    """The pinned stamp for one report, or the `--generated` override if one was passed."""
    override = getattr(args, "generated", None)
    return override or GENERATED_DATES[key]


def estimate_only(args) -> int:
    """Cost from measured throughput. No model load, no cache, no torch import."""
    lines: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        lines.append(s)

    budgets = tuple(args.budgets)
    ck = _read_jsonl(args.checkpoint)
    measured = measured_throughput(ck) if ck else None
    log(f"# n_scaling_grid cost estimate  ({generated_date('cost-estimate', args)})")
    log("")
    log("Source of the per-eval numbers: "
        + ("the LIVE CHECKPOINT plus the repo's measured anchors for budgets not yet run"
           if measured else "this repo's measured throughput anchors"))
    log("")
    for line in COST_PROVENANCE:
        log(f"  {line}")
    log("")
    cost_section(log, budgets, args.n_per_stratum, args.strata == "both", measured)
    log("Every hours figure above names the n it was computed on, on the same line. If you")
    log("are quoting one of these numbers somewhere else, quote the n with it.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n_samples", type=int, default=40,
                    help="the sample budget to MEASURE (default 40; smaller budgets are "
                         "then derived by replay at zero GPU cost)")
    ap.add_argument("--budgets", type=lambda s: [int(x) for x in s.split(",")],
                    default=list(DEFAULT_BUDGETS),
                    help="budgets to report on (default 10,20,40)")
    ap.add_argument("--strata", choices=("correct", "both"), default="both",
                    help="'correct' gives the FPR grid and the floor; 'both' adds the "
                         "hallucinating stratum so every achievable point carries a TPR. "
                         "'both' exactly doubles the bill; both costs are reported.")
    ap.add_argument("--n_per_stratum", type=int, default=N_PER_STRATUM)
    ap.add_argument("--limit", type=int, default=None,
                    help="score only the first LIMIT targets of each stratum")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--max_new_tokens", type=int, default=MAX_NEW_TOKENS)
    ap.add_argument("--checkpoint", default=str(RESULTS_DIR / "n_scaling_ckpt.jsonl"))
    ap.add_argument("--cache", default=None, help="the Week-4 sample cache directory")
    ap.add_argument("--no-samples", action="store_true",
                    help="do not store sample text in the checkpoint (scores and verdict "
                         "bits are always stored)")
    ap.add_argument("--generated", default=None,
                    help="date stamped in the report header. Defaults to the "
                         "pinned date for whichever report is being written "
                         "(see GENERATED_DATES); regenerating without changing "
                         "the data must reproduce the file byte for byte.")
    ap.add_argument("--estimate-only", action="store_true")
    ap.add_argument("--derive-only", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="drive the whole loop with a deterministic fake scorer (no GPU)")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild the report from the checkpoint without scoring anything")
    args = ap.parse_args(argv)

    if args.estimate_only:
        return estimate_only(args)
    if args.derive_only:
        return write_plan(args)

    cache = resolve_cache(args.cache)
    pool = load_pool(cache, args.n_per_stratum)
    targets = build_targets(pool, args.strata, args.limit)
    ckpt = Path(args.checkpoint)

    if args.report_only:
        records = _read_jsonl(ckpt)
        if not records:
            raise SystemExit(f"nothing in {ckpt} to report on")
        return write_grid_report(args, records, pool)

    scorer = make_fake_scorer() if args.smoke else make_gpu_scorer(args.max_new_tokens)
    if args.smoke:
        print("[smoke] deterministic fake scorer; no model is loaded", flush=True)
    records = run_measurement(targets, args.n_samples, args.seed, ckpt, scorer,
                              store_samples=not args.no_samples,
                              max_new_tokens=args.max_new_tokens,
                              scorer="fake" if args.smoke else "gpu")
    return write_grid_report(args, records, pool)


if __name__ == "__main__":
    sys.exit(main())
