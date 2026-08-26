# START HERE — current state, 2026-08-26 20:40

**36 days to the 2026-10-01 arXiv target.** 27 citations resolve (27 cite keys, 27 bib
entries, exact bijection) — **[RE-DERIVED]** 2026-08-26 by parsing all 8 `.tex` files and
`paper/related_work.bib`: no cited key is missing from the bib and no bib entry is uncited.
The overnight record is `docs/critique_log.md` entry **38**.

At 20:31 the suite was **1035 pass / 17 skip / 2 fail** **[RE-DERIVED]** — a full
`.venv/Scripts/python.exe -m pytest -q` run on 2026-08-26. Both failures are the one unownable
site described in section 6. Re-run it before quoting it; the count is stable only while
nobody is editing.

> **SETTLED, 2026-08-26: the target is 2026-10-01.** The previous version of this section
> flagged the date as uncorroborated, and it was right to: `results/schedule_2026_08_26.md`
> asserted the move while `2026-10-01` appeared nowhere else in the repo, and no agent should
> adopt a deadline change on one untracked file's authority. **The user gave the instruction
> directly on 2026-08-26**, which is the corroboration that was missing; the countdown above,
> the memory index, and `results/schedule_2026_08_26.md` now agree. Older files still say
> 2026-09-15 and are left alone on purpose — they are timestamped analyses
> (`results/schedule_2026_08_19.md`, `judge_owed_conditions.md`, `null_objective_ablation_plan.md`,
> `latex_build_risk.md`), and rewriting a dated record to match today is how an audit trail
> stops being one. **This document is the live countdown; those are history.**
>
> One live site does still need fixing and is not history: `scripts/n_scaling_grid.py:996`
> emits a hard-coded countdown of the form *"NN days remain to the <date> target"* into
> `results/n_scaling_plan.md`,
> and the operational-provenance checker already flags it as a stale countdown. The repair is to
> stop hard-coding a countdown at all, not to change the date to the next one that will go stale.

**What changed between 2026-08-19 05:20 and this version, and why you should care.** The
previous version of this file carried the *withdrawn* interval for the measured N=40 floor
in three separate representations, and one of them was an INSTRUCTION telling the next agent
to move `scripts/derived_paper_quantities.py` toward the estimator that had been retired at
0.00% measured coverage. A stale number in a handoff misleads a reader once; a stale
instruction schedules the error. Section 2 now states the settled ruling, and the parts of
this document that described *another* file's contents have been re-read against that file
rather than carried forward.

This document does not claim to supersede anything. It claims to be true at the timestamp in
its title, and it dates every number so you can tell how far that claim has travelled. The
version before last opened with "Supersedes every earlier version" while being six days stale
in four separate places, and it had been handing out wrong methodological guidance the whole
time. An absolute claim of currency is exactly the sentence a stale document keeps making.

**The countdown line above is deliberately written in the shape that
`scripts/check_operational_provenance.py` checks.** When the suite starts reporting it as a
stale countdown, that is not the suite breaking — that is this document telling you it has
aged. Refresh it, or stop trusting it.

---

## 0. How to read the numbers in this file

Every figure below carries one of three marks. Nothing is unmarked.

| mark | meaning |
|---|---|
| **[LIVE]** | read out of a running artifact at the timestamp given. It will have moved by the time you read this; the artifact is named so you can re-read it. |
| **[RE-DERIVED]** | recomputed from first principles or from a primary artifact during this session, on 2026-08-19. Safe to quote with that date attached. |
| **[CARRIED]** | inherited from an earlier session and **not** re-verified here. The owning artifact is named. **Do not quote a [CARRIED] number into the paper without opening that artifact first.** |

The reason for the third category is the whole reason this file was rewritten. Tonight a
figure reached three separate briefings because it was printed under a heading that invited
lifting. A handoff document is the highest-leverage place in the repo to launder a dead
number, because it is read by someone who has no context yet.

---

## 1. The machine right now — read it, never assume it

