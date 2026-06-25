# Positioning: how this project sits against the literature

Written 2026-06-25 after an independent, web-grounded verification pass over a
piece of positioning feedback. Every arXiv id below was checked against the
actual source. This is the document to position the preprint against, and the
related-work spine for Phase 3.

## The contribution, stated precisely

We attack the **detector**, not the model. Given a sampling-based hallucination
detector (Semantic Entropy and its reformulation variant SRE), we search for a
**meaning-preserving paraphrase of the question** that moves the detector's
uncertainty score in a chosen direction while the model's answer is unchanged:

- **Hide**: suppress semantic entropy on a question the model answers wrong, so
  the detector misses the hallucination.
- **False-alarm**: inflate semantic entropy on a question the model answers
  right, so the detector flags a correct answer.

Constraint: bidirectional DeBERTa-NLI semantic equivalence between original and
paraphrase. Black-box (no detector gradients). Benchmarks TriviaQA + SQuAD,
Llama 3.1 8B. This exact cell is **open** in the literature (verified by a
multi-phrasing null search, 2026-06-25).

## The four fence posts (verified)

| Work | arXiv | What it is | Why it does NOT scoop us |
| --- | --- | --- | --- |
| **SECA** (Liang, Vidal et al., NeurIPS 2025) | 2510.04398 | Zeroth-order constrained search for prompts that elicit hallucinations; MMLU MCQ | Attacks the **model's answer**, not a detector. We fork its optimizer as tooling only. |
| **REALISTA** (Liang, Vidal et al., ICML 2026) | 2605.12813 | SECA successor: continuous latent-space edit directions; free-form reasoning models; MMLU | Still attacks the **model** to elicit hallucinations. No detector. The "SE" it edits is *semantic equivalence*, not *semantic entropy* — a name collision. Cite-and-distinguish, not a threat. |
| **SRE** (Tong et al., Sept 2025) | 2509.17445 | **Semantic Reformulation Entropy**: a detector (input reformulations + energy clustering) on SQuAD/TriviaQA | It is our **victim**, a defense to be attacked. Cannot scoop an attack. |
| **SEPs** (Kossen et al., COLM 2024) | 2406.15927 | Linear probe approximating SE from one hidden state | A transfer target, not an attack. (See risk below.) |

## The real scooping risks, ranked (the feedback got this wrong)

The feedback named **REALISTA** as the biggest risk. That is **incorrect**:
REALISTA attacks models, not detectors. The genuine adjacent-attack risks are:

1. **CORVUS** (Min, Pham, Zhang, Sun; arXiv **2601.14310**, Jan 2026) —
   **the real one to differentiate.** It red-teams single-pass hallucination
   detectors and explicitly degrades **SEP**. Our novelty survives because CORVUS
   is (a) **model-side** (fine-tunes LoRA adapters, inputs fixed), not an
   input-paraphrase attack; (b) **suppression-only**, not bidirectional — no
   false-alarm direction; (c) **no semantic-equivalence/NLI constraint**;
   (d) targets single-pass telemetry + probes, **not the sampling-based SE
   detector**; (e) Alpaca/FAVA, not TriviaQA/SQuAD. If we pursue the SEP-transfer
   angle, CORVUS must be cited and contrasted head-on.
2. **"Uncertainty is Fragile"** (arXiv 2407.11282) — shows answer-confidence is
   manipulable via a fine-tuned **backdoor trigger** on MCQ self-evaluation. Not
   input paraphrase, not SE, not bidirectional. Distinguish on threat model.
3. **Text-origin paraphrase-evasion line** — Adversarial Paraphrasing (2506.07001,
   NeurIPS 2025), CoPA (2505.15337, EMNLP 2025). Attack AI-vs-human **text
   classifiers**, evasion-only. Different victim class. Two naming/positioning
   cautions: pick a project name distinct from "Adversarial Paraphrasing", and
   contrast our **hard bidirectional-NLI gate** against CoPA's soft >90% cosine
   similarity.
4. **Red-teaming Activation Probes** (2511.00554) — prompts to fool safety
   probes generally; not SE/hallucination. Weak overlap.

## Verdict on the feedback

**Valid but overstated.** Act on the structural advice; correct two errors.

- Gap is open (confirmed). Lead-with-False-alarm, transferability, and defense
  are sound and largely unclaimed (confirmed).
- "So what?" risk for a plain one-directional Hide result is a reasonable,
  unverifiable editorial call — heed it.
- REALISTA is **not** the biggest risk and does not attack detectors. The feedback
  missed **CORVUS**, which is.

## What this changes about the plan (recommendation)

The Phase 2 infrastructure already runs **both directions x both detectors x both
benchmarks**, so the stronger framing is mostly a matter of analysis emphasis plus
two scoped additions, not a rebuild:

1. **Lead the paper with False-alarm.** It is the more surprising, less "of course"
   result and is genuinely unaddressed against these detectors. Our own Week 3 data
   already shows SE false-alarming on correct answers (tc_56: right answer, max
   entropy) — the attack amplifies a real fragility.
2. **Frame SE -> SRE as a transferability result**, not two separate attacks. One
   paraphrase that fools both is "attacking the paradigm". (Already in the matrix.)
3. **Stretch goal: SEP transfer** (Weeks 15+ stretch, swapping the defence slot or
   sharing it). Strongest "attack the paradigm" claim, but only with explicit CORVUS
   differentiation. Needs hidden-state probe training — more engineering; scope as
   optional.
4. **Keep a small defence experiment** (input-paraphrase averaging, or an NLI
   hardening) so the paper is arms-race-shaped, not just "we broke it".
5. **Citations**: add SECA, REALISTA, SRE, SEPs, CORVUS, Uncertainty-is-Fragile,
   Adversarial Paraphrasing, CoPA to the bib now (ids above) so Related Work in
   Week 12 is a fill-in, not a search.

## Citation ids (verified 2026-06-25)

SECA 2510.04398 · REALISTA 2605.12813 · SRE 2509.17445 · SEPs 2406.15927 ·
CORVUS 2601.14310 · Uncertainty-is-Fragile 2407.11282 ·
Adversarial Paraphrasing 2506.07001 · CoPA 2505.15337 ·
Red-teaming Activation Probes 2511.00554
