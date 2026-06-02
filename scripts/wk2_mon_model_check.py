"""Week 2 Monday session.

Download Llama 3.1 8B Instruct, load it at 4-bit, run a greedy generation
and a small N-sample generation, and measure VRAM. Writes a short report to
results/model_check.md.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk2_mon_model_check.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, ModelConfig, RESULTS_DIR
from se import model as M


TEST_QUESTIONS = [
    "What is the capital of France?",
    "Who wrote the novel Pride and Prejudice?",
    "What year did the first human land on the Moon?",
]


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log(f"# Week 2 Mon: Llama 3.1 8B Instruct, 4-bit load + generation")
    log(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    total_vram = (
        torch.cuda.get_device_properties(0).total_memory / 1024**3
        if torch.cuda.is_available() else 0.0
    )
    log(f"Total VRAM: {total_vram:.2f} GB")
    log("")

    log("## Load (downloads on first run)")
    cfg = ModelConfig()
    lm = M.load_llama(cfg)
    log(f"model: {cfg.model_id}")
    log(f"quant: 4-bit {cfg.bnb_4bit_quant_type}, double_quant={cfg.bnb_4bit_use_double_quant}, compute={cfg.compute_dtype}")
    log(f"load time: {lm.load_seconds:.1f} s")
    log(f"VRAM after load: {lm.load_vram_mb:.0f} MB ({lm.load_vram_mb/1024:.2f} GB)")
    log("")

    log("## Greedy single-answer generation")
    for q in TEST_QUESTIONS:
        t0 = time.perf_counter()
        ans = M.generate_one(lm, q, GenConfig(max_new_tokens=48))
        dt = time.perf_counter() - t0
        log(f"Q: {q}")
        log(f"A: {ans!r}  ({dt:.2f} s)")
        log("")

    log("## N-sample generation (the SE sampling step)")
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    q = "What is the capital of Australia?"
    t0 = time.perf_counter()
    samples = M.generate_samples(lm, q, gen)
    dt = time.perf_counter() - t0
    log(f"Q: {q}")
    log(f"N={gen.n_samples} samples at T={gen.temperature} in {dt:.2f} s ({dt/gen.n_samples:.2f} s/sample):")
    for i, s in enumerate(samples):
        log(f"  [{i}] {s!r}")
    log("")

    log("## VRAM")
    peak = M.peak_vram_mb()
    log(f"peak VRAM: {peak:.0f} MB ({peak/1024:.2f} GB) of {total_vram:.2f} GB")
    headroom = total_vram - peak / 1024
    log(f"headroom: {headroom:.2f} GB")
    log("")
    log("## Verdict")
    if peak / 1024 < total_vram * 0.85:
        log("Fits comfortably with headroom for KV cache growth and larger N.")
    else:
        log("Tight. Consider N=5 or shorter max_new_tokens for full-scale runs.")

    out_path = RESULTS_DIR / "model_check.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
