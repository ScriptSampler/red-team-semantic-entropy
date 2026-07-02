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

## 4. 2026-07-01 — B1 checkpoint (v1, select_stratified). Critic verdict: BLOCK.

Score-independence, the demotion of the extreme rule, the CI (0.704 [0.653,0.753]),
the fail-loud accepted_forms guard, and representativeness were all verified correct
on the code. But B1's DEFINING requirement — the cross-detector shared pool — was
only **asserted, not enforced**: `assert_shared_pool` re-called one function with
one seed (proving determinism, never in doubt), and `wk9_scaleup.py` still branched
on detector (`triviaqa+se` → `select_examples`; `triviaqa+sre` → `_label_fresh`),
reopening the founding doubly-confounded comparison. `select_examples`'s `**_`
silently swallowed `seed`. The identity held by accident (all cells fell through to
default seed=0), not by construction. DoD to clear: (1) prove SE-cell ids == SRE-cell
ids at the real call site; (2) forward seed explicitly; (3) grep-confirm wk8/wk9 SRE
no longer route through `_label_fresh`. Numbers stand; re-prove the pool.

## 5. 2026-07-02 — B1 re-submission (v2, campaign_pool). Critic verdict: APPROVE.

BLOCK cleared. The loophole is closed **structurally**: `campaign_pool(dataset, want,
n, *, seed, label_fresh)` has NO detector parameter, so an SE cell and an SRE cell
are the same call for a given (dataset, want, n, seed) — identity by construction.
`assert_detector_blind` enforces (via inspect.signature) that no selector exposes a
detector param. wk9 routes every cell through campaign_pool at module SEED=0; the old
detector selection branch is deleted; `args.detector` survives only in `sre_kwargs`
(scoring, not selection). SQuAD's `label_fresh` is detector-blind + seeded; fails
loud if missing. `select_examples` forwards seed. The critic **accepts the structural
proof in lieu of a behavioral triviaqa print** (cache gone) and notes it is STRONGER:
it holds for every (want,n,seed), test-enforced, not one sampled tuple. wk8 was never
confounded (SE and SRE share load_triviaqa()[:N] in one loop). Tests 51 (+4 B1
enforcement incl. squad SE==SRE pool). Fair AUROC 0.704 [0.653,0.753] stands.
Residual (non-gating): add a one-line behavioral SE==SRE print when the cache is
rebuilt, for the record.

## 6. 2026-07-02 — B2 answer-invariance (harness.py). Critic verdict: APPROVE-WITH-NITS.

The metric now measures the claim. `success = entropy_and_feasible AND status_held`
— a genuine conjunction that GATES success, not a recorded-alongside flag. The
re-check is on the SAME footing as the label (the load-bearing fidelity point,
verified against se_pipeline.py): original `greedy_correct` = `is_acceptable(generate_one(
lm, question, greedy_cfg), example)`; B2 re-check = `is_acceptable(generate_one(lm,
best_query, greedy_cfg), ex)` — same span oracle (B3), same deterministic greedy
decode (`do_sample=False`, no seed dependence), same pinned max_new_tokens=48. No
gen-config mismatch. Attrition recoverable (`entropy_and_feasible` stored beside
`success`); `answer_under_q_prime` persisted for retroactive re-oracling. Re-check
runs only when entropy_and_feasible (cannot manufacture a success). Tests: 6 truth-
table cases incl. the two that matter (hide voided when model becomes correct; false-
alarm voided when model becomes wrong). Two nits carried to the GPU-recompute
checkpoint: (1) report the answer-flip subcategory separately (hide→correct under Q'
is weak evidence the paraphrase shifted meaning → feeds B5/NLI-fidelity); (2) filter
on `entropy_and_feasible` before aggregating `status_held` (default True dilutes the
rate with never-re-checked attacks).

## 7. 2026-07-02 — INFRA finding. **[RETRACTED — FALSE ALARM. See entry 8.]**

**This entry is WRONG.** The cache was never lost and the GPU was never down; I
queried the wrong WSL distro. Retained for the record; superseded by entry 8.

