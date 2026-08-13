# Fair-pool recompute — B1 shared pool + B2 answer-invariance metric

Detector-independent pool via `campaign_pool` (seed=0, n=80/stratum), success = entropy moved AND feasible AND hallucination status held under Q'. All rates carry bootstrap 95% CIs. This supersedes the pre-B1/B2 wk9 matrix.

> **PRELIMINARY / EXPLORATORY (critic, critique_log entry 10).** Seeded SE is reproducible but each candidate's entropy is a finite N=10 estimate, so the beam max carries an attenuated winner's-curse bias. These numbers are NOT the confirmatory headline until reported NET OF the noise floor (scripts/null_control.py, finding 13). Treat effect sizes as upper-ish bounds.

## Per-cell summaries

**SE / false_alarm** (n=80)

- success (B2 invariance-gated, greedy): 0.550 [0.438, 0.662]
- success (finding 16, sampled status): 0.487 [0.387, 0.600]
- success (entropy-only, pre-B2): 0.600 [0.500, 0.700]
- attrition from B2: 4 of 48 would-be wins (8%)
- of those, answer-flip subcategory (meaning-shift suspect): 4/48 of entropy+feasible (8%)
- sampled fraction-correct under Q' (finding 16): 80%
- equivalence-gate pass rate (per candidate): 65.0% (3058/4703 candidates admitted)
- mean intended entropy move: 0.526 nats

**SE / hide** (n=80)

- success (B2 invariance-gated, greedy): 0.550 [0.438, 0.662]
- success (finding 16, sampled status): 0.588 [0.475, 0.700]
- success (entropy-only, pre-B2): 0.738 [0.637, 0.825]
- attrition from B2: 15 of 59 would-be wins (25%)
- of those, answer-flip subcategory (meaning-shift suspect): 15/59 of entropy+feasible (25%)
- sampled fraction-correct under Q' (finding 16): 24%
- equivalence-gate pass rate (per candidate): 68.4% (2949/4313 candidates admitted)
- mean intended entropy move: 0.659 nats

### sre_false_alarm: (no outcomes)

### sre_hide: (no outcomes)

## AUROC degradation on the fair pool (paired bootstrap 95% CI)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after; degradation = clean AUROC - attacked AUROC (positive = the attack made the detector worse). CI resamples questions jointly so the clean/attacked pairing is preserved.

| detector | n | clean AUROC | attacked AUROC | degradation |
| --- | --- | --- | --- | --- |
| SE | 160 | 0.665 [0.579, 0.748] | 0.126 [0.074, 0.187] | 0.539 [0.458, 0.615] |
| SRE | - | (needs both hide+fa cells) | | |

## Operating-point flips (clean-data threshold sweep)

Hide=positives (model wrong), false-alarm=negatives (model right); clean=entropy_before, attacked=entropy_after. Headline FPR 0.10; 0.05 is noisy at small n (few negatives set the threshold).

### SE
| target FPR | thr | hide flip (flagged→unflagged) | fa flip (unflagged→flagged) | n_neg |
| --- | --- | --- | --- | --- |
| 0.05 | 2.303 | 22/80 (28%) | 34/80 (42%) | 80 |
| 0.10 | 2.178 | 22/80 (28%) | 34/80 (42%) | 80 |
| 0.20 | 2.164 | 33/80 (41%) | 30/80 (38%) | 80 |

answer-flip (NLI-fidelity suspects): hide→correct 15/59, false_alarm→wrong 4/48.

### SRE: operating point needs both cells (missing one).

