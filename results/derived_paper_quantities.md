# Derived quantities the paper quotes, with their arithmetic

Producing script: `scripts/derived_paper_quantities.py`. These are numbers that are
arithmetic on artifact-sourced inputs but were printed only in the .tex, so no reader
(and no future run) could check them. Two guards run before any arithmetic: each
INPUT names the artifact it came from and a literal that must still be there, and
each PAPER claim names the literal `paper/` must still print. The second guard is new
on 2026-08-19 and is the one that was missing: this report previously verified that
`experiments.tex` says "roughly nine GPU-days" while that file had not said so for
five days, because the paper side was a hard-coded dict checked against nothing.

Paper files are edited concurrently. A PAPER miss may be a race; the digests below
are taken at check time so a miss can be re-checked against the same bytes.

| paper file | bytes | sha256[:12] |
|---|---|---|
| `paper/main.tex` | 16636 | `892d52974003` |
| `paper/sections/conclusion.tex` | 7149 | `0e4aa252d140` |
| `paper/sections/discussion.tex` | 41178 | `d9398beab64d` |
| `paper/sections/experiments.tex` | 33820 | `933226f99fa6` |
| `paper/sections/introduction.tex` | 17242 | `7f5242d85baa` |
| `paper/sections/limitations.tex` | 19704 | `9aca28572e73` |
| `paper/sections/methods.tex` | 31238 | `a26c6ffb534b` |

## Inputs, and where they come from

