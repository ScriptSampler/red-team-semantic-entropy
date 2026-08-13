# How much dynamic range does semantic entropy actually have? (rev. 2026-08-07)

> ⚠ **RETIRED (2026-08-13): "22 distinct values" is not a property of the estimator, and it
> was never "attainable".** The number of distinct values a score *realises* is monotone in
> the number of targets scored, so it is a statement about the sample. This is the artifact
> that fed the retired claim into the paper. `results/fair_pool_granularity.md` (2026-08-13)
> settles it, by enumeration and by rarefaction:
>
> | quantity | value |
> |---|---|
> | **ATTAINABLE** values at N=10 (enumerating the p(10) = 42 partitions) | **39** |
> | attainable values in the top tenth of the range | **2** (2.1640 and ln 10) |
> | REALISED by the attacked 80 correct targets | 22 |
> | E[realised] for a random 80 from the same stratum | **23.0** (MC sd 1.59) — so 22 is the **37th percentile**, an unremarkable draw |
> | realised by the same population at n=200 / n=2000 | **28** / **35** (still only 35/39) |
>
> Every "22 attainable values" below is therefore a **category error**: 39 are attainable,
> 22 were realised. The n-invariant replacement is the lattice — **39 attainable values at
> N=10, of which 2 lie in the top tenth of the range**. Corrections are struck through in
> place rather than deleted. Provenance: critique_log entry 33 §4 (2026-08-13); commit `e6e7629`
> removed the claim from all four paper sites.
>
> **The companion claim is dead too.** "Granularity is NON-RELAXABLE — raising N does not buy
> range" is false: N=20 has **455** attainable values, ~12x the N=10 lattice. What survives
> is narrower and sharper: N=20 takes the **top decile only from 2 points to 7**, so
> relaxation is weakest exactly where a false alarm has to land. See
> `results/n20_verdict.md` and critique_log entry 33 §3 (commit `4683e26`).
>
> **Denominator note.** Every "97 targets" figure below is a snapshot of 2026-08-07, when the
> hide arm stood at n=17. That cell is still running (n=46 on 2026-08-13, heading for 80), so
> the 97 and the 17 are stale by construction until it finishes. The 80-denominated
> correct-stratum counts (8/80 at the cap, 21/80 in the top decile) are unaffected — the FA
> arm is complete.

Measured on the **clean, unattacked** scores of the definitive pool (SE, N=10, TriviaQA,
Llama-3.1-8B-Instruct 4-bit): 80 targets the model answers correctly, 17 it answers wrongly.
Nothing here depends on the attack working or on any pending run.

**This revision replaces the 2026-08-02 version, three of whose claims independent
verification refuted.** The corrections are kept visible below rather than quietly dropped,
because two of them were errors I had explicitly warned myself against.

## What the clean scores look like

| quantity | value |
|---|---|
| clean entropy, **correct** answers (n=80) | mean 1.477, sd 0.667 |
| clean entropy, **wrong** answers (n=17) | mean 1.661, sd 0.598 |
| class separation, mean(wrong) − mean(correct) | **+0.184 nats**, 95% CI **[−0.136, +0.488]**, permutation **p = 0.296** |
| Cohen's d | 0.28 (**not significantly different from 0**) |
| correct answers at the ln(10) ceiling | **8/80 = 10%** |
| correct answers in the top decile of the scale | **21/80 = 26%** |
| wrong answers at the ceiling | **4/17 = 24%** |
| distinct entropy values ~~across all 97 targets~~ **realised** by these 97 targets (a sample statistic; **39** are attainable at N=10) | 22 |

## ⚠ POPULATION CORRECTION (2026-08-11) — the separation claim is withdrawn from the spine

Everything above is computed on the **attacked subset** (the 80 FA + 17 hide campaign
targets), and the hide arm is **truncated mid-campaign at n=17**. That is not the population
a claim about "the detector" may be made on. The fair pool says something materially
different:

| population | wrong | right | separation | implied AUROC |
|---|---|---|---|---|
| **fair pool** (the right one) | 1.843 | 1.380 | **0.463 nats**, d ≈ 0.76 | **0.704** |
| attacked subset (used above) | 1.661 (n=17) | 1.477 (n=80) | 0.184, d = 0.28 | 0.579 |

