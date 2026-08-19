# The replay control: what the subsetting does, and what survives without it

Generated 2026-08-19 by `scripts/replay_control.py`. CPU-only:
no model is loaded and no GPU is touched. Every score below is replayed from the
recorded pairwise verdicts through `se.entropy.cluster_and_score` via the replay
machinery imported from `scripts/n_scaling_grid.py`, so replayed numbers here are
bit-identical to that report's.

**The question.** `results/n_scaling_grid.md` compares budgets across two sources:
N=10 is the direct Week-4 cache, N=20 and N=40 come from the N=40 checkpoint. One
claim already died on that mismatch. A second one -- *AUROC 0.704 -> 0.746, so the
budget makes it a better ranker* -- rests on the same step. This file measures the
step, explains it, and then redoes the comparison with the step removed.

**The three answers, up front.**

1. The published control's evidence for a bias is not evidence. It read 20 subset
   draws landing above the direct point estimate as a sign test at 2^-20. The
   replicates are not coin flips around the direct value: they are draws from a
   distribution whose centre is elsewhere. Over 200 draws, 10/200 (5.0%) fall BELOW
   the direct floor, so "20 of 20 above" has probability 0.36 even treating
   the draws as independent -- which they are not, and the dependence pushes it
   higher still.
2. Every apparent bias in that table is one difference wearing four hats: the
   direct cache has 19 clean answers at the ln 10 cap where the replay predicts
   24.0. Condition on the floor and the TPR and pAUC gaps vanish (residual
   |z| <= 0.14). The one count that carries it all is not significant: exact
   Poisson-binomial p = 0.081 one-sided, and the whole cluster-count
   distribution passes a goodness-of-fit test.
3. Like-for-like, **neither blocked claim survives in the form it was written.**
   The AUROC gain shrinks from +0.041 to +0.024 [-0.013, +0.059], which covers zero;
   the low-FPR pAUC does not fall with budget, it rises by +0.007, so the
   sentence "partial AUROC below a 10% false-alarm rate is 0.145 at N=10 and 0.126
   at N=40" is a measurement of the provenance step and not of the budget.

---

## 1. The replay-vs-direct step, characterised

200 independent 10-subset draws of the N=40 run, against the one direct Week-4
N=10 measurement, on the identical 200 correct + 200 hallucinating fair-pool
targets (id match verified at load; the run aborts otherwise).

| statistic | direct N=10 | replay N=10: mean | sd over draws | range | step (replay - direct) | paired 95% |
| --- | --- | --- | --- | --- | --- | --- |
| floor (min non-zero achievable FPR) | 9.5% | 11.9% | 1.6% | 7.0%-15.5% | +2.4 pts | [-3.0 pts, +8.0 pts] |
| AUROC | 0.7043 | 0.7219 | 0.0126 | 0.6837-0.7535 | +0.0176 | [-0.0266, +0.0621] |
| pAUC, FPR <= 5% (mean TPR in band) | 0.0724 | 0.0593 | 0.0105 | 0.0394-0.0917 | -0.0131 | [-0.0619, +0.0306] |
| pAUC, FPR <= 10% (mean TPR in band) | 0.1446 | 0.1185 | 0.0207 | 0.0788-0.1822 | -0.0260 | [-0.1025, +0.0548] |
| TPR at a matched 9.5% FPR | 27.5% | 23.4% | 3.2% | 18.3%-33.9% | -4.1 pts | [-12.8 pts, +8.8 pts] |
| TPR at a matched 10.0% FPR | 28.3% | 24.6% | 3.2% | 19.2%-34.7% | -3.7 pts | [-12.4 pts, +8.9 pts] |
| TPR at a matched 20.0% FPR | 43.7% | 45.5% | 3.4% | 38.3%-54.5% | +1.9 pts | [-8.1 pts, +13.0 pts] |

**Sign and magnitude.** The replay reads HIGHER than the direct cache on the floor
(+2.4 points, +26% relative) and on AUROC (+0.018), and LOWER on
everything that prices detection near the operating region: TPR at a matched 9.5%
false-alarm rate (-4.1 points) and partial AUROC below 10% (-0.026). Every
one of those intervals covers zero. None of them is a small effect on the scale of
the claims they would be used to license -- the TPR step alone is larger than the
entire budget effect that was proposed as a finding.

