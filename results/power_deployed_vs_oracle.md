# Deployed (analytic-null) vs oracle-calibrated power, same draws, stated levels

Producing script: `scripts/power_sim_deployed.py`. Companion to
`results/power_randomized.md`, which reported the ORACLE column only. The deployed
column is the test the pipeline actually runs: `se.stats.exceedance_test`'s analytic
BetaBinomial null, no access to the true simulated null.

DGP imported verbatim from `scripts/power_sim_randomized.py`. Headroom from `data\cache\attacks\wk9_defb_snap\triviaqa_se_false_alarm.jsonl`, mirrored to `results/fa80_headroom.md` so this reproduces without the cache. n_targets = 80, attacker candidates N = 181, nominal alpha = 0.05.
Per-draw exponential scale 0.12, calibrated to 45% attack saturation against the observed 49%.

Rules: **deployed** = analytic p <= alpha on one tie-break draw; **dep.-median** = median p over 25 tie-break draws (what `exceedance_test_over_seeds` ships); **oracle** = S <= 5th percentile of a separate simulated null, which the deployed test cannot compute.

## A. Published settings — reproduces results/power_randomized.md's oracle column

Simulated draws: 2500 H0 trials for the oracle critical value, 400 trials each for the achieved level and for every power cell; seed 11. Level and power are measured on the SAME draws for every rule, so the columns are paired and differ only in the cut applied. `nominal dep.` is the analytic null's own tail at the deployed cut — what the test BELIEVES its level is; `level dep.` is what it achieves on this DGP, from the 400-trial sample, and `(big null)` repeats it on the 2500-trial one.

| m | crit (deployed) | crit (oracle) | nominal dep. | level dep. | level dep. (big null) | level dep.-median | level oracle | pow 2x dep. | pow 2x dep.-med | pow 2x oracle | pow 3x dep. | pow 3x oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 4.0 | 0.030 | 0.020 | 0.028 | 0.005 | 0.058 | **0.33** | 0.33 | 0.51 | 0.70 | 0.83 |
| 30 | 6 | 7.0 | 0.031 | 0.020 | 0.032 | 0.013 | 0.052 | **0.50** | 0.54 | 0.67 | 0.81 | 0.92 |
| 50 | 13 | 14.0 | 0.044 | 0.043 | 0.035 | 0.020 | 0.068 | **0.78** | 0.85 | 0.84 | 0.97 | 0.99 |
| 80 | 23 | 25.0 | 0.041 | 0.030 | 0.028 | 0.013 | 0.058 | **0.88** | 0.93 | 0.94 | 1.00 | 1.00 |

At 400 trials an achieved level near 0.05 carries a standard error of about 0.011, so read these levels as indicative and the ones in table B as the measurement.

## B. High precision — the numbers to quote

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
power is bought conservatism, not a worse statistic — and, unlike the oracle, it is
a level the pipeline can actually claim without knowing the truth it is testing.

The `exact-level` rule below is the best a cut on S can do while honouring alpha on
this DGP; it brackets how much of the deployed/oracle gap is discreteness.

| m | crit dep. | level dep. | pow 2x dep. | crit exact | level exact | pow 2x exact | crit oracle | level oracle | pow 2x oracle |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 0.028 | 0.352 | 3 | 0.028 | 0.352 | 4.0 | 0.066 | 0.553 |
| 30 | 6 | 0.025 | 0.511 | 6 | 0.025 | 0.511 | 7.0 | 0.056 | 0.658 |
| 50 | 13 | 0.041 | 0.769 | 13 | 0.041 | 0.769 | 14.0 | 0.064 | 0.841 |
| 80 | 23 | 0.034 | 0.900 | 24 | 0.048 | 0.930 | 25.0 | 0.070 | 0.952 |

## D. The two cells the paper quotes, against what reproduces

`paper/sections/experiments.tex` states the deployed test "reaches power 0.51 at
level 0.035 for m=30, and 0.77 at level 0.053 for the pre-registered m=50", and the
pre-registration disclosure differences against those. Those four numbers had no
producing artifact. Here is every reproducible reading of them.

| cell | quantity | paper | this run (high precision) | published settings | verdict |
|---|---|---|---|---|---|
| m=30 | deployed power @2x | 0.51 | 0.511 | 0.500 | MATCHES |
| m=30 | deployed level, ACHIEVED | 0.035 | 0.025 (on 20000 H0 trials 0.029) | 0.020 | **DIFFERS** |
| m=30 | deployed level, NOMINAL (analytic tail at the cut) | 0.035 | 0.031 | 0.031 | **DIFFERS** |
| m=30 | oracle power @2x | 0.67 | 0.658 | 0.670 | MATCHES |
| m=30 | oracle level | 0.052 | 0.056 | 0.052 | MATCHES |
| m=30 | power gap oracle-deployed | 0.16 | 0.147 | 0.170 | MATCHES (derived; brackets the two passes) |
| m=50 | deployed power @2x | 0.77 | 0.769 | 0.780 | MATCHES |
| m=50 | deployed level, ACHIEVED | 0.053 | 0.041 (on 20000 H0 trials 0.037) | 0.043 | **DIFFERS** |
| m=50 | deployed level, NOMINAL (analytic tail at the cut) | 0.053 | 0.044 | 0.044 | **DIFFERS** |
| m=50 | oracle power @2x | 0.84 | 0.841 | 0.845 | MATCHES |
| m=50 | oracle level | 0.068 | 0.064 | 0.068 | MATCHES |
| m=50 | power gap oracle-deployed | 0.07 | 0.072 | 0.065 | MATCHES (derived; brackets the two passes) |

**The powers reproduce; the two LEVELS do not.** Every reproducible estimate of the
deployed test's level is BELOW what the paper quotes, in both cells: the shipped test
is more conservative than the paper says it is, not less. The direction is benign for
the paper's argument (a more conservative test makes the non-rejection reading
stricter, and the ordering that drove the m=50 choice is untouched) but the numbers
as printed are not reproducible from this DGP and should be replaced by this table's.

Both powers must be quoted WITH a level, because at unequal levels powers are not
comparable (section C) — and the level to quote is the achieved one, not the analytic
null's nominal tail, which differs from it by up to a third of its own value here.

## Reproduction

```
.venv/Scripts/python.exe scripts/power_sim_deployed.py
```
Asserted on every run: (i) the split DGP is stream-identical to
`power_sim_randomized.one_target`; (ii) the analytic p-value depends on the
exceedance TOTAL only, which is what licenses the reduction of both tests to a cut.
