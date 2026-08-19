# Which interval belongs to the measured N=40 achievable false-alarm floor

Ruling, 2026-08-19. Revised the same morning after an adversarial re-derivation found three
defects in the first version's model. All three were re-checked against the primary artifact.
Two reproduce exactly; the third reproduces as arithmetic but its inference does not survive.
**The practical ruling is unchanged. The reason for it has changed, and one sentence of the
first version's suggested Abstract text was wrong and must not be printed.** Section 1 is new
and states the part of this document that needs no model at all.

CPU only; the live GPU run (WSL `Ubuntu-24.04` PID 473, `scripts/null_control.py --tag _defb`,
verified with `ps` at 906 min CPU) was neither touched nor read from.

---

## 0. How every number in this document is labelled

Every quantitative claim carries one of three tags. This is not decoration -- the whole dispute
turned out to hinge on which tag a number deserves.

| tag | meaning | what has to be true for it to hold |
| --- | --- | --- |
| `[measured]` | an exact count or exact computation over the 200 recorded correct/`N=40` partitions | only that `verdict_bits` faithfully records the August DeBERTa verdicts |
| `[bounded]` | a confidence bound | the sampling assumption named at each use |
| `[model]` | depends on the fitted Ewens/CRP population | the parametric family, *in the region where it is used* |

A fourth thing that is not a tag, because it must never be quoted as a result:
`[extrapolation]`. It appears once, in section 7, and is flagged there.

---

## 1. What survives with no model at all

This section is self-contained. Nothing in it uses the Ewens fit, the coverage simulation, or
any distributional assumption beyond "the 200 questions are an i.i.d. sample". If everything
after section 5 were deleted, the ruling would still follow from these seven facts.

**M1.** `[measured]` `ln 40 = 3.6888794541139363`. The highest score attained by any of the 200
correct answers is `3.6195647360579453`. **0 of 200 reach the cap.** The threshold `ln 40` is
fixed by the sample budget before any data exists, so Wilson applies to the at-cap count with
no data-selection problem at all: **`0/200 = 0.0% [0.0%, 1.8845%]`**.

**M2.** `[measured]` The pool's highest score is the `(2, 2, 1^36)` rung -- "two coincidental
pairs among 40" -- attained by `qz_2135`, `qz_3833`, `qz_3927`, `qz_4127`. The count is 4, so
the cheapest alarm this pool can exhibit costs `4/200 = 2.0%`. The achievable ladder is
`2.0, 2.5, 4.0, 4.5, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0 %` -- five firing points at or
below 5%, the fifth landing exactly on `10/200`.

**M3.** `[measured]` The largest number of mutually inequivalent answers any question produces
is **38**, and this is exhaustive rather than sampled. Re-clustering *inside* a subset -- which
is what a smaller-budget run does, and what `results/n_scaling_grid.md` line 83 specifies --
makes "all `k` distinct" equivalent to "the `k` chosen samples form an independent set in the
recorded verdict graph", not "the `k` chosen samples fall in distinct blocks of the full-40
partition". The two differ: removing a sample can break a transitive chain. Computing the full
independence polynomial of each question's graph gives the exact subset-averaged fraction:

| k | exact `U_k` | k | exact `U_k` |
| --- | --- | --- | --- |
| 10 | **11.992117%** | 36 | 0.080671% |
| 20 | **3.129089%** | 37 | 0.040334% |
| 30 | 0.620551% | 38 | **0.013462%** (`7/52000`) |
| 35 | 0.134621% | 39 | **0.000000%** (exactly) |
| | | 40 | **0.000000%** (exactly) |

`U_39 = 0` is exact and exhaustive: all `200 x 40 = 8,000` 39-subsets were enumerated and not
one is all-distinct. `U_40 = 0` is the same statement as M1.

> **Correction to the first version.** It reported the measured `N=10` and `N=20` atoms as
> `12.002%` and `3.134%`. Those are Monte-Carlo estimates. The exact values are
> **`11.992117%`** and **`3.129089%`**. The difference is immaterial to every conclusion here
> -- but it moves the calibration knob, and section 7 shows the calibration knob *is* the
> coverage headline.

**M4.** `[bounded]` 0 of 200 questions reach `K >= 39`. Assuming only that the 200 questions
are i.i.d., that bounds the population rate at **`<= 1.8845%`** (Wilson upper) or
**`<= 1.8275%`** (Clopper-Pearson, 97.5% one-sided). It places **no positive lower bound**.
This is the only valid model-free bound on the two rungs above the observed maximum; section 6
shows why the tighter-looking bound offered against the first version is not one.

**M5. The dichotomy, and it is the whole ruling.** Write `tau_top` for the population mass at
the top of the population's support -- what "the floor" literally means for an operator who
could see the whole population. Then:

- if `P(K >= 39) = 0` **exactly**, the top of support is the observed `(2, 2, 1^36)` rung and
  `tau_top` is an ordinary binomial proportion with point estimate `4/200 = 2.0%`;
- if `P(K >= 39) > 0` by any amount, the top of support moves up to a rung of mass at most
  `1.88%` `[bounded, M4]` **and with no positive lower bound** -- it may be `10^-6`, and
  `tau_top` is then that number rather than `2.0%`.

`tau_top` is **discontinuous** at `P(K >= 39) = 0`, and `0/200` is the modal outcome under both
branches. The sample cannot choose between them. So `tau_top` is not merely badly estimated at
`n = 200`; it is **not identified**, and its two admissible values differ by an unbounded
factor.

**M6.** `[measured]` Wilson on `4/200` is `[0.780443%, 5.028709%]`. Under M5's first branch it
covers; under the second it fails for every `tau_top` below `0.780443%`, which is most of that
branch. Its unconditional coverage is a mixture whose weight is the probability of a hypothesis
the data cannot test. **There is therefore no coverage statement to attach to it** -- and that
conclusion needs no population model.

