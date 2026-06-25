"""Cross-detector transferability: does an attack tuned on one detector move the other?

The wk10 matrix reports SE and SRE degradation from separate campaigns (different
questions). This script measures true per-question transfer on the SAME questions:

  SE -> SRE: take the paraphrase found against SE, evaluate SRE on it vs the
             original. Did SRE move in the attack's intended direction?
  SRE -> SE: the symmetric test.

A high transfer rate means one meaning-preserving paraphrase fools both detectors
-> we are attacking the paradigm of sampling-based uncertainty detection, not one
implementation. That is the differentiated result from docs/positioning.md.

Requires GPU (re-evaluates the other detector on cached paraphrases). Run after
the wk9 TriviaQA campaigns exist:
    python scripts/wk_transfer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR, GenConfig, ModelConfig
from se import model as M
from se.nli import NLI
from se.sampling import DEFAULT_SAMPLES_DIR
from se.se_pipeline import semantic_entropy
from se.sre import self_reflective_entropy
from se.attacks.harness import read_outcomes


CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"
SRE_KW = dict(n_reform=3, k_samples=8, temperature=0.8)
MAX_PER_CELL = 40  # compute cap, logged


def _intended_moved(attack: str, before: float, after: float) -> bool:
    return (after < before) if attack == "hide" else (after > before)


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Cross-detector transferability (SE <-> SRE)")
    log(f"capped at {MAX_PER_CELL} questions per cell (logged cap)")
    log("")

    lm = M.load_llama(ModelConfig())
    nli = NLI()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    def eval_other(detector: str, q: str) -> float:
        if detector == "se":
            return semantic_entropy(q, lm, nli, gen).entropy_nats
        return self_reflective_entropy(q, lm, nli, **SRE_KW).entropy_nats

    # source detector -> target detector
    pairs = [("se", "sre"), ("sre", "se")]
    for src, tgt in pairs:
        for attack in ("hide", "false_alarm"):
            camp = CAMPAIGN_DIR / f"triviaqa_{src}_{attack}.jsonl"
            if not camp.exists():
                log(f"## {src}->{tgt} {attack}: no campaign, skipped\n")
                continue
            outcomes = [o for o in read_outcomes(camp) if o.improved][:MAX_PER_CELL]
            if not outcomes:
                log(f"## {src}->{tgt} {attack}: no improved attacks, skipped\n")
                continue
            moved = 0
            deltas = []
            for o in outcomes:
                b = eval_other(tgt, o.question)
                a = eval_other(tgt, o.best_query)
                deltas.append(a - b)
                if _intended_moved(attack, b, a):
                    moved += 1
            rate = moved / len(outcomes)
            log(f"## {src}->{tgt} {attack}: {len(outcomes)} paraphrases")
            log(f"transfer rate (target moved in intended direction): {rate*100:.0f}%")
            log(f"mean target delta: {np.mean(deltas):+.3f} nats")
            log("")

    log("Interpretation: high SE->SRE and SRE->SE transfer means a single")
    log("meaning-preserving paraphrase defeats both detectors -> the vulnerability")
    log("is in the sampling-based-uncertainty paradigm, not one implementation.")

    (RESULTS_DIR / "transfer_eval.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'transfer_eval.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
