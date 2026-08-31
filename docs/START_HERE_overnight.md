# START HERE, current state, 2026-08-31 01:40

**arXiv target: 2026-10-01.** There is deliberately no countdown in this file. A countdown is
monotone in time, so it is the one figure that is guaranteed to be wrong by the time you read
it, and this document has produced a stale-countdown finding twice, one of those from text that
was itself warning against the practice. The target date does not go stale; a number of
days does. If you want the remainder, subtract.

**What this file is.** It is the handoff a future session reads first, before it has any
context. That makes it the highest-leverage place in the repository to launder a dead number,
and this project's convention is stricter than "a stale line records an error": a stale line in
here SCHEDULES one, because an obedient agent acts on it. That has already happened once, when
an earlier version instructed the next session to adopt an estimator that the ruling had
withdrawn on measured coverage.

**What this file is not.** It does not supersede anything. It claims to be true at the
timestamp in its title and it dates every number so you can tell how far that claim has
travelled. A previous version opened with "Supersedes every earlier version" while being six
days stale in four separate places.

**Live at the top of this rewrite, all re-derived 2026-08-31 and each shown its source below:**

| fact | value | how it was read |
|---|---|---|
| HEAD | `59b5003` | `git rev-parse HEAD` |
| GPU | **nothing is running** | `ps` inside WSL, section 1 |
| the definitive null control | **80/80, complete** | the checkpoint itself, section 1 |
| suite | **1389 pass / 17 skip / 2 fail** | a real `pytest -q` run, section 6 |
| citations | **33 keys cited, 33 bib entries, exact bijection, 0 uncited** | `scripts/check_latex_source.py` |
| committed PDF | **41 pages** | rebuilt and recommitted 2026-08-31, so the blob and the working tree agree |
| working tree | **dirty, and moving under you** | see the warning immediately below |

> **A CLOSING ROUND WAS EDITING THE REPOSITORY WHILE THIS WAS WRITTEN**, and it was widening as
> it went: five files dirty at 01:25, fifteen at 01:36, including `.gitignore`,
> `ARTIFACT_AVAILABILITY.md`, `docs/critique_log.md`, six of the eight `.tex` files,
> `scripts/derived_paper_quantities.py` and `tests/test_derived_paper_quantities.py`.
>
> Two consequences, and they govern how to read the rest of this document.
>
> 1. **Do not quote a page count, an overfull count or a test count off the working tree until
>    it settles.** Measured across three minutes, the working-tree build went 38 pages with 2
>    overfull, then 39 with 0, then 39 with 3. **The 38 in the table above is the committed
>    blob**, extracted with `git show HEAD:paper/main.pdf` and measured on the extracted file,
>    which is the only stable reading available while a build is in flight.
> 2. **Every DONE / OWED status in section 7 was read between 01:05 and 01:36 on 2026-08-31,
>    against a tree that was changing under the reader.** Some of them will have been closed by
>    that round before you get here. **Re-check each one against the file before acting**; the
>    section says where to look for each. A status line is a claim about another file and decays
>    exactly like a number does.

---

## 0. How to read the numbers in this file

Every figure below carries one of three marks. Nothing is unmarked.

| mark | meaning |
|---|---|
| **[LIVE]** | read out of a running or moving artifact at the timestamp given. It will have moved by the time you read this; the artifact is named so you can re-read it. |
| **[RE-DERIVED]** | recomputed from first principles or from a primary artifact during the session named in the tag. Safe to quote **with that date attached**. |
| **[CARRIED]** | inherited from an earlier session and **not** re-verified here. The owning artifact is named. **Do not quote a [CARRIED] number into the paper without opening that artifact first.** |

A **[RE-DERIVED]** tag is not a warrant. It says where a number came from, never how old it is,
and it is itself a heading that invites lifting: section 2 records a cell that was copied under
a **[RE-DERIVED]** mark from a document that had since moved, which is worse than no tag at all
because it is an assurance that somebody checked.

---

## 1. The machine right now: idle

**Nothing is running on the GPU.** **[LIVE 2026-08-31 01:05]**, read from
`wsl -d Ubuntu-24.04 -- ps -eo pid,etime,cmd`. The process table holds `init`, `systemd`,
`udev` workers, `snapd`, `cron` and the shell that ran the query. There is no
`scripts/null_control.py`, no `scripts/overnight_2026_08_14.sh`, no `scripts/stop_watcher_v2.sh`
and no `scripts/watcher_supervisor_v3.sh`. WSL itself had an elapsed time of one second, i.e.
the distro booted to serve that command.

The previous version of this file described a live resume at 54 of 80 targets with four named
PIDs. **That run finished.** Do not restart it: see below.

**The definitive null control is COMPLETE.** **[RE-DERIVED 2026-08-31]** by parsing
`results/null_control_ckpt_defb.jsonl` directly: **80 lines, 80 distinct `question_id`, 0 torn
lines**, last write 2026-08-29 03:54:35. The report
`results/null_control_report_defb.md` (2026-08-29 10:23) states the run finished 2026-08-29
03:57 and re-verifies the same 80/80 with a sha256. `results/diag_defb.json` landed in the same
second as the checkpoint.

**Do not relaunch `scripts/overnight_2026_08_14.sh`.** The instruction to do so, in the previous
version of this file, was correct on 2026-08-27 and is now the single most expensive stale line
in the repository: it would burn GPU-days re-running a cell that is finished and would rewrite
the checkpoint every downstream artifact is keyed to.

Consequences of the machine being idle, which is the state this project has spent months not
being in:

- **The no-edit rule on the runner scripts has LIFTED.** The reason they were frozen was that
  Python and bash read a script at invocation, so an edit to a running job lands later as a
  crash or as silent garbage. Nothing is invoking them. Section 6's suite failure is now
  payable. **Re-run `ps` before you edit any of them anyway**, because a later session may read
  this line while a run is up.
- **Every remaining item on the owed list in section 7 is CPU work or prose**, with the two
  exceptions named there. The adjudication says so in its own words: no must-fix item requires a
  new experiment.

### Do not touch

- **Never** create `STOP.txt`, `STOP.txt.txt`, `STOP (1).txt`, `STOP (2).txt`, `stop.txt`,
  `STOP_SESSION.txt` or `STOP` in the repo root or in `C:/Users/Abhi/Downloads`. The watcher
  polls those exact paths every 15 s and kills the run on sight. It is the **user's** channel:
  `stop_watcher_v2.sh` says in its own header that nothing in the agent pipeline may write it,
  because a self-triggering stop makes the button useless. Naming the files in prose, as here,
  is safe; creating one is not. **This survives the run being over.** The next run will have the
  same channel.