| input | value | artifact | literal checked | provenance |
|---|---|---|---|---|
| mean clean entropy, correct answers, fair pool | 1.38 | `results/fair_pool_report.md` | `| right | fair pool | 1.380` | - |
| mean clean entropy, wrong answers, fair pool | 1.843 | `results/fair_pool_report.md` | `| wrong | fair pool | 1.843` | - |
| K=8 lattice point (next attainable value below the cap) | 2.0253 | `results/cluster_count_bound.md` | `2.0253` | - |
| hallucinating answers at the ceiling, fair pool | 0.275 | `results/achievable_fpr_grid.md` | `55/200 = 27.5%` | - |
| correct answers at the ceiling, fair pool | 0.095 | `results/achievable_fpr_grid.md` | `19/200 = 9.5%` | - |
| clean fair-pool AUROC and CI | 0.704 | `results/fair_pool_report.md` | `0.704 [0.653, 0.753]` | - |
| null-control benign draws per target (K) | 5 | `results/null_control_3arm_judge_n6.md` | `K=5 benign` | - |
| greedy-correct count, SUBSTRING oracle | 1440 | `results/relabel_report.md` | `old correct rate: 1440/2000` | - |
| greedy-correct count, SPAN oracle | 1424 | `results/relabel_report.md` | `new correct rate: 1424/2000` | - |
| judge evaluations per target at K=180 | 185 | `results/operational_number_audit.md` | `185 evaluations/target` | - |
| measured seconds per clustering, deployed run | 24.0 | `results/operational_number_audit.md` | `the measured 24.0 s/clustering from the deployed run` | MEASURED on the deployed run, same symmetric judge, `judge_batch_size` 6, N=10 |
| retired entry-22 price of the judge arm, GPU-hours | 227.8 | `results/operational_number_audit.md` | `| judge arm, K=180, n=80 | 227.8 GPU-h` | MODELLED from the 55 s unit of `docs/critique_log.md` 22 at K=180, n=80; superseded |
| re-priced judge arm, GPU-hours (cross-check) | 98.7 | `results/operational_number_audit.md` | `**98.7 GPU-h — 4.1 GPU-days**` | MEASURED, re-derived from the 24.0 s/clustering unit above |
| clean correct answers at the ln 40 cap, fair pool | 0 | `results/post_overnight_claim_review.md` | `| N=40 measured | 0/200 = 0.0% [0.0, 1.9] |` | - |
| clean correct answers above the cheapest firing threshold, N=40 | 4 | `results/replay_control.md` | `| measured N=40 | 2.0% | **none -- withdrawn, see 2c** |` | - |
| hallucinating answers caught at that threshold, N=40 (rate) | 6.0 | `results/n_scaling_grid.md` | `| 40 | 1% | 0.0% (flags nothing) | 0.0% | 2.0% **over budget** | 6.0% |` | - |
| achieved false-alarm rate at a 5% budget, N=40 (rate) | 5.0 | `results/n_scaling_grid.md` | `| 40 | 5% | 5.0% | 11.0% | 5.0% | 11.0% |` | - |
| count behind that achieved 5.0% | 10 | `results/gate_paper_edits_2026_08_19.md` | `It is 10/200 on the fair pool's correct stratum; Wilson` | - |
| subset-averaged replay floor at N=10 (percent) | 11.974 | `results/replay_control.md` | `| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |` | - |
| subset-averaged replay floor at N=20 (percent) | 3.134 | `results/replay_control.md` | `| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |` | - |
| exact replay floor at N=10 (percent) | 11.9921 | `results/replay_control.md` | `Exact: N=10 floor 11.9921%, N=20 floor 3.1291%` | EXACT, by independent-set counting; not the 40k-draw MC row above |
| exact replay floor at N=20 (percent) | 3.1291 | `results/replay_control.md` | `Exact: N=10 floor 11.9921%, N=20 floor 3.1291%` | EXACT, by independent-set counting; not the 40k-draw MC row above |
| exact 10 -> 20 paired floor leg (points) | -8.863 | `results/replay_control.md` | `a 10 -> 20 paired leg of -8.8630` | EXACT; the report's own MC rendering of this leg is -8.8 and is marked as MC in its differences table |
| N=10 question component, sd in rate points | 1.6346 | `results/replay_control.md` | `| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |` | - |
| N=10 subset-draw component, sd in rate points | 1.6119 | `results/replay_control.md` | `| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |` | - |
| N=20 question component, sd in rate points | 0.7433 | `results/replay_control.md` | `| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |` | - |
| N=20 subset-draw component, sd in rate points | 0.9826 | `results/replay_control.md` | `| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |` | - |
| mean answer length, June direct cache (chars) | 116.0 | `results/replay_control.md` | `116.0 chars direct vs 119.6 in the checkpoint, paired difference **+3.63 +/- 0.91**` | - |
| mean answer length, August checkpoint (chars) | 119.6 | `results/replay_control.md` | `116.0 chars direct vs 119.6 in the checkpoint, paired difference **+3.63 +/- 0.91**` | - |
| paired length difference (chars) | 3.63 | `results/replay_control.md` | `paired difference **+3.63 +/- 0.91**` | - |
| paired length difference, standard error (chars) | 0.91 | `results/replay_control.md` | `paired difference **+3.63 +/- 0.91**` | - |
| paired terminal-punctuation difference (fraction) | 0.0163 | `results/replay_control.md` | `0.738 vs 0.722, paired -0.0163 +/- 0.0071` | - |
| cluster-count chi-square, correct stratum, k=10 | 7.39 | `results/replay_control.md` | `| correct, direct | 11 | 17 | 27 | 18 | 27 | 24 | 18 | 15 | 24 | 19 | 7.39 | 9 | 0.60 |` | - |
| its degrees of freedom | 9 | `results/replay_control.md` | `| correct, direct | 11 | 17 | 27 | 18 | 27 | 24 | 18 | 15 | 24 | 19 | 7.39 | 9 | 0.60 |` | - |
| exact Poisson-binomial P(X <= 19), producing implementation | 0.081 | `results/replay_control.md` | `P(X <= 19) = 0.081` | - |
| the same p, independent reimplementation | 0.083 | `results/gate_paper_edits_2026_08_19.md` | `| exact Poisson-binomial P(X ≤ 19) | **0.081** | **0.083** | yes |` | - |

## What the paper prints, and where

