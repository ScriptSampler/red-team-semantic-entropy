# START HERE — state as of Sun 2026-08-02 ~03:00

## The night changed the paper's centre of gravity

We came in to run the definitive judge experiment. Instead we found that **the measurement
itself is the problem**, and that is a better paper. Three findings, all committed with
tests and independently verified:

1. **The false-alarm attack saturates the metric.** Semantic entropy over N samples is
   capped at log(N) = 2.3026 at N=10. **39/80 (49%) of attacked FA targets finish exactly at
   that cap**; 8/80 baselines are already there (structurally unattackable). Attack, a
   null-objective beam, and plain random paraphrasing all landed on exactly 2.3026 on the
   first ablation target. → `results/ceiling_saturation_finding.md`
2. **That ceiling kills the planned analysis.** The exact test I built has **ZERO power at
   N=10** at every affordable benign budget (m=30/50/60, for effects worth 2x/3x/5x): on a
   saturated target the benign draws also hit the cap, conservative ties count them, and the
   statistic can never reject. Raising m makes it *worse*. → `results/power_under_ceiling.md`
3. **The detector has almost no dynamic range where the attack operates.** On clean data the
   entire correct-vs-wrong separation is **0.184 nats (Cohen's d = 0.28)**, 26% of *correct*
   answers already sit in the top 10% of the scale, and the estimator takes only 22 distinct
   values. The attack's mean move is ~**2.8x the detector's whole signal**. →
   `results/dynamic_range_finding.md`

Together: it is less "we built a clever attack" and more "**the score has nowhere to go, and
getting it there is easy**" — a paradigm-level statement, which is exactly what the
protocol-led framing exists to carry.

## What is running / what to do first

- **N=20 ceiling pilot** (`scripts/pilot_n20_ceiling.py`, per-target checkpointed, resume by
  re-running the same command). At last check 5/15 done, 1 still saturated. **This decides
  everything**: if residual saturation < 20%, the FA analysis proceeds at **N=20, m=50**
  (simulated power 0.71 @2x, 0.96 @3x). If >= 20%, FA nats are declared NOT identifiable at
  feasible N and we report censoring-robust statistics only. THIS BAR WAS PRE-COMMITTED
  BEFORE THE DATA (critique_log 23) — do not renegotiate it after seeing the result.
  ⚠ Caveat found mid-pilot: **baselines rise with N too**, so headroom grows far less than
  log(20)−log(10)=0.693 (observed gains: +0.11, +1.61, +0.49). Re-run the power simulation
  with the pilot's EMPIRICAL headroom gains before trusting the N=20 power numbers.
- **Null-objective ablation** paused at 1/10 (`results/null_objective_ablation_ckpt_def.jsonl`),
  resumable. It is now the **validity gate** for the exact test's exchangeability null, and
  the critic ruled 10 targets underpowered for that — run the exchangeability check on the
  cheap NLI arm with many more targets instead, then transfer to the judge.
- **Hide cell** at 17/80 (`recompute_fair.py --only se_hide --n 80 --tag _def`), resumable.

## Locked decisions (do not re-litigate)

- **Judge = 0.93 [0.90, 0.96], n=300, symmetric deployed config.** The one citation number.
  Pre-registered gate FAILS on positives (0.65) — disclosed in Methods main text, FA-only
  scope, NLI/exact bracket reported alongside.
- **Claim statistic = the exact beta-binomial exceedance test** (rank-based, hence
  censoring-robust), CONDITIONAL on the ablation validating exchangeability; **prefix is the
  pre-registered fallback**. Pre-committed switch: exact test is primary iff the ablation's
  mean exceedance count lies within [0.5x, 2.0x] of m/(N+1).
- **Ties: conservative primary, mid-p secondary, strict = disqualified diagnostic.** The
  strict-vs-conservative disagreement is itself a publishable diagnostic.
- **No cross-direction comparisons in nats.** FA has half the headroom of hide (0.826 vs
  1.661) — now a Methods section, not a caveat.
- Effect sizes to report as a triple: saturation rate + uncensored-subset nats + headroom
  fraction, with the 0/0 exclusion rule stated; plus the ratio-to-detector-signal framing.

## Still owed
Messy-real-sample judge validation; differential over-splitting check; human equivalence
audit (harness built: `prepare_equivalence_audit.py`); benign-floor diagnosis
(`diagnose_benign_floor.py`); the venue re-checks flagged in `related_work.bib` annotes.

## Reference
`docs/critique_log.md` entries 21-23 hold the rulings and both pre-commitments.
`docs/paper_review_punchlist.md` tracks the 25-item review. Tests: 129 passing.
