# Morning decision list — 2026-08-19

## If you read nothing else

1. **Today, and only today: decision 3 — human equivalence audit, round 1.** The one
   calendar-locked item here; 27 days does not fit two audits.
2. **Yours to judge this week: decision 2** (the spine — keep it), **decision 5** (soften two
   claims — untouched for a third night), **and one cut**: the Abstract is ~100 characters over
   arXiv's 1920-character abstract field and would be rejected by the submission form today.
3. **Decision 4 moved. Do not plan around 22:45** — the run now lands **00:33 tomorrow**.
4. **Decisions 1, 6, 8 and 9 are closed**; 8 by a simulation whose arithmetic I re-derived myself.
5. **Decision 10 is new and needs an agent before you spend any time here, not you:**
   `docs/START_HERE_overnight.md` still tells the next session to adopt the withdrawn estimator.

---

*Refreshed 07:50 after a **fourth** overnight round. Three earlier versions of this file (03:06,
05:06, 05:52) are superseded. Decisions 1, 6, 8 and 9 are now **done**; one new item, decision
10, is the residue the round-4 pass left behind. Everything below was re-derived against the
files as they stand at 07:50, not against any agent's report.*

27 days to the arXiv target. Four rounds of agents worked overnight. Round 1 landed the paper
edits and cleared the gate's BLOCK; round 2 found round 1's interval correction inverted and
fixed it; round 3 applied four assigned fixes to `paper/`, regenerated `results/replay_control.md`,
and closed the ratchet debt; round 4 ran the coverage simulation decision 8 was waiting on,
took the ruling, and applied it across the paper and its generators in one pass.

**`pytest` is now 2 failed / 1014 passed / 15 skipped / 1 warning** — I ran it. That is *one
fewer* failure than the 3/997/7 this file reported at 05:52; the regression round 3 opened is
gone, and both survivors are the one pre-existing site (`scripts/overnight_2026_08_14.sh`,
which is do-not-edit) reported twice by `tests/test_operational_provenance.py`. All three
checkers behave as designed: `check_population_labels.py` exit 0, `check_latex_source.py` exit 0
(0 ERROR / 4 pre-existing WARN), `check_operational_provenance.py` exit 1 on that same script.

The run is alive: **30/80 done**, ETA **2026-08-20 00:33** — nearly two hours later than the
05:45 projection, and this one is a real slowdown, not a basis artefact. See "what is running
now". Nothing on this list needs the GPU or the run state.

**Read this first.** Round 4 closed decision 8 and it closed it well: the N=40 floor now carries
**no interval at all**, the Abstract asserts that the *obstruction* is gone rather than that an
interval clears 5%, and the eight `.tex` files are consistent — I grepped them and re-derived the
numbers. What it did not do is finish. Two verifiers, working independently, found **seven sites
still carrying the retired value or the retired argument, five of them in files the pass itself
owned or edited** — including the one table in the repo whose entire job is to say which interval
belongs to which estimator, and the live handoff document. That is decision 10, and it is
mechanical: no judgement of yours is needed, only that it happens before another agent reads
`START_HERE`.

| # | Decision | When | My recommendation |
|---|---|---|---|
| 10 | Round 4's residue: seven sites still carry the retired interval or the retired argument, two of them actively propagating | **before another agent runs** — not before you work | Mechanical, ~30 min, needs an agent and not your judgement. Start with `START_HERE` |
| 3 | The human equivalence audit | **today** — the only calendar-locked item | Start round 1 this session. Drop the second audit |
| 2 | The paper's spine | today, before any rewriting | **Keep the current spine.** Unchanged, and now better supported still |
| 5 | Two claims repeating the project's named failure mode | this week | Soften both. **Untouched by rounds 3 and 4**; 5a still contradicts itself inside one paragraph |
| 4 | The LaTeX toolchain | this week | Option A (WSL apt), but the run now lands **00:33 Thursday**, not 22:45 tonight |
| 7 | The `24.0` quarantine collision | 2 min | Leave it out. No exemption |
| ~~1~~ | ~~Abstract + Conclusion assert an existence claim~~ | — | **CLOSED overnight (round 3).** See "what changed while you slept" §1 |
| ~~6~~ | ~~`replay_control.md` prints the retired trend~~ | — | **CLOSED overnight (round 3).** Verified: the retired strings are gone |
| ~~8~~ | ~~The N=40 floor carries three intervals; the concession inverts depending on which~~ | — | **CLOSED overnight (round 4)**, by a coverage simulation and option (C). Verified |
| ~~9~~ | ~~`fig_floor_budget` is referenced nowhere and encodes the losing side of decision 8~~ | — | **CLOSED overnight (round 4).** Regenerated, repointed, and now included at `discussion.tex:187` |

---

## Decision 8 — CLOSED overnight (round 4). Settled by simulation, applied in one pass, and re-checked. No action needed.

**The ruling.** `results/n40_floor_estimator_ruling.md` (06:32). The paper prints **no interval**
on the measured N=40 floor. It prints the point, $2.0\%$, as the cheapest rate a 200-answer pool
can *exhibit*, and beside it the quantity that does carry an interval — the **at-cap mass at
$\ln 40$, $0.0\%$ [$0.0$, $1.9$]** (Wilson on 0 of 200, at a threshold fixed before the data).
Neither `[0.8, 5.03]` nor `[0.5, 4.0]` appears anywhere in `paper/`. The Abstract no longer says
the interval does or does not clear 5%; it says the **obstruction** is gone — at N=10 the floor
is a full ceiling atom, so the budget is unbuyable at any threshold, and at N=40 the atom is
empty and what is left is a limit on measurement resolution, not on achievability.

**Why neither estimator, rather than one of them.** This is the part I want you to be able to
defend at a referee, so here is the evidence rather than the conclusion. 40,000 simulated pools
of 200, three seeds, nominal 95%, against a population model fitted at N=40:

| budget | true floor | Wilson coverage | bootstrap coverage |
|---|---|---|---|
| N=10 (atom full) | 11.86% | 95.1% | 94.8% |
| N=20 (atom full) | 3.13% | 96.2% | 98.4% |
| **N=40 (atom empty)** | **0.27%** | **53.7%** | **0.00%** |

Neither estimator is broken. The **estimand** dissolves at the moment the atom empties, and both
candidates then have an endpoint placed by construction: the bootstrap's $0.5\%$ lower end is
1/200, the statistic's support boundary, and it exceeds the true floor in 100% of pools. So
objection 2 from the 05:52 version of this file was right, and objection 1 bites in a way that
resizing the bootstrap cannot fix. **The Discussion's own argument for the bootstrap was
inverted** — it read a fact about the estimator's range as a fact about the population — and that
argument has been replaced rather than propagated. The opposite ruling was made on the achieved
5%-budget row, which is an interior quantile and not a boundary case: it keeps Wilson
$5.0\%$ [$2.7$, $9.0$] (94.4% coverage) and retires the bootstrap `[2.5, 5.0]` (54.8%, upper end
pinned at the budget in 100% of pools). Two rulings in opposite directions, for a stated reason.

**What I checked myself, with my own code, importing nothing from the project.** Wilson from the
closed form: 0/200 = [0.0000, 1.8845], 3/200 = [0.5114, 4.3166], 4/200 = [0.7804, 5.0287],
10/200 = [2.7383, 8.9578], 19/200 = [6.1663, 14.3602], 150/1424 = [9.0440, 12.2357] — every one
matches. From `results/n_scaling_ckpt.jsonl` directly: 400 records, 200/200 split,
$\ln 40 = 3.6888794541139363$, maximum attained entropy $3.6195647360579453$, **0 of 200 at the
cap**. The four tied answers are really *three* on a raw comparison — the fourth sits one ULP low
(gap $4.44\times10^{-16}$) and only a 9-dp snap merges it. **The ruling does not depend on 3
versus 4, which is the reason to take it:** the old framing made the Abstract's claim turn on
floating-point addition order. And the headline legs, which I recomputed exactly rather than by
Monte Carlo — "all singletons" means the chosen subset is an independent set of the question's
verdict graph, so each question's saturation probability is a ratio of independent-set counts and
needs no sampling at all: **N=10 floor 11.992117%, N=20 floor 3.129089%, N=40 at-cap 0%.** The
10→20 leg is **−8.863028**, which is **8.9** at one decimal and not 8.8. Printed legs
$8.9 + 1.1 = 10.0$ and the exact plug-ins $-8.863 + -1.129 = -9.992$ agree; nothing was rounded
into place.

**What I took on trust:** the coverage simulation itself (I did not re-run 40,000 pools), the
Ewens population model behind it, the recorded DeBERTa verdict bits, and the fair pool's
score-independent construction.

