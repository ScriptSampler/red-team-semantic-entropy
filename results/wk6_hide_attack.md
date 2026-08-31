> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.
>
> **The `Verdict: PASS` at the foot of this file is retracted.** This is a week-6 pilot on ten
> targets picked for extreme entropy (every one starts at the `ln 10` ceiling, which is the
> selection rule, not a finding). It has no benign-paraphrase noise floor, no answer-invariance
> gate and no correction for selection on noise, so it cannot separate an attack effect from
> what benign rephrasing and sampling variance already do. The paper claims no attack effect;
> its confirmatory null control is `results/null_control_report_defb.md`. The **hide** direction
> was never run under that confirmatory null control at all.

# Attack summary: hide (wk6_hide.jsonl)

questions: 10
success (feasible + entropy drop >= 0.25 nats): 9/10
feasible paraphrase found: 10/10
mean entropy drop among feasible: 0.811 nats
max entropy drop among feasible: 1.978 nats

| qid | SE before | SE after | delta | feasible | success |
| --- | --------- | -------- | ----- | -------- | ------- |
| tc_79 | 2.303 | 1.973 | -0.330 | yes | yes |
| tc_690 | 2.303 | 2.303 | +0.000 | yes | no |
| tc_691 | 2.303 | 1.609 | -0.693 | yes | yes |
| tc_847 | 2.303 | 1.359 | -0.943 | yes | yes |
| tc_938 | 2.303 | 1.228 | -1.075 | yes | yes |
| tc_1029 | 2.303 | 1.228 | -1.075 | yes | yes |
| tc_1098 | 2.303 | 1.973 | -0.330 | yes | yes |
| tc_1128 | 2.303 | 1.973 | -0.330 | yes | yes |
| tc_1179 | 2.303 | 0.940 | -1.362 | yes | yes |
| tc_1348 | 2.303 | 0.325 | -1.978 | yes | yes |

## Verdict: PASS (9/10 = 90%)
