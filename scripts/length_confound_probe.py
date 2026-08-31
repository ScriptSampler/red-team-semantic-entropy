"""Is the NLI clustering length-driven, and if so does any live claim move?

Provenance: an out-of-scope measurement surfaced while costing the judge's owed
validation conditions (scripts/judge_owed_conditions.py section D) reported that the
NLI clusterer puts two samples that BOTH name the gold answer into DIFFERENT clusters
63.5% of the time pool-wide. The proposed explanation was a length artefact: generation
is pinned at max_new_tokens=48 and the cached samples are ~20 words, so two long
generations can both name the gold entity and still fail bidirectional entailment
because each carries content the other does not.

This script separates three things that the raw split rate runs together:

  (1) ORACLE COARSENESS. "Oracle-positive" means both samples CONTAIN a gold alias
      (span oracle, B3). That is not the same relation as "both give the same answer":
      for gold "Cancer", the samples "died of breast cancer" and "died of ovarian
      cancer" are both oracle-positive and are genuinely different answers. A split
      there is the clusterer being RIGHT. judge_owed_conditions.oracle_pair_strata
      already says this in its docstring; this script measures how big it is.

  (2) LENGTH / TRUNCATION. The hypothesised artefact. Measured as the split rate's
      dependence on pair length and on cap-truncation, holding the oracle fixed.

  (3) CLAIM IMPACT. The live claims (clean AUROC, ceiling saturation, the K bound)
      are all DIFFERENCES between the correct and hallucinating strata. A length
      effect common to both strata inflates K everywhere and cancels in the
      difference; only a length effect CORRELATED WITH THE LABEL can move them.
      So the load-bearing measurement is not the split rate at all -- it is
      length-vs-label, and AUROC recomputed within length bands.

CPU only. Reads the cached pool; no model, no GPU, no re-clustering.
Section F costs the GPU probe that WOULD be needed to re-cluster truncated text.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

N_SAMPLES = 10
PAIRS_PER_Q = math.comb(N_SAMPLES, 2)


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def read_jsonl(path: Path) -> list[dict]:
    out = []
    with open(path) as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def index_by(records: list[dict], key: str = "question_id") -> dict[str, dict]:
    return {r[key]: r for r in records}


def stratum_ids(want: str, seed: int, labels: dict[str, dict]) -> list[str]:
    """Byte-for-byte the rule in se.attacks.select._stratum_ids, inlined so this
    script needs no repo import inside WSL."""
    want_correct = (want == "right")
    ids = sorted(qid for qid, lab in labels.items()
                 if bool(lab["greedy_correct"]) == want_correct)
    rng = random.Random(f"{seed}:{want}")
    rng.shuffle(ids)
    return ids


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def wilson_ci(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUROC with midrank tie correction. labels: 1 = positive
    (hallucinating), 0 = negative. Ties matter here: discrete entropy at N=10 takes
    only 39 distinct values, so a naive implementation would be materially wrong."""
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    ranks = np.empty(len(order), dtype=float)
    srt = np.concatenate([pos, neg])[order]
    i = 0
    while i < len(srt):
        j = i
        while j + 1 < len(srt) and srt[j + 1] == srt[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    r_pos = ranks[:len(pos)].sum()
    return (r_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))


