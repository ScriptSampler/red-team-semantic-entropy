> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.

# Attack summary: false_alarm (triviaqa_sre_false_alarm.jsonl)

questions: 15
success (feasible + entropy rise >= 0.25 nats): 12/15
feasible paraphrase found: 15/15
mean entropy rise among feasible: 0.982 nats
max entropy rise among feasible: 2.903 nats

| qid | SE before | SE after | delta | feasible | success |
| --- | --------- | -------- | ----- | -------- | ------- |
| tc_2 | 2.983 | 2.983 | +0.000 | yes | no |
| tc_33 | 1.171 | 2.543 | +1.371 | yes | yes |
| tc_40 | 1.979 | 2.312 | +0.333 | yes | yes |
| tc_49 | 1.395 | 2.453 | +1.058 | yes | yes |
| tc_56 | 2.889 | 3.063 | +0.173 | yes | no |
| tc_133 | 0.624 | 1.486 | +0.862 | yes | yes |
| tc_137 | 0.847 | 1.041 | +0.194 | yes | no |
| tc_217 | 0.837 | 1.536 | +0.699 | yes | yes |
| tc_219 | 2.048 | 3.005 | +0.957 | yes | yes |
| tc_241 | 0.173 | 1.979 | +1.806 | yes | yes |
| tc_267 | 2.441 | 2.925 | +0.484 | yes | yes |
| tc_280 | 0.000 | 1.639 | +1.639 | yes | yes |
| tc_282 | 0.000 | 2.903 | +2.903 | yes | yes |
| tc_288 | 1.113 | 2.296 | +1.183 | yes | yes |
| tc_304 | 1.878 | 2.947 | +1.069 | yes | yes |

## Verdict: PASS (12/15 = 80%)
