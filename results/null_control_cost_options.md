# Null control: what the remaining GPU-hours buy, and what a cheaper design forfeits

Produced by `scripts/null_control_cost_options.py` (read-only; launches no GPU work).
Job under costing:

```
scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 \
    --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 \
    --dump_diag results/diag_defb.json --checkpoint auto
```

**Bottom line: the ~60 GPU-h figure is wrong by about 2.5x. Measured on the run's own
wall-clock, the remainder is 23-26 GPU-h -- two to three nights, not six. Finish
it as designed.** No cheaper design removes a meaningful cost; the largest saving on
offer is under one night and costs a third of the design's power. The one genuinely
free result (the prefix statistic) is a companion to this run's data, not a
substitute for it -- half of it is the benign arm this run exists to produce.

## 1. Re-deriving the cost from the run itself

`~67 GPU-h` (critique_log 26a, `docs/definitive_run_plan.md`,
`results/null_objective_ablation_plan.md` §6) is a MODEL: *55 clusterings/target at
~55 s each => ~50 min/target*. The 55 s came from a K=8 measurement in critique_log
22 (*13 calls ~ 12 min/target*, 2026-08-02). The deployed run refutes it.

Three filesystem anchors (local time), none depending on a per-eval assumption:

| anchor | source | local time |
|---|---|---|
| matrix stage hands the chain over | mtime of `wk9_defb/triviaqa_se_hide.jsonl` | 2026-08-13 07:21:22 |
| target 1 written | ctime of `null_control_ckpt_defb.jsonl` -- the file is opened `"a"` only at the first record write (`null_control.py:413`) | 2026-08-13 07:42:07 |
| target 11 written | mtime of the same file | 2026-08-13 11:00:42 |

- Targets 2..11 span **11915 s** for 10 targets => **1191 s/target** (19.9 min) as a mixed average.
- Hand-off to target 11 is 13160 s. Charging 11 targets at that rate leaves **53 s** for process start plus loading Llama-8B-4bit + DeBERTa-large + Qwen-7B-4bit. That the residual lands at a plausible model-load time is the consistency check; it is not something the two anchors were fitted to.

Measured per clustering: **24.0 s** (fit below) against the 55 s the
budget assumed.

**The conclusion does not depend on reading the ctime as target 1's write.** Suppose
instead that the file somehow existed from process start. Then all 11 targets fall
inside the 11915 s span, giving 1083 s/target and 20.8 GPU-h remaining -- and it would also
require 1245 s of pure model loading between the hand-off and process start, which is not credible for three cached quantised models. Either
reading lands in the low twenties of GPU-hours; neither lands near 60.

### The mixed average understates a normal target, and why

Two of the 11 completed targets did not get a full benign arm. `_benign_moves_arms` stops at `K` feasible draws **or `5K` tries**, so a question
whose paraphrases keep failing the NLI gate returns a short arm -- and a short arm
is CHEAPER, not dearer (250 proposer+gate attempts, but fewer than 50 SE evals).

| question_id | benign draws returned |
|---|---|
| `qb_565` | **0** of 50 |
| `qz_1745` | **26** of 50 |
| the other 9 | 50 of 50 |

Fitting `T_j = c_arms*(2 + n_seeds + m_j) + 0.52*tries_j` over the measured span gives **c_arms = 24.0 s** and a full-arm target at **1349 s**. Two inputs to that fit are
assumed rather than measured -- the 0.52 s propose+gate unit (the token split in
`null_objective_ablation_plan.md` §6) and an 85% benign gate pass rate -- and neither
matters: proposer work is only 4% of the span, so halving the
assumed pass rate moves the full-target cost by 2 s and doubling the per-try cost moves it by 28 s.
So:

| projection for the remaining 69 targets | GPU-h |
|---|---|
| at the observed mix (2/11 short arms) | **22.8** |
| if every remaining target gets a full 50-draw arm (upper bound) | **25.9** |
| the budget's own figure, for comparison | ~60 |

Both anchors *include* any crash and restart inside the window
(`run_definitive_chain.sh` retries after 60 s with a full model reload), so these are
upper bounds on marginal cost, not best cases.

**Caveats, stated not buried.** `/tmp/defb_chain.log` did not survive the WSL restart
at 22:56 on 2026-08-13, so per-target timing lines are gone; this is a span/count
average over 10 targets, not 10 individual timings. GPU contention during the window is unknown. The short-arm rate (2/11) is itself
estimated on 11 targets. All three uncertainties push the estimate up, and it is
still under half the budgeted figure.

