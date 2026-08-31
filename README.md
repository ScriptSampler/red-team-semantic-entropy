# Red-Teaming Semantic Entropy

Code, analysis scripts, artifacts of record and paper source for a preprint on **what it takes
to evaluate a paraphrase attack against a sampling-based hallucination detector** — and on the
measurement-validity result that turned up when we built the controls.

- **Paper:** [`paper/main.pdf`](paper/main.pdf) (41 pages), source in [`paper/`](paper).
  Working title: *Crying Wolf, Carefully: What It Takes to Evaluate Paraphrase Attacks on
  Sampling-Based Hallucination Detectors.*
- **Status:** preprint in preparation. arXiv target **2026-10-01**. Not yet posted, so there is
  no arXiv identifier to cite.
- **Author:** ScriptSampler (solo project).

Read [`docs/START_HERE_overnight.md`](docs/START_HERE_overnight.md) before touching anything.
It is the live handoff document: it dates every number it prints and marks each one as measured,
re-derived or carried, and it lists the claims this project has retired and must not restate.

---

## What the paper claims

### 1. The headline is a measurement-validity result about *discrete* semantic entropy

Discrete semantic entropy weights meaning-clusters by sample counts, so its score is the entropy
of an integer partition of the sample budget `N`. That makes it a **lattice-valued** statistic,
not a continuous one. Enumerating the partitions is pure arithmetic — no run, no model, no data — and the counts are
pinned by the test suite in `tests/test_achievable_fpr_grid.py::test_lattice_counts_quoted_by_the_report`
and `tests/test_n_scaling_grid.py::test_lattice_counts_the_plan_quotes`, against independent
implementations:

| `N` | partitions | distinct SE values | cap `ln N` | values in the top tenth of the range |
|---|---|---|---|---|
| 10 | 42 | **39** | 2.302585 | **2** (2.163956 and 2.302585, 0.1386 nats apart) |
| 20 | 627 | 455 | 2.995732 | 7 |
| 40 | 37338 | 14114 | 3.688879 | 42 |

There is an **atom at the maximum**. A detector that flags when the score reaches a threshold can
only change its false-alarm rate at a value some clean correct answer actually took, and every
threshold above `ln N` flags nothing at all. So while that atom carries mass, the smallest
non-zero false-alarm rate any firing threshold can have **is** the chance that a clean correct
answer yields `N` mutually distinct meanings. That is an identity, not a curve fit.

Measured at the standard `N=10`:

- **10.5% [9.0, 12.2]** on the 1424-answer clean-correct superset
  (`results/achievable_fpr_grid.md`).
- **9.5% [6.2, 14.4]** (Wilson on 19/200) on the score-independent fair pool's 200-answer correct
  stratum (`figures/fig_floor_budget_data.csv`).

The consequence is a constraint on the **operator**, not on the attacker: at `N=10` an operator
who specifies a 5% false-alarm budget cannot have one, however well the score ranks, because the
only threshold that honours it never fires. The scope qualifiers are load-bearing — the claim is
about the *discrete* estimator at *that* budget, and the paper concedes both edges:

- It does **not** transfer to Kuhn's unnormalised Eq. (4), which has no such bound. The `log N`
  ceiling is shared with the likelihood-weighted Eq. (5); the lattice argument is
  discrete-specific.
- It does **not** survive a bigger sample budget. At `N=40` none of the same 200 correct answers
  reaches `ln 40` (0/200, at-cap mass **0.0% [0.0, 1.9]**), the atom is empty and the obstruction
  goes with it. The cheapest threshold that fires at all then costs **2.0%** — quoted as a bare
  point **with no interval**, because at n=200 the quantity an interval would describe is not
  identified (`results/n40_floor_estimator_ruling.md`). A 5% budget is honoured at `N=40` at an
  achieved **5.0% [2.7, 9.0]**, reported as a measured operating point and not as proof that one
  at or below 5% exists.