**Why the published sign test is the wrong test.** The control in
`results/n_scaling_grid.md` drew 20 replicates, found all 20 above 9.5%, and that
was read as 2^-20 evidence of bias. The null behind that arithmetic is "each
replicate is independently above or below the direct value with probability 1/2",
which is true only if the replicate distribution is CENTRED on the direct value.
It is not centred there, and it does not have to be: the direct value is one draw
of a 10-sample run, and the replicate distribution is centred on the conditional
mean given the N=40 draw. Measured over 200 replicates:

| statistic | direct | percentile of the direct value in the replicate distribution | P(20 of 20 on one side), if independent |
| --- | --- | --- | --- |
| floor (min non-zero achievable FPR) | 9.5% | 5.0% of draws below | 0.358 |
| AUROC | 0.7043 | 7.0% of draws below | 0.234 |
| TPR at a matched 9.5% FPR | 27.5% | 88.5% of draws below | 0.087 |
| pAUC, FPR <= 10% (mean TPR in band) | 0.1446 | 87.5% of draws below | 0.069 |

So the observation that licensed the sentence "if those disagree beyond the Wilson
interval, the subsetting is unsound" has probability 0.36 under the replay's
own distribution. Two further reasons the sign test cannot be rescued: the
replicates share one 40-sample realisation per question and one set of 200
questions, so they are positively correlated, which pushes the probability of a
unanimous run UP and not down; and the replicate spread measures only the subset
draw, so it is not an uncertainty on the step at all. The uncertainty on the step
is the paired interval in the table above: +/-5.5 points on the floor, where
an interval built from the subset-draw spread alone would be +/-3.1 points, 1.8x
narrower.

## 2. The like-for-like budget comparison

All three budgets from the one N=40 checkpoint. N=10 and N=20 are means over 200
subset draws; N=40 is the single realisation there is. Intervals are a paired
bootstrap (4000 resamples) that resamples the 200+200 targets jointly across
budgets AND resamples the subset draw, so both variance components are inside
every replayed cell. The direct row is shown for contrast only -- it is the row
that must not be mixed into a trend.

| statistic | direct N=10 (do not mix) | replay N=10 | replay N=20 | measured N=40 |
| --- | --- | --- | --- | --- |
| floor (min non-zero achievable FPR) | 9.5% [5.5%, 13.5%] | 11.9% [7.0%, 17.5%] | 3.0% [0.5%, 6.5%] | 2.0% [0.5%, 4.0%] |
| AUROC | 0.704 [0.654, 0.753] | 0.722 [0.666, 0.776] | 0.738 [0.686, 0.788] | 0.746 [0.697, 0.792] |
| pAUC, FPR <= 5% (mean TPR in band) | 0.072 [0.046, 0.125] | 0.059 [0.035, 0.106] | 0.069 [0.025, 0.144] | 0.069 [0.036, 0.131] |
| pAUC, FPR <= 10% (mean TPR in band) | 0.145 [0.093, 0.222] | 0.119 [0.070, 0.201] | 0.123 [0.062, 0.215] | 0.126 [0.068, 0.203] |
| pAUC, FPR <= 20% (mean TPR in band) | 0.249 [0.183, 0.330] | 0.229 [0.145, 0.332] | 0.237 [0.150, 0.341] | 0.234 [0.158, 0.333] |
| pAUC, FPR 20-50% | 0.636 [0.546, 0.724] | 0.671 [0.564, 0.770] | 0.699 [0.598, 0.790] | 0.717 [0.622, 0.804] |
| pAUC, FPR 50-100% | 0.927 [0.888, 0.957] | 0.950 [0.913, 0.977] | 0.962 [0.931, 0.983] | 0.967 [0.941, 0.985] |
| TPR at a matched 5.0% FPR | 14.5% [9.6%, 25.0%] | 12.3% [9.0%, 21.2%] | 14.5% [10.3%, 24.5%] | 13.2% [10.5%, 23.1%] |
| TPR at a matched 9.5% FPR | 27.5% [18.2%, 36.3%] | 23.4% [17.1%, 36.0%] | 25.5% [19.5%, 38.2%] | 24.0% [19.7%, 35.8%] |
| TPR at a matched 10.0% FPR | 28.3% [19.2%, 37.2%] | 24.6% [18.0%, 37.1%] | 26.7% [20.5%, 39.5%] | 25.1% [20.7%, 37.0%] |
| TPR at a matched 20.0% FPR | 43.7% [36.1%, 54.8%] | 45.5% [35.7%, 59.2%] | 48.6% [39.5%, 62.0%] | 47.8% [40.1%, 63.1%] |
| achieved FPR, 5% budget | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] | 3.1% [0.0%, 5.0%] | 5.0% [2.5%, 5.0%] |
| deterministic TPR, 5% budget | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] | 8.8% [0.0%, 22.0%] | 11.0% [4.5%, 21.5%] |
| achieved FPR, 10% budget | 9.5% [0.0%, 10.0%] | 1.4% [0.0%, 10.0%] | 9.3% [3.5%, 10.0%] | 10.0% [8.5%, 10.0%] |
| deterministic TPR, 10% budget | 27.5% [0.0%, 33.5%] | 4.1% [0.0%, 33.5%] | 22.0% [7.0%, 36.5%] | 24.0% [12.5%, 33.5%] |
| achieved FPR, 20% budget | 9.5% [7.0%, 20.0%] | 14.5% [8.5%, 20.0%] | 19.6% [17.5%, 20.0%] | 20.0% [18.5%, 20.0%] |
| deterministic TPR, 20% budget | 27.5% [22.0%, 51.0%] | 33.8% [20.5%, 56.5%] | 45.3% [30.0%, 59.5%] | 44.5% [30.0%, 61.0%] |