**A GPU run is live, and it is a RESUME.** Verified from `ps` inside WSL at 2026-08-26 20:40,
not from any brief. The PIDs are new — the 2026-08-19 run was stopped by the user at 08:38
with 32 of 80 targets done, and this is the same job picking those 32 up from the checkpoint:

| PID | what | elapsed |
|---|---|---|
| 521 | `bash scripts/overnight_2026_08_14.sh` (wrapper) | 00:16 |
| 529 | `.venv-wsl/bin/python scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 --dump_diag results/diag_defb.json --checkpoint auto` | 00:17 |
| 387 | `bash scripts/stop_watcher_v2.sh` | 00:17 |
| 499 | `bash scripts/watcher_supervisor_v3.sh` | 00:17 |

The distro is `Ubuntu-24.04`. Always `wsl -d Ubuntu-24.04`, never `wsl -d Ubuntu`.

**Progress, from the checkpoint itself** — `results/null_control_ckpt_defb.jsonl`, counted as
distinct `question_id`, 0 torn lines:

- **[LIVE]** 32 of 80 false-alarm targets complete at 20:40; **48 remaining**. All 32 are
  carried over: the checkpoint's mtime is still 2026-08-19 08:18:38, so **nothing has been
  written since the resume at 20:23:41** and the first target of this session is still in
  flight.
- **[LIVE]** **no rate is measurable yet this session.** `dashboard/progress_status.json`
  reports `targets_timed: 0`, `sufficient: false` — it needs 2 completed targets to time an
  interval and has 0. Do not quote a rate off this session until it does.
- **[CARRIED]** the 2026-08-19 session ran at a mean of **1197 s/target** [MEASURED from
  checkpoint mtime deltas, the 20 sub-hour entries of `dashboard/progress_status.json`'s `gaps`
  block]. Its spread was **392 s/target** at the fastest [MEASURED, same block] and
  **1404 s/target** at the slowest [MEASURED, same block]. The block's 21st entry is 484,744 s
  and is the week-long stop, not a target. Every one is now labelled `resume gap` by the
  monitor, which is correct: they belong to a session that ended.
- **[MODELLED]** from the carried mean above: the 48 remaining targets are roughly **16 GPU-h**
  [MODELLED from the 1197 s/target mean above, measured on the 2026-08-19 session at the same
  K=50 / `judge_batch_size` 6 operating point]. The fast and slow ends of that spread would put
  it at **5.2 GPU-h** and **18.7 GPU-h** respectively [MODELLED from the same two measured
  extremes]. Treat 16 as an order of magnitude and not a landing time until the monitor can
  time this session.

Three cautions on that remainder, all of which have already cost this project a decision:

1. It is **wall clock**, measured from file mtimes. It is quoted as GPU-hours because this run
   is the only consumer of the device; those are not in general the same quantity.
2. It is a **measurement that ages**, and this file is the demonstration: the version before
   this one printed a rate and a landing time as **[LIVE]** and they were a week old by the
   time anyone read them. Measurements rot too. A MEASURED tag says where a number came from,
   never how old it is.
3. A rate carried across a **restart** is the weakest kind of carried number: model load,
   cache warmth and the judge's batching all reset. The mean above is the best anchor
   available [MEASURED, previous session], and it is still an anchor from a different session.

**The retired figure for this same job was ~67 GPU-h** [MODELLED from the K=8 probe in `docs/critique_log.md` entry 22, then spent on a K=50 run at a different judge batch size; superseded].
That number must not re-enter any planning document. An earlier version of this file carried
it as a live cost, which is the path by which it reached the overnight queue.

### Do not touch

- **Never** create `STOP.txt`, `STOP.txt.txt`, `STOP (1).txt`, `STOP (2).txt`, `stop.txt`,
  `STOP_SESSION.txt` or `STOP` in the repo root or in `C:/Users/Abhi/Downloads`. The watcher
  polls those exact paths every 15 s and kills the run on sight. It is the **user's** channel:
  `stop_watcher_v2.sh` says in its own header that nothing in the agent pipeline may write it,
  because a self-triggering stop makes the button useless. Naming the files in prose, as here,
  is safe; creating one is not.
