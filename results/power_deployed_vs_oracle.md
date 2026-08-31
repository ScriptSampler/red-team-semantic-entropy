# Deployed (analytic-null) vs oracle-calibrated power, same draws, stated levels

Producing script: `scripts/power_sim_deployed.py`. Companion to
`results/power_randomized.md`, which reported the ORACLE column only. The deployed
column is the test the pipeline actually runs: `se.stats.exceedance_test`'s analytic
BetaBinomial null, no access to the true simulated null.

DGP imported verbatim from `scripts/power_sim_randomized.py`. Headroom from `data\cache\attacks\wk9_defb_snap\triviaqa_se_false_alarm.jsonl`, mirrored to `results/fa80_headroom.md` so this reproduces without the cache. Attacker candidates N = 181, nominal alpha = 0.05.
Per-draw exponential scale 0.12, calibrated to 45% attack saturation against the observed 49%.

**Sections A-D are the PLANNED design** (80 targets, one benign budget m shared by all of them). **Section E is the design that ran**, whose per-target budgets differ, and it is section E the paper's non-rejection has to be read against.

Rules: **deployed** = analytic p <= alpha on one tie-break draw; **dep.-median** = median p over 25 tie-break draws (what `exceedance_test_over_seeds` ships); **oracle** = S <= 5th percentile of a separate simulated null, which the deployed test cannot compute.

## A. Published settings - reproduces results/power_randomized.md's oracle column

Simulated draws: 2500 H0 trials for the oracle critical value, 400 trials each for the achieved level and for every power cell; seed 11. Level and power are measured on the SAME draws for every rule, so the columns are paired and differ only in the cut applied. `nominal dep.` is the analytic null's own tail at the deployed cut — what the test BELIEVES its level is; `level dep.` is what it achieves on this DGP, from the 400-trial sample, and `(big null)` repeats it on the 2500-trial one.

| m | crit (deployed) | crit (oracle) | nominal dep. | level dep. | level dep. (big null) | level dep.-median | level oracle | pow 2x dep. | pow 2x dep.-med | pow 2x oracle | pow 3x dep. | pow 3x oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 4.0 | 0.030 | 0.020 | 0.028 | 0.005 | 0.058 | **0.33** | 0.33 | 0.51 | 0.70 | 0.83 |
| 30 | 6 | 7.0 | 0.031 | 0.020 | 0.032 | 0.013 | 0.052 | **0.50** | 0.54 | 0.67 | 0.81 | 0.92 |
| 50 | 13 | 14.0 | 0.044 | 0.043 | 0.035 | 0.020 | 0.068 | **0.78** | 0.85 | 0.84 | 0.97 | 0.99 |
| 80 | 23 | 25.0 | 0.041 | 0.030 | 0.028 | 0.013 | 0.058 | **0.88** | 0.93 | 0.94 | 1.00 | 1.00 |

At 400 trials an achieved level near 0.05 carries a standard error of about 0.011, so read these levels as indicative and the ones in table B as the measurement.

## B. High precision - the numbers to quote

Simulated draws: 20000 H0 trials for the oracle critical value, 4000 trials each for the achieved level and for every power cell; seed 11. Level and power are measured on the SAME draws for every rule, so the columns are paired and differ only in the cut applied. `nominal dep.` is the analytic null's own tail at the deployed cut — what the test BELIEVES its level is; `level dep.` is what it achieves on this DGP, from the 4000-trial sample, and `(big null)` repeats it on the 20000-trial one.

| m | crit (deployed) | crit (oracle) | nominal dep. | level dep. | level dep. (big null) | level dep.-median | level oracle | pow 2x dep. | pow 2x dep.-med | pow 2x oracle | pow 3x dep. | pow 3x oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 4.0 | 0.030 | 0.028 | 0.028 | 0.008 | 0.066 | **0.35** | 0.36 | 0.55 | 0.65 | 0.83 |
| 30 | 6 | 7.0 | 0.031 | 0.025 | 0.029 | 0.006 | 0.056 | **0.51** | 0.54 | 0.66 | 0.83 | 0.91 |
| 50 | 13 | 14.0 | 0.044 | 0.041 | 0.037 | 0.017 | 0.064 | **0.77** | 0.83 | 0.84 | 0.97 | 0.99 |
| 80 | 23 | 25.0 | 0.041 | 0.034 | 0.029 | 0.013 | 0.070 | **0.90** | 0.94 | 0.95 | 1.00 | 1.00 |

