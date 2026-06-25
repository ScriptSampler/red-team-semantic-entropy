"""Week 8: SRE implementation, AUROC vs vanilla SE on 100 TriviaQA questions.

Implements Semantic Reformulation Entropy (Tong et al., arXiv 2509.17445) in
se.sre and checks it reproduces in the same ballpark as the paper. For 100
validation questions we compute both vanilla SE and SRE, label correctness
by greedy answer, and compare AUROC.

Paper reference numbers (Llama3-8B, no context):
  TriviaQA  SE 0.828  SRE 0.871

Our vanilla SE on the Week 4 2000-question set is the local baseline; this
script's 100-question SE is a sanity cross-check on the same code path.

Run after Week 4 completes and the GPU is free:
    python scripts/wk8_sre.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.data import load_triviaqa
from se.sampling import DEFAULT_SAMPLES_DIR
from se.scoring import is_acceptable
from se.se_pipeline import semantic_entropy
from se.sre import self_reflective_entropy
from se.attacks.harness import load_pair


N_QUESTIONS = int(os.environ.get("SRE_N", "100"))
OUT = DEFAULT_SAMPLES_DIR / "wk8_sre_100q.jsonl"


def main() -> int:
    examples = load_triviaqa(split="validation")[:N_QUESTIONS]
    pair = load_pair()
    se_gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    rows: list[dict] = []
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if line.strip():
                obj = json.loads(line); done.add(obj["question_id"]); rows.append(obj)

    t0 = time.perf_counter()
    with OUT.open("a", encoding="utf-8") as f:
        for i, ex in enumerate(examples):
            if ex.question_id in done:
                continue
            se = semantic_entropy(ex.question, pair.lm, pair.nli, se_gen,
                                  example=ex, compute_greedy=True)
            sre = self_reflective_entropy(ex.question, pair.lm, pair.nli,
                                          n_reform=3, k_samples=8, temperature=0.8)
            row = {
                "question_id": ex.question_id,
                "greedy_correct": bool(se.greedy_correct),
                "se_entropy": se.entropy_nats,
                "sre_entropy": sre.entropy_nats,
                "se_clusters": se.n_clusters,
                "sre_clusters": sre.n_clusters,
                "n_reform": len(sre.reformulations),
            }
            f.write(json.dumps(row) + "\n"); f.flush()
            rows.append(row)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(examples)} in {time.perf_counter()-t0:.0f}s", flush=True)

    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    labels = [0 if r["greedy_correct"] else 1 for r in rows]
    se_scores = [r["se_entropy"] for r in rows]
    sre_scores = [r["sre_entropy"] for r in rows]

    log("# Week 8: SRE vs SE on 100 TriviaQA questions")
    log("")
    log(f"questions: {len(rows)}")
    log(f"greedy correct: {sum(r['greedy_correct'] for r in rows)}/{len(rows)}")
    log("")
    if 0 < sum(labels) < len(labels):
        se_auc = roc_auc_score(labels, se_scores)
        sre_auc = roc_auc_score(labels, sre_scores)
        log(f"vanilla SE AUROC: {se_auc:.3f}  (paper 0.828)")
        log(f"SRE AUROC:        {sre_auc:.3f}  (paper 0.871)")
        log(f"SRE - SE:         {sre_auc - se_auc:+.3f}  (paper +0.043)")
    else:
        log("AUROC undefined (all one class in this subset)")
    log("")
    log(f"mean SE entropy:  {statistics.mean(se_scores):.3f}")
    log(f"mean SRE entropy: {statistics.mean(sre_scores):.3f}")
    log(f"mean reformulations kept: {statistics.mean([r['n_reform'] for r in rows]):.2f}")
    log("")
    log("Note: SRE here uses NLI union-find clustering, not the paper's full")
    log("energy-based HSC. If AUROC is far below 0.871, that backend is the")
    log("first thing to revisit; the plan permits dropping SRE to future work.")

    (RESULTS_DIR / "wk8_sre.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'wk8_sre.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
