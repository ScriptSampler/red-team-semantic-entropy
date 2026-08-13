# Budget scaling of the achievable-FPR grid: the plan, the cost, and everything
# that needs no new data

Generated 2026-08-13 by `scripts/n_scaling_grid.py --derive-only` (CPU only; no GPU, no model, no attack data).

`results/achievable_fpr_grid.md` measures the operator's menu at ONE sample
budget: at N=10 the achievable clean false-alarm rates below one in four are
0% -> 9.5% -> 21.5%, so a 5% budget cannot be honoured by any firing threshold.
Its section 7 concedes the rebuttal -- *just raise N* -- and admits the concession
is unmeasured. This file is the design, the price and the free half of the
answer.

## 1. The design, and the one thing that makes it cheap

Clean side only: no attack, no judge, no null control, no hide arm. Population:
the score-independent fair pool, `select_stratified(want, 200, seed=0)` -- correct stratum as the negatives (n=200),
hallucinating stratum as the positives (n=200) that supply TPR at each achievable point.
Generation settings are the Week-4 ones and are PINNED: max_new_tokens=48,
T=1.0, top_p=1.0, seed=0. **N is the only thing that changes.**

**One pass at the largest budget yields every smaller budget, exactly.** The
clusterer is union-find over PAIRWISE bidirectional entailment, so the clustering
of a subset of the samples is fixed by the verdicts inside that subset. The run
records the full C(N,2) verdict matrix per target, so the score at any k <= N is
recomputable with zero GPU by replaying those verdicts through the very same
`se.entropy.cluster_samples`. And a k-subset of an i.i.d. N-draw is an i.i.d.
k-draw, so the subset-derived grid at budget k estimates exactly what a direct
k-run would estimate.

Three consequences, and the third is the reason to trust the first two:

1. Buy N=40 once and the whole curve k = 2..40 comes free, not three points.
2. Repeating the subset draw re-runs the entire experiment at zero cost, so the
   grid comes with a subset-choice spread as well as a Wilson interval.
3. **The N=10 cache is the control.** The subset-derived N=10 grid must reproduce
   the cached one within sampling error. If it does not, the subsetting is
   unsound and the run says so before any N=20/40 number is quoted.

Residual caveats, stated up front: subset replicates share one underlying draw, so
their spread understates fresh-sampling variance (the Wilson interval over targets
stays the headline uncertainty); and per-target resolution degrades as k
approaches N (at k=N/2 a target supplies only two disjoint subsets). Neither
biases the population estimate.

## 2. Cost, honestly

Measured anchors, every one of them read out of an artifact in this repo:

- `T_Q_N10_WITH_GREEDY = 12.70 s/question -- results/run_all.log, wk4_sample.py sustained over 1907 questions (12.51-12.80 s/Q); includes one greedy generation and an fsync per question`
- `T_GREEDY_1SEQ       = 1.49 s -- results/pipeline_check.md, mean over 10 greedy answers (batch of 1)`
- `T_GEN_N10           = 11.21 s -- the N=10 sample batch alone, by subtraction`
- `T_NLI_N10           = 1.75 s/question -- results/run_all_status.txt, wk4_cluster.py did 2000 questions in 3509 s; cross-checked at 1.84 s/Q on 50 questions in results/wk3_fri_entropy.md`

Two reconciliations, because three different per-eval figures are quotable from
this repo and they are not the same number:

- **"12.7 s" is the SAMPLING LOOP, not an SE evaluation.** `wk4_sample.py` also
  generates one greedy answer per question and fsyncs a JSONL line. A clean SE
  evaluation at N=10 is the 10-sample batch plus the clustering: **13.0 s**. The two
  differ by about 5%, but only one of them is the unit this experiment buys.
- **`results/null_objective_ablation_plan.md` section 6 implies ~2.8 s per SE
  eval**, by splitting a 3.26 s objective call across its generated tokens. That
  cannot be reconciled with a directly measured 11.2 s for the same 480 generated
  tokens, and the live hide cell's 568-607 s/target divides by 13.0 s into 44-47
  SE evals per target -- inside that same file's own estimate of 22-58 distinct
  feasible strings. So the direct measurement is the one used here. If the 2.8 s
  attribution were right instead, every figure below is ~4x too high and the buy
  gets cheaper; the error runs in the safe direction, and the run measures its own
  throughput from the first target anyway. (Flagged, not edited: that file belongs
  to another workstream.)