- The distro is `Ubuntu-24.04`. Always `wsl -d Ubuntu-24.04`, never `wsl -d Ubuntu`.
- The manual stop of last resort, from the supervisor's own log line:
  `wsl -d Ubuntu-24.04 -- pkill -f venv-wsl`.
- The per-target sample cache is at `~/.cache/se-research/samples/` **inside WSL, not in the
  repo**. A repo-scoped search finding nothing there is not evidence of failure. This is now
  also a publication problem: see R2 in section 7.
- `recompute_fair.py` writes its report only at the very end, in a single `write_text`. Watch
  the per-target JSONL for progress, never `results/`.

### The cost model, retired in full

The remaining-work estimates that lived in this section (a per-target mean, a remainder in
GPU-hours, a fast-to-slow spread) were about a run that has finished. Their digits are deleted
rather than archived, because a plan figure for completed work has no consumer, and one live
readable number is how a retired cost once reached the overnight queue. **That retired
`~67 GPU-h` null-control price** [MODELLED from the K=8 probe in `docs/critique_log.md`
entry 22, then spent on a K=50 run at a different judge batch size; DEAD, and superseded by the
measurement in `results/null_control_cost_options.md`] **must still not re-enter any planning
document.** If a future run needs a cost, measure it from that run's own first hour: three
filesystem anchors and a division beat any model here.

---

## 2. The surviving headline, and which interval belongs to which estimator

**Anchors, not line numbers.** The previous version cited `results/replay_control.md` by line
(181, 203, 219). Those had already drifted by roughly seven lines when checked on 2026-08-31,
without the file changing, because a line number is a claim about a file's *layout*. Grep for
the row instead. The rows below were re-read on 2026-08-31 by grepping
`results/replay_control.md` for `floor (min non-zero achievable FPR)`, for
`replay10 -> replay20`, and for `AUROC`, and by reading
`figures/fig_floor_budget_data.csv` for the at-cap row and the estimator mapping.

| statistic | direct N=10 (do not mix) | replay N=10 | replay N=20 | measured N=40 |
|---|---|---|---|---|
| floor, min non-zero achievable FPR (MATCHED) | 9.5% [6.2, 14.4] | 12.0% [8.9, 15.3] | 3.1% [1.8, 4.7] | **2.0%, no interval** |
| at-cap mass at `ln N` (the quantity that DOES carry one at N=40) | 9.5% [6.2, 14.4] | 12.0% [8.9, 15.3] | 3.1% [1.8, 4.7] | **0/200 = 0.0% [0.0, 1.9]** |
| estimator the interval belongs to | Wilson on 19/200 | question bootstrap | question bootstrap | floor: **none**; at-cap: Wilson on 0/200 |

**[RE-DERIVED 2026-08-31]** for the row identities and the N=40 cells; the interval endpoints
are **[CARRIED]** from `results/replay_control.md` and `figures/fig_floor_budget_data.csv`,
which the figure generator refuses to write unless it can re-derive every cell from
`results/n_scaling_ckpt.jsonl`.

The two rows are the *same number* at every budget except N=40, where they part company: the
floor is `4/200 = 2.0%` and the at-cap mass is `0/200`. That is the whole of subsection (a),
and it is the thing this document previously got wrong.

The paired legs: **10 -> 20 is -8.9 [-11.1, -6.8]**, **20 -> 40 is -1.1 [-2.4, +0.2]** (covers
zero), **10 -> 40 is -10.0 [-12.9, -7.2]**. All three are matched paired bootstraps over the 200
questions. `results/replay_control.md` prints the 10 -> 20 leg as **-8.8** and says so in the
row itself: that file's floors are a 40,000-draw Monte Carlo where the figure counts independent
sets exactly, the exact value is -8.8630, and **the paper quotes -8.9**. Do not "correct" the
paper down to 8.8. There is a guard on this; see the trap in section 6.

The claim is the **fall across sample budgets within uniform provenance**: replay N=10 to
measured N=40 is **-10.0 points [-12.9, -7.2], excluding zero**. The paper keeps
**9.5% [6.2, 14.4]** as its own N=10 floor, because every other N=10 number in the paper is
welded to the same June cache; the replayed 12.0% is what the budget comparison runs on.

### (a) The N=40 floor: the settled ruling

**This is settled. `results/n40_floor_estimator_ruling.md` is the adjudication and carries the
coverage simulation that decided it. Read that file before you touch any N=40 interval.** Two
independent 2026-08-30 reviews reached the same verdict; the panel chair's phrase is that the
refusal to interval the N=40 floor "is a correct call, not a hedge".

**At N=10 and N=20 the ceiling atom is full.** The floor and the at-cap mass are the same
number, the threshold is the a-priori `ln N`, and Wilson is the correct interval: coverage
**95.1%** at N=10 and **96.2%** at N=20 against a nominal 95% **[CARRIED]** from the coverage
table in `results/replay_control.md`, generated from the ruling.

**At N=40 the atom is EMPTY.** No clean correct answer reaches `ln 40` (`0/200`), so the floor
stops being the atom and becomes an order statistic: the top rung *this* pool happened to reach,
`4/200 = 2.0%`. Both candidate intervals were tested against a true population floor of
**0.27%** and **both failed**: Wilson on 4/200 covers **53.7%**, the question bootstrap
**0.00%**, at nominal 95%, **under the fitted Ewens population and only there.** The reason is
not data selection, and it is NOT that the estimand dissolves: ruling section 13 retracts that
sentence as branch-conditional dressed as unconditional. It is that `tau_top` is **not
identified**. If the population can never yield 39 mutually inequivalent answers out of 40, then
`4/200` estimates a real population quantity, Wilson covers it at **95.06%** and the bootstrap
at **100%**. If it can, `4/200` is the pool's resolution and can be arbitrarily far above the
truth. `n = 200` cannot separate those cases: `p = 0.1175` for the fitted model against the
measured `0/200`, and the model-free bound `[0%, 1.88%]` contains both zero and the model's
`1.065%`. The practical ruling is unchanged, quote `2.0%` with no interval, **but quote it for
THIS reason**, which needs no model, rather than for the retracted one, which needs the model to
be right.