**M7.** `[measured]` The question bootstrap `[0.500%, 4.000%]` fails M5's second branch by
construction rather than by chance. Its lower endpoint sits at `1/200` because `7.9315%` of
resample mass -- exact, section 4 -- piles onto the smallest value the statistic can return,
which is more than the `2.5%` needed to place the endpoint. The estimator's range is bounded
below by `0.5%`; the population is under no such obligation.

**What follows, with no model.** Print the at-cap mass `0/200 = 0.0% [0.0%, 1.9%]`, whose
threshold is a priori and whose Wilson interval is therefore valid in both branches. Print
`2.0%` beside it with **no interval**, because the quantity a reader would take that interval
to describe is not identified. Both candidate intervals are unquotable for the floor -- Wilson
because its coverage is branch-dependent and the branch is untestable, the bootstrap because
its endpoints are placed by the estimator's range rather than by the data.

Everything from section 6 onward is model-dependent and is offered as *one branch quantified*,
not as the reason.

---

## 2. The ruling, operationally

**Row 1, the N=40 floor.** Report the row as the ceiling-atom mass, `0/200 = 0.0% [0.0, 1.9]`
by Wilson at the a-priori threshold `ln 40` `[measured]`, and report `2.0%` beside it as the
smallest false-alarm rate a 200-answer pool can *exhibit* `[measured]`, with no confidence
interval attached -- print neither `[0.8, 5.03]` nor `[0.5, 4.0]`. **Unchanged from the first
version.**

**Row 2, the achieved 5%-budget operating point.** Print Wilson, `5.0% [2.7, 9.0]`, and retire
the bootstrap `[2.5, 5.0]`. **Unchanged, and untouched by all three defects** -- row 2 is an
interior quantile and does not depend on the deep tail (section 11).

**What the Abstract's concession should assert.** That the obstruction is gone: at `N=10` the
floor is a full ceiling atom, so the 5% budget is unbuyable at any threshold; at `N=40` the
atom is empty (`0/200`, at most `1.9%`) and the identity lapses.

> **Revised, and this is the one substantive retraction.** The first version proposed the
> Abstract say that the `2.0%` "is the resolution of the pool and not a property of the
> detector". **Do not print that sentence.** It is true only in M5's second branch. In the
> first branch `2.0%` is a genuine estimate of a genuine population quantity, and section 8
> measures Wilson's coverage there at **95.06%**. The sentence that is true in *both* branches
> is the non-identification one:
>
> > The cheapest alarm 200 correct answers can exhibit costs `2.0%`. Whether that is a property
> > of the detector or of the pool's size turns on whether the population can ever produce 39
> > mutually inequivalent answers out of 40; 200 answers cannot tell, and the two answers differ
> > by more than two orders of magnitude. We therefore quote no interval for it.

---

## 3. The count is 3 before it is 4

`[measured]` The four tied answers are mathematically tied -- identical partitions must have
identical entropy -- but they are not numerically tied in the recorded file. Read back
directly from `results/n_scaling_ckpt.jsonl`:

```
qz_3927  3.6195647360579453
qz_2135  3.6195647360579453
qz_4127  3.6195647360579453
qz_3833  3.619564736057945    <-- one ULP lower, difference 4.44e-16
```

`se.entropy.discrete_entropy` accumulates `-p log p` in `Counter` iteration order, which
follows cluster-id assignment order, and floating-point addition is not associative. **My own
replay, which sums in descending block-size order, produces all four identical** -- so the
split is a property of one accumulation order, not of the partitions. A strict `score >= t`
rule at the raw maximum flags **three**, not four; the pipeline gets four because
`scripts/n_scaling_grid.py` snaps to `DP = 9` decimals before building the lattice
(`round(v, DP)`, lines 411 and 1544). The snap is correct and robust -- the split does not
reappear at any `DP <= 15` -- so nothing in the repo is broken.

Wilson on `3/200` is `[0.5114%, 4.3166%]`, entirely below 5%; on `4/200` it is
`[0.7804%, 5.0287%]`, over the line. On the *old* framing the entire Abstract-versus-Discussion
conflict was decided by the order in which four identical sums are added. The ruling in
section 1 does not depend on 3 versus 4 at all, which is one reason to prefer it.

> Note on the replay check itself: my independent union-find reproduces every recorded
> `n_clusters` (0 mismatches over 200) and every recorded `entropy_nats` to a maximum absolute
> difference of **8.88e-16** -- not `0.0`, as the first version claimed. Exact bit equality
> holds only if you also reproduce the accumulation order. One ULP is the honest number for an
> independent reimplementation.

---

## 4. The bootstrap in closed form

`[measured]` The percentile bootstrap of this statistic needs no resampling. With the pool's
distinct values indexed from the top, `m_r` the pool proportion at rung `r` and `M_r` its
cumulative sum,

```
P(floor* = j/200) = sum over r of  C(200, j) * m_r^j * (1 - M_r)^(200-j),    j >= 1
```

Evaluated on the observed pool (rung counts from the top: `4, 1, 3, 1, 1, 2, 1, 1, 1, 1, 1, 1`):

| j | FPR | exact mass | cumulative |
| --- | --- | --- | --- |
| 1 | 0.5% | 7.9315% | 7.9315% |
| 2 | 1.0% | 15.0549% | 22.9864% |
| 3 | 1.5% | 19.8925% | 42.8790% |
| 4 | 2.0% | 19.8739% | 62.7529% |
| 5 | 2.5% | 15.8611% | 78.6140% |
| 6 | 3.0% | 10.5067% | 89.1207% |
| 7 | 3.5% | 5.9376% | 95.0583% |
| 8 | 4.0% | 2.9216% | 97.9799% |
| 9 | 4.5% | 1.2714% | 99.2513% |
| 10 | 5.0% | 0.4954% | 99.7467% |

Percentile interval `[0.500%, 4.000%]`; mass strictly above `4.0%` is `2.0201%`, against the
`2.5%` needed to move the upper endpoint one lattice step to `4.5%`. Every figure is exact, so
the endpoints carry no Monte Carlo error at all.

