# Null / noise-floor control (three-band: seed < benign < attack)

> ⚠ MACHINERY-VALIDATION ONLY (n=6 < 80). These numbers are NOT a result — they confirm the pipeline runs and reports correctly on real generations. A confirmatory claim needs n>=80/stratum (critique_log 13). The exact-match arm is the STRICT bound (over-counts surface-form change); reframe (b) is adjudicated only under an embedding-cosine clusterer, not yet added. Do NOT lift these numbers into the paper.

K=8 benign feasible paraphrases + 3 same-question seeds per target, on the fair pool (wk9_fair). The attack is placed as a PERCENTILE within the FULL benign-move distribution (not max-vs-max, which is biased toward the attack by its larger candidate budget). Headline success = attack move exceeds the benign 90th percentile. See docs/critique_log.md 13.

## SE / false_alarm  (n=6)

### shared NLI clusterer (the detector's own — confounded/permissive bound)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.053 · benign floor: +0.005 · attack: +0.534
- attack beats benign p90 (headline): 80% [40%, 100%] · beats benign max (budget-biased): 40% [0%, 80%]
- mean attack percentile in benign: 80% · net (attack - mean benign): +0.636 [+0.239, +1.034] nats
- benign clears seed floor (reframe b): 40% [0%, 80%]

### independent exact-match clusterer (strict bound — over-counts surface form)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.041 · benign floor: -0.056 · attack: +0.070
- attack beats benign p90 (headline): 60% [20%, 100%] · beats benign max (budget-biased): 0% [0%, 0%]
- mean attack percentile in benign: 52% · net (attack - mean benign): +0.140 [-0.004, +0.291] nats
- benign clears seed floor (reframe b): 0% [0%, 0%]

### independent embedding-cosine clusterer (intfloat/e5-base-unsupervised @ 0.82) — reframe-(b) ADJUDICATOR
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: +0.000 · benign floor: +0.063 · attack: +0.054
- attack beats benign p90 (headline): 20% [0%, 60%] · beats benign max (budget-biased): 20% [0%, 60%]
- mean attack percentile in benign: 20% · net (attack - mean benign): +0.002 [-0.164, +0.187] nats
- benign clears seed floor (reframe b): 40% [0%, 80%]

Reading the 2x2 (finding 14): a targeted attack needs 'beats benign p90' + net CI > 0. Reframe (b) 'SE fragile to any paraphrase' needs the benign floor to clear the seed floor UNDER THE INDEPENDENT CLUSTERER — if it only clears it under the shared NLI, the 'fragility' was the NLI talking to itself, not a property of the model's answer distribution.

## se_hide: no outcomes yet

