"""Week 9: scale-up attack campaign. Parameterised, resumable, checkpointed.

One invocation runs one campaign: an (attack, detector, dataset) triple over
a pool of questions, writing per-question outcomes to a campaign JSONL. The
plan warns these are multi-day runs on a single GPU, so each campaign is
resumable (re-invoke to continue) and you run them one at a time.

Usage:
    python scripts/wk9_scaleup.py --attack hide        --detector se  --dataset triviaqa --n 200
    python scripts/wk9_scaleup.py --attack false_alarm --detector se  --dataset triviaqa --n 200
    python scripts/wk9_scaleup.py --attack hide        --detector sre --dataset triviaqa --n 200
    ... and the SQuAD equivalents for the full Week 10 matrix.

For SQuAD and for SRE, targets are labelled fresh (no Week 4 cache), which
adds a labelling pass before the attack loop.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig
from se.data import load_triviaqa, load_squad, TriviaQAExample
from se.sampling import DEFAULT_SAMPLES_DIR
from se.se_pipeline import semantic_entropy
from se.attacks.harness import load_pair, run_attack_batch, LoadedPair
from se.attacks.select import select_examples


CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"


def _label_fresh(examples: list[TriviaQAExample], pair: LoadedPair,
                 gen: GenConfig, want: str, n: int) -> list[TriviaQAExample]:
    """Greedy-label examples and keep n with the desired correctness.

    Used for SQuAD (no Week 4 cache) and SRE campaigns. Stops once n found.
    """
    want_correct = (want == "right")
    kept: list[TriviaQAExample] = []
    for ex in examples:
        se = semantic_entropy(ex.question, pair.lm, pair.nli, gen,
                              example=ex, compute_greedy=True)
        if bool(se.greedy_correct) == want_correct:
            kept.append(ex)
            if len(kept) >= n:
                break
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack", choices=["hide", "false_alarm"], required=True)
    ap.add_argument("--detector", choices=["se", "sre"], default="se")
    ap.add_argument("--dataset", choices=["triviaqa", "squad"], default="triviaqa")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--max_iteration", type=int, default=20)
    args = ap.parse_args()

    want = "wrong" if args.attack == "hide" else "right"
    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    sre_kwargs = dict(n_reform=3, k_samples=8, temperature=0.8) if args.detector == "sre" else None

    # Target selection.
    if args.dataset == "triviaqa" and args.detector == "se":
        # Use the Week 4 cache for fast label-free selection.
        try:
            examples = select_examples(want, args.n)
        except FileNotFoundError:
            examples = _label_fresh(load_triviaqa("validation"), pair, gen, want, args.n)
    else:
        loader = load_triviaqa if args.dataset == "triviaqa" else load_squad
        pool = loader("validation")[: max(args.n * 4, 800)]  # oversample, label, filter
        examples = _label_fresh(pool, pair, gen, want, args.n)

    print(f"campaign: attack={args.attack} detector={args.detector} "
          f"dataset={args.dataset} n={len(examples)}", flush=True)

    out = CAMPAIGN_DIR / f"{args.dataset}_{args.detector}_{args.attack}.jsonl"
    run_attack_batch(
        examples, args.attack, pair, out,
        detector=args.detector, gen_cfg=gen, sre_kwargs=sre_kwargs,
        max_iteration=args.max_iteration, candidate_size_M=3, top_N=3,
        min_delta_nats=0.25, progress_every=5,
    )
    print(f"campaign written to {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
