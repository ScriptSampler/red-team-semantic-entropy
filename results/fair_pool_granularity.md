# Granularity of semantic entropy on the SCORE-INDEPENDENT FAIR POOL

Generated 2026-08-13 by `scripts/fair_pool_granularity.py` (CPU only; no GPU, no model).

**Population.** The *fair pool*: the score-independent stratified-random sample
of **200 correct + 200 hallucinating** TriviaQA targets
(`select_stratified(want, 200, seed=0)`) -- the same ids on which
`results/fair_pool_report.md` reports clean SE AUROC **0.704 [0.653, 0.753]**.
Scores are the CLEAN (unattacked) `entropy_nats` of the Week-4 span-oracle cache
`wk4_full_2000q/relabeled.jsonl`. Every proportion below carries its n, its
population, and a Wilson 95% interval.

Estimator: semantic entropy over **N=10** samples; attainable maximum
**ln(10) = 2.3026 nats**; "top tenth of the RANGE" means
score >= 0.9 x ln(10) = **2.0723 nats** (a fixed cut on the scale,
not a sample quantile).

## 0. The attacked subset is NESTED inside the fair pool (verified)

`_stratum_ids` returns a seed-shuffled id list and `select_stratified` takes
`[:n]`, so an attacked cell of size n is the first n ids of the fair pool's
stratum. These are not two populations; the smaller is a prefix of the larger.
Asserted here against the on-disk attack cells, together with the check that the
`entropy_before` they recorded is bit-identical to the `entropy_nats` used here:

| attack cell | size | stratum | nesting | clean-score agreement |
| --- | --- | --- | --- | --- |
| `wk9_defb/triviaqa_se_false_alarm.jsonl` | n=80 | right | prefix: **True**, subset: **True** | max |Δclean| = 0 |
| `wk9_defb/triviaqa_se_hide.jsonl` | n=43 | wrong | prefix: **True**, subset: **True** | max |Δclean| = 0 |
| `wk9_def/triviaqa_se_false_alarm.jsonl` | n=80 | right | prefix: **True**, subset: **True** | max |Δclean| = 0 |
| `wk9_def/triviaqa_se_hide.jsonl` | n=55 | wrong | prefix: **True**, subset: **True** | max |Δclean| = 0 |

(Hide-cell sizes are whatever the still-running multi-day chain had written when
this ran; the prefix property holds at any size.) `load_triviaqa` drops **0/200** correct and **0/200** hallucinating ids, so the ids scored here are exactly `select_stratified(want, 200, seed=0)`.

Consequence: the fair-pool numbers below do not *contradict* the attacked-subset
numbers -- they are the same measurement carried out on a superset that was
chosen without reference to any score.

## 1. The attainable lattice at N=10 (the honest denominator)

Semantic entropy here is the Shannon entropy of a cluster-size distribution over
N=10 samples, and a cluster-size distribution over 10 samples IS an
integer partition of 10. Enumerating all p(10) = 42 partitions and
taking each one's entropy gives **39 distinct attainable values** (42 partitions,
3 entropy coincidences). No dataset, no model: this is a property of the
estimator and the sample budget.

- attainable values in the top tenth of the range (>= 2.0723): **2 of 39** -- 2.1640, 2.3026
- smallest gap between adjacent attainable values: 2.90e-03 nats
- for reference, N=20: **455** attainable values, **7** in the top tenth of [0, ln 20]

**This is the sharp fact.** Doubling the sample budget to N=20 multiplies the
lattice by ~12x overall but only takes the top decile from 2 points to
7. The coarseness at the top of the scale is not a small-sample accident that
more targets would fix; it is where the lattice is sparsest.

## 2. Distinct realised values on the fair pool

Rounding tolerance: values are treated as equal when they agree to **9 decimal
places** (1e-9 nats). Raw float64 comparison inflates the count with ~1e-16
accumulation noise from the entropy sum. The count is stable across 3-12 dp:

| population | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | raw float64 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fair pool, n=400 | 31 | 31 | 31 | 31 | 31 | 31 | 31 | 31 | 31 | 31 | 42 |
| correct stratum, n=200 | 28 | 28 | 28 | 28 | 28 | 28 | 28 | 28 | 28 | 28 | 36 |
| hallucinating stratum, n=200 | 26 | 26 | 26 | 26 | 26 | 26 | 26 | 26 | 26 | 26 | 32 |
| _full labelled pool, n=2000 (suppl.)_ | 35 | 35 | 35 | 35 | 35 | 35 | 35 | 35 | 35 | 35 | 52 |