## 2. The prefix statistic: exactly which half is free

critique_log 22 pre-registers the fallback claim statistic as *attack-max over the
FIRST m candidates vs benign-max over m, both matched at m, under the judge*, with
**m = 36** (k=4 iterations x 9 candidates) fixed in writing.
`results/null_objective_ablation_plan.md` §7 calls it assumption-free and says it
*costs ZERO new GPU*. Both halves of that need separating.

**Free, and genuinely so.** `trajectory_best_obj[t]` is the running best after
`1 + 9t` objective calls, recorded on all 80 targets, so the attack's achievement at
every prefix budget is already on disk. The budget curve, at no cost:

| budget (calls) | iterations | mean move (nats) | share of the full-181 move | targets already at their final max |
|---|---|---|---|---|
| 1 | 0 | 0.0000 | 0.0% | 25.0% |
| 10 | 1 | 0.3282 | 62.4% | 53.8% |
| 19 | 2 | 0.4049 | 77.0% | 66.2% |
| 28 | 3 | 0.4471 | 85.1% | 77.5% |
| 37 | 4 | 0.4578 | 87.1% | 81.2% |
| 46 | 5 | 0.4696 | 89.3% | 85.0% |
| 55 | 6 | 0.4830 | 91.9% | 86.2% |
| 91 | 10 | 0.5001 | 95.2% | 91.2% |
| 136 | 15 | 0.5221 | 99.3% | 97.5% |
| 181 | 20 | 0.5256 | 100.0% | 100.0% |

n = 80 targets (60 move at all); every target ran the full [181] objective calls, so no target's prefix is an artefact of a short run.
A budget-37 prefix keeps 87% of the attack's total move and 89% at 46. Truncating the attacker to the pre-registered m=36 is a mild handicap, not a gutting -- which is the substantive
thing this free computation establishes, and it was worth establishing.

**Not free.** The statistic is a comparison and its other half is `benign-max over
m`, which is the null control's benign arm and nothing else. §7's phrase is written
inside a branch where the null control has ALREADY run; lifted out of that branch it
reads as though the whole statistic were free. It is not:

| component | on disk today | GPU to obtain |
|---|---|---|
| attack-max at any budget m <= 181, all 80 targets | yes (`trajectory_best_obj`) | none |
| benign-max over m <= 50 under NLI / exact / judge | 11 of 80 targets | this run |
| seed-noise band | 11 of 80 targets | this run |

Two consequences worth acting on:

1. **A K=50 benign arm already serves the prefix statistic at every m <= 50.** Benign
   draws are exchangeable, and `se.stats.expected_max_at_budget` computes the exact
   expected max of a random m-subset with no distributional assumption. So the
   pre-registered m=36 needs no separate run and no change to `--K 50`. The prefix
   statistic is a free *by-product* of finishing this job.
2. **It does not shrink the job.** The only version of the prefix statistic that
   costs nothing more is the one restricted to the targets whose benign arm exists,
   i.e. n = 11. What that buys is §3 and §5.

## 3. The exceedance test cannot reject below a minimum n -- and n=11 is below it

`exceedance_test` returns P(S <= s) under a convolution of BetaBinomial(m; 1, A), so
the smallest p it can EVER return is P(S = 0) = (A/(A+m))^n. Below the n where that
crosses alpha, no data can produce a rejection.

| m | min attainable p at n=11 | min attainable p at n=80 | smallest n that can reject at 0.05 |
|---|---|---|---|
| 20 | 0.3157 | 2.28e-04 | **29** |
| 30 | 0.1851 | 4.70e-06 | **20** |
| 36 | 0.1360 | 4.98e-07 | **17** |
| 50 | 0.0683 | 3.35e-09 | **13** |
| 80 | 0.0178 | 1.92e-13 | **9** |

Computed through the deployed `exceedance_test`; agrees with the closed form to 7.1e-14. A = 181.

**The 11 targets on disk therefore cannot reject under the exceedance test at any m: min p = 0.068 > 0.05.** The floor is far below n=40, so it never
binds on a reduced-n design -- it binds only on *just analyse what we already have*.