| claim | value | file | literal | must be | provenance |
|---|---|---|---|---|---|
| headroom_correct | 0.923 | `paper/sections/methods.tex` | `$0.923$ nats to the ceiling` | present | - |
| headroom_next_lattice | 0.277 | `paper/sections/methods.tex` | `the next lattice point down, $2.025$, still leaves $0.277$ nats` | present | - |
| arm_step | 0.03333333333333333 | `paper/sections/methods.tex` | `moves in steps of roughly $1/30$` | present | - |
| pinned_pair_fraction | 0.026 | `paper/sections/discussion.tex` | `That is $0.275 \times 0.095 = 2.6\%$ of pairs,` | present | - |
| bias_bound | 0.013 | `paper/sections/discussion.tex` | `bounding the downward bias at $0.013$` | present | - |
| ci_half_width | 0.05 | `paper/sections/discussion.tex` | `a confidence half-width of $0.050$` | present | - |
| counterfactual_ratio | 2.9 | `paper/sections/discussion.tex` | `$2.9\times$ as many pairs would be affected` | present | - |
| gpu_hours_retired | 228 | `paper/sections/experiments.tex` | `$228$ GPU-hours` | present | MODELLED from the 55 s unit of `docs/critique_log.md` 22 at K=180, n=80; superseded; the paper names it only to correct it |
| gpu_hours_repriced | 99 | `paper/sections/experiments.tex` | `about $99$ GPU-hours` | present | MEASURED, re-derived from the 24.0 s/clustering unit |
| gpu_trigger_ratio | 2.3 | `paper/sections/experiments.tex` | `$2.3\times$ too large` | present | - |
| gpu_days_retired_phrase | 0 | `paper/sections/experiments.tex` | `roughly nine GPU-days` | **absent** | - |
| n40_atcap | 0.0 | `paper/sections/discussion.tex` | `$0.0\%$ [$0.0$, $1.9$]` | present | - |
| n40_atcap_hi | 1.9 | `paper/sections/discussion.tex` | `$0.0\%$ [$0.0$, $1.9$]` | present | - |
| n40_floor | 2.0 | `paper/sections/discussion.tex` | `a measured $2.0\%$ at $N{=}40$` | present | - |
| n40_floor_wilson_retired_disc | 5.03 | `paper/sections/discussion.tex` | `[$0.78$, $5.03$]` | **absent** | - |
| n40_floor_boot_retired_disc | 4.0 | `paper/sections/discussion.tex` | `[$0.5$, $4.0$]` | **absent** | - |
| n40_floor_503_retired_disc | 5.03 | `paper/sections/discussion.tex` | `5.03` | **absent** | - |
| n40_floor_wilson_retired_main | 5.03 | `paper/main.tex` | `[$0.8$, $5.03$]` | **absent** | - |
| n40_floor_503_retired_main | 5.03 | `paper/main.tex` | `5.03` | **absent** | - |
| n40_floor_wilson_retired_concl | 5.03 | `paper/sections/conclusion.tex` | `[$0.8$, $5.03$]` | **absent** | - |
| n40_floor_503_retired_concl | 5.03 | `paper/sections/conclusion.tex` | `5.03` | **absent** | - |
| n40_floor_rounded_retired_intro | 5.0 | `paper/sections/introduction.tex` | `[$0.8$, $5.0$]` | **absent** | - |
| n40_atcap_hi_main | 1.9 | `paper/main.tex` | `($0/200$, at most $1.9\%$)` | present | - |
| n40_atcap_intro | 0.0 | `paper/sections/introduction.tex` | `$0.0\%$ [$0.0$, $1.9$]` | present | - |
| n40_atcap_concl | 0.0 | `paper/sections/conclusion.tex` | `$0.0\%$ [$0.0$, $1.9$]` | present | - |
| n40_tpr | 6.0 | `paper/sections/discussion.tex` | `$6.0\%$ [$3.5$, $10.2$]` | present | - |
| n40_tpr_lo | 3.5 | `paper/sections/discussion.tex` | `$6.0\%$ [$3.5$, $10.2$]` | present | - |
| n40_tpr_hi | 10.2 | `paper/sections/discussion.tex` | `$6.0\%$ [$3.5$, $10.2$]` | present | - |
| n40_achieved | 5.0 | `paper/sections/discussion.tex` | `an achieved $5.0\%$ [$2.7$, $9.0$]` | present | - |
| n40_achieved_lo | 2.7 | `paper/sections/discussion.tex` | `an achieved $5.0\%$ [$2.7$, $9.0$]` | present | - |
| n40_achieved_hi | 9.0 | `paper/sections/discussion.tex` | `an achieved $5.0\%$ [$2.7$, $9.0$]` | present | - |
| replay10_floor | 12.0 | `paper/sections/discussion.tex` | `falls from a replayed $12.0\%$ [$8.9$, $15.3$] at $N{=}10$` | present | - |
| fall_points | 10.0 | `paper/sections/discussion.tex` | `$10.0$ points [$7.2$, $12.9$]` | present | - |
| leg_10_20_points | 8.9 | `paper/sections/discussion.tex` | `$8.9$ points [$6.8$, $11.1$]` | present | - |
| leg_20_40_points | 1.1 | `paper/sections/discussion.tex` | `$1.1$ points [$-0.2$, $2.4$]` | present | - |
| leg_10_20_mc_retired | 8.8 | `paper/sections/discussion.tex` | `8.8` | **absent** | - |
| leg_10_20_mc_ci_retired | 11.0 | `paper/sections/discussion.tex` | `[$6.8$, $11.0$]` | **absent** | - |
| fall_points_retired | 9.9 | `paper/sections/discussion.tex` | `9.9` | **absent** | - |
| replay10_floor_retired | 11.9 | `paper/sections/discussion.tex` | `11.9` | **absent** | - |
| replay20_floor_retired | 3.0 | `paper/sections/discussion.tex` | `3.0` | **absent** | - |
| fall_ci_lo_retired | 15.5 | `paper/sections/discussion.tex` | `15.5` | **absent** | - |
| sd20_subset | 0.98 | `paper/sections/discussion.tex` | `$0.98$ and $0.74$ points against a binomial $1.23$` | present | - |
| sd20_question | 0.74 | `paper/sections/discussion.tex` | `$0.98$ and $0.74$ points against a binomial $1.23$` | present | - |
| sd20_binomial | 1.23 | `paper/sections/discussion.tex` | `$0.98$ and $0.74$ points against a binomial $1.23$` | present | - |
| sd10_subset | 1.61 | `paper/sections/discussion.tex` | `$1.61$ and $1.63$ against $2.30$` | present | - |
| sd10_question | 1.63 | `paper/sections/discussion.tex` | `$1.61$ and $1.63$ against $2.30$` | present | - |
| sd10_binomial | 2.3 | `paper/sections/discussion.tex` | `$1.61$ and $1.63$ against $2.30$` | present | - |
| drift_chars | 3.6 | `paper/sections/discussion.tex` | `about $3.6$ characters` | present | - |
| drift_z | 4.0 | `paper/sections/discussion.tex` | `($z{=}+4.0$)` | present | - |
| drift_punct_points | 1.6 | `paper/sections/discussion.tex` | `$1.6$ points less often` | present | - |
| poisson_binomial_p | 0.081 | `paper/sections/discussion.tex` | `$p{=}0.081$` | present | - |
| chisq_p | 0.6 | `paper/sections/discussion.tex` | `$p{=}0.60$` | present | - |
| span_oracle_count | 1424 | `paper/sections/limitations.tex` | `$1424$ greedy-correct questions` | present | - |
| substring_oracle_count_absent | 1440 | `paper/sections/limitations.tex` | `1440` | **absent** | - |

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