**The paired differences that matter.**

| comparison | statistic | difference | 95% | verdict |
| --- | --- | --- | --- | --- |
| replay10 -> replay20 | floor (min non-zero achievable FPR) | -8.9 pts | [-14.5 pts, -3.5 pts] | excludes zero |
| replay10 -> replay20 | AUROC | +0.0160 | [-0.0255, +0.0559] | covers zero |
| replay10 -> replay20 | pAUC, FPR <= 10% (mean TPR in band) | +0.0048 | [-0.0780, +0.0880] | covers zero |
| replay10 -> replay20 | TPR at a matched 9.5% FPR | +2.1 pts | [-7.8 pts, +12.2 pts] | covers zero |
| replay10 -> replay20 | TPR at a matched 10.0% FPR | +2.1 pts | [-7.7 pts, +12.2 pts] | covers zero |
| replay20 -> measured40 | floor (min non-zero achievable FPR) | -1.0 pts | [-4.5 pts, +1.5 pts] | covers zero |
| replay20 -> measured40 | AUROC | +0.0076 | [-0.0153, +0.0304] | covers zero |
| replay20 -> measured40 | pAUC, FPR <= 10% (mean TPR in band) | +0.0025 | [-0.0586, +0.0578] | covers zero |
| replay20 -> measured40 | TPR at a matched 9.5% FPR | -1.5 pts | [-7.1 pts, +5.5 pts] | covers zero |
| replay20 -> measured40 | TPR at a matched 10.0% FPR | -1.6 pts | [-7.3 pts, +5.5 pts] | covers zero |
| replay10 -> measured40 | floor (min non-zero achievable FPR) | -9.9 pts | [-15.5 pts, -5.0 pts] | excludes zero |
| replay10 -> measured40 | AUROC | +0.0236 | [-0.0135, +0.0595] | covers zero |
| replay10 -> measured40 | pAUC, FPR <= 10% (mean TPR in band) | +0.0074 | [-0.0677, +0.0768] | covers zero |
| replay10 -> measured40 | TPR at a matched 9.5% FPR | +0.6 pts | [-7.7 pts, +10.3 pts] | covers zero |
| replay10 -> measured40 | TPR at a matched 10.0% FPR | +0.6 pts | [-7.6 pts, +10.3 pts] | covers zero |
| direct10 -> measured40 | floor (min non-zero achievable FPR) | -7.5 pts | [-11.5 pts, -4.0 pts] | excludes zero |
| direct10 -> measured40 | AUROC | +0.0412 | [+0.0064, +0.0767] | excludes zero |
| direct10 -> measured40 | pAUC, FPR <= 10% (mean TPR in band) | -0.0187 | [-0.0798, +0.0428] | covers zero |
| direct10 -> measured40 | TPR at a matched 9.5% FPR | -3.5 pts | [-8.5 pts, +7.3 pts] | covers zero |
| direct10 -> measured40 | TPR at a matched 10.0% FPR | -3.1 pts | [-8.1 pts, +7.5 pts] | covers zero |

