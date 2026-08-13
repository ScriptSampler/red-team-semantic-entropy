"""Build the blinded human equivalence audit of the attack's paraphrases (owed item B5;
Limitations, "Equivalence is certified automatically, not by humans").

WHAT THIS IS FOR
----------------
The paper's title says *meaning-preserving*. The only thing currently certifying that a
paraphrase q' preserves the meaning of q is an automatic bidirectional-NLI feasibility
gate. This script lays out q/q' pairs for a human to re-judge by hand, so the gate's
FALSE-PASS RATE can be estimated instead of assumed.

WHAT CHANGED (2026-08-13) AND WHY
---------------------------------
The previous version sampled `success == True` only, and wrote every outcome field --
attack direction, status_held, the model's answer under q', the entropy delta -- into the
sheet the annotator reads. That design cannot measure equivalence:

  * It measures EXPECTATION. An annotator who can see `attack=hide` and
    `answer_under_q_prime` knows what the pair is supposed to show before judging it.
  * It cannot see the interesting stratum at all. In this codebase
    `success == entropy_and_feasible and status_held` (se/attacks/harness.py), so
    "a successful attack whose answer flipped" is EMPTY BY CONSTRUCTION. The paper's
    disclosed lower bound on gate leakage is the answer-FLIP subcategory -- outcomes that
    would have been wins but were voided because the model's correctness status changed
    under q'. Those are `success == False`, so the old sampler discarded exactly the
    pairs most likely to be non-equivalent.

This version partitions the whole gate-passed pool into strata, censuses or samples them
under a seed, strips every provenance cue out of the annotator's view, randomises which
side of the pair is the original, shuffles, and writes the key to a SEPARATE file.

STRATA (a partition of the gate-passed pool; see `classify`)
------------------------------------------------------------
  win           entropy_and_feasible and status_held      -- the wins the paper reports.
                Licenses: the headline false-pass rate ON THE REPORTED WINS. A win the
                annotator marks non-equivalent is a claim the paper should not be making.
  flip          entropy_and_feasible and not status_held  -- would-be wins voided by a
                correctness flip under q'. Licenses: a test of the paper's own claim that
                the flip subcategory is a LOWER BOUND on non-equivalence. If the hand
                non-equivalence rate here is no higher than in `win`, the flip statistic
                is not the canary the paper treats it as.
  subthreshold  not entropy_and_feasible                  -- gate passed, but the entropy
                move never cleared the claim threshold, i.e. the optimiser did NOT get a
                win out of this paraphrase. Licenses: the selection-pressure contrast --
                is the gate leakier on the pairs the optimiser won on than on the pairs it
                did not? Same gate, no successful adversarial selection.
  catch         a synthetic, unambiguously NON-equivalent pair (two unrelated questions).
                Licenses: nothing about the gate. It validates the ANNOTATOR. With a
                single annotator there is no second human to catch a rubber-stamped
                "yes"; catch trials are the substitute. Built from records excluded from
                the real strata (no-op paraphrases), so no question text appears twice in
                the sheet -- a repeated question would itself be a tell.

NOT A STRATUM, AND HONESTLY SO: a benign-paraphrase arm. The right control for "what does
this annotator call non-equivalent when nothing adversarial happened?" is paraphrases from
the SAME proposer and the SAME gate with the entropy objective switched off. Those do not
exist in text form anywhere in the cache -- the null-control and ablation checkpoints store
MOVES, not paraphrase strings -- and generating them needs the proposer LLM (GPU).
`subthreshold` is the closest available stand-in and is weaker: those paraphrases were
still produced by an optimiser trying to move entropy, it just failed. `--benign_jsonl`
accepts such a file the day one exists; see results/equivalence_audit_protocol.md.

BLINDING
--------
The annotator CSV carries exactly: pair_id, question_A, question_B, and blank response
columns. No stratum, no attack direction, no detector, no entropy delta, no model answer,
no question_id. pair_ids are assigned AFTER the shuffle so their order carries nothing.
Which of q/q' lands in column A is randomised per pair, so "A is always the original" is
not a usable cue. Everything needed to un-blind is in <stem>_key.csv, which the annotator
must move out of the working directory before starting. With one person who owns the repo,
blinding is self-imposed discipline; the script's job is to make the honest path the easy
one, not to pretend it can enforce it.

STANDALONE by design: stdlib only (no se/torch/numpy import), so it runs on any
interpreter, including while the GPU is busy.

USAGE
-----
  python scripts/prepare_equivalence_audit.py \
      data/cache/attacks/wk9_defb_snap/triviaqa_se_*.jsonl \
      --out results/equivalence_audit

Writes <out>.csv (round 1, annotator), <out>_round2.csv (re-annotation sheet, held back
until after the washout), <out>_key.csv (both rounds, un-blinding), and <out>_design.md
(provenance hashes, realised strata, the n-vs-interval-width table).

The annotator PROTOCOL -- the exact question, the worked hard cases, the agreement plan --
is a hand-authored research document at results/equivalence_audit_protocol.md. This script
deliberately does not generate or overwrite it.

PIN YOUR INPUT. The sampler is only reproducible if the pool is. Point it at a frozen
snapshot, not at a campaign directory a run is still appending to; <out>_design.md records
a sha256 per input file so a moved pool is detectable after the fact.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Columns. ANNOTATOR_COLS is the blinding contract: anything not in this tuple
# must not reach the annotator's sheet. Tests enforce it.
# ---------------------------------------------------------------------------
PAIR_COLS = ("pair_id", "question_A", "question_B")
RESPONSE_COLS = ("equivalent_yes_no_unsure", "answer_could_differ_yes_no",
                 "confidence_1_to_3", "notes")
ANNOTATOR_COLS = (*PAIR_COLS, *RESPONSE_COLS)

KEY_COLS = ("pair_id", "round", "stratum", "orientation", "round1_pair_id",
            "question_id", "source_file", "attack", "detector",
            "question", "best_query",
            "success", "entropy_and_feasible", "status_held",
            "correct_under_q_prime", "frac_correct_under_q_prime",
            "answer_under_q_prime", "entropy_before", "entropy_after", "delta")

REAL_STRATA = ("win", "flip", "subthreshold")
ALL_STRATA = (*REAL_STRATA, "catch")

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an the of in on at to for from by with and or is was were are be been being "
    "which what who whom whose when where why how did does do had has have that this "
    "these those it its as into during about".split())


# ---------------------------------------------------------------------------
# Loading and classification
# ---------------------------------------------------------------------------
def load_outcomes(paths: list[Path]) -> list[dict]:
    """Every outcome record across the given JSONL files, tagged with source_file.

    Unlike the previous version this does NOT filter on success: the flip and
    subthreshold strata are success==False by construction and are the point.
    """
    out: list[dict] = []
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            r["source_file"] = p.name
            out.append(r)
    return out


def is_auditable(rec: dict) -> bool:
    """A record yields a judgeable pair only if the gate actually passed a paraphrase
    that differs from the original. `feasible` false means the gate never admitted
    anything; best_query == question means the optimiser returned a no-op, which is
    trivially equivalent and would be a giveaway in a blinded sheet."""
    if not rec.get("feasible"):
        return False
    q, qp = (rec.get("question") or "").strip(), (rec.get("best_query") or "").strip()
    return bool(q) and bool(qp) and q != qp


def classify(rec: dict) -> str | None:
    """Stratum for an auditable record, else None.

    Mirrors se/attacks/harness.py: success == entropy_and_feasible and status_held, and
    status_held/correct_under_q_prime are only MEASURED when entropy_and_feasible (the
    harness leaves them at their defaults otherwise -- "B2 nit 2"). So status_held is
    read only inside the entropy_and_feasible branch.
    """
    if not is_auditable(rec):
        return None
    if not rec.get("entropy_and_feasible"):
        return "subthreshold"
    return "win" if rec.get("status_held") else "flip"


def partition(records: list[dict]) -> dict[str, list[dict]]:
    """Records grouped by stratum, each group in a stable question_id order so the
    seed alone determines the draw."""
    groups: dict[str, list[dict]] = {s: [] for s in REAL_STRATA}
    for r in records:
        s = classify(r)
        if s is not None:
            groups[s].append(r)
    for lst in groups.values():
        lst.sort(key=lambda r: (r.get("source_file", ""), r.get("question_id", "")))
    return groups


def excluded_records(records: list[dict]) -> list[dict]:
    """Records that yield no real pair (no-op paraphrase or gate never passed). Their
    `question` text is unused elsewhere, which makes them the right raw material for
    catch trials: no question appears twice across the finished sheet."""
    out = [r for r in records if classify(r) is None]
    out.sort(key=lambda r: (r.get("source_file", ""), r.get("question_id", "")))
    return out


# ---------------------------------------------------------------------------
# Catch trials
# ---------------------------------------------------------------------------
def _content(s: str) -> set[str]:
    return {w for w in _WORD.findall(s.lower()) if w not in _STOP}


def overlap(a: str, b: str) -> float:
    """Content-word Jaccard. Used only to keep catch trials unambiguous."""
    ca, cb = _content(a), _content(b)
    if not ca or not cb:
        return 0.0
    return len(ca & cb) / len(ca | cb)


def make_catch_pairs(pool: list[dict], n: int, rng: random.Random,
                     max_overlap: float = 0.25) -> list[dict]:
    """`n` synthetic non-equivalent pairs, each from two DISTINCT unused records.

    Each record is consumed at most once, so no question text repeats. Pairs are
    rejected if the two questions share too much content, so that "no" is the only
    defensible answer -- a catch trial that is genuinely arguable measures nothing.
    """
    if n <= 0:
        return []
    avail = list(pool)
    rng.shuffle(avail)
    pairs: list[dict] = []
    while len(pairs) < n and len(avail) >= 2:
        left = avail.pop()
        mate_i = next((i for i, cand in enumerate(avail)
                       if overlap(left["question"], cand["question"]) <= max_overlap),
                      None)
        if mate_i is None:
            continue
        right = avail.pop(mate_i)
        pairs.append({
            "question": left["question"],
            "best_query": right["question"],
            "question_id": f"catch:{left.get('question_id')}|{right.get('question_id')}",
            "source_file": "synthetic",
            "attack": "", "detector": "",
            "success": "", "entropy_and_feasible": "", "status_held": "",
            "correct_under_q_prime": "", "frac_correct_under_q_prime": "",
            "answer_under_q_prime": "", "entropy_before": "", "entropy_after": "",
            "delta": "",
        })
    return pairs


# ---------------------------------------------------------------------------
# Sheet assembly
# ---------------------------------------------------------------------------
def _take(items: list[dict], n: int, rng: random.Random) -> list[dict]:
    """n items without replacement; n < 0 or n >= len means take all (a census)."""
    if n < 0 or n >= len(items):
        return list(items)
    return rng.sample(items, n)


def build_round1(groups: dict[str, list[dict]], catch: list[dict],
                 alloc: dict[str, int], seed: int) -> tuple[list[dict], list[dict]]:
    """(annotator_rows, key_rows) for round 1.

    Order of operations matters and is fixed: draw per stratum -> orient -> shuffle the
    combined list -> only then assign pair_ids. Assigning ids before the shuffle would
    make the id an index into the stratum blocks.
    """
    rng = random.Random(seed)
    drawn: list[tuple[str, dict]] = []
    for s in REAL_STRATA:
        drawn.extend((s, r) for r in _take(groups.get(s, []), alloc.get(s, -1), rng))
    drawn.extend(("catch", r) for r in _take(catch, alloc.get("catch", len(catch)), rng))

    # Balanced by construction rather than by coin flip: a fair coin over ~120 pairs
    # can land 62/38, which reintroduces the positional cue the randomisation exists to
    # remove. Half the sheet shows the original first, half shows the paraphrase first.
    orients = ["q_first"] * (len(drawn) // 2)
    orients += ["qprime_first"] * (len(drawn) - len(orients))
    rng.shuffle(orients)
    oriented = [(s, r, o) for (s, r), o in zip(drawn, orients)]
    rng.shuffle(oriented)

    ann, key = [], []
    for i, (stratum, rec, orient) in enumerate(oriented, start=1):
        pid = f"P{i:03d}"
        ann.append(_annotator_row(pid, rec, orient))
        key.append(_key_row(pid, 1, stratum, orient, "", rec))
    return ann, key


def build_round2(round1_key: list[dict], frac: float, seed: int
                 ) -> tuple[list[dict], list[dict]]:
    """Re-annotation sheet for the intra-annotator (test-retest) agreement estimate.

    A sampled fraction of round 1, with the orientation FLIPPED, fresh R-prefixed ids and
    an independent shuffle, so a pair cannot be recognised by its position, its id, or
    which column the original sat in. Recall is suppressed by time (the washout in the
    protocol), not by this file.
    """
    rng = random.Random(seed + 1)
    k = max(0, min(len(round1_key), round(frac * len(round1_key))))
    picked = rng.sample(round1_key, k) if k else []
    picked.sort(key=lambda kr: kr["pair_id"])          # stable before the reshuffle
    rng.shuffle(picked)

    ann, key = [], []
    for i, kr in enumerate(picked, start=1):
        pid = f"R{i:03d}"
        flipped = "qprime_first" if kr["orientation"] == "q_first" else "q_first"
        rec = {c: kr.get(c, "") for c in KEY_COLS}
        rec["question"], rec["best_query"] = kr["question"], kr["best_query"]
        ann.append(_annotator_row(pid, rec, flipped))
        key.append(_key_row(pid, 2, kr["stratum"], flipped, kr["pair_id"], rec))
    return ann, key


def _annotator_row(pair_id: str, rec: dict, orientation: str) -> dict:
    q, qp = rec.get("question", ""), rec.get("best_query", "")
    a, b = (q, qp) if orientation == "q_first" else (qp, q)
    row = {"pair_id": pair_id, "question_A": a, "question_B": b}
    row.update({c: "" for c in RESPONSE_COLS})
    return row


def _key_row(pair_id: str, rnd: int, stratum: str, orientation: str,
             round1_pair_id: str, rec: dict) -> dict:
    row = {c: rec.get(c, "") for c in KEY_COLS}
    row.update({"pair_id": pair_id, "round": rnd, "stratum": stratum,
                "orientation": orientation, "round1_pair_id": round1_pair_id})
    return row


def write_rows(rows: list[dict], cols: tuple[str, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cols), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Interval arithmetic for the sizing table
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    """Wilson score interval for a proportion. Chosen over the normal approximation
    because the interesting case is a SMALL false-pass count -- possibly zero -- where
    the Wald interval is degenerate."""
    if n <= 0:
        return (0.0, 1.0)
    d = n + z * z
    centre = (k + z * z / 2) / d
    half = z / d * math.sqrt(k * (n - k) / n + z * z / 4)
    return (max(0.0, centre - half), min(1.0, centre + half))


def wilson_fpc(k: int, n: int, pop: int, z: float = 1.959963985) -> tuple[float, float]:
    """Wilson with a finite-population correction: the width for the rate AMONG THESE
    `pop` pairs, having audited n of them. At n == pop the interval collapses, which is
    the correct statement -- a census of a finite population has no sampling error.

    This is a genuinely different estimand from `wilson`, which answers "what is the
    gate's false-pass rate as a property of the method", where these pairs are one draw
    from a superpopulation and a census still leaves binomial uncertainty.
    """
    if pop <= 1 or n >= pop:
        p = k / n if n else 0.0
        return (p, p)
    return wilson(k, n, z * math.sqrt((pop - n) / (pop - 1)))


def sizing_table(pop: int, ns: list[int], rates: list[float]) -> list[dict]:
    rows = []
    for n in ns:
        for p in rates:
            k = round(p * n)
            lo, hi = wilson(k, n)
            flo, fhi = wilson_fpc(k, n, pop)
            rows.append({"n": n, "observed_k": k, "p_hat": k / n if n else 0.0,
                         "wilson_lo": lo, "wilson_hi": hi, "wilson_width": hi - lo,
                         "fpc_lo": flo, "fpc_hi": fhi, "fpc_width": fhi - flo})
    return rows


# ---------------------------------------------------------------------------
# Design manifest
# ---------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def design_manifest(paths: list[Path], groups: dict[str, list[dict]],
                    n_excluded: int, key1: list[dict], key2: list[dict],
                    seed: int, retest_frac: float, out_stem: str) -> str:
    from collections import Counter
    drawn = Counter(k["stratum"] for k in key1)
    by_attack = Counter((k["stratum"], k["attack"] or "-") for k in key1)
    pop_win = len(groups.get("win", []))

    prov = _md_table(
        ["input file", "records", "sha256"],
        [[p.name, str(sum(1 for ln in p.read_text(encoding="utf-8").splitlines()
                          if ln.strip())), sha256_of(p)] for p in paths])

    strata = _md_table(
        ["stratum", "available", "drawn", "of which false_alarm", "of which hide"],
        [[s, str(len(groups.get(s, []))), str(drawn.get(s, 0)),
          str(by_attack.get((s, "false_alarm"), 0)),
          str(by_attack.get((s, "hide"), 0))] for s in REAL_STRATA]
        + [["catch", "-", str(drawn.get("catch", 0)), "-", "-"]])

    ns = sorted({20, 30, 40, 50, 60, pop_win, 100, 150} | {pop_win})
    tbl = sizing_table(pop_win, ns, [0.0, 0.05, 0.10, 0.20])
    sizing = _md_table(
        ["n audited", "false passes seen", "p&#770;", "95% Wilson (superpopulation)",
         "width", f"95% Wilson+FPC (among the {pop_win} wins)", "width"],
        [[str(r["n"]), str(r["observed_k"]), f"{r['p_hat']:.2f}",
          f"[{r['wilson_lo']:.3f}, {r['wilson_hi']:.3f}]", f"{r['wilson_width']:.3f}",
          (f"[{r['fpc_lo']:.3f}, {r['fpc_hi']:.3f}]" if r["n"] <= pop_win else "—"),
          (f"{r['fpc_width']:.3f}" if r["n"] <= pop_win else "—")]
         for r in tbl])

    return f"""# Equivalence audit — sampling design and provenance

