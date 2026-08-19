# START HERE — current state, 2026-08-19 05:20 (overnight, round 2)

**27 days to the 2026-09-15 arXiv target.** 27 citations resolve (27 cite keys, 27 bib
entries, exact bijection). The overnight record is `docs/critique_log.md` entry **36**.

At 05:27 the suite was **997 pass / 7 skip / 3 fail** — but that count moved by 17 tests
inside twenty minutes while this was being written, because **three agents are editing
`paper/` and `results/` concurrently.** Re-run it; do not quote it:
`.venv/Scripts/python.exe -m pytest -q`. What the three failures *mean* is stable, and is in
section 6.

This document does not claim to supersede anything. It claims to be true at the timestamp in
its title, and it dates every number so you can tell how far that claim has travelled. The
previous version opened with "Supersedes every earlier version" while being six days stale in
four separate places, and it had been handing out wrong methodological guidance the whole
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

**A GPU run is live.** Verified from `ps` inside WSL at 2026-08-19 05:20, not from any brief:

| PID | what | elapsed |
|---|---|---|
| 457 | `bash scripts/overnight_2026_08_14.sh` (wrapper) | 04:28 |
| 473 | `.venv-wsl/bin/python scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 --dump_diag results/diag_defb.json --checkpoint auto` | 04:28 |
| 5751 | `bash scripts/stop_watcher_v2.sh` | 03:58 |
| 25204 | `bash scripts/watcher_supervisor_v3.sh` | 03:16 |

The distro is `Ubuntu-24.04`. Always `wsl -d Ubuntu-24.04`, never `wsl -d Ubuntu`.

**Progress, from the checkpoint itself** — `results/null_control_ckpt_defb.jsonl`, counted as
distinct `question_id`, 0 torn lines:

- **[LIVE]** 23 of 80 false-alarm targets complete at 05:20; 57 remaining.
- **[LIVE]** rate 1109 s/target over the last 5 targets [MEASURED from `dashboard/progress_status.json`, checkpoint mtime deltas, 11 targets timed this session].
- **[LIVE]** rate 1164 s/target over all targets timed this session [MEASURED from the same block, `all timed targets this session`].
- **[LIVE]** remainder therefore about 17.6 to 18.4 GPU-h [MEASURED, 57 targets x the two rates above], i.e. finishing roughly 23:00-23:45 today.

Two cautions on that remainder, both of which have already cost this project a decision:

1. It is **wall clock**, measured from file mtimes. It is quoted as GPU-hours because this run
   is the only consumer of the device; those are not in general the same quantity.
2. It is a **measurement that ages**, and the clearest example is on screen right now: the
   header of the running script quotes "~25 GPU-h at 1191 s/target x 69 remaining" [MEASURED when it was written, and already stale — 57 remain, at a faster rate].
   Measurements rot too. A MEASURED tag says where a number came from, never how old it is.

**The retired figure for this same job was ~67 GPU-h** [MODELLED from the K=8 probe in `docs/critique_log.md` entry 22, then spent on a K=50 run at a different judge batch size; superseded].
That number must not re-enter any planning document. The previous version of this file carried
it on line 197 as a live cost, which is the path by which it reached the overnight queue.

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

## 2. The surviving headline, and the twin that will try to replace it

**[RE-DERIVED]** from `results/replay_control.md`, the floor row of the table at line 173 and
the paired-difference table at line 205:

| statistic | direct N=10 (do not mix) | replay N=10 | replay N=20 | measured N=40 |
|---|---|---|---|---|
| floor, min non-zero achievable FPR (MATCHED) | 9.5% [6.2, 14.4] | 12.0% [8.9, 15.3] | 3.1% [1.8, 4.7] | 2.0% [0.8, 5.0] |

The claim is the **fall across sample budgets within uniform provenance**: replay N=10 to
measured N=40 is **-10.0 points [-12.9, -7.2], excluding zero**. The paper keeps
**9.5% [6.2, 14.4]** as its own N=10 floor, because every other N=10 number in the paper is
welded to the same June cache; the replayed 12.0% is what the budget comparison runs on.

### The ways this section gets quoted wrong

**(a) The superseded fall.** `results/replay_control.md` still prints
**-9.9 points [-15.5, -5.0]** at lines 263-264 and again at 626-629, the second time under the
heading *"What is worth carrying instead"* — the exact section a reader lifts from. It is
**superseded**; the live matched value is -10.0 points [-12.9, -7.2]. The same paragraph also
prints the retired floor triple "11.9% -> 3.0% -> 2.0%"; the live triple is 12.0 / 3.1 / 2.0.
That dead figure propagated into three separate briefings on the night of 2026-08-19. It is
not a rounding difference — the interval is materially wider and the point estimate is off.
**Check line 205 before quoting either.** (Those lines are in `results/`, which this session
did not own; they are still live as written.)

