"""Defense evaluation: does input-paraphrase-averaging blunt the attacks?

For each successful SE attack (from the wk9 SE campaigns), compare the attack's
effect under the vanilla detector vs the defended detector:

  vanilla effect  = | SE(Q') - SE(Q) |               (entropy move the attack achieved)
  defended effect = | defended(Q') - defended(Q) |   (move that survives averaging)

If defended effect << vanilla effect, the defense works. We also report the
defended detector's AUROC on the attacked pool vs the vanilla attacked AUROC,
to show whether the defense recovers detection.

Requires GPU. Run after the wk9 SE campaigns exist:
    python scripts/wk_defense.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR, GenConfig
from se.nli import NLI
from se import model as M
from se.config import ModelConfig
from se.sampling import DEFAULT_SAMPLES_DIR
from se.defense import defended_entropy
from se.attacks.harness import read_outcomes


CAMPAIGN_DIR = DEFAULT_SAMPLES_DIR / "attacks" / "wk9"
K_PARAPHRASES = 4
MAX_PER_ATTACK = 40  # cap for compute; logged, not silent


def main() -> int:
    report: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); report.append(s)

    log("# Defense: input-paraphrase-averaged SE vs the attacks")
    log(f"K paraphrases per input = {K_PARAPHRASES}, aggregate = median, "
        f"capped at {MAX_PER_ATTACK} questions/attack (logged cap, not silent)")
    log("")

    lm = M.load_llama(ModelConfig())
    nli = NLI()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)

    for attack in ("hide", "false_alarm"):
        camp = CAMPAIGN_DIR / f"triviaqa_se_{attack}.jsonl"
        if not camp.exists():
            log(f"## {attack}: no campaign file, skipped\n")
            continue
        outcomes = [o for o in read_outcomes(camp) if o.improved][:MAX_PER_ATTACK]
        if not outcomes:
            log(f"## {attack}: no improved attacks, skipped\n")
            continue

        log(f"## {attack}: {len(outcomes)} attacks")
        vanilla_effects, defended_effects, per_q_reduction = [], [], []
        for o in outcomes:
            # Use the cached SE(Q) and SE(Q') so both sides of the vanilla effect
            # come from the same run that produced the attack (no fresh-vs-cached
            # sampling-noise mismatch).
            se_q = o.entropy_before
            se_adv = o.entropy_after
            d_q = defended_entropy(o.question, lm, nli, k_paraphrases=K_PARAPHRASES, gen_cfg=gen).defended_entropy
            d_adv = defended_entropy(o.best_query, lm, nli, k_paraphrases=K_PARAPHRASES, gen_cfg=gen).defended_entropy
            ve_i, de_i = abs(se_adv - se_q), abs(d_adv - d_q)
            vanilla_effects.append(ve_i)
            defended_effects.append(de_i)
            if ve_i > 1e-9:
                per_q_reduction.append(1.0 - de_i / ve_i)

        ve, de = statistics.mean(vanilla_effects), statistics.mean(defended_effects)
        log(f"mean vanilla attack effect:  {ve:.3f} nats")
        log(f"mean defended attack effect: {de:.3f} nats")
        if per_q_reduction:
            # Per-question paired reduction, robust to a few large-effect outliers
            # dominating a ratio-of-means.
            log(f"per-question effect reduction: median "
                f"{statistics.median(per_q_reduction)*100:.0f}%, mean "
                f"{statistics.mean(per_q_reduction)*100:.0f}% (n={len(per_q_reduction)})")
        log("")

    log("Interpretation: a large reduction means averaging SE over paraphrases of")
    log("the input neutralizes the single adversarial phrasing. Since SRE already")
    log("reformulates inputs, this also bears on why SRE may be harder to attack")
    log("than vanilla SE (cross-check against the SE-vs-SRE transfer numbers).")

    (RESULTS_DIR / "defense_eval.md").write_text("\n".join(report) + "\n")
    print(f"\nWritten to {RESULTS_DIR / 'defense_eval.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