- Do not edit `scripts/null_control.py`, `scripts/overnight_2026_08_14.sh`,
  `scripts/stop_watcher_v2.sh` or `scripts/watcher_supervisor_v3.sh`. Python reads a script at
  invocation, so an edit now lands days from now as a crash or as silent garbage.
- The manual stop of last resort, from the supervisor's own log line:
  `wsl -d Ubuntu-24.04 -- pkill -f venv-wsl`.
- The per-target sample cache is at `~/.cache/se-research/samples/attacks/wk9_defb/` **inside
  WSL, not in the repo**. A repo-scoped search finding nothing is not evidence of failure.
- `recompute_fair.py` writes its report only at the very end, in a single `write_text`. Watch
  the per-target JSONL for progress, never `results/`.

---

## 2. The surviving headline, and which interval belongs to which estimator

**[RE-DERIVED]** on 2026-08-26 by re-reading the artifacts themselves — the floor row of
`results/replay_control.md`'s section 2 table at line 181, its paired-difference table at line
203, and `figures/fig_floor_budget_data.csv` for the at-cap row and the estimator mapping — and
**not** by carrying this table forward from the previous version of this file, which is how it
came to be wrong:

| statistic | direct N=10 (do not mix) | replay N=10 | replay N=20 | measured N=40 |
|---|---|---|---|---|
| floor, min non-zero achievable FPR (MATCHED) | 9.5% [6.2, 14.4] | 12.0% [8.9, 15.3] | 3.1% [1.8, 4.7] | **2.0%, no interval** |
| at-cap mass at `ln N` (the quantity that DOES carry one at N=40) | 9.5% [6.2, 14.4] | 12.0% [8.9, 15.3] | 3.1% [1.8, 4.7] | **0/200 = 0.0% [0.0, 1.9]** |
| estimator the interval belongs to | Wilson on 19/200 | question bootstrap | question bootstrap | floor: **none**; at-cap: Wilson on 0/200 |

The two rows are the *same number* at every budget except N=40, where they part company: the
floor is `4/200 = 2.0%` and the at-cap mass is `0/200`. That is the whole of subsection (a),
and it is the thing this document previously got wrong. [RE-DERIVED 2026-08-26 from
`figures/fig_floor_budget_data.csv`, which the figure generator refuses to write unless it can
re-derive every cell from `results/n_scaling_ckpt.jsonl`.]

The paired legs, from the same CSV: **10 → 20 is -8.9 [-11.1, -6.8]**, **20 → 40 is
-1.1 [-2.4, +0.2]** (covers zero), **10 → 40 is -10.0 [-12.9, -7.2]**. All three are matched
paired bootstraps over the 200 questions. Note `results/replay_control.md` prints the 10 → 20
leg as **-8.8** — that file's floors are a 40,000-draw Monte Carlo where the figure counts
independent sets exactly, they disagree in the first decimal, and **the paper quotes the exact
-8.9**. Its table says so in the row itself; do not "correct" the paper down to 8.8.

The claim is the **fall across sample budgets within uniform provenance**: replay N=10 to
measured N=40 is **-10.0 points [-12.9, -7.2], excluding zero**. The paper keeps
**9.5% [6.2, 14.4]** as its own N=10 floor, because every other N=10 number in the paper is
welded to the same June cache; the replayed 12.0% is what the budget comparison runs on.

### (a) The N=40 floor: the settled ruling, and the three ways this file used to get it wrong

**This is settled. `results/n40_floor_estimator_ruling.md` is the adjudication, and it carries
the coverage simulation that decided it.** Read that file before you touch any N=40 interval.

**At N=10 and N=20 the ceiling atom is full.** The floor and the at-cap mass are the same
number, the threshold is the a-priori `ln N`, and Wilson is the correct interval — coverage
**95.1%** at N=10 and **96.2%** at N=20 against a nominal 95% [RE-DERIVED 2026-08-26 from the
coverage table at `results/replay_control.md:396-398`, which is generated from the ruling].