Generated by `scripts/prepare_equivalence_audit.py`. Seed `{seed}`. Do not hand-edit;
re-run the script instead.

## Provenance of the pool

{prov}

Re-running with the same seed reproduces the same sheet **only if these hashes match**.
If a campaign run was still appending when the snapshot was taken, the pool is partial and
the audit covers the snapshot, not the finished campaign — top up with a second batch
(`--exclude_audited`) rather than re-drawing.

## Strata

{strata}

Excluded from the auditable pool: {n_excluded} records whose gate never passed a
paraphrase, or whose returned `best_query` was identical to `question` (a no-op, trivially
equivalent, and a giveaway in a blinded sheet). Their question text is reused as raw
material for catch trials, so no question appears twice across the sheet.

Round 1: **{len(key1)} pairs**. Round 2 (re-annotation, {retest_frac:.0%} of round 1):
**{len(key2)} pairs**.

## What each stratum licenses

- **win** — the headline. The fraction the annotator marks non-equivalent is the gate's
  false-pass rate *on the results the paper reports*. Every such pair is a win the paper
  should withdraw.
- **flip** — tests the paper's claim that the answer-flip subcategory is a *lower bound*
  on gate leakage. That claim requires the hand non-equivalence rate here to be materially
  **higher** than in `win`. If it is not, the flip statistic is not diagnostic.
