> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.

# Attack summary: false_alarm (triviaqa_se_false_alarm.jsonl)

questions: 15
success (feasible + entropy rise >= 0.25 nats): 12/15
feasible paraphrase found: 15/15
mean entropy rise among feasible: 0.907 nats
max entropy rise among feasible: 2.303 nats

| qid | SE before | SE after | delta | feasible | success |
| --- | --------- | -------- | ----- | -------- | ------- |
| tc_280 | 0.000 | 1.498 | +1.498 | yes | yes |
| tc_954 | 0.000 | 1.418 | +1.418 | yes | yes |
| tc_2701 | 0.000 | 1.168 | +1.168 | yes | yes |
| tc_2836 | 0.000 | 0.940 | +0.940 | yes | yes |
| tc_2849 | 0.000 | 2.303 | +2.303 | yes | yes |
| qz_1354 | 0.000 | 1.418 | +1.418 | yes | yes |
| qz_2324 | 0.000 | 0.802 | +0.802 | yes | yes |
| qz_2426 | 0.000 | 1.834 | +1.834 | yes | yes |
| qz_5520 | 0.000 | 0.000 | +0.000 | yes | no |
| qz_5812 | 0.000 | 0.325 | +0.325 | yes | yes |
| qb_34 | 0.000 | 0.639 | +0.639 | yes | yes |
| qb_66 | 0.000 | 0.000 | +0.000 | yes | no |
| qb_92 | 0.000 | 0.000 | +0.000 | yes | no |
| qb_189 | 0.000 | 0.325 | +0.325 | yes | yes |
| qb_203 | 0.000 | 0.940 | +0.940 | yes | yes |

## Verdict: PASS (12/15 = 80%)