**One caveat, disclosed rather than buried.** A verifier reproduced the ruling's population model
to the digit and found it **mildly misfit in exactly the region that decides the answer** — it
predicts 0.55 and 1.59 questions at K=40 and K=39 where 0 are observed, so the true floor may sit
above the model's 0.27%. The ruling states this itself in its §5. It does not move the ruling,
and the reason is the sensitivity sweep in its §8, which is anchored on the two atoms I
re-derived exactly above: for the true floor to be as high as Wilson's own lower end, 0.78%, the
N=20 atom would have to be 5.03% against a measured 3.129% [1.79, 4.69]; for it to be the printed
2.0%, the N=20 atom would have to be 8.46%. Both are ruled out by measurements this paper already
has. **The ruling's conclusion survives its model being somewhat wrong, which is the only kind of
robustness worth having here.**

**Two things worth knowing that came out of the pass, neither of which needs you.**
The 5%-budget point is optimistically biased by about half a point (4.67% in sample against 5.17%
deployed on fresh data) — that is a Limitations sentence, not a correction. And the pre-registration
this ruling leans on, `results/n_scaling_plan.md`, **mislabels its own criterion in two places**
(:309-311 and :403-404) — it describes a Wilson upper bound *under* 5%, which certifies that an
operating point at or below 5% **does** exist, as though it certified that none does. Only :425
states the intent correctly. The paper does not inherit the error; the plan should be corrected
before anyone cites it, and that belongs with decision 10.

---

**The record, as this file had it at 05:52, follows. It is superseded — read it only if you want
the reasoning the ruling was answering.**

**What must be decided:** which interval, if any, the paper prints beside the measured N=40
false-alarm floor of $2.0\%$.

**What is written right now.** I grepped all eight `.tex` files myself rather than taking the
verifier's list:

| file:line | prints | estimator |
|---|---|---|
| `paper/main.tex:49` | `2.0\% [$0.8$, $5.03$]` | Wilson on 4/200, 2 dp |
| `paper/sections/conclusion.tex:23` | `2.0\% [$0.8$, $5.03$]` | Wilson on 4/200, 2 dp |
| `paper/sections/introduction.tex:97` | `2.0\% [$0.8$, $5.0$]` | Wilson on 4/200, 1 dp |
| `paper/sections/discussion.tex:139` | `2.0\% [$0.5$, $4.0$]` | question bootstrap |
| `paper/sections/discussion.tex:173` | **both**, side by side | — |
| `paper/sections/limitations.tex:184` | `2.0\%`, no interval | — |

Outside `paper/` the Wilson reading is also in `scripts/derived_paper_quantities.py:156,159`,
`results/derived_paper_quantities.md:39,40,208`, `results/replay_control.md:349` (which prints
both columns), `results/n_scaling_grid.md:22`, `figures/fig_floor_budget_data.csv`,
`figures/fig_floor_budget_stats.json`, `scripts/make_floor_budget_figure.py:122`,
`tests/test_derived_paper_quantities.py:54` and `docs/START_HERE_overnight.md:102`.

**It is why the suite is red.** I ran it and read the failure rather than inferring it. Three
`PaperClaim`s (`n40_floor`, `n40_floor_lo`, `n40_floor_hi`) pin the literal string
`a measured $2.0\%$ [$0.8$, $5.0$] at $N{=}40$` in `discussion.tex`; `discussion.tex` was
rewritten to `[$0.5$, $4.0$]` at 05:26, after the generator was last regenerated at 04:38.
`tests/test_derived_paper_quantities.py::test_the_repo_is_green_today` is the new third failure.
**This is the guard working exactly as designed** — it caught a cross-file inconsistency within
the hour. Do not silence it; resolve the row.

**Why this is worse than a formatting inconsistency.** The Abstract's concession is
*"whose interval does not exclude $5\%$."* Wilson's upper end is $5.029 \to 5.03$: over the line,
so the concession is **true**. The bootstrap's upper end is $4.0$: under the line, so the
concession is **false** — and the paper would then be conceding something its own interval
refutes. The sentence's truth value is decided by an estimator choice made in a different file.

**What I checked myself, and what I did not.** I recomputed Wilson from the closed form:
4/200 = 2.0000% **[0.7804, 5.0287]**; also 0/200 [0, 1.8845], 10/200 [2.7383, 8.9578],
19/200 [6.1663, 14.3602], 3/200 [0.5114, 4.3166], 150/1424 [9.0440, 12.2357]. Every one matches
what the paper prints. I did **not** re-run the bootstrap; `[0.5, 4.0]` is on trust from two
agents who report it stable at 400k resamples across four seeds.

**The argument the Discussion makes for the bootstrap, and the two objections nobody has
answered.** `discussion.tex:168-175` argues Wilson is the wrong estimator because its threshold
must be fixed before the data, whereas the N=40 floor's threshold is the top score *this* sample
attained, so both which answers are counted and how many of them there are move under
resampling. **That argument is correct and it is the reason not to simply revert.** But:

1. **The n-out-of-n bootstrap is not consistent for functionals of the sample maximum.** This
   floor is "the count of answers tying the sample max, over 200" — precisely the class where
   the naive bootstrap is known to fail, because a resample re-uses the same finite set of
   attained maxima. This is textbook, not something I derived here, and *it has not been checked
   against this statistic.* **The check that would settle it costs an hour of CPU:** simulate
   from a generative model whose true floor you set, draw 200 questions, and measure whether the
   bootstrap interval covers at 95%. If it under-covers, `[0.5, 4.0]` is too narrow and the
   Discussion has replaced a wrong interval with a differently wrong one.
2. **The bootstrap's lower end, $0.5\%$, is the statistic's support boundary, not evidence.** On
   200 questions at least one always attains the max, so the floor can never be below 1/200. The
   Discussion cites Wilson's exclusion of $0.5\%$ as a defect — but $0.5\%$ is special only to
   the *statistic*, not to the *parameter*; a larger correct stratum can have a floor below it.
   An interval pinned at its own support floor is uninformative there, and using that pinning as
   an argument conflates the two.

I am raising both as open, not as a refutation. Objection 1 is checkable and cheap; objection 2
is an argument and you may disagree with it.

**Options.**

- **(A) Bootstrap everywhere.** Propagate `[0.5, 4.0]` to `main.tex:49`, `conclusion.tex:23`,
  `introduction.tex:97`, then `scripts/derived_paper_quantities.py:253-255` *and* its Wilson
  cross-check at `:598-599`, `results/n_scaling_grid.md:22`, `results/replay_control.md`,
  `results/derived_paper_quantities.md`, and the figure triple. ~45-60 min across 7 files and
  two generators. **It also makes the Abstract's own concession false**, so the Abstract has to
  be rewritten anyway — which is most of option (C)'s work on top of all of (A)'s.
- **(B) Wilson everywhere.** Revert `discussion.tex:139` to `[$0.8$, $5.0$]`, keep `:168-175` as
  a caveat. ~10 min, suite goes green with no generator change. **Cheapest and wrong**: it
  re-installs the interval the Discussion argues at length is the wrong estimator, and it does
  so the same night that argument was written.
- **(C) Make the concession estimator-free, and print both intervals only where the argument
  lives.** The Abstract and Conclusion stop printing an interval on this row and rest the
  concession on the pre-registered criterion instead — *the plan required the cheapest firing
  threshold to flag at most three of the 200; it flags four; we do not certify it.* That is a
  count, it is exactly what was pre-registered (`n_scaling_plan.md` §6/§8), and it is true under
  every estimator. `discussion.tex:173` already prints both and claims neither — that policy just
  needs to propagate as *"no interval outside the Discussion"* rather than as *"one interval,
  chosen elsewhere."* Introduction takes the same treatment. ~25 min.

**RECOMMENDATION: (C).** It is the only option whose correctness does not depend on settling a
statistical question this project has not settled, and the Discussion has already written its
own policy for exactly this case — "we print both and claim neither as the pre-registered
certificate." The defect is that the policy was applied in the file where it was written and
nowhere else. Then run the coverage simulation from objection 1 as a background CPU job; if the
bootstrap survives it, option (A) becomes available later at leisure and nothing you ship today
has to be retracted.

**One thing not to do:** do not re-baseline `test_the_repo_is_green_today` to accept three
failures. The guard is reporting a real inconsistency, and this is the second time in two nights
a ratchet has been asked to absorb a defect instead of reporting it (see checklist item 5).

---

## Decision 9 — CLOSED overnight (round 4). The figure was regenerated, repointed and included.

