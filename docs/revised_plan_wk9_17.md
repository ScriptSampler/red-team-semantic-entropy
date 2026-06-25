# Revised plan, Weeks 9-17 (false-alarm-led reframe)

Supersedes the back half of SE_Project_Execution_Plan.md, following the
literature-positioning verdict in docs/positioning.md (verified 2026-06-25).
The original plan framed the contribution as "attack SE/SRE, show AUROC
degrades." That is the weakest version of our own idea and risks a reviewer
"so what?". The infrastructure already built supports the stronger version at
little extra cost, because the Phase 2 matrix already runs both attack
directions across both detectors and both benchmarks.

## What changes and why

| Axis | Original framing | Revised framing |
| --- | --- | --- |
| Headline | Hide attack degrades SE | **False-alarm**: meaning-preserving paraphrase makes a *correct* answer look hallucinated. Less "of course", genuinely unaddressed. |
| Scope of claim | SE (and maybe SRE) | **Transferability**: one paraphrase fools SE *and* SRE -> attacking the paradigm, not one detector. |
| Stretch | NLI hardening (vague) | **SEP transfer** (input attack moves a hidden-state probe) + a concrete **input-paraphrase-averaging defense**. |
| Risk posture | none stated | Differentiate **CORVUS** (2601.14310) explicitly; cite **REALISTA/SECA** as forked tooling. |

The empirical spine (the wk9 matrix + wk10 assembly) is unchanged; what changes
is emphasis, two added experiments, and the narrative.

## Week 9 (current) — full attack matrix, running

No change to execution: 8 campaigns (Hide/False-alarm x SE/SRE x TriviaQA/SQuAD)
at reduced scale via run_all.sh. Deliverable: per-question outcomes cached.
Add one analysis emphasis: when reporting, separate the False-alarm cells as
the primary result and the Hide cells as the confirming/expected result.

## Week 10 — result matrix + transferability (was: result matrix)

- wk10_matrix.py as-is for the 12+ AUROC numbers.
- ADD: SE<->SRE transferability analysis (scripts/wk_transfer.py). For each
  attacked question, does the paraphrase found against detector A also move
  detector B's score? Report a transfer rate and a transfer-AUROC-degradation.
  This is the "attacking the paradigm" evidence.
- Headline figure: group bars by attack direction, with False-alarm first.

## Week 11 — qualitative analysis + close-out (unchanged in spirit)

- wk11_analysis.py as-is, but lead the write-up with False-alarm successes:
  what kinds of correct-answer questions are most inflatable, and what
  structural trait of the paraphrase does it (added hedging, scope widening,
  reordering). Tie back to SE's linguistic-invariance claim being breakable.

## Week 12 — skeleton + Related Work (Phase 3)

- Related Work is largely pre-built in docs/positioning.md + related_work.bib.
  Four buckets: (1) the detectors we attack (SE, SRE, SEPs); (2) hallucination-
  elicitation attacks on models (SECA, REALISTA) — shared tooling, different
  target; (3) paraphrase-evasion of text-origin detectors (Adversarial
  Paraphrasing, CoPA) — different victim class, one-directional; (4) attacks on
  uncertainty/probes (Uncertainty-is-Fragile, CORVUS) — differentiate threat
  model (input-side, bidirectional, NLI-constrained, sampling-based victim).
- Paper title must avoid collision with "Adversarial Paraphrasing" (2506.07001).

## Week 13 — Methods + Experiments

- Methods: define SE, SRE; the two attack objectives with the sign convention;
  the bidirectional-NLI equivalence gate; the SECA-derived optimizer.
- Experiments: main matrix; transferability; and (if done) the SEP-transfer and
  defense results.

## Week 14 — Intro, Discussion, Limitations, Conclusion

- Intro hook shifts: not "safety mechanisms can be evaded" (expected) but
  "a deployed hallucination detector can be made to fire on correct answers by
  a meaning-preserving rephrasing, and the same rephrasing fools the whole
  family of sampling-based detectors." Lead with false-alarm + transfer.
- Limitations: single model family, English, deberta-large NLI (weaker than the
  v2-xlarge used by SRE/SEP papers; we replicate SE at 0.787 vs 0.828), reduced
  attack budget for compute. State all plainly.

## Weeks 15-17 — stretch goals + polish

Two stretch experiments, in priority order. Either elevates the paper from
"we broke it" to "we broke the paradigm and probed the fix":

1. **SEP transfer (strongest, higher effort).** Train Semantic Entropy Probes
   (Kossen et al. 2406.15927) on Llama hidden states to approximate SE, then
   test whether paraphrases optimized against sampling-SE also move the SEP
   score. A positive result shows the attack reaches a *hidden-state* detector,
   not just the sampled outputs. MUST differentiate CORVUS (model-side LoRA,
   suppression-only, no NLI) head-on. Code scaffolded in src/se/seps.py.
2. **Defense (lower effort, good arms-race shape).** Input-paraphrase-averaging:
   the detector averages SE over K paraphrases of the question before deciding.
   Test whether it blunts Hide/False-alarm and at what cost. Code in
   src/se/defense.py. Note: SRE already does input reformulation, so this
   doubles as "does SRE's own mechanism make it harder to attack?" — which our
   SE-vs-SRE transfer numbers speak to directly.

Polish, self-review x3, external review, arXiv submit on 15 Sep unchanged.

## Non-negotiable, unchanged

15 September arXiv submission. If the stretch goals don't land, the false-alarm
+ transferability matrix is already a complete, differentiated paper on its own.
Drop order under pressure: SEP transfer -> defense -> SQuAD -> never the date.
