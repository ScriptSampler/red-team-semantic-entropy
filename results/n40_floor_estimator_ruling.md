# Which interval belongs to the measured N=40 achievable false-alarm floor

Ruling, 2026-08-19. Settled by coverage simulation against a population model fit from the
per-question structure in `results/n_scaling_ckpt.jsonl` and validated out-of-sample against
two measured budgets. CPU only; the live GPU run (WSL `Ubuntu-24.04` PID 473,
`scripts/null_control.py`, 5 h 16 m elapsed at the time of writing) was verified with `ps` and
not touched.

---

## 0. The ruling, first

**Row 1, the N=40 floor.** Print treatment (c): report the row as the ceiling-atom mass,
`0/200 = 0.0% [0.0, 1.9]` by Wilson at the a-priori threshold `ln 40`, and report `2.0%`
beside it as the smallest false-alarm rate a 200-answer pool can *exhibit*, with no confidence
interval attached to it at all -- print neither `[0.8, 5.03]` nor `[0.5, 4.0]` as an interval
for the floor, because both are intervals for a quantity that is not the population floor and
both are measured far below their nominal coverage (Wilson 53.7%, bootstrap 0.00%, at nominal
95%).

**Row 2, the achieved 5%-budget operating point.** Print Wilson, `5.0% [2.7, 9.0]`, and retire
the bootstrap `[2.5, 5.0]` from `results/replay_control.md`'s quotable set: measured coverage
is Wilson 94.4% against bootstrap 54.8%, and the bootstrap's upper endpoint is pinned at the
budget in 100.00% of pools by construction. This is the opposite ruling from row 1 and the
reason is in section 10; the Discussion's rule ("data-selected threshold, therefore bootstrap")
is wrong in both rows, and it is wrong in opposite directions.

**What the Abstract's concession should assert.** Not that the floor's interval does or does
not clear 5%. It should assert that the obstruction itself is gone: at `N=10` the floor is a
full ceiling atom, so the 5% budget is unbuyable at any threshold; at `N=40` the atom is empty
(`0/200`, at most `1.9%`), the identity lapses, and what remains is a limit on *measurement
resolution* -- 200 correct answers cannot exhibit an operating point cheaper than `2.0%` --
not a limit on what the detector can be operated at. The 5%-budget sentence should keep its
current careful phrasing, strengthened by a new finding: fitted on the same 200 answers that
threshold is optimistic by about half a point, running at `5.17%` on fresh data against the
`4.67%` it shows in sample.

The Abstract and Conclusion are therefore closer to right than the Discussion, but for the
wrong reason, and their concession is over-stated in a way that costs the paper a real result.

---

## 1. What I re-derived, and what I took on trust

Re-derived from primary artifacts, independently of the repo's own scripts:

- 400 records in `results/n_scaling_ckpt.jsonl`, 200 `correct`/`n_samples=40` and 200
  `hallucinating`/`n_samples=40`.
- Union-find over the recorded 780-bit upper triangle reproduces every recorded
  `entropy_nats` **bit-for-bit** (max absolute difference `0.0` over 200 records) and every
  recorded `n_clusters` (0 mismatches). The replay path is sound.
- `ln 40 = 3.6888794541139363`; highest score attained `3.6195647360579453`; **0 of 200 at the
  cap**. Confirmed.
- The four tied answers are `qz_3927`, `qz_2135`, `qz_4127`, `qz_3833`, all with block sizes
  `(2, 2, 1^36)` -- the "two coincidental pairs among 40" partition. Confirmed, with a caveat
  in section 2.
- Wilson on `4/200` = `[0.7804%, 5.0287%]`. Confirmed.
- Question bootstrap of the order statistic = `[0.500%, 4.000%]`. Confirmed, and re-derived a
  second way in closed form (section 3).
- The adversarial verifier's two measurements: mass at exactly `1/200` is **7.93%** (verifier
  said 7.96%; my 400k-resample Monte Carlo gives 7.921%, about one standard error away), and
  mass strictly above `4.0%` is **2.020%** (verifier said 2.02%). Both stand.
