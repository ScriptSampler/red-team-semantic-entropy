# The achievable false-positive-rate grid of semantic entropy at N=10

Generated 2026-08-13 by `scripts/achievable_fpr_grid.py` (CPU only; no GPU, no model, no attack data).
Clean scores: `entropy_nats` of the Week-4 span-oracle cache `samples/wk4_full_2000q/relabeled.jsonl`.
Threshold rule and achieved FPRs come from `se.stats.attainable_fprs` /
`se.stats.operating_point` (the versions FIXED on 2026-08-13); nothing here
reimplements the quantile rule they replaced.

## The claim in one line

> A detector that flags when `score >= tau` can only change its false-positive rate
> at a value some clean correct answer actually took. Semantic entropy at N=10 takes
> **39** values in total and **2** above 0.9 x ln 10, and it
> puts an ATOM on the top one. So the false-alarm rates an operator can select from
> are a short finite list, and its smallest non-zero entry is **9.5%** [6.2%, 14.4%]
> (fair pool, correct stratum, n=200). **An operator who wants a 5%
> false-alarm rate cannot have one.** The next rate up is **21.5%**; between them there is nothing.

Why the smallest non-zero FPR is exactly the ceiling atom, by construction: the
largest value the estimator can emit is ln(10) = 2.3026, so every
threshold above it flags nothing, and the first threshold that fires at all is
tau = ln(10) itself, which flags EVERY negative at the ceiling and no other.
The minimum non-zero attainable FPR is therefore not a tuning choice; it is
P(a clean correct answer produces N mutually distinct meanings).

## 1. The full grid, fair pool correct stratum (n=200 negatives)

Every operating point the detector can be run at, ascending FPR. FPR is measured on
the fair pool's **correct** stratum (n=200); TPR on its **hallucinating**
stratum (n=200). Wilson 95% intervals. `tau = inf` is the always-available
"never fire" policy; it is a real operating point and it is the only one below
9.5%.

