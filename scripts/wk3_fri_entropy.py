"""Week 3 Friday session.

Walk the 50 Monday sample records, cluster each by NLI, compute the
semantic entropy, and check that high-entropy questions tend to be
the ones the model gets wrong.

Outputs:
  - results/wk3_fri_entropy.md (the report)
  - ~/.cache/se-research/samples/wk3_mon_50q/entropy.jsonl (per-question
    entropy + cluster assignments, so Week 4 does not redo this work)

Pass criteria for this session (from the plan):
  - mean entropy when greedy is wrong is materially higher than when
    greedy is right
  - AUROC on the 50-question subset is comfortably above 0.5 (not the
    Phase 1 stop condition; that needs the full 2000 question pass and
    requires comparison to Farquhar et al.'s number)
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.entropy import cluster_and_score
from se.nli import NLI
from se.sampling import DEFAULT_SAMPLES_DIR, iter_sample_records


SAMPLES_DIR = DEFAULT_SAMPLES_DIR / "wk3_mon_50q"


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log("# Week 3 Fri: semantic clustering + entropy on the 50 Monday samples")
    log(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    log("")

    log("## Load NLI")
    t0 = time.perf_counter()
    nli = NLI()
    log(f"NLI loaded in {time.perf_counter()-t0:.1f}s")
    log("")

    log("## Cluster and score each question")
    records = list(iter_sample_records(SAMPLES_DIR))
    log(f"records: {len(records)}")

    entries: list[dict] = []
    t0 = time.perf_counter()
    for rec in records:
        cs = cluster_and_score(rec.samples, nli)
        entries.append({
            "question_id": rec.question_id,
            "question": rec.question,
            "canonical_answer": rec.canonical_answer,
            "greedy_correct": rec.greedy_correct,
            "samples_correct": rec.samples_correct,
            "n_samples": len(rec.samples),
            "n_clusters": cs.n_clusters,
            "entropy_nats": cs.entropy_nats,
            "entropy_bits": cs.entropy_bits,
            "assignments": cs.assignments,
        })
    elapsed = time.perf_counter() - t0
    log(f"clustered {len(records)} questions in {elapsed:.1f}s ({elapsed/len(records):.2f}s/Q)")
    log("")

    # Persist for Week 4.
    out_jsonl = SAMPLES_DIR / "entropy.jsonl"
    with out_jsonl.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    log(f"per-question entropy written to {out_jsonl}")
    log("")

    log("## Distribution stats")
    entropies = [e["entropy_nats"] for e in entries]
    log(f"entropy (nats): mean={statistics.mean(entropies):.3f}, "
        f"median={statistics.median(entropies):.3f}, "
        f"min={min(entropies):.3f}, max={max(entropies):.3f}")
    log(f"cluster count:  mean={statistics.mean([e['n_clusters'] for e in entries]):.2f}, "
        f"median={statistics.median([e['n_clusters'] for e in entries]):.0f}, "
        f"max={max(e['n_clusters'] for e in entries)}")
    log("")

    log("## Greedy-correct vs greedy-wrong, entropy")
    right = [e["entropy_nats"] for e in entries if e["greedy_correct"]]
    wrong = [e["entropy_nats"] for e in entries if not e["greedy_correct"]]
    log(f"greedy correct ({len(right)}): mean entropy {statistics.mean(right):.3f} nats")
    log(f"greedy wrong   ({len(wrong)}): mean entropy {statistics.mean(wrong):.3f} nats")
    log(f"gap:            {statistics.mean(wrong) - statistics.mean(right):.3f} nats")
    log("")

    log("## AUROC, entropy ranking vs greedy correctness")
    log("Positive class is greedy wrong (the hallucination we want to flag).")
    labels = [0 if e["greedy_correct"] else 1 for e in entries]
    scores = [e["entropy_nats"] for e in entries]
    if 0 < sum(labels) < len(labels):
        auroc = roc_auc_score(labels, scores)
        log(f"AUROC on 50 questions: {auroc:.3f}")
    else:
        log("AUROC undefined (all one class)")
    log("")
    log("Caveat: 50 questions is small and the label is greedy correctness,")
    log("which Farquhar et al. handle differently. The Phase 1 stop-condition")
    log("number comes from the 2000 question Week 4 run with their convention.")
    log("")

    log("## Top 10 highest entropy")
    log("Expectation: mostly greedy-wrong.")
    log("")
    top = sorted(entries, key=lambda e: -e["entropy_nats"])[:10]
    log("| entropy | clusters | greedy ok | samples ok | question_id | question |")
    log("| ------- | -------- | --------- | ---------- | ----------- | -------- |")
    for e in top:
        sok = sum(e["samples_correct"])
        log(f"| {e['entropy_nats']:.3f} | {e['n_clusters']} | "
            f"{'yes' if e['greedy_correct'] else 'no':>3} | "
            f"{sok}/{e['n_samples']} | {e['question_id']} | "
            f"{e['question'][:60]}{'...' if len(e['question'])>60 else ''} |")
    log("")

    log("## Bottom 10 lowest entropy")
    log("Expectation: mostly greedy-correct.")
    log("")
    bottom = sorted(entries, key=lambda e: e["entropy_nats"])[:10]
    log("| entropy | clusters | greedy ok | samples ok | question_id | question |")
    log("| ------- | -------- | --------- | ---------- | ----------- | -------- |")
    for e in bottom:
        sok = sum(e["samples_correct"])
        log(f"| {e['entropy_nats']:.3f} | {e['n_clusters']} | "
            f"{'yes' if e['greedy_correct'] else 'no':>3} | "
            f"{sok}/{e['n_samples']} | {e['question_id']} | "
            f"{e['question'][:60]}{'...' if len(e['question'])>60 else ''} |")
    log("")

    out_path = RESULTS_DIR / "wk3_fri_entropy.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