## experiments.tex — cost of the matched design (input repaired 2026-08-19)

**The old registration was stale in both directions and green anyway.** It pinned
a MODELLED and long-superseded `228 GPU-h` to `docs/critique_log.md`, which still
contains that string, so the input
guard passed; and it verified the paper against the phrase "roughly nine GPU-days",
which `experiments.tex` had already stopped containing. A guard that reads only the
upstream side cannot see a paper that has moved on. Both sides are now pinned.

The entry-22 figure is superseded and is named here only so it cannot come back
silently. Every operational figure below carries its tag and its anchor.

| figure | provenance | value |
|---|---|---|
| entry-22 price of the judge arm (retired, superseded) | MODELLED from the 55 s unit of `docs/critique_log.md` 22, at K=180, n=80 | 227.8 GPU-h |
| clustering time on the deployed run | MEASURED, same symmetric judge, `judge_batch_size` 6, N=10, from `results/operational_number_audit.md` 2.4 | 24.0 s/clustering |
| judge arm re-priced on that unit | MEASURED, re-derived from the 24.0 s figure above at K=180, n=80 | 98.7 GPU-h |

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| re-priced cost of the judge arm | 185 x 24.0 x 80 / 3600 | 98.7 | 99 | MATCHES |
| how much too large the recorded trigger was | 228 / 98.7 | 2.31 | 2.3 | MATCHES |