The shape is worth naming: this is almost exactly a `Binomial(200, 0.02)` count truncated below
at 1 -- the top rung is missed entirely in only `(1 - 0.02)^200 = 1.76%` of resamples, and the
rest is the multiplicity with which four known questions get redrawn. **The interval is a
prediction interval for how many copies of four specific answers land in a resample, not a
confidence interval for any rate in the population.** It holds the estimate fixed at `p = 0.02`
and reports the spread of the count at that fixed `p`; it never propagates uncertainty in `p`
itself. That is why it is *narrower on top* than Wilson (`4.0%` against `5.03%`) while claiming
to describe the same thing.

---

## 5. The three estimands that collide

`[measured]` The score at `N=40` lives on a finite, a-priori-known lattice -- the entropy of a
partition of 40 items. The top rungs are fixed before any data exists:

| rung | partition | score |
| --- | --- | --- |
| 0 | `1^40` (the cap) | 3.688879 |
| 1 | `2, 1^38` | 3.654222 |
| 2 | `2, 2, 1^36` | 3.619565 (the observed maximum) |
| 3 | `3, 1^37` | 3.606484 |

Every `P(score >= rung r)` is a binomial proportion at a threshold fixed in advance, and Wilson
is valid for each of them. Nothing is data-selected except *which rung gets called "the floor"*.
That single act of selection makes three different quantities collide:

- **`tau_top`** -- the population mass at the top of the population's support. Section 1 shows
  it is not identified at `n = 200`.
- **`tau_deploy`** -- the false-alarm rate a rule actually delivers on fresh data when its
  threshold is fitted at the sample maximum of 200 answers. Operationally the honest target.
- **`tau_cap`** -- the mass at `ln 40`, threshold fixed a priori. The pre-registered quantity,
  and the only one of the three both branches agree about.

The paper currently prints a point estimate of the first, an interval that is a poor fit for
all three, and a concession that turns on the third without saying so.

---

## 6. The population model, what it is validated on, and where it fails

**Fit.** `[model]` For each of the 200 questions, take its observed partition of the 40 samples
and fit a one-parameter Chinese-restaurant / Ewens model by matching the expected block count:
`sum_{i=0}^{39} alpha/(alpha+i) = K_observed`. The model is projective in the sample size, so
an `alpha` fitted at `N=40` predicts `N=20` and `N=10` with no refitting. The population is the
uniform mixture over the 200 fitted questions. Top-of-lattice masses are computed exactly from
the Ewens sampling formula; partitions down to `K >= 28` are enumerated (272 partitions, 173
distinct scores, 14.63% of the mass), leaving probability `1.8e-14` that a pool of 200 misses
every enumerated rung.

**Calibration.** Tune a single global multiplier `f` on every `alpha` so the predicted `N=20`
atom matches the measured one. Pinned to the **exact** `U_20 = 3.129089%` this gives
`f = 0.846406`; the first version pinned to the Monte-Carlo `3.134%` and got `f = 0.8475`.
Out-of-sample, the calibrated model then predicts the `N=10` atom at **11.851%** against a
measured **11.992%** -- one knob, fitted at one budget, correct at another to 0.14 points. That
check is genuine and it reproduces.

| quantity | first version | this version | measured |
| --- | --- | --- | --- |
| multiplier `f` | 0.8475 | **0.846406** | -- |
| `N=10` atom, out of sample | 11.863% | **11.851%** | **11.992117%** |
| `N=40` cap mass, calibrated | 0.2735% | **0.272573%** | **0.000000%** |
| `N=40` cap mass, raw (`f = 1`) | 0.4121% | **0.412136%** | **0.000000%** |

**Rejected alternative.** `[model]` The competitor in which duplications are structural rather
than coincidental -- each question's meaning set is exactly the clusters observed, 40 fresh
draws from that fixed categorical -- predicts an `N=10` atom of `2.7%` and an `N=20` atom of
`0.007%` against measured `11.99%` and `3.13%`. It is incompatible with two budgets the paper
already measures, so the "the 2% atom is real and structural" branch is genuinely dead.

### 6.1 Where the model fails, and it is exactly where the answer lives

This is the third defect, and it is the most serious of the three. The Ewens fit is honest at
the budgets it was checked against and diverges monotonically above `k ~ 30`. The comparison is
like for like: `U_k` is an unbiased estimator of the model's own `P(k draws all distinct)`, so
the two columns are the same quantity.

| k | `U_k` exact `[measured]` | model `D_k` `[model]` | ratio model/data |
| --- | --- | --- | --- |
| 10 | 11.992117% | 11.851071% | **0.99** |
| 20 | 3.129089% | 3.129089% | 1.00 *(pinned)* |
| 25 | 1.538737% | 1.762685% | 1.15 |
| 30 | 0.620551% | 0.980227% | 1.58 |
| 32 | 0.381028% | 0.768624% | **2.02** |
| 35 | 0.134621% | 0.527696% | 3.92 |
| 37 | 0.040334% | 0.407312% | 10.10 |
| 38 | 0.013462% | 0.356915% | **26.51** |
| 39 | **0.000000%** | 0.312192% | infinite |
| 40 | **0.000000%** | 0.272573% | infinite |

The model tracks the data to within 15% through `k = 25`, crosses a factor of two at `k = 32`,
and is off by more than an order of magnitude by `k = 37`. **The `N=40` floor is set at
`k = 39` and `k = 40`, which is the far side of the divergence.** The calibrated
`tau_top = 0.272573%` that the coverage simulation treats as truth is therefore an
extrapolation from a region where the model is validated into a region where it is not, and
the direction of the extrapolation error is known: the model is too fat.

**How significant is the divergence?** `[model]` Not very, taken on its own -- and it is
important to say so rather than overclaim. Simulating 4,000 pools of 200 questions from the
calibrated model and computing each pool's `U_38`:

