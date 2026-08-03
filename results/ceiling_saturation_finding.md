# The false-alarm attack saturates the metric's ceiling (2026-08-02)

**Semantic entropy over N sampled answers is bounded above by log(N)** — the value attained
when every sample forms its own cluster. With the deployed N=10 that ceiling is
**ln(10) = 2.3026 nats**. This is not a modelling nicety: it censors the false-alarm effect
on half our targets, and it changes how the null control must be computed.

## Measured on the complete n=80 FA cell

| quantity | value |
|---|---|
| attacked entropy **exactly at** the ln(10) ceiling | **39/80 = 49%** |
| baseline entropy already at the ceiling (zero headroom) | 8/80 = 10% |
| headroom (ceiling − baseline) | mean 0.826, median 0.749 nats |
| attack move | mean 0.524, median 0.416 nats |
| fraction of *available* headroom consumed | mean **66%**, median **83%** |
| successes at the ceiling | 21 of 47 |

The attack does not have a free scale to move on: it consumes most of the headroom that
exists and then stops, because it cannot go further.

## Why this matters (three consequences)

**1. The effect size is CENSORED, so raw nats understate the attack.** On 49% of targets the
attacked score is at the maximum the estimator can express. Any comparison of attack
against another method is compressed at the top: two methods that both saturate look
identical regardless of how differently they would rank on an uncensored scale. Reporting
mean nats alone is therefore misleading in both directions — it understates a strong
attack and overstates the similarity between methods.

**2. It breaks the naive exceedance/null statistic.** The exchangeability null assumes a
continuous score distribution, under which ties have probability zero. Here an atom sits at
the ceiling and benign paraphrases reach it too. Confirmed on the first null-objective
ablation target (`dpql_1059`): the real attack, a null-objective beam, and plain random
paraphrasing **all landed on exactly 2.3026**. Counting only strict exceedances
(`benign > attack`) scores a benign draw that *matched* the attack as a non-exceedance —
manufacturing evidence for the attack. Fixed: `exceedance_counts(..., ties="conservative")`
(default) counts `benign >= attack`; both policies are reported, and disagreement between
them is itself the diagnostic that ceiling saturation, not attack superiority, is driving
the result. A unit test pins the failure mode (strict says p<0.05, conservative says p>0.99
on the same saturated data).

**3. N=10 is arguably too small for the false-alarm direction.** The FA attack pushes
*upward*, straight into the ceiling; the hide attack pushes *downward*, away from it, so
the two directions are not symmetric in measurement headroom. Raising N to 20 would lift
the ceiling to ln(20)=3.00 nats at 2x sampling cost. We do not re-run at N=20 here, but the
asymmetry must be disclosed: the FA direction is the one our estimator censors.

## What to report

- The **saturation rate** (49%) alongside every FA effect size, so readers can see the
  censoring rather than infer it.
- Both tie policies for any exceedance-based null test, with the conservative one as the
  claim statistic.
- The headroom-consumed fraction (66% mean / 83% median) as a censoring-robust companion to
  raw nats: it is scale-free and defined even at saturation.
- A limitation sentence on the N=10 ceiling and the FA/hide asymmetry it induces.

Code: `se.stats.ceiling_saturation`, `se.stats.exceedance_counts(ties=...)`.
Data: `wk9_def/triviaqa_se_false_alarm.jsonl` (n=80), `results/null_objective_ablation_ckpt_def.jsonl`.