**Verified at 07:50, by running the linter rather than reading the report.** `check_latex_source.py`
now resolves **two** figures, not one: `fig_achievable_roc` at `discussion.tex:90` and
`fig_floor_budget` at `discussion.tex:187`, referenced from the ladder paragraph at `:150` and
labelled at `:198`. The sidecar was rebuilt: it computes the floors exactly rather than by
Monte Carlo (the dead `--draws` flag is gone), it plots the N=40 bar with **no error bar**, and
its `source_of_record` is now the checkpoint plus the ruling, with `discussion.tex` listed as a
file checked *against* the figure rather than as the figure's source. Its re-derived floors,
11.992 and 3.129, match my own exact computation to three decimals. One stale sentence remains
inside it — see decision 10, item 5.

**The record, as this file had it at 05:52, follows.**

**New tonight.** `figures/fig_floor_budget.pdf` / `.png` / `_data.csv` / `_stats.json` were
generated at 04:38 by `scripts/make_floor_budget_figure.py` (all five files untracked). The
sidecar is good work — it records population, seed 20260819, 200,000 bootstrap resamples,
20,000 subset draws, and re-derives every plotted value. I read it.

Two problems, both mechanical:

1. **It is referenced nowhere.** I ran `check_latex_source.py`: it resolves exactly one figure
   across all eight `.tex` files, `fig_achievable_roc`. The paper still ships one figure.
2. **Its `source_of_record` names `paper/sections/discussion.tex`** — the one file that no longer
   agrees with it. `plotted_floor` is `[2.0, 0.8, 5.0]` and the CSV row says
   `2.0,0.8,5.0,Wilson on 4/200`. Discussion says `[0.5, 4.0]`.

**RECOMMENDATION: decide 8 first, then regenerate the figure from the decision and include it in
`discussion.tex` where the ladder paragraph already is.** Do not include it as-is. If decision 8
lands on (C), the figure should carry both intervals on the N=40 bar or none.

---

## Decision 10 — Round 4's residue: seven sites the single-owner pass did not reach [NEW — needs an agent, not you]

**What this is.** Round 4 was deliberately organised as the opposite of round 3: one agent given
the *whole* surface for one change, precisely so that no fix would stop at a file boundary again.
It still stopped. Two verifiers working independently — one auditing the pass's own hit list,
one re-deriving the paper from the primary checkpoint with its own code — found seven sites
still carrying the retired value or the retired argument. **Five are in files the pass owned or
edited.** I confirmed all seven myself, by reading the lines.

**The two that actively propagate the defect.** These are why this has a "before another agent
runs" deadline rather than a "this week" one.

1. **`docs/START_HERE_overnight.md` — the live handoff, and the worst of the seven.** Three
   places. Its `[RE-DERIVED]` headline table at `:102` still prints `2.0% [0.8, 5.0]` for the
   measured N=40 cell and sources it to `results/replay_control.md`, which now prints
   `2.0% (no interval -- see 2c)`. Its §2(a2) at `:123-131` states the *superseded* position in
   prose — that the floor "is outside Wilson's reach" and "therefore takes the same question
   bootstrap as the paired fall" — and then **instructs the next agent** that "what is owed is a
   regeneration of `results/replay_control.md` and an update to the expected literal in
   `scripts/derived_paper_quantities.py`", i.e. toward the estimator the ruling withdrew at
   **0.00% measured coverage**. And §6 at `:248-258` describes a three-failure suite that no
   longer exists, including a failure it tells the reader not to "fix". A fresh agent handed this
   document would undo the night's work and believe it was paying a debt.
2. **`results/replay_control.md:344`, generated from `scripts/replay_control.py:1512`.** The
   table headed *"Which interval goes with which estimator"* — the one table in the repo whose
   entire job is that mapping — still reads `| the measured N=40 floor | the questions only |
   Wilson on the count; the question bootstrap only for PAIRED differences |`. It contradicts its
   own file's banner 340 lines above, its own corrected floor table 13 lines below at `:357`
   (`**none -- withdrawn, see 2c**`), its own §2c, and the paper. It is hard-coded in the
   generator, so **regenerating does not fix it**, and no test covers it: the existing guard
   matches only `X% [a, b]` renderings, and this row is prose.

**The three quieter ones.**

3. **`tests/test_derived_paper_quantities.py:54`** parametrises
   `(4, 200, 2.0, 0.8, 5.0),  # the cheapest firing threshold at N=40` inside a test named
   *`test_wilson_reproduces_every_interval_the_paper_prints`*. The paper prints no interval for
   that count any more. The assertion is pure arithmetic on `wilson()`, so it is **permanently
   green and structurally incapable of reporting the discrepancy** — this is the same defect
   class as critique entry 35. Three reasons it was missed are worth naming: the file is
   untracked, so `git diff` on it is empty; it encodes the retired choice as a numeric tuple
   rather than a string, so the pass's eight new `present=False` literal claims cannot see it;
   and `check_population_labels.py`'s scope is the eight `.tex` files, so the linter cannot
   reach `tests/` at all.
4. **The two new paired-difference legs are pinned by nothing.** `discussion.tex:145-147` now
   prints $8.9$ points [$6.8$, $11.1$] and $1.1$ points [$-0.2$, $2.4$], and neither has a
   `PaperClaim` in `scripts/derived_paper_quantities.py` — only `fall_points` and
   `replay10_floor` do. That matters more than it sounds: the pass **wrote one of these wrong
   once already tonight** (it computed the 20→40 leg as $[-0.2, 2.5]$ by resampling a fixed
   top-4 indicator instead of re-finding the top score inside each resample, then caught itself
   and reverted), and the 11.05 lower endpoint is a documented coin flip at one decimal. Two
   numbers with that history should not be the only unguarded ones in the paragraph.
5. **`results/replay_control.md:203`** still prints the 10→20 leg as `-8.8 pts [-11.0, -6.8]`
   against the paper's and the figure's `8.9 [6.8, 11.1]`. §2c discloses the *point* discrepancy
   and says explicitly not to correct the paper down to 8.8 — but says nothing about the lower
   endpoint, so `-11.0` sits there unmarked, which is the exact value
   `make_floor_budget_figure.py:159-161` warns must not be adopted. Related cosmetic: the figure
   sidecar's `not_the_source_of_record` note claims `replay_control.md`'s N=40 floor "still
   carries the withdrawn Wilson interval". It does not, and that sentence is in the generator, so
   it survives regeneration too.

**RECOMMENDATION: hand all five to one agent as a single change, and require it to report a
before/after grep for each site rather than a description.** ~30 minutes. Do `START_HERE` first
and on its own, because until it is fixed every *other* agent you launch inherits the wrong
instruction. **None of this touches the paper** — I re-grepped all eight `.tex` files and no
`5.03`, `[$0.78$, $5.03$]`, `[$0.8$, $5.03$]`, `[$0.8$, $5.0$]` or `[$0.5$, $4.0$]` survives, all
four 5%-budget sites print `5.0% [2.7, 9.0]`, and the at-cap `0.0% [0.0, 1.9]` reproduces from
`wilson(0, 200)`. **The paper is correct this morning.** What is wrong is the scaffolding that
tells the next agent what the paper says.

**Do not let the guard layer be the fix on its own.** The pass's response to being wrong about
literals was to add eight more literal patterns. That is the right move and it adds no coverage
against any of the five above, because none of them is a literal in a `.tex` file. See critique
log entry 38.

---

## Decision 1 — CLOSED overnight (round 3). Kept as a record, no action needed.

The Abstract and Conclusion no longer assert that a 5% operating point *exists*. I verified this
by reading the files, not the report. `main.tex:49-52` now reads "…the floor is an ordinary order
statistic, $2.0\%$ […], whose interval does not exclude $5\%$. The threshold that honours a $5\%$
budget achieves $5.0\%$ [$2.7$, $9.0$] on those same $200$ answers, **which we report as a
measured operating point and not as a demonstration that one at or below $5\%$ exists.**"
`conclusion.tex:23-29` carries the same conversion and states the criterion in place, so the
`\ref{sec:discussion}` pointer is no longer load-bearing. `introduction.tex:82-85` uses the
measured-operating-point form. No site in `paper/` asserts existence.

Two things the acting agent did that are worth knowing, because they are judgement calls you may
want to reverse:

- **It prints `[$0.8$, $5.03$]`, breaking the paper's 1-dp house style,** on the ground that at
  this one site 1-dp rounding turns the digit the concession depends on into its own refutation.
  `discussion.tex:197` already set the precedent. I agree with the reasoning; note that decision
  8 may make the interval disappear from these sites entirely, which moots it.
- **It declined to write the qualifier the brief asked for.** "Every threshold above the maximum
  flags nothing" is true *unconditionally*; only the identity between the floor and the atom is
  conditional. So the premise stays unconditional and the condition attaches to the conclusion:
  "…so **while the atom carries mass** the lowest false-alarm rate a firing threshold can have
  \emph{is}…". That is the better reading and it also closes old checklist item 6.

