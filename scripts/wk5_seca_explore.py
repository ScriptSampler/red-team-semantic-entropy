"""Week 5: SECA fork operational on our setup + Hide objective stubbed.

Deliverable from the plan: "SECA fork operational, running on your setup;
Hide attack objective specified and stubbed."

We forked SECA into vendor/SECA and ported its optimisation loop into
se.attacks.optimizer with our SE objective swapped in. This script proves
the machinery runs end to end on our Llama + NLI setup:

  1. load Llama 4-bit + DeBERTa NLI
  2. for 3 TriviaQA questions, propose paraphrases and feasibility-check them
  3. compute SE on the original vs an accepted paraphrase
  4. run the full optimise() loop for a couple of iterations on one example
     with the Hide objective, to show the beam search executes

Run after the Week 4 sampling run frees the GPU:
    python scripts/wk5_seca_explore.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.data import load_triviaqa
from se.se_pipeline import semantic_entropy
from se.attacks import feasibility, proposer, objectives, optimizer
from se.attacks.harness import load_pair


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Week 5: SECA fork operational + Hide objective")
    log("")
    log("Forked github.com/Buyun-Liang/SECA into vendor/SECA. Ported the")
    log("zeroth-order beam search (src/seca.py) into se.attacks.optimizer with")
    log("the objective swapped from MC-confidence to semantic entropy.")
    log("")

    pair = load_pair()
    log("loaded Llama 4-bit + DeBERTa NLI")
    log("")

    examples = load_triviaqa(split="validation")[:3]
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    log("## Proposer + feasibility + SE on 3 questions")
    for ex in examples:
        log(f"### {ex.question_id}: {ex.question}")
        se0 = semantic_entropy(ex.question, pair.lm, pair.nli, gen)
        log(f"original SE: {se0.entropy_nats:.3f} nats, {se0.n_clusters} clusters")
        cands = proposer.propose_many(ex.question, pair.lm, 3)
        for j, c in enumerate(cands):
            fr = feasibility.check(c, ex.question, pair.nli)
            tag = "feasible" if fr.feasible else f"rejected ({fr.reason})"
            log(f"  paraphrase {j}: {tag}")
            log(f"    {c}")
            if fr.feasible:
                se1 = semantic_entropy(c, pair.lm, pair.nli, gen)
                log(f"    paraphrase SE: {se1.entropy_nats:.3f} nats "
                    f"(delta {se1.entropy_nats - se0.entropy_nats:+.3f})")
        log("")

    log("## Hide objective, short optimise() run on one example")
    ex = examples[0]
    bundle = objectives.make_objective("hide", pair.lm, pair.nli, gen_cfg=gen)
    log(f"objective direction: {bundle.direction}")
    res = optimizer.optimize(
        ex.question, bundle.fn, pair.lm, pair.nli,
        max_iteration=3, candidate_size_M=2, top_N=2, verbose=True,
    )
    log(f"original entropy: {bundle.entropy(ex.question):.3f}")
    log(f"best entropy:     {bundle.entropy(res.best_query):.3f}")
    log(f"improved:         {res.improved}")
    log(f"objective calls:  {res.n_objective_calls}")
    log(f"best query:       {res.best_query}")
    log("")
    log("Fork is operational. Hide objective specified and runs end to end.")

    (RESULTS_DIR / "wk5_seca_explore.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'wk5_seca_explore.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