### 2. The paraphrase attack is a case study, and its null control does not reject

The attack rephrases a question under a hard bidirectional-NLI equivalence constraint, aiming to
move the detector's score while the model's answer — and its correctness — stays put. Two
directions were formulated (*false-alarm*: inflate the score on a correct answer; *hide*: suppress
it on a wrong one). **Only the false-alarm direction was run under the confirmatory null control.**

That null prices the attacker's own search budget in, against the benign arm's 50 draws. The
optimiser *scores* 181 candidates per target, but a candidate can become the reported maximum
only if it also clears the feasibility gate, and the gate is applied lazily, so **181 is an
upper bound on the budget rather than the budget itself**. Nothing the run recorded identifies
how many of the never-gated candidates would have passed, so the budget `A` is **not
identified**; the defensible range is **[41, 181]** and the paper reports the test across it
rather than at one end of it. Run to completion over all 80 false-alarm targets, the
pre-committed randomised-tie exceedance test **fails to reject in every clustering arm**:
p = **0.939** (shared NLI), **1.000** (exact match), **1.000** (LLM judge), on the 77 targets
that have a benign arm (`results/null_control_report_defb.md`), each a median over 101
tie-break draws. **Those three figures are at the upper bound `A=181`.**

What the range does to the arms is not symmetric, and it is why the defence is stated this way.
The shared-NLI arm's p-value is **not identified**: its median runs from 0.939 at `A=181` to
below 0.001 at `A=41`, and it crosses the 5% cut near `A=90`, which is inside the range. The
two re-scored arms do not move: the **pre-registered adjudicator arm's median p is 1.000 at
every `A` in [41, 181]** and at every one of the 101 tie draws, as is the exact-match arm's.
That invariance to the one parameter that cannot be pinned down, and not any headroom in the
shared-NLI arm, is what the non-rejection rests on.

**The paper therefore claims no attack effect.** The design *that ran* — 77 targets, six of them
with short benign arms — has power **0.67** against a two-fold effect, so this bounds what could
have been seen rather than measuring a zero. The design that was *planned* (80 targets, a uniform
50 benign draws each) had 0.77, and it is the stronger of the two at every level at which both
can be read: 0.699 against 0.669 at a common achieved level of 0.025, and 0.809 against 0.783
at 0.050. Most of the difference is the analytic null's integer granularity, which admits no cut
between 0.0296 and 0.0501 and so forces the cut from 13 down to 11; about a third of it is the
three targets with no benign arm and the six short ones. A fixed cut is not a fixed level and
does not overturn this: at `S<=13` the realized design's analytic tail is 0.0793 against the
planned design's 0.0437, so it scores higher there only by running at 1.8x the type-I error.

**Every power, level and cut in the paragraph above is at the upper bound `A=181`**, the same
scope as the three p-values, and none of them is a statement about the whole range. The cut
moves a long way down it: the design that ran cuts at `S<=11`, `S<=19` and `S<=66` at `A=181`,
`A=121` and `A=41`, and the planned design at `S<=13`, `S<=21` and `S<=72`. No power is
re-simulated at the lower budgets and none is reported there.

### 3. What the controls cost, which is the reusable part

- **Selection inflation.** Re-scoring each *selected* paraphrase on an independent sample retains
  only **44% [23%, 64%]** of the apparent effect; the shrinkage is **-0.341 nats
  [-0.469, -0.212]**, excluding zero (`results/winners_curse_se_false_alarm.md`). *That* the
  selection-time figure is inflated is established; *how much* is not.
- **Score-independent target selection.** Selecting targets on the detector's own scores inflates
  clean AUROC to **1.000** by construction, against **0.704 [0.653, 0.753]** on the fair pool
  (`results/fair_pool_report.md`).
