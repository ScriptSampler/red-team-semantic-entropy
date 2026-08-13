# Does the log N pile-up survive likelihood re-weighting?

Generated 2026-08-13 by `scripts/likelihood_weight_sensitivity.py` (CPU only; no GPU, no model, no attack data).
Cluster assignments: `samples/wk4_full_2000q/entropy.jsonl`. Correctness labels: `samples/wk4_full_2000q/relabeled.jsonl`.
Estimator: Farquhar Eq. (5), p(C_k) proportional to the summed weight of the cluster's members, normalised over the at most N=10 observed clusters.
Weights w_i = exp(l_i) with l_i ~ N(0, s^2) a simulated LENGTH-NORMALISED sequence log-likelihood. 200 reps per spread.

> **This file replaces a phantom citation.** `scripts/rescore_likelihoods.py` twice attributed this result to `scripts/duplication_level_sim.py`, which does no likelihood re-weighting at all. The producing code was never committed; this is the reconstruction.

- `entropy.jsonl` vs `relabeled.jsonl` `entropy_nats` agree to 0.00e+00 over all 2000 questions (same run, two label sets).
- Span oracle keeps 1424 correct, the superseded substring oracle 1440; they disagree on 20 questions.

## Harness check: s = 0 must return the estimator we cached

Setting every weight equal makes Eq. (5) collapse to p(C_k) = n_k / N, so s=0 must
return the cached discrete `entropy_nats` exactly. The script exits non-zero if it
does not, and also requires the at-cap rate, the top-decile rate and the FPR floor
to be identical at s=0 to the ones the cached scores give.

- **fair pool, correct stratum** (n=200): max |H_eq5(s=0) - cached entropy_nats| = **4.44e-16** over n=200
- **full pool, correct (span oracle)** (n=1424): max |H_eq5(s=0) - cached entropy_nats| = **4.44e-16** over n=1424
- **full pool, correct (substring oracle, SUPERSEDED)** (n=1440): max |H_eq5(s=0) - cached entropy_nats| = **4.44e-16** over n=1440

## fair pool, correct stratum (n=200)

*headline: the population `methods.tex` names for detector claims*

| spread s | mean H | at-cap | top decile | **FPR floor** | eps=0.01 | eps=0.05 | eps=0.139 | distinct FPRs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (discrete) | 1.380 | 9.50% | 21.5% | **9.50%** | 9.5% | 9.5% | 21.5% | 28 |
| 1e-06 | 1.380 | 9.50% | 21.5% | **9.50%** | 9.5% | 9.5% | 21.5% | 170 |
| 1e-05 | 1.380 | 9.50% | 21.5% | **9.50%** | 9.5% | 9.5% | 21.5% | 172 |
| 0.0001 | 1.380 | 0.38% | 21.5% | **1.10%** | 9.5% | 9.5% | 21.5% | 178 |
| 0.001 | 1.380 | 0.00% | 21.5% | **0.51%** | 9.5% | 9.5% | 21.5% | 190 |
| 0.01 | 1.380 | 0.00% | 21.5% | **0.50%** | 9.5% | 9.5% | 17.2% | 190 |
| 0.05 | 1.380 | 0.00% | 21.5% | **0.50%** | 9.5% | 9.5% | 15.4% | 190 |
| 0.1 | 1.378 | 0.00% | 21.5% | **0.50%** | 9.4% | 9.5% | 14.6% | 190 |
| 0.2 | 1.371 | 0.00% | 21.5% | **0.50%** | 4.5% | 9.5% | 13.5% | 190 |
| 0.3 | 1.360 | 0.00% | 20.9% | **0.50%** | 2.0% | 8.4% | 12.7% | 190 |
| 0.5 | 1.325 | 0.00% | 15.7% | **0.50%** | 1.0% | 3.8% | 10.4% | 190 |
| 0.7 | 1.275 | 0.00% | 8.9% | **0.50%** | 0.7% | 2.1% | 7.2% | 190 |
| 1 | 1.180 | 0.00% | 2.7% | **0.50%** | 0.6% | 1.4% | 4.3% | 190 |
| 1.5 | 1.005 | 0.00% | 0.3% | **0.50%** | 0.6% | 1.0% | 2.6% | 190 |
| 2 | 0.846 | 0.00% | 0.0% | **0.50%** | 0.6% | 0.9% | 2.0% | 190 |

At s=0 the floor is 9.50% (19/200, Wilson [6.2%, 14.4%]); the smallest floor any score vector with no ties can have is 1/n = 0.50%.
The ceiling atom is already **gone** by s = 0.001: at-cap 0.00%, floor 0.51% = 1/n. It does not decay towards zero as s grows -- it is absent at every s at or above 0.001, so there is no crossover in s to locate.
The atom appears to persist at s <= 0.0001 only because scores are compared at the repo's canonical 1e-9 tie tolerance. log N is a stationary point of the entropy, so a spread s displaces a saturated score by O(s^2); below s ~ 3e-5 that displacement is smaller than the tolerance and the tie is preserved by rounding, not by the estimator. Those rows are numerical resolution, not a finding.
Half-life of the top-decile rate: s = 0.65.
Half-life of the eps=0.05 floor: s = 0.46.
Half-life of the eps=0.139 floor: s = 0.47.

