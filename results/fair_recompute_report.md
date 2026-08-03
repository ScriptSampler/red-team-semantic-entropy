# Fair-pool recompute — B1 shared pool + B2 answer-invariance metric

Detector-independent pool via `campaign_pool` (seed=0, n=80/stratum), success = entropy moved AND feasible AND hallucination status held under Q'. All rates carry bootstrap 95% CIs. This supersedes the pre-B1/B2 wk9 matrix.

> **PRELIMINARY / EXPLORATORY (critic, critique_log entry 10).** Seeded SE is reproducible but each candidate's entropy is a finite N=10 estimate, so the beam max carries an attenuated winner's-curse bias. These numbers are NOT the confirmatory headline until reported NET OF the noise floor (scripts/null_control.py, finding 13). Treat effect sizes as upper-ish bounds.

## Per-cell summaries

**SE / false_alarm** (n=80)

- success (B2 invariance-gated, greedy): 0.588 [0.475, 0.688]
- success (finding 16, sampled status): 0.475 [0.362, 0.588]
- success (entropy-only, pre-B2): 0.613 [0.512, 0.713]
- attrition from B2: 2 of 49 would-be wins (4%)
- of those, answer-flip subcategory (meaning-shift suspect): 2/49 of entropy+feasible (4%)
- sampled fraction-correct under Q' (finding 16): 81%
- feasible paraphrase rate: 1.000 [1.000, 1.000]
- mean intended entropy move (feasible): 0.524 nats

**SE / hide** (n=17)

- success (B2 invariance-gated, greedy): 0.412 [0.176, 0.647]
- success (finding 16, sampled status): 0.471 [0.235, 0.706]
- success (entropy-only, pre-B2): 0.529 [0.294, 0.765]
- attrition from B2: 2 of 9 would-be wins (22%)
- of those, answer-flip subcategory (meaning-shift suspect): 2/9 of entropy+feasible (22%)
- sampled fraction-correct under Q' (finding 16): 16%
- feasible paraphrase rate: 1.000 [1.000, 1.000]
- mean intended entropy move (feasible): 0.445 nats

### sre_false_alarm: (no outcomes)

### sre_hide: (no outcomes)

## AUROC degradation on the fair pool (paired bootstrap 95% CI)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after; degradation = clean AUROC - attacked AUROC (positive = the attack made the detector worse). CI resamples questions jointly so the clean/attacked pairing is preserved.

| detector | n | clean AUROC | attacked AUROC | degradation |
| --- | --- | --- | --- | --- |
| SE | 97 | 0.579 [0.419, 0.726] | 0.145 [0.057, 0.254] | 0.434 [0.303, 0.568] |
| SRE | - | (needs both hide+fa cells) | | |

## Operating-point flips (clean-data threshold sweep)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after. Headline FPR 0.10; 0.05 is noisy at small n (few negatives set the threshold).

### SE
| target FPR | thr | hide flip (flagged→unflagged) | fa flip (unflagged→flagged) | n_neg |
| --- | --- | --- | --- | --- |
| 0.05 | 2.303 | 3/17 (18%) | 31/80 (39%) | 80 |
| 0.10 | 2.178 | 3/17 (18%) | 31/80 (39%) | 80 |
| 0.20 | 2.164 | 4/17 (24%) | 31/80 (39%) | 80 |

answer-flip (NLI-fidelity suspects): hide→correct 2/9, false_alarm→wrong 2/49.

### SRE: operating point needs both cells (missing one).

