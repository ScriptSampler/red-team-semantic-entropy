# figures/ — what is here, what the paper includes, and what each one is measured on

Written 2026-08-19. An unreferenced PDF in a submission directory is a trap twice over:
someone deletes it as an orphan, or someone `\includegraphics`es it without re-checking
whether its numbers are still current. This file exists so neither happens silently.

**The population column is the important one.** Two different pools appear below, and
binding a number to the wrong one is this project's most-repeated error.

| figure | included by the paper? | population | budget | provenance | status |
| --- | --- | --- | --- | --- | --- |
| `fig_achievable_roc` | **yes** — `paper/sections/discussion.tex` | fair pool, correct stratum (n=200) + its 200 hallucinating | N=10 | direct, Week-4 (June) cache | current |
| `fig_floor_budget` | **yes** — `paper/sections/discussion.tex` (added 2026-08-19) | fair pool, correct stratum (n=200) | N=10 / 20 / 40 | mixed; the figure says which | current; regenerated 2026-08-19 under the floor ruling |
| `fig1_ceiling` | no | false-alarm **attack** pool (n=80 correct-answer targets) | N=10 | direct, definitive cell `wk9_defb` | current, unreferenced |
| `fig2_censoring` | no | false-alarm **attack** pool (n=80 correct-answer targets) | N=10 | direct, definitive cell `wk9_defb` | current, unreferenced |

## Generators

| figure | script |
| --- | --- |
| `fig_achievable_roc` | `scripts/achievable_fpr_grid.py` |
| `fig_floor_budget` | `scripts/make_floor_budget_figure.py` |
| `fig1_ceiling`, `fig2_censoring` | `scripts/make_ceiling_figures.py` |

Each writes its plotted points beside it as `*_data.csv`, and `fig_floor_budget`
additionally writes `fig_floor_budget_stats.json`, the record of the re-derivation that
had to pass before it would draw.

### `fig_floor_budget`, two things that changed on 2026-08-19

**The N=40 floor is drawn as a point with no error bar, on purpose.**
`results/n40_floor_estimator_ruling.md` withdrew both candidate intervals after measuring
their coverage against a population model validated out-of-sample on the N=20 and N=10
ceiling atoms: Wilson on 4/200 covers the true floor 53.7% of the time and the question
bootstrap 0.00%, at a nominal 95%. Neither estimator is broken — the estimand is, once the
ceiling atom empties. The generator now *refuses to plot* if either endpoint is filled back
in. The interval that survives at N=40 is the at-cap mass, 0/200 = 0.0% [0.0, 1.9], whose
threshold (ln 40) is fixed a priori.

**The per-question saturation probabilities are now exact, not Monte Carlo.** "All
singletons" is "the subset is an independent set of the recorded verdict graph", so the
probability is a ratio of independent-set counts and needs no sampling. The old 20,000-draw
estimate was off by about 0.01 rate points — enough to move the 10 → 20 paired leg from
-8.86 to -8.84 and so across a rounding boundary, which is how this figure came to plot
-8.8 while the paper printed 8.9. **The paper was right.** `results/replay_control.md` still
carries the Monte-Carlo value (-8.8 at 40,000 draws) and is the file to distrust in the
second decimal, not this one.

## `fig1_ceiling` and `fig2_censoring`: keep, do not delete, do not wire in blind

**Nothing from the 2026-08-19 overnight round touches either of them.** That round
reversed claims about the *fair pool* and the *sample budget*; these two are N=10
measurements on the 80-target attacked pool, which was not re-measured. They are
reproducible (their generator refuses to plot if the data stops matching its verified
list), they name their pool in every panel title and axis label, and the numbers in them
still hold. **Deleting them would destroy intact work that nothing refuted.**

They are also not ready to be dropped into the paper unexamined. Wiring either one in
puts a *second population* into the paper's figure set: `fig_achievable_roc` and
`fig_floor_budget` are both the 200-answer fair-pool correct stratum, and these two are
the 80-target attacked pool. That is legitimate — they are about the attack, which is a
different question — but the captions have to carry the distinction, and the two pools
must not sit adjacent without a sentence separating them. `check_population_labels.py`
guards the `.tex` side; it does not guard a reader's eye.

So: **left alone, deliberately, and recorded here as a decision rather than an
oversight.** Whoever owns `paper/` decides whether the attack figures earn their space;
this file's only job is to make sure that decision is made on purpose.

## A cross-check worth knowing about

`fig_achievable_roc` and `fig_floor_budget` share a point. The achievable-ROC figure's
floor is the first firing threshold on the June N=10 cache: 19/200 false alarms = 9.5%,
catching 55/200 = 27.5% of the hallucinating stratum, with the next achievable rate at
21.5%. That is the same 9.5% [6.2, 14.4] drawn as the detached diamond in
`fig_floor_budget`. If those two ever disagree, one of the two generators has drifted.
