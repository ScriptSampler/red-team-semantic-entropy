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
| feasible-paraphrase rate | 1.000 [1.000, 1.000] |
| mean intended entropy move (feasible) | 0.524 nats |

Reading, conservatively:
- **The B2 status gate costs little in the FA direction** (4% attrition; 0.613 → 0.588).
  Contrast the partial hide cell, where attrition is 22% — consistent with the design
  intuition that hiding is more prone to accidentally *fixing* the answer. This is a
  genuine, null-control-independent finding about the criterion's bite per direction.
- **Feasibility is saturated at 1.000**: every reported win passed the bidirectional-NLI
  gate. That is exactly why the gate's fidelity is load-bearing and why the human
  equivalence audit (B5, harness built) is owed — a 100% pass rate is a statement about
  the gate, not about meaning preservation.
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
