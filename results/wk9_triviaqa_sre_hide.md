> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.

# Attack summary: hide (triviaqa_sre_hide.jsonl)

questions: 15
success (feasible + entropy drop >= 0.25 nats): 11/15
feasible paraphrase found: 15/15
mean entropy drop among feasible: 0.644 nats
max entropy drop among feasible: 1.803 nats

| qid | SE before | SE after | delta | feasible | success |
| --- | --------- | -------- | ----- | -------- | ------- |
| tc_69 | 2.045 | 1.603 | -0.442 | yes | yes |
| tc_79 | 3.120 | 2.636 | -0.484 | yes | yes |
| tc_106 | 0.847 | 0.287 | -0.560 | yes | yes |
| tc_149 | 1.368 | 1.368 | +0.000 | yes | no |
| tc_165 | 2.080 | 2.080 | +0.000 | yes | no |
| tc_245 | 2.381 | 2.381 | +0.000 | yes | no |
| tc_261 | 1.573 | 1.113 | -0.460 | yes | yes |
| tc_276 | 2.395 | 1.190 | -1.205 | yes | yes |
| tc_298 | 2.348 | 1.113 | -1.234 | yes | yes |
| tc_397 | 1.878 | 1.878 | +0.000 | yes | no |
| tc_515 | 2.513 | 1.872 | -0.641 | yes | yes |
| tc_518 | 1.594 | 0.847 | -0.747 | yes | yes |
| tc_559 | 2.485 | 0.682 | -1.803 | yes | yes |
| tc_585 | 2.579 | 1.486 | -1.093 | yes | yes |
| tc_626 | 2.496 | 1.501 | -0.995 | yes | yes |

## Verdict: PASS (11/15 = 73%)