- The two smaller-budget rows, by my own subset replay of the recorded matrices:
  `N=10` floor `12.002%`, question bootstrap `[8.92%, 15.32%]`; `N=20` floor `3.134%`,
  `[1.79%, 4.69%]`. These match the quoted `12.0% [8.9, 15.3]` and `3.1% [1.8, 4.7]` to the
  printed precision. This is a third independent implementation of those two numbers.
- The achievable ladder at `N=40`: `2.0%, 2.5%, 4.0%, 4.5%, 5.0%, 6.0%, 6.5%, ...` -- five
  firing points at or below 5%, the fifth landing exactly on `10/200 = 5.0%`.
- What `results/n_scaling_plan.md` actually pre-registers (section 9, and it is not what the
  brief says).

Taken on trust, and load-bearing to different degrees:

- That the recorded verdict bits faithfully record the DeBERTa verdicts of the August GPU run.
  I replayed them; I cannot re-run the NLI without the GPU. If the bits are wrong everything
  here is wrong, but so is the rest of the paper.
- The fair pool's score-independent construction (`paper/sections/methods.tex`). Not re-derived.
- The end-to-end fall `10.0 points [7.2, 12.9]` and the first leg `-8.86 [-11.05, -6.78]`.
  Out of scope; I did re-derive both endpoints that the first leg connects.
- The TPR figures (`6.0% [3.5, 10.2]` at the floor threshold, and the matched-FPR rows).
- `results/replay_control.md`'s `5.0% [2.5%, 5.0%]`. I read it and reproduced its *structure*
  in simulation (section 10); I did not re-run its own bootstrap.

---

## 2. One thing nobody has flagged: the count is 3 before it is 4

The four tied answers are mathematically tied -- identical partitions must have identical
entropy. They are not numerically tied. `se.entropy.discrete_entropy` accumulates `-p log p`
in `Counter` iteration order, which follows cluster-id assignment order, and floating-point
addition is not associative:

```
qz_3927  3.6195647360579453
qz_2135  3.6195647360579453
qz_4127  3.6195647360579453
qz_3833  3.619564736057945    <-- one ULP lower, difference 4.44e-16
```

A strict `score >= t` rule at the raw maximum flags **three**, not four. The pipeline gets four
only because `scripts/n_scaling_grid.py` snaps every score to `DP = 9` decimals before building
the lattice (`round(v, DP)`, lines 411 and 1544), which merges them. The snap is correct and
robust -- the split does not reappear at any `DP <= 15` -- so nothing in the repo is broken.

It is worth one sentence in the paper anyway, because of where the number lands. Wilson on
`3/200` is `[0.5114%, 4.3166%]`, entirely below 5%; Wilson on `4/200` is `[0.7804%, 5.0287%]`,
over the line. **On the current framing the entire Abstract-versus-Discussion conflict is
decided by whether four mathematically identical sums are added in the same order.** That is
not a reason to prefer one interval over the other. It is a reason to notice that the framing
hangs a load-bearing claim on a quantity with no stability, which is what section 4 shows
directly. The ruling in section 0 does not depend on 3 versus 4 at all.

---

## 3. The bootstrap in closed form

The percentile bootstrap of this statistic needs no resampling. Draw 200 questions with
replacement; the resample's maximum is the highest distinct pool value that gets drawn at all.
With the pool's distinct values indexed from the top, `m_r` the pool proportion at rung `r` and
`M_r` its cumulative sum,

```
P(floor* = j/200) = sum over r of  C(200, j) * m_r^j * (1 - M_r)^(200-j),    j >= 1
```

because the other `200-j` draws must miss rungs `1..r` entirely. Evaluated on the observed pool
(rung counts from the top: `4, 1, 3, 1, 1, 2, 1, 1, 1, 1, ...`):

| j | FPR | exact mass | 400k-resample Monte Carlo |
| --- | --- | --- | --- |
| 1 | 0.5% | 7.9315% | 7.921% |
| 2 | 1.0% | 15.0549% | 15.037% |
| 3 | 1.5% | 19.8925% | 19.876% |
| 4 | 2.0% | 19.8739% | 19.862% |
| 5 | 2.5% | 15.8611% | 15.864% |
| 6 | 3.0% | 10.5067% | 10.562% |
| 7 | 3.5% | 5.9376% | 5.934% |
| 8 | 4.0% | 2.9216% | 2.919% |
| 9 | 4.5% | 1.2714% | 1.288% |
| 10 | 5.0% | 0.4954% | 0.490% |