### Per-evaluation cost, by sample budget

Semantic entropy at budget N costs one batched generation of N sequences plus
N(N-1) DeBERTa forward passes (C(N,2) pairs, both directions). The second term is
**exactly quadratic**, so N=40 is not four times N=10 -- the clustering alone is
17.3x.

| N | generation (s) | NLI passes | NLI (s) | total per eval (s) | x N=10 | linear-in-N would be |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 11.2 | 90 | 1.8 | **13.0** | 1.00x | 1.0x |
| 20 | 22.0 | 380 | 7.4 | **29.4** | 2.27x | 2.0x |
| 40 | 43.6 | 1560 | 30.3 | **73.9** | 5.71x | 4.0x |

Generation scaling is bracketed, because this repo has never measured a batch
wider than 20. The bracket is named and both ends are stated:

| N | amortised (optimistic) | linear (central) | loaded (pessimistic) |
| --- | --- | --- | --- |
| 10 | 13.0 s | **13.0 s** | 13.0 s |
| 20 | 19.7 s | **29.4 s** | 33.8 s |
| 40 | 43.8 s | **73.9 s** | 93.1 s |

### What a configuration costs

- N=10: **free** -- re-derived from the Week-4 cache (`samples/wk4_full_2000q/entropy.jsonl`), which was produced at exactly these generation settings. n=200 negatives, 0.00 GPU-h.
- N=20, correct stratum only (the FPR grid and the floor): n=200 evals -> 1.63 GPU-h [29.4 s/eval]
- N=20, both strata (adds TPR at every achievable point): n=400 evals -> 3.27 GPU-h [29.4 s/eval]
- N=40, correct stratum only (the FPR grid and the floor): n=200 evals -> 4.11 GPU-h [73.9 s/eval]
- N=40, both strata (adds TPR at every achievable point): n=400 evals -> 8.22 GPU-h [73.9 s/eval]

- ALL budgets measured directly, both strata: n=800 evals -> 11.48 GPU-h [51.7 s/eval]  (one pass per budget)
- the recommended buy: ONE pass at N=40, both strata: n=400 evals -> 8.22 GPU-h [73.9 s/eval]  (every budget k <= 40 then comes free by replay)

Saving from buying only the top budget: **3.3 GPU-h** (n=400 evals avoided), and the replay gives every k in between rather than three isolated points.

VRAM is not a constraint. The KV cache for Llama-3.1-8B is ~131 kB/token
(32 layers x 8 KV heads x 128 dims x 2 tensors x 2 bytes), so a batch of 40
sequences over a ~40-token prompt plus 48 new tokens holds ~0.46 GB against
~0.12 GB at N=10 -- an extra ~0.35 GB on a 16 GB card that peaked at 5.8 GB
during the Week-4 N=10 run (`results/pipeline_check.md`).

**Against the queue.** 33 days remain to the 2026-09-15 target, and the
outstanding GPU commitment is the ~67 GPU-h definitive null control plus the
remainder of the hide cell (`docs/START_HERE_overnight.md`).
The recommended buy is 8.2 GPU-h at n=400 evals, i.e. **12% of the null control** and about 0.34 of one day.
It is affordable. The honest risk is not the hours, it is the device: the card is
shared with a multi-day chain, so this must be queued, not raced -- hence
per-target checkpointing and a resume that costs at most one target.

## 3. What the lattice PERMITS, with no data at all

Semantic entropy at budget N is the entropy of a partition of N, so the estimator
can only emit the entropy of an integer partition. That set is finite and
enumerable, and it bounds how good the achievable grid could possibly get.

| N | partitions p(N) | attainable values | in the top tenth of the range | in the top 5% | in the top 1% | last step below the cap (nats) |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 42 | **39** | **2** | 1 | 1 | 0.1386 |
| 20 | 627 | **455** | **7** | 3 | 1 | 0.0693 |
| 40 | 37338 | **14116** | **42** | 10 | 2 | 0.0347 |