def concordance_counts(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """(concordant + 0.5*tied, total) pairs. Summing these across strata and dividing
    gives the LENGTH-STRATIFIED AUROC: only pairs inside the same length band are ever
    compared, so a length effect common to both strata cannot contribute."""
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return (0.0, 0.0)
    return (auroc(scores, labels) * len(pos) * len(neg), float(len(pos) * len(neg)))


def boot_auroc_ci(scores, labels, *, seed=0, n_boot=2000, alpha=0.05):
    """Question-level bootstrap. Resamples the pool, not the pairs."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        s, l = scores[idx], labels[idx]
        if l.sum() == 0 or l.sum() == len(l):
            continue
        vals.append(auroc(s, l))
    if not vals:
        return (float("nan"), float("nan"))
    v = np.sort(np.array(vals))
    return (float(np.quantile(v, alpha / 2)), float(np.quantile(v, 1 - alpha / 2)))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    def rank(a):
        order = np.argsort(a, kind="mergesort")
        r = np.empty(len(a), float)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    d = math.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d else float("nan")


# ---------------------------------------------------------------------------
# text properties
# ---------------------------------------------------------------------------
_TERMINAL = re.compile(r'[.!?]["\')\]]*\s*$')


def looks_truncated(s: str) -> bool:
    """Proxy for "this generation hit the 48-token cap": it does not end on terminal
    punctuation. Validated in section B against the word-count distribution -- if the
    proxy is tracking the cap, flagged samples must pile up at the long end."""
    return not bool(_TERMINAL.search(s.strip()))


def norm(s: str) -> str:
    """Cheap canonical normalisation for the duplicate-pair floor check. Deliberately
    NOT se.scoring.normalize_answer (no repo import inside WSL); only used to identify
    string-identical samples, where any reasonable normaliser agrees."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="~/.cache/se-research/samples")
    ap.add_argument("--pool", default="wk4_full_2000q")
    ap.add_argument("--fa_tag", default="wk9_defb")
    ap.add_argument("--n_boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    L: list[str] = []

    def say(s=""):
        print(s, flush=True)
        L.append(s)

    root = Path(os.path.expanduser(args.cache))
    smp = index_by(read_jsonl(root / args.pool / "samples.jsonl"))
    ent = index_by(read_jsonl(root / args.pool / "entropy.jsonl"))
    rel = index_by(read_jsonl(root / args.pool / "relabeled.jsonl"))

    fa_p = root / "attacks" / args.fa_tag / "triviaqa_se_false_alarm.jsonl"
    fa_ids = [r["question_id"] for r in read_jsonl(fa_p)] if fa_p.exists() else []

    qids = [q for q in smp if q in ent and q in rel]
    say(f"pool={args.pool}  questions with samples+entropy+labels: {len(qids)}")
    say(f"FA targets ({args.fa_tag}): {len(fa_ids)}")
    say()

    # -- per-question derived quantities ------------------------------------
    words = {q: [len(s.split()) for s in smp[q]["samples"]] for q in qids}
    trunc = {q: [looks_truncated(s) for s in smp[q]["samples"]] for q in qids}
    label = {q: (0 if bool(rel[q]["greedy_correct"]) else 1) for q in qids}   # 1 = hallucinating
    K = {q: ent[q]["n_clusters"] for q in qids}
    H = {q: ent[q]["entropy_nats"] for q in qids}
    meanlen = {q: statistics.mean(words[q]) for q in qids}

    # =======================================================================
    say("=" * 78)
    say("A. REPRODUCTION of the reported split rate")
    say("=" * 78)
    say("  oracle-positive = both samples contain a gold alias (span oracle).")
    say("  split           = the NLI clusterer put them in DIFFERENT clusters.")
    say()

    def split_stats(ids):
        mg = sp = 0
        for q in ids:
            a, sc = ent[q]["assignments"], smp[q]["samples_correct"]
            for i, j in combinations(range(len(sc)), 2):
                if sc[i] and sc[j]:
                    if a[i] == a[j]:
                        mg += 1
                    else:
                        sp += 1
        return mg, sp

    for lbl, ids in (("whole pool", qids),
                     ("FA-80 targets", [q for q in fa_ids if q in smp])):
        mg, sp = split_stats(ids)
        lo, hi = wilson_ci(sp, mg + sp)
        say(f"  {lbl:<16} n={len(ids):<5} oracle-positive pairs={mg+sp:<7} "
            f"SPLIT {sp}/{mg+sp} = {sp/(mg+sp):.3f} [{lo:.3f}, {hi:.3f}]")
    say()
    say("  -> reproduced independently of judge_owed_conditions.py.")
    say()

    # =======================================================================
    say("=" * 78)
    say("B. WHAT THE SAMPLES LOOK LIKE (is the 48-token cap biting?)")
    say("=" * 78)
    allw = [w for q in qids for w in words[q]]
    allt = [t for q in qids for t in trunc[q]]
    say(f"  words/sample: mean {statistics.mean(allw):.1f}  median {statistics.median(allw):.0f} "
        f"  p90 {np.percentile(allw, 90):.0f}  max {max(allw)}")
    say(f"  no terminal punctuation (cap-truncation proxy): "
        f"{sum(allt)}/{len(allt)} = {sum(allt)/len(allt):.1%}")
    say()
    say("  proxy validation -- truncated samples must pile up at the long end:")
    for lo_w, hi_w in ((0, 9), (10, 19), (20, 29), (30, 39), (40, 999)):
        sel = [t for q in qids for w, t in zip(words[q], trunc[q]) if lo_w <= w <= hi_w]
        if sel:
            say(f"    {lo_w:>2}-{hi_w if hi_w<999 else '+':<3} words: n={len(sel):<6} "
                f"truncated {sum(sel)/len(sel):>6.1%}")
    say()

    # =======================================================================
    say("=" * 78)
    say("C. IS THE SPLIT RATE LENGTH-DRIVEN? (the hypothesis, tested directly)")
    say("=" * 78)
    say("  Every row is oracle-positive pairs only. If length is the driver, the split")
    say("  rate must climb steeply with pair length and with truncation.")
    say()

    by_maxlen = defaultdict(lambda: [0, 0])     # bucket -> [merged, split]
    by_trunc = defaultdict(lambda: [0, 0])
    by_dup = defaultdict(lambda: [0, 0])
    for q in qids:
        a, sc, w, tr = ent[q]["assignments"], smp[q]["samples_correct"], words[q], trunc[q]
        ns = [norm(s) for s in smp[q]["samples"]]
        for i, j in combinations(range(len(sc)), 2):
            if not (sc[i] and sc[j]):
                continue
            slot = 1 if a[i] != a[j] else 0
            mx = max(w[i], w[j])
            bucket = min(mx // 10 * 10, 40)
            by_maxlen[bucket][slot] += 1
            key = ("both truncated" if tr[i] and tr[j]
                   else "one truncated" if tr[i] or tr[j] else "neither truncated")
            by_trunc[key][slot] += 1
            by_dup["identical text" if ns[i] == ns[j] else "different text"][slot] += 1

    say("  by max(words) of the pair:")
    for b in sorted(by_maxlen):
        mg, sp = by_maxlen[b]
        lo, hi = wilson_ci(sp, mg + sp)
        lbl = f"{b}-{b+9}" if b < 40 else "40+"
        say(f"    {lbl:>6} words: n={mg+sp:<7} split {sp/(mg+sp):.3f} [{lo:.3f}, {hi:.3f}]")
    say()
    say("  by cap-truncation:")
    for k in ("neither truncated", "one truncated", "both truncated"):
        if k in by_trunc:
            mg, sp = by_trunc[k]
            lo, hi = wilson_ci(sp, mg + sp)
            say(f"    {k:<20}: n={mg+sp:<7} split {sp/(mg+sp):.3f} [{lo:.3f}, {hi:.3f}]")
    say()
    say("  floor check -- pairs whose text is IDENTICAL after normalisation:")
    for k in ("identical text", "different text"):
        if k in by_dup:
            mg, sp = by_dup[k]
            lo, hi = wilson_ci(sp, mg + sp)
            say(f"    {k:<20}: n={mg+sp:<7} split {sp/(mg+sp):.3f} [{lo:.3f}, {hi:.3f}]")
    say("    (identical text splitting at ~0 shows the clusterer is not simply broken;")
    say("     the split rate on DIFFERENT text is the quantity in question.)")
    say()

    # =======================================================================
    say("=" * 78)
    say("D. THE LOAD-BEARING TEST: is length CORRELATED WITH THE LABEL?")
    say("=" * 78)
    say("  Every live claim is a DIFFERENCE between the correct and hallucinating")
    say("  strata. A length effect common to both cancels in that difference. It can")
    say("  only move a claim if length itself predicts the label.")
    say()

    ids = np.array(qids)
    y = np.array([label[q] for q in qids])
    ml = np.array([meanlen[q] for q in qids], dtype=float)
    hh = np.array([H[q] for q in qids], dtype=float)
    kk = np.array([K[q] for q in qids], dtype=float)

    say(f"  mean words/sample, correct stratum      (n={int((y==0).sum())}): "
        f"{ml[y==0].mean():.2f}")
    say(f"  mean words/sample, hallucinating stratum (n={int((y==1).sum())}): "
        f"{ml[y==1].mean():.2f}")
    say(f"  difference: {ml[y==1].mean()-ml[y==0].mean():+.2f} words")
    say()

    a_len = auroc(ml, y)
    lo, hi = boot_auroc_ci(ml, y, seed=args.seed, n_boot=args.n_boot)
    say(f"  AUROC of MEAN LENGTH ALONE as a hallucination detector: "
        f"{a_len:.4f} [{lo:.4f}, {hi:.4f}]")
    a_ent = auroc(hh, y)
    lo2, hi2 = boot_auroc_ci(hh, y, seed=args.seed, n_boot=args.n_boot)
    say(f"  AUROC of SEMANTIC ENTROPY (full labelled pool):          "
        f"{a_ent:.4f} [{lo2:.4f}, {hi2:.4f}]")
    say()
    say(f"  Spearman corr(mean length, K)                 : {spearman(ml, kk):+.4f}")
    say(f"  Spearman corr(mean length, K) | correct only  : "
        f"{spearman(ml[y==0], kk[y==0]):+.4f}")
    say(f"  Spearman corr(mean length, K) | hallucinating : "
        f"{spearman(ml[y==1], kk[y==1]):+.4f}")
    say()

    # -- length-stratified AUROC -------------------------------------------
    say("  LENGTH-STRATIFIED AUROC. Questions are binned by mean sample length; the")
    say("  AUROC is recomputed comparing correct vs hallucinating ONLY WITHIN a bin,")
    say("  then pooled over concordant-pair counts. If the separation were an artefact")
    say("  of length, controlling for length would collapse it toward 0.5.")
    say()
    for nbins in (5, 10, 20):
        edges = np.quantile(ml, np.linspace(0, 1, nbins + 1))
        edges[-1] += 1e-9
        num = den = 0.0
        for b in range(nbins):
            sel = (ml >= edges[b]) & (ml < edges[b + 1])
            if sel.sum() < 2:
                continue
            n_, d_ = concordance_counts(hh[sel], y[sel])
            num += n_
            den += d_
        say(f"    {nbins:>2} length bins: stratified AUROC = {num/den:.4f}  "
            f"(pairs compared: {int(den)})")
    say()
    say("  per-bin detail at 5 bins:")
    edges = np.quantile(ml, np.linspace(0, 1, 6))
    edges[-1] += 1e-9
    for b in range(5):
        sel = (ml >= edges[b]) & (ml < edges[b + 1])
        if sel.sum() < 2 or y[sel].sum() in (0, y[sel].size):
            continue
        say(f"    words [{edges[b]:5.1f}, {edges[b+1]:5.1f}): n={int(sel.sum()):<5} "
            f"halluc={int(y[sel].sum()):<4} AUROC={auroc(hh[sel], y[sel]):.4f}  "
            f"meanK correct={kk[sel & (y==0)].mean():.2f} halluc={kk[sel & (y==1)].mean():.2f}")
    say()

    # -- the K>=8 bound, within length bands --------------------------------
    say("  The cluster-count bound (results/cluster_count_bound.md) within length bands:")
    say("  K>=8 share, correct vs hallucinating, per band.")
    for b in range(5):
        sel = (ml >= edges[b]) & (ml < edges[b + 1])
        c = sel & (y == 0)
        h_ = sel & (y == 1)
        if c.sum() == 0 or h_.sum() == 0:
            continue
        pc = (kk[c] >= 8).sum() / c.sum()
        ph = (kk[h_] >= 8).sum() / h_.sum()
        say(f"    words [{edges[b]:5.1f}, {edges[b+1]:5.1f}): "
            f"correct {pc:.1%} (n={int(c.sum())})  halluc {ph:.1%} (n={int(h_.sum())})  "
            f"gap {ph-pc:+.1%}")
    say()

    # -- fair pool ----------------------------------------------------------
    right = stratum_ids("right", 0, rel)[:200]
    wrong = stratum_ids("wrong", 0, rel)[:200]
    fair = [q for q in right + wrong if q in ent]
    if fair:
        fy = np.array([label[q] for q in fair])
        fh = np.array([H[q] for q in fair], dtype=float)
        fl = np.array([meanlen[q] for q in fair], dtype=float)
        lo3, hi3 = boot_auroc_ci(fh, fy, seed=args.seed, n_boot=args.n_boot)
        say(f"  FAIR POOL (n={len(fair)}): SE AUROC {auroc(fh, fy):.4f} [{lo3:.4f}, {hi3:.4f}]"
            f"   length-alone AUROC {auroc(fl, fy):.4f}")
        edges_f = np.quantile(fl, np.linspace(0, 1, 6))
        edges_f[-1] += 1e-9
        num = den = 0.0
        for b in range(5):
            sel = (fl >= edges_f[b]) & (fl < edges_f[b + 1])
            if sel.sum() < 2:
                continue
            n_, d_ = concordance_counts(fh[sel], fy[sel])
            num += n_
            den += d_
        say(f"  FAIR POOL length-stratified (5 bins): {num/den:.4f}")
    say()

    # =======================================================================
    say("=" * 78)
    say("E. HOW MUCH OF THE SPLIT RATE IS ORACLE COARSENESS?")
    say("=" * 78)
    say("  'Oracle-positive' only means both samples CONTAIN a gold alias. When the gold")
    say("  is a short common word the containment test is weak: two samples can contain")
    say("  it and still assert different things. Split rate by gold-answer length:")
    say()
    by_gold = defaultdict(lambda: [0, 0])
    for q in qids:
        g = len(str(smp[q].get("canonical_answer", "")).split())
        bucket = "1 word" if g <= 1 else "2 words" if g == 2 else "3+ words"
        a, sc = ent[q]["assignments"], smp[q]["samples_correct"]
        for i, j in combinations(range(len(sc)), 2):
            if sc[i] and sc[j]:
                by_gold[bucket][1 if a[i] != a[j] else 0] += 1
    for k in ("1 word", "2 words", "3+ words"):
        if k in by_gold:
            mg, sp = by_gold[k]
            lo, hi = wilson_ci(sp, mg + sp)
            say(f"    gold {k:<8}: n={mg+sp:<7} split {sp/(mg+sp):.3f} [{lo:.3f}, {hi:.3f}]")
    say()

    # =======================================================================
    say("=" * 78)
    say("F. GPU COST of the re-clustering probe (NOT run here)")
    say("=" * 78)
    say("  To test the length hypothesis causally you must RE-CLUSTER truncated text,")
    say("  which needs DeBERTa-large-MNLI on GPU. Cost model, from the anchors in")
    say("  docs/critique_log.md entry 22 (~6.1 s per cheap-arm evaluation = 10 samples")
    say("  + NLI clustering + exact + embedding):")
    say()
    nli_pairs = PAIRS_PER_Q * 2
    say(f"    per question: C(10,2) x 2 directions = {nli_pairs} DeBERTa forward passes")
    for n_q, lbl in ((400, "fair pool"), (2000, "full pool")):
        total = n_q * nli_pairs
        # the cheap-arm anchor bundles generation; NLI clustering alone is the ~1.5 s of it
        sec = n_q * 1.5
        say(f"    {lbl:<12} n={n_q:<5}: {total:>7} forward passes  "
            f"~{sec/60:.0f} min ({sec/3600:.2f} GPU-h) at the measured ~1.5 s/question")
    say()
    say("    x2 for the sentence-truncated and N-token-truncated arms, x1 for the")
    say("    un-truncated control already on disk = ~2 GPU-h for the full pool, ~0.4 for")
    say("    the fair pool. That is cheap. Whether it is WORTH it depends on section D.")
    say()

    if args.out:
        Path(args.out).write_text("\n".join(L) + "\n")
        print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