**At N=40 the atom is EMPTY.** No clean correct answer reaches `ln 40` (`0/200`), so the floor
stops being the atom and becomes an order statistic: the top rung *this* pool happened to
reach, `4/200 = 2.0%`. Both candidate intervals were then tested against a true population
floor of **0.27%** and **both failed**: Wilson on 4/200 covers **53.7%**, the question
bootstrap **0.00%**, at nominal 95%. The reason is not data selection. It is that the estimand
dissolves — `4/200` is the **resolution limit of a 200-answer pool**, not an estimate of a
population floor, and a larger pool reaches a higher rung and reports a smaller one.

> **Do not quote `53.7%` as a measurement.** Every number in that coverage table, *including*
> the "true floor" column, is a property of the fitted Ewens/CRP model — there is no
> measurement of a population floor anywhere in this project. Worse, the ruling's own sections
> 7 and 8 show `53.7%` is a **step function**: moving the model's floor by 0.0100 points takes
> it to 80.7%, and in the live zero branch it is 0%. It is `P(floor count = 1)` wearing a
> coverage label. **The `0.00%` for the bootstrap is the robust half** — it holds across the
> whole plausible range, because that interval's lower endpoint is pinned at `1/200` by
> construction. Nothing in the practical ruling depends on `53.7%` being right.

**So the N=40 floor row prints the at-cap mass `0/200 = 0.0% [0.0, 1.9]`** — Wilson at the
a-priori threshold `ln 40`, where it is valid — **with `2.0%` beside it carrying NO interval.**

**The OPPOSITE ruling applies to the achieved 5%-budget operating point, `10/200`.** There
Wilson **`5.0% [2.7, 9.0]`** is correct and the question bootstrap **`[2.5, 5.0]` is retired**
— its upper endpoint is pinned at the budget in 100% of simulated pools, so it restates a fact
about the estimator's range as a fact about the world. Coverage **54.81%** against Wilson's
**94.44%** [CARRIED from `results/n40_floor_estimator_ruling.md` section 12; same model, same
caveat as above, but this row does not sit on a knife edge — the ruling states that none of
the three defects found against the floor row touches it]. That point is an *interior*
quantile with ~190 answers below it; **being at the boundary of the support is what breaks an
interval, not data selection.** That one sentence is why the two rows rule opposite ways.

**Three representations of the withdrawn position lived in THIS FILE until 2026-08-26.** Two
are below; the third is in section 6, where this document described a suite failure that no
longer exists and told the reader to pay a debt that had been cancelled. They are named
because the shape matters more than the instance:

1. The headline table above printed `2.0% [0.8, 5.0]` for the measured N=40 cell under a
   **[RE-DERIVED]** mark, and sourced it to `results/replay_control.md` — which by then printed
   `2.0% (no interval -- see 2c)`. A **[RE-DERIVED]** tag on a number copied from a document
   that has since moved is worse than no tag: it is an assurance that nobody checked.
2. A prose argument that the floor is "outside Wilson's reach" and "therefore takes the same
   question bootstrap as the paired fall", ending in an **instruction to the next agent** to
   update the expected literal in `scripts/derived_paper_quantities.py` toward that bootstrap.
   The ruling had withdrawn that bootstrap at **0.00%** coverage. An instruction does not
   merely record an error, it schedules one, and this is the highest-leverage file in the repo
   in which to schedule it. Both are gone. **Nothing is owed toward either candidate interval.**

### (b) The AUROC row that looks alive

In the same section 2 table, `direct10 -> measured40` gives AUROC **+0.0412 [+0.0064, +0.0767]**
[RE-DERIVED 2026-08-26 from `results/replay_control.md:219`], which excludes zero and reads
like a finding. It is the one comparison that **mixes provenance** — the column is labelled
"do not mix" — and AUROC-vs-budget is one of the two claims that **died on their merits**.
Like-for-like it is **+0.0236 [-0.0135, +0.0595]**. Inside the uniform-provenance replay family
every AUROC, pAUC and TPR difference covers zero. The rows are in the file only so that the
refutation is checkable like-for-like.