**A closed form worth putting in the paper.** The highest attainable value below
the cap is the partition (2,1,...,1), whose entropy is ln N - (2 ln 2)/N. So the
last step of the scale is ALWAYS exactly `2 ln 2 / N` nats wide:
0.1386 at N=10, 0.0693 at N=20, 0.0347 at N=40 -- it shrinks like 1/N while the
lattice as a whole grows superpolynomially. That asymmetry IS the surviving form
of the granularity claim: the scale is sparsest exactly where the false-alarm
claim lives, at every budget.

**The finest FPR spacing the lattice permits** -- an upper bound on the grid's
quality that costs nothing to compute. Two things bound the number of distinct
achievable false-alarm rates: the lattice (FPR can only change at an attainable
score) and the sample (every realised FPR is a multiple of 1/n). The tighter one
binds.

| N | attainable values | n negatives | max distinct FPRs | finest spacing | binding constraint | in the top tenth: max points | finest spacing there |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 39 | 200 | 39 | 2.56% | **lattice** | 2 | 50.00% (lattice) |
| 20 | 455 | 200 | 200 | 0.50% | **sample size** | 7 | 14.29% (lattice) |
| 40 | 14116 | 200 | 200 | 0.50% | **sample size** | 42 | 2.38% (lattice) |

Read that table as the ceiling on what the measurement can find:

- At **N=10** the lattice binds everywhere: 39 values against 200 negatives, so the grid can be no finer than 2.6%, and in the top tenth no finer than 50% of whatever mass lands there. The measured grid (0% -> 9.5% -> 21.5%) is at that limit, not far from it.
- At **N=20** the lattice stops binding globally (455 values > 200 negatives) but still binds at the top: only 7 points in the top tenth, and only 3 in the top twentieth.
- At **N=40** the lattice has stopped binding anywhere that matters: 14116 values, 42 of them in the top tenth. **From N=40 on, the coarseness of the grid can no longer be blamed on the estimator's arithmetic** -- if it is still coarse it is because the population is piled on one value, which is a fact about the language model, not about entropy of a partition.

That is the sharpest thing enumeration alone can say, and it is what makes the
N=40 arm the decisive one: it separates *the estimator cannot express a 5% rate*
from *this model's answers cannot produce one*.

Rounding control, per budget (the N=10 report rounds scores to 9 dp before the
grid is built; that mitigation has to be re-checked at each N because the lattice
gets denser):

| N | smallest gap in the lattice | smallest gap in the top tenth | values merged by 9-dp rounding | of those, in the top tenth |
| --- | --- | --- | --- | --- |
| 10 | 2.90e-03 | 1.39e-01 | 0 | 0 |
| 20 | 1.42e-04 | 2.62e-02 | 0 | 0 |
| 40 | 1.00e-12 | 7.25e-04 | 2 | 0 |

At N=40 two pairs of attainable values fall within 1e-9 of each other and 9-dp
rounding merges them -- but none is in the top tenth, where the smallest gap is
7.3e-04 nats, seven orders of magnitude clear. The mitigation still
points at the real risk (float noise fabricating operating points) and still
cannot destroy a real one anywhere a claim is made.

## 4. The coupling bound: the floor is provably non-increasing in N

The minimum non-zero achievable FPR is the mass of the ceiling atom -- the
probability that a clean correct answer yields N pairwise-inequivalent meanings --
because every threshold above ln N flags nothing and the first one that fires
flags exactly the atom. That probability is non-increasing in N:

> A set of samples is all-singletons iff NO pair inside it is equivalent. A subset
> of a set with no equivalent pair has no equivalent pair. So {all 20 distinct} is
> contained in {the first 10 are distinct}, realisation by realisation. Coupling
> the budgets by "the N=10 draw is the first 10 of the N=20 draw", and using that
> the first 10 of an i.i.d. 20-draw have the law of an i.i.d. 10-draw:
>
>     min non-zero FPR at N=20  <=  min non-zero FPR at N=10.

The containment is exact for ANY clusterer that is union-find over a pairwise
relation -- the deployed NLI one, `cluster_samples_exact`,
`cluster_samples_embedding` and `cluster_samples_judge` all qualify, because each
scores a pair without reference to the rest of the sample set. It would fail for
a clusterer with global structure (k-means, or any rule that reads all N samples
at once), which is worth one sentence in the paper: the bound is a property of
the clustering rule, not a law of nature.