Percentile interval `[0.500%, 4.000%]`, reproduced on every seed, as reported.

The shape is worth naming. This is almost exactly a `Binomial(200, 0.02)` count truncated below
at 1: the top rung is missed entirely in only `(1 - 0.02)^200 = 1.76%` of resamples, and the
rest is the multiplicity with which four known questions get redrawn. **The interval is
therefore a prediction interval for how many copies of four specific answers land in a
resample, not a confidence interval for any rate in the population.** It holds the estimate
fixed at `p = 0.02` and reports the spread of the count at that fixed `p`; it never propagates
uncertainty in `p` itself. That is why it is *narrower on top* than Wilson (`4.0%` against
`5.03%`) while claiming to be an interval for the same thing -- a warning sign on its own, and
section 6 confirms what it means.

---

## 4. Why the question is ill-posed as asked, and what the estimands are

The score at `N=40` lives on a finite, a-priori-known lattice: the entropy of a partition of 40
items. The top rungs are fixed before any data exists.

| rung | partition | score |
| --- | --- | --- |
| 0 | `1^40` (the cap) | 3.688879 |
| 1 | `2, 1^38` | 3.654222 |
| 2 | `2, 2, 1^36` | 3.619565 (the observed maximum) |
| 3 | `3, 1^37` | 3.606484 |

Every `P(score >= rung r)` is a binomial proportion at a threshold fixed in advance, and Wilson
is valid for each of them. Nothing is data-selected except *which rung gets called "the
floor"*. That single act of selection is the whole problem, and it makes three different
quantities collide:

- **tau_top** -- the population mass at the top of the population's support. This is what "the
  floor" literally means for an operator who could see the whole population. It is well defined
  and, as section 6 shows, it is not estimable at n=200.
- **tau_deploy** -- the false-alarm rate a rule actually delivers on fresh data when its
  threshold is fitted at the sample maximum of 200 answers. Operationally the honest target.
- **tau_cap** -- the mass at `ln 40`, threshold fixed a priori. The pre-registered quantity.

The paper currently prints a point estimate of the first, an interval that is a poor fit for
all three, and a concession that turns on the third without saying so.

---

## 5. The population model, and the two measurements that validate it

**Fit.** For each of the 200 questions, take its observed partition of the 40 samples and fit a
one-parameter Chinese-restaurant / Ewens model by matching the expected block count:
`sum_{i=0}^{39} alpha/(alpha+i) = K_observed`. The model is projective in the sample size, so an
`alpha` fitted at `N=40` predicts `N=20` and `N=10` with no refitting. The population is the
uniform mixture over the 200 fitted questions. Top-of-lattice masses are computed exactly from
the Ewens sampling formula, not by Monte Carlo; partitions down to `K >= 28` are enumerated
(173 rungs, 14.6% of the mass), which leaves probability `1.8e-14` that a pool of 200 misses
every enumerated rung.

**Rejected alternative.** The natural competitor is the model in which duplications are
structural rather than coincidental: each question's meaning set is exactly the clusters
observed, with the observed proportions, and 40 fresh draws come from that fixed categorical.
This model is **rejected by the data by a factor of 450**:

| measured by subset replay | Pop-D (fixed meaning set) | Pop-C (Ewens) |
| --- | --- | --- |
| `N=10` ceiling atom `12.002%` | 2.733% | 13.397% |
| `N=20` ceiling atom `3.134%` | 0.007% | 3.735% |

The recorded ceiling atoms cannot be produced by a model without unseen meanings. That removes
the "the 2% atom is real and structural" branch entirely -- it is not merely disfavoured, it is
incompatible with the two budgets the paper already measures.

**Calibration, and the out-of-sample check that matters.** Pop-C is slightly optimistic. Tune a
single global multiplier `f` on every `alpha` so that the predicted `N=20` atom matches the
measured `3.134%` exactly. That gives `f = 0.8475` -- and the same model then predicts the
`N=10` atom at **11.863%** against a measured **12.002%**, a budget it was not tuned to. One
knob, fitted at one budget, correct at another to 0.14 points.