> **Do not quote `53.7%` as a measurement.** Every number in that coverage table, *including*
> the "true floor" column, is a property of the fitted Ewens/CRP model; there is no measurement
> of a population floor anywhere in this project. Worse, the ruling's own sections 7 and 8 show
> that `53.7%`, Wilson's coverage under the calibrated Ewens fit and nowhere else, is a
> **step function**: moving that fit's floor by 0.0100 points takes it to 80.7%.
> It is `P(floor count = 1)` wearing a coverage label. **And the `0.00%` is not the robust half
> either.** Under the zero branch the bootstrap's pinning at `1/200` is exactly right and it
> covers **100%**. Both columns are branch-conditional; neither is a measurement. Nothing in the
> practical ruling depends on either being right, which is the point of resting it on
> non-identification instead.

**So the N=40 floor row prints the at-cap mass `0/200 = 0.0% [0.0, 1.9]`**, Wilson at the
a-priori threshold `ln 40` where it is valid, **with `2.0%` beside it carrying NO interval.**

**The OPPOSITE ruling applies to the achieved 5%-budget operating point, `10/200`.** There
Wilson **`5.0% [2.7, 9.0]`** is correct and the question bootstrap **`[2.5, 5.0]` is retired**:
its upper endpoint is pinned at the budget in 100% of simulated pools, so it restates a fact
about the estimator's range as a fact about the world. Coverage **54.81%** against Wilson's
**94.44%** **[CARRIED]** from `results/n40_floor_estimator_ruling.md` section 12; same model,
same caveat, but this row does not sit on a knife edge, and the ruling states that none of the
three defects found against the floor row touches it. That point is an *interior* quantile with
about 190 answers below it. **Being at the boundary of the support is what breaks an interval,
not data selection.** That one sentence is why the two rows rule opposite ways.

**The withdrawn position is gone from `paper/`, verified 2026-08-31.** The previous version of
this file reported, as item 0 of its owed list and again in its process rules, that
`paper/sections/discussion.tex:306` still read "takes the question bootstrap for the reason
given above". **That was repaired.** The sentence now lives at
`paper/sections/discussion.tex:361` and reads *"the measured $N{=}40$ floor is a count at no
fixed threshold at all and takes neither, for the reason given above"*, which agrees with the
same file's earlier statement and with the ruling. **[RE-DERIVED 2026-08-31]** by grepping
`discussion.tex` for `takes neither` and `question bootstrap`: the only surviving
`question bootstrap` occurrence is at line 232 and is the paired-fall estimator, where it
belongs. The old entry is deleted rather than struck through, because it pointed a future agent
at a fixed defect and would have had them "repair" correct text.

### (b) The AUROC row that looks alive

In the same table, `direct10 -> measured40` gives AUROC **+0.0412 [+0.0064, +0.0767]**, which
excludes zero and reads like a finding. It is the one comparison that **mixes provenance**, the
column is labelled "do not mix", and AUROC-vs-budget is one of the two claims that **died on
their merits**. Like-for-like it is **+0.0236 [-0.0135, +0.0595]**. Inside the
uniform-provenance replay family every AUROC, pAUC and TPR difference covers zero. The rows are
in the file only so that the refutation is checkable like-for-like.

### (c) The superseded fall: closed, and this is what a closed item looks like

An older version warned that `results/replay_control.md` still printed **-9.9 points
[-15.5, -5.0]** and the floor triple **11.9% -> 3.0% -> 2.0%** under a heading reading "What is
worth carrying instead". **It no longer does**; the file now carries `12.0% -> 3.1% -> 2.0%` and
`-10.0 points [-12.9, -7.2]`. Those strings are in `RETIRED_QUOTES` in
`scripts/replay_control.py` and checked for absence in the generated report, so a relapse fails
rather than being noticed by a reader.

This entry is kept rather than deleted because a warning about another file is a claim about
another file, and it decays exactly like a number does. Re-read the file it names before
repeating it; that is how the `discussion.tex` entry above was found to be stale.

### Dead, and dead in both directions

These must not re-enter in any form, **including inverted**:

- **AUROC-vs-budget.** Dead on its merits.
- **Cross-budget TPR / pAUC.** Dead on its merits. Every interval covers zero.
- **Any interval on the measured N=40 floor**: `[0.8, 5.0]`, `[0.78, 5.03]`,
  `[0.7804, 5.0287]`, `[0.5, 4.0]`, and any future candidate. Both were withdrawn on measured
  coverage; the row prints a point. **Inverted counts too:** "the paper should reinstate Wilson
  there" and "the paper should switch to the bootstrap there" are the same dead claim wearing
  opposite signs, and this file has previously carried the second one as an instruction.
  `scripts/check_population_labels.py` arms six SUPERSEDED patterns against these renderings and
  `tests/test_derived_paper_quantities.py` pins their absence from `paper/`.
- **The question bootstrap `[2.5, 5.0]` on the achieved 5%-budget point.** Retired; that row
  takes Wilson, `5.0% [2.7, 9.0]`. This is the *opposite* direction to the row above. Do not
  "make the two rows consistent" by giving them the same estimator. Section 2(a).
- **The "2^-20 sign test".** A gate's decisive finding; refuted at R=200.
- **The widening "correction" to the paper's intervals.** It was itself wrong. An exact variance
  decomposition (independent sets counted by branching recursion, residual 1.4e-17) showed the
  subset-draw component is *already inside* Wilson, via `mean(p(1-p)) + var(p) = pbar(1-pbar)`.
  Fixed. Do not re-widen. **[CARRIED]** from `docs/critique_log.md` entry 36, section 3.
- **The judge arm's `-0.17` net as evidence that the attack underperforms the null.** New on
  2026-08-29 and easy to reintroduce because the number is real and the paper quotes it. See
  section 5.

An inverted dead claim is still a dead claim. The refutations killed the comparison, not one
sign of it.

---

## 3. Every rate must name a population

There are five, and a rate that does not name one is not a claim:

1. the **fair pool**, 200 correct + 200 hallucinating;
2. its **200-answer correct stratum**;
3. the **1424-answer superset** of that stratum;
4. a **2000-question replication pass**;
5. an **80-target attacked prefix**.

**They are nested, not separate.** `_stratum_ids(want, seed, labels)` seed-shuffles a stratum and
`select_stratified` takes `[:n]`, so both pools are prefixes of the *same* seed-0 shuffle. The 80
FA targets are exactly `right[:80]`. Every attacked target is *inside* the fair pool.
**[CARRIED]** from the prefix verification in `docs/critique_log.md`; re-run `verify_nesting`
before restating it.

