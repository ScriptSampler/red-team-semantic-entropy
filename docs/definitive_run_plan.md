# Definitive-run plan (the confirmatory SE result)

Consolidates the critic's DoDs (critique_log entries 13–14) into one runnable recipe.
Tonight built and validated all the *machinery*; this is what produces the *claim*.

## Question the run must answer
Distinguish, on the circularity-free fair pool, null-controlled:
- **(a) targeted attack** — the optimised paraphrase moves SE beyond what benign
  rephrasing achieves; vs
- **(b) SE is fragile to *any* meaning-preserving paraphrase** — benign rephrasing
  itself moves SE beyond the seed-noise floor, under an *independent* clusterer; vs
- **negative** — both collapse into the floor (then the null-controlled *protocol* is
  the contribution, which many published attacks lack).

## Steps
1. **Attack matrix at n ≥ 80/stratum** (pool supplies 576 wrong / 1424 right) on the
   fair pool via `campaign_pool` (detector-blind, shared seed). SE fa + hide first;
   SRE (now seeded) and SQuAD as extensions. The harness records `frac_correct_under_q_prime`
   (finding 16). `scripts/recompute_fair.py --n 80 --tag _def`.
2. **Four-arm null control** on all targets, WITH the diagnostic dump:
   `scripts/null_control.py --tag _def --K 8 --n_seeds 3 --judge_model Qwen/Qwen2.5-7B-Instruct --dump_diag results/diag_def.json`
   Produces, per clusterer {shared NLI, exact-match, embedding-cosine, LLM-judge}, the
   three bands seed < benign < attack. The **LLM-judge is the adjudicator** (validated
   0.92 vs e5's 0.51 on the adversarial case — risk #3 below vindicated: e5 is NOT
   trustworthy there). The `--dump_diag` JSON feeds `scripts/diagnose_benign_floor.py`
   to close the benign-floor gate (docs/benign_floor_diagnosis.md).
3. **Report (all already wired):** attack as a *percentile within the full benign
   distribution* (p90 headline, not max-vs-max); three-band ordering; `benign_over_seed`;
   finding-16 sampled-status gate; paired-bootstrap CIs (`auroc_diff_ci`); a
   multiple-comparisons note across the cells/FPR-sweep/cutoff-sweep.

## Decision rule
- attack > benign p90 **and** the ADJUDICATOR's (LLM-judge) net(attack − mean benign)
  CI > 0 at n≥80  →  **(a)** (critique_log 15). Lead with the percentile (scale-free,
  null-controlled); the net carries the benign-floor caveat that
  `diagnose_benign_floor.py` resolves.