**Does the AUROC gain survive?** No, not as a claim.

- claimed, across the provenance step: 0.704 -> 0.746 = **+0.041**
- like-for-like, replay N=10 -> measured N=40: 0.722 -> 0.746 = **+0.024** [-0.013, +0.059]
- so **43% of the advertised gain is the change of source**, not the
  change of budget.
- the residue is not separable from zero on 200 questions: the paired interval
  covers it, and the only comparison in this report that DOES clear zero (+0.041)
  is the confounded one, where the provenance step and the budget effect happen
  to add.

The N=10 replay and the N=40 run are nested -- same questions, same generations,
the smaller budget is literally a subset of the larger -- so the paired comparison
is as favourable as a design can be to detecting a real budget effect. It still
covers zero.

**Be precise about what that means.** This is an underpowered comparison, not a
demonstration that the budget does nothing. Holding the 200 questions and their
generations fixed and varying only the subset draw, the 40-sample budget ranks
better in 197 of 200 draws, so the direction is consistent. What the
interval says is that 200 questions cannot separate +0.024 from zero -- and a
paper claim needs the interval, because it is a claim about the detector and not
about these 200 questions. The right sentence is "rises by a fraction of the
advertised amount, and not distinguishable from flat at this sample size"; the
wrong ones are "makes it a better ranker" and "is flat".

**What DOES survive like-for-like** is the granularity result, which is what the
paper actually needs:

- the floor falls 11.9% -> 3.0% -> 2.0% on one source, and the
  N=10 -> N=40 difference clears zero by a wide margin (-9.9 points
  [-15.5, -5.0]); the N=20 -> N=40 step on its own does not;
- a 5% false-alarm budget is unbuyable at N=10 (deterministic rule flags nothing)
  and buyable at N=40;
- and it buys almost nothing: TPR at a matched 5% is
  12.3% at N=10 against 13.2% at N=40.

## 3. Where a step could come from -- and where this one comes from

**The estimator is exactly unbiased, and that is a theorem, not a hope.** The 40
samples for a question are i.i.d. draws, hence exchangeable. A uniformly random
10-subset of an exchangeable 40-tuple has exactly the distribution of 10 i.i.d.
draws. The clusterer is union-find over PAIRWISE verdicts, so the clustering of a
subset depends only on the verdicts inside it and is exactly what a direct 10-run
with those samples would have produced. Therefore, for every question i,
E[replayed score] = E[direct score], and the floor -- a mean of indicators -- is
unbiased term by term. Nothing about reusing one verdict matrix changes this: the
expectation is over the subset draw AND the sample draw, and both are honest.

**What reusing one matrix DOES do is destroy the independence of replicates.**
Every replicate conditions on the same 40 samples and the same 200 questions, so
the replicate spread is subset-draw noise around a conditional mean, and it
understates the true uncertainty by construction. That is the actual defect in the
published control -- not bias, but an interval that is too narrow and a test whose
null does not hold. It is also why the report's replayed Wilson intervals (e.g.
N=20 floor "3.0% [1.4%, 6.4%]", computed on replicate 0) are understated.

**So the gap has to be explained by the data, and the data explains it as one
number.** The four rows of the published control are not four findings:

| statistic | correlation with the floor across subset draws | direct value, predicted from its own floor | observed | residual z |
| --- | --- | --- | --- | --- |
| AUROC | -0.51 | 0.7318 | 0.7043 | -2.54 |
| TPR at a matched 9.5% FPR | -0.78 | 27.2% | 27.5% | +0.14 |
| TPR at a matched 10.0% FPR | -0.78 | 28.4% | 28.3% | -0.08 |
| pAUC, FPR <= 5% (mean TPR in band) | -0.85 | 0.0730 | 0.0724 | -0.12 |
| pAUC, FPR <= 10% (mean TPR in band) | -0.85 | 0.1456 | 0.1446 | -0.10 |