Consequences that keep being got wrong:

- **Do not say the attacked pool "separates worse."** It is a score-independent sub-sample of the
  same strata, so its AUROC estimates the *same* quantity as the fair pool's and its interval
  comfortably contains it. The gap is sampling error over far fewer ranked pairs.
- **Any pooled figure is a function of the assumed class balance.** The fair pool is 50/50; the
  real rate is not. **Prefer the per-stratum rows.**
- **Any statistic with 97 in its denominator is stale by construction.** It was a snapshot of a
  cell that was still growing.
- **New, 2026-08-30, and it reached print:** "the same population yields 28 at n=200 and 35 at
  n=2000" names two different populations, the fair pool's correct stratum against the full
  labelled pool. Both reviews flagged it independently. The offending phrase is the one doing the
  argumentative work, so "the same population" cannot simply be dropped; the populations have to
  be named. Owed item M8, section 7.

This error has been found at **eight** sites now, one of them in text written the same hour, one
inside a pre-registration, and one in the Introduction after five sweeps.
`scripts/check_population_labels.py` runs in the suite and enforces *attachment*, not mere
presence. It is red today for a bookkeeping reason that is not a defect; section 6 says which,
and R12 is the one-line fix. **What it still cannot catch is listed in its module docstring.
Read that list before trusting a green run**: it did not catch M8, which is in `paper/` and in
scope.

---

## 4. The lattice, and the one cell in it that is not stable

**[RE-DERIVED 2026-08-31]** by enumerating integer partitions and computing
`-sum (c/N) ln(c/N)` directly, with independent code, at three rounding tolerances.

| N | partitions p(N) | distinct SE values | coincidences | cap ln(N) | values in top tenth |
|---|---|---|---|---|---|
| 10 | 42 | **39** | 3 | 2.302585 | **2**, being 2.163956 and 2.302585 |
| 20 | 627 | **455** | 172 | 2.995732 | **7** |
| 40 | 37338 | **14114** | 23224 | 3.688879 | **42** |

**Every row is now exact, and the ambiguity this section used to warn about is resolved.**
Two partition entropies at N=40 differ by about one float ULP, so any count obtained by
rounding scores and deduplicating depends on the rounding. There is no correct tolerance to
pick: `scripts/fair_pool_granularity.attainable_lattice(40, dp=D)` returns 14114 at D=9, 10
and 11, **14116 at its own default D=12**, and 14138 at D=13. A quantity that moves in three
directions as you vary a display parameter is being measured with the wrong instrument.

**The fix is to stop comparing floats.** Cluster sizes are integers, and

    H = ln N - (1/N) * ln( prod over clusters of c^c )

so two partitions of N carry the same entropy **iff** their integer products `prod(c^c)` are
equal. Keying on that product is exact integer arithmetic: no tolerance, no interpreter
dependence, no float anywhere in the comparison. It gives

    N=10 -> 39      N=20 -> 455     N=30 -> 2980    N=40 -> 14114

reproduced on Windows CPython 3.11.9, on WSL CPython 3.12.3, and by a third route built on
`sympy.partitions`, all three agreeing exactly.

**Consequences.**

- **An N=40 count no longer needs a tolerance named beside it**, because the criterion that
  produces it is exact. The number is **14114**, and the earlier instruction in this file to
  never quote one bare is withdrawn.
- `tests/test_n_scaling_grid.py` now pins **14114** and passes on both platforms. It
  previously pinned 14116, which passed on Windows and would have failed under WSL.
- **`results/n_scaling_plan.md` was corrected in place** on 2026-08-31 and now prints 14114 in
  all four places, with the integer criterion stated beside its table. It is quotable again.
  It is one of the few results files corrected rather than bannered, because the wrong digit
  was arithmetic rather than a superseded finding.
- `attainable_lattice` is the float-rounding implementation and is the *source* of the 14116,
  not a second opinion about it. Its default `dp=12` is the branch that produces it.
- The *argument* never depended on the digit. It needs the N=40 lattice to be dense, and 14114
  against 14116 is the same claim. Nothing in section 2 moves.
- The **top decile** counts were stable throughout: 2 points at N=10, 7 at N=20, 42 at N=40.

At N=10 the gap between the top two attainable points is **0.138629 nats**, the next point down
is **2.025326**, leaving **0.277259 nats** of headroom from the cap. So at a success criterion of
delta = 0.25, every target sitting at 2.163956 has less headroom than delta and **cannot register
a success under any paraphrase**: the unwinnable set is the whole top decile, not just the
exact-ceiling cases, and at delta = 0.25 the two sets coincide exactly. All four of those figures
reproduced to the digit at every tolerance.

**Non-relaxability is withdrawn as FALSE.** 455 values at N=20 against 39 at N=10 is roughly
twelvefold, so granularity *is* relaxable. The honest residue, and it is the interesting half:
doubling N takes the top decile from **2 points to 7**, so the lattice stays sparsest exactly
where the false-alarm claim lives.

**Do not quote a distinct-value count as a finding.** "22 distinct values" was retired entirely:
it is a sample size, monotone in n. The lattice counts are not; they are enumerations of what the
estimator can emit at all. But see the N=40 row above for what a lattice count can still cost
you.

---

## 5. Findings still standing, and the two that moved on 2026-08-29

Deliberately **not** restated with their numbers where the artifact is authoritative. Each has
moved at least once.

| finding | owning artifact | status |
|---|---|---|
| ceiling saturation on the definitive `_defb` FA cell | `results/ceiling_saturation_finding.md` | **[CARRIED]** |
| crowding by stratum, Wilson intervals, CPU recompute | `results/achievable_fpr_grid.md`, `results/fair_pool_report.md` | **[CARRIED]** |
| asymmetric censoring, biases the clean AUROC *downward* | `results/fair_pool_report.md` | **[CARRIED]** |
| **winner's curse, now under `_defb`** | `results/winners_curse_se_false_alarm.md` (2026-08-30 09:54) | **MOVED, see below** |
| **judge validation** | `results/judge_validation.md` **plus** `results/judge_owed_conditions_run_2026_08_29.md` | **ARGUMENT OVERTURNED, see below** |
| replication, quote the greedy alias-aware span number | `results/n_scaling_grid.md` | **[CARRIED]** |
| the arithmetic the paper prints, input by input, with provenance | `results/derived_paper_quantities.md` | **[CARRIED]**, regenerated 2026-08-30 02:32 |
| **the definitive null control** | `results/null_control_report_defb.md` | **NEW, complete** |