The prefix statistic has no such floor. A one-sided sign test on 11 paired targets
reaches p = 2^-11 = 0.00049 at best, and the paired bootstrap is continuous.
That asymmetry -- not assumption-freeness -- is the operative reason the prefix
statistic is the right thing to compute on a partial run.

## 4. Power on the DEPLOYED analytic null, over m and n

DGP imported from `scripts/power_sim_deployed.py`: headroom from `data\cache\attacks\wk9_defb_snap\triviaqa_se_false_alarm.jsonl`,
per-draw scale 0.12 calibrated to 0.45 saturation against the observed 0.49,
A = 181, alpha = 0.05. Per-target draws are vectorised here so the (m x n)
grid is affordable; validated against the scalar `one_target_parts` they replace:

| m | effect | scalar mean K | vectorised mean K | z |
|---|---|---|---|---|
| 30 | 1x | 0.1611 | 0.1661 | -1.67 |
| 30 | 2x | 0.0827 | 0.0824 | +0.13 |
| 50 | 1x | 0.2754 | 0.2708 | +1.14 |
| 50 | 2x | 0.1404 | 0.1394 | +0.37 |

| m | n | crit on S | achieved level | power @2x | power @3x | power @2x at an exact-0.05 cut | E[S] |
|---|---|---|---|---|---|---|---|
| 30 | 40 | 1 | 0.014 | **0.17** | 0.36 | 0.17 | 6.6 |
| 30 | 60 | 4 | 0.037 | **0.45** | 0.77 | 0.45 | 9.9 |
| 30 | 80 | 6 | 0.027 | **0.51** | 0.84 | 0.51 | 13.2 |
| 36 | 40 | 2 | 0.017 | **0.25** | 0.51 | 0.25 | 7.9 |
| 36 | 60 | 5 | 0.027 | **0.46** | 0.79 | 0.46 | 11.9 |
| 36 | 80 | 8 | 0.029 | **0.60** | 0.91 | 0.60 | 15.8 |
| 50 | 40 | 4 | 0.023 | **0.36** | 0.70 | 0.36 | 11.0 |
| 50 | 60 | 8 | 0.025 | **0.56** | 0.89 | 0.69 | 16.5 |
| **50** | **80** | 13 | 0.041 | **0.77** | 0.98 | 0.77 | 22.0 |

The (m=50, n=80) cell reproduces `results/power_deployed_vs_oracle.md` table B on
independent draws -- power @2x 0.77 against its 0.77, achieved level 0.041 against its 0.041 -- which is the check that this
grid is the same test and not a re-implementation of a different one.

The exact-0.05 column matters for reading the n rows honestly: the analytic null is
discrete, and at small n its achieved level falls well below alpha, so part of the
power drop is conservatism rather than lost information. Even at the best cut a
level-0.05 test could take on this DGP, n=40 reaches only 0.36 against 0.77 at n=80.

### The realised design is slightly weaker than the nominal one

The grid above assumes every target contributes 50 benign draws. The run has already
shown it will not: 2/11 targets returned a short arm and 1/11 returned NONE. A target with zero benign draws is dropped by
`exceedance_counts_randomized` (`if not bl: continue`) and again by `exceedance_test`
(`m > 0`), so the test's n is the number of targets with a benign arm, not 80. Using
the observed attrition to build an 80-target design (this uses feasibility rates, not
outcome values, so it is not a peek at the result):

| design at n=80 nominal | targets with a benign arm | sum of m_j | crit | level | power @2x |
|---|---|---|---|---|---|
| every target gets 50 | 80 | 4000 | 13 | 0.041 | **0.77** |
| observed attrition replayed to 80 | 73 | 3482 | 11 | 0.043 | **0.73** |

A real but second-order correction. It is worth knowing before the run finishes
rather than after, and it argues mildly for n=80 over anything smaller, since the
attrition eats into n before the statistic sees it.

## 5. Interim look at the 11 completed targets -- QUARANTINED

> **Do not re-choose the design on this section.** m=50 and n>=80 are pre-committed
> (critique_log 26a) and the decision rule is locked (critique_log 21, M1). It is
> reported for three legitimate purposes: to confirm the arms are behaving, to
> supply the attrition rate §4 needs, and because a recommendation to spend or not
> spend 25 GPU-h that refused to look at the 14% already spent would be worthless.
> The recommendation in §9 is argued on cost and power, and would be the same with
> the sign of every number below reversed.