- **An independent equivalence oracle.** The detector's NLI model both clusters answers and
  certifies paraphrase equivalence, so a single-clusterer evaluation cannot separate a real change
  in the model's answers from that model's own inconsistency. Sentence embedders do not break the
  tie — e5 is near-chance (~0.51) on exactly the word-preserving, meaning-shifted case. The
  deployed Qwen2.5-7B-Instruct judge reaches **0.930 [0.900, 0.957]** on hard negatives
  (`results/judge_validation.md`), with conditions (ii) and (iii) of its validation still open.

### Claims this repository does not make

Versions of this README before 2026-08-30 asserted framings the project has since retracted.
They are named here because the file stood for 66 days and 202 commits after the evidence moved:

- **The false-alarm attack is not "the headline".** It is the case study that exercises the
  protocol, and its confirmatory test does not reject.
- **Nothing here is "evidence against the paradigm of sampling-based uncertainty detection."**
  The paper makes no such claim and explicitly declines to. Attribution of the NLI-arm effect is
  *unresolved but bounded*; what the paper concludes is that single-clusterer paraphrase-attack
  claims on these detectors are not adequately supported.
- **Not a general result about "semantic entropy".** Everything above is scoped to the *discrete*
  estimator, at a named sample budget, on a named population.
- **Two claims died on their merits and must not return in either direction**: AUROC-vs-sample-budget,
  and cross-budget TPR/pAUC. Every interval in the uniform-provenance family covers zero.
- **SRE, SQuAD, the hide direction, cross-detector transfer and the reformulation-averaging
  defense are not confirmatory results.** They exist as reduced-scale exploratory cells; the paper
  reports them as pending.

---

## What was run

