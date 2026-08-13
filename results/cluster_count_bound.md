# The cluster-count bound: the ceiling claim that survives every SE estimator

Generated 2026-08-13 by `scripts/cluster_count_bound.py` (CPU only; no GPU, no model, no re-clustering).

## 0. Why this measurement exists

There are three semantic entropies in the literature and this repo implements one of them:

| # | estimator | cluster weights | bounded by | ours? |
| --- | --- | --- | --- | --- |
| 1 | **Discrete** (sample proportion) | n_c / N, a multiple of 1/N | log N | **yes** -- `se.entropy.discrete_entropy` |
| 2 | **Farquhar Eq. (5)** | summed sequence likelihood, normalised over clusters | log K <= log N | no |
| 3 | **Kuhn Eq. (4)** | mean of per-cluster surprisals, **unnormalised** | **nothing** -- can exceed log N | no |

Farquhar et al. (Nature 2024) define (2) as their headline and (1) as an explicit discrete variant, which they use for all their GPT-4 results. Our lattice statement -- 39 attainable values at N=10, 2 of them in the top tenth of the range (`results/fair_pool_granularity.md`) -- is a property of (1) and **dies under (2)**: once cluster weights are likelihood-derived they are no longer multiples of 1/N and the attainable set is a continuum. The log N **ceiling** survives (1) and (2) and **does not survive (3)**.

What follows is the part that survives (1) AND (2): a necessary condition on the **clustering**, which all three variants share, rather than on the weighting, which is what they disagree about.

## 1. The bound

Let K be the number of distinct semantic clusters observed among the N samples. All three estimators consume the SAME clustering -- none of them changes which samples are merged, only how the merged groups are weighted. For any NORMALISED weighting p over those K clusters, entropy is maximised by the uniform weighting, so

```
    H  <=  log K                                     (any normalised weighting)

    H  >=  0.9 log N   (top tenth of the range [0, log N])
    =>  log K >= 0.9 log N
    =>  K^10  >= N^9            [exact integer form, no float tie-breaking]
    =>  K     >= ceil(N^0.9)
```

At N=10: log 8 = 2.079442 > 0.9 log 10 = 2.072327 > log 7 = 1.945910. So **K >= 8 is necessary** for a top-decile score, and the margin at K=8 is only 7.11e-03 nats.

| N | K_min = ceil(N^0.9) | K_min / N (fraction of samples that must land in distinct clusters) | continuous form N^(-0.1) | slack N - K_min | cap log N |
| --- | --- | --- | --- | --- | --- |
| 5 | 5 | 100.0% | 85.1% | 0 | 1.6094 |
| 10 | 8 | 80.0% | 79.4% | 2 | 2.3026 |
| 20 | 15 | 75.0% | 74.1% | 5 | 2.9957 |
| 40 | 28 | 70.0% | 69.2% | 12 | 3.6889 |
| 100 | 64 | 64.0% | 63.1% | 36 | 4.6052 |
| 1000 | 502 | 50.2% | 50.1% | 498 | 6.9078 |
| 1024 | 512 | 50.0% | 50.0% | 512 | 6.9315 |

**Does raising N relax the constraint or just the cap?** Both, but by wildly different amounts. The cap log N grows without limit. The *constraint* is the required fraction K_min/N ~ N^(-0.1), which decays glacially: 79.4% at N=10, 74.1% at N=20, 63.1% at N=100. Doubling the budget from 10 to 20 buys 5.3 percentage points of relief. To get the requirement down to "half the samples must be in distinct clusters" you need N^(-0.1) = 1/2, i.e. **N = 2^10 = 1024 samples per question**. So a bigger budget mostly raises the ceiling; it barely loosens what a question must look like to approach it.

## 2. Necessary, not sufficient -- how special the weighting has to be

K >= 8 admits a top-decile score; it does not deliver one. At K=8 the admissible region is everything within 7.11e-03 nats of the MAXIMUM entropy of an 8-point distribution -- a sliver around the uniform weighting. Measured as a fraction of the (K-1)-simplex, two ways: crude uniform sampling (Dirichlet(1,...,1) is exactly uniform on the simplex) and a ball-ratio estimator that samples a containing ball around the uniform weighting and rescales by the closed-form ball/simplex volume ratio. Crude sampling cannot resolve K=8 at any feasible draw count; the ball estimator can. 400,000 draws per cell, seed 0.

