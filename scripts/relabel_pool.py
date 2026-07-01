"""Relabel the cached Phase-1 pool under the new oracle, and report the
circularity-free clean AUROC + all the data-quality checks the critic owes B3.

CPU only: reads the cached samples.jsonl (greedy + samples text + accepted_forms)
and entropy.jsonl (per-question SE entropy, UNAFFECTED by the oracle change since
SE clustering uses NLI, not string normalisation). Recomputes correctness under
substring / span / strict oracles and writes results/relabel_report.md plus a
relabeled correctness file the stratified sampler (B1) will consume.

Deliverables (external review B3 + critic nits):
  - old-substring vs new-span label-flip count
  - substring/span/strict oracle-sensitivity table for clean SE AUROC
  - article-in-title scan (normalize_answer strips a/an/the)
  - alias-set provenance / richness
  - entity-ambiguity fraction (all-accepted-forms single-token gold)
  - the decisive number: clean SE AUROC on the FULL pool (no entropy selection)
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.data import TriviaQAExample
from se.sampling import DEFAULT_SAMPLES_DIR
from se.scoring import is_correct, normalize_answer

WK4_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
OUT_LABELS = WK4_DIR / "relabeled.jsonl"


def _ex_from(rec: dict) -> TriviaQAExample:
    forms = rec.get("accepted_forms") or [rec.get("canonical_answer", "")]
    return TriviaQAExample(rec["question_id"], rec.get("question", "?"),
                           forms[0], forms[1:])


def _auroc(labels, scores):
    y = np.asarray(labels)
    if 0 < y.sum() < len(y):
        return float(roc_auc_score(y, np.asarray(scores, float)))
    return float("nan")


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    samples = [json.loads(l) for l in (WK4_DIR / "samples.jsonl").read_text().splitlines() if l.strip()]
    entropy = {json.loads(l)["question_id"]: json.loads(l)
               for l in (WK4_DIR / "entropy.jsonl").read_text().splitlines() if l.strip()}

    log("# Relabel report: cached Phase-1 pool under the new oracle")
    log("")
    log(f"cached questions: {len(samples)} samples, {len(entropy)} entropy")
    log("")

    # --- recompute correctness under each oracle; keep entropy from cache ---
    rows = []
    for rec in samples:
        qid = rec["question_id"]
        if qid not in entropy:
            continue
        ex = _ex_from(rec)
        greedy = rec["greedy"]
        row = {
            "question_id": qid,
            "entropy_nats": entropy[qid]["entropy_nats"],
            "old_greedy_correct": bool(rec["greedy_correct"]),
            "greedy_span": is_correct(greedy, ex, "span"),
            "greedy_strict": is_correct(greedy, ex, "strict"),
            "greedy_substr": is_correct(greedy, ex, "substring"),
            "n_forms": len(ex.all_acceptable()),
            "single_token_gold": all(len(normalize_answer(f).split()) <= 1
                                     for f in ex.all_acceptable() if normalize_answer(f)),
            "canonical": ex.answer,
        }
        rows.append(row)

    n = len(rows)

    # --- label flips: old cached (substring) vs new span ---
    log("## Label flips: old substring -> new span (greedy correctness)")
    flip_to_wrong = sum(1 for r in rows if r["old_greedy_correct"] and not r["greedy_span"])
    flip_to_right = sum(1 for r in rows if not r["old_greedy_correct"] and r["greedy_span"])
    old_correct = sum(r["old_greedy_correct"] for r in rows)
    new_correct = sum(r["greedy_span"] for r in rows)
    log(f"old correct rate: {old_correct}/{n} ({old_correct/n:.1%})")
    log(f"new correct rate: {new_correct}/{n} ({new_correct/n:.1%})")
    log(f"flipped correct->wrong (over-credit removed): {flip_to_wrong}")
    log(f"flipped wrong->correct (under-credit recovered): {flip_to_right}")
    log(f"total labels changed: {flip_to_wrong + flip_to_right} "
        f"({(flip_to_wrong + flip_to_right)/n:.1%})")
    log("")

    # --- oracle sensitivity: clean SE AUROC under each oracle ---
    log("## Clean SE AUROC on the FULL 2000-question pool (circularity-free)")
    log("Label = greedy WRONG (positive/hallucination class); score = SE entropy.")
    log("No entropy-based selection: this is the detector's real ranking power.")
    log("")
    log("| oracle | correct rate | clean AUROC |")
    log("| --- | --- | --- |")
    for key, name in [("greedy_substr", "substring (old)"),
                      ("greedy_span", "span (new primary)"),
                      ("greedy_strict", "strict EM")]:
        labels = [0 if r[key] else 1 for r in rows]
        auc = _auroc(labels, [r["entropy_nats"] for r in rows])
        cr = sum(r[key] for r in rows) / n
        log(f"| {name} | {cr:.1%} | {auc:.3f} |")
    log("")
    log("Phase-1 replication reference: 0.787 (all-samples label). A full-pool")
    log("clean AUROC in the ~0.75-0.80 band confirms the 1.000 from the attack")
    log("matrix was pure selection artifact, per external review B2/§2.")
    log("")

    # --- article-in-title scan (critic nit) ---
    log("## Article-in-title scan (normalize_answer strips a/an/the)")
    art_titles = [r for r in rows
                  if r["canonical"].strip().lower().split()[:1] and
                  r["canonical"].strip().lower().split()[0] in ("the", "a", "an")]
    log(f"gold canonical answers beginning with an article: {len(art_titles)} of {n}")
    for r in art_titles[:8]:
        log(f"  - {r['canonical']!r} -> normalises to {normalize_answer(r['canonical'])!r}")
    log("Residual: these lose the leading article (SQuAD-standard behaviour). Aliases")
    log("usually include the article-free form, so span match still succeeds; the risk")
    log("is only distinct entities differing solely by an article, which is rare.")
    log("")

    # --- alias provenance / richness ---
    log("## Alias-set richness (provenance: TriviaQA Aliases + NormalizedAliases)")
    forms = [r["n_forms"] for r in rows]
    log(f"accepted forms per question: mean {statistics.mean(forms):.1f}, "
        f"median {statistics.median(forms):.0f}, min {min(forms)}, max {max(forms)}")
    thin = sum(1 for f in forms if f <= 1)
    log(f"questions with a SINGLE accepted form (under-credit risk): {thin} ({thin/n:.1%})")
    log("Loader se.data.load_triviaqa combines row['answer']['aliases'] and")
    log("['normalized_aliases']; a mean well above 1 confirms the full set is loaded.")
    log("")

    # --- entity-ambiguity fraction ---
    log("## Entity-ambiguity (single-token gold; string oracle can over-match)")
    st = sum(r["single_token_gold"] for r in rows)
    log(f"questions whose every accepted form is a single token: {st} ({st/n:.1%})")
    st_wrong = sum(1 for r in rows if r["single_token_gold"] and not r["greedy_span"])
    log(f"  of those, currently labelled WRONG (hide-pool candidates): {st_wrong}")
    log("For hide targets, over-matching would mislabel a wrong answer as right and")
    log("DROP it from the pool (shrinks, not corrupts). If this fraction is large, the")
    log("model-graded judge stops being deferrable.")
    log("")

    OUT_LABELS.write_text("\n".join(
        json.dumps({"question_id": r["question_id"],
                    "entropy_nats": r["entropy_nats"],
                    "greedy_correct": r["greedy_span"],           # NEW primary label
                    "greedy_correct_strict": r["greedy_strict"],
                    "greedy_correct_substr": r["greedy_substr"],
                    "single_token_gold": r["single_token_gold"]})
        for r in rows) + "\n")
    log(f"Relabeled correctness written to {OUT_LABELS} (consumed by the B1 sampler).")

    (RESULTS_DIR / "relabel_report.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'relabel_report.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