| arm | role | attack move (mean) | benign-MAX (mean) | paired net | net sd | wins/losses/ties | one-sided sign p |
|---|---|---|---|---|---|---|---|
| nli | shared with the optimiser's objective -- confounded/permissive | +0.5796 | +0.3685 | +0.2112 | 0.2992 | 5/0/5 | 0.031 |
| exact | independent, strict (over-counts surface form) | +0.1924 | +0.2392 | -0.0468 | 0.1085 | 0/2/8 | 1.000 |
| judge | **the adjudicator** (validated 0.93) | +0.4533 | +0.4780 | -0.0247 | 0.6875 | 3/5/2 | 0.855 |

Exceedance test on the judge arm, n=10 usable: observed S = 103 against an expected 2.6 under H0. The p-value is
1.000, and per §3 no value of S could have produced a rejection at this n.

Two things follow, and only two:

1. **The arms are behaving as the design predicted.** The attack wins under the
   clusterer it was optimised against and does not win under the independent
   adjudicator. That is precisely the confound the null control exists to expose,
   and it means the machinery is measuring what it was built to measure.
2. **The remaining hours buy a power qualifier, not a direction.** The direction is
   already legible. What n=80 buys is the right to write *non-rejection at power
   0.77 against a 2x effect* instead of *we did not find one*. For a
   null result that qualifier IS the result; without it the case study is an anecdote.

On optional stopping: the usual hazard runs the other way (stop once significant),
and stopping early on a null makes the null weaker, never stronger -- so the
integrity risk here is small and the cost is interpretability. But if n is cut after
this section exists, the paper must say that an interim was seen and that n was cut
on compute grounds. That disclosure is cheap; discovering the omission in review is not.

## 6. The designs, costed

Unit: the measured targets, scaled by clusterings per target (2 + K + n_seeds),
which also carries the proposer retries since those scale with K. **expected** uses
the observed mix (1191 s/target, i.e. with the §1 attrition); **max** assumes
every target gets a full arm (1349 s). `to run` counts only targets not
already on disk. **Changing K invalidates the checkpoint**: `_ckpt_load` matches on
the whole cfg dict, K included (`null_control.py:338`), so any m other than 50
discards all 11 completed targets and restarts from zero.

| design | to run | GPU-h expected | GPU-h max | power @2x | what it can still claim | what it forfeits |
|---|---|---|---|---|---|---|
| **A. Finish as launched** — m=50, n=80 | 69 | **22.8** | 25.9 | 0.77 | the pre-registered exceedance verdict at full power; the prefix statistic at any m<=50 as a free companion; the benign arm the null-objective gate needs; the reframe-(b) seed-vs-benign question | nothing |
| B. m=30, n=80 — restart | 80 | **16.8** | 19.1 | 0.51 | the same verdict at two-thirds the power | the 11 completed targets; the prefix statistic above m=30; an interpretable non-rejection |
| C. m=36 (the pre-registered prefix budget), n=80 — restart | 80 | **19.7** | 22.3 | 0.60 | the exceedance verdict plus the prefix statistic at exactly its pre-registered m | the 11 completed targets; ~0.16 of power; and it buys nothing the m=50 arm does not already contain |
| D. m=50, n=60 | 49 | **16.2** | 18.4 | 0.56 | the same verdict with n disclosed as short of the pre-registered 80 | 0.22 of power; the n>=80 pre-commitment; a sixth of the gate's n |
| E. m=50, n=40 | 29 | **9.6** | 10.9 | 0.36 | a bracketed result — rejection is still arithmetically possible (§3), but a non-rejection carries little | 0.40 of power; n>=80; half the null-objective gate's n |
| F. Drop or subsample an arm | 69 | **22.8** | 25.9 | 0.77 | nothing — there is no arm to drop; see below | see below |
| G. Prefix-only, zero new GPU | 0 | **0.0** | 0.0 | n/a | the free budget curve (§2) and a descriptive paired net + sign test on n=11 | the exceedance test entirely (§3 floor); any power statement; the gate's benign arm; the reframe-(b) answer |

Read the two cost columns together: the *largest* saving any cheaper design offers is 6.0-6.8 GPU-h (B), and it
costs 0.26 of power. Design C is within a rounding error of simply finishing.

### F: there is no arm to drop

