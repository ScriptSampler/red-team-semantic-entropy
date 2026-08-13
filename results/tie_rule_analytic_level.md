# Tie rules scored against the DEPLOYED analytic null

Producing script: `scripts/tie_rule_analytic_level.py`. Companion to
`results/tie_rule_showdown.md`, which scored each rule against a null SIMULATED with
that same rule. The pipeline cannot do that — it scores against
`se.stats.exceedance_test`'s BetaBinomial null — so the level that matters for a
deployment claim is the `analytic` column here.

DGP executed from `scripts/tie_rule_showdown.py` itself (its `draw` / `one_target`),
so the two cannot drift: atom of mass q at the ceiling, Uniform(0,1) below, attacker
candidates N = 181, 80 targets, alpha = 0.05, H1 = the attack is worth 2x its budget.
3000 H0 trials for the simulated critical value, 3000 trials each for level and power (SE on a level near 0.05: 0.0040).

Analytic critical values (reject iff the exceedance total S <= c): m=30 -> c=6, m=60 -> c=16.

| q | rule | m | E[S]\|H0 | **analytic level** | **analytic power @2x** | simulated level | simulated power @2x |
|---|---|---|---|---|---|---|---|
| 0.000 | strict | 30 | 13.14 | 0.033 | 0.52 | 0.066 | 0.67 |
| 0.000 | strict | 60 | 26.25 | 0.035 | 0.81 | 0.056 | 0.87 |
| 0.000 | conservative | 30 | 13.14 | 0.033 | 0.52 | 0.066 | 0.67 |
| 0.000 | conservative | 60 | 26.25 | 0.035 | 0.81 | 0.056 | 0.87 |
| 0.000 | randomized | 30 | 13.14 | 0.033 | 0.52 | 0.066 | 0.67 |
| 0.000 | randomized | 60 | 26.25 | 0.035 | 0.81 | 0.056 | 0.87 |
| 0.010 | strict | 30 | 5.93 | 0.590 | 1.00 | 0.097 | 0.93 |
| 0.010 | strict | 60 | 12.02 | 0.822 | 1.00 | 0.068 | 0.97 |
| 0.010 | conservative | 30 | 25.99 | 0.000 | 0.00 | 0.055 | 0.12 |
| 0.010 | conservative | 60 | 52.22 | 0.000 | 0.00 | 0.048 | 0.13 |
| 0.010 | randomized | 30 | 12.04 | 0.056 | 0.69 | 0.056 | 0.69 |
| 0.010 | randomized | 60 | 24.03 | 0.082 | 0.94 | 0.054 | 0.90 |
| 0.050 | **strict** | 30 | 0.01 | **1.000** | **1.00** | 0.994 | 1.00 |
| 0.050 | strict | 60 | 0.02 | 1.000 | 1.00 | 0.995 | 1.00 |
| 0.050 | **conservative** | 30 | 120.02 | **0.000** | **0.00** | 0.054 | 0.06 |
| 0.050 | conservative | 60 | 240.04 | 0.000 | 0.00 | 0.047 | 0.05 |
| 0.050 | **randomized** | 30 | 11.84 | **0.051** | **0.57** | 0.102 | 0.71 |
| 0.050 | randomized | 60 | 23.74 | 0.057 | 0.87 | 0.057 | 0.87 |

## The cell the paper quotes (full saturation, q=0.05, m=30)

experiments.tex: "counting ties strictly gives a null rejection rate of 0.995 and
counting them against the attack gives power 0.05 at a two-fold effect, while the
randomised rule stays calibrated there (analytic-null level 0.021)".

| claim | paper | this run | which null | verdict |
|---|---|---|---|---|
| randomised tie rule stays calibrated | 0.021 | 0.051 | analytic, showdown DGP (b redrawn) | **DIFFERS** |
| randomised tie rule stays calibrated | 0.021 | 0.019 | analytic, probe DGP (b measured) | MATCHES |
| strict tie rule null rejection | 0.995 | 0.994 | simulated (as in tie_rule_showdown.md) | MATCHES |
| conservative tie rule power @2x | 0.05 | 0.06 | simulated | MATCHES |

Note the strict rule's ANALYTIC level in the table above: under a ceiling atom its
exceedance total collapses to ~0.01, which is at or below
the analytic critical value, so the deployed test would reject essentially always.
Both nulls disqualify it; only the reasons differ.

## Where 0.021 could have come from: the tie multiplicity b

`scripts/tie_level_probe.py` runs the same question with ONE structural difference:
it takes b as the number of attack candidates ACTUALLY at the atom, where the
showdown redraws b as 1 + Binomial(N-1, q). The measured-b convention is the one the
deployed statistic uses (`exceedance_counts_randomized` is handed a measured
`n_feasible_at_best`) and the one `scripts/power_sim_randomized.py` simulates, so it
is the faithful DGP; the showdown's b runs about one higher, which shrinks the tie
credit 1/(b+1) and pushes the level up. Both are re-measured here, and the probe's
numbers have never been in an artifact either — they live in a docstring in
`src/se/stats.py`.

| q | showdown b = 1+Bin(N-1,q) | probe b = measured | stats.py docstring (1500 trials) |
|---|---|---|---|
| 0.000 | 0.033 | 0.036 | 0.041 |
| 0.010 | 0.056 | 0.028 | 0.037 |
| 0.050 | 0.051 | 0.019 | 0.024 |

At the paper's cell the two conventions give **0.051** (b redrawn) and **0.019** (b measured), against the paper's **0.021** (3-sigma tolerance at 3000 trials: +/-0.008).

**The paper's 0.021 reproduces under the MEASURED-b DGP and not under the other one** (confirmed here). That is the resolution, and
it is worth stating because the sentence in experiments.tex reads as one simulation:
its 0.995 and its 0.05 come from `tie_rule_showdown.py`, where b is redrawn, while
its 0.021 comes from the measured-b path. Both are defensible numbers; quoting them
in one breath is what hides the fact that the randomised rule's level at this cell is
0.051, not 0.019, if b is generated the way the same sentence's other two
numbers were. The measured-b figure is the right one to keep, because b is measured
in deployment.

## The max-of-N null percentile the same paragraph uses

`se.stats.analytic_max_percentile(A)` = A/(A+1): under exchangeability, where the
max of A candidates sits in an individual draw's distribution with NO adversarial
signal at all.

| A (attacker candidates) | analytic percentile |
|---|---|
| 10 | 0.9091 |
| 30 | 0.9677 |
| 50 | 0.9804 |
| 180 | 0.9945 |
| 181 | 0.9945 |

So the paper's "~99%" for A=181 is 0.9945; the point of
the sentence is that it is nowhere near 50%, and it is a closed form, not an estimate.