| | |
| --- | --- |
| model `E[U_38]` | 0.356915% (closed form), 0.357698% (simulated) |
| simulated 5% / 50% / 95% quantiles | 0.00513% / 0.15321% / 1.10385% |
| observed `U_38` | 0.012179% (clique rule -- the like-for-like comparison) |
| `P(U_38^sim <= observed)` | **0.115** |

`U_38` is dominated by whether any of the 200 questions lands at `K = 40` (a single such
question contributes `1/200` to `U_38` on its own) or `K = 39`. The model puts
`0.272573% + 0.792396% = 1.065%` on those two rungs, so it expects `2.13` such questions and we
saw none: exact binomial p-value `(1 - 0.01065)^200 = 0.1175`. **The model is not refuted at
any conventional level.** What the table shows is a systematic, monotone, one-directional
divergence in the deep tail, not a rejection.

---

## 7. The coverage headline is a step function, not a measurement

This is the first defect and it reproduces exactly.

`[model]` Wilson's lower endpoints at `n = 200` are a fixed lattice, and they decide everything:

| count `k` | Wilson 95% interval |
| --- | --- |
| 0 | `[0.000000%, 1.884533%]` |
| 1 | `[0.088317%, 2.777370%]` |
| 2 | `[0.274666%, 3.572176%]` |
| 3 | `[0.511424%, 4.316573%]` |
| 4 | `[0.780443%, 5.028709%]` |

The floor count is by definition at least 1. The calibrated model's `tau_top = 0.272573%` lies
**0.002093 points below** the `k = 2` lower endpoint of `0.274666%` (with the first version's
`0.2735%`, 0.001166 points below). Since Wilson's lower endpoint is increasing in `k` and its
upper endpoint at `k = 1` is `2.78%`, far above the truth, the interval covers **if and only if
the simulated pool's floor count is exactly 1**.

So the reported "53.7% / 53.5% / 53.7%" over three seeds is not a coverage measurement with
Monte Carlo error. It is three noisy readings of a single indicator probability that can be
computed in closed form. Using the exact rung masses and
`P(count = j) = sum_r C(200,j) p_r^j (1 - M_r)^(200-j)`:

| floor count `j` | `P(count = j)` `[model]` | cumulative |
| --- | --- | --- |
| 1 | **53.671%** | 53.671% |
| 2 | 27.055% | 80.726% |
| 3 | 12.090% | 92.816% |
| 4 | 4.819% | 97.635% |
| 5 | 1.675% | 99.310% |
| 6 | 0.509% | 99.820% |
| 7 | 0.138% | 99.957% |

