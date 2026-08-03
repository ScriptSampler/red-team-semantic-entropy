# N=20 verdict: the ceiling is structural, not a sample-budget artifact (2026-08-02)

> ⚠ **SUPERSEDED IN PART — see `results/CORRECTIONS_2026-08-02.md` (2026-08-02).**
> Independent verification found the "conservative" tie rule is a ~61x OVERCORRECTION
> (exchangeable tie credit is a/(b+1) with b>=1, and measured mean b = 60.4), and that it
> is what produced the degeneracy. With a correct randomized tie rule the test is
> calibrated and powerful AT N=10 (power 0.40/0.82/0.99 at m=30/50/60) — better than
> lifting to N=20 under the broken rule, at zero GPU cost. The conclusion below does NOT
> follow; re-run with the corrected statistic before relying on it.


The pre-committed question (critique_log 23/23a) was whether raising the sample budget
rescues the false-alarm analysis. **It does not.** The decision was made by the rule fixed
in writing *before* the data landed.

## Pilot result

15 targets that saturate at N=10, re-scored at N=20 (cap ln(20) = 2.9957), same seed:

| quantity | value |
|---|---|
| still saturated at the new cap | **3/15 = 20%** |
| baselines already at the new cap | 1/15 |
| mean attack move | 0.595 nats (N=10) → 0.558 (N=20) |
| **empirical headroom gain** | **+0.304 mean, +0.110 median** |

The headroom gain is the crux. Lifting the cap by ln(20) − ln(10) = **0.693** nats does
*not* give 0.693 nats of new room, because **the baselines rise with N too**: more samples
means more clusters means higher entropy for the unattacked question as well. The median
target gained **0.110** nats of usable headroom — about a sixth of the naive expectation.

## Decision

The residual saturation of 20% landed exactly on the ambiguous bar from entry 23, which is
why entry 23a moved the decision (before the data) to a quantity that could not be argued
either way: **simulated power ≥ 0.60 at a 2× effect with m ≤ 50**, using the pilot's
empirical gains rather than the naive uniform +0.693.

Re-running with those gains (`scripts/power_sim_empirical.py`, calibrated to 46% simulated
saturation against the observed 49%):

| config | m | saturation | H0 level | power @2× | power @3× |
|---|---|---|---|---|---|
| N=10 | 30 | 46% | 0.000 | 0.00 | 0.00 |
| N=10 | 50 | 47% | 0.000 | 0.00 | 0.00 |
| N=20 | 30 | 40% | 0.000 | 0.00 | 0.00 |
| N=20 | 50 | 41% | 0.000 | 0.00 | 0.00 |

**VERDICT: do not proceed.** Power stays at zero because saturation barely moves (46% → 41%).
Note the precise word: the test is **degenerate**, not underpowered. The H0 level is also
0.000 — with conservative ties and ~46% saturation the statistic cannot reject *under the
null either*, so no increase in n would rescue it.
Per the pre-commitment, false-alarm effect sizes in nats and the false-alarm exceedance test
are **not identifiable at any feasible sample budget**, and false-alarm results are reported
via censoring-robust statistics only: operating-point flips, rank statistics on the
uncensored subset, headroom fraction, and the ratio-to-detector-signal framing.

## The identifiable false-alarm number: operating-point flips

Effect sizes in nats are censored, but a **threshold crossing is not** — once the attacked
score is past the operating point it does not matter how far past. So the deployment-relevant
quantity survives the ceiling intact:

> At a threshold set to a **10% false-positive rate on clean data**, **31 of 80 correct
> answers (39% [29%, 49%]) flip from unflagged to flagged** under a meaning-preserving
> paraphrase.

This number is valid *now*, despite the hide cell being incomplete: the threshold is set on
the clean **negatives**, which are exactly the false-alarm targets, so including or excluding
the 17 hide targets leaves it unchanged at 2.1778 (verified). It remains the **raw** attack
figure — the benign floor must still tell us what fraction random paraphrasing flips — but it
is identifiable, censoring-proof, and operationally meaningful in a way nats are not.

## What this is, positively

This is not a failed experiment; it is a measurement result about the detector. Semantic
entropy at feasible sample budgets has a hard ceiling that a meaning-preserving paraphrase
reaches on roughly half of correct answers, and raising the budget does not meaningfully
move it because the ceiling and the baseline rise together. Combined with the clean-data
finding that the whole correct-vs-wrong separation is 0.184 nats (d = 0.28) with 26% of
correct answers already in the top decile of the scale, the false-alarm direction is better
described as **a detector with no headroom** than as **a detector we cleverly attacked**.

## Note on the two saturation populations

Both are reported, as promised: **20%** of previously-saturated targets remain saturated
(the pilot's conditional rate), implying roughly **10%** overall saturation at N=20 across
all 80 targets if previously-unsaturated targets stay unsaturated. Neither number changes
the verdict, because the verdict was moved to power, and power is driven by the realized
headroom gain (+0.11 median), not by either rate.
