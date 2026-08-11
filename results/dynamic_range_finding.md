# How much dynamic range does semantic entropy actually have? (rev. 2026-08-07)

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
| distinct entropy values across all 97 targets | **22** |

## What can and cannot be concluded

**Solid.** The score is coarse and crowded at the top: 22 attainable values over 97 targets,
a quarter of *correct* answers already in the top decile, a tenth already pinned at the
maximum before anything is done to them. Those are direct counts on clean data and they do
not depend on the class separation being significant.

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
- All 22 distinct values come from the 80 correct targets; the 17 wrong targets contribute
  10 values, every one a subset. The wrong-group mean is 17 draws over 10 atoms.

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