In days that is 4.11, against the 9.5 the retired
figure implied. The audit's own cross-check value is carried as an input and agrees:
98.7 against 98.67 computed here.

**One thing that does not reproduce, and it is upstream of the paper.** Entry 22's
chain as quoted in `results/operational_number_audit.md` 2.4 is
`185 evaluations/target x 55 s = 171 min/target x 80 = 228 GPU-h` (MODELLED throughout, from that 55 s unit, and superseded). But 185 x 55 s is
169.6 min, not 171, and 185 x 55 x 80 / 3600 is 226.1,
not 227.8. The audit's own 227.8 back-solves to a unit of 55.4 s, not the 55 s the
same sentence prints. Nothing downstream moves — the ratio is 2.3x either way — but the
retired chain is not internally consistent, and a reader who checks it will find that
before they find anything else.

## discussion.tex — the N=40 operating points (registered 2026-08-19)

Every interval the paper prints on a COUNT over the fair pool's 200 is a Wilson
interval, and the paper says so. None of them was checkable outside the .tex. The
counts are artifact-sourced; the intervals are arithmetic and are recomputed here.

ONE ROW PRINTS NO INTERVAL. The N=40 floor is a point, `2.0%`, and that is the
ruling of `results/n40_floor_estimator_ruling.md`, not an omission: once the
ceiling atom empties, whether the top score this pool reached is the top of the
population's support is not determinable at n=200, so the estimand is NOT
IDENTIFIED -- it is 2.0% if the population can never produce 39 mutually
inequivalent answers out of 40, and can be arbitrarily smaller if it can. That
argument uses no population model. Coverage figures for the two candidates DO
use one and must be quoted with it: under the calibrated Ewens fit, 53.7%
(Wilson on 4/200) and 0.00% (question bootstrap) at nominal 95%; under the zero
branch, 95.06% and 100% (ruling sec. 8.4). The row below still prints
what Wilson WOULD give, so the withdrawal stays auditable, but nothing is
compared against the paper there -- the paper has no interval on that row to
compare to, and both candidates are pinned as retired literals above.
Population, once, for all four rows: the fair pool's 200-answer correct stratum for
false-alarm rates, its 200-answer hallucinating stratum for the true-positive rate.

| quantity | count | Wilson 95% computed | paper | verdict |
|---|---|---|---|---|
| clean correct answers at the ln 40 cap | 0/200 | 0.0% [0.00, 1.88] | 0.0% [0.0, 1.9] | MATCHES |
| cheapest firing threshold at N=40 (the floor) | 4/200 | 2.0%, no interval (Wilson on this count would be [0.78, 5.03] -- WITHDRAWN) | 2.0%, no interval | MATCHES |
| hallucinating answers that threshold catches | 12/200 | 6.0% [3.47, 10.19] | 6.0% [3.5, 10.2] | MATCHES |
| achieved false-alarm rate at a 5% budget | 10/200 | 5.0% [2.74, 8.96] | 5.0% [2.7, 9.0] | MATCHES |

The true-positive count is not printed as a count anywhere: `results/n_scaling_grid.md`
section 3 gives the rate 6.0%, and 12 is 6.0% of 200. The Wilson interval that
follows reproduces the paper's [3.5, 10.2] exactly, which is the check that the count
was read off the right denominator — the 200 HALLUCINATING answers, not the 200
correct ones. On the correct stratum the same rate would be a false-alarm rate, and
the paragraph would say the opposite of what it means.

