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
2. **Three-arm null control** on all targets: `scripts/null_control.py --tag _def`
   (already the 2×2; add the embedding arm — see below). Produces, per clusterer
   {shared NLI, exact-match, embedding-cosine}, the three bands seed < benign < attack.
3. **Report (all already wired):** attack as a *percentile within the full benign
   distribution* (p90 headline, not max-vs-max); three-band ordering; `benign_over_seed`;
   finding-16 sampled-status gate; paired-bootstrap CIs (`auroc_diff_ci`); a
   multiple-comparisons note across the cells/FPR-sweep/cutoff-sweep.

## Decision rule
- attack > benign p90 **and** net(attack − mean benign) CI > 0  →  **(a)**.
- benign floor clears the seed floor **under the EMBEDDING clusterer** (not just NLI or
  exact-match)  →  **(b)**. NLI arm is the confounded permissive bound; exact-match the
  strict bound (over-counts surface form); embedding is the adjudicator.
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
3. **Is e5 even a good oracle for short answers?** Sentence encoders are built for
   sentences; their discrimination on short entity spans is unproven. If the short-answer
   paraphrase-AUROC is mediocre, the embedding arm is not a trustworthy adjudicator and the
   finding-14 conclusion is unsupported. This is the make-or-break check — report it first.
   (Fallback if e5 fails on short spans: gtr-t5-base, or an LLM-judge equivalence oracle on
   the answer samples, which is slower but domain-robust.)

## Still owed before external submission
- Embedding threshold calibration (Youden-J on short-answer + STS-B/PAWS; tool built) and
  the short-answer paraphrase-AUROC that decides whether e5 can adjudicate at all.
- Human / disclosed-LLM-judge equivalence audit of a sample of successful Q' (B5).
- Verify the `%TODO` bib author lists against arXiv (camera-ready).
