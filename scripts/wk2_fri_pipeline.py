"""Week 2 Friday session.

Wire model and dataset together. For ten real TriviaQA validation
questions, generate one greedy answer, print it next to the canonical
answer and a rough correctness flag. Then measure the cost of the SE
sampling step (N=10 at T=1.0) over 100 questions and extrapolate to
the full validation split.

Run:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk2_fri_pipeline.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se import model as M
from se.config import GenConfig, ModelConfig, RESULTS_DIR
from se.data import TriviaQAExample, load_triviaqa


# Light normalisation: lowercase, drop articles, strip punctuation,
# collapse whitespace. Same idea as the SQuAD F1 normaliser.
_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def _normalise(s: str) -> str:
    s = s.lower()
    s = _PUNCT.sub(" ", s)
    s = _ARTICLES.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def is_acceptable(generation: str, ex: TriviaQAExample) -> bool:
    """Rough containment check. Week 3 replaces this with the proper SE scorer."""
    g = _normalise(generation)
    for form in ex.all_acceptable():
        f = _normalise(form)
        if f and f in g:
            return True
    return False


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log(f"# Week 2 Fri: end-to-end pipeline + timing")
    log(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    log("")

    log("## Load model and dataset")
    t0 = time.perf_counter()
    lm = M.load_llama(ModelConfig())
    t_load = time.perf_counter() - t0
    log(f"model loaded in {t_load:.1f} s, VRAM {lm.load_vram_mb:.0f} MB")

    examples = load_triviaqa(split="validation")
    log(f"TriviaQA validation: {len(examples)} examples")
    log("")

    log("## Greedy generation for 10 real questions")
    log("Correctness flag is a rough containment check; the full SE scorer ships in Week 3.")
    log("")
    greedy_times: list[float] = []
    n_right = 0
    for i, ex in enumerate(examples[:10]):
        t0 = time.perf_counter()
        ans = M.generate_one(lm, ex.question, GenConfig(max_new_tokens=64))
        dt = time.perf_counter() - t0
        greedy_times.append(dt)
        ok = is_acceptable(ans, ex)
        if ok:
            n_right += 1
        mark = "ok " if ok else "no "
        log(f"[{i}] {mark} ({dt:.2f} s)")
        log(f"    Q: {ex.question}")
        log(f"    canonical: {ex.answer}")
        log(f"    model:     {ans}")
        log("")

    log(f"greedy: {n_right}/10 acceptable, mean {sum(greedy_times)/len(greedy_times):.2f} s per question")
    log("")

    log("## Timing: N=10 sampling over 100 questions")
    log("This is the actual SE sampling primitive. The number drives the Week 4 eval budget.")
    log("")
    n_questions = 100
    gen = GenConfig(max_new_tokens=64, n_samples=10, temperature=1.0, seed=0)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    for ex in examples[:n_questions]:
        _ = M.generate_samples(lm, ex.question, gen)
    t_sample = time.perf_counter() - t0
    peak_sample_mb = torch.cuda.max_memory_allocated() / 1024**2

    per_q = t_sample / n_questions
    per_sample = per_q / gen.n_samples
    log(f"N={gen.n_samples} samples for {n_questions} questions: {t_sample:.1f} s total")
    log(f"  per question:  {per_q:.2f} s")
    log(f"  per sample:    {per_sample:.3f} s")
    log(f"  peak VRAM:     {peak_sample_mb:.0f} MB ({peak_sample_mb/1024:.2f} GB)")
    log("")

    log("## Runtime extrapolations at N=10")
    for n in (1000, 2000, 5000, len(examples)):
        secs = per_q * n
        hrs = secs / 3600
        log(f"  {n:>6} questions: {hrs:.2f} h")
    log("")

    log("## Verdict")
    full_hours = per_q * len(examples) / 3600
    if full_hours <= 36:
        log(f"Full validation eval at N=10 projects to {full_hours:.1f} h, inside the 12 to 36 h budget.")
    else:
        log(f"Full validation eval projects to {full_hours:.1f} h, over the 36 h budget. Drop N to 5 or use a 2000-question subset for Week 4 first pass.")

    out_path = RESULTS_DIR / "pipeline_check.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