**Residual, still open:** `5.03` and `0.78` are guarded by nothing. `check_population_labels.py`
arms the fair-pool grid rule with `\b5\.0\\?%`, and `PCT` is a *required* percent sign, so the
pattern cannot match `5.03`. I confirmed this at `scripts/check_population_labels.py:671` with
`PCT` defined at `:334` rather than accepting the report of it. Three sites now carry `5.03`
(`main.tex:49`, `conclusion.tex:23`, `conclusion.tex:28`), plus `0.78` at `discussion.tex:173`
and the new endpoints `0.5` / `4.0` at `discussion.tex:139` and `:173`. The checker says OK,
which is correct and uninformative. Fold into decision 8's cleanup.

**[07:50 — CLOSED, and I checked it the hard way after nearly filing a false finding against it.]**
Round 4 added four `SUPERSEDED` patterns: `\b5\.03`, `\b0\.78(?!\d)`, `\b0\.5\s*,\s*4\.0(?!\d)`
and `\b0\.8\s*,\s*5\.0(?!\d)`. My first probe ran those regexes against the raw LaTeX
`[$0.8$, $5.0$]` and they missed, because `$` is not whitespace — I was two minutes from writing
this up as a guard that cannot fire. It was my probe that was wrong: the checker matches against
`strip_latex(raw)`, which deletes `$` at `check_population_labels.py:1262`, so the flattened text
is `[0.8, 5.0]` and the pattern hits. **Driven through the real code path, all four retired
renderings fire and both controls stay silent** — the replication AUROC `0.787` is protected by
the lookahead, and the live at-cap `0.0% [0.0, 1.9]` is untouched. The gap is genuinely closed.
The lesson is in critique log entry 38, and it is not a flattering one: I reproduced, against the
guard, the exact error the gate made against the correction two rounds ago — measure a component
in isolation, infer the whole is absent.

---

## Decision 2 — The paper's spine

**What must be decided:** which claim the Abstract leads with. **My recommendation has not
changed, and the interval correction made the case slightly stronger rather than weaker.**

Both previously blocked claims are dead on their merits and neither may be re-entered inverted:
the AUROC-vs-budget gain is **+0.024 [−0.013, +0.059]** like-for-like (43% of the advertised
+0.041 was a change of cache), and the low-FPR pAUC "fall" is **+0.0074 [−0.0677, +0.0768]**
like-for-like — a refusal to claim, not a null.

**(a) Keep the non-existence spine, N=10-scoped.** *"At the standard $N{=}10$ an operator who
specifies a 5% false-alarm budget cannot have one, however well the score ranks."*

- Core number: **10.5% [9.0, 12.2] over 1424 clean correct answers** (150/1424; I recomputed
  Wilson: 10.53% [9.044, 12.236]). An **atom mass** — a population probability — whose one-sided
  lower bound of 9.0% clears the 5% budget on the largest population in the paper. On the fair
  pool's 200 it is 9.5% [6.2, 14.4].
- Cost to adopt: **zero.** Already written, gate-cleared, population-labelled. I re-derived the
  core number tonight: Wilson(150/1424) = 10.5337% [9.0440, 12.2357].
- Its known weakness **was** decision 1, and round 3 fixed it: the asymmetric evidential standard
  (an exclusion demanding a lower bound, a concession granted on an in-sample point estimate)
  disappeared the moment the concession stopped saying "exists". This spine does not touch
  decision 8 — 10.5% on 1424 is a count at $\ln 10$, a threshold fixed before the data, and
  Wilson is uncontroversially the right estimator for it.

**(b) Cost-quality spine.** Unchanged and still the highest-risk move: the "catches only a small
fraction" number (11.0% [4.5, 21.5]) is quarantined, and the sentence is structurally the blocked
cross-budget TPR claim with the sign flipped. The cost half remains better than you framed it —
N=10 → N=40 is 4× the generations but **17.3× the pairwise entailment calls** (780 vs 45), which
is hardware-free.

**(c) Granularity spine.** *Now:* the floor falls **12.0 → 3.1 → 2.0 percent**, a fall of **10.0
points [7.2, 12.9]** that excludes zero and needs no AUROC.

- **Better than it was 24 hours ago.** The interval is 40% narrower than the `−9.9 [−15.5, −5.0]`
  I gave you last night, and it is the *correct* interval rather than a conservative one.
  Independently reproduced at a different seed and resample count in
  `figures/fig_floor_budget_stats.json`: −9.98 [−12.93, −7.21].
- **Still not a spine, for the same three reasons, and one of them got sharper overnight.** Its
  terminal 2.0% is a data-selected order statistic on n=200, not a population parameter — the
  class this project has already withdrawn a claim for. **Decision 8 is that objection cashing
  out:** the project cannot currently say what interval that order statistic deserves, and a
  spine whose terminal value has an unsettled interval is not a spine. The trend also mixes two
  kinds of quantity (two atom masses and one order statistic), and the N=20 → N=40 step on its
  own still does **not** clear zero (−1.1 pts [−2.4, +0.2]).
- It lives on n=200, against (a)'s n=1424.
- Round 3 did add the leg-by-leg decomposition to `discussion.tex:145-148`, which is the gate
  requirement that was old checklist item 4. That is a real improvement to (c) as a qualifier.
  See new checklist item 9 for a rounding problem in it.

**RECOMMENDATION: (a), unchanged, with (c) kept exactly where it is — the load-bearing qualifier
in the Discussion.** The reasons are the ones from last night and they all still hold; the only
change is that (c) is now a *better* qualifier. One reason has expired and should not be quoted
back at you: "decide the spine after the confirmatory run lands" was written when that run was 23
hours out. It is now ~18 hours out and it is a false-alarm arm, not a spine test — do not defer
this decision past today waiting for it.

**What this costs you, stated plainly:** the Abstract's sentence is longer and flatter than the
one you started the week with, and there is no rhetorical rescue available — the mitigation
earlier reports proposed (leading with 11.0% vs 14.5%) is quarantined.

---

## Decision 3 — The human equivalence audit [decide today]

**Unchanged. Round 3 did not touch it either, and it is still the only calendar-locked item.
The cost of not deciding it has now gone up by one more night.**

**State (I counted the rows myself, again):** `results/equivalence_audit.csv` — **123 rows, 0
annotated**; `equivalence_audit_round2.csv` — **37 rows, 0 annotated**. Both files last modified
**2026-08-13 02:45** — six days ago, and three overnight rounds have passed over them. The four-stratum
breakdown (72 win / 13 flip / 30 subthreshold / 8 catch) is from the design document, not from
the sheet, which carries no stratum column.
Protocol caps sessions at 40 pairs and budgets 60–90 s/pair → **2.05–3.08 h** for round 1 across
4 sessions. That pace is **assumed and has never been observed on this sheet.**

- `protocol §7a` requires a **≥7-day washout** before round 2: "Do not shorten it; a 1-day retest
  measures memory, not reliability." Hours cannot buy that back later.
- The schedule's "BLOCKING (title word *meaning-preserving*)" flag is **stale** — the live title
  is the protocol-led one and contains no such word. The preprint can ship without the audit;
  running it converts a disclosed limitation into a measurement.
- The real argument for starting today is the duty cycle, not the arithmetic: between 2026-08-14
  12:19 and 2026-08-19 01:14 — **4.53 days — not one file in this repo was modified.** Slack
  measured in sessions is not slack if the sessions do not happen.

**RECOMMENDATION: run round 1 now (4 sessions), drop the second audit today.** It needs no GPU
and no run state, so it overlaps the null control perfectly. `judge_owed_conditions.md` §8 says
outright of the second audit: *"If one must be dropped, drop this one."* Write the fallback for
judge condition (ii) now rather than improvising it in September.

**One hedge that costs nothing: time your first 40 pairs.** If session 1 runs at 120 s/pair,
round 1 is 4.1 h not 2.7 h — and *that* is when you choose between keeping and cutting round 2.

---

## Decision 4 — The LaTeX toolchain

**Unchanged except for the timing, which slipped six minutes.** Nothing has been installed and
nothing will be without a yes from you.

There is still no TeX — I re-checked `pdflatex`, `tectonic` and `latexmk` on the Windows path and
found none. No PDF of this paper has ever existed. But the source is clean: 8 files,
`check_latex_source.py` exits 0 with 4 warnings, all pre-existing unescaped `%` in
`related_work.bib` annotations that `plainnat` never emits. I re-ran it tonight and the count is
unchanged after three rounds of edits. **Estimated cost to first PDF: 15–60 minutes, one-time.**

