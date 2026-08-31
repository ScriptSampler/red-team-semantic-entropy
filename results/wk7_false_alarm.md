> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.
>
> **The `Verdict: PASS` at the foot of this file is retracted.** This is a week-7 pilot on ten
> targets picked for extreme entropy (every one starts at zero, which is the selection rule,
> not a finding). It has no benign-paraphrase noise floor, no answer-invariance gate and no
> correction for selection on noise, so it cannot separate an attack effect from what benign
> rephrasing and sampling variance already do. Run to completion under the confirmatory null
> control, the false-alarm cell **fails to reject in every clustering arm**
> (`results/null_control_report_defb.md`), and the paper claims no attack effect.

# Attack summary: false_alarm (wk7_false_alarm.jsonl)

questions: 10
success (feasible + entropy rise >= 0.25 nats): 9/10
feasible paraphrase found: 10/10
mean entropy rise among feasible: 1.137 nats
max entropy rise among feasible: 2.303 nats

| qid | SE before | SE after | delta | feasible | success |
| --- | --------- | -------- | ----- | -------- | ------- |
| tc_280 | 0.000 | 1.228 | +1.228 | yes | yes |
| tc_954 | 0.000 | 1.194 | +1.194 | yes | yes |
| tc_2701 | 0.000 | 1.359 | +1.359 | yes | yes |
| tc_2836 | 0.000 | 1.498 | +1.498 | yes | yes |
| tc_2849 | 0.000 | 2.303 | +2.303 | yes | yes |
| qz_1354 | 0.000 | 1.498 | +1.498 | yes | yes |
| qz_2324 | 0.000 | 0.802 | +0.802 | yes | yes |
| qz_2426 | 0.000 | 1.168 | +1.168 | yes | yes |
| qz_5520 | 0.000 | 0.000 | +0.000 | yes | no |
| qz_5812 | 0.000 | 0.325 | +0.325 | yes | yes |

## Verdict: PASS (9/10 = 90%)
