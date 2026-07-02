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
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig
from se.data import load_triviaqa, load_squad, TriviaQAExample
from se.sampling import DEFAULT_SAMPLES_DIR
from se.se_pipeline import semantic_entropy
from se.attacks.harness import load_pair, run_attack_batch, LoadedPair
from se.attacks.select import campaign_pool

SEED = 0   # fixed across ALL cells so SE and SRE draw the identical pool.


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
    ap.add_argument("--candidate_size_M", type=int, default=3)
    ap.add_argument("--top_N", type=int, default=3)
    ap.add_argument("--tag", default="",
                    help="suffix for the campaign dir, e.g. '_fair' -> attacks/wk9_fair. "
                         "Keeps a corrected (B1/B2) recompute separate from old runs.")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="shared-pool seed (identical across SE/SRE cells).")
    args = ap.parse_args()
    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"

    want = "wrong" if args.attack == "hide" else "right"
    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    # sre_kwargs configures the DETECTOR, not selection — SE and SRE still share
    # the same pool below; only how each cell scores that pool differs.
    sre_kwargs = dict(n_reform=3, k_samples=8, temperature=0.8, seed=0) if args.detector == "sre" else None

    # Detector-INDEPENDENT target selection (external review B1). Both the SE and
    # SRE cells route through campaign_pool, which has no detector parameter, so
    # they draw the identical pool by construction. triviaqa uses the Week-4 span-
    # oracle cache; squad has no cache and is labelled fresh via this callback —
    # which is itself detector-blind (it never reads args.detector) and seeded so
    # the SQuAD SE and SRE cells select the same questions.
    def label_fresh(want: str, n: int, seed: int) -> list[TriviaQAExample]:
        loader = load_triviaqa if args.dataset == "triviaqa" else load_squad
        pool = list(loader("validation"))
        random.Random(f"labelpool:{args.dataset}:{seed}:{want}").shuffle(pool)
        return _label_fresh(pool[: max(n * 6, 1000)], pair, gen, want, n)

    examples = campaign_pool(args.dataset, want, args.n, seed=args.seed, label_fresh=label_fresh)
    if len(examples) < args.n:   # finding 12: fail loud on a silently undersized pool
        print(f"WARNING: pool undersized: {len(examples)} < requested {args.n} for "
              f"stratum '{want}' on {args.dataset} (rare in the scanned window). CIs will "
              f"be wider and cross-cell n unequal — widen the scan or lower --n.", flush=True)

    print(f"campaign: attack={args.attack} detector={args.detector} "
          f"dataset={args.dataset} n={len(examples)} (pool seed={args.seed}, detector-blind) "
          f"-> {campaign_dir.name}",
          flush=True)

    out = campaign_dir / f"{args.dataset}_{args.detector}_{args.attack}.jsonl"
    run_attack_batch(
        examples, args.attack, pair, out,
        detector=args.detector, gen_cfg=gen, sre_kwargs=sre_kwargs,
        max_iteration=args.max_iteration, candidate_size_M=args.candidate_size_M,
        top_N=args.top_N, min_delta_nats=0.25, progress_every=5,
    )
    print(f"campaign written to {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