### (c) The superseded fall — FIXED, and this is what a closed item looks like

The previous version of this file warned that `results/replay_control.md` still printed
**-9.9 points [-15.5, -5.0]** and the floor triple **11.9% -> 3.0% -> 2.0%** under the heading
*"What is worth carrying instead"*. **It no longer does** [RE-DERIVED 2026-08-26 — I grepped
that file for `9.9`, `15.5`, `11.9%` and `3.0%` and the retired renderings are absent; line 721
now reads `12.0% -> 3.1% -> 2.0%` and `-10.0 points [-12.9, -7.2]`]. Those strings are now in
`RETIRED_QUOTES` in `scripts/replay_control.py` and checked for absence in the generated
report, so a relapse fails rather than being noticed by a reader.

This entry is kept rather than deleted because a warning about another file is a claim about
another file, and it decays exactly like a number does. Re-read the file it names before
repeating it — that is how this one was found to be stale.

### Dead, and dead in both directions

These must not re-enter in any form, **including inverted**:

- **AUROC-vs-budget.** Dead on its merits.
- **Cross-budget TPR / pAUC.** Dead on its merits. Every interval covers zero.
- **Any interval on the measured N=40 floor** — `[0.8, 5.0]`, `[0.78, 5.03]`, `[0.7804,
  5.0287]`, `[0.5, 4.0]`, and any future candidate. Both were withdrawn on measured coverage;
  the row prints a point. **Inverted counts too:** "the paper should reinstate Wilson there"
  and "the paper should switch to the bootstrap there" are the same dead claim wearing
  opposite signs, and this file has previously carried the second one as an instruction.
  `scripts/check_population_labels.py` arms six SUPERSEDED patterns against these renderings
  and `tests/test_derived_paper_quantities.py` pins their absence from `paper/`.
- **The question bootstrap `[2.5, 5.0]` on the achieved 5%-budget point.** Retired; that row
  takes Wilson, `5.0% [2.7, 9.0]`. Note this is the *opposite* direction to the row above — do
  not "make the two rows consistent" by giving them the same estimator. Section 2(a).
- **The "2^-20 sign test".** A gate's decisive finding; refuted at R=200.
- **The widening "correction" to the paper's intervals.** It was itself wrong. An exact
  variance decomposition (independent sets counted by branching recursion, residual 1.4e-17)
  showed the subset-draw component is *already inside* Wilson, via
  `mean(p(1-p)) + var(p) = pbar(1-pbar)`. Fixed. Do not re-widen. **[CARRIED]** — the
  decomposition is in `docs/critique_log.md` entry 36, section 3.

An inverted dead claim is still a dead claim. The refutations killed the comparison, not one
sign of it.

---

## 3. Every rate must name a population

There are five, and a rate that does not name one is not a claim:

1. the **fair pool** — 200 correct + 200 hallucinating;
2. its **200-answer correct stratum**;
3. the **1424-answer superset** of that stratum;
4. a **2000-question replication pass**;
5. an **80-target attacked prefix**.

**They are nested, not separate.** `_stratum_ids(want, seed, labels)` seed-shuffles a stratum
and `select_stratified` takes `[:n]`, so both pools are prefixes of the *same* seed-0 shuffle.
The 80 FA targets are exactly `right[:80]`. Every attacked target is *inside* the fair pool.
**[CARRIED]** from the prefix verification recorded in `docs/critique_log.md`; re-run
`verify_nesting` before restating it.

Consequences that keep being got wrong:

- **Do not say the attacked pool "separates worse."** It is a score-independent sub-sample of
  the same strata, so its AUROC estimates the *same* quantity as the fair pool's and its
  interval comfortably contains it. The gap is sampling error over far fewer ranked pairs.
- **Any pooled figure is a function of the assumed class balance.** The fair pool is 50/50;
  the real rate is not. **Prefer the per-stratum rows.**