The attacked-subset separation is **2.5× smaller**, and its implied AUROC (0.579) is exactly
the attacked-subset figure `fa_n80_milestone.md` quarantined as not-to-be-confused-with the
fair pool's 0.704. I used the quarantined number as a headline anyway — the second time this
project has attached a real number to the wrong population.

**Consequence, stated plainly: the claim "the detector's class separation is a fraction of
its own noise" does not survive.** On the fair pool d ≈ 0.76 and AUROC ≈ 0.70 — a moderate
detector, not a useless one. That claim is removed from the Abstract, Discussion and
Conclusion rather than restated with a caveat, because at d ≈ 0.76 it is simply not true.

**What survives, and is still on the false-alarm-relevant region:** the crowding at the top
of the scale (10% of clean correct answers exactly at the cap, 26% in the top decile) and the
granularity limit (~~22 attainable values~~ **39 attainable values at N=10, only 2 of them
in the top tenth of the range**; 22 is merely what these targets realised). Those are direct counts, they concern the top of
the range where the false-alarm attack operates, and they do not depend on the class
separation at all. The honest scope is **"little usable range at the top of the scale"**, not
"the detector barely separates the classes".

## What can and cannot be concluded

**Solid.** The score is coarse and crowded at the top: ~~22 attainable values over 97
targets~~ **only 39 values are attainable at N=10 and just 2 of them lie in the top tenth of
the range** (22 was the count these 97 targets happened to realise — see the banner: it is
the 37th percentile of what a random 80 produces, and it is not "attainable"),
a quarter of *correct* answers already in the top decile, a tenth already pinned at the
maximum before anything is done to them. The crowding counts are direct counts on clean data
and they do not depend on the class separation being significant; the lattice count is an
enumeration and depends on no data at all.

**Not solid — and previously overstated here:**

- **The separation is not statistically significant.** +0.184 nats has a 95% CI of
  [−0.136, +0.488] and a permutation p of 0.296, on n=17 wrong answers. It is a sample
  statistic from a small, still-growing stratum, **not a fixed property of the detector**.
  On the repo's own fair-pool strata the same quantity is +0.463 nats, 2.5× larger — so
  even its magnitude is unsettled.
- **d = 0.28 does not correspond to AUROC 0.704.** It implies AUROC = Φ(d/√2) = **0.579**,
  which is exactly what a Mann-Whitney on this pool returns. AUROC 0.704 corresponds to
  d = 0.758. The earlier version reconciled the two — which `fa_n80_milestone.md` had
  explicitly flagged as a trap (the 0.704 is the *fair pool*; 0.579 is the *attacked
  subset*; different populations). I made exactly the error I had written down a warning
  about. The reconciliation is withdrawn.
- **The "attack moves ~2.8× the detector's whole signal" headline is withdrawn.** Its
  bootstrap CI is [−24, +28] — 12.6% of resamples are negative — because the denominator is
  a near-zero, non-significant quantity. Censoring-corrected (Tobit, right-censored at the
  ceiling) the ratio is **~2.13×**; on fair-pool strata **~1.13×**. The defensible statement
  is **"roughly one class separation, not three"**, and even that should carry its interval.
- **The wrong-answer group is censored 2.4× more than the correct group** (24% vs 10% at
  the cap). That biases the measured separation *downward*, so the true separation may be
  larger than 0.184 — a caveat that cuts against the finding and must be stated.
- All 22 **realised** distinct values come from the 80 correct targets; the 17 wrong targets
  contribute 10 values, every one a subset. The wrong-group mean is 17 draws over 10 atoms.
  (Both counts are sample statistics and both grow with n — the wrong stratum is at n=46 and
  still climbing. Neither may be quoted as a property of the estimator.)

## What to say in the paper

Report the **coarseness and crowding** — those are robust. Do **not** claim a small
correct-vs-wrong separation as a measured property until the hide cell completes and the
wrong stratum reaches n=80; at n=17 the interval is too wide to support it, and censoring
biases it in the inconvenient direction.

The ratio-to-detector-signal framing remains the right *currency* for an effect size — it is
scale-free and immune to the log(N) censoring that makes raw nats unreportable for the
false-alarm direction — but its denominator must be estimated on the completed pool, and it
must be reported with an interval rather than as a point.

Data: `wk9_def/triviaqa_se_{false_alarm,hide}.jsonl`. Analysis: `scripts/dynamic_range.py`.
Corrections: `results/CORRECTIONS_2026-08-02.md` (C3–C7).