Standard error on a level near 0.05 at 4000 trials: 0.0034.

## C. Level-matched: is the deployed STATISTIC weaker, or just stricter?

With a common benign budget the analytic p-value is a strictly increasing function
of the exceedance total S alone, so the deployed test rejects iff S <= c_analytic and
the oracle test iff S <= c_oracle: the same rule on the same statistic at different
cut points. Comparing their powers at face value therefore compares two levels, not
two tests. The columns below read both at the ORACLE's achieved level.

| m | level oracle | pow 2x oracle | pow 2x deployed, re-cut to that level | cut | delta |
|---|---|---|---|---|---|
| 20 | 0.066 | 0.553 | 0.553 | 4 | +0.000 |
| 30 | 0.056 | 0.658 | 0.658 | 7 | +0.000 |
| 50 | 0.064 | 0.841 | 0.841 | 14 | +0.000 |
| 80 | 0.070 | 0.952 | 0.952 | 25 | +0.000 |

A delta of zero is the expected and correct result: it says the analytic null costs
nothing in discriminating power and everything in level. The deployed test's lower
power is bought conservatism, not a worse statistic - and, unlike the oracle, it is
a level the pipeline can actually claim without knowing the truth it is testing.

The `exact-level` rule below is the best a cut on S can do while honouring alpha on
this DGP; it brackets how much of the deployed/oracle gap is discreteness.

| m | crit dep. | level dep. | pow 2x dep. | crit exact | level exact | pow 2x exact | crit oracle | level oracle | pow 2x oracle |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 0.028 | 0.352 | 3 | 0.028 | 0.352 | 4.0 | 0.066 | 0.553 |
| 30 | 6 | 0.025 | 0.511 | 6 | 0.025 | 0.511 | 7.0 | 0.056 | 0.658 |
| 50 | 13 | 0.041 | 0.769 | 13 | 0.041 | 0.769 | 14.0 | 0.064 | 0.841 |
| 80 | 23 | 0.034 | 0.900 | 24 | 0.048 | 0.930 | 25.0 | 0.070 | 0.952 |

## D. The two cells the paper quotes for the PLANNED design, against what reproduces

`paper/sections/experiments.tex` states that the randomised rule against the analytic
null "reaches power 0.51 at an achieved level of 0.025 for m=30, and 0.77 at 0.041
for the pre-registered m=50", with nominal tails of 0.031 and 0.044 at those cut
points, against an oracle's 0.66 at level 0.056 and 0.84 at 0.064. Those numbers had
no producing artifact before this table. They are the PLANNED design's; section E is
the design that ran.

| cell | quantity | paper | this run (high precision) | published settings | verdict |
|---|---|---|---|---|---|
| m=30 | deployed power @2x | 0.51 | 0.511 | 0.500 | MATCHES |
| m=30 | deployed level, ACHIEVED | 0.025 | 0.025 (on 20000 H0 trials 0.029) | 0.020 | MATCHES |
| m=30 | deployed level, NOMINAL (analytic tail at the cut) | 0.031 | 0.0310 | 0.0310 | MATCHES |
| m=30 | oracle power @2x | 0.66 | 0.658 | 0.670 | MATCHES |
| m=30 | oracle level | 0.056 | 0.056 | 0.052 | MATCHES |
| m=30 | power gap oracle-deployed (derived) | 0.15 | 0.147 | 0.170 | MATCHES |
| m=50 | deployed power @2x | 0.77 | 0.769 | 0.780 | MATCHES |
| m=50 | deployed level, ACHIEVED | 0.041 | 0.041 (on 20000 H0 trials 0.037) | 0.043 | MATCHES |
| m=50 | deployed level, NOMINAL (analytic tail at the cut) | 0.044 | 0.0437 | 0.0437 | MATCHES |
| m=50 | oracle power @2x | 0.84 | 0.841 | 0.845 | MATCHES |
| m=50 | oracle level | 0.064 | 0.064 | 0.068 | MATCHES |
| m=50 | power gap oracle-deployed (derived) | 0.07 | 0.072 | 0.065 | MATCHES |