**Wilson's coverage of `tau_top` is `P(count = 1) = 53.671%`, exactly and identically.** No
simulation was needed, and quoting it to three significant figures across three seeds implied a
precision the quantity does not have. (As a by-product, `P(count >= 4) = 7.18%` reproduces the
first version's "the observed `2.0%` sits at the 93rd percentile of the model's own predictive
distribution".)

### 7.1 What the headline does under perturbation, which is the honest version

`[model]` Coverage as a function of the assumed true floor is a staircase whose risers are the
Wilson lower-endpoint lattice:

| assumed true floor | counts whose Wilson interval covers | coverage |
| --- | --- | --- |
| below `0.088317%` | none | **0.000%** |
| `0.088317%` to `0.274666%` | `1` | **53.671%** |
| `0.274666%` to `0.511424%` | `1, 2` | **80.726%** |
| `0.511424%` to `0.780443%` | `1, 2, 3` | 92.816% |
| `0.780443%` upward | `1, 2, 3, 4` | 97.635% |

The model's point value sits `0.0021` points below a riser. Two consequences, and they are the
headline:

1. **A 0.8%-relative move in an unmeasured parameter moves the answer by 27 points.** Pushing
   `tau_top` from `0.272573%` to `0.274666%` takes coverage from 53.7% to 80.7%.
2. **The knob that moves it is the calibration target, and it is far less certain than the move
   requires.** `d(tau_top)/d(N=20 atom) = 0.2095`, so recalibrating to an `N=20` atom of
   `3.13908%` instead of `3.129089%` puts `tau_top` on the far side of the riser: a shift of
   **`0.0100` points** flips the headline from 53.7% to 80.7%. The first version's own
   Monte-Carlo estimate of that atom (`3.134%`) differs from the exact value by `0.0049`
   points -- half the flip distance, and it landed on the same side only by luck. The atom's
   own question-bootstrap interval is `[1.79%, 4.69%]`, a span of `2.90` points, about
   **290 times** the flip distance.

And in the direction section 6.1 says the model errs -- too fat in the deep tail -- the
staircase runs the other way and falls off a cliff: for any `tau_top` below `0.088317%`,
Wilson's coverage is **0%**, not 53.7%.

**Restated honestly:** Wilson's coverage of `tau_top` under this model is not `53.7%`. It is
`P(floor count = 1)`, a number that takes the values `0%`, `53.7%`, `80.7%` or `92.8%` according
to which cell of a four-cell lattice the true floor falls in, and the data does not locate the
true floor to within one cell. The bootstrap is the one number here that is robust to all of
this: its lower endpoint of `0.5%` exceeds every `tau_top` in the whole plausible range, so its
coverage is **0.00%** throughout `[0%, 0.5%]` and no perturbation rescues it.

---

## 8. The zero branch is live, and it flips the coverage headline

This is the second defect. **Its arithmetic reproduces exactly. Its inference does not, and the
correction matters in the opposite direction from the one intended.**

### 8.1 What reproduces

`[measured]` The U-statistic values are exactly as claimed, and I re-derived them independently
by two routes (exhaustive subset enumeration at `k = 38, 39, 40`; full independence polynomial
for all `k`):

- `U_39 = 0` exactly -- not one of the `8,000` 39-subsets across the 200 questions is
  all-distinct.
- `U_40 = 0` exactly.
- `U_38 = 21 / (780 x 200) = 7/52000 = 0.013462%`, contributed by six questions:
  `qz_2135`, `qz_3833`, `qz_3927`, `qz_4127` (4 each), `qz_2884` (3), `dpql_1061` (2).
- The 97.5% bootstrap upper bound on `U_38` over questions is **0.025641%** -- matching the
  `0.0256%` put to me, to four significant figures.

Against the model's `0.272573% + 0.792396% = 1.065%` on rungs 39 and 40, that is the claimed
factor of forty (`1.065 / 0.0256 = 41.6`).

### 8.2 What does not reproduce: `0.0256%` is not a bound

`[bounded]` **The 97.5% bootstrap upper bound on `U_38` is not a valid upper bound on `D_38`,
and it fails in exactly the direction that would make the argument work.** The bootstrap
resamples from an empirical distribution of per-question values whose largest element is
`4/780 = 0.0051`. But `D_38` is dominated by a stratum that is absent from the sample: a
question with `K = 40` contributes `x_38 = 1`, and one with `K = 39` contributes `0.0987`. A
resampling scheme that has never seen such a question cannot produce one, so the bound it
returns is anti-conservative by construction.

Measured. Simulate pools from the calibrated model, in which the true `D_38 = 0.356915%`, and
compute each pool's own 97.5% bootstrap upper bound:

| | |
| --- | --- |
| pools where the bound falls **below** the truth | **315 / 600 = 52.5%** |
| failure rate a valid 97.5% upper bound may have | 2.5% |

A bound that fails 52.5% of the time is not a bound. The "factor of forty" is therefore not a
model-free cap on the model's deep tail, and the first version's caveat 3 cannot be rewritten
around it.

**The valid model-free bound is M4 and it is much weaker:** `P(K >= 39) <= 1.8845%` (Wilson) or
`<= 1.8275%` (Clopper-Pearson). The model's `1.065%` sits **inside** it. `0/200` does not refute
the model; it is a `p = 0.1175` outcome under it.

The deeper reason the U-statistic buys so little: `8,000` 39-subsets sound like a lot of
evidence, but they are `40` heavily dependent subsets within each of `200` questions. The
effective sample size for a question-level rate is `200`, not `8,000`, and `200` observations
of a zero cannot distinguish `0` from `0.3%`.

### 8.3 The rewritten caveat, and why the branch is live anyway

The first version's caveat 3 dismissed the zero branch because "the calibrated model puts
`0.27% + 0.79% = 1.07%` on those two rungs". That is circular -- it dismisses a hypothesis about
the population by citing a model whose only support in that region is extrapolation (section
6.1). The caveat should read:

> The population may assign exactly zero probability to a question producing 39 or 40 mutually
> inequivalent answers out of 40. Nothing in the data excludes it: no question reached `K >= 39`
> `[measured]`, no subset of any question's 40 answers is a 39-element independent set
> `[measured]`, and the model-free bound on the rate is `[0%, 1.88%]` `[bounded]`, which
> contains both zero and the fitted model's `1.065%`. The fitted model's mass on those rungs is
> an extrapolation from `k <= 30`, where it is validated, into `k >= 39`, where it over-predicts
> the measured subset curve by more than a factor of ten `[model]`.

### 8.4 And this is where the ruling's stated reason breaks

`[measured, plus a plug-in population]` Take the zero branch seriously and price it. Let the
population be the empirical rung distribution over the 200 observed questions -- top of support
at `(2, 2, 1^36)` with mass `tau* = 2.0%`, nothing above it -- and compute the floor-count
distribution exactly, as in section 7:

| population | `P(pool max reaches the top rung)` | Wilson coverage | bootstrap `[0.5, 4.0]` coverage |
| --- | --- | --- | --- |
| calibrated Ewens (`tau_top = 0.2726%`) | 42.1% | **53.67%** | **0.00%** |
| zero branch (`tau* = 2.0%`) | **98.24%** | **95.06%** | **100%** |

**Under the branch the data cannot exclude, Wilson has its nominal coverage and the bootstrap
covers too.** And it is not a knife edge in `tau*` either -- the zero branch is well behaved
across the whole range the data allows:

| `tau*` `[model: plug-in]` | `P(pool sees it)` | Wilson coverage |
| --- | --- | --- |
| 0.25% | 0.394 | 56.33% |
| 0.50% | 0.633 | 80.99% |
| 1.00% | 0.866 | 93.82% |
| 1.50% | 0.951 | 96.70% |
| **2.00%** | **0.982** | **95.06%** |
| 3.00% | 0.998 | 94.49% |
| 5.00% | 1.000 | 96.72% |

Once `tau*` exceeds about 1%, the top-of-support rung is one a 200-pool essentially always
reaches, the selection stops biting, and Wilson recovers. **"Both estimators fail" and "the
estimand dissolves" are statements about one branch, not about the data.**

---

## 9. Objection 1 adjudicated: it bites, and resizing the bootstrap does not fix it

`[model]` The n-out-of-n bootstrap is inconsistent for functionals of a sample maximum, and the
standard remedy does not apply here, which is worth saying rather than reaching for
`m`-out-of-`n` and moving on. `m`-out-of-`n` bootstrap and subsampling repair the *sampling
distribution* of an estimator of a fixed population functional. Here the functional itself moves
with the pool size. Measured on the calibrated population, against a true floor constant at
`0.2726%`:

| pool size `m` | mean `floor_hat` | median | `m * floor_hat` | `P(pool max reaches the true top rung)` |
| --- | --- | --- | --- | --- |
| 50 | 2.4201% | 2.000% | 1.21 | 0.131 |
| 100 | 1.4376% | 1.000% | 1.44 | 0.243 |
| **200** | **0.8775%** | 0.500% | 1.76 | 0.421 |
| 400 | 0.5587% | 0.500% | 2.23 | 0.658 |
| 800 | 0.3571% | 0.250% | 2.86 | 0.896 |
| 1424 | 0.2888% | 0.281% | 4.11 | 0.978 |
| 4000 | 0.2744% | 0.275% | 10.97 | 1.000 |

If the floor were a population parameter, column 2 would be flat. It is not; `floor_hat` falls
roughly like `c/m` until the pool is large enough to hit the true top rung essentially always.
**A resizing scheme cannot fix an estimator whose target moves with the resizing.**

Two caveats now attach to this table that did not before. First, it is `[model]` throughout, and
the model is the one section 6.1 shows is too fat in this region -- with a smaller true
`tau_top` the whole table shifts right and the `n = 1424` row stops being reassuring. Second,
under the zero branch of M5 the table would be nearly flat from `m = 200` upward, because the
top of support is a rung a 200-pool already reaches 98% of the time. The *qualitative* point
survives both -- the target moves with `m` unless the pool reaches the top of support -- but the
`n = 1424` extension should not be costed off this table.

---

## 10. Objection 2 adjudicated: the Discussion's argument is inverted

The Discussion (`paper/sections/discussion.tex`, around line 175) argues:

> Wilson's lower end excludes 0.5% -- the one value this floor can never fall below on 200
> answers, since the top score is always attained by at least one of them.

`[measured]` The premise is true and the conclusion does not follow. "The estimator can never
return less than `1/200`" is a statement about the estimator's range. "The floor can never fall
below 0.5%" is a statement about the population, and it is false: the population floor is a
proportion in a population much larger than 200 and is under no obligation to be a multiple of
`1/200`. M5's second branch is precisely a family of populations whose floor is far below
`0.5%`, and M4 does not exclude it.

The mass pinning the bootstrap's lower endpoint is `7.9315%` `[measured]`, above the `2.5%`
needed, so the endpoint is placed by construction and carries no information. The upper endpoint
is no better founded: mass strictly above `4.0%` totals `2.0201%` against the `2.5%` needed to
move the 97.5th percentile one lattice step, so `4.0%` versus `4.5%` is decided by `0.48`
percentage points of resample mass -- and it is the difference between the Discussion's claim
and no claim at all. Neither endpoint of `[0.5, 4.0]` is doing statistical work.

**The consistency argument, and it must now be labelled.** `[model]` Sweeping the global
multiplier asks what the world would have to look like for each candidate endpoint to be true:

| for the true `N=40` floor to be | implied `N=20` atom | implied `N=10` atom |
| --- | --- | --- |
| 0.27% (calibrated fit) | 3.12% | 11.82% |
| 0.41% (raw fit) | 3.73% | 13.38% |
| 0.50% (bootstrap lower end) | 4.07% | 14.24% |
| **0.78% (Wilson lower end)** | **5.03%** | **16.58%** |
| **2.00% (the printed point estimate)** | **8.46%** | **24.28%** |
| 4.00% (bootstrap upper end) | 13.51% | 33.97% |
| *measured* `[measured]` | **3.129089%** | **11.992117%** |

This is a **`[model]` argument and the first version presented it as stronger than it is.** It
holds *within the Ewens family*: inside that family, a floor as high as `2.0%` would require an
`N=20` atom of `8.46%`, nearly double the top of its measured interval. What it does not do is
exclude M5's second branch, which lives outside the family altogether -- a population with a
2.0% atom at `(2, 2, 1^36)` and exactly nothing above it reproduces the measured `N=10` and
`N=20` atoms fine, because those atoms are set by the bulk of the distribution and not by its
last two rungs.

What *is* model-free is the direction, and only the direction: the elementary coupling that 40
mutually inequivalent answers requires the first 20 to be mutually inequivalent, so
`P(cap at 40) <= P(cap at 20) = 3.129089%` `[measured]`. The model supplies the tightening; the
coupling supplies the direction; and the tightening is the part section 6.1 shows is unreliable.

---

## 11. Treatment (c): what the plan pre-registers, and why it is still the answer

**The brief's description of (c) is half wrong, and the half that is wrong matters.**
`results/n_scaling_plan.md` does *not* pre-register an estimator-free count. It pre-registers
**Wilson** and derives a count from it (lines 308-310 and 402-406):

> the Wilson upper bound clears 5% only when at most **3 of the 200** negatives sit at the cap,
> i.e. a floor of **1.5%** or less

But read what the criterion is a criterion *on*: **negatives at the cap**. Both statements say
"at the cap", twice each. The pre-registered count is the ceiling-atom count and the
pre-registered quantity is `tau_cap`; the plan identifies it with the floor (line 277) because
at every budget the plan was written against, they were the same number.

**The observed value of the pre-registered count is 0, not 4** `[measured]`. Comparing the
observed `4` against the pre-registered `3` compares the first-firing-point count against a
threshold derived for the at-cap count -- different quantities, which is the entire content of
`floor_cells()`'s docstring in `scripts/n_scaling_grid.py`. On the quantity the plan
pre-registered, with the estimator the plan pre-registered, the criterion is met with three
counts to spare: `0/200`, Wilson upper bound `1.8845%`.

**And treatment (c) is the only one of the three whose validity does not depend on the branch,**
because its threshold really is fixed in advance. `[model]` Wilson's one-sided upper bound on a
binomial proportion at a fixed threshold:

| true cap mass | Wilson two-sided | **Wilson upper >= truth** | Clopper-Pearson two-sided |
| --- | --- | --- | --- |
| 0.10% | 98.25% | **100.00%** | 98.25% |
| 0.27% | 89.76% | **100.00%** | 98.26% |
| 0.50% | 92.02% | **100.00%** | 98.13% |
| 1.00% | 94.83% | **100.00%** | 98.40% |
| 1.50% | 96.76% | **100.00%** | 98.87% |
| 2.00% | 93.31% | 98.24% | 96.22% |

The one-sided upper bound -- the only direction the concession uses -- has 100% coverage across
the entire plausible range, and in the zero branch `tau_cap = 0` exactly, so it holds there too.
(The two-sided dip to 89.8% at 0.27% is the same discreteness knife edge section 7 anatomises:
Wilson's lower endpoint at `k = 2` is `0.274666%`, `0.0021` points above the model's point
value. The first version noticed this here and failed to carry it across to its own coverage
headline, which is defect 1.)

**Three caveats, so this is adopted for the right reason.**

1. The plan did not anticipate the atom emptying. Its identity "ceiling-atom mass = minimum
   non-zero achievable FPR" is what broke, and the paper's switch to the first firing point is
   an unpre-registered re-specification of the row. Invoking the plan's criterion is the
   *literal* pre-registration, but the paper must disclose that the two quantities came apart.
   It is already disclosing a gate re-spec (the locked judge at 0.93); this belongs in the same
   list.
2. The plan's own section 6 table is mislabelled. Its column reads "can n=200 certify 'no 5%
   operating point'?" and answers "yes, upper bound below 5%" for a true floor of 1.0% -- but an
   upper bound below 5% certifies that a sub-5% operating point *does* exist. The arithmetic and
   the intent are unambiguous (line 425: "put a one-sided certificate under 5%"); the label is
   inverted, and since the criterion hangs on this sentence it should be fixed.
3. **(rewritten -- see section 8.3)** The certification rests on the possibility that the
   population assigns zero probability to 39 or 40 mutually inequivalent answers. That branch is
   **not excluded by anything in the data**, and in it the floor is `4/200` with Wilson
   `[0.78, 5.03]` and the current concession stands. The saving grace is that treatment (c) is
   valid in that branch too -- `tau_cap = 0` and the one-sided Wilson bound of `1.9%` still
   holds -- so adopting (c) does not require betting on a branch. It is the *2.0%-with-no-interval*
   half of the row, not the at-cap half, that the branch bears on, and section 2 now words that
   half so it is true either way.

---

## 12. Row 2: the achieved 5%-budget operating point

`[model]` Same machinery; statistic changed to "the largest achievable FPR at or below 5% on the
pool" (observed `10/200 = 5.0%`), estimand changed to the true population FPR of that fitted
threshold. 12,000 pools, 3,000 bootstrap resamples each.

| | value |
| --- | --- |
| true FPR of the fitted threshold on fresh data | **5.1697%** |
| in-sample achieved FPR | 4.6699% |
| **Wilson `[2.7, 9.0]` coverage** | **94.44%** (mean width 6.03 pts) |
| **question bootstrap `[2.5, 5.0]` coverage** | **54.81%** (mean width 2.56 pts) |
| bootstrap upper endpoint pinned at the 5% budget | **100.00% of pools** |

**None of the three defects touches this row**, and that is worth stating because row 2 is where
the opposite ruling lands. The floor is an extreme order statistic -- the estimand sits at the
edge of the support, the pool rarely reaches it, and no interval built from the pool can price
it. The 5%-budget point is an *interior* quantile: the pool has 10 answers above the threshold
and roughly 190 below, the empirical quantile is stable, and Wilson at a fixed count recovers
its nominal coverage. Nothing about it depends on the deep tail where the model is misfit, and
nothing about it depends on which branch of M5 is true. **Data selection is not what breaks
Wilson; being at the boundary of the support is.** That is the sentence the Discussion needs,
and it keeps the two rows consistent while ruling them opposite ways.

**The bootstrap here is affirmatively misleading, not merely uninformative.** Its upper endpoint
is `5.0%` in 100.00% of pools because the statistic can never exceed the budget by construction.
So `[2.5, 5.0]` asserts at 97.5% confidence that the operating point is at most 5% -- a fact
about the estimator's range restated as a fact about the world -- while the fitted rule's true
rate exceeds 5% roughly half the time. This is the identical error to row 1's pinned lower
endpoint, mirrored onto the other end. `results/replay_control.md` shows the degeneracy in the
open at smaller budgets: `0.0% [0.0%, 0.0%]` at `N=10` and `3.1% [0.0%, 5.0%]` at `N=20`.

**The new finding the paper should take from this row:** the in-sample achieved rate understates
the deployed rate by about half a point (`4.67%` in sample against `5.17%` deployed), because
choosing the largest achievable rate at or below the budget selects rungs where the empirical
count happened to fall low. The Abstract's existing refusal to read `5.0%` as a demonstration
that a sub-5% operating point exists is therefore quantitatively correct, and it can now say
why.

---

## 13. Does the ruling survive?

**The ruling's output survives unchanged. Its stated reason does not, and the reason has to be
replaced rather than repaired.**

**What survives.** Print `0/200 = 0.0% [0.0, 1.9]` for the at-cap mass and `2.0%` beside it with
no interval; retire both `[0.8, 5.03]` and `[0.5, 4.0]` as intervals for the floor; print Wilson
for row 2 and retire the bootstrap there. Every one of those instructions is now supported by
section 1, which uses no model at all. That is a strictly better footing than the first version
had, because the first version rested the row-1 half of it on a coverage simulation.

**What does not survive: "the estimand dissolves when the atom empties."** That is a
branch-conditional claim dressed as an unconditional one. Section 8.4 measures Wilson at
**95.06%** under the zero branch, where the estimand does not dissolve, the pool max is the
population's top rung 98% of the time, and even the bootstrap covers. The data does not exclude
that branch: `p = 0.1175` for the fitted model against `0/200`, and the valid model-free bound
`[0%, 1.88%]` contains both zero and the model's `1.065%`.

The replacement is stronger, not weaker, because it is model-free: **`tau_top` is not
identified.** It equals `2.0%` if `P(K >= 39)` is exactly zero and can be arbitrarily small
otherwise, and no amount of data at `n = 200` distinguishes those cases. An estimand whose value
jumps by more than two orders of magnitude across a hypothesis the sample cannot test does not
have a confidence interval, and that argument needs neither Ewens nor a coverage simulation.

**On the reading I was asked to check.** The suggestion was that the ruling gets *stronger*: if
the model overstates the deep tail, the true floor is even further below the printed `2.0%`,
making "the estimand dissolves" more true. **That is half right and the other half is inverted,
and the inverted half is the one that matters.** Yes -- *within* the branch where
`P(K >= 39) > 0`, a thinner deep tail pushes `tau_top` down, and once it drops below
`0.088317%` Wilson's coverage goes to **0%** rather than 53.7%, so both intervals fail harder.
But the same evidence that thins the deep tail also raises the standing of the branch in which
`P(K >= 39)` is exactly zero -- and in that branch the floor is `2.0%`, Wilson has 95.06%
coverage, and the estimand is an ordinary binomial proportion. The deep-tail misfit does not
move the estimand down. **It widens the estimand's range in both directions at once**, which is
non-identification rather than a smaller floor. Adopting the proposed reading would have put a
directional claim in the paper that the evidence does not support.

**Where the conclusion does still touch the model.** Three places, all now labelled. The `53.7%`
coverage figure and everything in sections 7 and 9 are `[model]`. The consistency sweep in
section 10 is `[model]` and does not exclude the zero branch. And the `n = 1424` extension
costing should not be read off section 9's table. None of these carries the ruling; all of them
were doing so in the first version.

**Residual risk to the paper, stated plainly.** If a referee accepts the zero branch, the
paper's `2.0% [0.78, 5.03]` is defensible and the concession the Abstract currently makes
stands. The paper's protection is that treatment (c) is valid in both branches -- section 11's
one-sided Wilson bound on `tau_cap` holds whether or not the population can reach the cap -- so
the printed row survives the referee either way. What does *not* survive is any sentence
asserting that `2.0%` is purely a resolution artifact. Section 2 supplies wording that is true
in both branches.

---

## 14. Suggested text

Not edits -- this ruling touches no file but itself. Offered so it is falsifiable against
something concrete.

**Abstract**, replacing "the floor is an ordinary order statistic, `2.0%` [`0.8`, `5.03`], whose
interval does not exclude `5%`" (`paper/main.tex` lines 48-49):

> Running the fair pool's 200 correct answers out to `N=40` empties the atom: no clean correct
> answer reaches `ln 40` (`0/200`, at most `1.9%`), and with the atom gone so is the
> obstruction. What 200 answers cannot then do is locate the floor. The cheapest alarm they can
> exhibit costs `2.0%`, but whether that is a property of the detector or of the pool's size
> turns on whether the population can ever produce 39 mutually inequivalent answers out of 40 --
> a question 200 answers cannot settle -- so we quote no interval for it.

**Conclusion** (`paper/sections/conclusion.tex` lines 22-28), same substitution, plus: delete
"would need the Wilson upper bound on the floor to fall below 5%, and on these 200 correct
answers it is 5.03 -- over the line rather than under it". The pre-registered bound is on the
at-cap mass and it is `1.9%`, under the line.

**Discussion** (lines 168-177): delete the sentence beginning "That is not a widening" through
"attained by at least one of them", and the claim that the `N=40` floor is "outside Wilson's
reach" -- the latter is exactly as wrong as the sentence it replaces, because under the zero
branch Wilson reaches it fine. Replace with the non-identification reason: the floor's threshold
is the top rung this pool happened to reach; whether that is the population's top rung is not
determinable from 200 answers; and the two answers differ by more than two orders of magnitude.

**`results/replay_control.md`**: retire `5.0% [2.5%, 5.0%]` for the achieved-FPR-at-budget rows
in favour of Wilson, or relabel them as ranges of the estimator rather than confidence
intervals. The `0.0% [0.0%, 0.0%]` cell at `N=10` is the same defect fully visible.

**One number the paper could add and currently does not have.** The exact subset curve of
section 1 (M3) is a measured, model-free description of how the atom empties with budget:
`11.992117%` at `N=10`, `3.129089%` at `N=20`, `0.013462%` at `N=38`, `0` at `N=39` and `N=40`.
It is computed exactly rather than by replicate sampling, so it replaces the "20 replicates,
median 12.0%, range 10.0-14.5%" line in `results/n_scaling_grid.md` with a number that has no
Monte Carlo error. That is a free tightening and it is owned by whoever holds that file.

---

## 15. Reproduction

Everything is CPU-only and deterministic given the seeds. Working files are in the session
scratchpad: `base.py` (loader and an independent union-find replay), `ustat2.py` (exhaustive
independent-set counts at `k = 38, 39, 40`), `exactU.py` (the full exact `U_k` curve by
independence polynomial, branch-and-memo), `ewens.py` (CRP fit, calibration, the model-vs-data
table), `coverage.py` (exact rung masses, the exact floor-count distribution, the Wilson
staircase), `branch.py` (bootstrap-bound validity, the zero branch), `verify.py` (ladder and
closed-form bootstrap).

The chain is reconstructible from this file alone. Five ingredients:

1. union-find on the recorded 780-bit triangle, for the observed partitions;
2. **the independence polynomial of each question's verdict graph**, for the exact `U_k` curve
   -- note that a subset's clustering is recomputed inside the subset, so all-distinct means
   *independent set*, not *transversal of the full-40 blocks*. Getting this wrong understates
   `U_10` as `9.264%` instead of `11.992%`;
3. `alpha_q` solving `sum_{i<40} alpha/(alpha+i) = K_q`, and a single global multiplier pinned
   to the exact `U_20`;
4. the Ewens sampling formula `P(a) = n! / theta^(n) * prod_j (theta/j)^{a_j} / a_j!` for rung
   masses, enumerated over partitions of 40 with `K >= 28`;
5. `P(count = j) = sum_r C(200,j) p_r^j (1 - M_r)^(200-j)` for the floor-count distribution --
   the same closed form serves the bootstrap (with pool proportions) and the coverage
   calculation (with population masses), which is why neither needs Monte Carlo.

Seeds: model goodness-of-fit at `k = 38`, `424242` (4,000 pools); bootstrap-bound validity, `7`
(600 pools x 2,000 resamples); `U_38` bootstrap UCB, `20260819` (200,000 resamples). The
row-1 coverage figures, the floor-count distribution, the Wilson staircase and the section-4
bootstrap are all **exact** and carry no seed.

Verified not disturbed: WSL `Ubuntu-24.04` PID 473 still running at exit.