## full pool, correct (span oracle) (n=1424)

*superset of the fair pool; 7x the negatives, same parameter*

| spread s | mean H | at-cap | top decile | **FPR floor** | eps=0.01 | eps=0.05 | eps=0.139 | distinct FPRs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (discrete) | 1.399 | 10.53% | 21.3% | **10.53%** | 10.5% | 10.5% | 21.3% | 34 |
| 1e-06 | 1.399 | 10.53% | 21.3% | **10.53%** | 10.5% | 10.5% | 21.3% | 1118 |
| 1e-05 | 1.399 | 10.53% | 21.3% | **10.53%** | 10.5% | 10.5% | 21.3% | 1185 |
| 0.0001 | 1.399 | 0.37% | 21.3% | **0.35%** | 10.5% | 10.5% | 21.3% | 1203 |
| 0.001 | 1.399 | 0.00% | 21.3% | **0.07%** | 10.5% | 10.5% | 21.3% | 1328 |
| 0.01 | 1.399 | 0.00% | 21.3% | **0.07%** | 10.5% | 10.5% | 17.5% | 1343 |
| 0.05 | 1.398 | 0.00% | 21.3% | **0.07%** | 10.5% | 10.5% | 15.7% | 1343 |
| 0.1 | 1.396 | 0.00% | 21.3% | **0.07%** | 10.4% | 10.5% | 14.8% | 1343 |
| 0.2 | 1.389 | 0.00% | 21.3% | **0.07%** | 3.6% | 10.5% | 13.5% | 1343 |
| 0.3 | 1.378 | 0.00% | 20.7% | **0.07%** | 0.9% | 8.8% | 12.4% | 1343 |
| 0.5 | 1.341 | 0.00% | 16.0% | **0.07%** | 0.2% | 2.8% | 9.8% | 1343 |
| 0.7 | 1.290 | 0.00% | 9.3% | **0.07%** | 0.1% | 1.0% | 5.5% | 1343 |
| 1 | 1.193 | 0.00% | 2.7% | **0.07%** | 0.1% | 0.4% | 2.3% | 1343 |
| 1.5 | 1.014 | 0.00% | 0.3% | **0.07%** | 0.1% | 0.2% | 0.9% | 1343 |
| 2 | 0.852 | 0.00% | 0.0% | **0.07%** | 0.1% | 0.2% | 0.6% | 1343 |

At s=0 the floor is 10.53% (150/1424, Wilson [9.0%, 12.2%]); the smallest floor any score vector with no ties can have is 1/n = 0.07%.
The ceiling atom is already **gone** by s = 0.001: at-cap 0.00%, floor 0.07% = 1/n. It does not decay towards zero as s grows -- it is absent at every s at or above 0.001, so there is no crossover in s to locate.
The atom appears to persist at s <= 0.0001 only because scores are compared at the repo's canonical 1e-9 tie tolerance. log N is a stationary point of the entropy, so a spread s displaces a saturated score by O(s^2); below s ~ 3e-5 that displacement is smaller than the tolerance and the tie is preserved by rounding, not by the estimator. Those rows are numerical resolution, not a finding.
Half-life of the top-decile rate: s = 0.66.
Half-life of the eps=0.05 floor: s = 0.42.
Half-life of the eps=0.139 floor: s = 0.44.

## full pool, correct (substring oracle, SUPERSEDED) (n=1440)

*provenance only -- the stratum the uncommitted original actually ran on*

| spread s | mean H | at-cap | top decile | **FPR floor** | eps=0.01 | eps=0.05 | eps=0.139 | distinct FPRs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (discrete) | 1.400 | 10.49% | 21.0% | **10.49%** | 10.5% | 10.5% | 21.0% | 34 |
| 1e-06 | 1.400 | 10.49% | 21.0% | **10.49%** | 10.5% | 10.5% | 21.0% | 1132 |
| 1e-05 | 1.400 | 10.49% | 21.0% | **10.49%** | 10.5% | 10.5% | 21.0% | 1199 |
| 0.0001 | 1.400 | 0.38% | 21.0% | **0.34%** | 10.5% | 10.5% | 21.0% | 1217 |
| 0.001 | 1.400 | 0.00% | 21.0% | **0.07%** | 10.5% | 10.5% | 21.0% | 1343 |
| 0.01 | 1.400 | 0.00% | 21.0% | **0.07%** | 10.5% | 10.5% | 17.4% | 1358 |
| 0.05 | 1.400 | 0.00% | 21.0% | **0.07%** | 10.5% | 10.5% | 15.5% | 1358 |
| 0.1 | 1.398 | 0.00% | 21.0% | **0.07%** | 10.4% | 10.5% | 14.8% | 1358 |
| 0.2 | 1.391 | 0.00% | 21.0% | **0.07%** | 3.6% | 10.5% | 13.5% | 1358 |
| 0.3 | 1.379 | 0.00% | 20.5% | **0.07%** | 1.0% | 8.8% | 12.4% | 1358 |
| 0.5 | 1.343 | 0.00% | 15.9% | **0.07%** | 0.3% | 2.8% | 9.7% | 1358 |
| 0.7 | 1.291 | 0.00% | 9.3% | **0.07%** | 0.1% | 1.0% | 5.5% | 1358 |
| 1 | 1.194 | 0.00% | 2.8% | **0.07%** | 0.1% | 0.4% | 2.3% | 1358 |
| 1.5 | 1.016 | 0.00% | 0.3% | **0.07%** | 0.1% | 0.2% | 0.9% | 1358 |
| 2 | 0.854 | 0.00% | 0.0% | **0.07%** | 0.1% | 0.2% | 0.6% | 1358 |