The calibrated model's `N=40` ceiling-atom mass is **0.2735%** (uncalibrated: 0.4121%).

**Goodness of fit at the top**, predicted against observed counts among the 200 questions:

| K | observed | predicted (calibrated) | predicted (raw) |
| --- | --- | --- | --- |
| 40 | 0 | 0.55 | 0.82 |
| 39 | 0 | 1.59 | 2.10 |
| 38 | 5 | 2.43 | 2.89 |
| 37 | 3 | 2.72 | 3.00 |
| 36 | 4 | 2.62 | 2.78 |
| 35 | 2 | 2.41 | 2.54 |
| 34 | 1 | 2.23 | 2.42 |
| 33 | 3 | 2.17 | 2.42 |
| 32 | 3 | 2.21 | 2.53 |
| 31 | 2 | 2.33 | 2.69 |
| 30 | 1 | 2.49 | 2.87 |

**The honest caveat, stated before it can be used against me:** the model mildly under-predicts
the very top. The observed floor of `2.0%` sits at the 93rd percentile of the model's own
predictive distribution for a pool of 200 (`P(floor_hat >= 2.0%) = 7.13%`). So the model may
place the true floor somewhat too low. Section 8 shows how much that would have to matter
before it changes the ruling, and the answer is that it cannot.

---

## 6. Coverage. This is what decides it

40,000 simulated pools of 200 questions per cell, three independent seeds, nominal 95%.

### Row 1, the N=40 floor, calibrated population (true floor `tau_top = 0.2735%`)

| interval | two-sided coverage of `tau_top` | upper end >= truth | lower end > truth | mean width |
| --- | --- | --- | --- | --- |
| **(a) Wilson `[0.78, 5.03]`** | **53.7% / 53.5% / 53.7%** | 100.00% | 45.8% | 3.11 pts |
| **(b) Bootstrap `[0.50, 4.00]`** | **0.00% / 0.00% / 0.00%** | 100.00% | 100.00% | 2.45 pts |

On the uncalibrated raw fit (true floor `0.4121%`): Wilson **76.6%**, bootstrap **0.00%**.

The pool's maximum reaches the true top rung in only 42.3% of pools (56.0% uncalibrated). More
than half the time the reported "floor" is the multiplicity of a rung the population's floor is
not even on. The mean point estimate is `0.8754%` against a truth of `0.2735%` -- biased up by
a factor of 3.2.

### The positive controls, where the atom is not empty

Same machinery, same model, one knob changed -- the budget.

| budget | true floor | pool max reaches it | Wilson coverage | bootstrap coverage |
| --- | --- | --- | --- | --- |
| `N=10` | 11.8627% | 100.00% | **95.11%** | **94.85%** |
| `N=20` | 3.1336% | 99.78% | **96.20%** | **98.39%** |
| `N=40` | 0.2735% | 42.27% | **54.17%** | **0.00%** |

This is the diagnosis in one table. Neither estimator is broken. **What breaks is the estimand,
and it breaks exactly when the ceiling atom empties.** While the atom carries mass, the floor is
a fixed population proportion at a fixed threshold and both methods price it correctly. Once it
empties, "the floor" stops naming anything a pool of 200 can see.

### Coverage of `tau_deploy`, the rate the fitted rule actually delivers

| | Wilson | bootstrap |
| --- | --- | --- |
| calibrated | **87.97% / 87.69% / 87.94%** | 55.91% / 55.78% / 56.53% |
| raw fit | 93.69% | 42.46% |

Wilson is defensible-but-under-nominal here; the bootstrap is not defensible for any of the
three estimands.

### Certification, and the false-certification rate a referee will ask for

"Certify" means the interval's upper end falls below 5%.

| population | true floor | Wilson certifies | bootstrap certifies |
| --- | --- | --- | --- |
| calibrated | 0.27% (below) | 92.89% | 96.64% |
| raw fit | 0.41% (below) | 90.20% | 94.56% |
| `N=20` calibrated | 3.13% (below) | 12.36% | 19.77% |
| adversarial | **5.000% (at the line)** | **0.93%** | **2.11%** |
| adversarial | **5.500% (above)** | **0.40%** | **1.09%** |
| adversarial | 7.000% (above) | 0.02% | 0.11% |
| `N=10` calibrated | 11.86% (above) | 0.00% | 0.00% |