- **subthreshold** — the selection-pressure contrast. Same gate, same proposer, but the
  optimiser failed to clear the entropy threshold. A leak rate higher in `win` than here
  is evidence the optimiser is actively *selecting for* gate failures rather than
  stumbling into them at the base rate.
- **catch** — annotator validation only. Any catch trial marked equivalent (or unsure)
  invalidates that session's other judgements; see the protocol.

## Sizing: interval width as a function of n

Two different estimands, and the honest answer differs between them.

{sizing}

Read the **FPC column** for the first estimand: *how often did the gate leak among the
{pop_win} wins this paper actually reports*. That population is finite and small enough to
**census**, which drives its sampling error to zero — which is why the default allocation
takes all {pop_win}. Rows above n={pop_win} are blank there because you cannot audit more
pairs than exist.

Read the **plain Wilson column** for the second estimand: *the gate's false-pass rate as a
property of the method*, where these wins are one draw from a superpopulation. Here a
census does **not** buy certainty: at n={pop_win} and an observed 10%, the interval is
still about [0.05, 0.19]. Rows at n=100/150 show what a larger campaign would buy — the
width falls roughly as 1/√n, so halving it from here costs roughly four times the pool.
This is the honest ceiling on what this audit can do, and it is a property of the pool
size, not of the annotator.