- **Any statistic with 97 in its denominator is stale by construction.** It was a snapshot of
  a cell that was still growing.

This error has been found at **seven** sites, one of them in text written the same hour, one
of them inside a pre-registration. `scripts/check_population_labels.py` runs in the suite and
enforces *attachment*, not mere presence. **What it still cannot catch is listed in its module
docstring — read that list before trusting a green run.**

---

## 4. The lattice — re-enumerated 2026-08-26

**[RE-DERIVED]** again on 2026-08-26 by enumerating integer partitions and computing
`-sum (c/N) ln(c/N)` directly, independently of the 2026-08-19 enumeration. Every cell below
reproduced to the digit. This is pure arithmetic, independent of any run, any population and
any n, so it is the one block in this file you may quote without re-checking:

| N | partitions p(N) | distinct SE values | coincidences | cap ln(N) | values in top tenth |
|---|---|---|---|---|---|
| 10 | 42 | **39** | 3 | 2.302585 | **2** — 2.163956 and 2.302585 |
| 20 | 627 | **455** | 172 | 2.995732 | **7** |
| 40 | 37338 | **14116** | 23222 | 3.688879 | **42** |

The N=40 row is added here because that is the budget the floor argument now turns on, and it
makes the granularity point without any statistics: the lattice at N=40 is dense, which is
precisely why `4/200` is a resolution limit of the *pool* and not a property of the detector.
`tests/test_judge_owed_conditions.py::test_n20_lattice_matches_the_repo_s_own_455` pins the
455 against an independent implementation.

At N=10 the gap between the top two attainable points is **0.138629 nats**, and the next
point down is **2.025326**, leaving **0.277259 nats** of headroom. So at a success criterion
of delta = 0.25, every target sitting at 2.163956 has less headroom than delta and **cannot
register a success under any paraphrase**: the unwinnable set is the whole top decile, not
just the exact-ceiling cases, and at delta = 0.25 the two sets coincide exactly.

**Non-relaxability is withdrawn as FALSE** — 455 values at N=20 against 39 at N=10 is roughly
twelvefold, so granularity *is* relaxable. The honest residue, and it is the interesting half:
doubling N takes the top decile from **2 points to 7**, so the lattice stays sparsest exactly
where the false-alarm claim lives.

**Do not quote a distinct-value count as a finding.** "22 distinct values" was retired
entirely: it is a sample size, monotone in n. The lattice counts above are not — they are
enumerations of what the estimator can emit at all.

---

## 5. Findings still standing — pointers, not copies

Deliberately **not** restated here with their numbers. Each one's artifact is authoritative
and each has moved at least once. All **[CARRIED]**.

| finding | owning artifact |
|---|---|
| ceiling saturation on the definitive `_defb` FA cell | `results/ceiling_saturation_finding.md` |
| crowding by stratum, Wilson intervals, CPU recompute | `results/achievable_fpr_grid.md`, `results/fair_pool_report.md` |
| asymmetric censoring — biases the clean AUROC *downward* | `results/fair_pool_report.md` |
| winner's curse / shrinkage / retention (`_def`; **will move under `_defb`**) | `results/winners_curse_partial.md` |
| judge validation — cite the **deployed symmetric** config, 0.93 | `results/judge_validation.md` |
| replication — quote the greedy alias-aware span number, not the all-samples-correct one | `results/n_scaling_grid.md` |
| the arithmetic the paper prints, input by input, with its provenance column | `results/derived_paper_quantities.md` |

Two of these carry standing warnings that have each been "fixed" back by mistake before:

- The judge number **0.93** is the deployed symmetric config. A critic gate flagged it as
  drift; that ruling was wrong, was overruled, and the overrule was sustained. The
  **superseded** asymmetric run gave different figures. Do not "correct" it back.
- The replication comparison must use the **greedy alias-aware span** convention. The
  all-samples-correct label is *coupled to the score* — it calls a question correct iff all
  ten samples are correct, and SE is the entropy of the clustering of those same ten.

---

## 6. The guards, and why the suite is red on purpose