Neither procedure falsely certifies. And note what the adversarial rows also show: on every one
of them -- all of which have a true floor above 5%, which at `N=40` requires a full atom --
two-sided coverage returns to 95.4-96.6% (Wilson) and 93.9-95.4% (bootstrap). The failure is
caused by the empty atom and by nothing else.

---

## 7. Objection 1 adjudicated: it bites, and resizing the bootstrap does not fix it

The verifier is right that the n-out-of-n bootstrap is inconsistent for functionals of a sample
maximum, and right that it applies here. But the standard remedy does not apply, and it matters
to say why rather than to reach for `m`-out-of-`n` and move on.

`m`-out-of-`n` bootstrap and subsampling repair the *sampling distribution* of an estimator of
a fixed population functional. Here the functional itself moves with the pool size. Measured on
the calibrated population, against a true floor that is constant at `0.2735%`:

| pool size `m` | mean `floor_hat` | median | `m * floor_hat` | P(pool max reaches the true top rung) |
| --- | --- | --- | --- | --- |
| 50 | 2.4201% | 2.000% | 1.21 | 0.131 |
| 100 | 1.4376% | 1.000% | 1.44 | 0.243 |
| **200** | **0.8775%** | 0.500% | 1.76 | 0.422 |
| 400 | 0.5587% | 0.500% | 2.23 | 0.658 |
| 800 | 0.3571% | 0.250% | 2.86 | 0.896 |
| 1424 | 0.2888% | 0.281% | 4.11 | 0.978 |
| 4000 | 0.2744% | 0.275% | 10.97 | 1.000 |
| 20000 | 0.2745% | 0.275% | 54.90 | 1.000 |

If the floor were a population parameter, column 2 would be flat. It is not; `floor_hat` falls
roughly like `c/m` until the pool is large enough to hit the true top rung essentially always,
and only then does it converge. **A resizing scheme cannot fix an estimator whose target moves
with the resizing.** An `m`-out-of-`n` bootstrap at `m = 50` would faithfully report the floor
of a 50-answer pool, `2.42%`, which is not the quantity anyone wants.

The table also prices the extension the plan holds in reserve, and prices it honestly: the
`n = 1424` full correct stratum would land the estimator within 0.02 points of the truth. The
`n = 230` the plan contemplates would not come close.

---

## 8. Objection 2 adjudicated: the Discussion's argument is exactly inverted

The Discussion (`paper/sections/discussion.tex`, around line 175) argues:

> Wilson's lower end excludes 0.5% -- the one value this floor can never fall below on 200
> answers, since the top score is always attained by at least one of them.

The premise is true and the conclusion does not follow from it. "The estimator can never return
less than `1/200`" is a statement about the estimator's range. "The floor can never fall below
0.5%" is a statement about the population. The sentence slides from the first to the second,
and the second is false: the population floor is a proportion in a population much larger than
200 and is under no obligation to be a multiple of `1/200`.

Measured: the bootstrap's lower endpoint of `0.5%` exceeds the true floor in **100.00% of
40,000 pools, on all three seeds, on both the calibrated and the raw model**. The mass pinning
that endpoint is 7.93% -- above the 2.5% needed -- so the endpoint is placed by construction
and carries no information, exactly as the verifier said. It is a degeneracy, and the
Discussion presents the degeneracy as the reason to prefer the estimator that has it.

The upper endpoint is no better founded. Mass strictly above `4.0%` totals **2.020%**, against
the 2.5% needed to move the 97.5th percentile one lattice step to `4.5%`. So `4.0%` versus
`4.5%` is decided by 0.48 percentage points of resample mass on a lattice whose steps are 0.5
points apart -- and it is the difference between the Discussion's claim and no claim at all.
Neither endpoint of `[0.5, 4.0]` is doing statistical work.

**How hard is this conclusion?** The most useful robustness check is to ask what the world would
have to look like for each candidate endpoint to be the truth, and whether that world is
consistent with the two atoms the paper has already measured. Sweeping the global multiplier:

| for the true `N=40` floor to be | the same model implies `N=20` atom | implies `N=10` atom |
| --- | --- | --- |
| 0.27% (calibrated fit) | 3.12% | 11.82% |
| 0.41% (raw fit) | 3.73% | 13.38% |
| **0.50% (bootstrap lower end)** | 4.07% | 14.24% |
| **0.78% (Wilson lower end)** | **5.03%** | **16.58%** |
| **2.00% (the printed point estimate)** | **8.46%** | **24.28%** |
| 4.00% (bootstrap upper end) | 13.51% | 33.97% |
| 5.03% (Wilson upper end) | 15.99% | 38.18% |
| *measured* | **3.134% [1.79, 4.69]** | **12.002% [8.92, 15.32]** |

For the true floor to be as high as the printed `2.0%`, the `N=20` ceiling atom would have to be
`8.46%` -- nearly double the top of its measured interval -- and the `N=10` atom `24.3%`,
against a measured `12.0%`. Even Wilson's *lower* endpoint of `0.78%` implies an `N=20` atom of
`5.03%`, outside `[1.8, 4.7]`. Only `0.50%` and below survives contact with the paper's own
smaller-budget measurements.

The paper's `N=20` and `N=10` rows therefore already bound its `N=40` floor, and they bound it
below both candidate intervals. The direction of that argument does not depend on the Ewens
family: it is the elementary coupling that 40 mutually inequivalent answers requires the first
20 to be mutually inequivalent, so `P(cap at 40) <= P(cap at 20) = 3.134%`, tightened by the
observation that the merge hazard does not vanish after the twentieth draw. The model supplies
the tightening; the coupling supplies the direction.

---

## 9. Treatment (c): what the plan actually pre-registers, and why it is still the answer

**The brief's description of (c) is half wrong, and the half that is wrong matters.**
`results/n_scaling_plan.md` does *not* pre-register an estimator-free count. It pre-registers
**Wilson**, and derives a count from it (lines 308-310 and 402-406):

> the Wilson upper bound clears 5% only when at most **3 of the 200** negatives sit at the cap,
> i.e. a floor of **1.5%** or less

> SAYING 'no operating point at or below 5% exists' needs the Wilson upper bound under 5%,
> which at n=200 requires at most 3 negatives at the cap (1.5%)

So the criterion is a Wilson criterion, and the hope that the estimator dispute could be
side-stepped by a pure count is not supported by the plan.