The TPR and pAUC "biases" are not independent of the floor -- they ARE the floor.
Give the replay the direct cache's floor and it predicts the direct cache's TPR at
a matched rate to within 0.14 of a standard deviation. The AUROC residual is the
one that does not vanish (-2.54 subset-draw sd, i.e. +0.028 in AUROC units), and
even that sits inside the paired interval on the AUROC step in section 1.
(This is a redundancy
decomposition, not a significance test: the yardstick is the subset-draw spread,
which omits the direct arm's own sampling noise. The honest interval on each step
is the paired one in section 1, and all of them cover zero.)

**Is the one number itself out of line?** No.

- **correct stratum:** direct cache has 19/200 answers at the ln 10 cap; the
  replay says the expected count is 24.0 (+/-0.05 Monte-Carlo, sd 3.23 under
  the exact Poisson-binomial null over the 200 per-question probabilities). P(X <= 19) = 0.081,
  P(X >= 19) = 0.957.
- **hallucinating stratum:** direct cache has 55/200 answers at the ln 10 cap; the
  replay says the expected count is 55.2 (+/-0.08 Monte-Carlo, sd 4.75 under
  the exact Poisson-binomial null over the 200 per-question probabilities). P(X <= 55) = 0.527,
  P(X >= 55) = 0.557.

And the discrepancy does not extend past that one cell. The full distribution of
the cluster count at k=10 -- the thing the whole score is a function of -- matches:

| stratum | K=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | chi-square | df | p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| correct, direct | 11 | 17 | 27 | 18 | 27 | 24 | 18 | 15 | 24 | 19 | 7.39 | 9 | 0.60 |
| correct, replay expected | 12.0 | 19.9 | 23.7 | 24.3 | 22.4 | 20.1 | 18.1 | 17.2 | 18.3 | 24.0 | | | |
| hallucinating, direct | 2 | 3 | 5 | 14 | 17 | 20 | 24 | 26 | 34 | 55 | 3.57 | 7 | 0.83 |
| hallucinating, replay expected | 0.7 | 2.3 | 5.3 | 9.8 | 14.7 | 19.4 | 24.3 | 30.1 | 38.2 | 55.2 | | | |

**One provenance difference IS real, and it is not the subsetting.** The two
sample sets were generated at different times (Week 4 in June, the checkpoint on
2026-08-13) under an identical config -- same model, 4-bit, T=1.0, top_p=1.0,
max_new_tokens=48, seed 0 -- and they still differ measurably in the text:

- mean answer length: 116.0 chars direct vs 119.6 in the checkpoint, paired difference **+3.63 +/- 0.91** (z = +4.0);
- fraction of answers ending in terminal punctuation (a truncation proxy): 0.738 vs 0.722, paired -0.0163 +/- 0.0071;
- but exact-duplicate rate among 10 answers -- a pure generation statistic with no
  NLI in it -- is indistinguishable: 0.1590 direct vs 0.1638 replayed on the correct stratum, paired -0.0048 +/- 0.0077.

So the checkpoint's answers run about 3% longer and are slightly more often cut off
at the token cap. That is a genuine run-to-run difference of unknown cause, its
sign is the right one to nudge the ceiling atom upward (longer, more truncated
answers entail each other less often), and it is small enough to leave the
cluster-count distribution statistically indistinguishable.

**Verdict on mechanism.** The bias is not a property of the estimator (unbiased by
exchangeability), not a property of the finite verdict matrix (which affects the
correlation between replicates, not their mean), and not a property of the
subsetting scheme (uniform, independent per question, and it reproduces the whole
cluster-count marginal). The remaining candidates are (a) sampling noise in the
direct measurement -- 19 versus 24 questions in one tail cell, one-sided p = 0.081
-- and (b) a small real generation-run difference between June and August. Both
point the same way: **the replay is the sounder of the two measurements, and the
direct N=10 cache is the row whose provenance deserves the scrutiny.** It is a
single realisation, generated on different hardware-days, and it is the only row
in the budget table that cannot be reproduced from the checkpoint.