**Sharper this morning:** round 3's verifier makes the point that none of the three overnight
rounds ran a LaTeX toolchain, so nine `.tex` edits have landed with compilation unverified.
`check_latex_source.py` is a source linter, not a build. Nothing in the edits introduced a new
macro, `\ref` or math environment, which is an argument and not a build.

| Option | Cost | Notes |
|---|---|---|
| **A — WSL apt** | **49.1 MB download, 21 packages, 144 MB on disk, ~5 min** (measured) | `texlive-latex-base texlive-latex-recommended texlive-fonts-recommended`. Only hazard: takes the dpkg lock inside the distro running the live job |
| **B — Tectonic** | ~25 MB binary + a few hundred MB cached on first run | Sizes **not measured**. Single binary, no admin |
| **C — Overleaf** | Zero install | Uploads the unpublished draft off-machine; the repo is the system of record |
| **D — Do nothing** | Zero now | The largest unpriced blocking schedule item stays unpriced |

**RECOMMENDATION: Option A, triggered when the device goes idle — but the idle time moved.**
At 05:45 that was ~22:45 tonight and the recommendation was "a first PDF inside today". The
07:45 sample puts the finish at **2026-08-20 00:33**, so a compile that waits for idle is a
**Thursday-morning** job, not a tonight job. Nothing forces the wait except courtesy to the run:
`apt` and a first LaTeX build are CPU and disk, not GPU. If you want the PDF today, the honest
options are to install now and accept some I/O contention with a run that is already the slower
of its two rate estimates, or to accept Thursday. I would accept Thursday — decision 3 is the
calendar-locked item and this is not. **Say the word and I will run it. I have not, and will not,
without that.**

Two things a first compile will surface: `main.tex:12-13` loads `hyperref` before `natbib`
(canonical order is the reverse — likely cosmetic), and **arXiv does not run BibTeX**, so the
first successful build's `main.bbl` is a required submission artifact.

---

## Decision 5 — Two claims that repeat the project's named failure mode, in the reject direction

Both still live, **and round 3 did not touch either one** — it was scoped to four other defects.
I re-grepped `discussion.tex` and found both sentences verbatim at their new line numbers. Both
are the same error you have withdrawn three claims for, running toward rejection rather than
acceptance. **5a got worse in round 1 and has not been repaired since.**

**5a. `discussion.tex:225-226`** (was `:197`; the file grew) **— "The pre-registered direction of
the error is therefore itself
falsified."** Asserted from two point estimates whose intervals both overlap their bands. At
N=40, 0/200 against the band's near edge of 1.2% is a one-sided binomial p = 0.089 (0.988²⁰⁰ — I
recomputed it); Wilson [0.0, 1.9] overlaps 1.2–2.4%. At N=20, 3.1% against a 3.5% edge is z ≈
0.50. "Falsified" is a categorical claim a referee will check against `n_scaling_plan.md` §5, and
it is not delivered at any conventional level.

**What changed:** round 1 rewrote the *following* six lines to concede that the N=20 row "may
carry no load-bearing claim" and "cannot be turned into a falsification either" — while leaving
"therefore itself falsified" standing at the top of the same paragraph. The paragraph now asserts
a falsification from two budgets and then disqualifies one of them, in 200 words.
**Recommended replacement for the top sentence:** "both point estimates came in below their
bands, neither miss significant on its own." One sentence, and the paragraph becomes coherent.

**5b. `discussion.tex:311`** (was `:270`) **— "the effect is much too small to disturb the
cluster-count
distribution, which matches."** Unchanged and still a null accepted from a non-significant
goodness-of-fit test. The χ² (7.39 on 9 df) is over all ten cells **including the K=10 cap cell
that carries the entire discrepancy**, and it has little power against a shift confined to the
top cell — which is the shape of the observed gap. No estimate of how far a +3.6-character shift
moves the atom exists anywhere. The source artifact says only "small enough to leave the
cluster-count distribution statistically indistinguishable"; the paper upgraded that to a
positive claim of no effect, in the one paragraph whose closing line is "we claim no direction
for the gap." **Recommended replacement:** revert to the artifact's own wording.

**RECOMMENDATION: fix both, ~20 minutes together.** Neither costs a result.

---

## Decision 6 — CLOSED overnight (round 3), by option (A). Verified.

The generator was edited at 05:18 and `results/replay_control.md` regenerated at 05:26. **I
verified the outcome by grepping the regenerated file, not by reading the report:** `−9.9`,
`[−15.5, −5.0]`, `11.9%` and the `11.9 → 3.0 → 2.0` triple appear **nowhere** in it. §6, still
titled "What is worth carrying instead", now reads at line 626-629: *"the floor falls
monotonically with budget (12.0% → 3.1% → 2.0%), the N=10 → N=40 fall clears zero (−10.0 points
[−12.9, −7.2])."* The one remaining `15.5` in the file is at line 86, the `7.0%–15.5%` **range**
column over 200 replicate draws, which is a different quantity and correctly labelled.

This is the fix that mattered most for how the project works, not for what the paper says — see
critique entry 37.

---

## Decision 7 — The `24.0` quarantine collision

Unchanged. Gate A3.4 specified the sentence "19 against **24.0** expected". `24.0` is on the
quarantine list, where it is the N=40 matched-9.5% TPR from the dead cross-budget claim — a
different quantity sharing the digits. The acting agent declined to write it, declined to
disguise it, and reported the collision. The paper carries the inference through the exact
Poisson-binomial p = 0.081 and omits the expected count.

**RECOMMENDATION: leave it out. No exemption.** The p-value carries the inference completely, and
a quarantine with one hand-granted exception is a quarantine the next agent will argue with. 2
minutes: ratify and move on.

---

## Edits with no decision in them

**Round 3 closed seven of the eight items that were here at 05:06.** I verified each closure
against the file rather than against the report; the record is below, short, because a closed
item you can re-check in ten seconds is worth more than a deleted one. **Items 5, 9, 10, 11
and 12 are live**, and 9 through 12 are new this morning.

- **1. `discussion.tex` "under an identical configuration" — CLOSED.** The
  `same model and quantisation, T=1.0, top-p=1.0, 48 new tokens, seed 0` clause is gone.
  `discussion.tex:303-306` now states the drift first and says the artefacts record only the
  sample count, the token budget and the seed in common. **But see item 10 — the removal created
  a dangling reference in `limitations.tex`.**
- **2. Withdrawn mechanism — CLOSED.** `because the clean baseline climbs along with the cap` is
  struck; the measurement (+0.304 vs +0.693, 3/15 still saturated) is kept, and the section now
  names why no mechanism is offered — it is the plug-in negative-bias decay this paper cites
  `mccabe2025alphabet` / `pan2026shade` *in support of*. `introduction.tex:184` now points at a
  section that says exactly that.
- **3. `introduction.tex` "no N=20 generation pass was run" — CLOSED and artifact-true.**
  `introduction.tex:90-97` now says no direct measurement of the *grid* at N=20 exists, "the only
  answers this project has ever scored at that budget being the $15$ saturated targets of the
  headroom pilot below, which were selected on their attacked $N{=}10$ score." Two agents
  independently re-derived `results/pilot_n20_ckpt_def.jsonl` (15 rows, all 15 `entropy_after_old`
  equal $\ln 10$ to <1e-12, 3/15 at $\ln 20$) and both report the selection was on the
  **attacked** score, which is what the file shows. I took the re-derivation on trust; I did not
  open the checkpoint.
- **4. The dropped gate requirement (A3.5) — CLOSED.** `discussion.tex:145-148` now gives the
  ladder leg by leg and says outright that the $N{=}20 \to N{=}40$ leg **covers** zero. See item 9
  for a rounding problem introduced with it.
- **6. The floor identity in the Abstract — CLOSED**, and better than asked. See decision 1's
  record above.
- **7. The search budget quoted three ways — CLOSED.** I grepped all five sites: `methods.tex:166`
  ($1 + 20 \times P \times B \approx 181$ objective evaluations), `experiments.tex:46/62/63/72/73`,
  `limitations.tex:101`, `discussion.tex:421`. **181 is now consistently the evaluation count and
  ~180 consistently the candidate paraphrases**, including at `experiments.tex:72-73`, which spells
  out why they differ by one. A notation collision was also caught and fixed in passing: line 64
  used $N$ for the attack candidate count two lines below a sentence declaring $A$ distinct from
  $N{=}10$.
- **8. The variance identity illustrated with standard deviations — CLOSED.**
  `discussion.tex:264-266` now says the components "combine as $\sqrt{0.98^{2}+0.74^{2}}$ rather
  than by addition." A reader who adds them no longer concludes the paragraph is wrong.

