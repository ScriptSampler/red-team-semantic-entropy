"""The replication AUROC is not one number: (correctness oracle) x (label convention).

WHY THIS SCRIPT EXISTS. paper/sections/experiments.tex quotes three replication AUROCs
(greedy / majority-of-samples / all-samples-correct) and states they are all adjudicated by
the alias-aware SPAN oracle. Only the greedy one had a producing artifact
(results/relabel_report.md, 0.694). The other two were an in-session recompute that was
never persisted, and the only stored file, results/replication_auroc.json, holds the
SUBSTRING versions (0.6977 / 0.7296 / 0.7868) computed from the labels CACHED AT SAMPLING
TIME. Quoting a substring number as a span number, or vice versa, is a category error the
repo could not previously detect, so this script computes the whole grid from one source
with one code path and commits it.

WHAT IT COMPUTES. From the cached Phase-1 pool (samples.jsonl: greedy + 10 samples of raw
generation text; entropy.jsonl: the SE value, which is NLI-clustered and therefore does NOT
depend on the correctness oracle at all), it recomputes correctness with the repo's own
`se.scoring.is_correct` under every oracle mode, and forms the three conventions:

    greedy       the greedy answer is correct
    majority     at least half the samples are correct  (sok*2 >= n; matches wk4_auroc.py)
    all_samples  all n samples are correct

AUROC is over the full 2000-question pool with the hallucination case as the positive class
(label = NOT correct) and the SE entropy as the score. No entropy-based selection anywhere,
so these are circularity-free (external review B2).

RECONCILIATION OF THE CACHED LABELS. `samples.jsonl` stores `greedy_correct` /
`samples_correct` booleans written when the pool was sampled, under the substring oracle of
that day. `se.scoring.normalize_answer` has since changed (punctuation is now DELETED, SQuAD
`remove_punc`, rather than replaced by a space), so a fresh substring recompute is not
guaranteed to reproduce the cached booleans. The report prints both the cached-label AUROCs
(which must reproduce results/replication_auroc.json exactly) and the freshly recomputed
substring AUROCs, plus the per-question disagreement count, so any fourth-decimal difference
has a named cause instead of being a mystery.

Run (the sample cache is WSL-side):
    wsl -d Ubuntu-24.04
    cd "/mnt/i/GITHUBPROJECTS/SE Research" && ./.venv-wsl/bin/python scripts/replication_conventions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR                          # noqa: E402
from se.data import TriviaQAExample                        # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR                # noqa: E402
from se.scoring import is_correct                          # noqa: E402
from se.stats import auroc_ci                              # noqa: E402

WK4_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
ORACLES = ("substring", "span", "strict")
CONVENTIONS = ("greedy", "majority", "all_samples")
PUBLISHED_SE = 0.828          # Tong et al., SE on TriviaQA no-context, Llama-3-8B


def _ex_from(rec: dict) -> TriviaQAExample:
    forms = rec.get("accepted_forms") or [rec.get("canonical_answer", "")]
    return TriviaQAExample(rec["question_id"], rec.get("question", "?"),
                           forms[0], forms[1:])


def _conventions(greedy_ok: bool, samples_ok: list[bool]) -> dict[str, bool]:
    n, sok = len(samples_ok), sum(samples_ok)
    return {
        "greedy": bool(greedy_ok),
        "majority": bool(sok * 2 >= n),          # "at least half", as in wk4_auroc.py
        "all_samples": bool(n > 0 and sok == n),
    }


def main() -> int:
    samples_path, entropy_path = WK4_DIR / "samples.jsonl", WK4_DIR / "entropy.jsonl"
    if not samples_path.exists() or not entropy_path.exists():
        print(f"missing cached pool under {WK4_DIR}; run wk4_sample.py + wk4_cluster.py",
              file=sys.stderr)
        return 1

    samples = {}
    for line in samples_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            samples[r["question_id"]] = r
    entropy = {}
    for line in entropy_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            entropy[r["question_id"]] = r

    qids = sorted(set(samples) & set(entropy))
    if not qids:
        print("no shared question_ids", file=sys.stderr)
        return 1

    ent = np.array([entropy[q]["entropy_nats"] for q in qids], dtype=float)

    # --- recompute correctness under every oracle, and read the cached labels ---
    labels: dict[str, dict[str, np.ndarray]] = {}    # labels[oracle][convention] = 0/1 wrong
    rates: dict[tuple[str, str], tuple[int, int]] = {}
    for oracle in ORACLES:
        labels[oracle] = {c: [] for c in CONVENTIONS}
        for q in qids:
            rec = samples[q]
            ex = _ex_from(rec)
            g = is_correct(rec["greedy"], ex, oracle)
            s = [is_correct(t, ex, oracle) for t in rec["samples"]]
            for c, ok in _conventions(g, s).items():
                labels[oracle][c].append(0 if ok else 1)   # 1 = hallucination = positive
        for c in CONVENTIONS:
            labels[oracle][c] = np.asarray(labels[oracle][c], dtype=int)
            n_corr = int((labels[oracle][c] == 0).sum())
            rates[(oracle, c)] = (n_corr, len(qids))

    labels["cached"] = {c: [] for c in CONVENTIONS}
    for q in qids:
        rec = samples[q]
        for c, ok in _conventions(bool(rec["greedy_correct"]),
                                  [bool(x) for x in rec["samples_correct"]]).items():
            labels["cached"][c].append(0 if ok else 1)
    for c in CONVENTIONS:
        labels["cached"][c] = np.asarray(labels["cached"][c], dtype=int)
        rates[("cached", c)] = (int((labels["cached"][c] == 0).sum()), len(qids))

    def auc(oracle: str, conv: str):
        return auroc_ci(labels[oracle][conv], ent, n_boot=2000, seed=0)

    cells = {(o, c): auc(o, c) for o in (*ORACLES, "cached") for c in CONVENTIONS}

    # --- per-question disagreement between the cached booleans and a fresh substring pass ---
    dis_greedy = int((labels["cached"]["greedy"] != labels["substring"]["greedy"]).sum())
    dis_samples = 0
    for q in qids:
        rec = samples[q]
        ex = _ex_from(rec)
        fresh = [is_correct(t, ex, "substring") for t in rec["samples"]]
        dis_samples += sum(1 for a, b in zip(rec["samples_correct"], fresh)
                           if bool(a) != bool(b))

    # --- what the stored JSON says, if it is still around (it is gitignored) ---
    stored_path = RESULTS_DIR / "replication_auroc.json"
    stored = json.loads(stored_path.read_text()) if stored_path.exists() else None

    L: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); L.append(s)

    log("# Replication AUROC: the full (oracle x convention) grid")
    log("")
    log("Producing script: `scripts/replication_conventions.py`. One code path, one source: the")
    log("cached Phase-1 pool (raw generation text + NLI-clustered SE entropy). The entropy is")
    log("independent of the correctness oracle, so only the LABEL moves across this grid.")
    log("")
    log(f"pool: {len(qids)} questions (samples n={len(samples)}, entropy n={len(entropy)})")
    log("label = NOT correct (hallucination is the positive class); score = SE entropy, nats.")
    log("CIs are 2000-replicate percentile bootstrap over questions, seed 0.")
    log("")
    log("## The six cells the paper needs")
    log("")
    log("| oracle | convention | correct rate | AUROC | 95% CI |")
    log("| --- | --- | --- | --- | --- |")
    for o in ("substring", "span"):
        for c in CONVENTIONS:
            k, n = rates[(o, c)]
            ci = cells[(o, c)]
            log(f"| {o} | {c} | {k}/{n} ({k/n:.1%}) | **{ci.point:.4f}** | "
                f"[{ci.lo:.4f}, {ci.hi:.4f}] |")
    log("")
    log("## Supplementary: strict exact-match oracle, and the cached labels")
    log("")
    log("`cached` = the `greedy_correct` / `samples_correct` booleans stored in samples.jsonl at")
    log("sampling time (the substring oracle of that day). These are what wk4_auroc.py scored,")
    log("so they are the row that must reproduce `results/replication_auroc.json`.")
    log("")
    log("| oracle | convention | correct rate | AUROC | 95% CI |")
    log("| --- | --- | --- | --- | --- |")
    for o in ("strict", "cached"):
        for c in CONVENTIONS:
            k, n = rates[(o, c)]
            ci = cells[(o, c)]
            log(f"| {o} | {c} | {k}/{n} ({k/n:.1%}) | {ci.point:.4f} | "
                f"[{ci.lo:.4f}, {ci.hi:.4f}] |")
    log("")

    log("## Reconciliation: cached labels vs a fresh substring recompute")
    log("")
    log(f"greedy labels that disagree: **{dis_greedy}** of {len(qids)}")
    log(f"per-sample labels that disagree: **{dis_samples}** of {len(qids) * 10}")
    log("")
    if stored is not None:
        log("Stored `results/replication_auroc.json` (gitignored, so this may be absent on a")
        log("fresh clone) vs the `cached` row recomputed here:")
        log("")
        log("| convention | stored JSON | recomputed from cached labels | delta |")
        log("| --- | --- | --- | --- |")
        key = {"greedy": "greedy_correct", "majority": "majority_correct",
               "all_samples": "all_samples_correct"}
        for c in CONVENTIONS:
            sv = stored.get("auroc", {}).get(key[c])
            rv = cells[("cached", c)].point
            log(f"| {c} | {sv:.6f} | {rv:.6f} | {rv - sv:+.2e} |" if sv is not None
                else f"| {c} | (absent) | {rv:.6f} | - |")
    else:
        log("`results/replication_auroc.json` is not present (it is gitignored); the `cached`")
        log("row above is the reproducible replacement for it.")
    log("")
    log("If the cached row reproduces the JSON but the fresh `substring` row does not, the")
    log("difference is the oracle CODE having changed since sampling (`normalize_answer` now")
    log("DELETES punctuation rather than replacing it with a space), not a scoring bug. The")
    log("disagreement counts above size that effect directly.")
    log("")

    log("## What this means for the paper")
    log("")
    span = {c: cells[("span", c)].point for c in CONVENTIONS}
    sub = {c: cells[("substring", c)].point for c in CONVENTIONS}
    log(f"Span-oracle spread (the number experiments.tex calls the convention span): "
        f"{max(span.values()) - min(span.values()):.4f} "
        f"({min(span.values()):.4f} to {max(span.values()):.4f}).")
    log(f"Substring-oracle spread: {max(sub.values()) - min(sub.values()):.4f}.")
    log(f"Gap from the operative span/greedy figure to the published {PUBLISHED_SE}: "
        f"{PUBLISHED_SE - span['greedy']:.4f}. "
        f"Gap from the span/all-samples figure: {PUBLISHED_SE - span['all_samples']:.4f}.")
    log("")
    log("The all-samples convention is the one mechanically coupled to the score (a")
    log("ten-of-ten-correct sample set is likelier to be semantically homogeneous, hence")
    log("low-entropy), so its AUROC is partly the score scored against itself. It is reported")
    log("here for completeness, not as the headline.")

    out = RESULTS_DIR / "replication_conventions.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