## Blinding

`{out_stem}.csv` contains only `{', '.join(ANNOTATOR_COLS)}`. Stratum, attack direction,
detector, entropy delta, the model's answer under q', and question_id live only in
`{out_stem}_key.csv`. Pair ids are assigned after the shuffle. Which of q/q' appears in
`question_A` is randomised per pair and recorded in the key as `orientation`.

**Move `{out_stem}_key.csv` out of the working directory before annotating.** With a
single annotator who owns this repository the blind is self-imposed; the file layout makes
the honest path the easy one but cannot enforce it. Disclose that in the paper.
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("jsonl", nargs="+", help="attack-outcome JSONL file(s) or globs")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n_win", type=int, default=-1,
                    help="pairs from the win stratum; -1 = census (default)")
    ap.add_argument("--n_flip", type=int, default=-1)
    ap.add_argument("--n_subthreshold", type=int, default=-1)
    ap.add_argument("--n_catch", type=int, default=8)
    ap.add_argument("--retest_frac", type=float, default=0.30,
                    help="fraction of round 1 re-presented in round 2 for the "
                         "intra-annotator agreement estimate")
    ap.add_argument("--exclude_audited", default="",
                    help="a previous <out>_key.csv; its question_ids are skipped so a "
                         "top-up batch is disjoint from the completed one")
    ap.add_argument("--benign_jsonl", default="",
                    help="reserved: a benign-paraphrase arm (same proposer and gate, "
                         "entropy objective off). No such file exists yet; see the "
                         "protocol. Named now so adding the arm is one flag, not a "
                         "redesign.")
    ap.add_argument("--out", default="results/equivalence_audit")
    ap.add_argument("--key_out", default="",
                    help="path for the un-blinding key (default <out>_key.csv). Point it "
                         "outside the repo if you want the blind to survive tab-completion.")
    args = ap.parse_args(argv)

    if args.benign_jsonl:
        print("--benign_jsonl: no benign-paraphrase arm exists yet; refusing to fabricate "
              "one. See results/equivalence_audit_protocol.md.", file=sys.stderr)
        return 2

    paths: list[Path] = []
    for pat in args.jsonl:
        p = Path(pat)
        paths.extend([p] if p.exists() else sorted(Path().glob(pat)))
    paths = sorted({p for p in paths if p.exists()})
    if not paths:
        print(f"no JSONL files matched {args.jsonl}", file=sys.stderr)
        return 2

    records = load_outcomes(paths)
    if args.exclude_audited:
        done = {r["question_id"] for r in read_rows(Path(args.exclude_audited))}
        records = [r for r in records if r.get("question_id") not in done]

    groups = partition(records)
    if not any(groups.values()):
        print("no auditable q/q' pairs (gate never passed a paraphrase that differs "
              "from the original)", file=sys.stderr)
        return 1

    excluded = excluded_records(records)
    catch = make_catch_pairs(excluded, args.n_catch, random.Random(args.seed + 977))
    alloc = {"win": args.n_win, "flip": args.n_flip,
             "subthreshold": args.n_subthreshold, "catch": args.n_catch}

    ann1, key1 = build_round1(groups, catch, alloc, args.seed)
    ann2, key2 = build_round2(key1, args.retest_frac, args.seed)

    out_csv = Path(args.out + ".csv")
    out_r2 = Path(args.out + "_round2.csv")
    out_key = Path(args.key_out or (args.out + "_key.csv"))
    out_md = Path(args.out + "_design.md")

    write_rows(ann1, ANNOTATOR_COLS, out_csv)
    write_rows(ann2, ANNOTATOR_COLS, out_r2)
    write_rows([*key1, *key2], KEY_COLS, out_key)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(design_manifest(paths, groups, len(excluded), key1, key2,
                                      args.seed, args.retest_frac, args.out),
                      encoding="utf-8")

    # Deliberately terse and stratum-free per pair: stdout must not un-blind either.
    from collections import Counter
    c = Counter(k["stratum"] for k in key1)
    print(f"pool: {len(records)} outcomes from {len(paths)} file(s); "
          f"auditable {sum(len(v) for v in groups.values())}, excluded {len(excluded)}")
    print(f"round 1: {len(ann1)} pairs  " +
          "  ".join(f"{s}={c.get(s, 0)}" for s in ALL_STRATA))
    print(f"round 2: {len(ann2)} pairs (re-annotation, {args.retest_frac:.0%})")
    print(f"wrote {out_csv}\n      {out_r2}\n      {out_md}")
    print(f"KEY -> {out_key}   move this out of the working directory before annotating.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