**5. `scripts/check_operational_provenance.py` — HALF DONE, and the half that was done is the
right half.** The `results/derived_paper_quantities.md` ratchet site is **closed**: I ran the two
`test_operational_provenance.py` failures and both now name only
`scripts/overnight_2026_08_14.sh` — the do-not-edit file, an expected and permanent failure. The
checker exits 1 with a single line: *"scripts/overnight_2026_08_14.sh: untagged: 3 operational
figure(s) carry no MEASURED/MODELLED/UNMEASURED tag, against a baseline of 0."* **The debt that
had been paid is now recorded.** What replaced it is the new failure in decision 8 — so the suite
went from 2 failures to 3 by closing one and opening one. **[07:50: round 4 closed the
regression. The suite is back to 2 failed / 1014 passed / 15 skipped, and both survivors are this
same do-not-edit script, surfaced by two different assertions. A verifier confirmed the
improvement was not bought by lowering a guard.]**

**9. WITHDRAWN at 07:50 — I was wrong, and the paper was right. Read this before you act on
anything else in this checklist.** I wrote item 9 at 05:52 accusing the paper of rounding a leg
to make two displayed decimals add. **The accusation is false.** The 10→20 leg does not need a
bootstrap at all: "all singletons" means the chosen subset is an independent set of the
question's verdict graph, so each question's saturation probability is a ratio of independent-set
counts and is exactly computable. **I computed it myself, with my own union-find and my own
counting code, importing nothing from the project: the N=10 floor is 11.992117%, the N=20 floor
is 3.129089%, and the leg is −8.863028 — which is 8.9 at one decimal, not 8.8.** The artifacts'
−8.8 and −8.84 are Monte-Carlo error at the second decimal. The paper's `8.9 [6.8, 11.1]` is the
correct value and must not be "corrected" down.

This matters beyond one digit, for two reasons. First, **it propagated**: item 9 was copied into
round 4's brief as an instruction to revert the paper, and the acting agent refused it and
recomputed — correctly. An agent overruled my error because it checked; had it complied, the
paper would be wrong this morning. Second, the presentational problem I thought I had found
**does not exist**: the exact legs are −8.863 + −1.129 = −9.992 and the rounded legs are
8.9 + 1.1 = 10.0, so both add, at both precisions, with nothing moved. The one residue is that
`results/replay_control.md:203` still prints the Monte-Carlo `−8.8 [−11.0, −6.8]`; §2c now
discloses the point discrepancy but not the endpoint. That is decision 10, item 5.

*The original item, as written at 05:52 and now known to be wrong, follows.*

**~~9. NEW — `discussion.tex:145-146` rounds a leg away from its artifact, apparently to dodge a
string guard.~~** The paper prints the N=10 → N=20 leg as "a fall of $8.9$ points [$6.8$, $11.1$]".
Two artifacts disagree: `results/replay_control.md:195` records **−8.8 pts [−11.0, −6.8]**, and
`figures/fig_floor_budget_stats.json`, generated at 200,000 resamples with seed 20260819,
re-derives **−8.84 [−11.02, −6.78]** and plots −8.8 [−11.0, −6.8]. I read both sidecars myself; I
did not re-run the bootstrap.

The acting agent's own report says why: *"the legs as printed sum exactly to the printed
end-to-end fall (8.9 + 1.1 = 10.0), which the artifacts' Monte-Carlo values do not (8.8 + 1.1 =
9.9 — and 9.9 is a registered retired string)."* **At full precision the legs do sum**
(−8.84 + −1.14 = −9.98). It is only the *rounded* legs that don't, which is ordinary rounding
non-additivity and not a defect. Rounding 8.84 up to 8.9 and 11.02 up to 11.1 to make two
displayed decimals add is a real defect, and the reason given for it — that the correct display
would have a reader mentally computing a string on the retired-figures register — means a
quarantine list influenced a rounding decision. **Fix: print 8.8 [11.0, 6.8] as the artifacts
give it, and add "(legs do not sum in the displayed precision)" if the arithmetic will bother a
reader.** ~5 min. The N=20 → N=40 leg and the end-to-end fall both match their artifacts exactly.

**10. CLOSED by round 4 — verified.** `limitations.tex:66-69` no longer claims the value appears
elsewhere in the paper; I grepped and there are zero `top-$p$` occurrences outside that sentence.
The replacement names `results/n_scaling_grid.md:161` as the one place the value *is* on file and
says that record describes the August pass. *Original item follows.*

**~~10. NEW — the top-p contradiction is half-fixed, in exactly the shape the round was warned
about.~~** Checklist item 1 deleted the Discussion's `top-$p{=}1.0$` clause. `limitations.tex:68`
still reads: *"…where a value for one of them appears elsewhere in this paper---top-$p{=}1.0$---that,
and not the run record, is its provenance."* I grepped `paper/` for `top-p`: the only hit is that
sentence. **It now refers to an occurrence that no longer exists.** Fix: reword to say the value
is recovered from the sampling script's defaults, full stop. ~3 min, one sentence, and it is the
same defect shape as decision 8 — a fix applied where the defect was noticed, not everywhere it
lives.

**11. CLOSED by round 4.** `discussion.tex:303-305` now reads "past the model id, its 4-bit
loading, temperature and that budget, … pins little", so the two lists agree and the Conclusion
does not lean on the stronger form. *Original item follows.*

**~~11. NEW — a quantifier disagreement between two sections that agree on the facts.~~**
`discussion.tex:303-305` says the June manifest "pins none of what decides the model's output —
not the nucleus, not the quantisation type, not the model revision" and cites
`\ref{sec:limitations}` two lines later. `limitations.tex:61-66` says the manifest pins the model
id, 4-bit loading, the sample count, temperature 1.0, a 48-token budget, the seed and the split,
and "of the settings that determine what the model emits it pins nothing further". The three
items the Discussion names are all on the Limitations missing-list, so the *lists* agree; "none
of what decides the output" and "nothing further" do not. ~3 min. Note this is a fresh edge
created by fixing item 1 — the third one tonight.

**12. STILL OPEN, and round 4 made it slightly worse rather than better.** `main.tex:29-36`'s
comment block says "~300 words (~200 at the critic gate of 2026-08-13; ~250 before 2026-08-19)"
and warns it is already over the usual arXiv limit. I expected decision 8's treatment to shorten
it; it did not, because the empty-atom sentence is longer than the interval it replaced. Measured
three ways this morning and all three agree on the direction: the comment block itself now claims
321 words / ~2020 characters, a verifier's stripper gives 321 / 2017, and mine gives 351 / 2054.
**The spread is a stripping artefact — LaTeX macro handling — and the conclusion does not depend
on which is right: the abstract is over arXiv's 1920-character abstract field by roughly 100–130
characters and will be rejected by the submission form as it stands.** This is no longer cosmetic;
it is a submission blocker, cheap to fix, and it needs one deliberate cut rather than another
round of additions. Note also that the comment block's self-reported count is now a claim in the
repo like any other — round 4 updated it and no guard checks it.

---

## Still unresolved — listed, not decided

**No side picked on any of these. Four are unchanged from 05:06; two moved; three are new.**

- **`results/n_scaling_grid.md:22` now disagrees with the paper on two rows, not one.** Its N=20
  row is still the single-replicate `6/200 = 3.0% [1.4%, 6.4%]` where the paper carries the
  matched `3.1% [1.8, 4.7]` — disclosed in the paragraph below the table, but the table is what
  gets read. Its N=40 row carries Wilson `[0.8%, 5.0%]`, which decision 8 may retire. Regenerating
  at R=200 is cheap and CPU-only; **do it after decision 8, not before**, or you will regenerate
  into the losing estimator. **[07:50: half of this is done. Round 4 edited the N=40 row in place
  to `4/200 = 2.0%, no interval (see below)` and added the explanatory block, so the losing
  estimator is gone and the regeneration is now unblocked. The N=20 row still reads
  `6/200 = 3.0% [1.4%, 6.4%]` against the paper's `3.1% [1.8, 4.7]`, and lines 24-26 still carry
  the unqualified absence claim below. Regenerate whenever convenient.]**
- **`results/n_scaling_grid.md:25-26`, unchanged and now the last copy of a defect the paper has
  fixed:** "the smallest purchasable false-alarm rate is 2.0%, NOT 0. There is no sub-2.0%
  operating point at this budget." An unqualified absence claim from a 4/200 point estimate. The
  paper spent round 3 removing exactly this form from three sections. **This is the same defect
  as the old decision 1, in the artifact rather than the paper**, and it is the sentence most
  likely to be lifted verbatim — which is not hypothetical, see critique entry 37.
- **`scripts/n_scaling_grid.py`: the floor fix is narrower than reported.** Unchanged. Four
  further sites in the same function still print `ceiling_atom()` under the label "floor", two of
  them live. No number is wrong today, but the "cannot be swapped again" guarantee does not hold,
  and one dormant site is the fresh-N=10 drift control — exactly the run that would empty an atom.
