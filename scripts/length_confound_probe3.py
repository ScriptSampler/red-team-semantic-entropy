"""Probe 3: would truncating the generations remove the length signal?

Probes 1-2 established that mean generation length carries most of semantic entropy's
label signal (length-alone AUROC 0.631 against SE's 0.694, and corr(length, K) = +0.67).
The obvious remedy is to truncate generations to the answer -- first sentence, or first
N tokens -- before clustering. Re-CLUSTERING truncated text needs the NLI model on GPU,
but two things can be measured on CPU from the cached text alone:

  J. Does the length GAP BETWEEN STRATA survive truncation? If hallucinating answers are
     longer only because they ramble AFTER stating the answer, first-sentence truncation
     should collapse the +2.87-word gap. If the gap survives, truncation will not remove
     the confound and the GPU re-clustering run would be answering a question whose
     answer is already visible.

  K. What happens to the repo's own CPU clusterer (exact-match, se.entropy.
     cluster_samples_exact) under truncation? It is not the NLI clusterer, but it is a
     real clusterer that consumes the same text, it is the repo's designated independent
     lower-bound arm, and it costs nothing. Its K-vs-label separation before and after
     truncation is a free preview of the direction the NLI arm would move.

CPU only.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

from length_confound_probe import (auroc, boot_auroc_ci, index_by, read_jsonl,
                                   spearman, stratum_ids)

# Sentence splitter: first terminal punctuation that is not an abbreviation dot.
# Deliberately simple -- the point is a cheap preview, not a parser.
_SENT = re.compile(r'(?<=[.!?])\s+')


def first_sentence(s: str) -> str:
    s = s.strip()
    parts = _SENT.split(s)
    return parts[0].strip() if parts else s


def first_n_words(s: str, n: int) -> str:
    return " ".join(s.split()[:n])


def norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def exact_K(samples) -> int:
    """se.entropy.cluster_samples_exact, inlined (no repo import inside WSL)."""
    return len({norm(s) for s in samples})


def discrete_H(samples) -> float:
    c = Counter(norm(s) for s in samples)
    tot = sum(c.values())
    return -sum((v / tot) * math.log(v / tot) for v in c.values())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="~/.cache/se-research/samples")
    ap.add_argument("--pool", default="wk4_full_2000q")
    ap.add_argument("--n_boot", type=int, default=2000)
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
    qids = [q for q in smp if q in ent and q in rel]
    y = np.array([0 if bool(rel[q]["greedy_correct"]) else 1 for q in qids])

    variants = {
        "full text (as clustered today)": lambda s: s,
        "first sentence": first_sentence,
        "first 10 words": lambda s: first_n_words(s, 10),
        "first 5 words": lambda s: first_n_words(s, 5),
    }

    say("=" * 78)
    say("J. DOES THE LENGTH GAP BETWEEN STRATA SURVIVE TRUNCATION?")
    say("=" * 78)
    say("  If hallucinating answers are longer only because they ramble after naming an")
    say("  answer, first-sentence truncation should collapse the gap.")
    say()
    say(f"  {'variant':<32} {'correct':>9} {'halluc':>9} {'gap':>8} {'len AUROC':>11}")
    for name, fn in variants.items():
        ml = np.array([statistics.mean(len(fn(s).split()) for s in smp[q]["samples"])
                       for q in qids], float)
        a = auroc(ml, y)
        say(f"  {name:<32} {ml[y==0].mean():>9.2f} {ml[y==1].mean():>9.2f} "
            f"{ml[y==1].mean()-ml[y==0].mean():>+8.2f} {a:>11.4f}")
    say()

    say("=" * 78)
    say("K. THE CPU (EXACT-MATCH) CLUSTERER UNDER TRUNCATION")
    say("=" * 78)
    say("  Not the NLI clusterer -- but a real clusterer on the same text, free to run,")
    say("  and the repo's designated independent lower-bound arm. Direction is the")
    say("  signal here, not the level (exact match always over-splits vs NLI).")
    say()
    say(f"  {'variant':<32} {'meanK':>7} {'K corr':>8} {'K halluc':>9} "
        f"{'H AUROC':>9} {'95% CI':>18}")
    for name, fn in variants.items():
        ks, hs = [], []
        for q in qids:
            t = [fn(s) for s in smp[q]["samples"]]
            ks.append(exact_K(t))
            hs.append(discrete_H(t))
        ks = np.array(ks, float)
        hs = np.array(hs, float)
        a = auroc(hs, y)
        lo, hi = boot_auroc_ci(hs, y, seed=0, n_boot=args.n_boot)
        say(f"  {name:<32} {ks.mean():>7.2f} {ks[y==0].mean():>8.2f} "
            f"{ks[y==1].mean():>9.2f} {a:>9.4f}   [{lo:.4f}, {hi:.4f}]")
    say()
    say("  For reference, the NLI clusterer on full text:")
    nk = np.array([ent[q]["n_clusters"] for q in qids], float)
    nh = np.array([ent[q]["entropy_nats"] for q in qids], float)
    lo, hi = boot_auroc_ci(nh, y, seed=0, n_boot=args.n_boot)
    say(f"  {'NLI, full text':<32} {nk.mean():>7.2f} {nk[y==0].mean():>8.2f} "
        f"{nk[y==1].mean():>9.2f} {auroc(nh, y):>9.4f}   [{lo:.4f}, {hi:.4f}]")
    say()

    # length-stratified AUROC for the truncated exact-match arms
    say("  Length-stratified (5 bins on that variant's own mean length):")
    for name, fn in variants.items():
        ml = np.array([statistics.mean(len(fn(s).split()) for s in smp[q]["samples"])
                       for q in qids], float)
        hs = np.array([discrete_H([fn(s) for s in smp[q]["samples"]]) for q in qids], float)
        edges = np.quantile(ml, np.linspace(0, 1, 6))
        edges[-1] += 1e-9
        num = den = 0.0
        for b in range(5):
            sel = (ml >= edges[b]) & (ml < edges[b + 1])
            if sel.sum() < 2 or y[sel].sum() in (0, y[sel].size):
                continue
            npos = int(y[sel].sum())
            nneg = int(sel.sum() - npos)
            num += auroc(hs[sel], y[sel]) * npos * nneg
            den += npos * nneg
        say(f"    {name:<32} stratified AUROC {num/den:.4f}")
    say()

    if args.out:
        Path(args.out).write_text("\n".join(L) + "\n")
        print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
