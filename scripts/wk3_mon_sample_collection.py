"""Week 3 Monday session.

For the first 50 TriviaQA validation questions, generate one greedy
answer plus N=10 samples at T=1.0, and store everything as JSONL on
the WSL Linux filesystem at ~/.cache/se-research/samples/wk3_mon_50q.

After collection, walk the records and produce a diversity report at
results/wk3_mon_samples_inspect.md. We are looking for two things:

  (1) the model is actually sampling with variation, not collapsing
      to a single answer at T=1.0
  (2) the variation pattern lines up with correctness, so high
      entropy correlates with the model being wrong. This is the SE
      signal we want to test in Friday's session.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk3_mon_sample_collection.py
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se import model as M
from se.config import GenConfig, ModelConfig, RESULTS_DIR
from se.data import load_triviaqa
from se.sampling import (
    DEFAULT_SAMPLES_DIR,
    collect_samples,
    iter_sample_records,
    load_manifest,
)
from se.scoring import is_acceptable, normalise


N_QUESTIONS = 50
OUT_DIR = DEFAULT_SAMPLES_DIR / "wk3_mon_50q"


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log(f"# Week 3 Mon: N=10 sample collection on {N_QUESTIONS} TriviaQA questions")
    log(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    log("")

    log("## Load model and dataset")
    t0 = time.perf_counter()
    lm = M.load_llama(ModelConfig())
    log(f"model loaded in {time.perf_counter()-t0:.1f}s, VRAM {lm.load_vram_mb:.0f} MB")

    examples = load_triviaqa(split="validation")[:N_QUESTIONS]
    log(f"selected first {N_QUESTIONS} validation examples")
    log("")

    log("## Generate samples")
    gen = GenConfig(
        max_new_tokens=48,         # tighter than Friday's 64; matches median answer length
        n_samples=10,
        temperature=1.0,
        top_p=1.0,
        seed=0,
    )
    log(f"config: N={gen.n_samples}, T={gen.temperature}, max_new_tokens={gen.max_new_tokens}, seed={gen.seed}")
    log(f"output: {OUT_DIR}")
    log("")
    out_dir = collect_samples(examples, lm, gen, scoring_fn=is_acceptable,
                              out_dir=OUT_DIR, split="validation")
    manifest = load_manifest(out_dir)
    log(f"collected {manifest['n_questions']} records in {manifest['elapsed_seconds']:.1f}s "
        f"({manifest['elapsed_seconds']/manifest['n_questions']:.2f}s/Q)")
    log("")

    log("## Diversity inspection")
    records = list(iter_sample_records(out_dir))
    distinct_counts: list[int] = []
    sample_correct_rates: list[float] = []
    greedy_correct_count = 0
    all_samples_correct = 0
    no_samples_correct = 0

    for rec in records:
        norm_set = {normalise(s) for s in rec.samples}
        distinct_counts.append(len(norm_set))
        rate = sum(rec.samples_correct) / len(rec.samples_correct) if rec.samples_correct else 0.0
        sample_correct_rates.append(rate)
        if rec.greedy_correct:
            greedy_correct_count += 1
        if all(rec.samples_correct):
            all_samples_correct += 1
        if not any(rec.samples_correct):
            no_samples_correct += 1

    log(f"greedy correctness:     {greedy_correct_count}/{len(records)}")
    log(f"all 10 samples right:   {all_samples_correct}/{len(records)}")
    log(f"all 10 samples wrong:   {no_samples_correct}/{len(records)}")
    log(f"distinct samples per Q: mean={statistics.mean(distinct_counts):.2f}, "
        f"median={statistics.median(distinct_counts):.0f}, "
        f"min={min(distinct_counts)}, max={max(distinct_counts)}")
    log("")

    log("### Distinct-count histogram")
    hist = Counter(distinct_counts)
    for k in sorted(hist):
        bar = "#" * hist[k]
        log(f"  {k:>2} distinct: {bar} ({hist[k]})")
    log("")

    log("### Greedy-correct vs greedy-wrong, sample correctness rate")
    correct_rates = [r for rec, r in zip(records, sample_correct_rates) if rec.greedy_correct]
    wrong_rates = [r for rec, r in zip(records, sample_correct_rates) if not rec.greedy_correct]
    if correct_rates:
        log(f"when greedy correct ({len(correct_rates)}): mean sample correctness {statistics.mean(correct_rates):.2f}")
    if wrong_rates:
        log(f"when greedy wrong   ({len(wrong_rates)}): mean sample correctness {statistics.mean(wrong_rates):.2f}")
    log("")

    log("## Five questions the greedy answer got wrong")
    log("These should be high-entropy under SE if the method is working.")
    log("")
    wrong_examples = [r for r in records if not r.greedy_correct]
    for rec in wrong_examples[:5]:
        norm_set = {normalise(s) for s in rec.samples}
        log(f"### {rec.question_id}")
        log(f"Q: {rec.question}")
        log(f"canonical: {rec.canonical_answer}")
        log(f"greedy:    {rec.greedy}")
        log(f"distinct sample forms: {len(norm_set)}")
        log(f"sample correctness:    {sum(rec.samples_correct)}/{len(rec.samples_correct)}")
        for i, (s, ok) in enumerate(zip(rec.samples, rec.samples_correct)):
            tag = "ok" if ok else "no"
            log(f"  [{i}] {tag} {s}")
        log("")

    log("## Five questions the greedy answer got right")
    log("These should be low-entropy under SE.")
    log("")
    right_examples = [r for r in records if r.greedy_correct]
    for rec in right_examples[:5]:
        norm_set = {normalise(s) for s in rec.samples}
        log(f"### {rec.question_id}")
        log(f"Q: {rec.question}")
        log(f"canonical: {rec.canonical_answer}")
        log(f"greedy:    {rec.greedy}")
        log(f"distinct sample forms: {len(norm_set)}")
        log(f"sample correctness:    {sum(rec.samples_correct)}/{len(rec.samples_correct)}")
        for i, (s, ok) in enumerate(zip(rec.samples, rec.samples_correct)):
            tag = "ok" if ok else "no"
            log(f"  [{i}] {tag} {s}")
        log("")

    out_path = RESULTS_DIR / "wk3_mon_samples_inspect.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
