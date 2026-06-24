"""Week 4 phase C: AUROC analysis and replication writeup.

Loads no models. Reads samples.jsonl plus entropy.jsonl. Computes AUROC
under three correctness conventions so the comparison to Farquhar et al.
is not bottlenecked on a single label choice:

  1. greedy_correct        the greedy answer matched accepted forms
  2. all_samples_correct   all 10 samples matched
  3. majority_correct      at least half of the samples matched

Writes results/replication_results.md with the headline numbers, the
distribution stats, and the audit data points the Friday session needs
to decide whether to tag phase-1-complete.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk4_auroc.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR


OUT_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"

# Farquhar et al. published TriviaQA AUROC for SE on LLaMA-class models
# is in the 0.75 to 0.79 range. Phase 1 stop condition is +-3pp of that.
TARGET_LOW = 0.72
TARGET_HIGH = 0.82


def main() -> int:
    samples_path = OUT_DIR / "samples.jsonl"
    entropy_path = OUT_DIR / "entropy.jsonl"
    if not samples_path.exists() or not entropy_path.exists():
        print("missing samples.jsonl or entropy.jsonl; run wk4_sample.py and wk4_cluster.py first.",
              file=sys.stderr)
        return 1

    # Build keyed indices.
    samples_by_id: dict[str, dict] = {}
    with samples_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            samples_by_id[obj["question_id"]] = obj

    entropy_by_id: dict[str, dict] = {}
    with entropy_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            entropy_by_id[obj["question_id"]] = obj

    joined_ids = sorted(set(samples_by_id) & set(entropy_by_id))
    if not joined_ids:
        print("no shared question_ids between samples and entropy.", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for qid in joined_ids:
        s = samples_by_id[qid]
        e = entropy_by_id[qid]
        n = len(s["samples_correct"])
        sok = sum(s["samples_correct"])
        rows.append({
            "question_id": qid,
            "n_samples": n,
            "samples_correct_count": sok,
            "greedy_correct": s["greedy_correct"],
            "all_samples_correct": sok == n,
            "majority_correct": sok * 2 >= n,
            "n_clusters": e["n_clusters"],
            "entropy_nats": e["entropy_nats"],
        })

    n = len(rows)
    entropies = [r["entropy_nats"] for r in rows]
    n_clusters = [r["n_clusters"] for r in rows]

    report: list[str] = []
    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log("# Phase 1 replication results: SE on TriviaQA")
    log("")
    log("## Configuration")
    log("- model: meta-llama/Llama-3.1-8B-Instruct, 4-bit nf4, bf16 compute")
    log("- NLI: microsoft/deberta-large-mnli, bidirectional argmax entailment")
    log("- dataset: TriviaQA rc.nocontext validation, first 2000 questions")
    log("- generation: N=10 samples at T=1.0, max_new_tokens=48, seed=0")
    log("- entropy: Shannon over cluster sizes, natural log")
    log("")
    log("## Coverage")
    log(f"questions scored: {n} of 2000 targeted")
    log("")
    log("## Distribution stats")
    log(f"entropy nats: mean {statistics.mean(entropies):.3f}, "
        f"median {statistics.median(entropies):.3f}, "
        f"min {min(entropies):.3f}, max {max(entropies):.3f}")
    log(f"cluster count: mean {statistics.mean(n_clusters):.2f}, "
        f"median {statistics.median(n_clusters):.0f}, "
        f"max {max(n_clusters)}")
    log("")

    log("## Correctness label rates")
    log(f"greedy_correct:        {sum(r['greedy_correct'] for r in rows)} of {n} "
        f"({sum(r['greedy_correct'] for r in rows)/n*100:.1f}%)")
    log(f"all_samples_correct:   {sum(r['all_samples_correct'] for r in rows)} of {n} "
        f"({sum(r['all_samples_correct'] for r in rows)/n*100:.1f}%)")
    log(f"majority_correct:      {sum(r['majority_correct'] for r in rows)} of {n} "
        f"({sum(r['majority_correct'] for r in rows)/n*100:.1f}%)")
    log("")

    log("## AUROC")
    log("Positive class is the hallucination case (the boolean is False).")
    log("")
    log("| label convention | AUROC | pass (in [0.72, 0.82])? |")
    log("| --- | --- | --- |")
    for label_key in ("greedy_correct", "all_samples_correct", "majority_correct"):
        labels = [0 if r[label_key] else 1 for r in rows]
        if 0 < sum(labels) < len(labels):
            auc = roc_auc_score(labels, entropies)
            pass_ = TARGET_LOW <= auc <= TARGET_HIGH
            log(f"| {label_key} | {auc:.3f} | {'yes' if pass_ else 'no'} |")
        else:
            log(f"| {label_key} | undefined (all one class) | n/a |")
    log("")

    log("## Right vs wrong entropy gap")
    for label_key in ("greedy_correct", "all_samples_correct", "majority_correct"):
        right = [r["entropy_nats"] for r in rows if r[label_key]]
        wrong = [r["entropy_nats"] for r in rows if not r[label_key]]
        if right and wrong:
            log(f"- {label_key}: right={len(right)} mean {statistics.mean(right):.3f}, "
                f"wrong={len(wrong)} mean {statistics.mean(wrong):.3f}, "
                f"gap {statistics.mean(wrong) - statistics.mean(right):.3f} nats")
    log("")

    log("## Stop-condition audit")
    log("Phase 1 stop condition: replicate Farquhar SE AUROC within ±3pp.")
    log("Farquhar Nature 2024 reports TriviaQA SE AUROC in the 0.75 to 0.79 range")
    log("on LLaMA-class models. Target window for this replication is 0.72 to 0.82.")
    log("")
    log("If any of the three AUROC labels lands in [0.72, 0.82], tag phase-1-complete.")
    log("If all three fall outside, see Friday's audit notes.")

    out_path = RESULTS_DIR / "replication_results.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