But read what the criterion is a criterion *on*: **negatives at the cap**. Both statements say
"at the cap", twice each. The pre-registered count is the ceiling-atom count, and the
pre-registered quantity is the ceiling-atom mass -- the plan identifies it with the floor ("the
ceiling-atom mass -- and therefore the minimum non-zero achievable FPR", line 277) because at
every budget the plan was written against, they were the same number.

**The observed value of the pre-registered count is 0, not 4.** Comparing the observed `4`
against the pre-registered `3` -- which the brief reports as the state of play, and which is the
natural misreading -- compares the first-firing-point count against a threshold derived for the
at-cap count. They are different quantities; that is the entire content of `floor_cells()`'s
docstring in `scripts/n_scaling_grid.py`, and the paper has already been burned once by
conflating them.

On the quantity the plan pre-registered, with the estimator the plan pre-registered, the
criterion is met with three counts to spare: `0/200`, Wilson upper bound `1.8845%`, comfortably
under 5%.

**And that treatment is the only one of the three with its nominal coverage**, because its
threshold really is fixed in advance:

| true cap mass | Wilson two-sided | **Wilson upper >= truth** | Clopper-Pearson two-sided |
| --- | --- | --- | --- |
| 0.10% | 98.25% | **100.00%** | 98.25% |
| 0.20% | 93.86% | **100.00%** | 99.22% |
| 0.27% | 89.76% | **100.00%** | 98.26% |
| 0.41% | 95.00% | **100.00%** | 99.03% |
| 0.50% | 92.02% | **100.00%** | 98.13% |
| 1.00% | 94.83% | **100.00%** | 98.40% |
| 1.50% | 96.76% | **100.00%** | 98.87% |
| 2.00% | 93.31% | 98.24% | 96.22% |

The one-sided upper bound -- the only direction the concession uses -- has 100% coverage across
the entire plausible range. (The two-sided dip to 89.8% at 0.27% is a discreteness knife edge
and nothing more: Wilson's lower endpoint at `k=2` is 0.2747%, which happens to sit 0.0012
points above the model's point value. Clopper-Pearson, which the row could use instead, stays
at or above 97.7% everywhere.)

**Three caveats, so this is adopted for the right reason and not because it is convenient.**

1. The plan did not anticipate the atom emptying. Its identity "ceiling-atom mass = minimum
   non-zero achievable FPR" is what broke, and the paper's switch to the first firing point is
   an unpre-registered re-specification of the row. Invoking the plan's criterion is the
   *literal* pre-registration, but the paper must disclose that the two quantities came apart
   and that the criterion is being read on the original one. It is already disclosing a gate
   re-spec (the locked judge at 0.93); this belongs in the same list.
2. The plan's own section 6 table is mislabelled. Its column reads "can n=200 certify 'no 5%
   operating point'?" and answers "yes, upper bound below 5%" for a true floor of 1.0% -- but an
   upper bound below 5% certifies that a sub-5% operating point *does* exist. The arithmetic and
   the intent are unambiguous (line 425: "put a one-sided certificate under 5%"); the label is
   inverted. Since this is the sentence the whole criterion hangs on, it should be fixed.
3. The certification rests on one assumption, which should be stated rather than hidden: that
   the population assigns *some* positive probability to a question producing 39 or 40 mutually
   inequivalent answers out of 40. If it assigns exactly zero to both, the top of support is the
   observed rung, the floor is `4/200` with Wilson `[0.78, 5.03]`, and the current concession
   stands. That branch requires every question in the population to merge at least twice in 40
   draws with probability one, while 3.1% of them already produce 20 mutually inequivalent
   answers out of 20. The calibrated model puts `0.27% + 0.79% = 1.07%` on those two rungs. I do
   not think a referee will buy the zero branch, but the paper should name it in one clause
   rather than let a referee find it.

---

## 10. Row 2: the achieved 5%-budget operating point

Same machinery; statistic changed to "the largest achievable FPR at or below 5% on the pool"
(observed: `10/200 = 5.0%`), estimand changed to the true population FPR of that fitted
threshold. 12,000 pools, 3,000 bootstrap resamples each, calibrated population.

| | value |
| --- | --- |
| true FPR of the fitted threshold on fresh data | **5.1697%** |
| in-sample achieved FPR | 4.6699% |
| **Wilson `[2.7, 9.0]` coverage** | **94.44%** (mean width 6.03 pts) |
| **question bootstrap `[2.5, 5.0]` coverage** | **54.81%** (mean width 2.56 pts) |
| bootstrap upper endpoint pinned at the 5% budget | **100.00% of pools** |

Two findings.

**Wilson is right here and the bootstrap is wrong, which is the opposite of row 1's diagnosis
and for a principled reason.** The floor is an extreme order statistic: the estimand sits at the
edge of the support, the pool rarely reaches it, and no interval built from the pool can price
it. The 5%-budget point is an *interior* quantile: the pool has 10 answers above the threshold
and roughly 190 below, the empirical quantile is stable, and Wilson at a fixed count recovers
its nominal coverage. The Discussion's rule -- "the threshold is data-selected, therefore
bootstrap" -- does not distinguish those two cases, and the distinction is the whole thing.
**Data selection is not what breaks Wilson; being at the boundary of the support is.** That is
the sentence the Discussion needs, and it is the one that keeps the two rows consistent while
ruling them opposite ways.

**The bootstrap here is not merely uninformative, it is affirmatively misleading.** Its upper
endpoint is `5.0%` in 100.00% of pools because the statistic can never exceed the budget by
construction. So `[2.5, 5.0]` asserts at 97.5% confidence that the operating point is at most
5% -- a fact about the estimator's range, restated as a fact about the world -- while the fitted
rule's true rate exceeds 5% roughly half the time. This is the identical error to row 1's pinned
lower endpoint, mirrored onto the other end of the interval. The same `results/replay_control.md`
row shows the degeneracy in the open at smaller budgets: `0.0% [0.0%, 0.0%]` at `N=10`, and
`3.1% [0.0%, 5.0%]` at `N=20`, where both endpoints are structural.

**The new finding the paper should take from this row:** the in-sample achieved rate understates
the deployed rate by about half a point (`4.67%` in sample against `5.17%` deployed), because
choosing the largest achievable rate at or below the budget selects rungs where the empirical
count happened to fall low. The Abstract's existing refusal to read `5.0%` as a demonstration
that a sub-5% operating point exists is therefore not merely cautious but quantitatively
correct, and it can now say why.

---

## 11. Suggested text

Not edits -- this ruling touches no file but itself. Offered so that the ruling is falsifiable
against something concrete.

**Abstract**, replacing "the floor is an ordinary order statistic, `2.0%` [`0.8`, `5.03`], whose
interval does not exclude `5%`" (`paper/main.tex` lines 48-49):

> Running the fair pool's 200 correct answers out to `N=40` empties the atom: no clean correct
> answer reaches `ln 40` (`0/200`, at most `1.9%`), and with the atom gone so is the
> obstruction. What 200 answers cannot then do is locate the floor -- the cheapest alarm they
> can exhibit costs `2.0%`, which is the resolution of the pool and not a property of the
> detector.

**Conclusion** (`paper/sections/conclusion.tex` lines 22-28), same substitution, plus: delete
"would need the Wilson upper bound on the floor to fall below 5%, and on these 200 correct
answers it is 5.03 -- over the line rather than under it". The pre-registered bound is on the
at-cap mass and it is `1.9%`, under the line.

**Discussion** (lines 168-177): delete the sentence beginning "That is not a widening" through
"attained by at least one of them", and the claim that the `N=40` floor is "outside Wilson's
reach". Replace with the reason the floor has no interval at all: its threshold is the top rung
this pool happened to reach, that rung is not the population's top rung in 58% of pools of this
size, and no interval computed from 200 answers prices it.

**`results/replay_control.md`**: retire `5.0% [2.5%, 5.0%]` for the achieved-FPR-at-budget rows
in favour of Wilson, or relabel them as ranges of the estimator rather than confidence
intervals. The `0.0% [0.0%, 0.0%]` cell at `N=10` is the same defect with the degeneracy fully
visible.

**If the paper prints both and claims neither** -- the outcome the brief asks me to price -- the
summary sections cannot carry a two-paragraph hedge, and the one-sentence version they would
have to carry is: *"at `N=40` the ceiling atom is empty (`0/200`, at most `1.9%`) and the
smallest false-alarm rate 200 answers can exhibit is `2.0%`; we quote no interval for the latter
because it is a property of the pool's size."* That is one sentence, it is true under both
candidate treatments, and it is what section 0 rules for -- so "print both and claim neither"
collapses into the ruling rather than competing with it.

---

## 12. Reproduction

Everything is CPU-only and deterministic given the seeds. Working files are in the session
scratchpad: `base.py` (loader and an independent union-find replay), `popmodels.py` (CRP fit),
`ewens.py` (exact top-of-lattice masses), `validate.py` (measured atoms by subset replay),
`coverage.py` (row 1), `row2.py` (row 2). The chain is reconstructible from this file alone: the
four ingredients are (i) union-find on the recorded 780-bit triangle, (ii) `alpha_q` solving
`sum_{i<40} alpha/(alpha+i) = K_q`, (iii) the Ewens sampling formula
`P(a) = n! / theta^(n) * prod_j (theta/j)^{a_j} / a_j!` for rung masses, and (iv) a single
global multiplier on `alpha` pinned to the measured `N=20` atom.

Seeds for the headline numbers: row-1 coverage `424242`, `1`, `2`, `3` (40,000 pools each);
subsampling `5`; adversarial `991` (30,000 pools); at-cap sweep computed exactly from the
binomial pmf, no seed; row 2 `31337` and `777`. The bootstrap for row 1 is exact (section 3), so
its endpoints carry no Monte Carlo error at all.

Verified not disturbed: WSL `Ubuntu-24.04` PID 473 still running at exit.