(The raw-float64 column is the artefact being guarded against: it reports 42
"distinct" values on the pooled n=400 -- 11 spurious extras, all of them 1e-16
neighbours of a value already counted. That 42 coinciding with p(10) = 42 above is
coincidence, not meaning. No attainable value can be missed by
9-dp rounding: the smallest gap in the lattice is 2.90e-03 nats.)

| population | n | distinct realised values | of 39 attainable |
| --- | --- | --- | --- |
| fair pool (correct + hallucinating) | 400 | **31** | 31/39 = 79% |
| fair pool, correct stratum | 200 | **28** | 28/39 = 72% |
| fair pool, hallucinating stratum | 200 | **26** | 26/39 = 67% |
| _full labelled pool (supplementary)_ | 2000 | **35** | 35/39 = 90% |

Every realised value is an attainable one (asserted). Attainable-but-unrealised
at n=400: **8 of 39** -- 0.6730, 0.6931, 0.9503, 1.0297, 1.3138, 1.3322, 1.3662, 1.5571.

Chao1 richness estimate from the n=400 sample: **35.0** distinct values (singletons f1=4, doubletons f2=2; f2 is
small so this point estimate is unstable -- read it as directional only),
against 39 attainable. So the realised count has not converged at n=400 either --
consistent with the rarefaction curve in section 4, and further evidence that a
distinct-value count is a statement about the sample, not about the estimator.

That extrapolation is checkable here, and it checks out: the supplementary full
labelled pool realises **35** distinct values at n=2000 -- the Chao1 figure the
n=400 fair pool predicted. Even at n=2000 the count is 35/39 of the lattice, so it
is still short of saturation. There is no n at which "the number of distinct values
semantic entropy produces" stops depending on n; only the lattice size does not.

## 3. Crowding at the top of the scale

"At the ceiling" = score within 1e-9 of ln(10) = 2.3026. "Top tenth of the
range" = score >= 2.0723. Wilson 95% intervals.

| population | n | at the ceiling | in the top tenth of the range |
| --- | --- | --- | --- |
| fair pool (correct + hallucinating) | 400 | 74/400 = 18.5% [15.0%, 22.6%] | 132/400 = 33.0% [28.6%, 37.8%] |
| fair pool, correct stratum | 200 | 19/200 = 9.5% [6.2%, 14.4%] | 43/200 = 21.5% [16.4%, 27.7%] |
| fair pool, hallucinating stratum | 200 | 55/200 = 27.5% [21.8%, 34.1%] | 89/200 = 44.5% [37.8%, 51.4%] |
| _full labelled pool, natural prevalence (suppl.)_ | 2000 | 295/2000 = 14.8% [13.3%, 16.4%] | 556/2000 = 27.8% [25.9%, 29.8%] |
| _full pool, correct (suppl.)_ | 1424 | 150/1424 = 10.5% [9.0%, 12.2%] | 303/1424 = 21.3% [19.2%, 23.5%] |
| _full pool, hallucinating (suppl.)_ | 576 | 145/576 = 25.2% [21.8%, 28.9%] | 253/576 = 43.9% [39.9%, 48.0%] |

Because only two attainable values lie in the top tenth of the range, the second
column decomposes exactly:

| population | n | at 2.1640 | at 2.3026 |
| --- | --- | --- | --- |
| fair pool (correct + hallucinating) | 400 | 58/400 = 14.5% [11.4%, 18.3%] | 74/400 = 18.5% [15.0%, 22.6%] |
| fair pool, correct stratum | 200 | 24/200 = 12.0% [8.2%, 17.2%] | 19/200 = 9.5% [6.2%, 14.4%] |
| fair pool, hallucinating stratum | 200 | 34/200 = 17.0% [12.4%, 22.8%] | 55/200 = 27.5% [21.8%, 34.1%] |
| _full labelled pool, natural prevalence (suppl.)_ | 2000 | 261/2000 = 13.1% [11.6%, 14.6%] | 295/2000 = 14.8% [13.3%, 16.4%] |
| _full pool, correct (suppl.)_ | 1424 | 153/1424 = 10.7% [9.2%, 12.5%] | 150/1424 = 10.5% [9.0%, 12.2%] |
| _full pool, hallucinating (suppl.)_ | 576 | 108/576 = 18.8% [15.8%, 22.1%] | 145/576 = 25.2% [21.8%, 28.9%] |

**The finding, restated on the correct population.** 132 of the 400 fair-pool
targets (33%) sit in the top tenth of the scale, a region in which the
estimator has exactly **2 expressible values**. A third of the population is
resolved to a 2-point scale. That is the granularity claim, and it does not
depend on the attack, on the optimiser, or on which targets were attacked.