| K | max attainable H = log K | clears 2.0723? | crude MC | **ball-ratio volume** | quadratic closed form |
| --- | --- | --- | --- | --- | --- |
| 7 | 1.9459 | no | 0 / 400,000 (95% upper bd 7.5e-06) | -- (empty set) | -- |
| 8 | 2.0794 | yes | 0 / 400,000 (95% upper bd 7.5e-06) | **1.958e-06** +/- 1.3e-08 (22,944 hits) | 1.998e-06 |
| 9 | 2.1972 | yes | 2.3552% (9,421/400,000) | **2.375e-02** +/- 2.2e-04 (11,452 hits) | 3.237e-02 |
| 10 | 2.3026 | yes | 15.9303% (63,721/400,000) | **1.601e-01** +/- 2.4e-03 (4,559 hits) | 3.653e-01 |

The ball-ratio estimator is the load-bearing one; the other two columns are there to keep it honest. Where crude MC works (K=9, K=10) the two agree to within Monte-Carlo error, which is what licenses the K=8 figure. The quadratic closed form agrees at K=8, where the region is small enough for the second-order expansion to hold, and over-estimates badly at K=9 and K=10, where the region is large and the expansion is out of its regime -- exactly the expected pattern.

- **K=8**: crude MC unresolvable (0 hits) / ball-ratio 1.958e-06 +/- 1.3e-08 / quadratic 1.998e-06. Containment: ball radius 1.5 x 0.0422 = 0.0633, furthest accepted point at 0.0437 (69% of the radius); widening the ball to 2.5x gives 2.034e-06 +/- 7.9e-08, so nothing is being clipped.
- **K=9**: crude MC 2.3552% / ball-ratio 2.375e-02 +/- 2.2e-04 / quadratic 3.237e-02. Containment: ball radius 1.5 x 0.1666 = 0.2499, furthest accepted point at 0.1892 (76% of the radius); widening the ball to 2.5x gives 2.099e-02 +/- 1.6e-03, so nothing is being clipped.
- **K=10**: crude MC 15.9303% / ball-ratio 1.601e-01 +/- 2.4e-03 / quadratic 3.653e-01. Containment: ball radius 1.5 x 0.2146 = 0.3219, furthest accepted point at 0.2447 (76% of the radius); widening the ball to 2.5x gives 1.568e-01 +/- 2.3e-02, so nothing is being clipped.

So K >= 8 is the honest necessary condition, but it is *barely* attainable: only **2.0e-06** of the K=8 weighting simplex clears the top decile -- about one part in 510,614 -- against 2.4% at K=9, a factor of 12,128. Concretely, an 8-cluster weighting reaches the top decile only if it lies within Euclidean distance 0.042 of the uniform vector (1/8, ..., 1/8), i.e. no cluster weight may sit more than about 0.042 away from 0.125 and most must be far closer than that. The working requirement is K >= 9 under any normalised estimator; K >= 8 is what can be *proved* without committing to one.

## 3. The discrete estimator tightens it to K >= 9 (exactly)

Under (1) the cluster weights are an integer partition of N, so the question is whether any partition of 10 into exactly K parts clears 2.0723:

| K (number of parts) | best partition's H | clears 2.0723? |
| --- | --- | --- |
| 6 | 1.7481 | no |
| 7 | 1.8867 | no |
| 8 | 2.0253 | no |
| 9 | 2.1640 | **yes** |
| 10 | 2.3026 | **yes** |

Binding requirement under the discrete estimator: **K >= 9**. The two top-decile lattice points are exactly the K=9 partition (2,1^8) -> 2.1640 and the K=10 partition (1^10) -> 2.3026. Empirically this is what the cache shows: of the 2000 questions, every top-decile score has K in {9, 10} (counts {9: 261, 10: 295}) and every at-cap score has K in {10} (counts {10: 295}).

**Reporting rule.** K >= 8 is the variant-proof number and is the one the paper should quote. K >= 9 is ours specifically, and quoting it as though it were general would repeat the mistake this document exists to correct.

## 4. Cache verification

K and H are recomputed here from the raw `assignments` array in `~/.cache/se-research/samples/wk4_full_2000q/entropy.jsonl`, not read off the cached summary fields:

- `assignments` -> K recomputed for all 2000 questions: **0 mismatches** against the cached `n_clusters`.
- `assignments` -> discrete H recomputed for all 2000 questions: max |dH| = **0.00e+00** nats against the cached `entropy_nats`.
- every record carries exactly N=10 assignments.

