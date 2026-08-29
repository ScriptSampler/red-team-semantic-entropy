# Null / noise-floor control (three-band: seed < benign < attack)

K=50 benign feasible paraphrases + 3 same-question seeds per target, on the fair pool (wk9_defb). The attack is placed as a PERCENTILE within the FULL benign-move distribution (not max-vs-max, which is biased toward the attack by its larger candidate budget). Headline success = attack move exceeds the benign 90th percentile. See docs/critique_log.md 13.

## SE / false_alarm  (n=80)

### shared NLI clusterer (the detector's own — confounded/permissive bound)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.015 · benign floor: -0.043 · attack: +0.526
- attack beats benign p90 (headline): 69% [58%, 78%] · beats benign max (budget-biased): 47% [36%, 57%]
- mean attack percentile in benign: 86% · net (attack - mean benign): +0.595 [+0.501, +0.692] nats
- benign clears seed floor (reframe b): 18% [10%, 27%]
- ⚠ the percentile + net-vs-MEAN above are winner's-curse BIASED (B2): attack-max over ~181 candidates vs benign INDIVIDUAL draws; the H0 percentile baseline is ~99.5%, NOT 50% (critique_log 21). Read the budget-matched line as the headline:
- budget-matched paired net (supplementary): attack-max − benign-MAX +0.183 [+0.114, +0.264] nats · sign-test 47% [35%, 57%]. Benign budget K=50 vs attack ~181: K≪budget under-estimates benign-max and INFLATES this net.
- **EXCEEDANCE TEST (CLAIM STATISTIC, randomized ties)**: n_targets=77 (of 80 in cell), observed 30 vs H0-expected 20.4, p=0.9704 (single tie-break draw), effective benign budget n_eff=122.5 ("the attack is worth n_eff random paraphrases").
  - across 101 tie-break realisations: median p=0.9392, range [0.2291, 0.9998], 0% below 0.05. A randomised test must not hinge on one coin flip; if this range straddles the threshold, the data do not settle it.
  - measured actual H0 level of this test at realistic ceiling saturation is <= 0.05 (conservative) for a SINGLE draw; do NOT average tie credit across draws (critique_log 28).
  - diagnostics: strict p=0.0000 · conservative p=1.0000. Disagreement between these indicates ceiling saturation is driving the comparison, not attack superiority (both are disqualified as claim statistics).

### independent exact-match clusterer (strict bound — over-counts surface form)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: +0.026 · benign floor: -0.006 · attack: +0.213
- attack beats benign p90 (headline): 27% [18%, 38%] · beats benign max (budget-biased): 14% [6%, 22%]
- mean attack percentile in benign: 53% · net (attack - mean benign): +0.219 [+0.153, +0.294] nats
- benign clears seed floor (reframe b): 10% [4%, 17%]
- ⚠ the percentile + net-vs-MEAN above are winner's-curse BIASED (B2): attack-max over ~181 candidates vs benign INDIVIDUAL draws; the H0 percentile baseline is ~99.5%, NOT 50% (critique_log 21). Read the budget-matched line as the headline:
- budget-matched paired net (supplementary): attack-max − benign-MAX +0.008 [-0.044, +0.066] nats · sign-test 14% [6%, 22%]. Benign budget K=50 vs attack ~181: K≪budget under-estimates benign-max and INFLATES this net.
- **EXCEEDANCE TEST (CLAIM STATISTIC, randomized ties)**: n_targets=77 (of 80 in cell), observed 383 vs H0-expected 20.4, p=1.0000 (single tie-break draw), effective benign budget n_eff=8.7 ("the attack is worth n_eff random paraphrases").
  - across 101 tie-break realisations: median p=1.0000, range [1.0000, 1.0000], 0% below 0.05. A randomised test must not hinge on one coin flip; if this range straddles the threshold, the data do not settle it.
  - measured actual H0 level of this test at realistic ceiling saturation is <= 0.05 (conservative) for a SINGLE draw; do NOT average tie credit across draws (critique_log 28).
  - diagnostics: strict p=1.0000 · conservative p=1.0000. Disagreement between these indicates ceiling saturation is driving the comparison, not attack superiority (both are disqualified as claim statistics).

### independent LLM-judge clusterer (Qwen/Qwen2.5-7B-Instruct) — finding-14 ADJUDICATOR (hard-neg-validated; positive-recognition ~0.7 -> slightly over-splits)
Three bands (mean intended move, nats) — expect seed < benign < attack:
- seed-noise floor: -0.074 · benign floor: -0.066 · attack: +0.291
- attack beats benign p90 (headline): 38% [26%, 48%] · beats benign max (budget-biased): 22% [13%, 31%]
- mean attack percentile in benign: 52% · net (attack - mean benign): +0.374 [+0.251, +0.507] nats
- benign clears seed floor (reframe b): 34% [23%, 44%]
- ⚠ the percentile + net-vs-MEAN above are winner's-curse BIASED (B2): attack-max over ~181 candidates vs benign INDIVIDUAL draws; the H0 percentile baseline is ~99.5%, NOT 50% (critique_log 21). Read the budget-matched line as the headline:
- budget-matched paired net (supplementary): attack-max − benign-MAX -0.119 [-0.251, +0.016] nats · sign-test 22% [13%, 31%]. Benign budget K=50 vs attack ~181: K≪budget under-estimates benign-max and INFLATES this net.
- **EXCEEDANCE TEST (CLAIM STATISTIC, randomized ties)**: n_targets=77 (of 80 in cell), observed 636 vs H0-expected 20.4, p=1.0000 (single tie-break draw), effective benign budget n_eff=4.8 ("the attack is worth n_eff random paraphrases").
  - across 101 tie-break realisations: median p=1.0000, range [1.0000, 1.0000], 0% below 0.05. A randomised test must not hinge on one coin flip; if this range straddles the threshold, the data do not settle it.
  - measured actual H0 level of this test at realistic ceiling saturation is <= 0.05 (conservative) for a SINGLE draw; do NOT average tie credit across draws (critique_log 28).
  - diagnostics: strict p=1.0000 · conservative p=1.0000. Disagreement between these indicates ceiling saturation is driving the comparison, not attack superiority (both are disqualified as claim statistics).

### Survival ratio (LLM-judge_net / NLI_net) — SUPPLEMENTARY (not headline)
- LLM-judge_net / NLI_net = +0.63 [+0.42, +0.86]. CAVEAT: a ratio of two nets is inflated when the LLM-judge benign floor is low; read the PERCENTILE comparison above as the headline, not this ratio.
- Net is per-target: mean_i(attack_i - mean(benign_i)), which differs from (pooled mean attack - pooled mean benign) when per-target benign counts vary.

Reading the arms (finding 14): NLI is the confounded/permissive bound; exact-match the strict/saturated bound; a VALIDATED LLM-judge (if present) is the ADJUDICATOR. HEADLINE INDICATOR = the attack's PERCENTILE within the benign distribution under each clusterer (beats-benign-p90 + mean-percentile): it is null-controlled AND scale-free, so it is robust to a clusterer's benign-floor LEVEL. The net-ratio below is a SUPPLEMENTARY view only — it is inflated when a clusterer's benign floor is low (e.g. the judge's -0.19), so do NOT read it as the headline. The raw attack-move is NOT null-controlled (winner's-curse biased). Claim reframe (a) IFF the ADJUDICATOR's net CI > 0 at n>=80 (critique_log 15); the NLI-arm alone is necessary but NOT sufficient (it cannot separate a real answer-distribution change from the NLI clusterer partitioning the same answers differently).