**The null control, in one line, from the report itself.** 80/80 targets. On the pre-committed
claim statistic, the randomised-tie exceedance test whose null prices the attack's search budget
into the comparison, median `p = 0.9392` (NLI), `1.0000` (exact), `1.0000` (judge) over 101
tie-break realisations. **No arm rejects under any realisation.** On the supplementary paired net
under locked convention (d): NLI `+0.1097 [+0.0626, +0.1612]` nats, measured with the clusterer
the attack was optimised against; exact match `-0.0269 [-0.0637, +0.0146]`; **judge
`-0.1729 [-0.3023, -0.0394]`, entirely below zero.** The denominators are **n = 77** for the
paired net and the exceedance test and **n = 69** for convention (c), against 80 campaign
targets. **A reader must not read any of them as 80.**

**The winner's curse moved to `_defb`.** `_defb` (n = 69) gives **44.0% [23.2, 63.9]**, which is
the paper's figure. `_def` (n = 60) gave **45.2% [24.8, 65.3]** and is **RETIRED**, with a
`results/winners_curse_ckpt_se_false_alarm_def.jsonl.SUPERSEDED.json` sidecar, because a `.jsonl`
has no comment syntax and nowhere to put a banner. `scripts/winners_curse_reeval.py` now defaults
`--tag` to `_defb`. Verified 2026-08-31 by reading the argparse default at line 494.

**The judge's conservative reading is refuted in its stated form, and the argument for it is
wrong even though the conclusion survives.** From
`results/judge_owed_conditions_run_2026_08_29.md`, CPU-only, no GPU used. The worry was that the
judge over-splits and inflates the baseline. It does not: the deployed judge **under-splits**,
collapsing 34% of benign targets to K = 1. Three things follow and each is owed work:

1. `methods.tex` around line 305 and `limitations.tex` around line 72 need the sentence
   **rewritten**, not qualified. The conclusion holds; the mechanism given for it is false.
2. **A new anti-conservative mechanism is visible and the planned check is blind to it by
   construction**: a floored judge baseline on a third of targets bounds the FA move below by
   zero there, and `delta_bias` sees split-side error only. **Do not launch the planned judge-side
   run against the current design** (its price is in section 7 D1). Fix the estimand first.
3. **The judge arm's `-0.17` net must not be cited as evidence that the attack underperforms the
   null.** It compares an unselected attack observation against a best-of-50 selection on the
   judge arm. Index-matched it is `+0.02` with a CI spanning zero and a sign test at `p = 0.66`.
   Report the judge arm as **null**, or withhold it pending recomputation. This is listed in
   section 2's dead-claims block as well, because it is a live number that reads like a finding.

Two standing warnings that have each been "fixed" back by mistake before:

- The judge number **0.93** is the deployed symmetric config. A critic gate flagged it as drift;
  that ruling was wrong, was overruled, and the overrule was sustained. The **superseded**
  asymmetric run gave different figures. Do not "correct" it back.
- The replication comparison must use the **greedy alias-aware span** convention. The
  all-samples-correct label is *coupled to the score*: it calls a question correct iff all ten
  samples are correct, and SE is the entropy of the clustering of those same ten.

---

## 6. The guards, and what the suite says today

**[RE-DERIVED 2026-08-31, late]**, a full `.venv/Scripts/python.exe -m pytest -q` run, 69.87 s:
**2 failed, 1389 passed, 17 skipped, 1 warning.** An earlier run the same day reported
3 failed / 1220 passed; the third failure was `tests/test_n_scaling_grid.py` pinning the
float-rounding count 14116, which is now pinned exactly at 14114 and passes on both
platforms. The suite has gained 169 passing tests since that run.
**Re-run before quoting it. The count is stable only while nobody is editing, and the warning at
the top of this file says somebody is.**

The named guards, both run 2026-08-31:

- `.venv/Scripts/python.exe scripts/check_population_labels.py` : it exited **0** against the
  previous version of this document and exits **1** against this one, on a single
  `ratchet-stale` line. That is not a new defect: this rewrite cleared all three of the sites
  the register pins against this file, the register is one-way by design so a drop below the
  baseline also fails, and the fix is the paired one-line edit filed as **R12** in section 7.
  **Do not resolve it by reintroducing the three findings.** Re-read the failure text; it names
  the edit itself.
- `.venv/Scripts/python.exe scripts/check_latex_source.py` : **0 ERROR, 4 WARN**, exit 0. All
  four warnings are an unescaped `%` inside `annote` fields in `paper/related_work.bib` at lines
  142, 196 and 204 twice. `annote` is not typeset, so they are cosmetic. It also reports
  **33 bib entries, 33 distinct keys cited, 0 uncited, 8 labels defined / 8 referenced**. The
  citation count was 27/27 on 2026-08-26; the related-work round added six.

**Failures 1 and 2, in `tests/test_operational_provenance.py`, are the same site and are now
payable.**

> `scripts/overnight_2026_08_14.sh` carries 3 operational figures with no
> MEASURED / MODELLED / UNMEASURED tag, against a ratchet baseline of 0.

The previous version said this was "unpayable by anyone while the run is up", because that file
was the wrapper the live job was executing. **The run is over and the file is idle** (section 1),
so the fix is now available: tag those three figures in the script and the suite goes green
without anyone touching the register. It was **not** silenced by raising the baseline: the
checker prints "Do not raise the baseline to make this pass", the file entered the repo after the
register was struck, and a guard that gets widened the first time it is inconvenient is worth
nothing. Re-run `ps` first anyway.

**Failure 3 is NEW, it is a guard collision, and the guard is wrong rather than the paper.**
`tests/test_derived_paper_quantities.py::test_the_repo_is_green_today` reports:

> PAPER `leg_10_20_mc_retired`: `paper/sections/discussion.tex` contains again `8.8`.

It does, and the occurrence is legitimate. `scripts/derived_paper_quantities.py` registers the
retired Monte-Carlo rendering of the 10 -> 20 leg as the **bare substring** `"8.8"`, held down by
absence. The 2026-08-30 adjudication then required a prevalence sentence in that same file, and
the natural hallucination rate is **28.8%**, which contains `8.8`. Verified 2026-08-31: the only
`8.8` in any `.tex` file is `paper/sections/discussion.tex:92`, inside `$28.8\%$`, and both the
guard and the prevalence sentence are present at HEAD `59b5003`. **The paper is right and the
pattern is too loose.** `scripts/derived_paper_quantities.py` is owned by the closing round in
flight and may already be fixed; check before acting. **Do not "fix" this by deleting 28.8% from
the paper**, which is the move the guard's own wording invites and which would undo an
adjudicator-mandated correction.

