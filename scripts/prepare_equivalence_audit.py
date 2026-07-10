"""Prepare the human equivalence audit of successful attacks (owed item B5;
Limitations "Equivalence is certified automatically, not by humans").

The meaning-preserving guarantee rests on the NLI feasibility gate. This samples the
SUCCESSFUL attacks (the wins we would report) and lays out q vs q' for a human to rate
whether q' is truly bidirectionally equivalent to q — estimating the false-admit rate of
the gate ON THE REPORTED WINS, with the answer-flip subcategory flagged (it is a lower
bound on non-equivalence: q' can shift scope/presupposition while leaving the answer put).

STANDALONE by design: reads the attack-outcome JSONL with plain json (no se/torch import),
so it runs on any interpreter, including while the GPU is busy. Point it at the definitive
pool once n>=80 completes:
  python scripts/prepare_equivalence_audit.py <campaign_dir>/triviaqa_*.jsonl \
      --n_sample 40 --out results/equivalence_audit
Outputs <out>.csv (one row per sampled win, blank human columns) + <out>_instructions.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Deterministic sampler: no Math.random-style nondeterminism; seed fixes the draw.
import random

FIELDS_IN = ("question_id", "attack", "detector", "question", "best_query",
             "answer_under_q_prime", "correct_under_q_prime", "status_held", "delta")
HUMAN_COLS = ("equivalent_yes_no_unsure", "answer_meaning_changed_yes_no", "notes")


def load_success(paths: list[Path]) -> list[dict]:
    """All outcomes with success==True, as plain dicts, across the given JSONL files."""
    wins: list[dict] = []
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("success"):
                wins.append(r)
    return wins


def sample_audit(records: list[dict], n: int, seed: int = 0) -> list[dict]:
    """Deterministic random sample of up to n successful attacks, stratified by attack
    direction so hide and false-alarm are both represented when both exist."""
    by_attack: dict[str, list[dict]] = {}
    for r in records:
        by_attack.setdefault(r.get("attack", "?"), []).append(r)
    # stable order within each stratum before sampling, so the seed fully determines it
    for lst in by_attack.values():
        lst.sort(key=lambda r: r.get("question_id", ""))
    rng = random.Random(seed)
    strata = sorted(by_attack)
    # proportional allocation, at least 1 per non-empty stratum when n allows
    picked: list[dict] = []
    total = sum(len(by_attack[s]) for s in strata)
    for s in strata:
        share = max(1, round(n * len(by_attack[s]) / total)) if total else 0
        picked.extend(rng.sample(by_attack[s], min(share, len(by_attack[s]))))
    # trim/pad to exactly min(n, total) deterministically
    rng.shuffle(picked)
    return picked[: min(n, total)]


def write_csv(rows: list[dict], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([*FIELDS_IN, *HUMAN_COLS])
        for r in rows:
            w.writerow([*(r.get(k, "") for k in FIELDS_IN), *("" for _ in HUMAN_COLS)])


_INSTRUCTIONS = """# Equivalence audit — annotator instructions

You are auditing the **meaning-preserving** claim of an attack on a hallucination
detector. Each row is a *successful* attack: an optimiser found a paraphrase `best_query`
(**q'**) of the original `question` (**q**) that moved the detector's score, and an NLI
model certified q' as bidirectionally equivalent to q. Your job is to check that NLI
judgement by hand.

For each row fill three columns:

1. **equivalent_yes_no_unsure** — Is q' asking the *same question* as q, such that any
   correct answer to one is a correct answer to the other (bidirectional entailment)?
   `yes` / `no` / `unsure`. Judge the QUESTIONS, not the answers.
2. **answer_meaning_changed_yes_no** — Independently: could q' legitimately have a
   *different* correct answer than q (a shift in scope, entity, time, or presupposition)?
   `yes` even if the model's greedy answer happened not to change.
3. **notes** — one phrase on any scope/presupposition shift you see.

`answer_under_q_prime`, `correct_under_q_prime`, and `status_held` are shown as context
(what the model actually answered under q'); `delta` is the entropy move. The headline
number this audit produces is the **false-admit rate**: fraction of reported wins you mark
`equivalent = no`. Report it with an inter-annotator agreement estimate if more than one
person rates the sheet.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+", help="attack-outcome JSONL file(s) or globs")
    ap.add_argument("--n_sample", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/equivalence_audit",
                    help="output stem; writes <out>.csv and <out>_instructions.md")
    args = ap.parse_args()

    paths: list[Path] = []
    for pat in args.jsonl:
        p = Path(pat)
        paths.extend([p] if p.exists() else sorted(Path().glob(pat)))
    paths = [p for p in paths if p.exists()]
    if not paths:
        print(f"no JSONL files matched {args.jsonl}", file=sys.stderr)
        return 2

    wins = load_success(paths)
    if not wins:
        print("no successful attacks found in the given files", file=sys.stderr)
        return 1
    rows = sample_audit(wins, args.n_sample, args.seed)

    out_csv = Path(args.out + ".csv")
    out_md = Path(args.out + "_instructions.md")
    write_csv(rows, out_csv)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(_INSTRUCTIONS, encoding="utf-8")

    by_attack: dict[str, int] = {}
    for r in rows:
        by_attack[r.get("attack", "?")] = by_attack.get(r.get("attack", "?"), 0) + 1
    print(f"{len(wins)} successful attacks across {len(paths)} file(s); "
          f"sampled {len(rows)} for audit ({by_attack}).")
    print(f"wrote {out_csv}  and  {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