**Prevalence caveat -- read the pooled row with care.** The fair pool is 50/50 by
construction; the model's actual error rate on this split is 28.8% (576/2000).
Since the hallucinating stratum is the crowded one, ANY pooled crowding figure is
a function of the class balance you assume. On the full labelled pool at natural
prevalence (n=2000, supplementary population, no selection at all) the same two
statistics are 295/2000 = 14.8% [13.3%, 16.4%] at the ceiling and 556/2000 = 27.8% [25.9%, 29.8%] in the top tenth.
The per-stratum rows are the prevalence-free way to state it and should be
preferred in the paper.

**Stratum asymmetry (new, and it cuts against the detector).** The hallucinating
stratum is crowded at the top far harder than the correct stratum: 27.5% vs 9.5% at
the ceiling, 44.5% vs 21.5% in the top tenth -- non-overlapping Wilson intervals in
both cases. Right-censoring at ln(10) therefore removes more of the hallucinating
class's spread than the correct class's, which biases the measured class
separation (and so the 0.704 clean AUROC) DOWNWARD. The attacked subset pointed
the same way (24% vs 10% at the cap) but on n=17 hallucinating targets; this is
n=200 per stratum.

## 4. Rarefaction: distinct realised values vs number of targets observed

Distinct-values-observed is **monotone non-decreasing in n**, so any such count is
a SAMPLE statistic, not a property of the estimator. This curve is what lets a
reader tell the two apart. `E[distinct]` is exact (a value of multiplicity m is
missed with probability C(M-m, n)/C(M, n)); the Monte-Carlo column is
4000 subsamples without replacement and is shown only for the spread.

**fair pool (n=400, correct + hallucinating)**

| targets sampled | E[distinct] (exact) | MC mean | MC sd | MC min-max | % of the 39-value lattice |
| --- | --- | --- | --- | --- | --- |
| 10 | 7.35 | 7.33 | 1.22 | 3-10 | 19% |
| 20 | 11.61 | 11.62 | 1.62 | 5-18 | 30% |
| 40 | 16.73 | 16.77 | 1.86 | 10-24 | 43% |
| 80 | 21.89 | 21.87 | 1.89 | 15-28 | 56% |
| 97 | 23.25 | 23.32 | 1.81 | 17-29 | 60% |
| 160 | 26.52 | 26.50 | 1.57 | 21-31 | 68% |
| 320 | 30.09 | 30.07 | 0.86 | 26-31 | 77% |
| 400 (full population) | 31.00 | 31.00 | 0.00 | 31-31 | 79% |

**fair pool, correct stratum (n=200)**

| targets sampled | E[distinct] (exact) | MC mean | MC sd | MC min-max | % of the 39-value lattice |
| --- | --- | --- | --- | --- | --- |
| 10 | 7.87 | 7.86 | 1.11 | 4-10 | 20% |
| 20 | 12.63 | 12.57 | 1.60 | 6-18 | 32% |
| 40 | 18.01 | 17.97 | 1.79 | 12-24 | 46% |
| 80 | 23.03 | 23.04 | 1.59 | 17-28 | 59% |
| 97 | 24.27 | 24.29 | 1.47 | 18-28 | 62% |
| 160 | 27.02 | 27.02 | 0.89 | 23-28 | 69% |

**fair pool, hallucinating stratum (n=200)**

| targets sampled | E[distinct] (exact) | MC mean | MC sd | MC min-max | % of the 39-value lattice |
| --- | --- | --- | --- | --- | --- |
| 10 | 6.51 | 6.50 | 1.25 | 3-10 | 17% |
| 20 | 9.98 | 10.00 | 1.62 | 5-15 | 26% |
| 40 | 14.37 | 14.33 | 1.81 | 8-21 | 37% |
| 80 | 19.38 | 19.40 | 1.78 | 13-26 | 50% |
| 97 | 20.83 | 20.80 | 1.69 | 15-26 | 53% |
| 160 | 24.55 | 24.55 | 1.08 | 20-26 | 63% |

**_full labelled pool, n=2000 (supplementary)_**

| targets sampled | E[distinct] (exact) | MC mean | MC sd | MC min-max | % of the 39-value lattice |
| --- | --- | --- | --- | --- | --- |
| 10 | 7.58 | 7.57 | 1.17 | 3-10 | 19% |
| 20 | 12.00 | 12.03 | 1.61 | 6-18 | 31% |
| 40 | 17.04 | 17.03 | 1.88 | 11-24 | 44% |
| 80 | 21.80 | 21.81 | 1.92 | 16-28 | 56% |
| 97 | 23.03 | 23.06 | 1.88 | 17-29 | 59% |
| 160 | 26.10 | 26.13 | 1.79 | 20-32 | 67% |
| 320 | 29.77 | 29.79 | 1.48 | 25-34 | 76% |
| 400 | 30.71 | 30.70 | 1.35 | 25-35 | 79% |
| 800 | 32.90 | 32.90 | 1.11 | 29-35 | 84% |
| 1600 | 34.64 | 34.63 | 0.56 | 32-35 | 89% |
| 2000 (full population) | 35.00 | 35.00 | 0.00 | 35-35 | 90% |

