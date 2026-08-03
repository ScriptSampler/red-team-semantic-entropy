# Power at N=20 using the pilot's EMPIRICAL headroom gains

Pilot targets: 15. Mean headroom 0.595 (N=10) -> 0.899 (N=20); empirical gain +0.304 nats vs the +0.693 the first simulation naively assumed (baselines rise with N too).

| config | m | saturation | H0 level | power @2x | power @3x |
|---|---|---|---|---|---|
| N=10 | 30 | 46% | 0.000 | 0.00 | 0.00 |
| N=10 | 50 | 47% | 0.000 | 0.00 | 0.00 |
| N=20 | 30 | 40% | 0.000 | 0.00 | 0.00 |
| N=20 | 50 | 41% | 0.000 | 0.00 | 0.00 |

**VERDICT: DO NOT PROCEED: power < 0.60 at 2x for every m <= 50. Per critique_log 23a, FA nats and the FA exceedance test are NOT identifiable at feasible N; report censoring-robust statistics only.**

Decision rule pre-committed in critique_log 23a BEFORE the pilot completed.
