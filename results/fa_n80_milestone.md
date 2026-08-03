# FA cell at the pre-registered n=80 — first look (2026-08-02)

Source: `results/fair_recompute_report.md` (rebuilt `--report_only` from
`wk9_def/triviaqa_se_false_alarm.jsonl`, 80/80 complete). **These are RAW attack numbers,
not the headline.** The pre-registered headline is the budget-matched paired net
(attack-max − benign-max-over-~181), which needs the K=180 null control; every rate below
carries the winner's-curse bias that control exists to remove (critique_log 21, B2).

## What the complete FA cell says

| quantity | value |
|---|---|
| success, B2 invariance-gated (greedy) | **0.588 [0.475, 0.688]** (n=80) |
| success, finding-16 sampled status | 0.475 [0.362, 0.588] |
| success, entropy-only (pre-B2) | 0.613 [0.512, 0.713] |
| attrition from the B2 status gate | 2 of 49 would-be wins (**4%**) |
| answer-flip subcategory (meaning-shift suspects) | 2/49 (4%) |
| sampled fraction-correct under q' | 81% |
| ~~feasible-paraphrase rate 1.000~~ | **WITHDRAWN — vacuous, see below** |
| mean intended entropy move | 0.524 nats |

Reading, conservatively:
- **The B2 status gate costs little in the FA direction** (4% attrition; 0.613 → 0.588).
  Contrast the partial hide cell, where attrition is 22% — consistent with the design
  intuition that hiding is more prone to accidentally *fixing* the answer. This is a
  genuine, null-control-independent finding about the criterion's bite per direction.
- **CORRECTION (critique_log 22): the "feasible rate 1.000" is an artifact, not a
  measurement, and my first reading of it was wrong.** `optimizer.best_is_feasible` is
  initialised `True` and never set `False` (the final `best_query` is either the original,
  trivially self-equivalent, or a candidate that already passed the gate), so
  `AttackOutcome.feasible` is `True` by construction and any rate over it is vacuous. It
  has been withdrawn from the report; a real per-candidate gate pass rate
  (`n_feasibility_passed / n_feasibility_checks`) is now recorded, but only for runs from
  2026-08-02 onward — the n=80 FA cell predates it, so we have NO gate-fidelity number for
  this cell. The human equivalence audit (B5) is correspondingly more load-bearing, not
  less. Two knock-ons in the same report were silently vacuous for the same reason: the
  "mean move (feasible)" was really the mean over all outcomes (relabelled), and the
  success-vs-cutoff sweep was ungated by feasibility.
- **The raw success rate is NOT the effect size.** Benign paraphrasing at the same search
  budget may achieve much of it; that comparison is the K=180 null control's job.

## ⚠ Two traps in the auto-generated report (do not lift into the paper)

1. **The AUROC degradation row (0.434 [0.303, 0.568]) is currently invalid**: it pools 80
   FA negatives against only **17** hide positives (the hide cell is mid-run). Both the
   clean AUROC and the degradation are unbalanced-subset artifacts. Recompute only when
   hide reaches 80.
2. **Clean AUROC 0.579 in that table ≠ the fair-pool 0.704** cited in the paper. The table
   computes AUROC over the *attacked subset* (80 right + 17 wrong), not the fair pool.
   Different populations; do not reconcile them, do not swap one for the other.

## Status of the hide cell
17/80 when the run was stopped by the dashboard button; per-target resumable
(`recompute_fair.py --only se_hide --n 80 --tag _def`). Its numbers above are n=17 and are
reported here only to contrast the attrition rates; they are not a result.
