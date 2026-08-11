# START HERE — current state, 2026-08-07

Supersedes every earlier version of this file. Two of its previous headline conclusions
were overturned; if you are reading a cached copy that says the ceiling makes the
false-alarm analysis impossible, or that conservative tie-breaking is the primary rule,
that copy is wrong.

## Where the project actually stands

**Findings that hold (verified, arithmetic independently re-derived from raw data):**

1. **The FA attack saturates the metric.** Semantic entropy is capped at log(N) = 2.3026
   at N=10. **39/80 attacked FA targets finish exactly there.** 8/80 baselines already sit
   at the cap and can never move (attack move exactly 0.000, zero successes). *Corrected
   denominators:* 49% is the TOTAL at-ceiling rate; **attack-induced saturation is 31/80 =
   38.75%**. The "66%/83% headroom consumed" figure was computed on n=72, not 80; on the 41
   uncensored targets it is **39.9% mean / 38.6% median**.
   corr(headroom, move) = **+0.70**, and it holds *within* the uncensored subset (+0.67), so
   it is not a censoring artifact. → `results/ceiling_saturation_finding.md`
2. **Winner's curse — COMPLETE at n=60.** Re-scoring the selected paraphrase on a fresh
   seed: **+0.698 → +0.315 nats, 45% retention**, shrinkage **−0.383 [−0.529, −0.234]**.
   The CI excludes zero, so the inflation is *proven*: the reported effect is ~2.2× what
   survives independent re-measurement. 36/60 keep a positive move (r = +0.46), so real
   signal remains. → `results/winners_curse_partial.md`
3. **The detector has little dynamic range** — but the numbers in that write-up are
   OVERSTATED and being fixed (see Owed). What survives: 10% of clean correct answers sit
   at the cap, 26% in the top decile, the estimator takes 22 distinct values over 97
   targets. → `results/dynamic_range_finding.md`

**Overturned — do not cite:** the N=20 verdict and the "zero power / FA not identifiable"
conclusion. Both were artifacts of the conservative tie rule, not of the ceiling
(`results/CORRECTIONS_2026-08-02.md`, critique_log 25–26). The N=20 *measurement* stands
(headroom gain only +0.11 median); the *inference* from it does not.

## The statistic (settled 2026-08-04, critique_log 26)

**Randomized (exchangeable) tie-breaking is the claim statistic.** Simulation at full
ceiling saturation: strict H0 level **0.995** (broken), conservative power **0.05** (dead),
randomized level 0.093 with power **0.71 @2×**. Strict and conservative are reported as
diagnostics only; disagreement between them signals that saturation, not attack strength,
is driving the comparison. → `results/tie_rule_showdown.md`

Why it works, and why I got it wrong twice: the ceiling pins the max's **value** under both
hypotheses, but the signal is the **multiplicity at the max** — a stronger attack lands more
candidates on the ceiling, shrinking each tied benign draw's `1/(b+1)` credit.

**`b` must be MEASURED.** Estimating it from benign data assumes H0 and erases the signal.
It was previously *unrecordable* (the optimiser filtered ties out before the feasibility
gate); now fixed and persisted as `n_feasible_at_best`. `null_control.py` prints a bold
warning if it runs on a campaign lacking it.

## Pre-committed design (critique_log 26a — fixed before any data)

> **N = 10 samples, m = 50 benign paraphrases/target, n ≥ 80 targets, randomized ties,
> LLM-judge as the FA adjudicator.** Power 0.84 @2×, 0.99 @3×. m=50 over the cheaper m=30
> because the winner's-curse result says the true effect is modest. If compute forces a
> smaller m, report the shortfall — do not re-choose m after seeing results.

## Running now

Fresh **`_defb`** campaign (both cells re-run under the instrumented optimiser, ~28 GPU-h),
chained into the **definitive null control** (m=50, ~67 GPU-h). ~95h total, all per-target
checkpointed. Resume either with the identical command.

`_defb` exists because `_def` is unusable for the claim statistic: its FA cell ran entirely
pre-instrumentation, and its hide cell is *mixed* (targets 1–17 old code, 18–55 new). `_def`
is retained for comparison.

## Owed

- **Fix the overstated dynamic-range claims** (C3/C4/C5): d=0.28 implies AUROC 0.579, not
  0.704 — that reconciliation is withdrawn; the +0.184 separation is NOT significant
  (p=0.296); "2.8× the detector's signal" is ~2.1× censoring-corrected with a CI spanning
  zero — honestly **one** class separation, not three.
- Judge validation on **messy real sampled pairs** (current 0.93 is on clean gold aliases).
- **Differential over-splitting check** (attack vs benign cluster counts).
- **Human equivalence audit** (harness built: `prepare_equivalence_audit.py`).
- **Quantify how often BENIGN paraphrases reach the ceiling** — if often, the sharpest
  honest claim is that inducing a false alarm needs no adversarial optimisation at all.
- **Exchangeability check** for the test's null, on the cheap NLI arm at many targets.
- Rebuild the **flip test's** null (currently quarantined, H0 level 0.35–0.81, Jensen bias).
- **Two-hour scoop de-risk**: OpenReview/ARR sweep + full-text grep of four papers for the
  log N bound (the (C) novelty is a claim of absence).

## Framing (critic-approved, scoop-checked)

FA-led survives, reframed: not "we attack FA, here is the effect size" but "**FA is where
the detector has no headroom**." The scoop check confirmed nobody attacks a hallucination
detector to manufacture false positives — that direction is the most defensible novelty.
But the protocol and winner's-curse contributions are **partially scooped** (Chouldechova
et al. NeurIPS 2025; Best-of-N Jailbreaking §5.4) and must be presented as imported hygiene
applied to a stochastic detector score, with the numbers as the deliverable.
→ `docs/paper_review_punchlist.md`, and the scoop memo.

## Reference
`docs/critique_log.md` 21–26a — every ruling and pre-commitment, including 23a and 26a where
bars were tightened *before* the data. 138 tests passing.
