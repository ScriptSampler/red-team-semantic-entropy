# The false-alarm attack saturates the metric's ceiling (2026-08-02)

> **REFRESHED FROM THE DEFINITIVE `_defb` RUN (2026-08-12).** Everything below was computed
> on the superseded `wk9_def` FA cell. The instrumented `_defb` FA cell is now complete at
> n=80 and supersedes it. Recomputed:
>
> | quantity | `_def` (below) | **`_defb` (definitive)** |
> |---|---|---|
> | baseline already at ceiling | 8/80 = 10% | **8/80 = 10%** (unchanged) |
> | at ceiling AFTER attack (total) | 39/80 = 49% | **42/80 = 52.5%** |
> | ATTACK-INDUCED saturation | 31/80 = 38.75% | **34/80 = 42.5%** |
> | baseline in top tenth of range | 21/80 = 26% | **21/80 = 26.2%** (unchanged) |
> | distinct baseline entropy values | 22 | **22** (unchanged) |
>
> The three *clean-baseline* statistics are IDENTICAL under the instrumented optimiser, which
> is the robustness check that matters: the ceiling/granularity finding does not depend on the
> attack instrumentation. Only the attack-induced figure moved (38.75% -> 42.5%), as expected
> since `_defb` changed the candidate filter from `>` to `>=`. The paper now cites the `_defb`
> numbers. Caught by the critic gate of 4c35975: the Abstract had been carrying the `_def` 39%
> while `_defb` was mid-flight.

> ⚠ **DENOMINATORS CORRECTED — see `results/CORRECTIONS_2026-08-02.md`.** The 49% is the
> TOTAL at-ceiling rate; ATTACK-INDUCED saturation is 31/80 = 38.75% (8 targets were
> already pinned). The "66%/83% of headroom consumed" was computed on n=72, not 80, with
> the estimand unstated; on the 41 UNCENSORED targets it is 39.9% mean / 38.6% median.
> The ceiling itself, and corr(headroom, move)=+0.71 (+0.68 within the uncensored subset, n=38) [_defb; the _def cell gave +0.70/+0.67 at n=41],
> are confirmed.


**Semantic entropy over N sampled answers is bounded above by log(N)** — the value attained
when every sample forms its own cluster. With the deployed N=10 that ceiling is
**ln(10) = 2.3026 nats**. This is not a modelling nicety: it censors the false-alarm effect
on half our targets, and it changes how the null control must be computed.

## Measured on the complete n=80 FA cell

| quantity | value |
|---|---|
| attacked entropy at the ln(10) ceiling (TOTAL) | 39/80 = 49% |
| **ATTACK-INDUCED** saturation (excludes the 8 already pinned) | **31/80 = 38.75%** |
| baseline entropy already at the ceiling (zero headroom) | 8/80 = 10% |
| headroom (ceiling − baseline) | mean 0.826, median 0.749 nats |
| attack move | mean 0.524, median 0.416 nats |
| headroom consumed, UNCENSORED targets (n=41, _def; n=38 under _defb) | mean **39.9%**, median **38.6%** |
| ~~headroom consumed, all targets~~ | ~~66%/83%~~ — computed on n=72, estimand unstated; withdrawn |
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
manufacturing evidence for the attack. SUPERSEDED FIX (critique_log 26): the conservative rule adopted here was itself wrong — it
overcredits ties and has power 0.05 at full saturation. The claim statistic is now
RANDOMIZED (exchangeable) tie-breaking, `exceedance_counts_randomized`, which is calibrated
AND powerful (0.71 @2x). Strict and conservative are retained as diagnostics only, and
their disagreement remains the signal that saturation is driving the comparison.

**3. N=10 is arguably too small for the false-alarm direction** (but raising it does NOT
rescue the analysis — see results/n20_verdict.md; and the statistic works at N=10 under the
correct tie rule, so no re-run is needed). The FA attack pushes
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
ceiling**. Those are now handled by randomized (exchangeable) tie-breaking, which reads the
tie multiplicity `b` the instrumented optimiser records; the conservative policy first
adopted here was itself wrong and is retained only as a diagnostic (critique_log 26).

## What to report

- The **saturation rate** (49%) alongside every FA effect size, so readers can see the
  censoring rather than infer it.
- All three tie policies, with the RANDOMIZED one as the claim statistic (critique_log 26).
- The headroom-consumed fraction on UNCENSORED targets (39.9% mean / 38.6% median), with
  the 0/0 exclusion rule stated explicitly (8 targets have zero headroom).
- A limitation sentence on the N=10 ceiling and the FA/hide asymmetry it induces.

Code: `se.stats.ceiling_saturation`, `se.stats.exceedance_counts(ties=...)`.
Data: `wk9_def/triviaqa_se_false_alarm.jsonl` (n=80), `results/null_objective_ablation_ckpt_def.jsonl`.