Putting the numbers in, from the N=10 data alone and with no new measurement:

- fair pool, correct stratum: floor(N=20) <= floor(N=40) <= floor(N=10) = 19/200 = 9.5% [6.2%, 14.4%]
- and therefore, at 95% confidence, the floor at every budget above 10 is at most **14.4%** on this population.

That is the whole of what reasoning buys. It is one-directional: it says the floor
cannot rise, and says NOTHING about whether it falls to 5%, to 1% or to 9.4%. The
measurement is the only thing that can, which is exactly the position the
withdrawn non-relaxability claim was in (`results/n20_verdict.md`) -- asserted
from a mechanism instead of measured.

## 5. A pre-registered prediction, free, out of the EXISTING N=10 cache

The N=10 cache stores each target's cluster assignment, and that is enough to
read off how the ceiling atom decays with the sample budget *below* 10 -- which
pins the shape of the curve before a single new sample is drawn.

For a target whose 10 samples fall into clusters of sizes c, the probability that
a uniformly random k-subset lands on k DISTINCT clusters is e_k(c) / C(10, k),
where e_k is the elementary symmetric polynomial -- exact, no Monte Carlo. A
k-subset of an i.i.d. 10-draw is an i.i.d. k-draw, so averaging that over targets
estimates the ceiling-atom mass at budget k.

**Direction of the error, stated before the numbers.** The subset's own clustering
is FINER than the restriction of the full clustering (a merge can travel through a
sample outside the subset), so this counts fewer all-distinct subsets than the
detector would actually produce. Every entry below is a LOWER bound on the atom at
that budget, and any curve fitted to it decays too fast. Both extrapolations
underneath inherit that bias, so they are optimistic about relaxation -- which is
the direction that makes a measured *failure* to relax the more interesting
outcome, not the more suspicious one.

**correct (the negatives -- this is the FPR floor) stratum, n=200**

| budget k | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P(all k distinct) | 0.697 | 0.492 | 0.361 | 0.277 | 0.220 | 0.179 | 0.146 | 0.119 | 0.095 |

**hallucinating (the positives) stratum, n=200**

| budget k | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P(all k distinct) | 0.873 | 0.740 | 0.624 | 0.531 | 0.457 | 0.398 | 0.350 | 0.309 | 0.275 |

The k=10 column is not an estimate -- it is the measured ceiling-atom mass
(19/200 = 9.5% [6.2%, 14.4%] on the correct stratum), so the curve is anchored at
the right-hand end by the number the paper already quotes.

**Two extrapolations, both stated in advance, neither trusted alone.**

1. *Power law in k.* The measured curve is close to a straight line in log P vs
   log k over k = 5..10, which is a much slower decay than independence would
   give. Fit there and extend.
2. *Pairwise Beta-Binomial.* Model each target as having its own per-pair
   equivalence probability q, estimate q from the pairs the clustering merged
   (sum C(c_i,2) of C(10,2)) under a Jeffreys prior, and take the predictive
   E[(1-q)^C(N,2)] per target, averaged over targets. This is the model that says
   'a question that gave 10 distinct answers still has a real chance of giving 20'.

| stratum | budget | power law in k | pairwise Beta-Binomial | coupling upper bound |
| --- | --- | --- | --- | --- |
| correct | N=20 | 3.5% | 5.3% | <= 9.5% |
| correct | N=40 | 1.2% | 2.4% | <= 9.5% |
| hallucinating | N=20 | 14.5% | 13.6% | <= 27.5% |
| hallucinating | N=40 | 7.5% | 6.7% | <= 27.5% |

(The power-law exponent on the correct stratum is -1.52: the atom
falls only like k^-1.52, so a doubling of the budget buys a factor
of 0.35, not the collapse that pairwise independence would
give -- under independence the decay would be exponential in C(k,2), which the data
flatly rejects. The atom is carried by a subpopulation of questions the model
answers differently every single time, not by independent coin flips, and THAT is
the thing a larger budget has to break.)