The 0.0% row is the one the concession now rests on: its threshold is ln 40, fixed
before any data, so its one-sided Wilson upper bound of 1.88% is the pre-registered
criterion read on the pre-registered quantity (at-cap mass), and it clears 5% with
three counts to spare. Do not read it as an operating point. It is a structural
zero — the never-fire
policy — and not an operating point; the cheapest alarm that exists at N=40 costs
2.0%. `results/replay_control.md` section 5 records that `n_scaling_grid.md` conflated
the two in its floor column, which is why both rows are registered here rather than
one.

## discussion.tex — the fall across the budget (registered 2026-08-19)

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| the replayed N=10 floor, as the paper rounds it | 11.974 to 1 dp | 11.97 | 12.0 | MATCHES |
| fall from the replayed N=10 floor to the measured N=40 floor | 11.974 - 2.0 (4/200) | 9.97 | 10.0 | MATCHES |
| the N=10 -> N=20 leg, from the EXACT floors | 11.9921 - 3.1291 (exact, not the 40k-draw MC pair) | 8.86 | 8.9 | MATCHES |
| the N=20 -> N=40 leg | 3.1291 - 2.0 (4/200) | 1.13 | 1.1 | MATCHES |

**Why the leg above is derived from the exact floors and not from the two floor
inputs this script already had.** Those inputs are the report's 40,000-draw Monte
Carlo, 11.974 and 3.134. Their difference is 8.840, which rounds to **8.8**. The
exact floors differ by 8.8630, which rounds to **8.9**, and 8.9 is what the paper
prints. The end-to-end fall lands on 10.0 under either pair, which is why the
distinction never came up before; this leg straddles the decimal place the paper
quotes. THE PAPER IS RIGHT. `results/replay_control.md` prints -8.8 in its
differences table and marks it as Monte Carlo; correcting the paper down to match
it has been attempted once and was correctly refused. The exact leg is independently
recorded in that same file as -8.863, and
in `figures/fig_floor_budget_stats.json` as -8.86.

The interval on that fall, [7.2, 12.9], is a PAIRED bootstrap over the 200 questions
and is not arithmetic on anything here — it is read from `results/replay_control.md`
section 2's step table and cannot be reconstructed from the two end intervals. It is
registered as a claim, not as a derivation, and this script does not verify it.

**A retired value, recorded so it cannot return.** An earlier round quoted this fall
as **-9.9 points [-15.5, -5.0]** off floors of 11.9 / 3.0 / 2.0. Those point
estimates were averages over 200 whole replicates, whose Monte-Carlo error straddled
the first decimal; they were replaced by the mean of the 200 per-question
probabilities (`results/replay_control.md` section 2b, and
`results/post_overnight_claim_review.md` section 3.3), giving 12.0 / 3.1 / 2.0 and a
fall of 10.0 points on a much tighter paired interval. **9.9 is superseded.** The
paper is checked above for the ABSENCE of `$9.9$ points`.

## discussion.tex — the variance decomposition (registered 2026-08-19)

The paper states an identity: for a floor that is a mean of independent indicators,
the subset-draw component and the question component sum in quadrature to exactly the
binomial standard error a Wilson interval on one replicate already reports. Both
components are artifact-sourced; the two things the paper asserts about them — that
they combine to the printed binomial figure, and that the binomial figure is the one
the floor implies — are arithmetic, and were printed only in the .tex.

| budget | derivation | computed | paper | verdict |
|---|---|---|---|---|
| N=20: subset-draw component, as the paper rounds it | 0.9826 to 2 dp | 0.983 | 0.98 | MATCHES |
| N=20: question component, as the paper rounds it | 0.7433 to 2 dp | 0.743 | 0.74 | MATCHES |
| N=20: components in quadrature | sqrt(0.9826^2 + 0.7433^2) | 1.232 | 1.23 | MATCHES |
| N=20: binomial sd implied by the floor | 100 x sqrt(3.134% x (1-3.134%) / 200) | 1.232 | 1.23 | MATCHES |
| N=10: subset-draw component, as the paper rounds it | 1.6119 to 2 dp | 1.612 | 1.61 | MATCHES |
| N=10: question component, as the paper rounds it | 1.6346 to 2 dp | 1.635 | 1.63 | MATCHES |
| N=10: components in quadrature | sqrt(1.6119^2 + 1.6346^2) | 2.296 | 2.30 | MATCHES |
| N=10: binomial sd implied by the floor | 100 x sqrt(11.974% x (1-11.974%) / 200) | 2.296 | 2.30 | MATCHES |

