# Power under the RANDOMIZED tie rule (supersedes power_under_ceiling.md)

Empirical n=80 headroom distribution, draws censored at the ceiling, null simulated with the same rule as the statistic.

| m | E[S] under H0 | level | power @2x | power @3x | power @5x |
|---|---|---|---|---|---|
| 20 | 8.74 | 0.058 | 0.51 | 0.83 | 0.96 |
| 30 | 13.03 | 0.052 | 0.67 | 0.92 | 1.00 |
| 50 | 22.17 | 0.068 | 0.84 | 0.99 | 1.00 |
| 80 | 35.08 | 0.058 | 0.94 | 1.00 | 1.00 |

The conservative rule gave 0.00 power at every m; that was the rule, not the ceiling (critique_log 26). Pick the smallest m clearing the pre-committed bar and cost the definitive run from it: the judge arm is ~(2+m+n_seeds) clusterings per target, ~55s each.