That third failure has exactly the shape of the one the previous version of this file misread: a
guard went red on a *correct* edit, the red was recorded as a debt, and paying the debt would
have written the error. That misreading is where the withdrawn-estimator instruction in section 2
came from. **A guard that reports a change is not a guard that says which direction is right.
Read the ruling, not the red.**

`scripts/check_operational_provenance.py` is **red by design**: it reports open sites across the
repo. That is a debt ledger, not a failing grade. Its rules:

1. a **dead anchor** may not be restated in a live planning document without saying it is dead;
2. an operational figure must be **tagged** MEASURED / MODELLED / UNMEASURED, ratcheted per file;
3. a MODELLED figure must **name the anchor** it came from;
4. a MODELLED figure may declare `supersede-when: <path>` and fails once that artifact exists;
5. a **countdown** must be arithmetically true today.

Its live output on 2026-08-31 flags one stale countdown at `results/n_scaling_plan.md:113`: that
line states a fixed day count against a 2026-09-15 target, and the checker's own arithmetic says
the count is wrong today. That text is *generated*: the emitter is
`scripts/n_scaling_grid.py`, at **line 1011**, not the 996 the previous version of
this file named, which is itself an illustration of why this document now prefers grep anchors to
line numbers. **The repair is to stop emitting a hard-coded countdown at all**, not to change the
date to the next one that will go stale.

**What no checker can do is decide whether an anchor FITS.** That is failure type (d) in the
checker's docstring, and every error the original audit found was type (d). A tag can read
MEASURED and the measurement can be of the wrong thing. Read the docstring's closing list before
trusting a green run.

---

## 7. Owed, in priority order

The list below is rebuilt from scratch against `results/heavy_review_2026_08_30.md` and
`results/gemini_adjudication_2026_08_30.md`, which are the authoritative records for the review
rounds. It replaces an owed list that predated the completed null control, the 23-agent internal
review, the independent Gemini review and the adjudication.

**Note on `docs/critique_log.md`.** Its last entry is still **38**, dated 2026-08-19. The recent
rounds are recorded in `results/*.md` instead, so the critique log is no longer the place to look
for current state. Adding entries for them is itself owed, at low priority.

**Standing verdict on all of this, in the adjudicator's words: "no new experiment is required for
any of them."** Every must-fix item is prose, scoping or repository work.

### A. Paper, must fix before posting

A closing round was editing most of `paper/` while this was written (see the warning at the top),
so **check each item against the file before doing it.** Items verified as landed are marked DONE
with the file and the check that established it.

| # | item | where |
|---|---|---|
| M1 | The floor's dependence on the **equivalence oracle** must be scoped everywhere it is claimed. Table 1 prints the same estimand three times on the same 80 targets with only the equivalence relation varying: clean saturation **46.2% exact / 10.0% NLI / 1.2% judge**, Wilson intervals for exact and NLI non-overlapping. Claim the oracle-dependence, which Table 1 proves; **do not** claim "under the judge a 5% budget is feasible", because the judge figure is 1/80 with Wilson [0.22, 6.75], which does not exclude 5%. | **DONE in `discussion.tex` and `limitations.tex`**, verified 2026-08-31: `discussion.tex:114` now has a paragraph "The floor belongs to the whole detector, equivalence relation included", `:177` names the three determinants, `limitations.tex:219` matches. **Still owed in `main.tex` Abstract, `introduction.tex`, `conclusion.tex`.** |
| M2 | **`A = 181` is an upper bound presented as a value.** Redefine A as the number of *feasible* candidates the maximum ranges over; state it is partially observed (4703 of 14,400 children gated, pooled pass 3058/4703 = 0.650); report 181 as upper bound, the observed feasible count as lower bound, ~118 as point estimate. **Lead the defence with the judge arm's invariance**: `p_med = 1.000` at every A from 41 to 181. | `experiments.tex`, Table 1 block header |
| M3 | **Delete the three claims that do not survive M2**: that the exceedance total is above its null expectation "in all three arms"; Table 1's "0/101" and range "[0.229, 1.000]" as unconditional; "n_eff ~ 122 ... fewer than the budget it spent". | `experiments.tex`, `introduction.tex`, `conclusion.tex` |
| M4 | The **exact-match "strict lower bound" bracket**: true of the intended move, false of every quantity the paper concludes from. Five sites. | `methods.tex`, `experiments.tex` |
| M5 | The **prevalence paragraph**: add TPR 25.2% [21.8, 28.9] and prevalence 28.8%. | **DONE in `discussion.tex`**, verified 2026-08-31 at `:90-96`. This is the edit that trips the guard in section 6. |
| M6 | **Threshold-selection rule stated inverted.** "select tau as the *largest* threshold whose achieved clean FPR is at or below the budget"; FPR is non-increasing in tau, so the largest such tau never fires. The code is correct (`src/se/stats.py:940` documents `at_most` as "smallest"). **One word: largest -> smallest.** | `methods.tex` |
| M7 | **Fidelity bound direction reversed.** A lower bound on leakage is an **upper** bound on fidelity, and `limitations.tex` already says it correctly. | `methods.tex` |
| M8 | "the same population yields 28 at n=200 and 35 at n=2000" names **two different populations**. See section 3. | `introduction.tex` |
| M9 | Methods says the **hide cell is still filling**; it completed 2026-08-13. Replace the withholding clause with the count. | `methods.tex` |
| M10 | **No Data and Code Availability statement, no licence, no repository URL, no commit hash anywhere in the PDF.** Verified absent 2026-08-31 by grepping all eight `.tex` files, though `main.tex` was being edited at that moment and may have gained one since. For a paper whose contribution is measurement validity, this is among the first things a referee checks. **A drafted statement is already sitting in `ARTIFACT_AVAILABILITY.md` section 8**; this is a transcription, not a writing job. | `main.tex`, new paragraph |
| M11 | **Framing.** The Abstract tells the paper's story correctly and `introduction.tex` then takes it back with "independent of whether any attack succeeds", which severs the causal link the Abstract established. Gemini finished the whole paper still asking why it is framed this way, which is a referee reporting that the pivot did not land, not a request for information. The fix is a clause and a bridging sentence, not a new narrative. | `introduction.tex` |

### B. Paper, should fix