Both powers must be quoted WITH a level, because at unequal levels powers are not
comparable (section C) - and the level to quote is the achieved one, not the analytic
null's nominal tail, which differs from it by up to a quarter of its own value here.

## E. The design that was planned, and the design that ran

Sections A-D vary one uniform benign budget over 80 targets, which is the experiment
that was DESIGNED. The confirmatory null control closed at 77 usable targets with six
short arms, and the analytic null is the convolution of per-target
BetaBinomial(m_j; 1, N) pmfs, so the cut moves with the whole m-VECTOR and not with n
alone. Until this section existed the shipped design could not be expressed in this
script at all, and the paper quoted the planned design's power for six review rounds.

Realized m-vector, read from `results\null_control_ckpt_defb.jsonl` (80 records, 3 of them with m=0): n = 77, 3704 benign draws, [1x1, 26x1, 27x2, 35x1, 38x1, 50x71]. Identical across the nli, exact, judge arms.
Monte-Carlo cells are 12000 trials at each of the seeds 11, 12, 13, pooled; the analytic rows are exact.

| quantity | planned (n=80, uniform m=50) | realized (n=77, shipped m-vector) |
|---|---|---|
| targets | 80 | 77 |
| benign draws | 4,000 | 3,704 |
| **deployed cut** | **S <= 13** | **S <= 11** |
| nominal level at the cut | 0.0437 | 0.0296 |
| the next cut up | S <= 14 at 0.0689 | S <= 12 at 0.0501 |
| E[S] under H0 (analytic) | 21.98 | 20.35 |
| mean S under H0 (simulated) | 21.96 | 20.33 |
| achieved level | 0.039 | 0.026 |
| **power vs a two-fold effect** | **0.770** | **0.669** |
| power vs a three-fold effect | 0.979 | 0.952 |

Per-seed spread, so the ten-point gap is not read as Monte-Carlo noise:

| design | level by seed | power @2x by seed | power @3x by seed |
|---|---|---|---|
| planned (n=80, uniform m=50) | 0.0397 / 0.0382 / 0.0382 | 0.7664 / 0.7711 / 0.7736 | 0.9765 / 0.9794 / 0.9809 |
| realized (n=77, shipped m-vector) | 0.0288 / 0.0246 / 0.0236 | 0.6740 / 0.6663 / 0.6667 | 0.9527 / 0.9501 / 0.9540 |

### E1. The granularity fact, which is exact

The achievable levels are a ladder on an integer cut, so a design lands on a rung
rather than on alpha. The realized design's ladder steps from
S <= 11 at 0.0296 straight to S <= 12 at 0.0501, which is already over alpha = 0.05. Nothing
lands between them, so its cut is 11 where the planned design's is 13. That much is
exact arithmetic on the analytic null and carries no simulation error.

| design | S <= cut-1 | S <= cut | S <= cut+1 |
|---|---|---|---|
| planned (n=80, uniform m=50) | 12: 0.0261 | **13: 0.0437** | 14: 0.0689 |
| realized (n=77, shipped m-vector) | 10: 0.0163 | **11: 0.0296** | 12: 0.0501 |

### E2. Why a FIXED cut is not a comparison

An earlier version of this section read the two designs at a common cut of 13 and
concluded from it that the realized design is the stronger of the two and that the
whole shortfall is granularity. **That inference was wrong and is retracted here.**
One integer cut does not mean one test: the two designs have different null
distributions, so at S <= 13 they run at different SIZES, and the more permissive
one is more powerful for free. This is the same error section C exists to warn about
for the deployed-versus-oracle pair, made across designs instead of across rules.

| at a fixed cut of 13 | planned (n=80, uniform m=50) | realized (n=77, shipped m-vector) |
|---|---|---|
| nominal level | 0.0437 | 0.0793 |
| achieved level | 0.0387 | 0.0716 |
| power vs two-fold | 0.770 | 0.841 |

The realized design's size at that cut is 1.82 times the
planned design's. The two powers in the last row are measurements and are recorded,
but no comparison between them is asserted, and the two levels are printed beside
them because omitting the levels is exactly what made the bad inference invisible.

### E3. Level-matched, which is the comparison that means something

Both designs are cut rules on S, so their attainable (level, power) pairs are the
vertices of their ladders and the segments between them: a randomised cut mixing
c and c+1 attains any level in between, with the correspondingly mixed power. Read
at a COMMON achieved level the two become commensurable, and the realized design is
the weaker of the two everywhere.

