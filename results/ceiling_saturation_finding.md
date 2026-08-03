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

## Follow-up: the FA success rate is substantially a property of the TARGET, not the attack

Splitting the n=80 cell by headroom (ceiling − baseline entropy):

| stratum | n | gated success | move (mean) | headroom (mean) | headroom used |
|---|---|---|---|---|---|
| saturated (censored) | 39 | 0.538 [0.385, 0.692] | 0.502 | 0.502 | **100%** (by definition) |
| uncensored | 41 | 0.634 [0.488, 0.780] | 0.544 | 1.133 | **40%** |
| low headroom (≤ median) | 40 | **0.375** [0.225, 0.525] | 0.208 | 0.292 | — |
| high headroom (> median) | 40 | **0.800** [0.675, 0.925] | 0.839 | 1.359 | — |

- **corr(headroom, move) = +0.70; corr(headroom, success) = +0.53.** Whether a false-alarm
  attack "succeeds" is predicted more by how much room the target had than by anything the
  optimiser did. A success rate quoted without this conditioning describes the pool as much
  as the attack.
- **8 of 80 targets (10%) have ZERO headroom** — their baseline is already at the ceiling,
  every attack move is exactly 0.000, and none can ever succeed. They are structurally
  unattackable in the false-alarm direction. Score-independent selection (which we insist
  on, to avoid circularity) is what puts them in the pool; that is the right trade, but it
  means ~10% of the denominator is unwinnable by construction and must be disclosed.
- On the targets that are NOT censored, the attack consumes only **40%** of the available
  headroom — i.e. where the metric can still move, the attack is far from exhausting it.

**Why the paired design survives this.** Censoring afflicts the attack and the benign floor
*equally within a target*, because both face the same ceiling on the same question. A
paired, per-target null control is therefore the right structure and is robust to the
censoring — with one exception, which is exactly the defect found above: **ties at the
ceiling**. That is now handled by the conservative tie policy rather than by luck.

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