Both budgets close to two decimals, which is the identity and not a coincidence: the
residual `results/replay_control.md` reports on the same rows is -1.1e-19 and 0.0e+00.

**Status of the 0.99 the previous round carried.** The N=20 subset-draw component was
quoted as 0.99 points from a 500-replicate Monte-Carlo
(`results/gate_paper_edits_2026_08_19.md`). The exact value over 40000 subset draws
per question is 0.9826, which is what the paper now prints as 0.98. Same quantity,
better estimator; 0.99 is superseded and is not registered.

## discussion.tex — the June/August generation drift (registered 2026-08-19)

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| how much longer the August answers run | 119.6 - 116.0 | 3.60 | 3.6 | MATCHES |
| z on the paired length difference | 3.63 / 0.91 | 3.99 | 4.0 | MATCHES |
| terminal-punctuation gap, in points | 100 x 0.0163 | 1.63 | 1.6 | MATCHES |

The z is the load-bearing one: it is what turns "the two caches differ a bit" into
"the two caches are measurably different runs", which is the sentence that stops
either arm being called the odd one out. It appears in the paper as `$z{=}+4.0$` and
nowhere else as arithmetic; 3.63 / 0.91 = 3.99 rounds to it, but only just, and a
reader who recomputed it from the printed 116.0 and 119.6 would get 3.6 / 0.91 = 3.96
instead, because the paired difference is not the difference of the two means.

## discussion.tex — the two goodness-of-fit p-values (registered 2026-08-19)

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| upper-tail p of the cluster-count fit | chisq_sf(7.39, 9) | 0.597 | 0.60 | MATCHES |

The Poisson-binomial p is NOT a derivation this script can do: it is an exact DP over
200 per-question probabilities that live in the checkpoint, not in any artifact this
file reads. It is registered as a claim with a cross-check instead.

| implementation | P(X <= 19) |
|---|---|
| `results/replay_control.md`, the producing run | 0.081 |
| `results/gate_paper_edits_2026_08_19.md`, independent reimplementation | 0.083 |
| what the paper prints | 0.081 |

**Flag, not a failure: the paper prints three decimals that two implementations do
not agree on.** 0.081 and 0.083 differ in the last digit the paper shows. The
difference changes nothing — both are far from any threshold, and the sentence they
support says the count is not out of line — but `$p{=}0.081$` claims a precision the
evidence does not have. Two significant figures (`$p \approx 0.08$`) is what the two
runs jointly support. This script does not edit the paper; it records the gap.

## Resolved: the 1440 vs 1424 oracle mix-up

This report previously carried an unresolved flag: `limitations.tex` described "the
1440 greedy-correct questions of our 2000-question replication pass" in the same
paragraph as the span-oracle AUROC, mixing the substring oracle's count with the span
oracle's result. **The paper has since been fixed** — `limitations.tex` now reads
"1424 greedy-correct questions (alias-aware span oracle...)" — and the fix is
held down by a claim above that requires `1440` to be ABSENT from that file. If it
returns, this script fails.

| quantity | derivation | computed | paper | verdict |
|---|---|---|---|---|
| the count limitations.tex now prints | results/relabel_report.md, span oracle | 1424.0 | 1424 | MATCHES |

| oracle | greedy-correct of 2000 | rate |
|---|---|---|
| substring (retired) | 1440 | 72.0% |
| span (operative) | 1424 | 71.2% |

## What is actually checked, and what is only pinned

A registration is worth exactly as much as the check behind it, and these are not
all the same strength. A DERIVED claim is recomputed from artifact inputs and
compared; a PINNED claim is only held to still appear in the .tex, which catches a
silent edit but proves nothing about the number. Anything in the second table is a
number this script cannot check — usually a bootstrap endpoint — and it is listed
here rather than left to look guarded.

