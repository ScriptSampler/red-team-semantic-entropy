"""Calibrate the embedding-clusterer cosine threshold (critic entry 15).

Runs the chosen encoder (default e5-base-unsupervised) on labeled paraphrase /
non-paraphrase pairs DISJOINT from the SE eval (STS-B, PAWS), and reports:
  - the encoder's paraphrase-discrimination AUROC (is it a trustworthy equivalence
    oracle at all? — a mediocre AUROC means its clustering can't adjudicate anything);
  - the Youden-J / equal-error cosine threshold to FREEZE before the definitive
    embedding arm (the threshold must NOT be chosen after seeing which value gives the
    more interesting SE result);
  - a band around it — the definitive null-control conclusion must be shown stable
    across the band, or it is a threshold artifact.

PAWS is included on purpose: its high-lexical-overlap non-paraphrases are the hard
case that separates a real semantic encoder from a bag-of-words matcher.

    # in Ubuntu-24.04, GPU free:
    ./.venv-wsl/bin/python scripts/calibrate_embed_threshold.py --model intfloat/e5-base-unsupervised
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.embedding import load_embedder, E5_UNSUP
from se.stats import youden_j_threshold


def _pairs_stsb(n):
    from datasets import load_dataset
    ds = load_dataset("glue", "stsb", split="validation")
    out = []
    for r in ds:                       # score in [0,5]; >=4 paraphrase, <=1 non
        if r["label"] >= 4.0:
            out.append((r["sentence1"], r["sentence2"], 1))
        elif r["label"] <= 1.0:
            out.append((r["sentence1"], r["sentence2"], 0))
    return out[:n]


def _pairs_paws(n):
    from datasets import load_dataset
    ds = load_dataset("paws", "labeled_final", split="validation")
    return [(r["sentence1"], r["sentence2"], int(r["label"])) for r in ds][:n]


def _cosines(pairs, embed_fn, batch=64):
    s1 = [p[0] for p in pairs]
    s2 = [p[1] for p in pairs]
    e1 = np.concatenate([embed_fn(s1[i:i + batch]) for i in range(0, len(s1), batch)])
    e2 = np.concatenate([embed_fn(s2[i:i + batch]) for i in range(0, len(s2), batch)])
    return (e1 * e2).sum(1)            # rows are L2-normalized -> dot == cosine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=E5_UNSUP)
    ap.add_argument("--n_per_source", type=int, default=1000)
    args = ap.parse_args()

    prefix = "" if "gtr" in args.model else "query: "
    embed_fn = load_embedder(args.model, prefix=prefix)
    print(f"[embed] {args.model} loaded", flush=True)

    L = [f"# Embedding-threshold calibration ({args.model})", "",
         "Threshold to FREEZE before the definitive embedding arm (critic entry 15). "
         "AUROC = the encoder's paraphrase-discrimination power on disjoint labeled pairs.", ""]
    for name, loader in [("STS-B", _pairs_stsb), ("PAWS", _pairs_paws)]:
        try:
            pairs = loader(args.n_per_source)
        except Exception as e:               # dataset unavailable offline -> skip loudly
            L.append(f"## {name}: unavailable ({type(e).__name__}: {e})"); L.append(""); continue
        y = [p[2] for p in pairs]
        cos = _cosines(pairs, embed_fn)
        thr, auroc, j = youden_j_threshold(y, cos)
        L.append(f"## {name}  (n={len(pairs)}, paraphrase={sum(y)})")
        L.append(f"- paraphrase-discrimination AUROC: {auroc:.3f}")
        L.append(f"- Youden-J cosine threshold: {thr:.3f}  (J={j:.3f})")
        L.append(f"- suggested band: [{thr - 0.03:.3f}, {thr + 0.03:.3f}] "
                 f"— run the null-control conclusion across it and show it does not swing.")
        L.append("")

    out = RESULTS_DIR / "embed_calibration.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