- **S1.** The **exact-match arm's rejection region is empty** on this data, so its `p = 1.000`
  corroborates nothing and must not be reported beside the others as independent confirmation.
  Power against ceiling saturation: 0.56 NLI, **0.00 exact**, 1.00 judge.
- **S2.** Per-target `A_j` rather than a scalar A. Three empty benign arms prove the gate rate
  varies enormously across targets.
- **S3.** Print counts rather than half-integers in the prevalence row. **DONE in
  `discussion.tex`**, verified 2026-08-31: it now reads "148 alerts per thousand (295 of 2000)".
- **S4.** Rewrite the judge's conservative-reading sentence in `methods.tex` and
  `limitations.tex`. Section 5, item 1. This one is a *mechanism* correction, not a hedge.

### C. Repository, before this is public

Each checked live on 2026-08-31 between 01:05 and 01:36, against a tree a closing round was
editing. **Re-check before acting.**

**Read `ARTIFACT_AVAILABILITY.md` first.** It is tracked at HEAD `59b5003`, was written
2026-08-30 against `fab9df1`, and already does most of the analysis this section only indexes:
what a clone can and cannot rebuild, which `.gitignore` lines exclude what, the hazards in what
does ship, a publication recommendation, and a draft availability statement for the paper that
M10 can be filled from. It also carries a repository item this handoff previously had nowhere:
`results/equivalence_audit_key.csv` is the *answer key* to the blinded equivalence sheet, it is
**already tracked**, and its blob is reachable from every commit after 2026-08-13, so publishing
this history publishes the key. Untracking it does not undo that. Sequestration means shipping a
snapshot or a squashed history. Do not treat a `.gitignore` line as the fix.

| # | item | status |
|---|---|---|
| R1 | Un-ignore and commit the load-bearing artifacts. | **PARTIAL.** `results/winners_curse_ckpt_se_false_alarm_defb.jsonl` is now TRACKED. Still ignored: `results/null_control_ckpt_defb.jsonl` and `results/n_scaling_ckpt.jsonl` by `.gitignore:102`, `results/diag_defb.json` by `:48`, `data/cache/attacks/wk9_defb_snap/` by `:47`. |
| R2 | Ship the Week-4 sample cache (`relabeled.jsonl`, `entropy.jsonl`; about 0.9 MB **[CARRIED]** from the adjudication, not re-measured here) or a release asset. **Every N=10 headline number is currently computable only from `~/.cache/se-research/samples/wk4_full_2000q/`, outside the repository tree.** Without this the headline is checkable by nobody. | **OWED.** No `relabeled.jsonl` anywhere under the repo. |
| R3 | Replace hard-coded `\\wsl.localhost` and `/home/abhi` paths with the `resolve_labels()` pattern (`--labels` flag plus `SE_RELABELED_JSONL` env var) that `achievable_fpr_grid.py` already implements. | **OWED. 14 files**, excluding `__pycache__`: `achievable_fpr_grid.py`, `crossing_test.py`, `likelihood_weight_sensitivity.py`, `make_ceiling_figures.py`, `make_floor_budget_figure.py`, `null_control.py`, `null_control_cost_options.py`, `null_control_defb_report.py`, `n_scaling_grid.py`, `overnight_2026_08_13.sh`, `overnight_2026_08_14.sh`, `overnight_queue.sh`, `recompute_fair.py`, `run_definitive_chain.sh`. |
| R4 | `scripts/winners_curse_reeval.py`: default tag to `_defb`, fix usage lines, mark or delete `_def`. | **DONE**, verified at line 494 and in the module docstring's tag gate. |
| R5 | SUPERSEDED banners on `results/wk6_hide_attack.md` and `results/wk7_false_alarm.md`, the two pre-B1 files still reporting the retracted 9/10 result unqualified. | **OWED.** Both still open with a bare `success ... 9/10` and no banner. |
| R6 | Rewrite `README.md` to the paper's position. | **DONE 2026-08-30 09:54.** It now says the false-alarm attack is not the headline and that nothing here is evidence against the paradigm. |
| R7 | Add a `LICENSE`. | **DONE 2026-08-30 09:52.** |
| R8 | Refresh `data/cache/attacks/wk9_defb_snap/` so its hide file carries the complete 80 records, or note in `SNAPSHOT.txt` that the cell has since completed. | **OWED**, and it now corroborates M9's false statement. `triviaqa_se_hide.jsonl` still has **52** records and `SNAPSHOT.txt` still says the file was being appended to at snapshot time. |
| R9 | The three untagged operational figures in `scripts/overnight_2026_08_14.sh`. | **OWED and now payable**, section 6. |
| R10 | Stop `scripts/n_scaling_grid.py:1011` emitting a hard-coded countdown. | **OWED**, section 6. |
| R11 | Add `docs/critique_log.md` entries for the null control, the review rounds and the adjudication. Last entry is 38, dated 2026-08-19. | **OWED**, low priority. |
| R12 | **Lower `KNOWN_OPEN['docs/START_HERE_overnight.md']` from 3 to 0 in `scripts/check_population_labels.py`.** This rewrite fixed all three pinned sites (two by removing the digit, one by naming the branch in the same sentence), and the register cannot be lowered from inside this file. Until the pin moves, `check_population_labels.py` exits 1 on a `ratchet-stale` line that reports *progress*, not a defect, and it names the exact edit. **Do not resolve it by putting the three findings back.** | **OWED, one line**, and it is the only reason that guard is currently red. |

### D. Needs something an editor cannot supply, and none of it blocks posting

1. **Judge condition (ii) proper**, validation on messy real sampled pairs, and `delta_bias`,
   which needs judge cluster *assignments* and the q' samples, both discarded.
   Price `3.1 GPU-h` [MODELLED, from the bracket at section 8 of
   `results/judge_owed_conditions_run_2026_08_29.md`, which labels itself a model rather than a
   measurement], with a 2.3 to 4.2 range at batch 6. **Fix the estimand first**, section 5
   item 2.
2. **The judge-oracle floor on the 1424.** M1 rests on 80 targets and the judge's clean at-cap
   rate there is 1/80, Wilson [0.22, 6.75], straddling 5%. Settling it means re-clustering the
   cached Week-4 samples under the judge: judge inference only, no generation, but not free.
   **This is what would let the paper say something about the judge oracle rather than merely
   scope the NLI claim.** It is not required for M1.