`_arms` generates ONE set of samples with `semantic_entropy(...)`, which *is* the NLI
arm; exact-match is a re-clustering of those same strings at zero GPU cost; the
embedding arm is already off (`--embedding_model ''`, disqualified at hard-negative
AUROC 0.51). The two bracket arms are by-products of a computation the judge arm
needs anyway. **The only arm that costs anything is the judge** -- 45 pairs x 2
orderings = 90 prompts per clustering, sub-batched at 6, so 15 `generate()` calls per
clustering and ~825 per target -- and the judge is the sole adjudicator.

Its share, from the fit in §1: a clustering costs 24.0 s, of which the sampling+NLI half is the ~2.8 s the token split in `null_objective_ablation_plan.md`
§6 attributes to an SE eval (10 x 48 new tokens). So the judge is roughly 88% of a
clustering and ~85% of the run. Dropping it deletes the answer; keeping it and
dropping the brackets saves nothing and costs the strict/permissive bounds.

Subsampling the judge is worse than it looks. Judging only some of the 50 benign
draws makes the benign-MAX a max over fewer draws, which biases the floor DOWNWARD
and inflates the attack's margin -- the same direction as the winner's curse that B2
introduced the budget-matched control to remove. critique_log 22 already rejected the
cheaper version of this idea (NLI pre-screening) for exactly that reason.

Levers that are engineering rather than statistics:

- **`--judge_batch_size 6` -> larger.** Pure throughput, zero statistical effect. The
  cap exists because ~90 prompts OOM a 16 GB card also holding Llama and DeBERTa
  (`judge.load_judge` docstring), but 6 -> 10 has not been probed at the current
  footprint. `scripts/probe_batched_judge.py` exists. This is the only free speed-up
  on the table and it is worth ten minutes before relaunching.
- **Single-ordering judge** (90 -> 45 prompts, ~2x). critique_log 22 permits it ONLY
  with a re-validation of hard-negative accuracy under that exact config, and the
  0.93 [0.90, 0.96] figure the paper cites once is the symmetric config. Not free,
  and not worth it to save ~12 GPU-h.

## 7. Is m=30 defensible on the corrected power figures?

**No, and the decisive reason is arithmetic, not discipline.**

The pre-registration chose m=50 over m=30 on ORACLE power, 0.84 vs 0.67. The
deployed analytic test delivers 0.77 vs 0.51 here (`results/power_deployed_vs_oracle.md`: 0.77 / 0.51). Both arms lost about the
same amount, so the ordering that drove the choice is untouched -- m=30 is simply
worse than it looked, in absolute terms.

**On the pre-registration question.** Re-costing an as-yet-unrun design against
corrected power figures is a different act from re-choosing it: it consumes no
outcome data, and critique_log 26a explicitly contemplates it (*if compute forces a
smaller m, the shortfall is REPORTED as such*). So the audit is legitimate. Acting on
it today is not, for a reason that has nothing to do with power: §5 above has now
looked at 11 targets, so a switch to m=30 could no longer be cleanly defended as
compute-forced even if it were. The window for a clean m change closed when the
interim was read.

**And it would not be worth taking anyway:**

- finish at m=50: **22.8-25.9 GPU-h**, power 0.77
- restart at m=30: **16.8-19.1 GPU-h**, power 0.51
- restart at m=36: **19.7-22.3 GPU-h**, power 0.60
- net saving at m=30: **6.0-6.8 GPU-h** -- under one night -- for 0.26 of power. At m=36 the saving is 3.1-3.5 GPU-h for 0.17 of power, which is close to paying full price for a worse design.

The restart is what kills it: K is part of the checkpoint key, so m=30 pays for 80
fresh targets to avoid 69. At power 0.51 against a 2x effect a non-rejection is close to
uninterpretable -- barely better than a coin flip at seeing the effect it is being
read as absent -- and a non-rejection is the outcome this design is most likely to
produce.

## 8. Cutting n is the only lever with a real price ratio -- and it is still a bad buy

critique_log 22 rejected reducing n (*power is the binding constraint; n drives CI
width and is not recoverable by argument*), but that ruling was written for the
brute-force budget-matched design the exceedance test replaced in entry 23. On the
deployed test the trade is measurable rather than doctrinal:

| n | GPU-h from here at m=50 | nights at 10 h | power @2x | power @3x | achieved level | can the test reject at all? |
|---|---|---|---|---|---|---|
| 40 | 9.6-10.9 | 1.0-1.1 | 0.36 | 0.70 | 0.023 | yes (floor is n=13) |
| 60 | 16.2-18.4 | 1.6-1.8 | 0.56 | 0.89 | 0.025 | yes (floor is n=13) |
| 80 | 22.8-25.9 | 2.3-2.6 | 0.77 | 0.98 | 0.041 | yes (floor is n=13) |

