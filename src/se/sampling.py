"""Multi-sample collection and JSONL storage.

For each question, generate N samples at a sampling temperature plus
one greedy answer. Store as JSONL with the config in a sidecar manifest.
The samples directory lives on the WSL Linux filesystem by default,
not on /mnt/i, because we touch each file enough during SE clustering
to feel the cross-boundary slowdown.

Read back with iter_sample_records for the Week 3 SE pipeline and the
Week 4 full eval.
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Iterator

import torch

from . import model as M
from .config import GenConfig, ModelConfig
from .data import TriviaQAExample


DEFAULT_SAMPLES_DIR = Path(os.path.expanduser("~/.cache/se-research/samples"))


@dataclass
class SampleRecord:
    """One question's worth of samples plus its scoring labels."""
    question_id: str
    question: str
    canonical_answer: str
    accepted_forms: list[str]
    greedy: str
    greedy_correct: bool
    samples: list[str]
    samples_correct: list[bool]


def _record_to_json(rec: SampleRecord) -> str:
    return json.dumps(asdict(rec), ensure_ascii=False)


def _json_to_record(line: str) -> SampleRecord:
    obj = json.loads(line)
    return SampleRecord(**obj)


def _write_manifest(out_dir: Path, model_cfg: ModelConfig, gen_cfg: GenConfig,
                    split: str, n_questions: int, elapsed_s: float) -> None:
    """Sidecar JSON describing how the samples in this directory were generated."""
    manifest = {
        "model": {
            "model_id": model_cfg.model_id,
            "load_in_4bit": model_cfg.load_in_4bit,
            "bnb_4bit_quant_type": model_cfg.bnb_4bit_quant_type,
            "bnb_4bit_use_double_quant": model_cfg.bnb_4bit_use_double_quant,
            "compute_dtype": str(model_cfg.compute_dtype),
        },
        "gen": {
            "max_new_tokens": gen_cfg.max_new_tokens,
            "temperature": gen_cfg.temperature,
            "top_p": gen_cfg.top_p,
            "n_samples": gen_cfg.n_samples,
            "seed": gen_cfg.seed,
        },
        "dataset": {
            "name": "trivia_qa",
            "config": "rc.nocontext",
            "split": split,
        },
        "n_questions": n_questions,
        "elapsed_seconds": elapsed_s,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def collect_samples(
    examples: list[TriviaQAExample],
    lm: M.LoadedModel,
    gen_cfg: GenConfig | None = None,
    *,
    scoring_fn: Callable[[str, TriviaQAExample], bool],
    out_dir: Path | str = DEFAULT_SAMPLES_DIR,
    split: str = "validation",
    progress_every: int = 10,
) -> Path:
    """Run greedy + N=gen.n_samples for each example, append to JSONL.

    Returns the directory the samples landed in. A manifest.json sidecar
    records the model and sampling config.
    """
    gen_cfg = gen_cfg or GenConfig()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "samples.jsonl"

    # Truncate any prior run in this directory so partial state cannot
    # masquerade as a completed run.
    if jsonl_path.exists():
        jsonl_path.unlink()

    greedy_cfg = GenConfig(
        max_new_tokens=gen_cfg.max_new_tokens,
        temperature=gen_cfg.temperature,
        top_p=gen_cfg.top_p,
        n_samples=1,
        seed=gen_cfg.seed,
    )

    t0 = time.perf_counter()
    with jsonl_path.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(examples):
            greedy = M.generate_one(lm, ex.question, greedy_cfg)
            samples = M.generate_samples(lm, ex.question, gen_cfg)
            rec = SampleRecord(
                question_id=ex.question_id,
                question=ex.question,
                canonical_answer=ex.answer,
                accepted_forms=ex.all_acceptable(),
                greedy=greedy,
                greedy_correct=scoring_fn(greedy, ex),
                samples=samples,
                samples_correct=[scoring_fn(s, ex) for s in samples],
            )
            f.write(_record_to_json(rec) + "\n")
            if (i + 1) % progress_every == 0:
                elapsed = time.perf_counter() - t0
                print(f"  collected {i+1}/{len(examples)} in {elapsed:.1f}s "
                      f"({elapsed/(i+1):.2f}s/Q)", flush=True)

    elapsed = time.perf_counter() - t0
    _write_manifest(out_dir, ModelConfig(), gen_cfg, split, len(examples), elapsed)
    return out_dir


def iter_sample_records(samples_dir: Path | str) -> Iterator[SampleRecord]:
    """Streaming iterator over records, for Week 3 SE clustering."""
    p = Path(samples_dir) / "samples.jsonl"
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield _json_to_record(line)


def load_manifest(samples_dir: Path | str) -> dict:
    return json.loads((Path(samples_dir) / "manifest.json").read_text())