| achieved level | realized power @2x | planned power @2x | planned - realized |
|---|---|---|---|
| 0.025 | 0.663 | 0.689 | +0.026 |
| 0.030 | 0.692 | 0.718 | +0.026 |
| 0.040 | 0.746 | 0.774 | +0.028 |
| 0.050 | 0.782 | 0.805 | +0.023 |

### E4. Splitting the drop, and how much of the split survives the ordering

The drop runs from 0.770 at the planned design's operating point (level 0.0387)
to 0.669 at the realized design's (level 0.0257), a total of 0.101. Two
things changed at once - the level moved and the experiment shrank - so the split
between them is path-dependent and both orders are given rather than one being
passed off as the answer.

| order | granularity (the cut moved) | design (fewer targets, short arms) |
|---|---|---|
| A: level first, on the planned design | 0.078 (77%) | 0.024 (23%) |
| B: design first, at the planned level | 0.070 (69%) | 0.031 (31%) |
| symmetric (Shapley) | 0.074 (73%) | 0.027 (27%) |

The larger term under BOTH orders is granularity. What is not true is that the other
term is nothing: the sentence "the shortfall is not the three missing targets or
the six short arms" is false as stated. Fewer targets and shorter arms cost real
power - 0.031 of it at the planned design's own level - and they
are the smaller share of the drop, not a null share of it.

The design term splits again. An intermediate design of 77 targets at a uniform
m = 50 (3,850 draws, cut S <= 12 at 0.0366) separates the three targets
the run could not test from the six arms that came up short. Read at each matched
level:

| achieved level | three lost targets | six short arms | total (planned - realized) |
|---|---|---|---|
| 0.025 | +0.010 | +0.016 | +0.026 |
| 0.030 | +0.008 | +0.018 | +0.026 |
| 0.040 | +0.019 | +0.010 | +0.028 |
| 0.050 | +0.010 | +0.012 | +0.023 |

Averaged over the four levels: +0.012 for the lost targets and +0.014 for the
short arms. The two sum to the level-matched gap by construction, which is the
check worth making on any statement of this split: `experiments.tex` currently puts
both at about 0.02, and 0.02 + 0.02 exceeds the gap it is decomposing. Each term
here is individually noisy - per level they run 0.006 to 0.020 - so what should be
read off this table is that both are positive and neither is the whole of it.

A note on E[S]. The realized design's null expects fewer exceedances (20.35 against
21.98) only because 3,704 < 4,000 benign draws, since E[S] = sum_j m_j / (A+1).
That is less data, not more power, and it must not be offered as a reason the
realized design is strong.

### E5. Against what the paper and the review record assert