Each 20 targets costs about half a night and buys about 0.2 of power. Three further
costs do not show up in that table:

- The null-objective ablation consumes this benign arm via
  `--benign_from results/diag_defb.json`. Its resolving power is *already* only *no
  gross violation at n=80* (`null_objective_ablation_plan.md` §5 computes that 3 sd on
  the lower band edge would need n~165). Halving n halves the gate's n too.
- The attrition in §4 eats n before the statistic sees it: nominal 80 is an effective
  73 on the observed rate, so n=40 nominal is more like 36 effective.
- n>=80 is the pre-registered decision rule (critique_log 21 M1, 26a). Cutting it is a
  disclosable deviation, and it would be the fifth.

## 9. Recommendation

**Finish design A. It is 23-26 GPU-h, not 60 -- 2.3-2.6 nights at 10 h -- against 33 days to the arXiv date. Every cheaper design on the
table trades a large fraction of the power for well under a night, and the one that
matches the pre-registered prefix budget (m=36) costs almost exactly what finishing
costs while delivering 0.17 less power.**

Order of operations:

1. **Ten minutes on `--judge_batch_size` before relaunching.**
   `scripts/probe_batched_judge.py` at 6 vs 8 vs 10 with Llama and DeBERTa resident.
   The judge is ~80% of the run; a 20% throughput win is ~4 GPU-h, and it is the
   only saving on this page that costs nothing statistically. If it OOMs, stay at 6.
2. **Relaunch A and let it run.** It resumes from the checkpoint. At the measured
   rate a 10 h night finishes 26-30 targets, so the cell completes on the third night. That also reverses the
   reasoning in `scripts/overnight_2026_08_13.sh` (*~60 GPU-h left ... yields nothing
   by morning*): at the measured rate it yields a third of the cell by morning.

   **Pre-flight, and this one is a trap.** `ckpt_cfg` is
   `{K, n_seeds, embedding_model, embed_threshold, judge_model}` and `_ckpt_load`
   reuses a record only on an EXACT dict match, so if the `--dump_judge_detail` work
   now in flight adds a field to that dict, all 11 completed targets silently
   stop being reusable and the run restarts from zero -- 3.6 GPU-h thrown away, with
   no error, just a `[ckpt] ... 0 reusable target(s)` line. Check that line on
   relaunch: it must say 11. Relatedly, the 11 existing records cannot contain
   per-pair judge detail that did not exist when they were written, so any detail
   dump will cover 69 targets, not 80, unless those 11 are deliberately recomputed.
3. **Compute the prefix statistic on the same data when it lands.** It is free, it is
   pre-registered (entry 22, m=36), it needs no exchangeability assumption, and it is
   the pre-committed fallback if the null-objective gate fails. Run it whatever the
   gate says -- an assumption-free companion to an assumption-dependent headline is
   worth having when the assumption is load-bearing for 92% of the tie multiplicity.
4. **Then the ~4 GPU-h null-objective ablation**, in the order its own plan specifies
   (after the null control, using `--benign_from results/diag_defb.json`).

What to skip:

- **Any change to m.** The best case saves under one night and costs a third of the
  power; at m=36 the saving nearly vanishes once the restart is priced. And the
  clean window for changing m closed when the interim was read (§7).
- **Any change to n.** ~0.2 of power per half-night, and it damages the ablation gate
  and the pre-registration at the same time (§8).
- **Dropping or subsampling arms.** Three of the four are free; the fourth is the
  adjudicator; subsampling it biases the floor the wrong way (§6F).
- **Stopping at n=11 and leaning on the prefix statistic alone.** It is the right
  companion and the wrong headline: at n=11 the exceedance test is arithmetically
  incapable of rejecting (§3), and a non-rejection with no power statement is exactly
  the reviewer bait the null control was built to avoid.

**The honest counter-case**, since the spine of the paper is now the measurement
result and this decides a case study: if the queue's other jobs are genuinely more
valuable per hour, the defensible cut is to run the null control to n=80 *later* --
not smaller. 25 GPU-h can be deferred inside a 33-day window; the power a smaller n
throws away cannot be recovered without paying for it twice.