**(a2) The N=40 floor's interval is being changed right now, and the artifact has not caught
up.** As of 05:27 `paper/sections/discussion.tex` prints the measured N=40 floor as
**2.0% [0.5, 4.0]**, while the table quoted above in `results/replay_control.md` still prints
**2.0% [0.8, 5.0]** for the same cell. This is not a contradiction to fix by picking one: the
paper argues, at length and coherently, that the N=40 floor is **outside Wilson's reach**,
because its threshold is not fixed in advance — it is the top score *this* sample attained, so
both which answers count and how many of them there are move under resampling — and it
therefore takes the same question bootstrap as the paired fall. Wilson is kept only for the
two rows that really are counts at a threshold fixed before the data. **The headline fall,
10.0 points [7.2, 12.9], is unchanged by this.** What is owed is a regeneration of
`results/replay_control.md` and an update to the expected literal in
`scripts/derived_paper_quantities.py`, which is what the third suite failure is reporting.

**(b) The AUROC row that looks alive.** In that same table, `direct10 -> measured40` gives
AUROC **+0.0412 [+0.0064, +0.0767]**, which excludes zero and reads like a finding. It is the
one comparison that **mixes provenance** — the column is labelled "do not mix" — and
AUROC-vs-budget is one of the two claims that **died on their merits** tonight. Inside the
uniform-provenance replay family every AUROC, pAUC and TPR difference covers zero. The rows
are in the file only so that the refutation is checkable like-for-like.

### Dead, and dead in both directions

These must not re-enter in any form, **including inverted**:

- **AUROC-vs-budget.** Dead on its merits.
- **Cross-budget TPR / pAUC.** Dead on its merits. Every interval covers zero.
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

## 4. The lattice — re-derived tonight, by enumeration

**[RE-DERIVED]** on 2026-08-19 by enumerating integer partitions and computing
`-sum (c/N) ln(c/N)` directly. This is pure arithmetic, independent of any run, any
population and any n, so it is the one block in this file you may quote without re-checking:

| N | partitions p(N) | distinct SE values | coincidences | cap ln(N) | values in top tenth |
|---|---|---|---|---|---|
| 10 | 42 | **39** | 3 | 2.302585 | **2** — 2.163956 and 2.302585 |
| 20 | 627 | **455** | 172 | 2.995732 | **7** |

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

Three failures at 05:27 [RE-DERIVED — full `pytest` run, 2026-08-19]. They are not the same
kind of thing, and only the first two are this section's subject.

**Failure 3 is somebody else's, and it is doing its job.**
`tests/test_derived_paper_quantities.py::test_the_repo_is_green_today` reports that
`paper/sections/discussion.tex` no longer contains the literal
`a measured $2.0\%$ [$0.8$, $5.0$] at $N{=}40$`. That is the live edit described in section
2(a2): the interval was deliberately moved from Wilson to a question bootstrap. The guard is
correctly reporting that a registered literal moved; the owed action is to update the expected
literal in `scripts/derived_paper_quantities.py` and regenerate. **Do not "fix" the paper back
to the Wilson interval** — the paper carries the argument for the change and the guard does
not.

**Failures 1 and 2** are both in `tests/test_operational_provenance.py` and both name the same
single file:

> `scripts/overnight_2026_08_14.sh` carries 3 operational figures with no
> MEASURED/MODELLED/UNMEASURED tag, against a ratchet baseline of 0.

That file is on the do-not-edit list **and is PID 457 above**. The debt is real, it is
recorded, and it is unpayable tonight by anyone. It was **not** silenced by raising the
baseline: the checker prints "Do not raise the baseline to make this pass", the file entered
the repo after the register was struck, and a guard that gets widened the first time it is
inconvenient is worth nothing. **When the null control lands and the no-edit rule lifts: tag
those three figures in the script, and the suite goes green without anyone touching the
register.**

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
- **A green test suite next to a known-broken statistic reads as validation of it.** Pin the
  failure or delete the test.
- **Do not assert run state — read it.** Both directions have burned this project: a stale
  progress figure reported as current, and a false "nothing has been written in hours" that
  was a repo-scoped search missing the WSL cache.
- **Unmeasured claims are the worst failure mode.** The Abstract once asserted something that
  had never been measured, twice having pre-committed not to say it until it was.
- **A number printed under a heading that invites lifting will be lifted.** See section 2(a).
