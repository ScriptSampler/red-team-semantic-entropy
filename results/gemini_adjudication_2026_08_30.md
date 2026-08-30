# Adjudication: internal panel vs. Gemini 3.1 Pro

**Date:** 2026-08-30
**Inputs:** `results/heavy_review_2026_08_30.md` (23-agent internal panel, ten lenses, defence
round); Gemini 3.1 Pro cold review of `paper/main.pdf` + referee brief; four adjudicator
re-derivations.
**Standing rule applied throughout:** neither reviewer has authority. Gemini saw only the PDF
and could not read source. The panel could read source but shares one model's priors. A claim
from either is a claim until re-derived. Every number below was recomputed for this ruling from
raw data with an independent implementation; where my numbers differ from an adjudicator's, mine
are reported and the difference explained.

**What I ran.** CPU only, no GPU, no edits to the paper, no commits. Sources:
`results/null_control_ckpt_defb.jsonl` (80 rows),
`data/cache/attacks/wk9_defb_snap/triviaqa_se_false_alarm.jsonl` (80 rows),
`src/se/attacks/optimizer.py`, `src/se/attacks/feasibility.py`, `paper/sections/*.tex`,
`results/achievable_fpr_grid.md`. I re-implemented the randomised-tie exceedance test from the
paper's own description rather than importing `src/se/stats.py`.

---

## 1. What the two reviews agreed on, and what that agreement is worth

Both reviews independently concluded that the paper's headline — the measurement-validity
result about discrete semantic entropy: the `log N` ceiling, the 39-value lattice at N=10,
the ceiling atom, and the achievable-FPR floor that follows from it — is sound. Gemini's word
was "exceptionally sound, highly rigorous, and absolutely postable". The panel refuted 13 of 22
material findings in its own defence round, and none of the nine survivors touches the identity
`floor = mass of the ceiling atom` or the arithmetic beneath it.

**This convergence is worth more than either verdict on its own, and it is the strongest evidence
this project has produced about its own correctness.** The reason is that the two reviews have
close to disjoint failure modes:

- Gemini read the artifact a referee will read — the PDF — with no access to source, no access to
  the checkpoints, and no knowledge of the project's history, its retracted claims, or the panel's
  findings. It could not be led by the repository's own framing. What it validated is that the
  headline *survives being read cold, by a different model family, from the paper alone*.
- The panel read source and raw data and re-derived. It could be led by the repository's framing —
  it shares the author's model — but it could check arithmetic Gemini could not see.

An error surviving both would have to be simultaneously invisible in the PDF's presentation and
absent from the code and data. The classes of error each review is individually blind to are
largely complementary, so the intersection is genuinely small.

**Three limits on what the agreement licenses, stated so it is not over-read.**

1. It is agreement on the *headline*, not on the paper. The disagreements below are real, and one
   of them (Section 2) changes a number the paper prints in four places.
2. Gemini and the panel are both language models. Correlated blind spots between them are
   plausible and unmeasured — both were more alert to statistical framing than to provenance and
   reproducibility, and neither re-ran a GPU experiment.
3. The agreement is about internal validity. Neither review can speak to whether the floor
   transfers to another model, another quantisation, or another corpus. Section 5 records that as
   still unchecked.

The correct summary: **the measurement-validity headline is the most independently corroborated
claim in the paper, and it should be the claim the paper leads with.** That last clause becomes a
recommendation in Section 6.

---

## 2. The disagreement, settled: A = 181

**Verdict: the panel is right. Gemini's endorsement of A = 181 does not survive. They were not
answering different questions — they were answering the same question, and Gemini got it wrong
for a reason that is structural, not careless.**

Gemini could not read `src/se/attacks/optimizer.py`. From the PDF alone the paper's definition of
A is internally coherent: "the number of scored evaluations the maximum ranges over", 181 = 180 +
1. Nothing visible in the PDF contradicts it. Gemini endorsed a definition, and the definition is
fine. What is wrong is the *value*, and the value is only falsifiable from source. This is a clean
instance of the access asymmetry, not of reviewer quality.