The clean way to close this is unchanged and cheap: re-measure N=10 directly on the
current box (about a quarter of the N=40 cost) and the drift component separates
from the subsetting component by subtraction.

## 4. The pAUC question

The blocked claim reads: *AUROC rises 0.704 -> 0.746, but the entire improvement
lies above 20% false alarms; partial AUROC below 10% is 0.145 at N=10 and 0.126 at
N=40.* Two things are wrong with it and one thing is right.

**Wrong 1: that fall is the provenance step, not the budget.** Like-for-like the
low-FPR pAUC does not fall at all -- it rises:

| band | direct N=10 | replay N=10 | replay N=20 | measured N=40 | chance in band |
| --- | --- | --- | --- | --- | --- |
| FPR 0%-5% | 0.072 | 0.059 | 0.069 | 0.069 | 0.025 |
| FPR 0%-10% | 0.145 | 0.119 | 0.123 | 0.126 | 0.050 |
| FPR 0%-20% | 0.249 | 0.229 | 0.237 | 0.234 | 0.100 |
| FPR 20%-50% | 0.636 | 0.671 | 0.699 | 0.717 | 0.350 |
| FPR 50%-100% | 0.927 | 0.950 | 0.962 | 0.967 | 0.750 |

Direct -> N=40 on the pAUC below 10% is -0.0187 -- the claim's quoted -0.019. Replay
N=10 -> N=40 is +0.0074: opposite sign, and 2.5x smaller. The quoted fall measures which
cache the N=10 row came from, not what the budget did.

**Wrong 2: the units are mislabelled in the source document.**
`results/post_overnight_claim_review.md` heads this table "standardised partial AUC
... (0.5 = chance within the band)". These numbers are the MEAN TPR inside the
band, for which chance is the band midpoint: 0.05 for FPR <= 10%, not 0.5. So the
direct row's 0.145 is not a near-catastrophic 0.145-against-0.5, it is 2.9x
chance. Any prose built on the mislabel will overstate how bad the operating
region looks.

**Right: the point-estimate decomposition really does put the gain up top.**
Splitting the like-for-like AUROC gain (replay N=10 -> N=40, +0.0236) into
contributions by false-alarm band (each band's mean-TPR change times its width;
the three contributions sum to the AUROC change):

| band | width | replay N=10 | measured N=40 | contribution to the AUROC gain | share |
| --- | --- | --- | --- | --- | --- |
| FPR 0%-20% | 0.20 | 0.229 | 0.234 | +0.00088 | 4% |
| FPR 20%-50% | 0.30 | 0.671 | 0.717 | +0.01390 | 59% |
| FPR 50%-100% | 0.50 | 0.950 | 0.967 | +0.00885 | 38% |

**What can honestly be said.** Only this: *no improvement in discrimination is
detectable in any false-alarm band, and what improvement the point estimates show
is concentrated above a 20% false-alarm rate.* The gate's objection is correct on its own terms -- overlapping
intervals mean undetectable, not absent -- but the repair is not to assert absence
more carefully. It is to notice that, like-for-like, the low-FPR point estimates
move the SAME way as the overall AUROC and by a trivial amount, so there is no
longer any tension to explain and no "where the gain lives" story to tell. The
sentence that fits the data is "not detectably concentrated at low FPR", and it is
a weaker sentence than the one the paper wanted.

## 5. A defect in `results/n_scaling_grid.md`, and the correct value

Section 1 of that report gives N=40 a "next FPR" of 2.5%; section 3's operator
menu says the closest achievable point to a 1% target is 2.0%. Both cells are
computing what their own code says, and the report is still wrong, because the
**floor** column is computing a third thing.

From the checkpoint, the achievable false-alarm rates at N=40 in ascending order
are 2.0%, 2.5%, 4.0%, 4.5%, 5.0%, 6.0%, ...

- the smallest false-alarm rate a firing threshold can realise at N=40 is
  **2.0%** (4/200 = 2.0% [0.8%, 5.0%]);
- the next one after it is **2.5%**, which is what the "next FPR" column reports;
- the floor column reports the CEILING-ATOM mass instead -- the share of negatives
  sitting exactly at ln 40 -- which is 0/200 = 0.0%, under a header that reads
  "floor = min non-zero FPR".