## 5. Head-to-head with the attacked-subset numbers the paper currently carries

The repo's `results/dynamic_range_finding.md` reports, on the attacked subset
(80 correct + 17 hallucinating = 97 targets): 22 distinct values, 8/80 at the
ceiling, 21/80 in the top decile. Recomputed here on the fair pool, with the
attacked-subset figures reproduced from the same cache for comparability.
Remember these are NESTED: the 80 are the fair pool's correct[:80].

| statistic | attacked subset (nested) | fair pool | fair pool, correct only |
| --- | --- | --- | --- |
| n | 97 (80 correct + 17 hallucinating) | 400 | 200 |
| distinct realised values | 22 | 31 | 28 |
| ... as a share of the 39 attainable | 56% | 79% | 72% |
| correct answers at the ceiling | 8/80 = 10.0% [5.2%, 18.5%] | - | 19/200 = 9.5% [6.2%, 14.4%] |
| correct answers in the top tenth | 21/80 = 26.2% [17.9%, 36.8%] | - | 43/200 = 21.5% [16.4%, 27.7%] |
| ALL targets in the top tenth (pooled) | 27/97 = 27.8% [19.9%, 37.5%] | 132/400 = 33.0% [28.6%, 37.8%] | - |
| ALL targets at the ceiling (pooled) | 12/97 = 12.4% [7.2%, 20.4%] | 74/400 = 18.5% [15.0%, 22.6%] | - |

**The rarefaction control.** Drawing 80 targets at random from the fair pool's
correct stratum gives E[distinct] = **23.0** (MC sd 1.59), against the **22** actually
realised by the attacked 80. The observed 22 sits at the 37% percentile of that
reference distribution -- an unremarkable draw. The attacked cell's distinct-value
count is what a random 80 from this population produces; the same population
yields 28 distinct values at n=200 and is still climbing. "22 distinct values"
was never an estimator property, it was a sample size.

**What replaces it.** The estimator-level statement is the lattice: at N=10 there
are **39 attainable values in total and 2 in the top tenth of the range** -- true
by enumeration, independent of n, and not something a larger pool can improve.
The population-level statement is section 3: 132/400 = 33% [29%, 38%] of the fair
pool lands in that 2-value region.

## 6. Verdict: does the central claim survive the population fix?

**The crowding claim survives and does not weaken. The distinct-value claim does
not survive and must be replaced by the lattice count.**

| claim component | on the attacked subset | on the fair pool | direction |
| --- | --- | --- | --- |
| targets in the top tenth of the range | 27/97 = 28% | 132/400 = 33% | **stronger** |
| targets pinned at the ceiling | 12/97 = 12% | 74/400 = 18% | **stronger** |
| correct answers in the top tenth | 21/80 = 26.2% | 43/200 = 21.5% | slightly weaker, intervals overlap |
| correct answers at the ceiling | 8/80 = 10.0% | 19/200 = 9.5% | unchanged |
| "only 22 distinct values" | 22 | 31 at n=400; 35 at n=2000 | **retire: it was a sample size** |
| attainable values in the top tenth | 2 | 2 | unchanged (enumeration, not a sample) |

Reading. The two statistics the paper leans on hardest -- crowding at the ceiling
and in the top decile -- come out HIGHER on the fair pool than on the attacked
subset, because the attacked subset is 80/97 correct answers while the fair pool
is half hallucinations, and hallucinations are the crowded class. The claim was
therefore being UNDER-stated by being made on the wrong population, not
over-stated. The correct-stratum numbers, which is what the false-alarm attack
actually operates on, are essentially unchanged (9.5% vs 10.0% at the cap;
21.5% vs 26.2% in the top decile, overlapping intervals) -- so nothing that
depends on the FA arm moves.

Do not over-read the pooled rows, though: both pools are artificial class
balances (82/18 correct for the attacked subset, 50/50 for the fair pool) and the
real rate is 71% correct. At natural prevalence on n=2000 the pooled figures
are 14.8% at the ceiling and 27.8% in the top tenth -- between the two. The
per-stratum statement is the one that does not move with the assumed balance.

The one component that does not survive is the distinct-value count. 22 was a
draw from a population that yields 28 at n=200 and 35 at n=2000, and has still not
converged. Quoting it as a property of the estimator confuses a rarefaction
artefact with a granularity
limit. The replacement is exact and immune to n: **39 attainable values at N=10, of
which 2 lie in the top tenth of the range**.

