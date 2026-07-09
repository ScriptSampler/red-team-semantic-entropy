# Null / noise-floor control (three-band: seed < benign < attack)

> ⚠ MACHINERY-VALIDATION ONLY (n=6 < 80). These numbers are NOT a result — they confirm the pipeline runs and reports correctly on real generations. A confirmatory claim needs n>=80/stratum (critique_log 13). NLI is the confounded/permissive bound; exact-match the strict bound (over-counts surface-form change); the embedding arm ADJUDICATES but MUST be threshold-calibrated first — an uncalibrated cosine cut saturates it (scripts/calibrate_embed_threshold.py). Do NOT lift these numbers into the paper.

K=5 benign feasible paraphrases + 2 same-question seeds per target, on the fair pool (wk9_def). The attack is placed as a PERCENTILE within the FULL benign-move distribution (not max-vs-max, which is biased toward the attack by its larger candidate budget). Headline success = attack move exceeds the benign 90th percentile. See docs/critique_log.md 13.

## SE / false_alarm  (n=6)

### shared NLI clusterer (the detector's own — confounded/permissive bound)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.079 · benign floor: -0.021 · attack: +0.456
- attack beats benign p90 (headline): 80% [40%, 100%] · beats benign max (budget-biased): 60% [20%, 100%]
- mean attack percentile in benign: 80% · net (attack - mean benign): +0.568 [+0.253, +0.884] nats
- benign clears seed floor (reframe b): 20% [0%, 60%]

### independent exact-match clusterer (strict bound — over-counts surface form)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.061 · benign floor: -0.062 · attack: +0.047
- attack beats benign p90 (headline): 40% [0%, 80%] · beats benign max (budget-biased): 20% [0%, 60%]
- mean attack percentile in benign: 56% · net (attack - mean benign): +0.119 [+0.007, +0.261] nats
- benign clears seed floor (reframe b): 20% [0%, 60%]

### independent LLM-judge clusterer (Qwen/Qwen2.5-7B-Instruct) — finding-14 ADJUDICATOR (hard-neg-validated; positive-recognition ~0.7 -> slightly over-splits)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.081 · benign floor: -0.190 · attack: +0.373
- attack beats benign p90 (headline): 80% [40%, 100%] · beats benign max (budget-biased): 60% [20%, 100%]
- mean attack percentile in benign: 76% · net (attack - mean benign): +0.638 [-0.092, +1.189] nats
- benign clears seed floor (reframe b): 20% [0%, 60%]

### Survival ratio (LLM-judge_net / NLI_net) — PRE-REGISTERED headline
- LLM-judge_net / NLI_net = +1.12 [-0.09, +2.53] — fraction of the (confounded) NLI-measured effect that survives under the independent LLM-judge clusterer.
- Rule (critique_log 15): claim reframe (a) IFF the independent-arm net CI > 0 at n>=80; ratio ~1 -> (a) survives; ~0 -> attack was largely an NLI-clusterer artifact (a real finding about SE, not a failure).

Reading the 3 arms (finding 14): NLI is the confounded/permissive UPPER bound; exact-match the strict/saturated LOWER bound; EMBEDDING is the adjudicator. The reported effect is the embedding-arm net move; the NLI-arm beating benign is necessary but NOT sufficient (it cannot separate 'model answer-distribution changed' from 'the NLI clusterer partitioned the same answers differently').

## se_hide: no outcomes yet

