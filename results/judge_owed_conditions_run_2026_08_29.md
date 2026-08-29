# Run log and interpretation: `scripts/judge_owed_conditions.py`, 2026-08-29

Owner of this file: the 2026-08-29 run task. It does **not** modify
`results/judge_owed_conditions.md` (the 2026-08-13 prose report) or any script. Where the two
disagree, the disagreement is stated here and the older file is left alone.

**No GPU was used.** Safety of the script was verified before running, not assumed: its only
imports are `argparse, json, math, os, random, statistics, collections, itertools, pathlib`
(lines 47-57). There is no `torch`, no `transformers`, no model load, no `subprocess`, no
network call, and the only file access is a read-mode `open()` at line 317. Wall time 0.90 s,
0.79 s user. The follow-up analyses in sections 5-7 are the same: stdlib, read-only, ~7 s total.

Command:

```
./.venv-wsl/bin/python scripts/judge_owed_conditions.py --cache ~/.cache/se-research/samples \
    --out /tmp/joc_run_20260829.txt
```

---

## 0. Verification status of every number used below

| claim | status |
|---|---|
| script is CPU/stdlib only | **verified** by reading imports + running |
| N=10 lattice: 42 partitions -> 39 entropies, 3 coincidences, each ambiguous by 1 | **re-derived independently** |
| inverter: 2000 records, 0 mismatch, 0 off-lattice | **re-derived independently**, plus an extra check the script does not do |
| (iii)-preliminary NLI paired dK | **re-derived independently**, incl. tie-break sensitivity |
| (ii) pair inventory and NLI false-split rate | reproduced from the run; not independently recomputed |
| judge-side numbers in sections 5-7 | **newly computed here** from `results/null_control_ckpt_defb.jsonl` (read-only) |
| judge accuracy 0.650 / 1.000 / 0.930 (`judge_validation.md`) | **taken on trust** — no source data on disk to recheck |
| cost-model anchors 55 s and 6.1 s per evaluation (`critique_log` 22) | **taken on trust**; the script itself labels the bracket a model, not a measurement |
| the span oracle's own error rate behind `samples_correct` | **unverifiable here** by construction; it is the human half of (ii) |

---

## 1. A/B — the lattice and the inverter (verified, no correction needed)

p(10) = **42** partitions map to **39** distinct entropies. Three coincidences, each ambiguous
by exactly one cluster:

- `H=1.088899975`: (6,2,1,1) vs (4,3,3) -> K in {3,4}
- `H=1.609437912`: (4,2,1,1,1,1) vs (2,2,2,2,2) -> K in {5,6}
- `H=1.748067349`: (4,1,1,1,1,1,1) vs (2,2,2,2,1,1) -> K in {6,7}

Validation against `wk4_full_2000q/entropy.jsonl` (n=2000): exact **1748 (87.4%)**, ambiguous
but containing the truth **252 (12.6%)**, **mismatch 0**, off-lattice 0. I added a check the
script does not make — recomputing `H(assignments)` and `|set(assignments)|` from the stored
assignment vectors and comparing to the stored `entropy_nats` / `n_clusters`: **0 of 2000
inconsistent**. The inverter is sound.

**One defect found, cosmetic.** The `LATTICE_ROUND` comment (script line ~63) says the two
closest attainable values at N=10 differ by "~4.6e-03 nats". Measured, the smallest gap is
**2.900e-03 nats**. The conclusion is unaffected — 1e-9 rounding is still ~6 orders of
magnitude tighter than the gap — but the number in the comment is wrong.

**Tie-break sensitivity, which the script does not report.** `invert_cluster_count` returns a
sorted candidate list and section C takes `cands[0]`, i.e. the **minimum**. On the FA cell
that touches 6 of 80 targets and moves the headline by at most 0.075 clusters
(+2.288 -> +2.362 if the maximum is taken instead). The shipped choice is the conservative one
for the false-alarm direction. Not a problem; worth stating rather than leaving implicit.

---

## 2. C — the (iii)-preliminary under NLI (reproduced exactly)

`wk9_defb`, paired within target, benign K read exactly from cache on 80/80:

| cell | n | K benign -> attacked | paired dK [95% boot] | +/0/- | sign p | mean move |
|---|---|---|---|---|---|---|
| se_false_alarm | 80 | 6.01 -> 8.30 | **+2.288 [+1.788, +2.788]** | 55/23/2 | 2.3e-14 | +0.5256 nats |
| se_hide | 80 | 7.51 -> 4.60 | **-2.913 [-3.425, -2.413]** | 0/12/68 | 6.8e-21 | -0.6593 nats |

