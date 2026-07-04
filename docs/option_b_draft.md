# Option-B draft prose (PROPOSED reframe — accept or discard)

Concrete prose for the protocol-led framing, so you can judge it. Nothing here is
committed to the paper; if you pick Option B I'll fold it in, if not, discard.

## Proposed thesis sentence (abstract / intro topic sentence)
> Claims that sampling-based hallucination detectors are vulnerable to paraphrase
> attacks have been made without the controls needed to support them. We introduce a
> circularity-free, null-controlled protocol for evaluating such attacks, and use it to
> show that the standard evaluation — in which the detector's own NLI model both clusters
> answers and certifies paraphrase equivalence — cannot distinguish a genuine attack from
> an artifact of that shared model, and that the cheap independent oracles one would reach
> for (sentence embedders) fail on exactly the adversarial case. On this basis we argue
> that existing paraphrase-attack claims on semantic entropy are not yet adequately
> supported, and we give the measurement protocol under which they could be.

## Proposed contributions (protocol-led order)
1. **A null-controlled evaluation protocol** for paraphrase attacks on sampling-based
   detectors: score-independent target selection (removing the clean-AUROC≈1.0 circularity),
   an answer-invariance success criterion, a benign-paraphrase noise floor (the attack is
   scored as a *percentile within the benign move distribution*, not a max-vs-max delta),
   and an independent-clusterer robustness check.
2. **A negative/bracketed result with a stated direction:** under the detector's own NLI
   clusterer the optimised attack robustly beats benign paraphrasing (net +0.636), but under
   an independent clusterer the effect is not established; because the clusterer and the
   equivalence gate share one NLI model, the standard setup *cannot* attribute the move to
   the model's answer distribution rather than the clusterer's self-inconsistency.
3. **Evidence that cheap independent oracles cannot close the gap:** sentence embedders
   (e5-base-unsupervised, chosen for provable NLI-training-independence) are near-chance on
   word-preserving, meaning-shifted pairs — the adversarial case — scoring AUROC 0.63 (PAWS)
   and 0.51 (hard short-answer near-misses). Attribution therefore requires a validated
   LLM-judge oracle, which we specify.
4. A reformulation-averaging defense and an analysis of what it does and does not close.

## Proposed Methods paragraph — "Independent-clusterer robustness (attribution)"
> Semantic entropy is defined by a DeBERTa-large-MNLI clustering of the sampled answers,
> and our attack's feasibility gate uses the same model; a measured entropy move under this
> clusterer therefore cannot be attributed to a change in the model's answer distribution
> rather than to the clusterer's own inconsistency. To separate these, we re-cluster the
> identical answer samples under equivalence relations independent of the DeBERTa-MNLI
> supervision: an exact-match relation (canonical-normalised string equality) and an
> embedding-cosine relation using e5-base-unsupervised, the E5 checkpoint trained only by
> contrastive pretraining before any NLI fine-tuning. We report the attack's net effect
> under each as a bracket — the shared-NLI arm as the confounded upper bound, exact-match as
> a strict lower bound — and the survival ratio between them. We find no cheap independent
> oracle adjudicates cleanly: exact-match saturates on short factoid answers, and the
> embedding oracle, though excellent on easy paraphrase pairs (STS-B AUROC 0.99), is
> near-chance on the word-preserving, meaning-shifted pairs the attack produces (hard-negative
> AUROC 0.51), so its clustering cannot be trusted to adjudicate. We therefore specify a
> victim- and NLI-independent LLM-judge equivalence oracle, validated on the same labeled
> pairs, as the instrument required to attribute the effect; absent it, attribution is
> reported as an explicit bracket rather than a claim.

## Why this is a strong paper (not a hedge)
It converts "we couldn't cleanly show the attack is real" into "we show *why* nobody can,
cheaply, and give the protocol that would." That is a reusable contribution the field needs:
it raises the bar for every subsequent paraphrase-attack claim on these detectors. The
attack itself remains a real, reported result (it beats benign paraphrasing under the
detector's own measure) — just correctly scoped.