At N=10 and N=20 the two coincide, because some negative does sit at the cap, and
the column has been read as the floor ever since. At N=40 no negative reaches ln 40
and they part company. The published row therefore says the N=40 floor is 0.0%
[0.0%, 1.9%], which invites exactly the wrong inference -- that a sub-1% operating
point might exist at N=40 with more data. It does not: the smallest one that exists
is 2.0%, and 0.0% is the structural zero of the never-fire policy.

**The correct value for the N=40 floor is 2.0% (4/200 negatives), and the next
achievable rate above it is 2.5%.** Section 2's claim that the `correct` row of the
ceiling-atom table "IS the achievable-FPR floor as a function of the sample
budget" inherits the same defect: it is the floor only while the atom is non-empty.

**The fix, not applied here** (`scripts/n_scaling_grid.py` is owned by another
task): in `write_grid_report`, the floor cell should be the first FIRING point,
`firing[0]['fpr']`, with the ceiling-atom mass reported as its own separate column
(it is a real and different quantity -- it is what section 2 predicts), and the
"next FPR" column should stay `firing[1]['fpr']`. The one-line version is that
`ceiling_atom()` answers "how much mass is at ln N" and the column header promises
"what is the cheapest alarm an operator can buy"; those are the same question only
when the answer is non-zero.

## 6. The two blocked claims

**Claim 1 -- "a larger sample budget makes semantic entropy a better ranker,
AUROC 0.704 -> 0.746 (+0.042)": DOES NOT SURVIVE.** Both ends must come from one
source. They do here, and the gain is +0.024 [-0.013, +0.059], which covers zero, on
the most favourable (fully nested, fully paired) design available. 43% of the
advertised +0.041 is the change of cache. The paper may say the point
estimate rises and is not distinguishable from flat on 200 questions; it may not
say the budget makes it a better ranker, and it may not say the ranker is flat
either -- an interval that covers zero is not a demonstration of no effect.

**Claim 2 -- "the entire AUROC gain sits above 20% FPR, low-FPR pAUC 0.145 -> 0.126":
DOES NOT SURVIVE AS WRITTEN.** The fall it cites is the provenance step with the
sign reversed: like-for-like the low-FPR pAUC rises by +0.007. What is left is a
decomposition of an undetectable gain, which is not a finding. If the paper wants a
sentence here, it is: *no budget effect on discrimination is detectable at any
false-alarm rate; the point estimates rise slightly and almost entirely above a 20%
false-alarm rate, where no operator runs.* That is honest and it is thin.

**What is worth carrying instead** is the result that does survive uniform
provenance and does not need an AUROC at all: the floor falls monotonically with
budget (11.9% -> 3.0% -> 2.0%), a 5% false-alarm budget
goes from unbuyable to buyable, and the deterministic rule it unlocks catches
11.0% of hallucinations -- against the 12.3% a coin-flip between two N=10 thresholds
already delivers at the same false-alarm rate, at a tenth of the cost. The
rebuttal "just raise N" is answered by granularity, not by discrimination --
which is the paper's thesis anyway.

## 7. Provenance and reproduction

- checkpoint: `I:\GITHUBPROJECTS\SE Research\results\n_scaling_ckpt.jsonl` (400 evaluations, N=40, full pairwise
  verdict matrices)
- Week-4 direct cache: `\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research\samples\wk4_full_2000q` (relabeled.jsonl, entropy.jsonl, samples.jsonl)
- population: fair pool, `_stratum_ids('right'/'wrong', seed=0)[:200]`; the ids in
  the checkpoint are verified identical to it at load, so every comparison above is
  paired on the same targets
- generation, both sources: Llama-3.1-8B-Instruct 4-bit, T=1.0, top_p=1.0,
  max_new_tokens=48, seed 0 (Week-4 `manifest.json` and the checkpoint records agree)
- subset draws per replayed budget: 200; bootstrap resamples: 4000; per-question
  subset draws for the cluster-count profiles: 4000
- replay path: `budget_scores` / `score_subset` imported from
  `scripts/n_scaling_grid.py`, which drive the project's own
  `se.entropy.cluster_and_score` from the recorded verdicts
- regenerate: `.venv\Scripts\python.exe scripts\replay_control.py`
- nothing here loads a model or uses the GPU