**The 2026-08-13 report's hide row is now stale.** It records n=59, 7.25 -> 4.81, dK -2.441.
The hide cell was still being appended to when that file was written; it is complete at 80 now.
The FA row is unchanged to three decimals. Whoever owns
`results/judge_owed_conditions.md` section 3 should refresh the hide row; I did not touch it.

---

## 3. D — condition (ii) inventory (reproduced)

90,000 real sampled pairs, mean 19.6 words, median 17, max 46; 99.0% longer than three words.
On the FA-80 targets: oracle-positive **76.3%**, oracle-hard-negative 17.6%, unlabelled 6.1% —
i.e. **93.9%** of FA-80 pairs carry a free label, better than the 74.5% pool-wide figure the
older report quotes. The NLI clusterer splits **0.664 [0.647, 0.682]** of the oracle-positive
FA-80 pairs. The machine half of (ii) is one GPU pass from closed.

---

## 4. E — cost (reproduced, and still a model)

n=80: 160 judge clusterings + 80 victim sampling passes. At `judge_batch_size=6`, 67 s per
clustering central -> **3.11 GPU-h, bracket 2.31-4.21**. At batch 12, 2.31 GPU-h. The script's
own docstring is right that this bracket is a model and not a measurement; it should be
replaced by timing ~20 clusterings the first time the device is free. See section 8 before
spending it.

---

# 5. The premise of section C is now false, and that changes the answer

Section C says, three times, that "the judge has never been run on the campaign" and therefore
reports NLI as a proxy for exposure. **That was true on 2026-08-13. It is no longer true.**
The definitive null control that finished at 03:57 today ran the judge on all 80 FA targets:
`results/null_control_ckpt_defb.jsonl` carries `cfg.judge_model =
"Qwen/Qwen2.5-7B-Instruct"`, a `baseline.judge` entropy and an `attack_move.judge` for every
row, plus a judge move for each of the 3,704 benign candidates.

For the false-alarm direction `_move` is `after - before` (`null_control.py:54`), so the
attacked-side judge entropy is recoverable as `baseline.judge + attack_move.judge`. Both ends
are on the N=10 lattice — **0/80 off-lattice at baseline, 0/80 attacked, 0/3704 across the
benign candidates** — so the script's own inverter yields judge-side cluster counts at zero
GPU cost. The measurement section C declares unavailable is available.

## 5.1 Paired cluster counts under the judge itself, n=80

Tie-break shown both ways because the attacked side needs inversion:

| clusterer | K benign -> attacked | paired dK [95% boot] | +/0/- | sign p |
|---|---|---|---|---|
| NLI | 5.88 -> 8.30 | +2.425 [+1.913, +2.950] | 55/24/1 | 1.6e-15 |
| **judge** | **3.10 -> 4.11** | **+1.012 [+0.487, +1.575]** | 36/30/14 | 2.6e-03 |
| **DiD (judge - NLI)** | | **-1.413 [-2.000, -0.825]** | 15/21/44 | 2.0e-04 |

(tie->max: judge +1.113 [+0.588, +1.675], DiD -1.250 [-1.837, -0.662]. Same sign, same
conclusion.)

On the nats scale over the same 80 targets: NLI move **+0.5256 [+0.4138, +0.6413]**, judge move
**+0.2913 [+0.1508, +0.4411]**, **DiD -0.2342 [-0.3895, -0.0793]**, sign p = 1.0e-02.

**Orientation, per the script's own `noninferiority_verdict` docstring: positive means the
judge splits relatively MORE on the attacked side = anti-conservative.** The measured value is
**negative with a CI that excludes zero**, and against the pre-registered margin of
0.20 x 0.5256 = 0.1051 nats the script's own rule returns **PASS**.

**Do not over-read that PASS.** This DiD is *not* `delta_bias` as designed in
`judge_owed_conditions.md` section 4.1. It compares two **different** clusterers, so the
genuine increase in answer diversity does not cancel; `delta_bias` compares H(J) against H(O)
within the *same* clusterer using the oracle force-merge, and that still needs the GPU run.
What the DiD does establish is a bound on the judge's *total* differential response, and it
points the conservative way.

Note also that `noninferiority_verdict` is defined at line 172 of the script and **never
called anywhere in `main()`**. That is not an oversight: it is the structural signature that
the estimand the verdict needs did not exist on disk when the script was written. It does now,
in the weaker DiD form above.

## 5.2 The premise is empirically wrong: the deployed judge is a merger, not a splitter

| | judge | NLI |
|---|---|---|
| mean benign K | **3.10** | 5.88 |
| median benign K | **2** | 6 |
| K=1 (all ten samples merged) | **27 / 80** | 4 / 80 |
| judge K < NLI K | **69 / 80** | — |
| judge K > NLI K | **1 / 80** | — |