At s=0 the floor is 10.49% (151/1440, Wilson [9.0%, 12.2%]); the smallest floor any score vector with no ties can have is 1/n = 0.07%.
The ceiling atom is already **gone** by s = 0.001: at-cap 0.00%, floor 0.07% = 1/n. It does not decay towards zero as s grows -- it is absent at every s at or above 0.001, so there is no crossover in s to locate.
The atom appears to persist at s <= 0.0001 only because scores are compared at the repo's canonical 1e-9 tie tolerance. log N is a stationary point of the entropy, so a spread s displaces a saturated score by O(s^2); below s ~ 3e-5 that displacement is smaller than the tolerance and the tie is preserved by rounding, not by the estimator. Those rows are numerical resolution, not a finding.
Half-life of the top-decile rate: s = 0.66.
Half-life of the eps=0.05 floor: s = 0.42.
Half-life of the eps=0.139 floor: s = 0.44.

## Secondary: intra-cluster correlation of the weights

The i.i.d. draw above is the reconstruction's least defensible modelling choice --
samples in one semantic cluster are often near-duplicate strings, so their
likelihoods are correlated. `rho` is the share of the log-likelihood variance that
is shared within a cluster; rho=1 makes the weights constant inside a cluster.
Population: fair pool, correct stratum (n=200).

| rho | s | at-cap | top decile | **FPR floor** | eps=0.139 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.1 | 0.00% | 21.5% | **0.50%** | 14.6% |
| 0 | 0.3 | 0.00% | 20.9% | **0.50%** | 12.6% |
| 0 | 0.5 | 0.00% | 16.0% | **0.50%** | 10.5% |
| 0 | 1 | 0.00% | 2.7% | **0.50%** | 4.5% |
| 0.5 | 0.1 | 0.00% | 21.5% | **0.50%** | 14.9% |
| 0.5 | 0.3 | 0.00% | 20.6% | **0.50%** | 12.9% |
| 0.5 | 0.5 | 0.00% | 15.6% | **0.50%** | 10.6% |
| 0.5 | 1 | 0.00% | 2.5% | **0.50%** | 4.5% |
| 1 | 0.1 | 0.00% | 21.5% | **0.50%** | 15.2% |
| 1 | 0.3 | 0.00% | 20.4% | **0.50%** | 13.2% |
| 1 | 0.5 | 0.00% | 15.9% | **0.50%** | 10.7% |
| 1 | 1 | 0.00% | 2.8% | **0.50%** | 4.4% |

Correlation does not restore the atom: even at rho=1 the cluster weights are still
real-valued, so p(C_k) proportional to n_k * w_k is still not n_k / N and the
normalised likelihoods are still not exactly equal. It only slows the decay of the
near-cap crowding statistics.

## What this does and does not license the paper to say

1. **The achievable-FPR floor does not transfer, at any spread.** It collapses to
   1/n at s as small as 1e-6. This is the measure-zero argument `methods.tex`
   already makes analytically; the simulation confirms it, it does not bracket it.
   A sentence claiming the crossover is 'inside the plausible range' is not true of
   this statistic -- there is no crossover, there is a discontinuity at s=0.
2. **Near-cap crowding does decay smoothly**, and only for those statistics is a
   bracketing sentence defensible. They are headroom statistics: they say a
   re-weighted score would still be bunched near its maximum, not that an operator
   would face a floor on the false-alarm rates available.
3. **The spread is uncalibrated.** No artifact in this repo records a single
   sequence log-likelihood: `samples.jsonl` stores strings only, and
   `scripts/rescore_likelihoods.py`, the pass that would measure them, has not been
   run. Which s are plausible for a 4-bit Llama-3.1-8B on these answers is an
   assumption, not a measurement, so the location of the crossover in (2) cannot be
   compared to reality from anything in this repository. Any sentence asserting the
   crossover falls inside the plausible range is resting on an unargued prior.

The measurement that settles it is `scripts/rescore_likelihoods.py`, which
teacher-forces the stored samples through the victim model to recover real
per-token log-probabilities and computes all three estimators on identical samples
and identical clusterings.
