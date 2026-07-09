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
import itertools
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.embedding import load_embedder, E5_UNSUP
from se.scoring import normalize_answer
from se.stats import youden_j_threshold


def _content_tokens(s):
    return {t for t in normalize_answer(s).split() if len(t) > 2}


def _clean_positive(a, b):
    """A RELIABLE same-answer positive: TriviaQA alias lists are noisy (they group
    genuinely different entities, e.g. 'Orange (album)' / 'Orange (film)'), so we keep
    only surface variants we can trust as equivalent ground truth: token-set nesting
    ('Broncos' subset of 'Denver Broncos') or a near-identical string (typo/case/spacing,
    e.g. 'Ennio Morricone' / 'Ennio Moricone'). Conservative: drops hard-but-true aliases,
    which is correct for a validation set."""
    from difflib import SequenceMatcher
    na, nb = normalize_answer(a), normalize_answer(b)
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return False
    if ta <= tb or tb <= ta:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.85


def _alias_strata(n):
    """DOMAIN-MATCHED short-answer calibration with the critic's REQUIRED hard-negative
    stratum (entry 16). Ground-truth from TriviaQA gold aliases (not the NLI). Returns
    {pos, easy_neg, hard_neg}:
      pos       aliases of one answer ("Broncos" ~ "Denver Broncos") — same meaning
      easy_neg  answers of DIFFERENT questions, no shared token — distant, trivial
      hard_neg  different answers sharing a content token ("Denver Broncos"/"Denver
                Nuggets", "born 1912"/"born 1921") OR near-miss numbers ("1912"/"1921")
    The pos-vs-HARD_NEG AUROC — not the pooled one — is the rehabilitation criterion:
    hard negatives are the word-preserving/meaning-shifted case the attack produces."""
    from collections import defaultdict
    from se.data import load_triviaqa
    exs = load_triviaqa(split="validation")
    forms_by_ex = [[f for f in dict.fromkeys(ex.all_acceptable()) if f and len(f) < 60]
                   for ex in exs]
    forms_by_ex = [f for f in forms_by_ex if f]
    rng = random.Random(0)

    pos = [(a, b, 1) for forms in forms_by_ex
           for a, b in itertools.combinations(forms[:4], 2)
           if normalize_answer(a) != normalize_answer(b) and _clean_positive(a, b)]

    firsts = [f[0] for f in forms_by_ex]
    tok2ids = defaultdict(list)
    for i, f in enumerate(firsts):
        for t in _content_tokens(f):
            tok2ids[t].append(i)

    hard, seen = [], set()
    for t, ids in tok2ids.items():
        if len(ids) < 2:
            continue
        for a, b in itertools.combinations(ids[:6], 2):
            if normalize_answer(firsts[a]) != normalize_answer(firsts[b]) and (a, b) not in seen:
                seen.add((a, b)); hard.append((firsts[a], firsts[b], 0))
    nums = sorted((int(normalize_answer(f)), i) for i, f in enumerate(firsts)
                  if normalize_answer(f).isdigit())
    for (vi, i), (vj, j) in zip(nums, nums[1:]):
        if 0 < abs(vi - vj) <= 20:
            hard.append((firsts[i], firsts[j], 0))

    easy = []
    while len(easy) < len(pos):
        i, j = rng.randrange(len(firsts)), rng.randrange(len(firsts))
        if i != j and not (_content_tokens(firsts[i]) & _content_tokens(firsts[j])) \
                and normalize_answer(firsts[i]) != normalize_answer(firsts[j]):
            easy.append((firsts[i], firsts[j], 0))

    rng.shuffle(pos); rng.shuffle(easy); rng.shuffle(hard)
    return {"pos": pos[:n], "easy_neg": easy[:n], "hard_neg": hard[:n]}


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
    ap.add_argument("--source", default="all", choices=["all", "sentence", "aliases"],
                    help="aliases = domain-matched TriviaQA short-answer set (the real task)")
    args = ap.parse_args()

    prefix = "" if "gtr" in args.model else "query: "
    embed_fn = load_embedder(args.model, prefix=prefix)
    print(f"[embed] {args.model} loaded", flush=True)

    L = [f"# Embedding-threshold calibration ({args.model})", "",
         "Threshold to FREEZE before the definitive embedding arm (critic entry 15/16). AUROC = "
         "the encoder's paraphrase-discrimination power on disjoint labeled pairs. The "
         "TriviaQA-aliases set is DOMAIN-MATCHED (short factoid spans, the actual clustering "
         "task); the sentence sets (STS-B/PAWS) test general/adversarial sentence similarity.", ""]

    def _one(name, y, cos):
        thr, auroc, j = youden_j_threshold(y, cos)
        L.append(f"### {name}  (n={len(y)}, paraphrase={int(sum(y))})")
        L.append(f"- paraphrase-discrimination AUROC: {auroc:.3f}")
        L.append(f"- Youden-J cosine threshold: {thr:.3f}  (J={j:.3f}); "
                 f"band [{thr - 0.03:.3f}, {thr + 0.03:.3f}]")
        L.append("")

    if args.source in ("all", "aliases"):
        st = _alias_strata(args.n_per_source)
        pc = _cosines(st["pos"], embed_fn)
        ec = _cosines(st["easy_neg"], embed_fn)
        hc = _cosines(st["hard_neg"], embed_fn)
        L.append("## TriviaQA-aliases (SHORT ANSWER — the real clustering task)")
        L.append(f"positives={len(pc)}, easy_neg={len(ec)}, hard_neg={len(hc)}")
        L.append("")
        _one("pos vs EASY negatives (distant answers — trivial)",
             [1] * len(pc) + [0] * len(ec), np.concatenate([pc, ec]))
        _one("pos vs HARD negatives (REHABILITATION CRITERION — near-miss shared-token/numeric)",
             [1] * len(pc) + [0] * len(hc), np.concatenate([pc, hc]))
        L.append("> Rehabilitation (critic entry 16): e5 is a usable finding-14 adjudicator ONLY "
                 "IF the pos-vs-HARD AUROC is high. A high pos-vs-easy AUROC does NOT rehabilitate "
                 "it — that is the STS-B/easy regime; the attack produces the HARD (word-preserving, "
                 "meaning-shifted) case. If pos-vs-HARD is near-chance, the adjudicator must be a "
                 "victim- and NLI-independent, self-validated LLM-judge (definitive-run).")
        L.append("")

    if args.source in ("all", "sentence"):
        for name, loader in [("STS-B (sentence)", _pairs_stsb),
                             ("PAWS (sentence, hard negatives)", _pairs_paws)]:
            try:
                pairs = loader(args.n_per_source)
            except Exception as e:           # dataset unavailable offline -> skip loudly
                L.append(f"### {name}: unavailable ({type(e).__name__}: {e})"); L.append(""); continue
            _one(name, [p[2] for p in pairs], _cosines(pairs, embed_fn))

    out = RESULTS_DIR / "embed_calibration.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
