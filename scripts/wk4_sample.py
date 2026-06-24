"""Week 4 phase A: sample 2000 TriviaQA validation questions at N=10.

Loads only Llama 4-bit. Does not touch the NLI model, so peak VRAM stays
around 5.5 GB and system RAM only carries one tokenizer plus activations.

The script is resumable. On startup it reads any existing samples.jsonl
in the output directory and skips question_ids already recorded, so an
interrupted run can be resumed by re-invoking with the same out dir.
Records are appended line-by-line and flushed after each question, so a
crash at most loses the question in flight.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk4_sample.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se import model as M
from se.config import GenConfig, ModelConfig
from se.data import load_triviaqa
from se.sampling import DEFAULT_SAMPLES_DIR, SampleRecord
from se.scoring import is_acceptable


# Configuration for the Phase 1 replication run.
N_QUESTIONS = 2000
OUT_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
GEN = GenConfig(
    max_new_tokens=48,
    n_samples=10,
    temperature=1.0,
    top_p=1.0,
    seed=0,
)
PROGRESS_EVERY = 50


def _completed_ids(jsonl_path: Path) -> set[str]:
    done: set[str] = set()
    if not jsonl_path.exists():
        return done
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                done.add(obj["question_id"])
            except Exception:
                # Corrupt trailing line from an interrupted write. Truncate
                # is handled below by reopening in append mode.
                pass
    return done


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUT_DIR / "samples.jsonl"

    already = _completed_ids(jsonl_path)
    print(f"resuming: {len(already)} question_ids already in {jsonl_path}", flush=True)

    print("loading TriviaQA validation...", flush=True)
    all_examples = load_triviaqa(split="validation")
    examples = all_examples[:N_QUESTIONS]
    todo = [ex for ex in examples if ex.question_id not in already]
    print(f"total selected: {len(examples)}, to do: {len(todo)}", flush=True)
    if not todo:
        print("nothing to do, exiting.", flush=True)
        return 0

    print("loading Llama 3.1 8B Instruct 4-bit...", flush=True)
    t0 = time.perf_counter()
    lm = M.load_llama(ModelConfig())
    print(f"loaded in {time.perf_counter()-t0:.1f}s, "
          f"VRAM {lm.load_vram_mb:.0f} MB", flush=True)

    greedy_cfg = GenConfig(
        max_new_tokens=GEN.max_new_tokens,
        temperature=GEN.temperature,
        top_p=GEN.top_p,
        n_samples=1,
        seed=GEN.seed,
    )

    t_start = time.perf_counter()
    with jsonl_path.open("a", encoding="utf-8") as f:
        for i, ex in enumerate(todo):
            greedy = M.generate_one(lm, ex.question, greedy_cfg)
            samples = M.generate_samples(lm, ex.question, GEN)
            rec = SampleRecord(
                question_id=ex.question_id,
                question=ex.question,
                canonical_answer=ex.answer,
                accepted_forms=ex.all_acceptable(),
                greedy=greedy,
                greedy_correct=is_acceptable(greedy, ex),
                samples=samples,
                samples_correct=[is_acceptable(s, ex) for s in samples],
            )
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

            if (i + 1) % PROGRESS_EVERY == 0:
                elapsed = time.perf_counter() - t_start
                per_q = elapsed / (i + 1)
                eta_s = per_q * (len(todo) - (i + 1))
                vram = torch.cuda.memory_allocated() / 1024**2
                print(f"  {i+1}/{len(todo)} done in {elapsed:.0f}s "
                      f"({per_q:.2f}s/Q), ETA {eta_s/60:.1f} min, "
                      f"VRAM {vram:.0f} MB", flush=True)

    elapsed = time.perf_counter() - t_start
    print(f"phase A done. {len(todo)} questions in {elapsed:.0f}s.", flush=True)

    manifest = OUT_DIR / "manifest.json"
    manifest.write_text(json.dumps({
        "phase": "A",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "load_in_4bit": True,
        "n_samples": GEN.n_samples,
        "temperature": GEN.temperature,
        "max_new_tokens": GEN.max_new_tokens,
        "seed": GEN.seed,
        "split": "validation",
        "n_questions_target": N_QUESTIONS,
        "n_questions_completed_this_run": len(todo),
        "elapsed_seconds_this_run": elapsed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