The FA attack stratum is the first 80 ids of the score-independent correct stratum (`_stratum_ids("right", seed=0)`), i.e. **nested inside** the fair pool's correct arm rather than disjoint from it. Checked against the on-disk cells:

| attack cell | size | nesting |
| --- | --- | --- |
| `wk9_defb/triviaqa_se_false_alarm.jsonl` | n=80 | prefix of the correct stratum: **True** |
| `wk9_def/triviaqa_se_false_alarm.jsonl` | n=80 | prefix of the correct stratum: **True** |

## 5. The K distribution, per population

Every row carries its n and a Wilson 95% interval. The distribution is the point, not just the tail rate.

### Fair pool -- correct stratum (n=200)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 11 | 5.5% | 100.0% |
| 2 | 17 | 8.5% | 94.5% |
| 3 | 27 | 13.5% | 86.0% |
| 4 | 18 | 9.0% | 72.5% |
| 5 | 27 | 13.5% | 63.5% |
| 6 | 24 | 12.0% | 50.0% |
| 7 | 18 | 9.0% | 38.0% |
| 8 | 15 | 7.5% | 29.0% |
| 9 | 24 | 12.0% | 21.5% |
| 10 | 19 | 9.5% | 9.5% |

- mean K = 5.64, median = 5.5, IQR = [3.0, 8.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 58/200 = 29.0% [23.2%, 35.6%]
- K >= 9 (top decile possible under the DISCRETE estimator): 43/200 = 21.5% [16.4%, 27.7%]
- K = 10 (at-cap possible under the discrete estimator): 19/200 = 9.5% [6.2%, 14.4%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 142/200 = 71.0% [64.4%, 76.8%]
- K <= 3 (bottom of the clustering range): 55/200 = 27.5% [21.8%, 34.1%]
- observed discrete top-decile rate: 43/200 = 21.5% [16.4%, 27.7%]; at-cap rate: 19/200 = 9.5% [6.2%, 14.4%]

### Fair pool -- hallucinating stratum (n=200)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 2 | 1.0% | 100.0% |
| 2 | 3 | 1.5% | 99.0% |
| 3 | 5 | 2.5% | 97.5% |
| 4 | 14 | 7.0% | 95.0% |
| 5 | 17 | 8.5% | 88.0% |
| 6 | 20 | 10.0% | 79.5% |
| 7 | 24 | 12.0% | 69.5% |
| 8 | 26 | 13.0% | 57.5% |
| 9 | 34 | 17.0% | 44.5% |
| 10 | 55 | 27.5% | 27.5% |

- mean K = 7.58, median = 8.0, IQR = [6.0, 10.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 115/200 = 57.5% [50.6%, 64.1%]
- K >= 9 (top decile possible under the DISCRETE estimator): 89/200 = 44.5% [37.8%, 51.4%]
- K = 10 (at-cap possible under the discrete estimator): 55/200 = 27.5% [21.8%, 34.1%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 85/200 = 42.5% [35.9%, 49.4%]
- K <= 3 (bottom of the clustering range): 10/200 = 5.0% [2.7%, 9.0%]
- observed discrete top-decile rate: 89/200 = 44.5% [37.8%, 51.4%]; at-cap rate: 55/200 = 27.5% [21.8%, 34.1%]

### Fair pool -- both strata pooled (n=400)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 13 | 3.2% | 100.0% |
| 2 | 20 | 5.0% | 96.8% |
| 3 | 32 | 8.0% | 91.8% |
| 4 | 32 | 8.0% | 83.8% |
| 5 | 44 | 11.0% | 75.8% |
| 6 | 44 | 11.0% | 64.8% |
| 7 | 42 | 10.5% | 53.8% |
| 8 | 41 | 10.2% | 43.2% |
| 9 | 58 | 14.5% | 33.0% |
| 10 | 74 | 18.5% | 18.5% |

- mean K = 6.61, median = 7.0, IQR = [5.0, 9.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 173/400 = 43.2% [38.5%, 48.1%]
- K >= 9 (top decile possible under the DISCRETE estimator): 132/400 = 33.0% [28.6%, 37.8%]
- K = 10 (at-cap possible under the discrete estimator): 74/400 = 18.5% [15.0%, 22.6%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 227/400 = 56.8% [51.9%, 61.5%]
- K <= 3 (bottom of the clustering range): 65/400 = 16.2% [13.0%, 20.2%]
- observed discrete top-decile rate: 132/400 = 33.0% [28.6%, 37.8%]; at-cap rate: 74/400 = 18.5% [15.0%, 22.6%]

### FA attack stratum (n=80, nested in fair-correct) (n=80)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 4 | 5.0% | 100.0% |
| 2 | 6 | 7.5% | 95.0% |
| 3 | 7 | 8.8% | 87.5% |
| 4 | 5 | 6.2% | 78.8% |
| 5 | 11 | 13.8% | 72.5% |
| 6 | 15 | 18.8% | 58.8% |
| 7 | 6 | 7.5% | 40.0% |
| 8 | 5 | 6.2% | 32.5% |
| 9 | 13 | 16.2% | 26.2% |
| 10 | 8 | 10.0% | 10.0% |

- mean K = 6.01, median = 6.0, IQR = [4.0, 9.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 26/80 = 32.5% [23.2%, 43.4%]
- K >= 9 (top decile possible under the DISCRETE estimator): 21/80 = 26.2% [17.9%, 36.8%]
- K = 10 (at-cap possible under the discrete estimator): 8/80 = 10.0% [5.2%, 18.5%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 54/80 = 67.5% [56.6%, 76.8%]
- K <= 3 (bottom of the clustering range): 17/80 = 21.2% [13.7%, 31.4%]
- observed discrete top-decile rate: 21/80 = 26.2% [17.9%, 36.8%]; at-cap rate: 8/80 = 10.0% [5.2%, 18.5%]

### Full labelled pool -- correct (n=1424)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 82 | 5.8% | 100.0% |
| 2 | 143 | 10.0% | 94.2% |
| 3 | 130 | 9.1% | 84.2% |
| 4 | 152 | 10.7% | 75.1% |
| 5 | 165 | 11.6% | 64.4% |
| 6 | 175 | 12.3% | 52.8% |
| 7 | 146 | 10.3% | 40.5% |
| 8 | 128 | 9.0% | 30.3% |
| 9 | 153 | 10.7% | 21.3% |
| 10 | 150 | 10.5% | 10.5% |

- mean K = 5.73, median = 6.0, IQR = [4.0, 8.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 431/1424 = 30.3% [27.9%, 32.7%]
- K >= 9 (top decile possible under the DISCRETE estimator): 303/1424 = 21.3% [19.2%, 23.5%]
- K = 10 (at-cap possible under the discrete estimator): 150/1424 = 10.5% [9.0%, 12.2%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 993/1424 = 69.7% [67.3%, 72.1%]
- K <= 3 (bottom of the clustering range): 355/1424 = 24.9% [22.8%, 27.2%]
- observed discrete top-decile rate: 303/1424 = 21.3% [19.2%, 23.5%]; at-cap rate: 150/1424 = 10.5% [9.0%, 12.2%]

### Full labelled pool -- hallucinating (n=576)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 2 | 0.3% | 100.0% |
| 2 | 9 | 1.6% | 99.7% |
| 3 | 15 | 2.6% | 98.1% |
| 4 | 42 | 7.3% | 95.5% |
| 5 | 49 | 8.5% | 88.2% |
| 6 | 59 | 10.2% | 79.7% |
| 7 | 64 | 11.1% | 69.4% |
| 8 | 83 | 14.4% | 58.3% |
| 9 | 108 | 18.8% | 43.9% |
| 10 | 145 | 25.2% | 25.2% |

- mean K = 7.58, median = 8.0, IQR = [6.0, 10.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 336/576 = 58.3% [54.3%, 62.3%]
- K >= 9 (top decile possible under the DISCRETE estimator): 253/576 = 43.9% [39.9%, 48.0%]
- K = 10 (at-cap possible under the discrete estimator): 145/576 = 25.2% [21.8%, 28.9%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 240/576 = 41.7% [37.7%, 45.7%]
- K <= 3 (bottom of the clustering range): 26/576 = 4.5% [3.1%, 6.5%]
- observed discrete top-decile rate: 253/576 = 43.9% [39.9%, 48.0%]; at-cap rate: 145/576 = 25.2% [21.8%, 28.9%]

### Full labelled pool -- natural prevalence (n=2000)

| K | count | share | share with K' >= K |
| --- | --- | --- | --- |
| 1 | 84 | 4.2% | 100.0% |
| 2 | 152 | 7.6% | 95.8% |
| 3 | 145 | 7.2% | 88.2% |
| 4 | 194 | 9.7% | 81.0% |
| 5 | 214 | 10.7% | 71.2% |
| 6 | 234 | 11.7% | 60.5% |
| 7 | 210 | 10.5% | 48.9% |
| 8 | 211 | 10.5% | 38.3% |
| 9 | 261 | 13.1% | 27.8% |
| 10 | 295 | 14.8% | 14.7% |

- mean K = 6.26, median = 6.0, IQR = [4.0, 9.0]
- **K >= 8** (top decile possible under ANY normalised weighting): 767/2000 = 38.4% [36.2%, 40.5%]
- K >= 9 (top decile possible under the DISCRETE estimator): 556/2000 = 27.8% [25.9%, 29.8%]
- K = 10 (at-cap possible under the discrete estimator): 295/2000 = 14.8% [13.3%, 16.4%]
- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: 1233/2000 = 61.7% [59.5%, 63.8%]
- K <= 3 (bottom of the clustering range): 381/2000 = 19.1% [17.4%, 20.8%]
- observed discrete top-decile rate: 556/2000 = 27.8% [25.9%, 29.8%]; at-cap rate: 295/2000 = 14.8% [13.3%, 16.4%]

## 6. The contrast that carries the finding

| population pair | K >= 8, correct | K >= 8, hallucinating | difference (Newcombe 95%) |
| --- | --- | --- | --- |
| fair pool (200 + 200) | 58/200 = 29.0% [23.2%, 35.6%] | 115/200 = 57.5% [50.6%, 64.1%] | +28.5% [+18.9%, +37.4%] |
| full labelled pool (1424 + 576) | 431/1424 = 30.3% [27.9%, 32.7%] | 336/576 = 58.3% [54.3%, 62.3%] | +28.1% [+23.3%, +32.7%] |

## 7. Do the circulating 30.3% / 59.1% figures hold?

They are close but were computed against the WRONG label column. `entropy.jsonl` carries the pre-relabel `greedy_correct`; the paper's rule uses the B3 span-oracle relabel in `relabeled.jsonl`, and the two disagree on 20 of 2000 questions. Corrected figures first:

| label column | correct stratum, K >= 8 | hallucinating stratum, K >= 8 |
| --- | --- | --- |
| relabeled.jsonl (span oracle, the paper's rule) | 431/1424 = 30.3% [27.9%, 32.7%] | 336/576 = 58.3% [54.3%, 62.3%] |
| entropy.jsonl (pre-relabel label) | 436/1440 = 30.3% [28.0%, 32.7%] | 331/560 = 59.1% [55.0%, 63.1%] |
| relabeled.jsonl `greedy_correct_substr` | 437/1440 = 30.3% [28.0%, 32.8%] | 330/560 = 58.9% [54.8%, 62.9%] |

The preliminary 30.3% / 59.1% reproduces exactly under `entropy.jsonl`'s label column. Under the span-oracle relabel the figures are **30.3% and 58.3%** -- the correct-stratum number is unchanged to the quoted precision and the hallucinating-stratum number moves by 0.8 points. The qualitative claim is unaffected; **quote the span-oracle numbers.**

## 8. Proposed paper sentence

> Because every semantic-entropy variant scores the same clustering and differs only in how clusters are weighted, and because any normalised weighting over K clusters satisfies H <= log K, a score in the top tenth of the range [0, log N] requires K >= ceil(N^0.9) -- at N = 10, K >= 8, since log 8 = 2.079 exceeds 0.9 log 10 = 2.072 while log 7 = 1.946 does not. On the score-independent fair pool this condition is met by only 58/200 = 29.0% [23.2%, 35.6%] of correct-stratum questions against 115/200 = 57.5% [50.6%, 64.1%] of hallucinating ones, so for the majority of the correct stratum the top decile of the scale is unreachable under any weighting scheme, not merely unreached under ours. Raising N lifts the cap without loosening the condition: the required fraction of samples in distinct clusters falls only as N^(-0.1), from 79% at N = 10 to 74% at N = 20.

(Scope: the bound follows from the log N ceiling, so it applies to the discrete estimator and to Farquhar Eq. (5). Kuhn et al.'s Eq. (4) is an unnormalised mean surprisal with no log N ceiling and is therefore outside its scope -- state that rather than let the reader assume otherwise.)
