# B7+ adversarial audit — findings and remediation (2026-07-02)

Six-lens adversarial audit of the corrected (B1–B6) pipeline + paper, each finding
adversarially verified. 26 filed, 20 survived, 19 CONFIRMED. This is the "next round"
a top-tier reviewer would raise. Status: **FIXED** (this session), **POST-HOC**
(cheap augmentation of results), **EXPERIMENT** (needs a GPU run), or **PROSE**.

## Fixed this session (commit a19214c)

- **[BLOCKER] SRE winner's curse + nondeterminism** (optimizer.py/sre.py). SRE was
  fully unseeded, so the objective was one noisy Monte-Carlo draw and the beam search
  kept the luckiest candidate without re-evaluation → inflated SRE success. FIX: seed
  `generate_reformulations` + `self_reflective_entropy`; callers pass seed=0. SRE is
  now deterministic like SE (no lucky-max, reproducible). **Correction (critic, entry
  10):** SE seeding makes `SE(query)` *reproducible* but NOT *noise-free* — the beam
  search still takes the max over ~180 finite-N=10 SE estimates, so seeded SE carries
  an ATTENUATED (not zero) winner's-curse bias in the attack-favoring direction. The
  running SE recompute is therefore valid only as an **exploratory/preliminary** number,
  not the confirmatory headline; see finding 13.
- **[major] No CI on AUROC degradation / no paired-diff CI** (stats.py). FIX:
  `auroc_diff_ci` — paired bootstrap resampling questions jointly for clean/attacked/
  degradation CIs. Wired into `recompute_fair.py` (which previously produced no AUROC).
- **[major] Stale pre-B1 artifacts are the only committed numbers** (results/, wk10).
  FIX: `wk10_matrix.py --tag` defaults to the fair pool + warns on clean AUROC ~1.0;
  SUPERSEDED banners prepended to the pre-B1 result md files.
- **[major] Proposer unseeded + greedy-not-temperature** (proposer.py). FIX: seedable
  RNG (`seed_proposer`, seeded per question in the harness); docstring corrected to
  admit greedy + template-randomised decoding.
- **[minor] Abstract overclaim "answer unchanged"** → "hallucination status unchanged".
- **[minor] Multiplicity / SE-SRE seed asymmetry** → Methods notes fixed seeds
  (like-for-like) and exploratory-vs-confirmatory framing.

## Post-hoc (augment the running run's outcomes; no restart)

- **[major, finding 16] status_held uses greedy decode but the detector clusters
  T=1.0 samples.** A hide can score "still wrong" (greedy) while the sampled
  distribution shifted toward correct — the entropy drop then isn't a hidden
  hallucination. PLAN: a cheap GPU pass over completed outcomes recording
  `frac_correct_under_q_prime` over the N detector samples; report greedy-status and
  sampled-status side by side. **Correction (critic):** this affects the FALSE-ALARM
  headline too, not just hide — status "still correct" (greedy) can disagree with a
  T=1.0 sampled set that shifted toward wrong, making the "false alarm" partly a true
  alarm. Report both statuses for false-alarm as well.

## Experiments (need a GPU run)

- **[BLOCKER, finding 13 — BLOCKS THE SE HEADLINE, not just the definitive run]** No
  null/noise control. Seeded SE is reproducible but the beam max over ~180 finite-N=10
  estimates is upward-biased, so a chunk of "success" may be max-over-noise rather than
  the attack. **The confirmatory SE headline may not be written until this lands.**
  NEED: for each target, a noise floor = re-score the original AND K random NLI-passing
  paraphrases (NOT chosen by the optimizer) under k>=3 seeds; report attack success /
  degradation **net of** that floor, with the paired-diff CI, on the fair pool. If the
  effect survives the floor the headline stands; if it collapses into the floor, that
  is the finding. Tooling: scripts/null_control.py (this session).
- **[major, finding 14] Shared NLI model for clustering AND the feasibility gate.**
  "AUROC degradation" partly measures one NLI model's self-inconsistency. NEED: a
  robustness check with an independent clusterer (different NLI / embedding / exact
  match) while keeping the attack gate; report whether degradation survives.
- **[major, finding 15] Answer-flip is only a lower bound on gate leakage.** NEED: a
  human (or disclosed strong-LLM-judge) equivalence audit of a random sample of
  "successful" Q' vs original, with a CI; reframe answer-flip as a lower bound.
- **[major, finding 9] SRE re-paraphrases Q', diluting the attacker's phrasing.** The
  SRE threat model is under-specified. DECIDE: attacker controls the reformulation set
  (pass Q' variants via `reformulations=`) OR freeze reformulations per query; match
  code + Methods. (SRE-specific; SRE not run tonight.)

## Prose / hygiene (quick, non-blocking)

- **[minor, finding 12] SQuAD label_fresh can silently return < n** — add an assert/
  floor + log the realised n and stratum hit-rate.
- **[minor, finding 3] Multiplicity** — apply Holm/BH to the primary comparison family
  when the numbers land; already noted in Methods as exploratory-vs-confirmatory.
- **[minor, finding 20] Bibliography** — resolve `%TODO` author/title placeholders and
  the `author={others}`; cite REALISTA/CORVUS as arXiv until acceptance is verifiable.

## Overall
The B1–B6 corrections hold. The B7+ set is dominated by **stochastic-control** issues
(SRE seeding — fixed; null control — experiment) and **construct-validity** depth
(shared-NLI confound, human equivalence audit) that a top venue will demand before the
"detectors are breakable" claim is airtight. None invalidate the running SE recompute
(SE is seeded); they shape the definitive run and the resubmission.