Derived and compared: **33** claims. Pinned only: **21**.

| derived claim | value | compared to (decimal places) |
|---|---|---|
| arm_step | 0.03333333333333333 | 3 |
| bias_bound | 0.013 | 3 |
| chisq_p | 0.6 | 2 |
| ci_half_width | 0.05 | 3 |
| counterfactual_ratio | 2.9 | 1 |
| drift_chars | 3.6 | 1 |
| drift_punct_points | 1.6 | 1 |
| drift_z | 4.0 | 1 |
| fall_points | 10.0 | 1 |
| gpu_hours_repriced | 99 | 0 |
| gpu_trigger_ratio | 2.3 | 1 |
| headroom_correct | 0.923 | 3 |
| headroom_next_lattice | 0.277 | 3 |
| leg_10_20_points | 8.9 | 1 |
| leg_20_40_points | 1.1 | 1 |
| n40_achieved | 5.0 | 1 |
| n40_achieved_hi | 9.0 | 1 |
| n40_achieved_lo | 2.7 | 1 |
| n40_atcap | 0.0 | 1 |
| n40_atcap_hi | 1.9 | 1 |
| n40_floor | 2.0 | 1 |
| n40_tpr | 6.0 | 1 |
| n40_tpr_hi | 10.2 | 1 |
| n40_tpr_lo | 3.5 | 1 |
| pinned_pair_fraction | 0.026 | 3 |
| replay10_floor | 12.0 | 1 |
| sd10_binomial | 2.3 | 2 |
| sd10_question | 1.63 | 2 |
| sd10_subset | 1.61 | 2 |
| sd20_binomial | 1.23 | 2 |
| sd20_question | 0.74 | 2 |
| sd20_subset | 0.98 | 2 |
| span_oracle_count | 1424 | 0 |

The decimal column is the honest limit of each check: a claim compared to 1 dp is
verified against the paper only as far as the paper prints it, and a drift smaller
than that would pass. `tests/test_derived_paper_quantities.py` mutates every row by
one unit in exactly this place and requires the run to go red, so none of these is a
comparison that cannot fail.

| pinned-only claim | value | why it cannot be derived here |
|---|---|---|
| gpu_hours_retired | 228 | a retired figure, held down so it cannot be quoted live |
| gpu_days_retired_phrase | 0 | absence check on the phrase this script used to verify |
| n40_floor_wilson_retired_disc | 5.03 | not derivable from the inputs here |
| n40_floor_boot_retired_disc | 4.0 | not derivable from the inputs here |
| n40_floor_503_retired_disc | 5.03 | not derivable from the inputs here |
| n40_floor_wilson_retired_main | 5.03 | not derivable from the inputs here |
| n40_floor_503_retired_main | 5.03 | not derivable from the inputs here |
| n40_floor_wilson_retired_concl | 5.03 | not derivable from the inputs here |
| n40_floor_503_retired_concl | 5.03 | not derivable from the inputs here |
| n40_floor_rounded_retired_intro | 5.0 | not derivable from the inputs here |
| n40_atcap_hi_main | 1.9 | not derivable from the inputs here |
| n40_atcap_intro | 0.0 | not derivable from the inputs here |
| n40_atcap_concl | 0.0 | not derivable from the inputs here |
| leg_10_20_mc_retired | 8.8 | not derivable from the inputs here |
| leg_10_20_mc_ci_retired | 11.0 | not derivable from the inputs here |
| fall_points_retired | 9.9 | absence check on the superseded -9.9 |
| replay10_floor_retired | 11.9 | not derivable from the inputs here |
| replay20_floor_retired | 3.0 | not derivable from the inputs here |
| fall_ci_lo_retired | 15.5 | not derivable from the inputs here |
| poisson_binomial_p | 0.081 | exact DP over 200 per-question probabilities in the checkpoint |
| substring_oracle_count_absent | 1440 | absence check on the retired oracle's count |

## Guard results

All input literals and all paper literals verified. Every derivation above
matches the number the paper prints.

