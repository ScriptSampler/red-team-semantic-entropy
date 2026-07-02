# Fair-pool recompute — B1 shared pool + B2 answer-invariance metric

Detector-independent pool via `campaign_pool` (seed=0, n=40/stratum), success = entropy moved AND feasible AND hallucination status held under Q'. All rates carry bootstrap 95% CIs. This supersedes the pre-B1/B2 wk9 matrix.

> **PRELIMINARY / EXPLORATORY (critic, critique_log entry 10).** Seeded SE is reproducible but each candidate's entropy is a finite N=10 estimate, so the beam max carries an attenuated winner's-curse bias. These numbers are NOT the confirmatory headline until reported NET OF the noise floor (scripts/null_control.py, finding 13). Treat effect sizes as upper-ish bounds.

## Per-cell summaries

**SE / false_alarm** (n=6)

- success (B2 invariance-gated): 0.500 [0.167, 0.833]
- success (entropy-only, pre-B2): 0.500 [0.167, 0.833]
- attrition from B2: 0 of 3 would-be wins (0%)
- of those, answer-flip subcategory (meaning-shift suspect): 0/3 of entropy+feasible (0%)
- sampled fraction-correct under Q' (finding 16): n/a (not yet computed)
- feasible paraphrase rate: 1.000 [1.000, 1.000]
- mean intended entropy move (feasible): 0.534 nats

### se_hide: (no outcomes)

### sre_false_alarm: (no outcomes)

### sre_hide: (no outcomes)

## AUROC degradation on the fair pool (paired bootstrap 95% CI)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after; degradation = clean AUROC - attacked AUROC (positive = the attack made the detector worse). CI resamples questions jointly so the clean/attacked pairing is preserved.

| detector | n | clean AUROC | attacked AUROC | degradation |
| --- | --- | --- | --- | --- |
| SE | - | (needs both hide+fa cells) | | |
| SRE | - | (needs both hide+fa cells) | | |

## Operating-point flips (clean-data threshold sweep)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after. Headline FPR 0.10; 0.05 is noisy at small n (few negatives set the threshold).

### SE: operating point needs both cells (missing one).

### SRE: operating point needs both cells (missing one).