Benign K distribution, judge: {1: 27, 2: 15, 3: 14, 4: 8, 5: 3, 6: 4, 8: 4, 9: 4, 10: 1}.
Benign K distribution, NLI: {1: 4, 2: 6, 3: 11, 4: 1, 5: 15, 6: 14, 7: 3, 8: 5, 9: 13, 10: 8}.

The 0.650 positive-recognition figure that drives the whole worry was measured on **clean gold
aliases**. On messy 20-word sampled answers the deployed judge's operating point is far more
permissive: it collapses a third of the benign targets to a single cluster. The scenario the
re-spec fears — "a judge with a 35% false-split rate would split MORE" in the high-diversity
attacked regime — is not what this judge does on this data.

## 5.3 The live risk is the mirror image, and the planned estimand is blind to it

27 of 80 FA targets (34%) have **judge baseline entropy exactly 0**. On those targets
`attack_move.judge` is structurally non-negative — measured minimum **+0.0000**, zero
negatives, 16 exact zeros. The judge arm's false-alarm effect is measured off a hard floor on a
third of the targets.

This is the same "bounded below by zero" defect that
`PREREG_noop_convention_2026_08_28.md` locked convention (d) to repair on the attack arm,
reappearing on the **judge's baseline**. Dropping the floored targets attenuates but does not
kill the effect: judge FA move **+0.2467 [+0.0718, +0.4288]** on the 53 non-floored targets vs
+0.2913 on all 80. Disclosure, not refutation — but it must be disclosed.

The mechanism is differential over-**merging** of the baseline, and section 4.1's `bias`
estimand states in its own scope note that it sees **split-side error only** and cannot see
false merges. **So the GPU run as currently designed would not settle the question this data
now raises.** The design should gain a merge-side estimand before 3.1 GPU-h is spent on it.

---

# 6. The judge arm of the null control is not usable as reported

This is the finding that bears hardest on the paper, and it is independent of everything above.

**The attack optimises the NLI objective only.** `harness.py:136` builds the objective through
`objectives.make_objective`, whose `_entropy_of` calls `semantic_entropy(...)`, i.e. the NLI
clusterer (`objectives.py:32-35`). `best_query` is therefore an NLI argmax over ~181
evaluations, and the judge score is read off that query **post hoc, unselected**.

**The benign arm is selected on the judge arm itself.** `_benign_moves_arms`
(`null_control.py:168-187`) builds a separate move list per arm from the same candidates, and
the paired net takes `max(benign["judge"])` — a **best-of-50 maximum on the judge arm**.

So the reported judge net compares an **unselected** attack observation against a **selected**
null. The size of that free selection is measurable: the judge arm's benign
`max-of-50 minus mean` is **+0.4925 nats**, the NLI-argmax candidate attains the judge maximum
on only **37 of 77** targets, and index-matching costs the benign arm **+0.2828 nats** of
premium on average.

Index-matching the comparator — take the benign candidate that maximises **NLI**, read **its**
judge move, so both sides are scored the same way:

| comparator (convention (d), seed 20260828, 20k boot) | n | judge net | +/0/- | sign p |
|---|---|---|---|---|
| arm-own max-of-50 (**as reported**) | 77 | **-0.1729 [-0.3032, -0.0391]** | 13/24/40 | 2.7e-04 |
| **index-matched to the NLI argmax** | 77 | **+0.0157 [-0.1146, +0.1505]** | 21/31/25 | 6.6e-01 |
| vs benign mean | 77 | +0.1750 [+0.0460, +0.3143] | 33/18/26 | 4.4e-01 |

**The significant negative judge result disappears under a matched comparator.** It is a
comparator artifact, not a finding. It is robust to the obvious challenges:

- dropping the 27 floored targets: -0.2384 -> **-0.0618 [-0.2242, +0.0982]**, CI includes zero;
- it is not the `max(0, .)` of convention (d) doing the work: index-matched under convention
  (a) gives **+0.1640 [+0.0297, +0.3020]**;
- the `exact` arm has the identical defect for the identical reason: -0.0269 -> +0.0180.

Note the family. This is the **same defect the null control exists to fix** — a maximum
compared against a differently-budgeted maximum — reappearing **per arm** rather than per
design. And unlike the July instance it runs *against* the attack, which is very likely why it
survived review: a gate looking for pro-attack bias would not flag it.

Residual caveat, stated so it is not later discovered: even index-matched, the attack searches
~181 NLI evaluations against the benign arm's 50, so the +0.0157 still carries a budget
advantage **toward** the attack. The honest reading is that the judge arm is **null**, not that
the attack wins on it.

---