- **`scripts/check_population_labels.py`.** Unchanged, and a second gap found tonight. Its replay
  rule's stated rationale still reads "replay OVERSTATES the floor ... all 20 replicates above" —
  the refuted claim, sitting inside the guard that polices the corrected text. Its docstring
  taxonomy still contradicts itself (lines 41-42 vs 74). And **the fair-pool grid rule cannot
  match the new literals**: `PCT` is a required percent sign, so `\b5\.0\?%` misses `5.03`, and
  `0.78`, `0.5` and `4.0` are not in the rule's `numbers` list at all. I confirmed this by reading
  `:671` and `:334`, not by accepting the report of it.
- **`tests/test_n_scaling_grid.py:47` and `:80`** are interpreter-dependent, not a bug. Unchanged:
  Windows CPython 3.11 gives `lattice_stats(40)` size 14116 / merged 2 (pass); WSL CPython 3.12.3
  gives 14114 / 0 (fail). Two partition entropies differ by a float ULP. **Do not send anyone
  hunting an enumeration bug.**
- **Figures.** `fig1_ceiling.pdf` and `fig2_censoring.pdf` exist and are never included. I ran
  `check_latex_source.py`: it still resolves exactly one figure across all eight `.tex` files,
  `fig_achievable_roc`, which is N=10-only and sits in a paragraph carrying no N anywhere. The new
  `fig_floor_budget` is now decision 9.
- **Errata #4:** the N=10 citation claim ("the budget Kuhn, Farquhar and Kossen all use") is
  unverified and needs three page cites before that Abstract sentence ships. Unchanged.
- **NEW — the Abstract's `44\%` [$23\%$, $64\%$] names no population.** `main.tex:53`. It is the
  winner's-curse retention figure and it belongs to the 80-target attacked prefix, but the
  Abstract does not say so, and the Abstract is the one place a population label cannot be
  inferred from context. Logged as gate finding N2 at `results/gate_paper_edits_2026_08_19.md:82`
  and still open after three rounds. `check_population_labels.py` does not catch it.
- **NEW — one paragraph switches population mid-section and is correct anyway.**
  `discussion.tex:73-75` gives 148 alerts / 49.2% PPV / 216 missed per thousand. Round 3's
  verifier reports these are jointly consistent **only** at hallucination rate 28.8%, FPR 10.5%,
  TPR 25.2% — the full labelled pool, not the fair pool whose numbers surround it — and that
  `results/achievable_fpr_grid.md:233` matches exactly (145/295 = 49.2%). The sentence does label
  itself. I took the reconstruction on trust and did not redo it. Worth a second label anyway,
  because it is the only population switch inside a section.
- **NEW — nine `.tex` files have been edited across four rounds and none of it has been
  compiled.** Not a defect, a gap in evidence; it is decision 4's real cost of delay, and round 4
  edited several of them again.
- **Owed measurements, both pre-registered and neither run:** a fresh direct N=10 pass on this
  machine (40 answers) to separate subsetting error from generation drift, and a direct N=20 pass
  (60 answers) to check a replayed grid against a measured one. The Discussion names both as
  missing. **The third — the coverage simulation from decision 8, objection 1 — is no longer
  owed: round 4 ran it, and it settled the decision.** The two GPU ones remain.
- **NEW — the pre-registration mislabels its own criterion.** `results/n_scaling_plan.md:309-311`
  and `:403-404` both describe "the Wilson upper bound under 5%" as what is needed to say *no*
  operating point at or below 5% exists. It is what is needed to say one **does**. Only `:425`
  states it correctly. The paper does not inherit the error and the ruling reads the criterion
  the right way round, but the plan is the document a referee would be pointed at. Fold into
  decision 10.

---


## What changed while you slept

### Round 4 (05:52 - 07:20) — one ruling, one consolidating pass, two verifiers

**Everything in this block I checked against the files at 07:50.**

1. **Decision 8 was settled by measurement, not by argument.** An agent ran the coverage
   simulation this file called for at 05:52 and wrote `results/n40_floor_estimator_ruling.md`
   (06:32). Both of the objections raised here were upheld, and the ruling went further than
   either: it withdrew *both* candidate intervals rather than choosing between them, and it made
   the opposite call on the achieved 5%-budget row. Full evidence under decision 8.
2. **The ruling was applied in one pass across ten site groups**, and the paper came out clean —
   I verified the eight `.tex` files by grep and re-derived their numbers from the checkpoint.
3. **The suite went 3 failures → 2**, and the two survivors are one pre-existing do-not-edit
   file reported twice. Both `KNOWN_OPEN` reductions a verifier checked are mechanically true
   against the live checker, so the improvement was not bought by weakening a guard. One
   assertion was deleted; a verifier confirmed it is strictly subsumed by a test that is red for
   exactly the right reason.
4. **The pass rejected part of its own brief, and was right to.** Its instructions said the
   paper's `8.9 [6.8, 11.1]` had been tidied and should revert to the artifacts' `-8.8`. It
   refused, on the ground that the exact value is `-8.863` and the artifact's `-8.8` is
   Monte-Carlo error. **I recomputed this independently and exactly** — 11.992117% and 3.129089%,
   leg `-8.863028` — and the pass is right. Notably, the brief contradicted *itself*: its own
   header carried `-8.86`. An agent overruling its instructions and saying so plainly is the
   behaviour to keep.
5. **It also caught itself mid-error and recorded the near-miss.** It first computed the 20→40
   leg as `[-0.2, 2.5]` and changed the paper, then found it had resampled a fixed top-4
   indicator instead of re-finding the top score inside each resample, and reverted to `2.4`. A
   verifier reproduced **both branches**. It further recorded that the `11.05` lower endpoint
   straddles the rounding boundary — `11.1` is a coin flip at one decimal — and wrote the
   instability into the figure generator so a later rerun does not "correct" it.
6. **And it left seven sites behind anyway.** That is decision 10, and it is the interesting part
   of the night, because round 4 was organised specifically to prevent it: one agent, the whole
   surface, one change. Ownership was not the binding constraint. Critique log entry 38.

### Round 3 (04:20 - 05:30) — five agents, four fixes, one new blocking defect

**Everything in this block I verified against the files at 05:52.**

1. **The 5% existence claim is gone from the Abstract and the Conclusion.** That was the
   BLOCKING item at the top of this list six hours ago. It is closed on all four sites —
   Abstract, Conclusion, Introduction, Discussion — and closed in the better direction: the
   summary sections now carry the criterion in place rather than deferring to a pointer.
2. **`results/replay_control.md` was regenerated and the retired `-9.9 [-15.5, -5.0]` is
   gone from it,** along with the `11.9 -> 3.0 -> 2.0` triple. I grepped for both. §6, "What is
   worth carrying instead", now carries the live ladder. The generator's two bypass sites were
   fixed before the regeneration, so the next regeneration will not revert it.
3. **The ratchet debt was paid and recorded.** `results/derived_paper_quantities.md` no longer
   appears in either `test_operational_provenance.py` failure; the only remaining site is the
   do-not-edit shell script.
4. **Three more paper defects closed:** the `identical configuration` claim, the withdrawn
   mechanism, and the false "no N=20 pass was run". Plus the gate's A3.5 leg-by-leg requirement,
   the search-budget wording, and the quadrature sentence. Details in the checklist above.
5. **And one new blocking defect, which is the whole story of round 3.** Fixing the estimator for
   the N=40 floor row in `discussion.tex` left the same row's Wilson interval standing in
   `main.tex`, `conclusion.tex`, `introduction.tex`, the generator, three `results/*.md` files and
   the new figure. **The suite went from 2 failures to 3.** That is decision 8, and the shape of
   it — a fix applied where the defect was noticed rather than everywhere the defect lives — is
   also the shape of the top-p half-fix (checklist item 10) and of the quantifier disagreement
   (item 11). Three instances, one night, one shape.
6. **`pytest` is 3 failed / 997 passed / 7 skipped.** I ran it and read all three failures. The
   passing count rose by 16 because a new test file, `tests/test_derived_paper_quantities.py`,
   landed at 04:34.

### Rounds 1 and 2 (01:20 - 04:00) — the record, unchanged from the 05:06 version