| | |
|---|---|
| Victim model | Llama-3.1-8B-Instruct, 4-bit (bitsandbytes), single 16 GB GPU |
| Detector | Discrete semantic entropy, DeBERTa-large-MNLI clustering, `N=10` unless stated |
| Equivalence oracle | Qwen2.5-7B-Instruct LLM judge; exact-match and shared-NLI reported alongside |
| Benchmark (confirmatory) | TriviaQA `rc.nocontext` |
| Attack search | Forked from [Buyun-Liang/SECA](https://github.com/Buyun-Liang/SECA) — we reuse its search; SECA attacks the model's answer, we attack the detector's score |
| Hardware | AMD Radeon RX 9070 XT (RDNA 4, gfx1201, 16 GB), WSL2 Ubuntu 24.04, ROCm 6.4, PyTorch 2.9.1+rocm6.4 |

Native Windows ROCm for RDNA 4 is not workable, so GPU work runs only under WSL2. Full bootstrap:
[`docs/setup_wsl_rocm.md`](docs/setup_wsl_rocm.md).

---

## Repository layout

```
.
├── README.md
├── SE_Project_Execution_Plan.md   # original week-by-week plan (superseded on dates and framing;
│                                  #   kept as a record — see "Reading the dated documents")
├── requirements.txt               # Windows venv, Python 3.11 (CPU: tests + all analysis)
├── requirements-wsl.txt           # WSL Ubuntu-24.04 venv (GPU research runtime)
├── paper/                         # main.tex, sections/, related_work.bib, main.pdf (41 pp.)
├── src/se/                        # library: sampling, NLI, entropy, SE/SRE pipelines, judge,
│   └── attacks/                   #   embeddings, defense, stats; attacks/ = the search harness
├── scripts/                       # 80 analysis and run scripts, plus WSL bootstrap and the
│                                  #   overnight/watchdog machinery
├── tests/                         # 37 pytest modules; also pin retracted claims OUT of paper/
├── results/                       # artifacts of record: 78 dated .md reports + evidence CSVs
├── figures/                       # the paper's figures, each beside its plotted-points CSV
│                                  #   and its re-derivation record; figures/README.md maps
│                                  #   every figure to the population it is measured on
├── docs/                          # handoff, methodology, critique log, positioning, setup
├── dashboard/                     # session_dashboard.html + the live-run status surfaces
│                                  #   (the JSON/log surfaces are gitignored; they churn)
├── configs/  notebooks/  data/    # placeholders; data/ contents are gitignored
└── vendor/                        # gitignored; the SECA clone lives here (see Provenance)
```

`scratch_stats_audit.py` at the root is a one-off statistics audit kept for the record, not part
of the library.

---

## Running it

### Without a GPU (Windows venv, Python 3.11)

This is where the tests and every analysis script live. The old README said the Windows venv was
"for IDE and editor tooling. Nothing computational runs there." That is no longer true.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Test suite** — 1408 tests, no GPU, no model, no cached samples:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected today: **2 failed, 1389 passed, 17 skipped** (verified 2026-08-31). The two failures are
deliberate and are both in `tests/test_operational_provenance.py`; they name three untagged
operational figures in `scripts/overnight_2026_08_14.sh`, a file that is on the do-not-edit list
because it is the wrapper the long GPU run executes. The debt is real, recorded, and payable only
when no run is up. It was **not** silenced by raising the checker's baseline. A green suite next
to a known-open debt would read as validation of it.

**Read-only checkers** — these run against tracked files only, so they work in a fresh clone:

```powershell
.venv\Scripts\python.exe scripts\check_population_labels.py       # every rate must name its population
.venv\Scripts\python.exe scripts\check_latex_source.py            # paper source hygiene
.venv\Scripts\python.exe scripts\check_operational_provenance.py  # the operational-figure debt ledger
.venv\Scripts\python.exe scripts\derived_paper_quantities.py      # re-derives every number the paper
                                                                  #   prints that had no producing artifact
```

`check_operational_provenance.py` is **red by design**: it reports open sites across the repo.
That is a debt ledger, not a failing grade.

**One checker that does not run against tracked files, and has to not:**

```powershell
.venv\Scripts\python.exe scripts\check_worktree_debt.py           # work stranded in an ignored worktree
.venv\Scripts\python.exe scripts\check_worktree_debt.py --list    # state only, always exit 0
```

`.claude/worktrees/` is gitignored, so an agent that edits files there and stops before
committing leaves work that `git status`, `git log main..`, `git diff` and every other checker
here are all blind to. That is not hypothetical: on 2026-08-31 six of seven worktrees held
uncommitted changes, two of them unlanded and one of those a cost constant that was wrong by
4.6x in the cheap direction and had been sitting unread for eighteen days, through two critic
panels and an external review. This checker enumerates the worktrees, classifies the dangerous
shape (**uncommitted AND no commits** -- nothing anywhere refers to it), and requires each one
carrying work to have a recorded verdict in `ADJUDICATED`. It is also red by design while any
verdict is `OPEN`. `tests/test_worktree_debt.py` fails if a worktree has never been read at
all, which is the tripwire; the script is the ledger.

### Without a GPU, but *not* from a bare clone

Several analysis scripts re-derive the paper's numbers from run checkpoints. Those checkpoints are
excluded by `.gitignore`, so **a clone does not carry them** (see Limitations below). With the
checkpoints present they are CPU-only and Windows-runnable:

```powershell
.venv\Scripts\python.exe scripts\null_control_defb_report.py   # the definitive null control, 80/80
.venv\Scripts\python.exe scripts\make_floor_budget_figure.py   # floor vs sample budget
.venv\Scripts\python.exe scripts\make_ceiling_figures.py       # the ln(N) ceiling and censoring
.venv\Scripts\python.exe scripts\achievable_fpr_grid.py        # achievable-FPR grid (reads the WSL
                                                               #   Week-4 cache over the UNC share)
.venv\Scripts\python.exe scripts\replay_control.py             # direct-vs-replay provenance control
```

`null_control_defb_report.py` is fully deterministic: every seed is fixed and no timestamp or
path-dependent value reaches the output, so running it twice produces a byte-identical report.

### With a GPU

Everything that samples from the victim model, clusters with NLI, or calls the judge needs the
GPU and runs only inside WSL2. One-time bootstrap, from elevated Windows PowerShell:

```powershell
wsl --install
wsl --install -d Ubuntu-24.04
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/bootstrap_ubuntu_2404.sh"
wsl --shutdown
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/install_rocm_64_wsl.sh"
wsl -d Ubuntu-24.04 bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/setup_venv_wsl.sh"
```

Always `wsl -d Ubuntu-24.04`, never `wsl -d Ubuntu`. Then:

```bash
source .venv-wsl/bin/activate
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# expect: True AMD Radeon RX 9070 XT
python scripts/preflight.py   # exits non-zero unless the Phase-1 cache is present and non-empty
```

Run order, coarsest first. Each stage is resumable and each consumes the previous stage's cache
in `~/.cache/se-research/` **inside WSL** — not in the repo, so a repo-scoped search finding
nothing is not evidence of failure.

1. **Replication and pool construction** — `scripts/run_all.sh` drives sampling
   (`wk4_sample.py`), clustering (`wk4_cluster.py`) and AUROC (`wk4_auroc.py`), then the Phase-2
   attack cells at a documented reduced scale. It halts before Phase 2 if clean AUROC falls below
   a sanity floor. Sampling 2000 questions at `N=10` is the long pole.
2. **Relabelling and the fair pool** — `relabel_pool.py`, then `fair_pool_check.py`. The fair
   pool is `select_stratified(..., 200, seed=0)`; the attacked cells are literal *prefixes* of the
   same seed-0 shuffle, so they are nested inside it, not disjoint from it.
3. **Attack campaigns** — `wk9_scaleup.py --attack false_alarm --detector se --dataset triviaqa`.
   The definitive false-alarm cell is `wk9_defb`.
4. **Sample-budget grid** — `n_scaling_grid.py` produces `results/n_scaling_ckpt.jsonl`, the
   source of every `N=10 / 20 / 40` floor number.
5. **The null control** — `scripts/overnight_2026_08_14.sh`, which wraps
   `null_control.py --only false_alarm --K 50 --n_seeds 3 --judge_model Qwen/Qwen2.5-7B-Instruct
   --checkpoint auto`. Checkpointed per target and resumable; it took roughly 20 minutes per
   target on this card. **Do not edit that wrapper or `null_control.py` while a run is up** —
   Python reads a script at invocation, so an edit lands days later as a crash or as silent
   garbage.
6. **Reporting** — `null_control_defb_report.py`, `winners_curse_reeval.py`,
   `replay_control.py`, then the figure generators.

`scripts/stop_watcher_v2.sh` polls for a `STOP` file in two fixed locations and kills the run on
sight. That channel belongs to the human operator; nothing in the automated pipeline may create
one, because a self-triggering stop makes the button useless.

### Building the paper

```bash
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

The shipped `main.pdf` was built with pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian) inside
the WSL distro, which is where the toolchain is installed. `\graphicspath` accepts a build
launched from either the repository root or `paper/`.

---

## Where the authoritative numbers live

Every claim in the paper is owned by an artifact under `results/`, and the artifacts have moved.
**Quote the artifact, not a summary of it** — including not this README.

| finding | artifact of record |
|---|---|
| Achievable-FPR grid, the floor, and the operating points below one in four | `results/achievable_fpr_grid.md` |
| Granularity on the score-independent fair pool | `results/fair_pool_granularity.md` |
| Clean AUROC, class separation, asymmetric censoring | `results/fair_pool_report.md` |
| Why the measured `N=40` floor carries no interval | `results/n40_floor_estimator_ruling.md` |
| Sample-budget comparison under uniform provenance | `results/replay_control.md` |
| The definitive null control, 80/80 | `results/null_control_report_defb.md` |
| Selection inflation, shrinkage and retention | `results/winners_curse_se_false_alarm.md` |
| Judge validation (cite the **deployed symmetric** config, 0.930) | `results/judge_validation.md` |
| Ceiling saturation on the definitive false-alarm cell | `results/ceiling_saturation_finding.md` |
| Every paper number that had no producing artifact | `results/derived_paper_quantities.md` |
| Which figure is measured on which population | `figures/README.md` |
| The running record of critiques, corrections and retractions | `docs/critique_log.md` |

Two standing warnings, both of which have been "corrected" back by mistake before: the judge's
**0.930** is the deployed symmetric configuration (the superseded asymmetric run gives different
figures), and the replication comparison must use the greedy alias-aware span convention, because
the all-samples-correct label is coupled to the score it is being compared against.

---

## Limitations of this artifact

Stated plainly, because the paper's main virtue is that it does not overclaim.

- **A clone cannot reproduce the headline numbers from raw data.** The two decisive checkpoints —
  `results/n_scaling_ckpt.jsonl` (2.3 MB, the sample-budget grid) and
  `results/null_control_ckpt_defb.jsonl` (237 KB, the 80 null-control targets) — are excluded by
  `.gitignore` (`results/*.jsonl`), as is `results/diag_defb.json` and the whole of `data/cache/`.
  They exist in the author's working tree and are not distributed. What a clone *does* carry is
  every derived report under `results/`, and each figure's plotted points beside it as a CSV plus
  a re-derivation record (`figures/fig_floor_budget_stats.json`), so the arithmetic is checkable
  even where the raw run is not re-runnable.
- **The upstream sample caches are outside the repository entirely**, in
  `~/.cache/se-research/` inside WSL. Regenerating them means re-running the GPU pipeline.
- **The GPU path is not portable.** ROCm 6.4 on RDNA 4 under WSL2 is the only configuration this
  was run on. Nothing here has been tested on CUDA.
- **Single model, single family, single quantisation, primarily one dataset.** Llama-3.1-8B-Instruct
  in 4-bit on TriviaQA. Broader coverage is future work, not a result.
- **Judge validation is incomplete.** Conditions (ii) validation on messy real sampled pairs and
  (iii) a differential-over-splitting check are open; `results/judge_validation.md` lists them.
  The judge is scoped to the false-alarm direction only.
- **The human equivalence audit is prepared but unrun** (`scripts/prepare_equivalence_audit.py`).
- **No pinned environment lockfile beyond the two requirements files**, and no container.

### Reading the dated documents

Several documents in this repository state things that were true when written and are not true
now — the original plan's 2026-09-15 target being the clearest case. They are **deliberately not
back-edited**: rewriting a dated analysis to match today is how an audit trail stops being one.
`docs/START_HERE_overnight.md` is the live document and names which older files are history.
Where they disagree with it, it wins; where either disagrees with the artifact it cites, the
artifact wins.

---

## Provenance of third-party code

`vendor/SECA` is a clone of [Buyun-Liang/SECA](https://github.com/Buyun-Liang/SECA), MIT-licensed,
Copyright (c) 2025 Buyun Liang. It is **gitignored and not redistributed here**; re-clone it with
the command and pinned commit recorded in [`docs/phase2_overview.md`](docs/phase2_overview.md).
Its licence terms govern that code, not this repository's.

Model weights (Llama-3.1-8B-Instruct, DeBERTa-large-MNLI, Qwen2.5-7B-Instruct) and datasets
(TriviaQA, SQuAD) are fetched from their upstream sources under their own licences and are not
redistributed here.

## Citing

There is no arXiv identifier yet. Until there is, cite the repository and the working title:

> ScriptSampler. *Crying Wolf, Carefully: What It Takes to Evaluate Paraphrase Attacks on
> Sampling-Based Hallucination Detectors.* Preprint in preparation, 2026.
> https://github.com/ScriptSampler/red-team-semantic-entropy

## Licence

MIT. See [LICENSE](LICENSE).