3. **Human equivalence audit. Needs a human, not a GPU.** The harness exists
   (`prepare_equivalence_audit.py`) and the blinded sheets are generated and tracked, but
   **[RE-DERIVED 2026-08-31]** by reading the CSVs: `equivalent_yes_no_unsure` is filled on
   **0 of 123** round-1 rows and **0 of 37** round-2 rows. Nothing has been annotated. This is
   also why `results/equivalence_audit_key.csv` must stay sequestered for now, section C.
4. **Regenerate `results/fair_recompute_report.md` from `_defb`. CPU.** Still dated 2026-08-13
   07:21 and still opening with its PRELIMINARY / EXPLORATORY banner, which says in terms that
   its numbers are not the confirmatory headline until reported net of the noise floor. The noise
   floor now exists: the null control landed on 2026-08-29.

### E. Conditional, only if promoted

- **The crossing test.** If it is ever promoted to a claim statistic: re-fix tau on a genuinely
  disjoint split, say which was used, and fix arm-exchangeability first. `feasible_objs` is a
  running-record subset, so any p from it is an upper bound on the evidence.
- **A negative control for the nesting check.** `verify_nesting` asserts the prefix property;
  nothing yet demonstrates it *failing* at another seed, so it is unproven as non-vacuous.

### F. What has no independent check at all

Recorded because the convergence between the two 2026-08-30 reviews is easy to over-read.

1. **Neither reviewer ran an experiment from scratch.** Both re-derived from checkpoints the
   original pipeline produced. A bug upstream of `null_control_ckpt_defb.jsonl` is inherited by
   every re-derivation in both reviews. Nothing there is a replication.
2. **A is not identified and cannot be identified from what was recorded.** The ungated candidate
   strings are not persisted anywhere.
3. **The judge-oracle floor on the 1424 is unmeasured.** D2 above.
4. **The judge's validation on messy real sample pairs remains owed.** The paper says so itself.
5. **Correlated blind spots between the two reviewers are unmeasured.** Both are language models.
6. **No human referee has read the paper.** Every finding in both reviews and in the adjudication
   is machine-generated.
7. **External validity is entirely unchecked.** One model family, one quantisation, one dataset.

---

## 8. Process rules, every one of them bought with an error

- **A correction is a claim, and carries the same burden as the thing it corrects, plus one.**
  Three corrections landed on the night of 2026-08-19 and two of them were wrong. One came from a
  critic gate that had reproduced the correction's own arithmetic and still shipped the error,
  because it measured a component's **magnitude** and inferred its **absence**.
- **"The critic approved it" and "the critic caught it" are the same kind of evidence, and
  neither is a safety property.** Twenty-three internal critics, an independent external review
  and five adjudicators have now passed over this paper, and the 2026-08-30 rounds still found
  ten must-fix items. Volume of review is not a correctness argument.
- **Check every gate ruling against the committed artifact before applying it.**
- **Before claiming two samples are independent, read the selector**, the code, not the names and
  not the design intent. That claim reached a pre-registration before anyone checked it.
- **Ask "monotone in n?" before any count enters a sentence.** A statistic that moves while you
  type it is a sample statistic, not a property.
- **Ask "stable under rounding?" of any exact-looking enumeration.** New on 2026-08-31. Section 4
  carried an N=40 lattice count under a heading saying the block could be quoted without
  re-checking, and the count moves by two depending on the float tolerance. A number can be pure
  arithmetic and still not be a fact.
- **Grep your own artifacts for the counterexample before publishing the claim.** The number that
  refuted non-relaxability sat in a corrections file for eleven days; the platform-dependence of
  the N=40 lattice count sat in `morning_review_2026_08_19.md` for twelve.
- **Never assert a property of your own script from memory.** Re-read it.
- **Sweep on numbers, not phrases.** LaTeX markup defeats phrase matching: a manual grep for a
  pool name missed a section because the source read `\emph{fair} pool`.
- **And sweep on the claim stated in words, with no digits, as a separate pass.** The rule above
  is necessary and not sufficient. Five rounds chased the N=40 interval by its renderings and each
  left sites behind, because **the misses do not sort by file, they sort by REPRESENTATION**:
  prose, an instruction to a future agent, a numeric tuple in a test, one file's assertion about
  another file's contents, a string literal inside a generator. Enumerate the representations
  first, then grep once per representation. `docs/critique_log.md` entry 38 is the long version.
- **A guard's pattern is a claim too, and a bare substring is the loosest kind.** New on
  2026-08-31. `"8.8"`, registered as a retired rendering held down by absence, now fires on
  `28.8%`, a correct and adjudicator-mandated number in the same file. A loose absence guard does
  not merely fail to catch things; it manufactures debts that look real, and the debt it
  manufactures is an instruction to delete correct text. Section 6.
- **A generator's prose can disagree with the generator's own code, and nothing will fail.** The
  figure script plotted the N=40 floor as a bare point for a week while its docstring said
  Wilson. Every artifact it produced was correct. Docstrings are read exactly when someone wants
  to know what the output means.
- **A green test suite next to a known-broken statistic reads as validation of it.** Pin the
  failure or delete the test.
- **A one-way register has to be lowered in the same commit as the fix that earns it.** New on
  2026-08-31, and this rewrite is the demonstration: clearing all three of this file's pinned
  population-label sites turns the guard red on a `ratchet-stale` line, because the register may
  not rot upward. That is the design working. The failure text names the edit; the wrong response
  is to restore the defects, and the pressure to do exactly that arrives at the moment the suite
  goes red. R12 in section 7.
- **Do not assert run state, read it.** Both directions have burned this project: a stale progress
  figure reported as current, and a false "nothing has been written in hours" that was a
  repo-scoped search missing the WSL cache. This rewrite adds a third: a finished run described as
  live, carrying an instruction to relaunch it.
- **Cite by anchor, not by line.** Section 2's pointers into `results/replay_control.md` had
  drifted about seven lines without the file changing. A line number is a claim about layout and
  decays faster than the number it points at.
- **Do not measure a moving artifact and print the reading as a fact.** The working-tree PDF gave
  three different page-and-overfull readings inside three minutes while a concurrent round was
  building it. Measure the committed blob, or wait.
- **Unmeasured claims are the worst failure mode.** The Abstract once asserted something that had
  never been measured, twice having pre-committed not to say it until it was.
- **A number printed under a heading that invites lifting will be lifted.** A retired fall sat
  under "What is worth carrying instead" and reached three briefings in one night. The same
  applies to a **[RE-DERIVED]** tag, which is a heading that invites lifting written at the level
  of a single number.
