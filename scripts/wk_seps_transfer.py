"""SE -> SEP transfer experiment (stretch goal, Weeks 15+).

Question: does an input paraphrase optimized against sampling-based Semantic
Entropy also move a hidden-state Semantic Entropy Probe (SEP)? If yes, the
attack reaches the representation, not just the sampled outputs -> "attack the
paradigm". Differentiate CORVUS (arXiv 2601.14310): that is model-side LoRA,
suppression-only, no NLI; this is input-side, bidirectional, NLI-constrained.

Pipeline:
  1. Train a SEP on clean TriviaQA: TBG hidden states -> binarized SE label
     (from the Week 4 entropy.jsonl). Report the probe's own AUROC (sanity:
     does the probe approximate SE at all on our setup).
  2. For each attacked question in the wk9 SE campaigns, extract TBG features
     of the ORIGINAL and the ATTACKED paraphrase, and measure whether the SEP
     score moved in the attack's intended direction (Hide: down, False-alarm: up).
  3. Report transfer rate and the SEP AUROC degradation under the attack.

Requires GPU (feature extraction). Run after the wk9 SE campaigns exist:
    python scripts/wk_seps_transfer.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR, ModelConfig
from se import model as M
from se.sampling import DEFAULT_SAMPLES_DIR
from se.seps import SEPProbe, binarize_entropy, extract_tbg_features
from se.data import load_triviaqa
from se.attacks.harness import read_outcomes


WK4_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"
TRAIN_FRAC = 0.7


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# SE -> SEP transfer experiment")
    log("")

    # --- load clean SE labels ---
    entropy_path = WK4_DIR / "entropy.jsonl"
    if not entropy_path.exists():
        log("No Week 4 entropy.jsonl; run Phase 1 first.")
        (RESULTS_DIR / "seps_transfer.md").write_text("\n".join(report) + "\n")
        return 1
    rows = [json.loads(l) for l in entropy_path.read_text().splitlines() if l.strip()]
    by_id = {ex.question_id: ex for ex in load_triviaqa(split="validation")}
    rows = [r for r in rows if r["question_id"] in by_id]
    # entropy.jsonl is in sample order, not shuffled. Use a seeded permutation so
    # the train/test split is random and reproducible.
    rng = np.random.default_rng(0)
    perm = rng.permutation(len(rows))
    rows = [rows[i] for i in perm]
    questions = [by_id[r["question_id"]].question for r in rows]
    entropies = np.array([r["entropy_nats"] for r in rows])
    n_train = int(len(rows) * TRAIN_FRAC)
    # Threshold from TRAIN entropies only; otherwise the held-out entropies leak
    # into the label definition and inflate the probe's reported AUROC.
    thr = float(np.median(entropies[:n_train]))
    labels = binarize_entropy(entropies, threshold=thr)
    log(f"clean set: {len(rows)} questions, train high-entropy rate "
        f"{labels[:n_train].mean():.2f}, threshold {thr:.3f}")

    # --- extract features + train probe ---
    lm = M.load_llama(ModelConfig())
    log("extracting TBG features for clean set...")
    feats = extract_tbg_features(lm, questions)
    probe = SEPProbe.train(feats[:n_train], labels[:n_train])
    test_scores = probe.score(feats[n_train:])
    test_labels = labels[n_train:]
    if 0 < test_labels.sum() < len(test_labels):
        probe_auc = roc_auc_score(test_labels, test_scores)
        log(f"SEP probe AUROC (predicting binarized SE on held-out): {probe_auc:.3f}")
    else:
        log("SEP probe AUROC: held-out is single-class, undefined")
    log("")

    # --- transfer: do attacked paraphrases move the SEP score? ---
    log("## Transfer from SE attacks to the SEP score")
    for attack in ("hide", "false_alarm"):
        camp = CAMPAIGN_DIR / f"triviaqa_se_{attack}.jsonl"
        if not camp.exists():
            log(f"{attack}: no campaign file, skipped")
            continue
        outcomes = [o for o in read_outcomes(camp) if o.improved]
        if not outcomes:
            log(f"{attack}: no improved attacks, skipped")
            continue
        orig_q = [o.question for o in outcomes]
        adv_q = [o.best_query for o in outcomes]
        f_orig = extract_tbg_features(lm, orig_q)
        f_adv = extract_tbg_features(lm, adv_q)
        s_orig = probe.score(f_orig)
        s_adv = probe.score(f_adv)
        # intended direction: hide lowers SEP score, false_alarm raises it
        moved = (s_adv < s_orig) if attack == "hide" else (s_adv > s_orig)
        log(f"{attack}: {len(outcomes)} attacks; SEP score moved in intended "
            f"direction for {moved.mean()*100:.0f}% (mean delta "
            f"{(s_adv - s_orig).mean():+.3f})")
    log("")
    log("Interpretation: a high transfer rate means the input paraphrase tuned")
    log("against sampling-SE also fools the hidden-state probe -> the weakness is")
    log("in the representation. Differentiate CORVUS (model-side, suppression-only).")

    (RESULTS_DIR / "seps_transfer.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'seps_transfer.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