**Two failures, both the same site, at 20:31** [RE-DERIVED — full `pytest -q` run, 2026-08-26:
1035 passed / 17 skipped / 2 failed / 1 warning]. The previous version of this file described
**three** failures and told the reader what to do about the third; that third failure no longer
exists, and the action it prescribed is the one the ruling withdrew. Both survivors are in
`tests/test_operational_provenance.py` and both name the same single file:

> `scripts/overnight_2026_08_14.sh` carries 3 operational figures with no
> MEASURED/MODELLED/UNMEASURED tag, against a ratchet baseline of 0.

That file is on the do-not-edit list **and is PID 521 in section 1** — it is the wrapper the
live run is executing. The debt is real, it is recorded, and it is unpayable by anyone while
the run is up. It was **not** silenced by raising the baseline: the checker prints "Do not
raise the baseline to make this pass", the file entered the repo after the register was
struck, and a guard that gets widened the first time it is inconvenient is worth nothing.
**When the null control lands and the no-edit rule lifts: tag those three figures in the
script, and the suite goes green without anyone touching the register.**

**The third failure is gone, and how it went is the part worth reading.** It was
`tests/test_derived_paper_quantities.py` reporting that a registered literal —
`a measured $2.0\%$ [$0.8$, $5.0$] at $N{=}40$` — had left `discussion.tex`. The previous
version of this file read that as a debt and instructed the next agent to update the expected
literal toward the question bootstrap. That was exactly backwards: the guard was reporting a
*correct* edit, and the interval it would have been pointed at was withdrawn at 0.00% coverage.
The registry now pins the **withdrawal** instead of an interval —
`test_the_n40_floor_count_carries_no_interval_in_the_paper` asserts that the paper prints
`a measured $2.0\%$ at $N{=}40$` as a bare point and that seven retired renderings
(`[$0.8$, $5.0$]`, `[$0.78$, $5.03$]`, `[$0.5$, $4.0$]`, `0.7804`, `5.0287`, …) are absent.
**A guard that reports a change is not a guard that says which direction is right.** Read the
ruling, not the red.

The checker itself, `scripts/check_operational_provenance.py`, is **red by design** — it
reports open sites across the repo. That is a debt ledger, not a failing grade. Its rules:

1. a **dead anchor** may not be restated in a live planning document without saying it is dead;
2. an operational figure must be **tagged** MEASURED / MODELLED / UNMEASURED (ratcheted per file);
3. a MODELLED figure must **name the anchor** it came from;
4. a MODELLED figure may declare `supersede-when: <path>` and fails once that artifact exists;
5. a **countdown** must be arithmetically true today.

**What it cannot do is decide whether an anchor FITS** — that failure mode is type (d) in its
docstring, and every error the original audit found was type (d). A tag can read MEASURED and
the measurement can be of the wrong thing. Read the docstring's closing list before trusting a
green run.

---

## 7. Owed, in priority order

**0. One live contradiction inside `paper/`, found 2026-08-26 and NOT fixed** — the sweep that
found it was scoped to leave `paper/` alone, so it is reported rather than repaired.
`paper/sections/discussion.tex:306` reads *"the measured $N{=}40$ floor is a count at no fixed
threshold at all and takes the question bootstrap for the reason given above."* That is the
**withdrawn** position. It contradicts `discussion.tex:164` — *"The measured $N{=}40$ floor
takes neither, for the reason below"* — 142 lines earlier in the same file, and it contradicts
the ruling, `results/replay_control.md` and this section 2. It survived four rounds of sweeps
because it is **prose with no digits in it**: every guard in the repo that watches the N=40
floor matches renderings like `[$0.8$, $5.0$]` or `5.03`, and this sentence contains no number
at all. Whoever owns `paper/` next: delete the clause or replace it with the non-identification
reason `:164` already gives. **Check `:164` and `:306` say the same thing before believing
either.**

1. **Judge conditions (ii) and (iii)** — validation on messy real sampled pairs, and a
   differential-over-splitting check. `judge_validation.md` lists both as unmet before the
   paper cites the judge as sole adjudicator. **Needs GPU.**