1. **The interval "correction" I relayed to you at 03:06 was itself wrong, and it has been
   inverted.** Last night's decision 1 said the paper's published intervals were too *narrow* and
   prescribed wider ones. They were too **wide** — about twice as wide as the estimator they were
   attached to deserves. The arithmetic: for question *i* with subset-saturation probability
   `p_i`, one replicate's floor is a mean of independent indicators, so
   `mean p(1−p) + var(p) = p̄(1−p̄)` identically — **the subset draw is already inside Wilson**
   and cannot be added a second time. Measured on the fair pool's 200 correct answers: at N=20 the
   components are 0.98 and 0.74 points, root-sum-square 1.232 against a binomial 1.232; at N=10,
   1.61 and 1.63 against 2.296 and 2.296. I re-derived the identity from the printed means alone;
   it is algebra, not a measurement, and the residual is under 5e-5.
   **Two independent agents agreed with the wrong version before a third recomputed it** — one of
   them a critic gate that measured the subset dispersion itself (sd 0.99 pp over 500 replays) and
   read a correct measurement as evidence the component was missing. Logged as critique entry 36.
2. **Every affected number, and every one moved in the safe direction:**

   | | was | now |
   |---|---|---|
   | replay N=10 floor | 11.9% [7.0, 17.5] | **12.0% [8.9, 15.3]** |
   | replay N=20 floor | 3.0% [0.5, 6.5] | **3.1% [1.8, 4.7]** |
   | measured N=40 floor | 2.0% [0.5, 4.0] | **2.0% [0.8, 5.0]** (Wilson on 4/200) |
   | direct N=10 floor | 9.5% [6.2, 14.4] | unchanged (Wilson on 19/200) |
   | **headline fall, N=10 → N=40** | **9.9 pts [5.0, 15.5]** | **10.0 pts [7.2, 12.9]**, excludes zero |
   | direct-vs-replay step | +2.4 pts, "covers zero" | +2.5 pts [−0.7, +5.5], covers zero |

   The tightening manufactured no new step: N=20 → N=40 is −1.1 pts [−2.4, +0.2] and still covers
   zero. The paper has been rebuilt against all of this and is current.
3. **One inference genuinely changed.** The N=20 pre-registration paragraph rested on the row's
   interval covering the whole predicted 3.5–5.3% band. The matched interval stops at 4.7% and
   covers only the band's lower edge. The conclusion survives (the miss is still not significant);
   the stated reason does not, and the paragraph was rewritten to say so.
4. **A bootstrap that moved while you read it.** At the 20,000 resamples in use, the N=10 lower
   endpoint moved **0.13 points across bootstrap seeds** — larger than the decimal place the paper
   prints. Both `[8.91, 15.31]` and a first corrected pass `[8.87, 15.24]` were inside that noise.
   Raised to 400,000; endpoints now stable to ~0.01 points.
5. **Round 2 read all eight `paper/` files against the artifacts** and found the four defects that
   are now decision 1 and checklist items 1–3, plus four cosmetics. It re-derived the Wilson
   intervals for all seventeen counts the paper prints and reports that every one matches to the
   digits shown; I spot-checked six of the seventeen myself (19/200, 4/200, 3/200, 10/200,
   150/1424, 6/200) and they match. No number appears in two sections with different values.
6. **The retired `−9.9 [−15.5, −5.0]` propagated tonight** — out of `replay_control.md` §6, into
   the agent briefing, and from there to six agents, three of whom repeated it. That is decision 6.
7. **`pytest` moved to 2 failed / 981 passed / 7 skipped.** One failure was fixed; both survivors
   then also named `results/derived_paper_quantities.md`, because the ratchet register was not
   lowered in the same commit as the fix. *Round 3 lowered it; the register is clean.*
8. **Both guards still exit 0**: `check_population_labels.py` OK (8 files, 16 rules, 78 number
   patterns); `check_latex_source.py` 0 ERROR / 4 pre-existing WARN.
9. **The quarantine held.** None of the eight quarantined cross-budget literals appears in
   `paper/`; the two occurrences of 14.5% are the within-N=10 randomised chord, independently
   derivable and admissible.
10. **`docs/critique_log.md` is current again.** Entry 36 records the sign-test refutation, the
    two dead claims, the inverted interval correction, and the rule that follows: *a correction is
    a claim, and carries the same burden as the thing it corrects — plus one.* **Entry 37 was
    added at 05:52** for round 3: the scope rule (fix the defect everywhere it lives, not where
    you noticed it), and the propagation finding — a superseded number surviving under a heading
    that said it was the thing to carry.

---

## What is running now

**Verified live at 2026-08-19 07:45 BST by my own read-only `ps -eo pid,ppid,etime,stat,args`
inside Ubuntu-24.04, run twice. Nothing signalled, nothing disturbed, nothing run on the GPU. I
did not take the PID table in the previous version of this file on trust — I re-ran `ps`, and all
four PIDs are the same ones, still alive.**

| PID | PPID | Elapsed | State | What |
|---|---|---|---|---|
| 457 | 453 | **7h08m** | `Ss+` | `bash scripts/overnight_2026_08_14.sh` — the retry wrapper |
| 473 | 457 | **7h08m** | `Sl+` / `Rl+` | `.venv-wsl/bin/python scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 --dump_diag results/diag_defb.json --checkpoint auto` |
| 5751 | 5746 | **6h38m** | `Ss` | `bash scripts/stop_watcher_v2.sh` |
| 25204 | 25197 | **5h56m** | `Ss` | `bash scripts/watcher_supervisor_v3.sh` |

PID 473 sampled twice inside one minute, once as `S` and once as `R` — it alternates, which is
what a batched judge loop looks like and not a stall. Distro load average 2.08 / 2.13 / 2.09
across the three windows, i.e. flat and unchanged from 05:48. Distro uptime 7h09m.

**Progress** (`dashboard/progress_status.json`, generated 07:45:07, checkpoint written 07:35:18,
age 589 s): **30 of 80 done, 50 remaining**, 19 produced this session, 11 carried over, **0 torn
lines**. Rate **1209 s/target** over the last 5 (1185 s over all 18 timed this session),
direction **slowing down**, disagreement 2.0%, judged stable, no slow intervals. Watcher healthy,
2 GPU processes, last wrote 10 s before the sample.

**The ETA moved nearly two hours later, it crossed midnight, and this time it is a real
slowdown.** The 05:52 version of this file told you to treat a six-minute move as noise and not
re-plan. That was right then. This one is not noise, and the reason is worth two lines because
it inverts the previous diagnosis.

| | 05:06 | 05:45 sample | **now (07:45 sample)** |
|---|---|---|---|
| done | 22/80 | 24/80 | **30/80** |
| remaining | 58 | 56 | **50** |
| last-5 s/target | 1099 | 1091 | **1209** |
| all-time s/target this session | 1150 (10 timed) | 1162 (12 timed) | **1185 (18 timed)** |
| direction | — | speeding up | **slowing down** |
| central ETA | 22:37 | 22:44 | **2026-08-20 00:33** |
| other-basis ETA | 23:27 | 23:50 | **2026-08-20 00:13** |

Last time the basis rate got *faster* while the ETA slipped, so the slip was an artefact. This
time the basis rate itself rose 1091 → 1209 s/target, and the crude check agrees with it: two
hours of clock (05:45 → 07:45) produced exactly **6** targets, i.e. **1200 s/target** measured
end to end, against the 1091 the old projection was spending. **50 × 1209 s = 16.8 GPU-hours
remaining.**

Two things make this more trustworthy than the earlier estimates, not less. The disagreement
between the two rate bases collapsed from 6.1% to **2.0%** — they now bracket the finish inside
20 minutes rather than an hour — and the sample count behind them doubled, 12 timed targets to
18. So the ETA is both **later and better determined**. It is also still inside the monitor's own
quoted per-target spread (392–1404 s), so I would not call it a fault; the honest reading is that
the early-session rate was optimistic and 1200 s/target is the run's real pace.

**What that changes: decision 4, and nothing else.** Plan around **00:30 Thursday ± 40 min**, not
22:45 tonight. The LaTeX install is the only item on this list that was scheduled against the
finish, and it is now a Thursday-morning job unless you choose to accept I/O contention. Nothing
else here needs the GPU or the run state — decision 10, the audit, and the plan correction are
all CPU and file reads.

**To stop it:** press STOP in `dashboard/session_dashboard.html`, or place a file named
`STOP.txt` in `C:\Users\Abhi\Downloads` or in the repo root. The watcher polls both locations
(plus the `.txt.txt`, ` (1)`, `STOP_SESSION.txt` and extensionless variants), TERMs the wrapper,
TERMs and then KILLs the python processes, and consumes the signal so a later relaunch is not
killed by a stale file.

**Do not create any of those files unless you mean it.** I did not create one, of any spelling,
in either watched location. Everything on this morning's list — decision 10, the audit, the
LaTeX call, the plan correction — needs neither the GPU nor the run state, so there is no reason
to stop it. The coverage simulation that was the one new owed measurement at 05:52 has been run,
on CPU, and it settled decision 8. The two remaining owed measurements (a direct N=10 pass and a
direct N=20 pass) *do* need the GPU and must wait for this run regardless.