# 7. The pre-registration's section-0 table is stale at n=80

Recomputed on all 80 checkpoint rows, seed 20260828, 20,000 resamples:

| convention | NLI | exact | judge |
|---|---|---|---|
| (a) as-is | +0.1835 [+0.1139, +0.2624] | +0.0077 [-0.0443, +0.0683] | -0.1188 [-0.2551, +0.0204] **incl. 0** |
| (b) neutralise no-ops | +0.1189 [+0.0662, +0.1780] | -0.0064 [-0.0433, +0.0349] | -0.1022 [-0.2301, +0.0278] **incl. 0** |
| (c) exclude no-ops (n=60) | +0.1526 [+0.0874, +0.2256] | -0.0082 [-0.0553, +0.0454] | -0.1311 [-0.2944, +0.0368] **incl. 0** |
| **(d) locked** | **+0.1097 [+0.0630, +0.1606]** | -0.0269 [-0.0644, +0.0138] | -0.1729 [-0.3032, -0.0391] excl. 0 |

At n=68 the pre-registration recorded (b), (c) **and** (d) excluding zero on the judge arm. At
the full n=80 **only (d) does**. The locked choice is unchanged and remains the least
favourable to the attack on every arm, so the pre-registration's own defence still holds — but
the table must be refreshed, and in light of section 6 the judge row should not be reported as
a substantive result at all.

**Data facts re-verified against the 80-row checkpoint** (all confirmed):

- 3 empty benign arms: **qb_565, qz_3393, qb_2689**.
- 6 partial arms: qz_1745 (26), qb_2833 (38), qb_6105 (**1**), qb_2922 (35), qz_4576 (27),
  dpql_250 (27).
- `benign["embed"]` length **0 on all 80**. The arm does not exist.
- `attack_move.nli` minimum exactly **+0.0000**, **0 negatives**, 20 exact zeros at n=80.
- `benign_max.nli` negative on **10 of 77**; `benign_max.judge` negative on 11 of 77.
- **The paired-net denominator is 77 of 80**, not the 65 of 68 the pre-registration states for
  its 68-target snapshot. Section 3 of that document needs its denominator restated.
- Benign `nli` and `judge` lists are the same length on all 80 rows, which is what makes the
  index-matching in section 6 valid.

---

# 8. The question that was asked: does the conservative reading hold?

**In its stated form the worry is refuted, and it took no GPU.** The judge does not amplify the
attacked side. Its response to the attack is *smaller* than the detector's own clusterer's, by
-0.23 nats / -1.41 clusters with a CI excluding zero on the anti-conservative side
(section 5.1).

**But the conservative reading does not hold for the reason `judge_validation.md` gives.** The
stated mechanism — over-splitting inflating the *baseline* — is not what the deployed judge
does on messy sampled answers. It under-splits, collapsing 34% of benign targets to K=1
(section 5.2). The conclusion survives; the argument for it does not. `methods.tex` (~305) and
`limitations.tex` (~72) need the sentence **rewritten**, not merely qualified with the
uniformity condition the 2026-08-13 report asked for.

**A new anti-conservative mechanism is now visible and is not covered by the planned check.**
A floored judge baseline on a third of the targets bounds the FA move below by zero there, and
section 4.1's `delta_bias` sees split-side error only, so it is blind to this by construction
(section 5.3). The 3.1 GPU-h run should not be launched against the current design.

**Can the judge arm's null-control result be used?** **No — not as it stands.** The
-0.17 judge net is an artifact of comparing an unselected attack observation against a
best-of-50 selection on the judge arm (section 6). Index-matched it is +0.02 with a CI spanning
zero and a sign test at p = 0.66. The judge arm should be reported as **null** — the attack
neither beats nor loses to a budget-matched benign search under the independent adjudicator —
or withheld pending recomputation. It must **not** be cited as evidence that the attack
underperforms the null, and the pre-registration's discussion of the judge arm should be
revisited on this basis.

**What still genuinely needs the GPU:** `delta_bias` proper, which requires judge cluster
*assignments* and the q' samples — both discarded — and the machine half of (ii). Cost
unchanged at ~3.1 GPU-h [2.3-4.2] at batch 6. Fix the estimand first.

---

## Appendix: reproduction

The three follow-up analyses in sections 5-7 are stdlib-only, read-only, and were run from WSL
against `results/null_control_ckpt_defb.jsonl` and the sample cache. Scratch copies:
`/tmp/verify_joc.py` (lattice + inverter + tie-break), `/tmp/judgearm.py` (conventions +
comparator), `/tmp/judgeK.py` (judge-side lattice inversion), `/tmp/floor.py` (floored baseline
+ robustness). Nothing in the repo was modified except this file.