### 2.1 The structural claim, verified from source

`src/se/attacks/optimizer.py`, the feasibility loop:

```
improved_children = [c for c in children if c.obj >= best_obj]     # line 124
...
    if fr.feasible:                                                 # line 133
        feasible_candidates.append(c)
        feasible_objs.append(float(c.obj))
        if c.obj >= best_obj:                                       # line 142
            best_obj = c.obj
            best_query = c.query
```

The `best_obj` / `best_query` update is nested inside `if fr.feasible:`. An infeasible candidate
can never become the reported value. The file's own `AttackResult` docstring concedes it at line
55: `best_is_feasible` is "True BY CONSTRUCTION". The maximum therefore ranges over the *feasible*
subset, not over 181 scored evaluations.

### 2.2 Verified on all 80 targets

| check | result |
|---|---|
| `n_objective_calls` | exactly 181 on every target (min = max = 181) |
| `entropy_after == max(feasible_objs)` | 0 mismatches on all 69 targets with feasible candidates; **worst absolute difference exactly 0.0** (bit-identical, not 1e-12) |
| the other 11 targets | `entropy_after == entropy_before` exactly (no-ops) |
| `len(feasible_objs) == n_feasibility_passed` | true on all 80 |
| pooled gate pass rate | **3058 / 4703 = 0.6502** |

The panel's 0.650 reproduces to four figures.

### 2.3 The part both reviews got wrong, and it matters more than the part they disagreed about

The gate is applied **lazily**. Only candidates clearing the `c.obj >= best_obj` pre-filter at
line 124 are ever submitted to it. **Only 4703 of 14,400 scored children (32.7%) were
feasibility-checked at all.** The observed feasible count per target is median 29.5, mean 38.2,
max 131.

A is therefore **not point-identified from the recorded artifacts**. I checked whether the ungated
candidate strings are recoverable so this could be settled on CPU: they are not. `feasible_objs`
stores floats; only `best_query` survives as a string.

Two corrections to the record, in opposite directions:

- **Against the adjudicator.** The claim that this is "a finding neither reviewer reported" is
  **wrong**. The panel reported it, in Section 7.1 of its own report ("The optimiser gates lazily:
  only 4703 of 14 480 candidates were ever feasibility-checked"). It did not fold it into F3's
  headline, which is a presentation failure, not a miss.
- **Against the panel.** The panel's Section 7.1 states "the true A therefore lies somewhere in
  [118, 181]". **The lower bound is wrong.** 118 is the extrapolated point estimate, not a floor.
  The hard lower bound is the case where no never-gated candidate would have passed, giving mean
  A ~ 41. The panel's stated range excludes exactly the region where its own conclusion changes.

### 2.4 My own transcription of the test, and why the verdict survives anyway

I re-implemented the exceedance test from the paper's description: `K_j ~ BetaBinomial(m_j; 1, A)`,
randomised tie credit at `1/(b_j+1)` with `b_j = max(1, n_feasible_at_best)`, p by exact
convolution over targets. It recovers the paper's design constants exactly: n = 77, sum of m_j =
3704, 71 targets at m = 50, the remaining six at m in {1, 26, 27, 27, 35, 38} — matching
`methods.tex:395-403` — and E[S] = 3704/182 = 20.35 at A = 181. My tie-break RNG stream differs
from the shipped one, so my seed-0 draw is not the paper's; but my minimum p over 101 draws at
A = 181 is **0.2291**, reproducing Table 1's published range floor of 0.229 to four decimals. The
implementation is the paper's.

Median p over 101 tie draws, as a function of scalar A:

| A | NLI p_med | NLI p_min | draws <= 0.05 | **judge p_med** |
|---|---|---|---|---|
| 181 (as shipped) | 0.9154 | 0.2291 | 0/101 | **1.0000** |
| 164 | 0.8288 | 0.1302 | 0/101 | **1.0000** |
| 140 | 0.5997 | 0.0395 | 1/101 | **1.0000** |
| 121 (approx. panel's 118) | 0.3426 | 0.0093 | 1/101 | **1.0000** |
| 110 | 0.1996 | 0.0030 | 18/101 | **1.0000** |
| 102 | 0.1163 | 0.0011 | 27/101 | **1.0000** |
| 95 | 0.0634 | 0.0004 | 43/101 | **1.0000** |
| **90** | **0.0373** | 0.0002 | 52/101 | **1.0000** |
| 80 | 0.0095 | 0.0000 | 79/101 | **1.0000** |
| 60 | 0.0001 | 0.0000 | 101/101 | **1.0000** |
| 41 (hard lower bound) | 0.0000 | 0.0000 | 101/101 | **1.0000** |

The NLI arm's median p crosses the 5% cut at A ~ 92-93. (The adjudicator's per-target A_j
parameterisation puts the crossing at A ~ 89-90; the gap is scalar-A vs per-target-A_j, and is
immaterial.)

**The consequence, stated precisely.** The panel wrote that "the verdict survives: the median p
does not approach 0.05 anywhere in the plausible range". That is true only under the panel's own
too-narrow [118, 181]. The defensible statement is different, and stronger:

> The NLI arm's p-value is **not identified**. Across the admissible range of A it runs from
> <0.001 to 0.92 and crosses the 5% cut at A ~ 92. The non-rejection headline survives **because
> the pre-registered adjudicator arm is invariant**: the judge's median p is 1.000 at every A from
> 41 to 181, and so is the exact-match arm's.

That is a better defence than the one the paper currently has, and it is the one the paper should
make. The headline does not depend on A at all in the arm that was pre-registered to carry it.

---

## 3. Gemini's two findings, ruled

### 3.1 Finding 1 — the exact-match "strict lower bound" bracket. **HOLDS.**

**The passage.** `paper/sections/methods.tex:336-338`: "We report the attack's net effect under
each as a bracket, with the shared-NLI arm as the confounded upper bound and exact-match as a
strict lower bound."

**Scope, settled against the paper.** A defence could argue the bracketed object is the raw
intended move, for which the bracket is true. Three facts defeat it:

1. **"net effect" occurs exactly once in the paper** — in this sentence. The paper's term of art
   for the raw quantity is "intended move" (Table 1: "Bands: mean intended move (nats)"). Every
   other occurrence of "net" denotes attack minus a benign comparator (`experiments.tex:135, 211,
   313, 334, 391, 397, 411`). The paper had a word for the raw move and did not use it here.
2. **The labels are Table 1 column headers** (`experiments.tex:113-114`: "& (confounded UB) &
   (strict LB) & (adjudicator)"). A column header is scoped to its column, and the column spans
   all four blocks — bands, exceedance test, saturation, and the supplementary paired net.
3. **The pre-registered decision rule makes the bracket the deliverable on the branch actually
   taken.** `experiments.tex:244-246`: "If the test does not reject, (a) is not claimed, and the
   NLI/exact-match bracket together with the judge's point estimate is reported as the honest
   **bounded** result. That is the branch the run took."

**Re-derivation.** All quantities recomputed by me from `results/null_control_ckpt_defb.jsonl`.
n = 80 for bands; n = 77 for benign-referenced rows (`qb_565`, `qz_3393`, `qb_2689` have empty
benign arms).

```
raw attack move (n=80):    NLI +0.5256   exact +0.2127   judge +0.2913
benign mean draw (n=77):   NLI -0.0491   exact +0.0021   judge -0.0710
benign best-of-m (n=77):   NLI +0.3626   exact +0.2133   judge +0.4215
```

Does the judge lie inside [exact, NLI]?

| quantity | status |
|---|---|
| raw attack move | **IN** (+0.2127 <= +0.2913 <= +0.5256) |
| net vs. mean benign draw | **IN** |
| benign best-of-m | **OUT**, above the "confounded upper bound" by 0.0589 |
| paired net vs. best-of-m, raw | **OUT** by 0.1265 (exact +0.0077, judge -0.1188) |
| paired net, convention (d) as shipped | **OUT** by 0.1460 (exact -0.0269, judge -0.1729) |
| attack's mid-rank percentile in benign | **OUT** by 0.0358 |
| effective benign budget n_eff | **OUT** |

The bracket holds on the intended move and **fails on every budget-controlled quantity** — which
is to say, on every quantity the paper draws a conclusion from. The Discussion's "the family does
not agree on a sign" paragraph (`discussion.tex:468-478`) is entirely about the three net
comparators, all of which sit outside the bracket.

**Why it fails, mechanically.** Exact-match is the strictest relation, so it splits the most, so
its clean baselines sit closest to the `log N` ceiling (clean saturation 46.2% exact vs 10.0% NLI
vs 1.2% judge, verified in M1 below). That saturation suppresses the benign best-of-m more than it
suppresses the attack's single unselected score. A lower bound on the attack's move together with
a lower bound on the benign comparator is **not** a lower bound on their difference. The bracket
does not survive differencing.

**Collateral damage.** `methods.tex:358-359` rests the independence argument on the bracket: "we
report the NLI and exact-match bracket *alongside* the judge so no conclusion rests on the
re-scoped oracle alone." That sentence fails on its own terms — the judge's conclusions are the
net rows, and they are not bounded by the bracket.

**Required change — `paper/sections/methods.tex:336-338`.** Replace with:

> "We report the attack's mean intended move under each as a bracket, with the shared-NLI arm as
> the confounded upper bound and exact-match as the saturation-limited lower bound. The bracket is
> a statement about the intended move only, and it does not survive differencing. Every
> budget-controlled quantity we report subtracts an arm-specific benign comparator, and a lower
> bound on the attack's move together with a lower bound on the benign comparator is not a lower
> bound on their difference. Exact-match is the strictest relation, so it splits the most, so its
> clean baselines sit closest to the log N ceiling; that same saturation suppresses the benign
> best-of-m by more than it suppresses the attack's single unselected score. The adjudicator
> therefore lies outside the bracket on the paired net, and we report where it does rather than
> let the column headers imply otherwise."

Four further sites: `experiments.tex:113-114` (column headers — restrict to the bands block or
re-word), `experiments.tex:82-85` (prose repetition), `experiments.tex:244-246` ("bounded result"
— the bound does not cover the reported quantity), `methods.tex:358-359` (independence argument).
Also **delete or discharge the "survival ratio" promise** at `methods.tex:337` and `:387`: it is
never reported.

### 3.2 Finding 2 — the prevalence arithmetic. **HOLDS.**

**The passage.** `paper/sections/discussion.tex:86-89` (PDF p. 20).

**Re-derivation.** From `results/achievable_fpr_grid.md:233` and the counts behind it, verified
arithmetically by me:

- Full labelled pool: 1424 correct / 576 hallucinating, n = 2000, prevalence 576/2000 = 28.80%.
  At tau = ln 10: k_fp = 150, k_tp = 145.
- alerts = 295/2000 -> 147.5 -> **"148"**
- precision = 145/295 = 49.1525% -> **"49.2%"**, Wilson **[43.5, 54.8]**
- missed = 431/2000 -> 215.5 -> **"216"**

**There is no arithmetic error.** All three integers are exact, mutually consistent counts on one
population. The rates producing them are FPR = 150/1424 = 10.53% and **TPR = 145/576 = 25.17%**.

**The defect is a population switch that the prose does not disclose.** The prevalence comes from
the pooled n = 2000; the *rates* come from the 1424-negative superset and its 576-positive
complement; but the section has just spent two paragraphs establishing the **fair pool's** rates
(FPR 9.5%, TPR 27.5% on 200 + 200). The sentence labels only the prevalence ("the full labelled
pool's natural hallucination rate"), never the rates.

**Confirmed reader failure.** A reader carrying the fair pool's rates forward computes prevalence
= 0.216/(1 - 0.275) = 29.79%, alerts = 148.63, precision = **55.1%** — **outside the quoted
[43.5, 54.8]**. I reproduce Gemini's 55.1% exactly. One correction to Gemini: that route gives
148.6 alerts, which rounds to **149, not 148** — so even the number Gemini conceded reconciles is
off by one under its own route. The other natural route (stated 28.8% prevalence with fair-pool
rates) gives 147 / 53.9% / 209 — a third distinct triple, and 209 vs 216 is a visible miss.

**The disclosure fails on the decisive half.** I grepped all seven section files and `main.tex`:
`25.2` — **0 hits**. `28.8` — **0 hits**. `576` — **0 hits**. The TPR and the prevalence that
generate the 49.2% appear **nowhere in the paper**. The FPR half is one paragraph away
(`discussion.tex:71-72` prints 10.5% [9.0, 12.2]); the TPR half is unreachable. Note that the
project's own working file `results/achievable_fpr_grid.md:233` **does** print the TPR column
(25.2%) — the paper dropped the one number a reader needs.

*(Minor but worth fixing: both reported integers are exact half-integers, 147.5 and 215.5,
resolved to 148 and 216 only because `"%.0f"` banker's rounding happened to land upward twice.
Fragile rendering, not an error.)*

**Required change — `paper/sections/discussion.tex:86-89`.** Prose only; every number stays.
Replace with:

> "Prevalence changes the consequences of a chosen operating point but not the grid, which is a
> within-negatives object and so does not move when the mix of correct and hallucinating questions
> does. What does move is the rest of the arithmetic, so we state the operator's experience on the
> full labelled pool throughout: its own floor of 10.5% [9.0, 12.2] on 1424 correct answers, its
> own true-positive rate of 25.2% [21.8, 28.9] on the 576 hallucinating ones at the same
> threshold, and its natural hallucination rate of 28.8% (576/2000). The fair pool cannot supply
> this row: it is 50% hallucinating by construction and has no natural prevalence. Running at the
> lowest firing threshold then raises 148 alerts per thousand questions (295 of 2000), of which
> 49.2% [43.5, 54.8] are genuine (145/295), and leaves 216 hallucinations per thousand unflagged
> (431 of 2000)."

In descending order of importance the sentence must carry: **(1) TPR 25.2% [21.8, 28.9] = 145/576**
— the load-bearing omission, without which 49.2% is unreachable from anything the paper prints;
(2) the prevalence 28.8% (576/2000) as a stated value; (3) the explicit note that the fair pool
cannot supply this row.

---

## 4. Prioritised fix list

### 4.1 MUST FIX BEFORE POSTING — visible to a referee reading the PDF alone

| # | Item | File |
|---|---|---|
| M1 | **The floor's oracle-dependence is never scoped.** Table 1 prints the same estimand three times on the same 80 targets with only the equivalence relation varying: clean saturation **46.2% (exact) / 10.0% (NLI) / 1.2% (judge)** — verified by me as 37/80, 8/80, 1/80. Wilson: exact [35.7, 57.1] vs NLI [5.2, 18.5], **non-overlapping**. The floor claim is printed unqualified in five places. `limitations.tex:205-208` calls it "a property of the model and the question distribution rather than of the estimator's arithmetic" — 60 lines after `limitations.tex:144-147` states the judge's clean baseline is 0.648 nats vs NLI's 1.477 and collapses 27/80 vs 4/80 (all four numbers verified). A referee meets both paragraphs in one sitting. **Scope every floor claim to the NLI clusterer.** Honest bound to respect: the judge figure is 1/80, Wilson [0.22%, 6.75%], which does *not* exclude 5% at n = 80 — so claim the oracle-dependence (which Table 1 proves), not "under the judge a 5% budget is feasible". | `main.tex` Abstract; `introduction.tex:90-97`; `discussion.tex:138-141`; `limitations.tex:205-208`; `conclusion.tex:13-19` |
| M2 | **A = 181 is an upper bound presented as a value** (Section 2). Redefine A as the number of *feasible* candidates the maximum ranges over; state that it is partially observed (4703 of 14,400 children gated, pooled pass 3058/4703 = 0.650); report 181 as an upper bound, the observed feasible count (median 30, mean 38) as a lower bound, A ~ 118 as the point estimate. Add a sensitivity row. **Lead the defence with the judge arm's invariance** (p_med = 1.000 at every A from 41 to 181). | `experiments.tex:155-157`; Table 1 block header |
| M3 | **Delete the three claims that do not survive M2:** "the observed exceedance total is *above* its null expectation in all three arms, which is the direction *against* the attack" (false for NLI at the measured feasible budget); Table 1's "0/101" and range "[0.229, 1.000]" presented as unconditional; "n_eff ~ 122 ... fewer than the budget it spent" (compares feasible paraphrases against scored evaluations). | `experiments.tex:281`; `introduction.tex:52-53`; `conclusion.tex:59-60` |
| M4 | **The exact-match bracket** (Section 3.1). Five sites. | `methods.tex:336-338, 358-359, 387`; `experiments.tex:82-85, 113-114, 244-246` |
| M5 | **The prevalence paragraph** (Section 3.2). Add TPR 25.2% [21.8, 28.9] = 145/576 and prevalence 28.8%. | `discussion.tex:86-89` |
| M6 | **Threshold-selection rule stated inverted.** "select tau as the *largest* threshold whose achieved clean FPR is at or below the stated budget" — FPR is non-increasing in tau, so the largest such tau is the never-firing one. The rule as written returns tau = infinity at every budget and would break the paper's own N=40 operating point. Code is correct (`src/se/stats.py:940` documents `at_most` as "smallest"). **One word: largest -> smallest.** | `methods.tex:314-316` |
| M7 | **Fidelity bound direction reversed.** Methods says the answer-flip subcategory "lower-bound[s] the fidelity of the NLI constraint"; `limitations.tex:163-167` correctly calls it a lower bound on *leakage*. A lower bound on leakage is an **upper** bound on fidelity. Limitations is right. | `methods.tex:318-320` |
| M8 | **"the same population yields 28 at n=200 and 35 at n=2000"** — those are two different populations (fair pool's correct stratum vs full labelled pool, correct *and* hallucinating). "The same population" is the phrase doing the argumentative work. | `introduction.tex:119` |
| M9 | **Methods says the hide cell is still filling; it completed 2026-08-13.** | `methods.tex:209-211` |
| M10 | **No Data and Code Availability statement, no licence, no repository URL, no commit hash** anywhere in the PDF. For a paper whose entire contribution is measurement validity, this is among the first things a referee checks. | `main.tex` (new paragraph) |

### 4.2 SHOULD FIX — real, but only visible from the artifact

| # | Item | File |
|---|---|---|
| S1 | **The exact-match arm's rejection region is empty**, so its p = 1.000 corroborates nothing. Exact-match benign draws are pinned at ln 10 on 1461/3704 = 39.4% of draws; the rejection cut is S <= 11 against E[S] = 20.35; under an attack pinned at the ceiling on every target at the measured b_j, exact-match E[S] = 150.1, sd 10.0, minimum over 20,000 sims = 110 — never reaching 11. Power against ceiling saturation: 0.56 (NLI) / **0.00 (exact)** / 1.00 (judge). The paper reports the exact-match p beside the others as though it were independent corroboration. Say that it cannot reject. *(The reader can derive the cut from the PDF — `methods.tex:395-403` prints the full m_j vector and `experiments.tex:145-160` the null — but the power calculation needs the artifact.)* | `experiments.tex` Table 1 + surrounding prose |
| S2 | Per-target A_j rather than a scalar A. The three empty benign arms prove the gate rate varies enormously across targets. | `experiments.tex` |
| S3 | Half-integer rounding in the prevalence row (147.5, 215.5) is fragile. Print the counts. | `discussion.tex:86-89` |

### 4.3 REPOSITORY WORK

| # | Item | File |
|---|---|---|
| R1 | Un-ignore and commit the five load-bearing artifacts: `results/null_control_ckpt_defb.jsonl`, `results/diag_defb.json`, `results/n_scaling_ckpt.jsonl`, `results/winners_curse_ckpt_se_false_alarm_defb.jsonl`, `data/cache/attacks/wk9_defb_snap/` (with `SNAPSHOT.txt`). A few MB. | `.gitignore:47, 48, 102` |
| R2 | Ship the Week-4 sample cache (`relabeled.jsonl`, `entropy.jsonl`, ~0.9 MB) or a release asset. **Every N=10 headline number is currently computable only from `~/.cache/se-research/samples/wk4_full_2000q/`, outside the repository tree.** Without this the headline is checkable by nobody. | new |
| R3 | Replace hard-coded `\\wsl.localhost` / `/home/abhi` paths with the `resolve_labels()` pattern (`--labels` flag + `SE_RELABELED_JSONL` env var) that `achievable_fpr_grid.py` already implements. At least ten scripts encode the author's username. | ~10 scripts |
| R4 | `scripts/winners_curse_reeval.py`: default tag `_def` -> `_defb`; fix docstring usage lines; mark or delete `_def`. The repo ships the superseded winner's-curse checkpoint and gitignores the definitive one. | `scripts/winners_curse_reeval.py:24, 28, 387` |
| R5 | Add SUPERSEDED banners to `results/wk6_hide_attack.md` and `results/wk7_false_alarm.md` — the two pre-B1 files still reporting the retracted 9/10 false-alarm result unqualified. | those two files |
| R6 | **Rewrite `README.md`.** It calls the false-alarm attack "the headline", says a perturbation fooling both detectors "is evidence against the *paradigm*", gives the deadline as 15 September 2026, and stops at Week 3. This is the framing the paper retracted. | `README.md` |
| R7 | Add a `LICENSE`. | repo root |
| R8 | Refresh `data/cache/attacks/wk9_defb_snap/` so its hide file carries the complete 80 records, or note in `SNAPSHOT.txt` that the cell has since completed — otherwise the repo copy corroborates M9's false statement. | snapshot |

---

## 5. What still has no independent check

Stated plainly, because the convergence in Section 1 is easy to over-read.

1. **Neither reviewer ran an experiment from scratch.** Both re-derived from checkpoints the
   original pipeline produced. If a bug lives upstream of `null_control_ckpt_defb.jsonl` — in
   sampling, in clustering, in the judge's invocation — every re-derivation in both reviews
   inherits it. Nothing here is a replication.
2. **A is not identified and cannot be identified from what was recorded.** The ungated candidate
   strings are not persisted anywhere. Settling it requires either re-instrumenting the optimiser
   to record feasibility on every candidate, or running a few hundred ungated feasibility checks —
   CPU-only NLI work — which cannot be done from the current artifacts.
3. **The judge-oracle floor on the 1424 is unmeasured.** M1 rests on 80 targets; the judge's clean
   at-cap rate is 1/80, Wilson [0.22%, 6.75%], straddling the 5% line. Settling it means
   re-clustering the cached Week-4 samples for the 1424 correct answers under the judge — judge
   inference only, no generation, but GPU and not free.
4. **The judge's validation on messy real sample pairs remains owed.** The paper says so itself.
   Validation is on clean gold-alias pairs; the deployed behaviour on sampled answers is the
   opposite (under-splits rather than over-splits). Neither review closed this.
5. **Correlated blind spots between the two reviewers are unmeasured.** Both are language models.
   The panel is the same model family as the author's tooling. Gemini is a different family but
   still an LLM, still trained on overlapping literature. The complementarity argued in Section 1
   is plausible and untested.
6. **No human referee has read the paper.** Every finding in both reviews and in this ruling is
   machine-generated.
7. **External validity is entirely unchecked.** One model family, one quantisation, one dataset.
   Neither review can speak to transfer, and the paper's own Limitations says so.

---

## 6. Gemini's closing question, and what it means

Gemini closed by asking the author:

> "What led you to investigate the discrete lattice bounds as the primary constraint rather than
> just focusing on the clustering model's weaknesses?"

**Take this as the most valuable line in Gemini's review.** It is not a request for information —
it is a referee reporting that the Introduction's pivot did not land. A referee who finishes a
34-page paper still asking *why is this paper framed this way* has not been given the paper's
spine.

**Does the paper tell the story?** Partly, and then it takes it back.

- **The Abstract tells it, in one sentence, correctly:** "We tried to break it with
  meaning-preserving paraphrases and found the binding constraint falls on the operator, not the
  attacker." That is exactly the provenance — the lattice result emerged *from* trying to measure
  the attack honestly.
- **The Introduction then contradicts it.** Lines 1-68 are entirely attack framing, ending on "The
  question we ask is therefore whether an attacker who only rephrases the question... can move a
  sampling-based detector's score." The measurement-validity result does not appear until
  `\paragraph{Contributions.}` at line 70 — and contribution (1) opens: "A measurement-validity
  result about *discrete* semantic entropy, **independent of whether any attack succeeds**."

That clause is the problem. It is *logically* true and *narratively* fatal. It asserts that the
headline has nothing to do with the attack, which severs the very causal link the Abstract just
established. A reader who takes it at face value is left with two unrelated papers stapled
together and no account of why either is here — precisely the state Gemini's question reports
being in.

**Assessment: yes, the paper should tell the story, and it nearly does.** The fix is not to add a
narrative; it is to **stop denying the one the Abstract already asserts.** Concretely:

1. **`introduction.tex:71`** — change "independent of whether any attack succeeds" to something
   that preserves the logical point without severing the provenance: e.g. "which the attack
   investigation uncovered and which stands whether or not any attack succeeds." Same logical
   content, opposite narrative effect.
2. **Add one bridging sentence before `\paragraph{Contributions.}`**, carrying the Abstract's
   sentence into the Introduction: the controls in (i)-(iii) were built to measure the attack
   honestly; building them is what surfaced the ceiling atom, because a null that must stay valid
   under ties at the cap forces you to characterise the cap; and characterising the cap is the
   measurement-validity result. The material already exists at `introduction.tex:130-133`
   ("false-alarm effects are *right-censored* on just over half of attacked targets, so
   native-unit effect sizes understate them and any null must stay valid under ties at the cap") —
   it is simply 60 lines too late and framed as a related-work observation rather than as the
   paper's own origin.
3. **Consider moving the pivot earlier.** Sixty-eight lines of attack setup before the headline
   appears is a long time for a referee to hold the wrong prior about what they are reading.

This costs a sentence and a clause. Given that the measurement-validity headline is the paper's
most independently corroborated claim (Section 1), it is worth paying.

---

## 7. Ruling summary

| Question | Ruling |
|---|---|
| Measurement-validity headline | **Sound.** Both reviews agree; convergence between reviewers with near-disjoint access is the strongest correctness evidence the project has. |
| A = 181 | **Panel right, Gemini wrong.** Not a difference of question — an access asymmetry. A is an upper bound and is not identified. |
| Panel's [118, 181] range | **Also wrong.** Hard lower bound is ~41. The panel's range excludes where its own conclusion flips. |
| Why the headline survives anyway | **Judge-arm invariance**, p_med = 1.000 at every A in [41, 181]. Verified independently. |
| Gemini Finding 1 (bracket) | **HOLDS.** Bracket is true of the intended move, false of every quantity the paper concludes from. |
| Gemini Finding 2 (prevalence) | **HOLDS.** No arithmetic error; undisclosed population switch. TPR 25.2% and prevalence 28.8% appear nowhere in the paper. |
| Gemini's closing question | **A framing defect, not a question.** The Abstract tells the story; `introduction.tex:71` takes it back. |

**Not posting-ready.** Ten must-fix items, of which M1, M2/M3 and M10 are the ones a referee will
find first. All are prose or scoping changes plus one repository release; **no new experiment is
required for any of them.**