While attempting to re-run fair_pool_check for a fresh behavioral shared-pool print,
found the entire Phase-1 cache **GONE**: `~/.cache/se-research/` does not exist on
Windows or in WSL home. It held `samples.jsonl` + `entropy.jsonl` (the 2000q Phase-1
run), `relabeled.jsonl`, and the wk9 attack-matrix JSONLs. Only the committed
`results/*.md` summaries survive → **0.704, the relabel numbers, and last night's
attack matrix are currently UNREPRODUCIBLE** (charter §6 reproducibility failure).
`DEFAULT_SAMPLES_DIR` still resolves to the standard path (confirmed) — so this is
genuine loss, not a path change. GPU diagnosis: ROCm 6.4 IS installed (/opt/rocm,
rocminfo present) but NO torch binding exists in any env (system python3, .venv
cpu-only 2.12.0, .venv-wsl none) — the GPU torch used last night is gone too.
Consequence: no post-attack numbers can be produced tonight; B1/B2 made the PIPELINE
correct but zero post-attack numbers exist yet — do not conflate "B1/B2 approved"
with "the degradation result is in." Morning priority: (1) diagnose the loss cause
(WSL home reset? disk cleanup?) before spending GPU-hours; (2) decide restore-vs-
regenerate; (3) reinstall torch-ROCm (user's infra decision, not done autonomously).

---

## 8. 2026-07-02 — RETRACTION of entry 7: cache + GPU are FINE (my error).

Entry 7 was a **false alarm caused by testing the wrong WSL distro.** There are two
distros: the DEFAULT `Ubuntu` (26.04, broken ROCm) and the research `Ubuntu-24.04`.
Every "cache gone / no GPU" check I ran used `wsl -e bash` (→ default 26.04) or the
Windows cpu-only `.venv`. In `Ubuntu-24.04` (which my own memory file names as the
research env), verified 2026-07-02:
- `rocminfo` sees the RX 9070 XT (**gfx1201**); `.venv-wsl` → **torch 2.9.1+rocm6.4,
  torch.cuda.is_available() = True**. GPU fully working.
- `~/.cache/se-research/samples/wk4_full_2000q/{samples,entropy,relabeled}.jsonl` =
  **2000 lines each**; manifest confirms the 2000q Llama-3.1-8B run; all four wk9
  attack JSONLs present (n=15/cell, the OLD pre-B1/B2 campaigns).

Nothing was lost. Process failure on my part: I did not heed the memory that says
research runs in `Ubuntu-24.04`, and I escalated a phantom crisis. Corrective
actions: deleted the wrong `project_cache_loss` memory, reinforced the distro gotcha
in `hardware_gpu` memory, corrected OVERNIGHT_2026-07-02.md, and preflight.py now
passes in the correct distro. **Consequence for the work: the GPU recompute (task
19) is UNBLOCKED.** The corrected B1/B2/B4 pipeline can now run the real fair-pool
attack matrix. (Silver lining: the preflight.py cache-check from the false alarm is
a genuine, kept improvement.)

---

## 9. 2026-07-02 — B7+ adversarial audit (6 lenses -> verify -> synth) + remediation.

Ran a multi-agent adversarial audit of the corrected (B1–B6) pipeline+paper to find
the NEXT round of reviewer blockers, each finding adversarially verified. 26 filed,
20 survived, **19 CONFIRMED**. Full list + status in docs/audit_b7_findings.md.

Landed this session (commit a19214c, 68 tests): (1) **SRE winner's-curse BLOCKER** —
SRE was unseeded so the beam search kept lucky Monte-Carlo maxima; fixed by seeding
generate_reformulations + self_reflective_entropy (SRE now deterministic like SE).
Verified SE was already seeded, so the running SE recompute is NOT affected. (2)
`auroc_diff_ci` paired bootstrap for the AUROC-degradation headline (the corrected
recompute previously produced no AUROC) + wired into recompute_fair. (3) artifact
hygiene — wk10 --tag defaults to the fair pool + warns on clean AUROC ~1.0; SUPERSEDED
banners on the pre-B1 result files (clean AUROC 1.000). (4) proposer seeded per
question + docstring corrected. (5) abstract overclaim + Methods multiplicity/seed
notes.

Deferred with a plan (docs/audit_b7_findings.md): finding 16 (greedy-vs-sampled
status) -> post-hoc frac_correct pass; findings 13/14/15/9 (null control, shared-NLI
confound, human equivalence audit, SRE indirect-control threat model) -> GPU
experiments for the definitive resubmit. These shape the definitive run; none
invalidate the running SE recompute. This audit-and-remediation is itself submitted to
the critic for verdict.

---