**The pre-registered prediction, written before the GPU is touched:** on the fair
pool's correct stratum the ceiling-atom mass -- and therefore the minimum non-zero
achievable FPR -- will land at roughly

    N=20:  3.5% to 5.3%   (hard upper bound from the coupling: 9.5%)
    N=40:  1.2% to 2.4%   (hard upper bound from the coupling: 9.5%)

Note what that says: the predicted floor at **N=20** sits ON the 5% boundary the
paper's claim turns on -- the least decidable place it could land, and at n=200
an interval around it would cover 5% either way (section 6).
**N=40** is the budget predicted to clear it, which is why the buy is the larger one.
If the measurement comes in far above this band the prediction is simply wrong and
the paper's claim gets stronger; if it comes in far below, the finding becomes
'here is the budget that buys a 5% false-alarm rate'. Both are results. This
paragraph exists so that neither can be written after the fact.

## 6. What n buys: the precision of the answer, before it is bought

The floor is a proportion, so its Wilson interval is fixed by n and by where the
floor lands. At the predicted values, here is what each pool size can conclude:

| true floor | n=200 (fair pool) | n=400 | n=1424 (full correct stratum) | can n=200 certify 'no 5% operating point'? |
| --- | --- | --- | --- | --- |
| 1.0% | 0.3%-3.6% | 0.4%-2.5% | 0.6%-1.6% | **yes**, upper bound below 5% |
| 1.5% | 0.5%-4.3% | 0.7%-3.2% | 1.0%-2.2% | **yes**, upper bound below 5% |
| 2.0% | 0.8%-5.0% | 1.0%-3.9% | 1.4%-2.8% | no -- interval covers 5% |
| 2.5% | 1.1%-5.7% | 1.4%-4.5% | 1.8%-3.5% | no -- interval covers 5% |
| 3.0% | 1.4%-6.4% | 1.7%-5.2% | 2.2%-4.0% | no -- interval covers 5% |
| 4.0% | 2.0%-7.7% | 2.5%-6.4% | 3.1%-5.2% | no -- interval covers 5% |
| 5.0% | 2.7%-9.0% | 3.3%-7.6% | 4.0%-6.2% | no -- interval covers 5% |
| 7.0% | 4.2%-11.4% | 4.9%-9.9% | 5.8%-8.5% | no -- interval covers 5% |
| 9.5% | 6.2%-14.4% | 7.0%-12.8% | 8.1%-11.1% | no -- interval covers 5% |

The crossover is sharp and worth knowing before the run: at n=200 the Wilson upper
bound clears 5% only when at most **3 of the 200** negatives sit at the cap, i.e. a floor
of **1.5%** or less. Above that the honest report is an interval that covers 5%.

