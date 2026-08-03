# Power of the exact exceedance test UNDER the ceiling — the FA analysis does not work at N=10

Critic ruling (critique_log 23) demanded the power calculation be redone with the empirical
saturation rate instead of the continuous-score assumption. Result: **at N=10 the test has
zero power at every budget we could afford.** This is the decisive design finding of the
session and it inverts the plan.

## Simulation

Anchored to the real data, not to a convenient model:
- per-target headroom drawn from the **empirical n=80 FA distribution** (ceiling − baseline),
- every draw censored at that target's headroom (i.e. at the ln(10) ceiling),
- **conservative ties** (a benign draw that matches the attack counts against it),
- per-draw scale calibrated so the simulated attack saturation is **48%**, matching the
  observed 49%,
- H1 modelled as "the attack is worth `mult`× its candidate budget"; 400 trials per cell.

## Result

| m (benign draws) | n | H0 level | power @2× | power @3× | power @5× |
|---|---|---|---|---|---|
| 30 | 80 | 0.000 | **0.00** | **0.00** | **0.00** |
| 50 | 80 | 0.000 | **0.00** | **0.00** | **0.00** |
| 60 | 80 | 0.000 | **0.00** | **0.00** | **0.00** |

**With the ceiling lifted** (N=20 ⇒ headroom + 0.693 nats), same machinery:

| m | saturation | H0 level | power @2× | power @3× |
|---|---|---|---|---|
| 30 | 7% | 0.022 | 0.46 | 0.77 |
| 50 | 7% | 0.045 | **0.71** | **0.96** |

## Why the test is DEGENERATE (not merely underpowered)

The H0 level is 0.000 alongside the zero power: the statistic cannot reject under the null
either. This is degeneracy, not a sample-size problem, and no increase in n fixes it.


On a saturated target the benign draws reach the ceiling too — confirmed on real data
(`dpql_1059`: the attack, a null-objective beam, and plain random paraphrasing all landed
on exactly 2.3026). Under the conservative tie rule every one of those benign draws counts
as an exceedance, so a saturated target contributes a large K_j regardless of how good the
attack was. With 49% of targets saturated, the observed total S sits far above the null
expectation (E[S] = 80·30/182 ≈ 13.2) on every run, and the one-sided p-value is ≈1 always.
**Increasing m makes it worse, not better** — more benign draws means more ties. That is why
buying power with a larger benign budget cannot work here; the constraint is the ceiling,
not the sample size.

This is model-robust: it follows from ties at an atom, not from the particular move
distribution assumed.

## Consequences

1. **N=20 is not a refinement — it is the enabling condition.** The FA exceedance analysis
   cannot be run at N=10 at any affordable m.
2. **m = 50 at N=20** is the design that clears the pre-registered bar (power 0.71 at 2×,
   0.96 at 3×), and it costs ~2× the sampling of N=10 — still far under the 228 GPU-hours we
   escaped by adopting the exact test.
3. **The pilot decides whether this is even available.** If the attack simply drives the
   model to 20 distinct answers, saturation returns at ln(20) and no feasible N fixes it; the
   honest fallback is then to report false-alarm results via censoring-robust statistics only
   (rank/exceedance on the uncensored subset, operating-point flips, headroom fraction) and to
   state that nats effect sizes are not identifiable for FA. `scripts/pilot_n20_ceiling.py`
   measures exactly this on the targets that saturate at N=10.

Caveat, stated plainly: the H1 model (exponential moves censored at headroom) is a model.
The *power* numbers inherit that; the *zero-power* conclusion does not, because it follows
from the tie mechanism above. The 48%-vs-49% saturation calibration is what anchors it.
