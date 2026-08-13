"""What the judge still owes: conditions (ii) and (iii) of results/judge_validation.md.

WHY THIS SCRIPT EXISTS
----------------------
`results/judge_validation.md` licenses the LLM-judge as the false-alarm adjudicator on a
re-spec that the paper repeats in Methods: the judge fails its pre-registered
positive-recognition gate (0.650 against a required 0.8), but over-splitting genuine
aliases INFLATES the baseline entropy, so a surviving false-alarm effect is understated ->
conservative -> usable.

That argument is only valid if the over-splitting is UNIFORM ACROSS CONDITIONS. The attack
selects paraphrases that maximise answer-set diversity, which is exactly the regime where a
judge with a 35% false-split rate would split MORE -- inflating the ATTACKED score, not the
baseline, and making the adjudication ANTI-conservative. Condition (iii) is the measurement
that decides the sign of that argument, and it has never been run.

This script does the part that needs no GPU:

  A. LATTICE INVERSION. At N=10 the discrete entropy takes 39 distinct values over the
     p(10)=42 integer partitions, so a stored entropy_nats almost always identifies the
     cluster-size partition -- and hence K -- EXACTLY. The three coincidences are enumerated
     and each is ambiguous by exactly one cluster. This turns every campaign JSONL, which
     stores entropies and discards clusterings, into a source of cluster COUNTS.
  B. INVERTER VALIDATION against `wk4_full_2000q/entropy.jsonl`, which stores BOTH
     `entropy_nats` and `n_clusters` -- 2000 independent checks of the inversion.
  C. THE (iii)-PRELIMINARY: paired attack-vs-benign cluster counts on the real campaign,
     n=80 FA. Under the NLI clusterer only -- the judge was never run on the campaign --
     so it measures the EXPOSURE (how far the attack moves the clustering regime), not the
     judge's differential behaviour. Reported as such.
  D. FALSE-SPLIT EXPOSURE and the (ii) INVENTORY: the cached samples ARE messy real
     sampled pairs (mean ~20 words), and `samples_correct` supplies an oracle-derived
     equivalence label on 74% of the pairs at zero cost. This is what makes (ii) closable.
  E. COST MODEL for the GPU run that closes both, and the PRE-REGISTERED margins, derived
     from the empirical nats-per-cluster slope rather than asserted.

NO GPU. NO MODEL. Standalone stdlib so it runs while the device is busy. Read-only over the
caches; writes nothing unless --out is given.

The prose report that consumes these numbers is `results/judge_owed_conditions.md`.

USAGE
-----
  # from WSL, where the cache lives:
  ./.venv-wsl/bin/python scripts/judge_owed_conditions.py
  ./.venv-wsl/bin/python scripts/judge_owed_conditions.py --cache ~/.cache/se-research/samples
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

# Number of samples per question, pinned by GenConfig(n_samples=10) everywhere in the repo.
N_SAMPLES = 10
# Rounding used to key the entropy lattice. The stored entropies are float64 sums of the
# SAME arithmetic, so exact bit-equality is common but not guaranteed across builds; 9
# decimals is far tighter than the smallest gap between distinct lattice values (the two
# closest attainable values at N=10 differ by ~4.6e-03 nats) and far looser than float noise.
LATTICE_ROUND = 9


# ---------------------------------------------------------------------------
# A. the entropy lattice, and inverting it back to a cluster count
# ---------------------------------------------------------------------------
def partitions_of(n: int, largest: int | None = None):
    """Every integer partition of n, each as a non-increasing tuple."""
    if largest is None:
        largest = n
    if n == 0:
        yield ()
        return
    for k in range(min(n, largest), 0, -1):
        for rest in partitions_of(n - k, k):
            yield (k,) + rest


def entropy_of_counts(counts, base: str = "nats") -> float:
    """Shannon entropy of a cluster-size vector. Mirrors se.entropy.discrete_entropy."""
    total = sum(counts)
    if total == 0:
        return 0.0
    log = math.log if base == "nats" else math.log2
    return -sum((c / total) * log(c / total) for c in counts if c > 0)


def build_k_lattice(n: int = N_SAMPLES, rounding: int = LATTICE_ROUND) -> dict[float, list[tuple]]:
    """entropy -> every partition of n with that entropy. The inversion table."""
    lattice: dict[float, list[tuple]] = {}
    for p in partitions_of(n):
        lattice.setdefault(round(entropy_of_counts(p), rounding), []).append(p)
    return lattice


def lattice_collisions(lattice: dict) -> list[tuple[float, list[tuple], list[int]]]:
    """The entropy values shared by more than one partition, with their candidate Ks."""
    out = []
    for h, parts in sorted(lattice.items()):
        if len(parts) > 1:
            out.append((h, parts, sorted({len(p) for p in parts})))
    return out


def invert_cluster_count(h: float, lattice: dict, rounding: int = LATTICE_ROUND) -> list[int] | None:
    """Candidate cluster counts consistent with a stored discrete entropy.

    Returns a SORTED list (length 1 = K identified exactly, length 2 = ambiguous by one
    cluster) or None if the value is not on the lattice at all -- which would mean the
    record was not produced by a discrete N-sample clustering and must not be inverted.
    """
    parts = lattice.get(round(h, rounding))
    if parts is None:
        return None
    return sorted({len(p) for p in parts})


def validate_inverter(entropy_records, lattice) -> dict:
    """Check the inverter against records that store BOTH entropy_nats and n_clusters."""
    exact = ambiguous = mismatch = offlattice = 0
    for r in entropy_records:
        cands = invert_cluster_count(r["entropy_nats"], lattice)
        if cands is None:
            offlattice += 1
        elif len(cands) == 1:
            exact += 1 if cands[0] == r["n_clusters"] else 0
            mismatch += 0 if cands[0] == r["n_clusters"] else 1
        elif r["n_clusters"] in cands:
            ambiguous += 1
        else:
            mismatch += 1
    return {"n": len(entropy_records), "exact": exact, "ambiguous": ambiguous,
            "mismatch": mismatch, "off_lattice": offlattice}


# ---------------------------------------------------------------------------
# statistics: paired bootstrap, exact sign test, the pre-registered verdict
# ---------------------------------------------------------------------------
def paired_bootstrap_ci(diffs, *, seed: int = 0, n_boot: int = 20000, alpha: float = 0.05):
    """Percentile bootstrap over the PAIRED per-target differences (resample targets)."""
    if not diffs:
        raise ValueError("no paired differences")
    rnd = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_boot):
        means.append(sum(diffs[rnd.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return sum(diffs) / n, lo, hi


def _binom_pmf(k: int, n: int, p: float = 0.5) -> float:
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def sign_test_p(n_pos: int, n_neg: int) -> float:
    """Exact two-sided sign test. Ties are DROPPED (the standard convention)."""
    n = n_pos + n_neg
    if n == 0:
        return 1.0
    k = min(n_pos, n_neg)
    tail = sum(_binom_pmf(i, n) for i in range(k + 1))
    return min(1.0, 2 * tail)


def noninferiority_verdict(ci_lo: float, ci_hi: float, point: float, margin: float) -> str:
    """The PRE-REGISTERED three-way rule, for an estimand oriented so that POSITIVE means
    ANTI-CONSERVATIVE (the judge splits relatively MORE on the attacked side).

      FAIL          -- the whole interval is above zero, or the point estimate alone exceeds
                       the material margin. The conservativeness argument is refuted; the
                       judge is withdrawn as sole adjudicator.
      PASS          -- the interval rules out a differential as large as the margin.
                       Conservativeness is CERTIFIED, not merely un-refuted.
      INCONCLUSIVE  -- everything else, including a wide interval straddling zero. This is
                       the DEFAULT and it is NOT a pass: the judge stays one arm of the
                       bracket and no headline rests on it alone.
    """
    if margin <= 0:
        raise ValueError("margin must be positive")
    if ci_lo > 0.0 or point >= margin:
        return "FAIL"
    if ci_hi < margin:
        return "PASS"
    return "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# D. exposure and the (ii) inventory
# ---------------------------------------------------------------------------
def within_cluster_pairs(assignments) -> int:
    """Pairs the clusterer MERGED -- the pairs on which a false SPLIT is even possible."""
    return sum(n * (n - 1) // 2 for n in Counter(assignments).values())


def oracle_pair_strata(samples_correct) -> dict:
    """Oracle-derived equivalence labels over the C(n,2) sampled pairs of one question.

    `samples_correct[i]` is the span oracle's verdict that sample i names the gold answer.

      positive  -- BOTH samples name the gold answer, so both give the SAME answer to the
                   question. This is an ANSWER-equivalence label; it is NOT a claim that the
                   two full generations bidirectionally entail each other, and the two
                   relations differ substantially (see the NLI split rate this script
                   reports). It is the relation the judge's own prompt asks about.
      hard_neg  -- EXACTLY ONE names the gold answer, so the other does not: a genuine
                   non-equivalent pair, in messy sampled prose rather than clean aliases.
      unlabelled-- NEITHER names the gold answer. They may agree on a wrong answer or
                   disagree; the oracle cannot tell, and nothing here labels them.

    Both labels inherit the span oracle's error rate; the residual human task is to bound
    it, not to label every pair from scratch.
    """
    n = len(samples_correct)
    pos = hn = un = 0
    for i, j in combinations(range(n), 2):
        if samples_correct[i] and samples_correct[j]:
            pos += 1
        elif samples_correct[i] != samples_correct[j]:
            hn += 1
        else:
            un += 1
    return {"positive": pos, "hard_neg": hn, "unlabelled": un, "total": pos + hn + un}


def false_split_rate(assignments, samples_correct) -> tuple[int, int]:
    """(merged, split) over the ORACLE-POSITIVE pairs: how often a clusterer separates two
    samples that both name the gold answer. Returns raw counts so they can be pooled."""
    merged = split = 0
    for i, j in combinations(range(len(samples_correct)), 2):
        if samples_correct[i] and samples_correct[j]:
            if assignments[i] == assignments[j]:
                merged += 1
            else:
                split += 1
    return merged, split


def wilson_ci(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


# ---------------------------------------------------------------------------
# E. the GPU cost model
# ---------------------------------------------------------------------------
# Measured anchors, both from docs/critique_log.md:
#   entry 22 -- the batched judge at K=8: 13 full evaluations ~ 12 min/target => ~55 s per
#               evaluation (generate 10 samples + NLI + exact + embedding + judge cluster).
#   entry 22 -- the cheap arms (no judge) at K=180: ~25 GPU-h for n=80 = 185 evaluations
#               each => ~6.1 s per evaluation.
# The judge clustering is therefore ~49 s of the ~55 s, i.e. ~90% of the cost. Both anchors
# were taken with judge_batch_size=12 (the module default); the deployed chain now runs
# judge_batch_size=6 after an OOM at 12 with the victim and DeBERTa co-resident.
SEC_PER_EVAL_WITH_JUDGE_B12 = 55.0
SEC_PER_EVAL_CHEAP_ARMS = 6.1
SEC_PER_JUDGE_CLUSTERING_B12 = SEC_PER_EVAL_WITH_JUDGE_B12 - SEC_PER_EVAL_CHEAP_ARMS
PROMPTS_PER_CLUSTERING = math.comb(N_SAMPLES, 2) * 2  # symmetric: both orderings


def judge_clustering_seconds(batch_size: int, *, regime: str = "central") -> float:
    """Seconds for ONE N=10 symmetric judge clustering at a given judge_batch_size.

    Halving the batch doubles the number of forward passes. The two ends of the bracket are
    the two things that can be true and neither is measured at batch 6:
      "compute"  -- time is dominated by tokens processed, so total time is unchanged.
      "overhead" -- time is dominated by per-call cost, so total time scales with the
                    number of chunks.
    "central" is their geometric mean. THIS BRACKET IS A MODEL, NOT A MEASUREMENT: replace
    it by timing 20 clusterings the first time the device is free (see the .md).
    """
    chunks_b12 = math.ceil(PROMPTS_PER_CLUSTERING / 12)
    chunks = math.ceil(PROMPTS_PER_CLUSTERING / batch_size)
    compute = SEC_PER_JUDGE_CLUSTERING_B12
    overhead = SEC_PER_JUDGE_CLUSTERING_B12 * chunks / chunks_b12
    if regime == "compute":
        return compute
    if regime == "overhead":
        return overhead
    return math.sqrt(compute * overhead)


def gpu_cost(n_targets: int, *, batch_size: int = 6, regenerate_attacked: bool = True) -> dict:
    """GPU-hours for the standalone (ii)+(iii) run.

    Benign arm: the samples are already on disk as TEXT, so it costs a judge clustering and
    nothing else -- no victim, no generation. Attacked arm: the campaign discarded the q'
    samples (harness.py keeps only the greedy answer), so they must be regenerated.
    """
    out = {}
    for regime in ("compute", "central", "overhead"):
        per = judge_clustering_seconds(batch_size, regime=regime)
        judge_s = 2 * n_targets * per
        gen_s = (n_targets * SEC_PER_EVAL_CHEAP_ARMS) if regenerate_attacked else 0.0
        out[regime] = (judge_s + gen_s) / 3600.0
    out["judge_clusterings"] = 2 * n_targets
    out["victim_sampling_passes"] = n_targets if regenerate_attacked else 0
    out["sec_per_clustering_central"] = judge_clustering_seconds(batch_size)
    return out


# ---------------------------------------------------------------------------
# cache readers
# ---------------------------------------------------------------------------
def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _index(records, key="question_id"):
    return {r[key]: r for r in records}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="~/.cache/se-research/samples",
                    help="sample cache root (inside WSL)")
    ap.add_argument("--pool", default="wk4_full_2000q", help="clean pool cell")
    ap.add_argument("--tags", default="wk9_def,wk9_defb", help="attack campaign tags")
    ap.add_argument("--effect_nats", type=float, default=None,
                    help="reference FA effect for the margin; default = the measured paired "
                         "mean delta of the LAST tag's FA cell")
    ap.add_argument("--margin_frac", type=float, default=0.20,
                    help="PRE-REGISTERED margin as a fraction of the reference effect")
    ap.add_argument("--n_boot", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="", help="also write the report to this path")
    args = ap.parse_args(argv)

    L = []

    def say(s=""):
        print(s, flush=True)
        L.append(s)

    root = Path(os.path.expanduser(args.cache))
    lattice = build_k_lattice(N_SAMPLES)

    # -- A ------------------------------------------------------------------
    say("== A. the N=10 entropy lattice ==")
    say(f"p({N_SAMPLES}) = {len(list(partitions_of(N_SAMPLES)))} partitions -> "
        f"{len(lattice)} distinct entropies")
    for h, parts, ks in lattice_collisions(lattice):
        say(f"   coincidence H={h:.9f}: {parts} -> K in {ks} "
            f"({'IDENTIFIED' if len(ks) == 1 else 'ambiguous by ' + str(max(ks) - min(ks))})")

    # -- B ------------------------------------------------------------------
    ent_path = root / args.pool / "entropy.jsonl"
    clean_ent = read_jsonl(ent_path) if ent_path.exists() else []
    if clean_ent:
        v = validate_inverter(clean_ent, lattice)
        say()
        say("== B. inverter validated against a cache that stores BOTH H and K ==")
        say(f"{ent_path}: n={v['n']}  K recovered exactly {v['exact']} "
            f"({v['exact']/v['n']:.1%})  ambiguous-but-containing-truth {v['ambiguous']} "
            f"({v['ambiguous']/v['n']:.1%})  MISMATCH {v['mismatch']}  off-lattice {v['off_lattice']}")
    clean_by_id = _index(clean_ent)

    # -- empirical nats-per-cluster, needed for the margin -------------------
    by_k = defaultdict(list)
    for r in clean_ent:
        by_k[r["n_clusters"]].append(r["entropy_nats"])
    slope = None
    if 5 in by_k and 10 in by_k:
        slope = (statistics.mean(by_k[10]) - statistics.mean(by_k[5])) / 5.0
        say()
        say("== nats per cluster, measured on the clean pool ==")
        say("   " + "  ".join(f"K={k}:{statistics.mean(by_k[k]):.3f}" for k in sorted(by_k)))
        say(f"   mean slope over K=5..10: {slope:.4f} nats/cluster")

    # -- C ------------------------------------------------------------------
    say()
    say("== C. (iii)-PRELIMINARY: paired attack-vs-benign cluster counts, NLI clusterer ==")
    say("   NOT the judge. The judge has never been run on the campaign. This measures the")
    say("   EXPOSURE -- how far the attack moves the clustering regime -- which is the thing")
    say("   a differentially-over-splitting judge would amplify.")
    ref_effect = args.effect_nats
    for tag in [t for t in args.tags.split(",") if t]:
        for cell in ("triviaqa_se_false_alarm", "triviaqa_se_hide"):
            p = root / "attacks" / tag / f"{cell}.jsonl"
            if not p.exists():
                continue
            rows = read_jsonl(p)
            kb, ka, amb, off, from_cache = [], [], 0, 0, 0
            for r in rows:
                cb = clean_by_id.get(r["question_id"])
                if cb is not None and abs(cb["entropy_nats"] - r["entropy_before"]) < 1e-12:
                    b = cb["n_clusters"]
                    from_cache += 1
                else:
                    cands = invert_cluster_count(r["entropy_before"], lattice)
                    b = cands[0] if cands else None
                cands = invert_cluster_count(r["entropy_after"], lattice)
                if cands is None or b is None:
                    off += 1
                    continue
                if len(cands) > 1:
                    amb += 1
                kb.append(b)
                ka.append(cands[0])
            if not kb:
                continue
            d = [a - b for a, b in zip(ka, kb)]
            m, lo, hi = paired_bootstrap_ci(d, seed=args.seed, n_boot=args.n_boot)
            npos = sum(1 for x in d if x > 0)
            nneg = sum(1 for x in d if x < 0)
            delta = statistics.mean(r["entropy_after"] - r["entropy_before"] for r in rows)
            say(f"   {tag}/{cell}: n={len(kb)}  benign K exact-from-cache {from_cache}/{len(rows)}  "
                f"attacked K ambiguous {amb}  off-lattice {off}")
            say(f"      K_benign {statistics.mean(kb):.2f} -> K_attack {statistics.mean(ka):.2f}   "
                f"paired dK {m:+.3f} [{lo:+.3f}, {hi:+.3f}]   "
                f"(+ {npos} / 0 {len(d)-npos-nneg} / - {nneg}, sign p={sign_test_p(npos, nneg):.2e})")
            say(f"      paired mean entropy move {delta:+.4f} nats")
            if cell.endswith("false_alarm"):
                ref_effect = args.effect_nats if args.effect_nats is not None else delta

    # -- D ------------------------------------------------------------------
    smp_path = root / args.pool / "samples.jsonl"
    fa_ids = []
    fa_p = root / "attacks" / args.tags.split(",")[-1] / "triviaqa_se_false_alarm.jsonl"
    if fa_p.exists():
        fa_ids = [r["question_id"] for r in read_jsonl(fa_p)]
    if smp_path.exists():
        smp = _index(read_jsonl(smp_path))
        say()
        say("== D. condition (ii): the messy real sampled pairs are ALREADY ON DISK ==")
        lens = [len(s.split()) for r in smp.values() for s in r["samples"]]
        say(f"   {smp_path}: {len(smp)} questions x C(10,2)={math.comb(10,2)} pairs "
            f"= {len(smp)*math.comb(10,2)} real sampled pairs")
        say(f"   sample length: mean {statistics.mean(lens):.1f} words, median "
            f"{statistics.median(lens):.0f}, max {max(lens)}; "
            f"{sum(1 for x in lens if x > 3)/len(lens):.1%} are longer than 3 words")
        for label, ids in (("whole pool", list(smp)), ("FA-80 targets", fa_ids)):
            ids = [q for q in ids if q in smp]
            if not ids:
                continue
            agg = Counter()
            for q in ids:
                for k, v in oracle_pair_strata(smp[q]["samples_correct"]).items():
                    agg[k] += v
            t = agg["total"]
            say(f"   {label} (n={len(ids)}): oracle-positive {agg['positive']} "
                f"({agg['positive']/t:.1%})  oracle-hard-negative {agg['hard_neg']} "
                f"({agg['hard_neg']/t:.1%})  unlabelled {agg['unlabelled']} ({agg['unlabelled']/t:.1%})")
            if clean_by_id:
                mg = sp = 0
                for q in ids:
                    if q not in clean_by_id:
                        continue
                    a, b = false_split_rate(clean_by_id[q]["assignments"], smp[q]["samples_correct"])
                    mg += a
                    sp += b
                if mg + sp:
                    lo, hi = wilson_ci(sp, mg + sp)
                    say(f"      the NLI clusterer SPLITS {sp}/{mg+sp} = {sp/(mg+sp):.3f} "
                        f"[{lo:.3f}, {hi:.3f}] of those oracle-positive pairs")
        if fa_ids and clean_by_id:
            ex = [within_cluster_pairs(clean_by_id[q]["assignments"]) for q in fa_ids
                  if q in clean_by_id]
            say(f"   FA-80 benign: the NLI clusterer merges {statistics.mean(ex):.1f}/45 pairs "
                f"per target on average -- the pairs on which a false split is possible at all")

    # -- E ------------------------------------------------------------------
    say()
    say("== E. GPU cost of the standalone run that closes (ii) and (iii) ==")
    n_t = len(fa_ids) or 80
    for bs in (6, 12):
        c = gpu_cost(n_t, batch_size=bs)
        say(f"   n={n_t} targets, judge_batch_size={bs}: "
            f"{c['judge_clusterings']} judge clusterings + {c['victim_sampling_passes']} "
            f"victim sampling passes")
        say(f"      {c['sec_per_clustering_central']:.0f} s/clustering (central) -> "
            f"{c['central']:.2f} GPU-h  [bracket {c['compute']:.2f}-{c['overhead']:.2f}]")

    if ref_effect and slope:
        margin_nats = args.margin_frac * ref_effect
        say()
        say("== pre-registered margins, derived not asserted ==")
        say(f"   reference FA effect  {ref_effect:+.4f} nats (paired mean move, NLI, n={n_t})")
        say(f"   margin  {args.margin_frac:.0%} of it = {margin_nats:.4f} nats")
        say(f"   at {slope:.4f} nats/cluster that is {margin_nats/slope:.2f} clusters")
        say("   ORIENTATION: positive = the judge splits relatively MORE on the attacked")
        say("   side = ANTI-conservative. FAIL if the 95% CI lies wholly above 0, or the")
        say("   point estimate reaches the margin. PASS only if the CI upper bound is below")
        say("   the margin. Anything else is INCONCLUSIVE, and inconclusive is not a pass.")

    if args.out:
        Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