| # | threshold tau (nats) | FPR (false alarms on correct answers) | TPR (hallucinations caught) | in top tenth of range? |
| --- | --- | --- | --- | --- |
| 0 | inf (never fire) | 0/200 = 0.0% (exact: the policy never fires) | 0/200 = 0.0% (exact: the policy never fires) | - |
| 1 | 2.302585 | 19/200 = 9.5% [6.2%, 14.4%] | 55/200 = 27.5% [21.8%, 34.1%] | yes |
| 2 | 2.163956 | 43/200 = 21.5% [16.4%, 27.7%] | 89/200 = 44.5% [37.8%, 51.4%] | yes |
| 3 | 2.025326 | 53/200 = 26.5% [20.9%, 33.0%] | 104/200 = 52.0% [45.1%, 58.8%] | - |
| 4 | 1.973001 | 58/200 = 29.0% [23.2%, 35.6%] | 115/200 = 57.5% [50.6%, 64.1%] | - |
| 5 | 1.834372 | 65/200 = 32.5% [26.4%, 39.3%] | 123/200 = 61.5% [54.6%, 68.0%] | - |
| 6 | 1.748067 | 76/200 = 38.0% [31.6%, 44.9%] | 139/200 = 69.5% [62.8%, 75.5%] | - |
| 7 | 1.695743 | 78/200 = 39.0% [32.5%, 45.9%] | 141/200 = 70.5% [63.8%, 76.4%] | - |
| 8 | 1.643418 | 81/200 = 40.5% [33.9%, 47.4%] | 143/200 = 71.5% [64.9%, 77.3%] | - |
| 9 | 1.609438 | 89/200 = 44.5% [37.8%, 51.4%] | 150/200 = 75.0% [68.6%, 80.5%] | - |
| 10 | 1.504788 | 91/200 = 45.5% [38.7%, 52.4%] | 151/200 = 75.5% [69.1%, 80.9%] | - |
| 11 | 1.497866 | 102/200 = 51.0% [44.1%, 57.8%] | 160/200 = 80.0% [73.9%, 85.0%] | - |
| 12 | 1.470808 | 103/200 = 51.5% [44.6%, 58.3%] | 161/200 = 80.5% [74.5%, 85.4%] | - |
| 13 | 1.418484 | 107/200 = 53.5% [46.6%, 60.3%] | 165/200 = 82.5% [76.6%, 87.1%] | - |
| 14 | 1.359237 | 111/200 = 55.5% [48.6%, 62.2%] | 167/200 = 83.5% [77.7%, 88.0%] | - |
| 15 | 1.279854 | 112/200 = 56.0% [49.1%, 62.7%] | 170/200 = 85.0% [79.4%, 89.3%] | - |
| 16 | 1.227529 | 128/200 = 64.0% [57.1%, 70.3%] | 179/200 = 89.5% [84.5%, 93.0%] | - |
| 17 | 1.193550 | 130/200 = 65.0% [58.2%, 71.3%] | 181/200 = 90.5% [85.6%, 93.8%] | - |
| 18 | 1.168282 | 132/200 = 66.0% [59.2%, 72.2%] | 181/200 = 90.5% [85.6%, 93.8%] | - |
| 19 | 1.088900 | 139/200 = 69.5% [62.8%, 75.5%] | 182/200 = 91.0% [86.2%, 94.2%] | - |
| 20 | 1.054920 | 140/200 = 70.0% [63.3%, 75.9%] | 182/200 = 91.0% [86.2%, 94.2%] | - |
| 21 | 0.943348 | 144/200 = 72.0% [65.4%, 77.8%] | 182/200 = 91.0% [86.2%, 94.2%] | - |
| 22 | 0.940448 | 150/200 = 75.0% [68.6%, 80.5%] | 190/200 = 95.0% [91.0%, 97.3%] | - |
| 23 | 0.897946 | 153/200 = 76.5% [70.2%, 81.8%] | 190/200 = 95.0% [91.0%, 97.3%] | - |
| 24 | 0.801819 | 157/200 = 78.5% [72.3%, 83.6%] | 192/200 = 96.0% [92.3%, 98.0%] | - |
| 25 | 0.639032 | 172/200 = 86.0% [80.5%, 90.1%] | 195/200 = 97.5% [94.3%, 98.9%] | - |
| 26 | 0.500402 | 173/200 = 86.5% [81.1%, 90.6%] | 196/200 = 98.0% [95.0%, 99.2%] | - |
| 27 | 0.325083 | 189/200 = 94.5% [90.4%, 96.9%] | 198/200 = 99.0% [96.4%, 99.7%] | - |
| 28 | 0.000000 | 200/200 = 100.0% [98.1%, 100.0%] | 200/200 = 100.0% [98.1%, 100.0%] | - |

**29 operating points in total, 28 of which fire.** The two
that matter for any realistic false-alarm budget are rows 0-2:

- `tau > 2.3026` -> FPR **0%**, TPR **0%** (flags nothing);
- `tau = 2.3026` (= ln 10) -> FPR **9.5%**, TPR **27.5%**;
- `tau = 2.1640` -> FPR **21.5%**, TPR **44.5%**.

How many FIRING operating points exist below a given false-alarm budget -- this is
`sun2026granularity`'s "handful of usable thresholds", counted:

| false-alarm budget | firing operating points at or below it (fair pool, n=200) | (full pool, n=1424) |
| --- | --- | --- |
| FPR <= 1% | **0** | 0 |
| FPR <= 2% | **0** | 0 |
| FPR <= 5% | **0** | 0 |
| FPR <= 10% | **1** | 0 |
| FPR <= 15% | **1** | 1 |
| FPR <= 20% | **1** | 1 |
| FPR <= 25% | **2** | 2 |
| FPR <= 50% | **10** | 11 |
| FPR <= 100% | **28** | 34 |

## 2. Which nominal operating points are ACHIEVABLE (and what asking for one costs)

`operating_point(..., mode=...)` on the fair pool's correct stratum. `at_most` is the
contract an operator states ("my false-alarm budget is X"); `closest` is what a
measurement wants (the nearest real operating point, which may be above budget);
`nominal_quantile` is the historical rule, kept only to show what it did.

