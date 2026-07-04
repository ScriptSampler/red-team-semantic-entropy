# Null / noise-floor control (three-band: seed < benign < attack)

> ⚠ MACHINERY-VALIDATION ONLY (n=6 < 80). These numbers are NOT a result — they confirm the pipeline runs and reports correctly on real generations. A confirmatory claim needs n>=80/stratum (critique_log 13). NLI is the confounded/permissive bound; exact-match the strict bound (over-counts surface-form change); the embedding arm ADJUDICATES but MUST be threshold-calibrated first — an uncalibrated cosine cut saturates it (scripts/calibrate_embed_threshold.py). Do NOT lift these numbers into the paper.

K=8 benign feasible paraphrases + 3 same-question seeds per target, on the fair pool (wk9_fair). The attack is placed as a PERCENTILE within the FULL benign-move distribution (not max-vs-max, which is biased toward the attack by its larger candidate budget). Headline success = attack move exceeds the benign 90th percentile. See docs/critique_log.md 13.

## SE / false_alarm  (n=6)

### shared NLI clusterer (the detector's own — confounded/permissive bound)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.108 · benign floor: +0.005 · attack: +0.534
- attack beats benign p90 (headline): 80% [40%, 100%] · beats benign max (budget-biased): 40% [0%, 80%]
- mean attack percentile in benign: 80% · net (attack - mean benign): +0.636 [+0.239, +1.034] nats
- benign clears seed floor (reframe b): 20% [0%, 60%]

### independent exact-match clusterer (strict bound — over-counts surface form)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.054 · benign floor: -0.056 · attack: +0.070
- attack beats benign p90 (headline): 60% [20%, 100%] · beats benign max (budget-biased): 0% [0%, 0%]
- mean attack percentile in benign: 52% · net (attack - mean benign): +0.140 [-0.004, +0.291] nats
- benign clears seed floor (reframe b): 0% [0%, 0%]

Reading the 3 arms (finding 14): NLI is the confounded/permissive UPPER bound; exact-match the strict/saturated LOWER bound; EMBEDDING is the adjudicator. The reported effect is the embedding-arm net move; the NLI-arm beating benign is necessary but NOT sufficient (it cannot separate 'model answer-distribution changed' from 'the NLI clusterer partitioned the same answers differently').

## se_hide: no outcomes yet

