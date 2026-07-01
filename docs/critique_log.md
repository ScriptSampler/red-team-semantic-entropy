# Critique log

Running record of the critic gate (charter: docs/critic_charter.md). Newest last.
Each entry: date, checkpoint, author's claim, critic verdict, resolution.

---

## 0. 2026-06-26 — Founding standard: external review intake

The external review (senior, adversarial-but-fair, top-tier bar) returned
**Reject-with-path**. Its standards are encoded into the charter. Two load-bearing
blockers, both verified by the author against the code:

- **B1 (selection circularity, §2).** `select_examples` picks hide targets at max
  entropy and false-alarm at min, so clean SE AUROC = 1.000 is the selection rule
  reflected back, and degradations (+0.213 SE, +0.567 SRE) are upper bounds.
  Refinement found on verification: SE cells used `select_examples` (extreme
  entropy) while SRE cells used `_label_fresh` (greedy first-N) — different rules,
  so the SE-vs-SRE comparison is doubly confounded.
- **B2 (metric doesn't hold hallucination status, §3).** `run_attack_on_example`
  scores success on entropy delta + NLI gate only; never re-checks the model still
  answers wrong (hide) / right (false-alarm) under Q'. Confirmed in harness.py.

Open blockers carried forward: B1, B2, plus B3 (weak substring oracle, §4),
B4 (no CIs / single dataset / quantization, §5), B5 (operating-point + threshold
motivation + NLI fidelity, §6), B6 (reporting hygiene: wk11 overlap, pinned gen
length, §7). The headline may not be written until B1+B2 are cleared.

---

## 1. 2026-06-26 — Plan gate for B1/B2/B3 fixes. Critic agentId a439a27974fba99b9.

Author submitted a plan (stratified-random sampler; answer-invariance re-check;
alias-aware EM oracle). **Verdict: BLOCK** — right strategy, but underspecified.
Definitions-of-done locked:

- **B3 must land FIRST** (oracle re-labels the pool that B1 strata + B2 re-check
  both consume). Sequence: oracle -> relabel -> sampler -> metric -> recompute.
- **B1:** one sampler, one seed, identical qid set across SE/SRE/SQuAD cells —
  proven by an equality assertion, not discipline. Sampler must not read any
  SE/SRE score (verifiable score-independence). Stratify on correctness AND
  verify per-stratum entropy is representative of the full pool (not skewed to
  extremes); external difficulty proxy optional. Pre-register the wrong/right
  fraction. Clean SE AUROC must drop materially below 1.000 (≈ lit. 0.79 / repo
  0.787); clean AUROC ≈ 1.0 = failed fix. Extreme-entropy selector demoted to a
  labelled maximal-headroom ablation, never headline.
- **B2:** re-check correctness on Q' using the SAME rule as the original
  greedy_correct label and the SAME pinned generation config; success becomes a
  conjunction (entropy moved AND feasible AND status held) that GATES success,
  not a recorded-only flag; store the raw Q' answer so the oracle can be
  re-applied without re-running; report the attrition (fraction of prior
  "successes" the re-check kills) as a finding; count answer-flips separately
  (they also implicate the NLI gate, B5).
- **B3:** equality (not containment) over accepted alias forms via the named
  TriviaQA/SQuAD normalize_answer recipe; explicit answer-extraction policy for
  phrase/multi-token answers (constrain short-answer output OR EM against an
  extracted span), tested on a date/place phrase; recompute pool labels under the
  new oracle; report headline under both old and new oracle side by side (must
  survive); quantify label flips.
- Cross-cutting: add bootstrap CIs to recomputed numbers now (avoids a third
  pass); pin max_new_tokens across all conditions (entangled with B2).

Author assessment (override protocol): verdict accepted as sound. One negotiation
to carry into the re-plan — for the headline "is the detector manipulable on
representative data" claim, correctness-stratified RANDOM sampling with the
per-stratum representativeness check (B1 item 3) is sufficient; the external
difficulty proxy stays optional polish, not a blocker. Will re-submit the revised
plan before implementing.

---

## 2. 2026-07-01 — B3 oracle implementation. Critic verdict: APPROVE-WITH-NITS.

Author submitted scoring.py span-match oracle + tests (9/9). **Span-match accepted
over extraction+EM as a recorded override** (less fragile than a first-sentence
extraction heuristic that could itself correlate with the manipulation; standard
SQuAD "gold span present" notion). Cleared to build relabel + fair-pool clean
AUROC on this oracle. Nits owed WITHIN the relabel checkpoint:
- Article-in-title edge case: `normalize_answer` strips a/an/the, so "The Who" ->
  "who", "A Beautiful Mind" -> "beautiful mind". Add a test; confirm the TriviaQA
  pool has no load-bearing-article gold answers or document the residual.
- Alias-set provenance: confirm `TriviaQAExample.all_acceptable()` surfaces the
  FULL TriviaQA alias set (thin aliases -> under-crediting -> inflated
  hallucination rate).
- `normalise()` caller audit: it now DELETES punctuation (was space-replace);
  confirm no clustering/SE caller depends on the old space behaviour.
- Ship the substring/span/strict oracle-sensitivity table + old-vs-new label-flip
  count + entity-ambiguity fraction (single-token ambiguous golds).

---

## 3. 2026-07-01 — Relabel checkpoint. Critic verdict: APPROVE.

All B3 nits discharged; critic verified AUROC polarity + alias provenance against
the code directly (the two ways it could have been silently wrong; both hold).
**Decisive circularity-free number landed: clean SE AUROC = 0.694 (span oracle) on
the full 2000-question pool, no entropy selection** — vs 1.000 on the attack
matrix's extreme-entropy pool. The 0.306 gap is the selection artifact made
visible (external review B2/§2). Cross-checks: 0.694 ~= Phase-1 greedy-label 0.698;
all-samples convention ~0.787. Oracle-robust (substr 0.697 / span 0.694 / strict
0.561, strict degenerate). 20/2000 label flips. "The finding of the project so far."
Cleared to build B1 on relabeled.jsonl. Four nits carried into the B1 checkpoint:
bootstrap CI on 0.694; assert accepted_forms coverage (fail loud, not silent
single-form); pin the cached-entropy invariant (sampler draws from the same cache,
no re-cluster); report 1.000-vs-0.694 side by side (0.694 is the honest number,
1.000 was never real).

---