2. **Winner's curse under `_defb`.** Cheap, quantified, not launched; the shrinkage and
   retention figures in the Abstract will both move. Competes with the device.
3. **The definitive null control** — running now, section 1. The gate on the attack verdict.
4. **Table 1 fill-in.** Attach n per row; the population linter watches this table.
5. **Human equivalence audit** — harness exists (`prepare_equivalence_audit.py`), unrun.
6. **Regenerate `fair_recompute_report.md`** from `_defb` when the matrix finishes.
7. **If the crossing test is ever promoted** to a claim statistic: re-fix tau on a genuinely
   disjoint split, say which was used, and fix arm-exchangeability first — `feasible_objs` is
   a running-record subset, so any p from it is an upper bound on the evidence.
8. **A negative control for the nesting check.** `verify_nesting` asserts the prefix property;
   nothing yet demonstrates it *failing* at another seed, so it is unproven as non-vacuous.

---

## 8. Process rules, every one of them bought with an error

- **A correction is a claim, and carries the same burden as the thing it corrects, plus one.**
  Three corrections landed on the night of 2026-08-19 and two of them were wrong. One came
  from a critic gate that had reproduced the correction's own arithmetic and still shipped the
  error, because it measured a component's **magnitude** and inferred its **absence**.
- **"The critic approved it" and "the critic caught it" are the same kind of evidence, and
  neither is a safety property.**
- **Check every gate ruling against the committed artifact before applying it.** The critic has
  been wrong, and applying a ruling on authority would have shipped the error.
- **Before claiming two samples are independent, read the selector** — the code, not the names
  and not the design intent. That claim reached a pre-registration before anyone checked it.
- **Ask "monotone in n?" before any count enters a sentence.** A statistic that moves while you
  type it is a sample statistic, not a property.
- **Grep your own artifacts for the counterexample before publishing the claim.** The number
  that refuted non-relaxability sat in a corrections file for eleven days.
- **Never assert a property of your own script from memory.** Re-read it.
- **Sweep on numbers, not phrases.** LaTeX markup defeats phrase matching: a manual grep for a
  pool name missed a section because the source read `\emph{fair} pool`.
- **And sweep on the claim stated in words, with no digits, as a separate pass.** The rule above
  is necessary and it is not sufficient. Five rounds of agents chased the N=40 interval by its
  renderings and each one left sites behind, because **the misses do not sort by file, they
  sort by REPRESENTATION**: prose, an instruction to a future agent, a numeric tuple in a test,
  one file's assertion about another file's contents, a string literal inside a generator. The
  last two survivors — `discussion.tex:306` and a docstring in
  `scripts/make_floor_budget_figure.py` — contain no digit belonging to the retired interval,
  so no numeric sweep could ever have found them. Enumerate the representations first, then
  grep once per representation. `docs/critique_log.md` entry 38 is the long version.
- **A generator's prose can disagree with the generator's own code, and nothing will fail.**
  The figure script has plotted the N=40 floor as a bare point since the ruling; its docstring
  went on saying "Wilson on the count for the two directly measured rows" for a week. Every
  artifact it produced was correct. Docstrings are read exactly when someone wants to know what
  the output means.
- **A green test suite next to a known-broken statistic reads as validation of it.** Pin the
  failure or delete the test.
- **Do not assert run state — read it.** Both directions have burned this project: a stale
  progress figure reported as current, and a false "nothing has been written in hours" that
  was a repo-scoped search missing the WSL cache.
- **Unmeasured claims are the worst failure mode.** The Abstract once asserted something that
  had never been measured, twice having pre-committed not to say it until it was.
- **A number printed under a heading that invites lifting will be lifted.** See section 2(c):
  a retired fall sat under "What is worth carrying instead" and reached three briefings in one
  night. The same applies to a **[RE-DERIVED]** tag, which is a heading that invites lifting
  written at the level of a single number — see section 2(a), item 1.