- benign floor clears the seed floor **under the LLM-judge clusterer** (not just NLI or
  exact-match)  →  **(b)**. NLI arm is the confounded permissive bound; exact-match the
  strict bound (over-counts surface form); the **validated LLM-judge is the adjudicator**
  (e5 embedding failed the adversarial case — risk #3).
- both collapse  →  negative result; lead with the protocol.

## Embedding clusterer (finding-14 adjudicator) — model choice pending
Core built + tested (`entropy.cluster_samples_embedding`, injected `embed_fn`). Model +
threshold being chosen by the `embedding-arm-design` workflow (must be plausibly
independent of DeBERTa-large-MNLI — NOT all-mpnet, which is MNLI-fine-tuned — with a
*calibrated*, not arbitrary, cosine threshold). Load via `transformers` mean-pooling
(no new dependency). Wire as a 3rd arm in `_both` → `_all_arms`.

## ⚠ Cost reality (needs a decision)
At the current optimiser (~875 s / SE attack: 181 objective calls × N=10), **n=80 ×
2 SE cells ≈ 39 GPU-hours** for the attack matrix alone — a multi-day run, not
overnight. Options, in order of preference:
1. **Cheaper optimiser for the definitive sweep** — fewer iterations / smaller beam
   (e.g. max_iteration 20→10, M 3→2) trades attack strength for n; report the budget.
   Weaker attack under-states (a) but is honest and gets n up.
2. **Smaller n with honest wide CIs** — e.g. n=30–40, report the intervals as-is.
3. **Full n=80 as a multi-day background run** if a targeted-attack claim is the goal.
The null control is cheap (~(K+n_seeds) evals/target) and not the bottleneck — the
*attack* is. Decide the optimiser budget vs n trade-off before committing GPU-days.

## Open risks discovered while running the machinery (2026-07-04)
1. **Uncalibrated embedding threshold saturates.** At the default 0.82, e5 merges all
   N=10 short factoid answer-samples into ONE cluster -> embedding entropy = 0 -> zero
   signal (observed: embed move +0.000 on the first targets). So BOTH independent arms
   are currently saturated (exact-match at high entropy, e5-at-0.82 at zero). **Threshold
   calibration is a HARD prerequisite, not optional** — the embedding arm cannot adjudicate
   until calibrated. Tool built: `scripts/calibrate_embed_threshold.py`.
2. **Calibration domain-mismatch.** STS-B/PAWS are full sentences; the SE answer-samples
   are SHORT factoid spans ("Denver Broncos" vs "the Broncos"). A threshold calibrated on
   sentence pairs may not transfer to short-span cosines. Calibrate on (or at least include)
   SHORT-answer paraphrase pairs matching the clustering domain, and report the
   short-answer paraphrase-AUROC specifically.
3. **Is e5 even a good oracle? Calibration says: NOT for the adversarial case.**
   Measured (2026-07-04, results/embed_calibration.md): e5 paraphrase-AUROC = **0.989 on
   STS-B** (easy semantic pairs) but **0.624 on PAWS** (hard high-lexical-overlap
   non-paraphrases) — near-chance on exactly the case the attack produces (meaning-shifted
   but word-preserving Q'). The Youden-J thresholds are irreconcilable (0.856 vs 0.990), so
   there is no single defensible cut. **e5 is therefore NOT a trustworthy finding-14
   adjudicator for the adversarial setting.** The finding-14 adjudicator is genuinely hard:
   sentence embedders are fooled by lexical overlap, and truly MNLI-independent *semantic*
   oracles are scarce. Options for the definitive run, none free: (a) an **LLM-judge
   equivalence oracle** on the answer samples (domain-robust, slow, and must use a judge
   independent of the victim Llama to avoid circularity); (b) a **different-architecture NLI**
   model (still NLI-trained, so weaker independence, but a second data point); (c) report the
   finding-14 conclusion as **bracketed/uncertain** and lean on the honest statement that no
   cheap independent oracle cleanly adjudicates — which itself is a contribution about how
   hard it is to attribute SE fragility. Note e5 could still cluster the EASY (STS-B-like)
   cases fine; its failure is specifically on the adversarial hard negatives.

## Still owed before external submission
- Embedding threshold calibration (Youden-J on short-answer + STS-B/PAWS; tool built) and
  the short-answer paraphrase-AUROC that decides whether e5 can adjudicate at all. DONE:
  e5 fails the adversarial case (0.51), superseded by the validated LLM-judge (0.92).
- Human equivalence audit of a sample of successful Q' (B5). Harness built
  (`scripts/prepare_equivalence_audit.py`) — run it on the definitive pool to emit the
  fill-in CSV; the human rating + inter-annotator agreement is the remaining owed step.
- Benign-floor diagnosis: tooled (`--dump_diag` + `scripts/diagnose_benign_floor.py`,
  pre-registered in docs/benign_floor_diagnosis.md) — run on the n>=80 dump.
- Bib `%TODO` author lists: DONE 2026-07-10 (5 verified vs arXiv; 3 titles corrected).
  Remaining: confirm the copa/realista venues (EMNLP/ICML) before camera-ready.