Read this honestly: **n=200 answers the granularity question but not always the
sharp feasibility question.** If the floor lands near 4%, n=200 gives an interval
that still covers 5% and the claim 'a 5% budget is now purchasable' cannot be
made -- while the claim it replaces ('the achievable grid below 25% has more than
three points') is perfectly well resolved at 0.5% steps. Three consequences for
the buy:

- The headline population stays the fair pool's correct stratum, n=200, because
  that is the population `paper/sections/methods.tex` commits to.
- **How many negatives each predicted floor would need**, if the paper wants to
  say 'no operating point at or below 5% exists' rather than quote an interval:

  | budget | predicted floor | n needed to certify (pessimistic end) | n needed (optimistic end) |
  | --- | --- | --- | --- |
  | N=20 | 3.5%-5.3% | unreachable -- too close to 5% | 780 |
  | N=40 | 1.2%-2.4% | 230 | 110 |

  Read that as the honest limit of the n=200 headline: even at the budget whose
  floor is predicted lowest, certifying the 5% statement can need more negatives
  than the fair pool has. Quoting the interval is still a complete answer to the
  granularity question; it is the *feasibility* sentence that needs the extension.
- The extension, if triggered, runs along the SAME seed-0 shuffle
  (`_stratum_ids('right', 0)[:n]`), so it is a strict superset and the fair
  pool stays a prefix of it -- the same nesting discipline
  `results/achievable_fpr_grid.md` uses for its n=1424 companion. The full correct
  stratum has 1424 members, so there is room. Sample costs:
  - 100 further negatives at N=40 (n=300 in total): n=100 evals -> 2.05 GPU-h [73.9 s/eval]
  - 200 further negatives at N=40 (n=400 in total): n=200 evals -> 4.11 GPU-h [73.9 s/eval]
  - 400 further negatives at N=40 (n=600 in total): n=400 evals -> 8.22 GPU-h [73.9 s/eval]

## 7. The move an operator actually has: average k runs

A reviewer will say it, so it goes in the paper: nobody needs a bigger N to
subdivide the grid. Run the N=10 detector k times and average, at k times the
cost. Worked out, and it does not rescue the detector:

| k | average k runs at N=10 | equal-resolution single run | finest step at the top (nats) | cost of averaging | cost of the single run | single run / averaging |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 395 attainable values | N=20, 455 attainable values | 0.0693 | 26 s | 29 s | **1.13x** |
| 3 | 1659 attainable values | N=30, 2982 attainable values | 0.0462 | 39 s | 50 s | **1.28x** |
| 4 | 5186 attainable values | N=40, 14116 attainable values | 0.0347 | 52 s | 74 s | **1.43x** |

**Averaging wins on price and loses on substance.** Both moves divide the last
step of the scale by the same factor -- averaging k runs at budget n gives steps of
(2 ln 2 / n)/k, one run at N = kn gives 2 ln 2/(kn) -- but clustering is quadratic
in the sample count, so k separate n-sized clusterings cost k*n(n-1) NLI passes
against kn(kn-1) for the single wide run. At k=4 that is the difference between
52 s and 74 s per target. Say so in the paper; do not let a reviewer
discover it.

Three things averaging does not buy, and they are the ones the finding rests on:

1. **It does not move the cap.** The maximum stays ln 10 = 2.3026 however many
   runs are averaged. Raising N raises it to ln N. Right-censoring of the
   hallucinating class -- the asymmetry that biases the clean AUROC downward -- is
   untouched by averaging.
2. **It does not dissolve the atom, it only shrinks it toward a hard floor.** The
   averaged score sits at the cap iff EVERY run saturates, so the residual atom is
   E_q[p(q)^k] over the question distribution. By Jensen that is at least (E p)^k,
   and more to the point it converges to the mass of questions the model answers
   10 different ways EVERY time -- a subpopulation averaging can never split,
   because those items are deterministic, not noisy. Section 5's decay curve says
   that subpopulation is exactly what carries the atom.
3. **It does not reduce the estimator's bias.** The plug-in entropy of N samples
   is biased low, and averaging k of them is a variance reduction of the SAME
   biased functional: it converges to E[H_10], not to the semantic entropy.
   Raising N is the only one of the two that attacks the bias, which is the
   mechanism `mccabe2025alphabet` / `pan2026shade` describe.

So the honest paper sentence is: *the grid can be subdivided cheaply by averaging
repeated runs, which is cheaper than raising N and is what an operator should do;
but averaging cannot lower the floor below the mass of questions that saturate
every time, and only a larger N attacks that mass.* Whether it does is section 5's
prediction and this run's measurement.

## 8. Recommendation

1. **Buy one pass at N=40, both strata** -- n=400 evals -> 8.22 GPU-h [73.9 s/eval].
   Every budget k <= 40 then comes free by replay, including N=20 and the N=10
   control, and the deliverable is a curve rather than three points.
2. **Do not buy a separate N=20 pass for the headline.** It is the least decidable
   budget (section 5 predicts it lands on the 5% boundary) and it is recoverable
   from the N=40 pass anyway. Buy instead a **60-target direct N=20 cell** (n=60 evals -> 0.49 GPU-h [29.4 s/eval])
   purely to confirm that the subset-derived N=20 grid matches a directly measured
   one. That is the only thing a direct N=20 run tells you that replay cannot.
3. **Re-derive N=10 from the cache as the control** (free) and additionally
   re-score 40 correct-stratum targets fresh at N=10 (n=40 evals -> 0.14 GPU-h [13.0 s/eval])
   to bound cache-vs-today drift, which no analysis currently rules out.
4. **Hold the negative-stratum extension in reserve, and pre-commit its trigger.**
   Section 6: quoting the floor as an interval needs nothing extra, but SAYING
   'no operating point at or below 5% exists' needs the Wilson upper bound under
   5%, which at n=200 requires at most 3 negatives at the cap (1.5%).
   If the floor lands at the pessimistic end of the N=40 prediction (2.4%), the
   certifying n is ~230, so the extension is 30 further negatives along the
   same seed-0 shuffle: n=30 evals -> 0.62 GPU-h [73.9 s/eval].
   Trigger it on the measured floor, not on a hunch, and write the trigger down
   before the run so the extension cannot be a reaction to an unwelcome interval.
5. **Queue it behind the null control, not against it.** Total for items 1-3 is ~8.8 GPU-h at n=500 evals (worst case 11.1 GPU-h at the same n), against ~67 GPU-h for the
   null control and 33 days remaining. It is affordable; it is not free of the
   device. With item 4 triggered it is at most ~9.5 GPU-h at n=530 evals.

What each outcome licenses, written before the data:

| measured floor at N=40 | what the paper says |
| --- | --- |
| still >= ~9% | the floor is a property of the model's answer distribution, not of the sample budget. The operating-point finding generalises across a 4x budget range and the granularity framing is at its strongest. |
| ~2-5% | the floor is relaxable and the paper reports the budget-response curve: 'at the N this literature uses you cannot buy a 5% false-alarm rate; here is what it costs to buy one'. More useful to a practitioner, and it retires the last of the non-relaxability framing cleanly. |
| < ~1% | granularity is not the operator's problem at N=40; the paper's contribution narrows to the measurement protocol plus the cost curve, and the abstract must say so. |

None of the three is a failure, and the run is worth buying precisely because the
three bands ARE separable at n=200: a 9.5% floor and a 2% floor have disjoint
Wilson intervals there. What n=200 cannot always do is the narrower thing -- put a
one-sided certificate under 5% -- and section 6 prices that separately rather than
letting it quietly become a reason to call the whole run underpowered.

## 9. Reproduction, resume and provenance

```
# cost only, no model load, no cache (prints n on every hours line)
.venv\Scripts\python.exe scripts\n_scaling_grid.py --estimate-only

# this file
.venv\Scripts\python.exe scripts\n_scaling_grid.py --derive-only

# the measurement, inside WSL where the GPU is
./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 40 --strata both

# the same, resumed after a kill: identical command, skips completed targets
./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 40 --strata both

# the N=20 validation cell (does replay match a direct measurement?)
./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 20 --strata correct --limit 60

# the N=10 drift control (is the Week-4 cache still what this box produces?)
./.venv-wsl/bin/python scripts/n_scaling_grid.py --n_samples 10 --strata correct --limit 40

# rebuild every table from the checkpoint, scoring nothing
.venv\Scripts\python.exe scripts\n_scaling_grid.py --report-only

# a dry run of the whole loop with a fake scorer, no GPU and no model
.venv\Scripts\python.exe scripts\n_scaling_grid.py --smoke --limit 25 --checkpoint /tmp/smoke.jsonl
```

- checkpoint: `I:\GITHUBPROJECTS\SE Research\results\n_scaling_ckpt.jsonl` -- one appended, flushed, fsync'd line per
  completed evaluation, keyed by (question_id, N, seed, max_new_tokens). Killing
  the run costs the target in flight and nothing else.
- the checkpoint carries the C(N,2) verdict matrix, so every smaller budget is
  recomputable offline and the run never has to be repeated to answer a question
  about a budget nobody thought to ask for.
- ids: `fair_pool_granularity.fair_pool_ids` (the same ids as the clean AUROC and
  the same ids as `results/achievable_fpr_grid.md`)
- threshold rule: `se.stats.attainable_fprs` / `operating_point` (fixed
  2026-08-13); the grid table itself is `achievable_fpr_grid.grid`, imported, not
  reimplemented
- intervals: Wilson score, 95%, `fair_pool_granularity.wilson`
- Week-4 cache read for the N=10 control: `\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research\samples\wk4_full_2000q`
- tests: `tests/test_n_scaling_grid.py` (CPU only, no cache, no model): the
  lattice counts and the 2 ln 2 / N identity, the subset-replay round trip, the
  coupling containment per realisation, the grid construction at N=20/40, the
  quadratic cost term, checkpoint resume, and the rule that every hours figure
  carries its n

