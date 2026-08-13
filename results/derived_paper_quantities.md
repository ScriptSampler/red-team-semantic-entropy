# Derived quantities the paper quotes, with their arithmetic

Producing script: `scripts/derived_paper_quantities.py`. These are numbers that are
arithmetic on artifact-sourced inputs but were printed only in the .tex, so no reader
(and no future run) could check them. Each input is guarded: the script refuses to
run if the artifact it claims to read no longer contains the literal it needs.

## Inputs, and where they come from

| input | value | artifact | literal checked |
|---|---|---|---|
| mean clean entropy, correct answers, fair pool | 1.38 | `results/fair_pool_report.md` | `| right | fair pool | 1.380` |
| mean clean entropy, wrong answers, fair pool | 1.843 | `results/fair_pool_report.md` | `| wrong | fair pool | 1.843` |
| K=8 lattice point (next attainable value below the cap) | 2.0253 | `results/cluster_count_bound.md` | `2.0253` |
| hallucinating answers at the ceiling, fair pool | 0.275 | `results/achievable_fpr_grid.md` | `55/200 = 27.5%` |
| correct answers at the ceiling, fair pool | 0.095 | `results/achievable_fpr_grid.md` | `19/200 = 9.5%` |
| clean fair-pool AUROC and CI | 0.704 | `results/fair_pool_report.md` | `0.704 [0.653, 0.753]` |
| null-control benign draws per target (K) | 5 | `results/null_control_report.md` | `K=5 benign` |
| judge-arm cost of the matched design, GPU-hours | 228 | `docs/critique_log.md` | `228 GPU-h` |
| greedy-correct count, SUBSTRING oracle | 1440 | `results/relabel_report.md` | `old correct rate: 1440/2000` |
| greedy-correct count, SPAN oracle | 1424 | `results/relabel_report.md` | `new correct rate: 1424/2000` |

Ceiling: log(10) = 2.302585 nats.

## methods.tex — headroom to the ceiling

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| headroom from the correct-answer mean | log(10) - 1.380 | 0.9226 | 0.923 | MATCHES |
| headroom at the next lattice point down | log(10) - 2.0253 | 0.2773 | 0.277 | MATCHES |
| (not quoted) headroom from the wrong-answer mean | log(10) - 1.843 | 0.4596 | - | - |

The second row is the one that carries an argument: the whole gap between the
correct-answer mean and the cap is 0.923 nats, but the score cannot occupy it
continuously — the last attainable step below the cap already leaves 0.277 nats, so
a move smaller than one lattice step is unrepresentable, not merely small.

## discussion.tex — the censoring bias bound

AUROC is P(score of a hallucinating answer > score of a correct one) with ties at
1/2, taken over all cross-stratum pairs. min(., log N) is monotone, so censoring
cannot reorder a pair unless BOTH members are pinned at the cap; such a pair becomes
a tie and contributes exactly 1/2, whatever it contributed before. The true
contribution lies in [0, 1], so each affected pair can move the AUROC by at most 1/2 —
**that factor of 1/2 is the step the paper does not write down**, and it is what
turns a 2.6% pair fraction into a 0.013 bound rather than a 0.026 one.

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| fraction of pairs with both members pinned | (55/200) x (19/200) = 1045/40000 | 0.0261 | 0.026 | MATCHES |
| bound on the downward AUROC bias | 1/2 x 2.6% (a tie contributes 1/2; truth in [0,1]) | 0.0131 | 0.013 | MATCHES |
| half-width of the clean fair-pool AUROC CI | (0.753 - 0.653) / 2 | 0.0500 | 0.050 | MATCHES |
| counterfactual: both strata censored at the higher rate | 0.275^2 / [0.275 x 0.095] = 0.0756 / 0.0261 | 2.89 | 2.9 | MATCHES |

So the bound is 0.0131 against a half-width of 0.050: the censoring
bias is at most 26% of the interval the AUROC is already reported
with, which is the point of the paragraph. Note the pair fraction is EXACT on this
pool (1045 of 40000 pairs), not an approximation — the two strata are
fixed sets of 200, so the cross-product is a count.

One wording caveat, recorded because the sweep raised it: `docs/critique_log.md` uses
2.9x for the ratio of the two CENSORING RATES' effect (27.5/9.5 = 2.89), while the
paper uses it for the ratio of AFFECTED PAIRS. The two coincide numerically here
(0.275^2 / (0.275 x 0.095) = 0.275/0.095 = 2.89) because the
hallucinating rate cancels, so the sentence is correct — but it is correct by
coincidence of algebra, not because it is quoting the logged quantity.

## methods.tex — resolution of the n=6 arm statistic

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| step of the arm-level statistic | 1 / (n=6 targets x K=5 benign draws) | 0.0333 | 0.033 | MATCHES |

A per-target rank among K=5 benign draws moves in fifths; averaging over 6 targets
makes the arm statistic move in thirtieths. Any arm-to-arm gap smaller than that is
below the machinery pass's resolution and cannot be read as a difference.

## experiments.tex — cost of the matched design

228 GPU-hours / 24 = **9.5 GPU-days**. The paper says "roughly nine GPU-days"; the logged figure
is 9.5, so "roughly nine" rounds the wrong way. "About nine and a half" or
"over nine" is the accurate phrasing; nothing else depends on it.

## Flagged inconsistency (not a derivation): 1440 vs 1424

`limitations.tex` describes "the 1440 greedy-correct questions of our 2000-question
replication pass" in the same paragraph that quotes the span-oracle AUROC 0.694.
But 1440 is the SUBSTRING-oracle
count; under the span oracle the same pass gives 1424 (`results/relabel_report.md`, corroborated by `results/replication_conventions.md`).
The paragraph mixes the two oracles. This script does not edit the paper; it records
the discrepancy so it cannot be lost again.

| oracle | greedy-correct of 2000 | rate |
|---|---|---|
| substring | 1440 | 72.0% |
| span (operative) | 1424 | 71.2% |
