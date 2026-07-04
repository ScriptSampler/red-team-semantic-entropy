# Start here — overnight of Sat 2026-07-04 → Sun 2026-07-05

## 60-second summary
Tonight resolved the deepest construct-validity question in the project and it forces one
decision from you. **The paraphrase attack moves Semantic Entropy, but whether that is a real
attack or an artifact of the NLI clusterer that SE shares with the attack's own gate CANNOT be
cheaply adjudicated** — the obvious independent oracle (a sentence embedder) is near-chance
(AUROC 0.51) on exactly the adversarial case. That difficulty is not a dead end: it makes the
**null-controlled evaluation protocol** the paper's strongest contribution.

## Read next, in order
1. **`docs/framing_decision.md`** — your decision: attack-led (A) vs protocol-led (B, recommended).
   Contains the three calls you need to make.
2. **`docs/option_b_draft.md`** — proposed prose for framing B, so you can judge it concretely.
3. **`docs/definitive_run_plan.md`** — the recipe + the ~39 GPU-hour cost reality + open risks.
4. **`docs/critique_log.md`** entries 13–17 — the full critic-gated record of tonight.

## The result (n=6 is machinery-validation, NOT a result — needs n≥80)
| clusterer | net (attack − benign) | role |
| --- | --- | --- |
| shared NLI (detector's own) | +0.636 [+0.239, +1.034] | confounded upper bound |
| exact-match (independent, strict) | +0.140 [−0.004, +0.291] | strict lower bound |
| e5 embedding (independent, semantic) | — | can't adjudicate: 0.51 AUROC on hard negatives |

The attack robustly beats benign paraphrasing **under the detector's own clusterer** — but that
measure cannot separate "the model's answers changed" from "the NLI clustered them differently."
No cheap independent oracle closes that gap.

## What's built and verified (94 tests, ~24 commits, all critic-gated)
- Null-controlled protocol: score-independent selection, answer-invariance gate, benign noise
  floor (attack scored as a percentile in the benign distribution, not max-vs-max), 3-band
  seed<benign<attack, pre-registered decision rule + survival ratio.
- The full independent-clusterer family: NLI / exact-match / embedding (e5) / **LLM-judge**
  (turnkey — plug in a 2nd model).
- Threshold-calibration tool (Youden-J on STS-B/PAWS + domain-matched TriviaQA short-answer
  hard negatives).
- A 7-agent verification pass over the new tooling caught + fixed **two correctness bugs**
  (seed=0 collision deflating the noise floor; youden-J inf in the near-chance regime), both
  regression-tested and verified on real generations.

## Your three decisions (nothing proceeds without them)
1. **Framing** — A (attack-led, riskier) or B (protocol-led, critic + I recommend).
2. **A second model** for the LLM-judge adjudicator (gates the attack claim + the equivalence
   audit; must be non-Llama, non-NLI, self-validated).
3. **Compute** — full n≥80 (~39 GPU-h) vs a cheaper optimiser / smaller n with wide CIs.

## Note on the earlier "cache lost" scare
Ignore `OVERNIGHT_2026-07-02.md`'s alarm about a lost cache / dead GPU — that was my error
(querying the wrong WSL distro). Everything is intact; the GPU path is `wsl -d Ubuntu-24.04`.