| design | quantity | claim | this run | verdict |
|---|---|---|---|---|
| planned (n=80, uniform m=50) | deployed cut | S <= 13 | S <= 13 | MATCHES |
| planned (n=80, uniform m=50) | nominal level | 0.0437 | 0.0437 | MATCHES |
| planned (n=80, uniform m=50) | E[S] under H0 | 21.98 | 21.98 | MATCHES |
| planned (n=80, uniform m=50) | achieved level | 0.039 | 0.039 | MATCHES |
| planned (n=80, uniform m=50) | power vs 2-fold | 0.769 | 0.770 | MATCHES |
| planned (n=80, uniform m=50) | power vs 3-fold | 0.978 | 0.979 | MATCHES |
| realized (n=77, shipped m-vector) | deployed cut | S <= 11 | S <= 11 | MATCHES |
| realized (n=77, shipped m-vector) | nominal level | 0.0296 | 0.0296 | MATCHES |
| realized (n=77, shipped m-vector) | E[S] under H0 | 20.35 | 20.35 | MATCHES |
| realized (n=77, shipped m-vector) | achieved level | 0.026 | 0.026 | MATCHES |
| realized (n=77, shipped m-vector) | power vs 2-fold | 0.670 | 0.669 | MATCHES |
| realized (n=77, shipped m-vector) | power vs 3-fold | 0.952 | 0.952 | MATCHES |
| realized (n=77, shipped m-vector) | the next cut up | S <= 12 at 0.0501 | S <= 12 at 0.0501 | MATCHES, MATCHES |
| planned (n=80, uniform m=50) | nominal level at a fixed cut of 13 | 0.0437 | 0.0437 | MATCHES |
| realized (n=77, shipped m-vector) | nominal level at a fixed cut of 13 | 0.0793 | 0.0793 | MATCHES |
| both | size ratio at a fixed cut of 13 | 1.82 | 1.82 | MATCHES |
| realized (n=77, shipped m-vector) | level-matched power @2x at 0.025 | 0.669 | 0.663 | MATCHES |
| planned (n=80, uniform m=50) | level-matched power @2x at 0.025 | 0.699 | 0.689 | MATCHES |
| realized (n=77, shipped m-vector) | level-matched power @2x at 0.030 | 0.696 | 0.692 | MATCHES |
| planned (n=80, uniform m=50) | level-matched power @2x at 0.030 | 0.722 | 0.718 | MATCHES |
| realized (n=77, shipped m-vector) | level-matched power @2x at 0.040 | 0.747 | 0.746 | MATCHES |
| planned (n=80, uniform m=50) | level-matched power @2x at 0.040 | 0.775 | 0.774 | MATCHES |
| realized (n=77, shipped m-vector) | level-matched power @2x at 0.050 | 0.783 | 0.782 | MATCHES |
| planned (n=80, uniform m=50) | level-matched power @2x at 0.050 | 0.809 | 0.805 | MATCHES |
| both | level-matched gap positive at all 4 levels | yes | yes | MATCHES |
| both | drop, planned op point to realized op point | 0.098 | 0.101 | MATCHES |
| both | granularity share (symmetric) | 0.071 | 0.074 | MATCHES |
| both | design share (symmetric) | 0.027 | 0.027 | MATCHES |
| both | three lost targets, level-matched mean | 0.010 | 0.012 | MATCHES |
| both | six short arms, level-matched mean | 0.015 | 0.014 | MATCHES |
| both | both sub-terms cost power (each > 0) | yes | yes | MATCHES |
| both | granularity is the larger term under BOTH orders | yes | yes | MATCHES |

A non-rejection in this campaign has to be read against the realized column. The
planned column is what the design promised and is quoted in sections A-D because the
paper still states it as the design's figure; it is not what the run can see.

### E6. What every number above is conditional on

All of it is computed at the attacker budget A = 181, which
`experiments.tex` calls an *upper* bound on a parameter it says is not identified
below 41 and reports the verdict across. The cut is very sensitive to it:

| A | planned cut | nominal | realized cut | nominal |
|---|---|---|---|---|
| 181 | 13 | 0.0437 | 11 | 0.0296 |
| 121 | 21 | 0.0382 | 19 | 0.0375 |
| 90 | 30 | 0.0414 | 27 | 0.0373 |
| 41 | 72 | 0.0464 | 66 | 0.0469 |

The power figures are therefore conditional on the top of the admissible range, and
the paper states them without that condition. This is a scope statement, not a
finding against any number above: nothing in this script inherits a constant from a
derivation whose other outputs were refuted. In particular A=181 is a
recorded evaluation count, not the A=41 scalar that heavy review 2 section 3.3
showed to be a Jensen error, and 41 appears nowhere in this script's inputs.

## F. What this script fails on

Nothing. Every claim pinned in `PAPER_CLAIMS` and `DESIGN_CLAIMS` reproduces
within tolerance, and the realized m-vector on disk still matches
`REALIZED_M_VECTOR`.

The checks that run on every invocation, any of which returns a non-zero exit:

  1. the split DGP is stream-identical to `power_sim_randomized.one_target`;
  2. the analytic p-value depends on the exceedance TOTAL only, at a uniform m and
     at the realized m-vector, which is what licenses reducing both tests to a cut;
  3. the realized m-vector on disk matches `REALIZED_M_VECTOR`, and is the same in
     all three scored arms (a hard stop, not a table row);
  4. every number in `PAPER_CLAIMS` (section D) and `DESIGN_CLAIMS` (section E),
     including the level-matched comparison, the sign of its gap at every level,
     and both terms of the decomposition.

## Reproduction

```
.venv/Scripts/python.exe scripts/power_sim_deployed.py
.venv/Scripts/python.exe scripts/power_sim_deployed.py --out-dir <dir>
```
`--out-dir` writes this report and the headroom mirror somewhere other than
`results/`, for re-running the checks without touching a committed artifact.
