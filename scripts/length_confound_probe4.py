"""Probe 4: does the verbose generation setting COST detection power?

Probe 3 found that the exact-match clusterer on truncated text separates the strata
better than the NLI clusterer does on full text. That comparison needs a paired interval
before it is said out loud, because both detectors are scored on the same questions.

If it holds, the reading of the length finding inverts: the 48-token verbose generations
are not manufacturing the separation, they are DILUTING it.

CPU only.
"""
from __future__ import annotations

import os
import statistics
from pathlib import Path

import numpy as np

from length_confound_probe import auroc, index_by, read_jsonl, stratum_ids
from length_confound_probe3 import discrete_H, first_n_words, first_sentence


def paired(a, b, y, seed=0, nb=4000):
    """Bootstrap auroc(a) - auroc(b), resampling questions jointly."""
    rng = np.random.default_rng(seed)
    n = len(y)
    v = []
    for _ in range(nb):
        i = rng.integers(0, n, n)
        yy = y[i]
        if yy.sum() in (0, len(yy)):
            continue
        v.append(auroc(a[i], yy) - auroc(b[i], yy))
    v = np.sort(np.array(v))
    return float(v.mean()), float(np.quantile(v, .025)), float(np.quantile(v, .975))


def main() -> int:
    root = Path(os.path.expanduser("~/.cache/se-research/samples"))
    smp = index_by(read_jsonl(root / "wk4_full_2000q" / "samples.jsonl"))
    ent = index_by(read_jsonl(root / "wk4_full_2000q" / "entropy.jsonl"))
    rel = index_by(read_jsonl(root / "wk4_full_2000q" / "relabeled.jsonl"))
    q = [x for x in smp if x in ent and x in rel]
    y = np.array([0 if bool(rel[x]["greedy_correct"]) else 1 for x in q])

    nli = np.array([ent[x]["entropy_nats"] for x in q], float)
    arms = {
        "exact-match, full text":
            np.array([discrete_H(smp[x]["samples"]) for x in q], float),
        "exact-match, first sentence":
            np.array([discrete_H([first_sentence(s) for s in smp[x]["samples"]])
                      for x in q], float),
        "exact-match, first 10 words":
            np.array([discrete_H([first_n_words(s, 10) for s in smp[x]["samples"]])
                      for x in q], float),
        "mean generation length":
            np.array([statistics.mean(len(s.split()) for s in smp[x]["samples"])
                      for x in q], float),
    }

    print(f"FULL LABELLED POOL n={len(q)}   (delta > 0 = beats the NLI clusterer)")
    print(f"  {'NLI clusterer, full text (deployed)':<36} AUROC {auroc(nli, y):.4f}")
    for nm, arr in arms.items():
        d, lo, hi = paired(arr, nli, y)
        flag = "SIGNIFICANT" if lo > 0 else ("worse" if hi < 0 else "ns")
        print(f"  {nm:<36} AUROC {auroc(arr, y):.4f}   delta {d:+.4f} "
              f"[{lo:+.4f}, {hi:+.4f}]  {flag}")

    right = stratum_ids("right", 0, rel)[:200]
    wrong = stratum_ids("wrong", 0, rel)[:200]
    fair = [x for x in right + wrong if x in ent]
    fi = np.array([q.index(x) for x in fair])
    print()
    print(f"FAIR POOL n={len(fair)}   -- the pool the headline 0.704 is quoted on")
    print(f"  {'NLI clusterer, full text (deployed)':<36} AUROC {auroc(nli[fi], y[fi]):.4f}")
    for nm, arr in arms.items():
        d, lo, hi = paired(arr[fi], nli[fi], y[fi])
        flag = "SIGNIFICANT" if lo > 0 else ("worse" if hi < 0 else "ns")
        print(f"  {nm:<36} AUROC {auroc(arr[fi], y[fi]):.4f}   delta {d:+.4f} "
              f"[{lo:+.4f}, {hi:+.4f}]  {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