Two different questions hide under the word "achievable" and the table keeps them
apart. *Budget honourable*: is there any firing threshold at or below the target
(what `at_most` answers)? *Rate achievable*: is the target itself one of the rates on
the grid? The second is the granularity question; the first is what an operator
actually gets told.

| target FPR | `at_most`: tau | achieved FPR | TPR | `closest`: achieved FPR | TPR | `nominal_quantile`: achieved FPR | budget honourable? | rate achievable? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1% | inf | **0.0%** (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% | 9.5% **over budget** | no -- flags nothing | **NO** |
| 5% | inf | **0.0%** (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% | 9.5% **over budget** | no -- flags nothing | **NO** |
| 10% | 2.3026 | **9.5%** | 27.5% | 9.5% | 27.5% | 21.5% **over budget** | yes, at 9.5% | **NO** |
| 20% | 2.3026 | **9.5%** | 27.5% | 21.5% **over budget** | 44.5% | 21.5% **over budget** | yes, at 9.5% | **NO** |

**Reading the `rate achievable?` column.** No threshold realises 1%, 5%, 10% or 20% on
this population. For 1% and 5% that is not a sampling accident and can be stated with
confidence: every firing threshold has FPR at least the ceiling-atom mass, estimated
19/200 = 9.5% with a Wilson 95% lower bound of **6.2%**, so at 95% confidence
*no operating point of any kind exists at or below a 5% false-alarm rate except the
degenerate one that flags nothing*. For 10% and 20% the honest statement is weaker:
they fall strictly BETWEEN adjacent attainable points (9.5% and 21.5%, and 21.5% and
26.5%), and the Wilson intervals of those points [6.2%, 14.4%] and [16.4%, 27.7%] cover them, so the data
cannot rule out that one of those two thresholds runs at exactly 10% or 20% in the
population. That is itself an operational cost and section 4 gives it a name.

**What asking for 5% costs.** `at_most` at a 5% budget returns `tau = inf`: the only
way to honour a 5% false-alarm budget is to flag nothing, catching **0%** of
hallucinations. Accept the nearest real point instead and the budget is blown by a
factor of 1.9x -- 9.5% FPR -- for a TPR of 27.5%. There is no third option, and
that is the whole of the operator's menu below a 21.5% false-alarm rate.

(The `nominal_quantile` column is the defect this file's tooling was fixed for: the
old rule, asked for 10%, returned a threshold that runs at 21.5%. It did not fail
because 10% is hard to hit -- it failed because 10% does not exist, and interpolating
between order statistics hides that by landing inside an atom.)

## 3. Why there is nothing in between: the ceiling atom is indivisible

At `tau = ln 10` the detector flags every item at the ceiling: **19 correct + 55 hallucinating = 74** of the
400 fair-pool targets. Those 74 items carry the SAME SCORE. No threshold can
separate them, so the 19 false alarms are not a tuning failure -- they are the price
of the 55 detections, fixed, take it or leave it. Within the atom the precision is
55/74 = 74.3% [63.3%, 82.9%] at the fair pool's 50/50 balance.

The same holds one point down. The second attainable value in the top tenth,
2.163956, carries 24 correct and 34 hallucinating answers; adding it to
the flagged set is the single jump from 9.5% to 21.5% FPR (and 27.5% to 44.5% TPR).

This is the mechanism the top-decile framing was gesturing at, stated without an
arbitrary cut: the two values above 0.9 x ln 10 are not "a small region of the
range", they are **two indivisible blocks of population**, and an operator's entire
low-false-alarm menu consists of taking neither, one, or both.

## 4. The achievable ROC is a set of POINTS

Plotted in `figures/fig_achievable_roc.pdf` (exact values in
`figures/fig_achievable_roc_data.csv`). Below, the low-FPR end in full.

| tau | FPR [95% CI] | TPR [95% CI] | slope to the next point |
| --- | --- | --- | --- |
| inf | 0/200 = 0.0% (exact: the policy never fires) | 0/200 = 0.0% (exact: the policy never fires) | 2.89 |
| 2.3026 | 19/200 = 9.5% [6.2%, 14.4%] | 55/200 = 27.5% [21.8%, 34.1%] | 1.42 |
| 2.1640 | 43/200 = 21.5% [16.4%, 27.7%] | 89/200 = 44.5% [37.8%, 51.4%] | 1.50 |
| 2.0253 | 53/200 = 26.5% [20.9%, 33.0%] | 104/200 = 52.0% [45.1%, 58.8%] | 2.20 |
| 1.9730 | 58/200 = 29.0% [23.2%, 35.6%] | 115/200 = 57.5% [50.6%, 64.1%] | 1.14 |
| 1.8344 | 65/200 = 32.5% [26.4%, 39.3%] | 123/200 = 61.5% [54.6%, 68.0%] | 1.45 |
| 1.7481 | 76/200 = 38.0% [31.6%, 44.9%] | 139/200 = 69.5% [62.8%, 75.5%] | 1.00 |
| 1.6957 | 78/200 = 39.0% [32.5%, 45.9%] | 141/200 = 70.5% [63.8%, 76.4%] | 0.67 |

**The randomisation caveat, stated before a reviewer states it.** A randomised rule
-- flag a ceiling item with probability p, otherwise never fire -- does reach any FPR
on the CHORD between two adjacent points. At a 5% budget that means p = 0.526 and a TPR of
14.5%. So the interpolated ROC curve is not
*unachievable*; the claim is narrower and survives:

1. Every **deterministic** operating point -- the only kind anyone deploys, and the
   only kind under which the same input reliably gets the same decision -- is one of
   the 29 rows in section 1. A hallucination guard that flags a
   response on a coin flip is not a policy an operator can be held to, cannot be
   audited, and is not what any deployment of this detector does.
2. On the chord the operator pays the *average* of an indivisible block. The chord
   from (0, 0) to (0.095, 0.275) has slope 2.89; a score that resolved the ceiling atom would
   let the operator spend that budget on its most informative members instead. The
   lost area is exactly what granularity costs.
3. Randomisation cannot invent a point below the chord's left end either: at any FPR
   the achievable TPR is capped by the upper convex hull of these 29
   points, and below 9.5% FPR that hull is a single straight line out of the origin.

## 5. The other two populations, and which one to report

**The 400-item fair pool has the SAME grid.** FPR is defined conditionally on the
negatives, so pooling the 200 hallucinating targets back in changes nothing about it;
the correct stratum IS the FPR population. What the other 200 supply is the TPR
column, which is already in section 1. There is no separate "n=400 FPR grid" to
report, and a paper that reported one would be reporting a prevalence-weighted
quantity under an FPR label.

**The full labelled pool (n=2000) at natural prevalence.** Its negatives are the
1424 correct answers (prevalence of hallucination 28.8%, 576/2000).
The fair pool's correct stratum is a strict subset of these, so this estimates the
SAME parameter with 7x the negatives -- which is what makes it the control that
matters here: at n=200 the empirical grid cannot resolve FPR steps below 0.5%, so a
sceptic can ask whether the coarseness at the top is just the sampling resolution.
It is not. At n=1424 the resolution is 0.07% and the gap is
unchanged:

| population | n negatives | resolution 1/n | lowest firing FPR | next FPR | gap | gap / resolution |
| --- | --- | --- | --- | --- | --- | --- |
| fair pool, correct stratum | 200 | 0.50% | **9.50%** [6.2%, 14.4%] | 21.50% | 12.00% | 24x |
| full labelled pool, correct stratum | 1424 | 0.07% | **10.53%** [9.0%, 12.2%] | 21.28% | 10.74% | 153x |

The lowest firing operating point sits at 150/1424 = 10.5% [9.0%, 12.2%] on the n=1424 negatives, against
19/200 = 9.5% [6.2%, 14.4%] on the nested n=200. The two agree; the
n=1424 interval is the one that pins the parameter, and its lower bound
**9.0%** rules out a 5% operating point
decisively.

It also **moves the 10% verdict**, which is the one place the two populations
disagree operationally and the reason the superset is worth carrying:

| target FPR | fair pool, n=200: budget honourable? | full pool, n=1424: budget honourable? | rate achievable on either? |
| --- | --- | --- | --- |
| 1% | no -- flags nothing | no -- flags nothing | **no** |
| 5% | no -- flags nothing | no -- flags nothing | **no** |
| 10% | yes, at 9.50% | no -- flags nothing | **no** |
| 20% | yes, at 9.50% | yes, at 10.53% | **no** |

At n=200 a 10% budget scrapes in at 9.5%; at n=1424 the floor is 10.53% and the same
budget cannot be honoured at all. The 95% intervals overlap, so this is not a
contradiction -- it is the parameter sitting within half a point of 10% and the
smaller sample landing on the lucky side. Report it that way: **the floor is about
one correct answer in ten, and a 10% budget is on the boundary of feasibility.** The
5% claim needs no such hedging on either population.

**Prevalence changes the consequences, not the grid.** At the natural rate the
operator's experience of the same operating point is:

| operating point | FPR | TPR | alerts per 1000 questions | precision (PPV) | hallucinations missed per 1000 |
| --- | --- | --- | --- | --- | --- |
| tau = 2.3026 | 10.5% | 25.2% | 148 | 145/295 = 49.2% [43.5%, 54.8%] | 216 |
| tau = 2.1640 | 21.3% | 43.9% | 278 | 253/556 = 45.5% [41.4%, 49.7%] | 162 |
| tau = 2.0253 | 25.3% | 50.2% | 324 | 289/649 = 44.5% [40.7%, 48.4%] | 144 |
| tau = inf (never fire) | 0.0% | 0.0% | 0 | - | 288 |

**Which to report.** The fair pool's correct stratum, n=200, as the headline: it is
the population `paper/sections/methods.tex` already commits to for any statement
about the detector, it is the population of the clean AUROC 0.704, and the false-alarm
arm's 80 targets are a prefix of it. Carry the n=1424 superset in a footnote as the
precision check, because it is what turns "5% is unavailable on our sample" into
"5% is unavailable, full stop". Do NOT report an FPR grid for the pooled n=400 or
the pooled n=2000: FPR is a within-negatives quantity and pooling only invites the
reader to read a prevalence-weighted number as a false-alarm rate.

## 6. Rounding control (the one knob that could have manufactured this result)

The entropy sum accumulates ~1e-16 of float noise, so two scores that are the SAME
attainable value can compare unequal. `attainable_fprs` deduplicates EXACTLY and by
design -- its reported rate has to be the rate the `>=` rule realises -- so raw
float64 input **fabricates operating points**, each 1/n of FPR apart. That is the one
direction that could make this grid look usably fine, so scores are rounded to 9 dp
(1e-9 nats) before anything touches them; the smallest gap in the N=10 lattice is
2.90e-03 nats, so rounding cannot merge two real values either.

| | distinct firing thresholds | of them above 0.9 x ln 10 | distinct float values at the ceiling |
| --- | --- | --- | --- |
| raw float64 | 36 | **2** | 1 |
| rounded to 9 dp | 28 | **2** | 1 |

**The headline is not a rounding artefact, and the check says so in the awkward
direction.** Raw float64 does fabricate 8 extra operating points on this stratum --
but none of them is near the top: it splits 8 attainable values, the highest at an
FPR of 26.5%, and the two top-decile values are each bit-identical across every
item that carries them (the ceiling is `-10 x (0.1 ln 0.1)`, evaluated the same way
every time). So the grid `0% -> 9.5% -> 21.5%` is what you get with or without rounding, and
the rounding choice only affects the middle of the scale, which no claim rests on.
Every number in this file is nonetheless on the rounded column; the 8 extra points
are noise, and reporting them would overstate the detector's resolution.

## 7. Does N=20 fix it? What the lattice settles, and what only data can

**Settled by enumeration, no data needed.** The lattice grows from 39
attainable values at N=10 to **455** at N=20 (12x), but the top tenth of the
range goes only from **2** points to **7**. The top of the
scale is where the lattice is sparsest at either budget. In absolute nats the gap
below the cap shrinks from 0.1386 (N=10) to 0.0693 (N=20); as a share of the range,
from 6.0% to 2.3%. The seven top-decile values at N=20 are 2.7185, 2.7616, 2.7878, 2.8309, 2.8571, 2.9264, 2.9957.

**Also settled, and it is the useful half.** The minimum non-zero achievable FPR is
P(a clean correct answer yields N mutually distinct meanings), and that probability is
**non-increasing in N**: couple the two budgets by taking the N=10 sample to be the
first 10 of the N=20 draw. If all 20 are pairwise inequivalent then so are any 10 of
them (greedy bidirectional-entailment clustering assigns singletons to a subset
whenever it does to the superset, in the same order), so {saturate at 20} is contained
in {saturate at 10}. Marginally, the first 10 of an i.i.d. draw of 20 have the law of an
i.i.d. draw of 10, hence

        min non-zero FPR at N=20  <=  min non-zero FPR at N=10  = 10.5% [9.0%, 12.2%].

So raising N can only help, and the floor on the operator's false-alarm rate is a
statement about how often the model answers a question 20 different ways -- a property
of the LM and the question distribution, not of the estimator's arithmetic.

**NOT settled, and no reasoning substitutes for the data.** Whether the grid becomes
*usably* fine near the operating region depends entirely on how negative mass
distributes over those seven top-decile values, and that is unmeasured. The lattice
bounds the number of thresholds in the top decile at seven; it says nothing about
their FPRs. The two extremes are both consistent with everything above: mass could
spread evenly (a usable ~1-2% grid) or stay concentrated on the cap (a 5% floor and a
single jump, i.e. the same pathology one budget along). We have no N=20 fair-pool
scores, so we cannot choose between them.

**The one N=20 clean measurement in the repo, and why it is not admissible here.**
`results/pilot_n20_ckpt_def.jsonl` re-scored 15 targets at N=20 and recorded their
clean `entropy_before_new`; 1 of 15 sits at ln 20 = 2.9957. Three reasons that is not
an estimate of the N=20 ceiling atom: (a) the 15 were selected because their
*attacked* N=10 score hit the cap -- selection on a score, on the attacked side, which
is exactly the selection the fair pool exists to avoid; (b) n=15 gives a Wilson
interval of [1.2%, 29.8%] around 6.7%, which contains almost everything that matters, including
both 1% and 10%; (c) it is a single seed. Directionally it is consistent with the
monotonicity above and with the atom not vanishing. It settles nothing.

**What would settle it:** clean N=20 scores on the fair pool's 200-target correct
stratum -- the same ids, the same seed discipline, nothing else changed. That is one
GPU pass over 200 questions at twice the sample budget, and it converts every
"cannot conclude" in this section into a number. Until then the honest claim is the
N=10 one, plus "N=20 can only lower the floor, by an amount we have not measured".

## 8. Recommended paper wording

Replaces the top-decile sentence wherever it appears (abstract, introduction
contribution (1), discussion, conclusion). Numbers are the fair pool, correct
stratum, n=200; the parenthetical is the n=1424 superset.
Copy-pasteable LaTeX -- every `%` is escaped, so it will not silently eat a line.

```latex
Semantic entropy over $N$ sampled answers is the entropy of a partition of $N$, so at
the standard $N{=}10$ it lives on a lattice of $39$ attainable values with an atom at
the maximum $\ln 10$. A detector that flags when the score reaches a threshold can
therefore be operated only at a finite list of false-alarm rates, and the list is short
exactly where an operator needs it: on a score-independent pool of $200$ correct answers
scored clean, the only achievable clean false-positive rates below one in four are
$0\%$, $9.5\%$ [6.2, 14.4] and $21.5\%$ [16.4, 27.7]. An operator who
specifies a $5\%$ false-alarm budget cannot have one: the only threshold that
honours it flags nothing at all. The nearest operating point that fires runs at
$9.5\%$ and catches $27.5\%$ [21.8, 34.1] of hallucinations; the next runs at
$21.5\%$ for $44.5\%$. The minimum non-zero false-positive rate is not a tuning
choice but the mass of the ceiling atom itself, since every threshold above $\ln N$
flags nothing ($10.5\%$ [9.0, 12.2] on the $1424$-answer superset). This is the score
granularity gap of \citet{sun2026granularity} -- a score that ranks acceptably while
leaving an operator only a handful of usable thresholds -- instantiated for a
sampling-based detector, where the lattice is fixed by the sample budget. Raising that
budget can only lower the floor, since the event ``all $N$ answers distinct'' shrinks
with $N$; $N{=}20$ affords $455$ attainable values, $7$ of them in the top tenth of the
range. Whether that makes the achievable grid usably fine near the operating region we
have not measured.
```

Notes for whoever edits the .tex:

- The top-decile cut can go entirely. Everything it was carrying is carried better by
  the grid, in units an operator uses, with no arbitrary constant.
- Keep the lattice counts (39, 455, and 2 vs 7 in the top decile): they are
  enumeration, they need no population, and section 7 leans on them.
- Do not write "the ROC curve is a lie". Write "the achievable operating points are
  a finite set"; the chords between them are reachable by randomisation and a
  reviewer will say so (section 4).
- Do not write that the detector cannot be operated at 10%. The data excludes 5% [Wilson
  lower bound 9.0% on n=1424]; for 10% the two populations split (section 5) and the
  honest phrasing is "about one correct answer in ten", not a bare inequality.
- The abstract currently spends two sentences on the top decile and on 21.5% of
  correct answers occupying one of two points. Both are the same fact as the grid,
  and the grid says it in an operator's units in one sentence, so the space is a
  net gain, not a cost.
- `sun2026granularity`'s own phrase ("only a handful of usable thresholds") is worth
  quoting at the point where the count table in section 1 lands.

## Appendix A. The full grid on the n=1424 superset

The same enumeration on the full labelled pool's correct stratum, with TPR on its
576 hallucinating answers. Reported in full so the coarseness at the top can be
checked against a population where the sampling resolution is 0.07%, not 0.5%.

| # | threshold tau (nats) | FPR | TPR |
| --- | --- | --- | --- |
| 0 | inf (never fire) | 0/1424 = 0.0% (exact: the policy never fires) | 0/576 = 0.0% (exact: the policy never fires) |
| 1 | 2.302585 | 150/1424 = 10.5% [9.0%, 12.2%] | 145/576 = 25.2% [21.8%, 28.9%] |
| 2 | 2.163956 | 303/1424 = 21.3% [19.2%, 23.5%] | 253/576 = 43.9% [39.9%, 48.0%] |
| 3 | 2.025326 | 360/1424 = 25.3% [23.1%, 27.6%] | 289/576 = 50.2% [46.1%, 54.2%] |
| 4 | 1.973001 | 431/1424 = 30.3% [27.9%, 32.7%] | 336/576 = 58.3% [54.3%, 62.3%] |
| 5 | 1.886697 | 437/1424 = 30.7% [28.3%, 33.1%] | 344/576 = 59.7% [55.7%, 63.7%] |
| 6 | 1.834372 | 494/1424 = 34.7% [32.3%, 37.2%] | 364/576 = 63.2% [59.2%, 67.0%] |
| 7 | 1.748067 | 577/1424 = 40.5% [38.0%, 43.1%] | 400/576 = 69.4% [65.6%, 73.1%] |
| 8 | 1.695743 | 591/1424 = 41.5% [39.0%, 44.1%] | 405/576 = 70.3% [66.5%, 73.9%] |
| 9 | 1.643418 | 608/1424 = 42.7% [40.2%, 45.3%] | 409/576 = 71.0% [67.2%, 74.6%] |
| 10 | 1.609438 | 668/1424 = 46.9% [44.3%, 49.5%] | 428/576 = 74.3% [70.6%, 77.7%] |
| 11 | 1.504788 | 677/1424 = 47.5% [45.0%, 50.1%] | 429/576 = 74.5% [70.8%, 77.9%] |
| 12 | 1.497866 | 761/1424 = 53.4% [50.8%, 56.0%] | 460/576 = 79.9% [76.4%, 82.9%] |
| 13 | 1.470808 | 766/1424 = 53.8% [51.2%, 56.4%] | 465/576 = 80.7% [77.3%, 83.7%] |
| 14 | 1.418484 | 786/1424 = 55.2% [52.6%, 57.8%] | 473/576 = 82.1% [78.8%, 85.0%] |
| 15 | 1.359237 | 833/1424 = 58.5% [55.9%, 61.0%] | 481/576 = 83.5% [80.3%, 86.3%] |
| 16 | 1.279854 | 838/1424 = 58.8% [56.3%, 61.4%] | 487/576 = 84.5% [81.4%, 87.3%] |
| 17 | 1.227529 | 922/1424 = 64.7% [62.2%, 67.2%] | 514/576 = 89.2% [86.4%, 91.5%] |
| 18 | 1.220607 | 928/1424 = 65.2% [62.7%, 67.6%] | 515/576 = 89.4% [86.6%, 91.7%] |
| 19 | 1.193550 | 936/1424 = 65.7% [63.2%, 68.2%] | 517/576 = 89.8% [87.0%, 92.0%] |
| 20 | 1.168282 | 953/1424 = 66.9% [64.4%, 69.3%] | 520/576 = 90.3% [87.6%, 92.4%] |
| 21 | 1.088900 | 997/1424 = 70.0% [67.6%, 72.3%] | 530/576 = 92.0% [89.5%, 94.0%] |
| 22 | 1.054920 | 999/1424 = 70.2% [67.7%, 72.5%] | 530/576 = 92.0% [89.5%, 94.0%] |
| 23 | 1.029653 | 1000/1424 = 70.2% [67.8%, 72.5%] | 530/576 = 92.0% [89.5%, 94.0%] |
| 24 | 0.943348 | 1009/1424 = 70.9% [68.4%, 73.2%] | 533/576 = 92.5% [90.1%, 94.4%] |
| 25 | 0.940448 | 1082/1424 = 76.0% [73.7%, 78.1%] | 553/576 = 96.0% [94.1%, 97.3%] |
| 26 | 0.897946 | 1102/1424 = 77.4% [75.1%, 79.5%] | 553/576 = 96.0% [94.1%, 97.3%] |
| 27 | 0.801819 | 1125/1424 = 79.0% [76.8%, 81.0%] | 557/576 = 96.7% [94.9%, 97.9%] |
| 28 | 0.693147 | 1127/1424 = 79.1% [77.0%, 81.2%] | 557/576 = 96.7% [94.9%, 97.9%] |
| 29 | 0.673012 | 1129/1424 = 79.3% [77.1%, 81.3%] | 557/576 = 96.7% [94.9%, 97.9%] |
| 30 | 0.639032 | 1203/1424 = 84.5% [82.5%, 86.3%] | 565/576 = 98.1% [96.6%, 98.9%] |
| 31 | 0.610864 | 1211/1424 = 85.0% [83.1%, 86.8%] | 567/576 = 98.4% [97.1%, 99.2%] |
| 32 | 0.500402 | 1230/1424 = 86.4% [84.5%, 88.1%] | 568/576 = 98.6% [97.3%, 99.3%] |
| 33 | 0.325083 | 1342/1424 = 94.2% [92.9%, 95.3%] | 574/576 = 99.7% [98.7%, 99.9%] |
| 34 | 0.000000 | 1424/1424 = 100.0% [99.7%, 100.0%] | 576/576 = 100.0% [99.3%, 100.0%] |

## Appendix B. Provenance and reproduction

- labels: `\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research\samples\wk4_full_2000q\relabeled.jsonl`
- fair pool ids: `select_stratified(want, 200, seed=0)`, via
  `scripts/fair_pool_granularity.fair_pool_ids` (the same ids as the clean AUROC)
- threshold rule: `se.stats.attainable_fprs`, `se.stats.operating_point` (fixed 2026-08-13)
- every reported achieved FPR is asserted equal to `mean(negatives >= tau)` at runtime
- intervals: Wilson score, 95%, from `scripts/fair_pool_granularity.wilson`
- regenerate: `.venv\Scripts\python.exe scripts\achievable_fpr_grid.py` (Windows, reads the
  cache over the WSL UNC share) or `./.venv-wsl/bin/python scripts/achievable_fpr_grid.py`
- unit tests: `tests/test_achievable_fpr_grid.py` (cache-free; asserts the minimum-non-zero-FPR
  identity, grid monotonicity, and the `at_most` contract under a ceiling atom)

