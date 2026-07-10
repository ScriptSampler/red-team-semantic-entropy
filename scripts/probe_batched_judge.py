"""GPU gate for the batched judge: batched verdicts MUST equal unbatched verdicts.

cluster_samples_judge_batched is proven (CPU test) to give identical clusters to
cluster_samples_judge FOR THE SAME per-pair verdicts. The only thing that can differ is
whether batched left-padded greedy generation yields the same yes/no as single-prompt
generation. This probe checks exactly that on a boundary-spanning pair set (aliases,
near-miss negatives, and deliberately borderline pairs where numerics could flip a token).

PASS => the batched judge is trustworthy; run the scale null control with --judge_batched.
FAIL => do NOT trust batched results; fall back to the unbatched path.

Needs the GPU free (loads Qwen twice, ~10 GB at 4-bit). Run after freeing the attack/GPU:
  python scripts/probe_batched_judge.py --model Qwen/Qwen2.5-7B-Instruct
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Boundary-spanning pairs. Correctness is validate_judge.py's job; here we only need
# batched==unbatched, so we include hard/borderline pairs where a token could flip.
PAIRS = [
    ("Broncos", "Denver Broncos"),          # alias -> yes
    ("JFK", "John F. Kennedy"),             # alias -> yes
    ("the Nile", "Nile River"),             # alias -> yes
    ("NYC", "New York City"),               # alias -> yes
    ("United States", "USA"),               # alias -> yes
    ("Mark Twain", "Samuel Clemens"),       # pen name -> yes
    ("Denver Broncos", "Denver Nuggets"),   # same city, diff team -> no
    ("1912", "1921"),                       # transposed digits -> no
    ("Paris", "Paris, Texas"),              # diff place -> no
    ("Mercury", "Venus"),                   # diff planet -> no
    ("Ford", "Ferrari"),                    # diff make -> no
    ("Theodore Roosevelt", "Franklin Roosevelt"),  # diff person, shared surname -> no
    ("eight", "8"),                         # borderline surface variant -> likely yes
    ("Mumbai", "Bombay"),                   # renamed city -> yes
    ("carbon dioxide", "CO2"),              # formula alias -> yes
    ("Great Britain", "United Kingdom"),    # borderline near-synonym -> judge decides
    ("colour", "color"),                    # spelling variant -> yes
    ("St. Petersburg", "Leningrad"),        # historical rename -> borderline
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--asymmetric", action="store_true",
                    help="probe the asymmetric judge (default: symmetric, as the run uses)")
    args = ap.parse_args()
    symmetric = not args.asymmetric

    from se.judge import load_judge
    print(f"[probe] loading UNBATCHED judge {args.model} ...", flush=True)
    jf = load_judge(args.model, symmetric=symmetric, batched=False)
    print(f"[probe] loading BATCHED judge {args.model} ...", flush=True)
    jp = load_judge(args.model, symmetric=symmetric, batched=True)

    unb = [jf(a, b) for a, b in PAIRS]        # one pair at a time (production validated path)
    bat = jp(PAIRS)                            # all pairs in one GPU batch (scale path)

    print(f"\n{'a':<22} {'b':<22} unbatched batched  match")
    n_match = 0
    for (a, b), u, v in zip(PAIRS, unb, bat):
        ok = (u == v)
        n_match += ok
        print(f"{a:<22.22} {b:<22.22} {str(u):>9} {str(v):>7}  {'OK' if ok else 'MISMATCH <<<'}")

    agree = n_match / len(PAIRS)
    print(f"\nagreement: {n_match}/{len(PAIRS)} = {agree:.1%}  (symmetric={symmetric})")
    if n_match == len(PAIRS):
        print("PASS — batched judge is verdict-identical to unbatched. Safe to run "
              "null_control.py --judge_batched.")
        return 0
    print("FAIL — batched and unbatched disagree; do NOT use --judge_batched until fixed "
          "(check left-padding / attention_mask / chat-template handling).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
