# Budget scaling of the achievable-FPR grid: measured

Generated 2026-08-19 by `scripts/n_scaling_grid.py`.
Budgets measured directly: [40]. Budgets derived by replaying the
recorded pairwise verdicts on random subsets: everything else below.

## 1. Floor and grid, by budget

**The floor is the first firing point, which is not always the ceiling atom.**
Every threshold above ln N flags nothing, so while targets remain AT the cap the
first threshold that fires flags exactly those targets and the floor equals the
at-cap mass. Once the atom empties, that identity breaks: the floor is then set by
the largest score strictly below the cap and is strictly LARGER than the at-cap
mass, which is 0. The two are reported in separate columns for that reason -- read
the floor column, not the at-cap column, for the smallest false-alarm rate an
operator can actually buy at this budget.

| budget N | source | n negatives | floor = min non-zero FPR (1st firing point) | at-cap mass (targets at the ln N ceiling) | next FPR (2nd firing point) | firing points at or below 5% | at or below 10% | at or below 25% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | Week-4 cache | 200 | 19/200 = 9.5% [6.2%, 14.4%] | 19/200 = 9.5% [6.2%, 14.4%] | 21.5% | 0 | 1 | 2 |
| 20 | replay of N=40, replicate 0 | 200 | 6/200 = 3.0% [1.4%, 6.4%] | 6/200 = 3.0% [1.4%, 6.4%] | 7.5% | 1 | 4 | 19 |
| 40 | measured | 200 | 4/200 = 2.0%, no interval (see below) | 0/200 = 0.0% [0.0%, 1.9%] | 2.5% | 5 | 14 | 43 |

At N=40 the ceiling atom is empty (0/200 = 0.0% [0.0%, 1.9%]), so the floor and the at-cap mass
come apart: the smallest purchasable false-alarm rate is 2.0%, NOT 0. There is
no sub-2.0% operating point at this budget.

**And the floor at N=40 is printed WITHOUT an interval, which is a finding
rather than an omission.** The same event that separates these two columns --
the empty atom -- also breaks the floor as an estimand. Its threshold is no
longer ln N, fixed in advance, but the top score this pool happened to reach,
and that rung is not the top of the population's support: a larger pool
reaches a higher one and reports a SMALLER floor, so the quantity moves with
the pool rather than holding still to be estimated. Measured coverage at a
nominal 95%, against a population model validated out-of-sample on the two
smaller budgets in this table: Wilson on the first-firing count 53.7%, a
question bootstrap over the questions 0.00%. Each also has an endpoint placed
by construction -- the bootstrap cannot return less than 1 negative in n, and
Wilson counts a rung the population may not have. Neither is quotable.
`results/n40_floor_estimator_ruling.md` settles this; the at-cap column is
the one that keeps an interval, because ln N really is fixed a priori.

**The replayed rows are ONE subset draw, and the paper quotes a different
estimator.** Every row above marked `replicate 0` is a single uniformly random
subset per question. Its Wilson interval is the correct interval FOR THAT
estimator, and not a narrow one: by the variance identity in
`results/replay_control.md` section 2b, a single replicate's binomial
spread already contains the subset draw as well as the draw of questions, so
nothing is missing from it and nothing may be added to it. But a single
replicate is not what the paper reports. The paper reports the subset-AVERAGED
floor -- the mean of the 200 per-question saturation probabilities -- whose
interval is a bootstrap over questions ONLY, because the subset draw has been
averaged out of the point estimate and putting it back would count it twice.

- N=20: this report's replicate 0 reads 6/200 = 3.0% [1.4%, 6.4%]. The quotable
  subset-averaged floor is **3.1% [1.8%, 4.7%]**, by question bootstrap, from
  `results/replay_control.md` section 2b as of 2026-08-19.
  Quote that one, from that file. The two point estimates are
  near-identical and their intervals are not, so a row lifted from here
  would carry the wrong width for the wrong estimator.

**The subsetting control.** Everything at a budget below the one actually run
is a replay of random subsets, so the method has to be checked against a
directly measured grid at the same budget. The Week-4 cache is exactly that at
N=10.

- Week-4 cache, direct N=10 (June generation run): floor = 19/200 = 9.5% [6.2%, 14.4%]
- replay of 10-subsets of the N=40 run (August), 20 replicates: floor median 12.0%, range 10.0%-14.5%

**These two arms do not disagree -- and a gap between them would not have
condemned the replay.** This block used to close with a decision rule: if the
arms disagree beyond the Wilson interval the subsetting is unsound and no
replayed budget in this report may be quoted. That rule is WITHDRAWN. It was
applied, it read 20 replicates all landing above the direct value as a sign
test at 2^-20, and the inference does not hold. `results/replay_control.md`
sections 1 and 3 redo this control at 200 draws and give the account that
replaces it:

1. **The replay estimator is unbiased, and that is a theorem rather than a
   hope.** A question's samples are i.i.d. and therefore exchangeable, so a
   uniformly random 10-subset of the recorded 40 has exactly the distribution
   of 10 i.i.d. draws; and the clusterer is union-find over PAIRWISE
   verdicts, so a subset's clustering depends only on the verdicts inside it
   and is exactly what a direct 10-sample run on those samples would have
   produced. E[replayed score] = E[direct score], question by question.
2. **Reusing one verdict matrix correlates the replicates; it does not bias
   their mean.** Every replicate conditions on the same 40 samples and the
   same 200 questions, so the spread across replicates is subset-draw noise
   about a CONDITIONAL MEAN. The retired sign test's null was that each
   replicate is an independent coin flip about the direct value. They are
   neither independent nor centred there, and they do not have to be: the
   direct value is itself one draw of a 10-sample run. It sits in the LOWER
   TAIL of the replicate distribution and well inside it, so a unanimous run
   of 20 is unremarkable: a probability of a few tenths, which
   `results/replay_control.md` section 1 measures at 0.36 -- not 2^-20. And
   the correlation between replicates pushes that number UP, not down.
3. **The two arms estimate different parameters, so neither is the odd one
   out.** The replay is unbiased for the generation run recorded in THIS
   checkpoint (August); the direct cache is one unbiased realisation of the
   run that produced it (June). Those two runs differ measurably in the text
   they emitted under an identical config -- mean answer length +3.6 chars
   paired, z = +4.0. Two unbiased estimators of two different parameters is
   not one sound arm and one unsound arm, and which of them is "sounder"
   stops being a statistical question at that point.

So what this control licenses is a LABELLING rule, not a gate: report a
budget trend entirely inside one family and say which family, and keep the
direct N=10 row on its June provenance wherever the paper quotes it -- every
other N=10 number in the paper is welded to that cache. Read
`results/replay_control.md` before quoting any comparison ACROSS the two
arms; the step between them, its interval and its two candidate causes are
that file's subject and not this one's.

## 2. The ceiling atom against the sample budget (the curve the paper needs)

Exact per target, not an extrapolation: a set of samples is all-singletons iff
no pair inside it is equivalent, so the recorded verdict matrix answers it for
every subset size directly.

| budget k | 2 | 3 | 5 | 10 | 15 | 20 | 30 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| correct (n=200) | 0.721 | 0.521 | 0.300 | 0.120 | 0.060 | 0.031 | 0.007 | 0.000 |
| hallucinating (n=200) | 0.905 | 0.792 | 0.580 | 0.277 | 0.147 | 0.085 | 0.039 | 0.025 |

The `correct` row is the AT-CAP MASS as a function of the sample budget, which
is the achievable-FPR floor only while the atom is non-empty. Where the row
reads 0.000 the atom has emptied and the floor is strictly larger -- take the
floor from the floor column of section 1, never from this row. Compare it
against the pre-registered prediction in `results/n_scaling_plan.md` section 5
before writing any prose about it.

## 3. The operator's menu at each budget

| budget | target FPR | `at_most` achieved | TPR | `closest` achieved | TPR |
| --- | --- | --- | --- | --- | --- |
| 10 | 1% | 0.0% (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% |
| 10 | 5% | 0.0% (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% |
| 10 | 10% | 9.5% | 27.5% | 9.5% | 27.5% |
| 10 | 20% | 9.5% | 27.5% | 21.5% **over budget** | 44.5% |
| 20 | 1% | 0.0% (flags nothing) | 0.0% | 3.0% **over budget** | 9.5% |
| 20 | 5% | 3.0% | 9.5% | 3.0% | 9.5% |
| 20 | 10% | 10.0% | 25.5% | 10.0% | 25.5% |
| 20 | 20% | 19.0% | 42.5% | 20.5% **over budget** | 44.0% |
| 40 | 1% | 0.0% (flags nothing) | 0.0% | 2.0% **over budget** | 6.0% |
| 40 | 5% | 5.0% | 11.0% | 5.0% | 11.0% |
| 40 | 10% | 10.0% | 24.0% | 10.0% | 24.0% |
| 40 | 20% | 20.0% | 44.5% | 20.0% | 44.5% |

## 4. Measured throughput (this replaces every cost estimate that preceded it)

| N | evals | median s/eval | median s in NLI | model predicted | ratio |
| --- | --- | --- | --- | --- | --- |
| 40 | 400 | 46.7 | 33.5 | 73.9 | 0.63x |

- measured, N=40: n=400 evals -> 5.19 GPU-h [46.7 s/eval]

## 5. Provenance

- checkpoint: `I:\GITHUBPROJECTS\SE Research\results\n_scaling_ckpt.jsonl` (400 evaluations)
- ids: fair pool, `select_stratified(want, 200, seed=0)`
- generation: max_new_tokens=48, T=1.0, top_p=1.0, seed=0
- plan, cost model and the derivations that need no data: `results/n_scaling_plan.md`
- the replay control -- what the subsetting does, which interval belongs to which
  estimator, and the subset-averaged floors the paper actually quotes: `results/replay_control.md`

