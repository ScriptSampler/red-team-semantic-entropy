# Operational-number audit — every figure that schedules work, and whether anyone measured it

**Scope.** Not the paper's factual claims (those have `scripts/check_population_labels.py` and
the re-derive-before-the-Abstract rule). This is the *other* class: GPU-hours, seconds per
evaluation, targets per night, per-cell costs, batch sizes, capacities and deadlines — the
numbers that decide what runs, what gets cut, and in what order. They are guarded by nothing.

**Why now.** The definitive null control was deprioritised on 2026-08-13 at 22:56 on the
grounds that it had `~60 GPU-h left against a ~10 h night`. That figure was a model —
55 clusterings/target × ~55 s — whose 55 s came from a **K=8** probe (critique_log 22,
2026-08-02) and was used to cost a **K=50** run. Re-derived from the run's own wall clock it
is 24.0 s/clustering and 1191 s/target: **23–26 GPU-h, not 60**. That correction was already
written down in `results/null_control_cost_options.md` (mtime 23:27) — twelve and a half hours
before the queue header that contradicted it was committed. The measurement was not missing.
It was not read.

This audit asks the same question of every other operational number in the repo.

---

## 0. Bottom line

- **Twelve distinct anchors** carry every operational number in the repo: **five measured**
  (A1–A5), **five modelled** (A6–A9, A12), **two with no recoverable provenance** (A10, A11) —
  plus one job admitted to tonight's queue with **no estimate at all**. Every derived figure
  of consequence traces back to one of four of them (A1, A6, A7, A8), and **all four are now
  dead**: refuted, or measured at an operating point they were then spent at somewhere else.
  Thirty-odd derived figures inherit from them.
- **The single most reused unit in the repo — an N=10 SE evaluation — is now measured at
  12.87 s** (§2.1), from a job that finished at 23:44 tonight. It confirms one model
  (`13.0 s`, −1%) and refutes two (`2.8 s`, 4.6× low; `6.1 s`, 2.1× low).
- **Six decisions currently rest on a superseded number** (§4). **Four the measurement
  reverses**; one was already corrected and ignored anyway; one is a scheduling decision that
  was never made because the capacity and the demand were both unmeasured and happened to
  cancel. One of the six is printed in the paper.
- **Mechanisable? Partly, and the honest split is unusual.** The "is it tagged" half and the
  "has the underlying job now run" half *are* enforceable by a script in the shape of
  `check_population_labels.py`, and one sub-rule (stale countdowns) is enforceable with zero
  false positives. The half that actually caused every failure here — *is this anchor the
  right anchor for this job* — is not mechanisable at all, and no checker will ever notice
  that a K=8 probe is being used to cost a K=50 run. §5 proposes both halves and says which
  is which. `scripts/check_operational_provenance.py` implements the mechanisable part.

---

## 1. Method: how the re-derivations were done, and the ctime/mtime trap

Every re-derivation below comes from filesystem timestamps or from in-band timestamps written
by the job itself. No GPU work was launched for this audit.

**Which timestamp, and why.** On Windows/NTFS, Python's `os.stat().st_ctime` is the file's
**creation** time — *not* the Unix inode-change time. Every checkpoint in this repo is opened
`"a"` and flushed per record (`winners_curse_reeval.py:445-448`, `null_control.py:413`), so
creation == **first record written** and `st_mtime` == **last record written**.

**That reading is verified, not assumed.** `results/n_scaling_ckpt.jsonl` has
`st_ctime = 2026-08-13T23:57:32.840` and its first JSON record carries
`"ts": "2026-08-13T23:57:32"` — the same second. The file is written from WSL to the NTFS
share, so this also validates the reading across the drvfs boundary, which is the case
`null_control_cost_options.md` §1 depended on without being able to check.

**The off-by-one that matters.** A span from first-record to last-record covers
`n − 1` intervals, not `n`. Dividing by `n` understates the unit by `n/(n−1)`: 1.5% at
n=69, **10% at n=11**. All figures below divide by intervals.

**On ext4** (the WSL sample cache) `stat` reports `Birth:` directly; used for the campaign
files in §2.5.

**Wall clock is not GPU-hours, and this repo mixes them.** Every "GPU-h" figure here is
compute time, but every decision that consumes one ("can it finish in a night?") is
wall-clock. On the `_defb` chain the observed ratio ranges from **1.00×** (hide cell, final
28 targets, device uncontended) to **2.28×** (FA cell, 80 targets across two days). Stated
per-figure below where it changes the answer.

---

## 2. The re-derivations

### 2.1 ★ The canonical unit: an N=10 SE evaluation costs **12.87 s**

`winners_curse_reeval.py` does exactly two `semantic_entropy(...)` calls per record at
`GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0)` — the canonical configuration —
and nothing else on the GPU.

| anchor | value |
|---|---|
| `results/winners_curse_ckpt_se_false_alarm_defb.jsonl` ctime (record 1) | 2026-08-13 23:15:11.916 |
| same file, mtime (record 69) | 2026-08-13 23:44:22.528 |
| span / 68 intervals | **25.74 s/target** |
| ÷ 2 SE evaluations per target | **12.87 s / SE evaluation** |

Cross-check: the job's own queue timing is 1880 s including a ~110 s three-model load
(`/tmp/overnight_20260813.log`), giving 25.7 s/target independently.

**What this settles, all at once:**

| modelled figure | source | measured | delta |
|---|---|---|---|
| `13.0 s/eval` (11.21 gen + 1.75 NLI) | `n_scaling_plan.md` §2 | 12.87 s | **−1.0%** ✓ |
| `~2.8 s` per SE eval | `null_objective_ablation_plan.md` §6 | 12.87 s | **4.6× too low** ✗ |
| `~6.1 s` cheap arms | `judge_owed_conditions.md` §6.2, from critique_log 22 | 12.87 s | **2.1× too low** ✗ |
| `12.70 s/Q` sampling loop *incl.* greedy | `run_all.log`, 1907 q | 12.87 s (different unit) | the reconciliation in `n_scaling_plan.md` §2 is correct in structure but had the sign backwards: the SE eval is marginally *dearer*, not cheaper, than the greedy-inclusive sampling loop |

`n_scaling_plan.md`'s decision to trust its own direct measurement over the 2.8 s attribution
was right, and it said so in writing before the confirmation existed. That is the only place
in the repo where a bad operational anchor was caught before it did damage.

### 2.2 ★ N=40 costs **42.6–44.6 s/eval**, not 73.9 — the recommended buy is 4.8 GPU-h, not 8.2

`scripts/n_scaling_grid.py --n_samples 40 --strata both --n_per_stratum 200` is **running
now** and records `seconds_total` per evaluation. At 75 completed evaluations (interim —
see §6):

| reading | value |
|---|---|
| in-process mean `seconds_total` | **44.55 s** |
| wall clock, ctime→mtime / 74 intervals | **42.60 s** |
| of which generation | **≈13.0 s** |
| of which NLI (`seconds_nli`) | **≈32.2 s** |

**The error is entirely in the generation half.** `n_scaling_plan.md` §2 modelled N=40 as
`43.6 s generation + 30.3 s NLI`. The NLI half was modelled almost exactly right (+6%,
quadratic scaling holds). The generation half assumed **linear** scaling from N=10's 11.21 s;
measured, generation at N=40 is **12.98 s** — batched generation is essentially **flat** in N
over this range. The plan offered a three-way bracket (amortised 43.8 / linear 73.9 / loaded
93.1) and picked *linear* as central; the measurement lands on the **amortised** end.

| figure | modelled | measured | delta |
|---|---|---|---|
| N=40 s/eval | 73.9 | 42.6–44.6 | **−41%** |
| the recommended buy, 400 evals | **8.22 GPU-h** | **4.73–4.95 GPU-h** | **−3.3 to −3.5 GPU-h** |
| N=20 s/eval (same linear-generation error) | 29.4 | ≈19 (implied: 11.5 gen + 7.4 NLI) | **−35%** |
| item 4 reserve, 30 evals at N=40 | 0.62 GPU-h | 0.37 GPU-h | −41% |

Every N>10 figure in `n_scaling_plan.md` carries the same 1.5–1.6× inflation, because they all
divide by the same modelled generation term. **This does not reverse the buy** — item 1 was
recommended and is running — but see §4.6 for what it does to tonight's schedule.

The VRAM claim in the same section (KV cache 0.46 GB at N=40 against a measured 5804 MB peak
at N=10 on a 16 GB card, `pipeline_check.md`) is a model, and it is now **corroborated**: the
N=40 pass is live and has not OOMed.

### 2.3 The judge is at most **46%** of a clustering, not 88%

`null_control_cost_options.md` §1 measures a clustering at **24.0 s**. §6F then splits it using
the refuted 2.8 s figure and concludes the judge is *"roughly 88% of a clustering and ~85% of
the run"*. With the measured cheap half:

```
judge increment = 24.0 s − 12.87 s = 11.13 s  →  46% of a clustering
```

12.87 s is a *lower* bound on the cheap half here (the null control holds Llama + DeBERTa +
Qwen co-resident, which can only slow generation), so **46% is an upper bound on the judge's
share**. The claimed 88% is wrong by roughly a factor of two.

This is the sharpest instance of the failure class in the repo: **the document that corrected
the 67 GPU-h figure imported a discredited anchor from the very file it was correcting, three
sections further down** — and then built its top engineering recommendation on it.

Consequences, and two of the three survive:

| downstream claim | modelled | re-derived | verdict |
|---|---|---|---|
| §9.1 "a 20% judge throughput win is ~4 GPU-h" | 4.0 | **~2.3 GPU-h** | recommendation **survives** — ten minutes for 2.3 GPU-h is still the best trade on the page |
| §6 "single-ordering saves ~12 GPU-h, not worth it" | 12 | **~5.6 GPU-h** | conclusion **survives**, and is strengthened |
| `judge_owed_conditions.md` §6.2 "the judge is ~49 s — about 90% of the cost" | 49 s | **11.13 s** | **refuted** |

### 2.4 ★ The paper's one operational number, superseded: **228 GPU-hours → ~99**

critique_log 22 priced the brute-force budget-matched design at K=180 as
`185 evaluations/target × 55 s = 171 min/target × 80 = 228 GPU-h ≈ 9.5 GPU-days`. Re-priced at
the measured 24.0 s/clustering from the deployed run (same symmetric judge, same
`judge_batch_size 6`, same N=10):

| | entry-22 unit (55 s) | measured unit (24.0 s) |
|---|---|---|
| judge arm, K=180, n=80 | 227.8 GPU-h — **9.5 GPU-days** | **98.7 GPU-h — 4.1 GPU-days** |
| cheap arms, K=180, n=80 (`~25h — affordable`) | 25.1 GPU-h | **52.9 GPU-h** |
| **ratio judge : cheap** | **9.1×** | **1.9×** |

Two things follow, and the second is worse than the first.

1. `paper/sections/experiments.tex:173` discloses a pre-registration deviation as triggered by
   *"the matched design pricing out at $228$ GPU-hours, about nine and a half GPU-days."* The
   real figure is ~99 GPU-h / ~4.1 GPU-days. The deviation itself is defensible — 99 GPU-h is
   still four days of a shared card — but the **stated magnitude of the trigger is wrong by
   2.3×**, in a paragraph whose entire purpose is to let a reader check that the rule was not
   tuned to the result. It is also hard-coded as an `Input(..., 228, source="docs/critique_log.md")`
   in `scripts/derived_paper_quantities.py:65`, i.e. the one place in the repo where an
   operational number *has* a provenance field, and the field points at a log entry rather
   than at an artifact.
2. The **9.1× ratio is the load-bearing part of entry 22's architecture** — cheap arms for the
   budget-dependence curve, judge only at a single budget, because the judge "cannot afford to
   answer" the curve. At **1.9×** that argument does not hold in the form it was written, and
   the "affordable" cheap-arm alternative is itself 2.2 GPU-days.

### 2.5 The attack cells: the compute model held, the wall-clock model never existed

| cell | anchor | targets | wall span | s/target |
|---|---|---|---|---|
| `_defb` FA | ext4 Birth 2026-08-11 01:21:39.978 → mtime 2026-08-12 07:02:16.790 | 80 | 106,837 s = **29.7 h** | 1352 (wall) |
| `_defb` hide | Birth 2026-08-12 07:02:21.081 → mtime 2026-08-13 07:21:22.782 | 80 | 87,542 s = 24.3 h | 1108 (wall) |
| `_defb` hide, **final 28** (52/80 recorded at `null_objective_ablation_plan.md` mtime 02:47:41 → hand-off 07:21:22) | — | 28 | 16,422 s | **≤586.5** |

The clean segment — 28 targets on an uncontended device — gives **≤586.5 s/target**, squarely
inside `null_objective_ablation_plan.md`'s measured `568–607 s/target` bracket. So:

| figure | modelled | measured | delta |
|---|---|---|---|
| "28 targets ≈ 4.7 GPU-h left" | 4.7 | **4.56 GPU-h** | **−3%** ✓ |
| "FA cell must be re-run, n=80, ~13 GPU-h" | 13 | **13.0 GPU-h** compute | **0%** ✓ / **29.7 h wall** |
| "hide cell 17→80, ~12 GPU-h" | 12 | 10.3 GPU-h | −14% ✓ |
| `definitive_run_plan.md` "~875 s / SE attack" | 875 | 586.5 | −33% (older optimiser settings; superseded honestly) |
| `definitive_run_plan.md` "n=80 × 2 SE cells ≈ 39 GPU-h" | 39 | **26.1 GPU-h** | −33%, inherited from the above |

**The attack-cost model is the healthiest number in the repo** — measured, bracketed, and
confirmed to 3%. The gap it does not cover is wall-clock: 13.0 GPU-h of compute took 29.7 h of
calendar. Any sentence of the form "X GPU-h, so it fits in a night" is silently asserting a
1.0× ratio that the FA cell falsified at 2.28×.

### 2.6 The null-objective ablation is **8.3–18.9 GPU-h**, not 3.2–5.7

`null_objective_ablation_plan.md` §6 builds its per-target table on `s_SE ≈ 2.8 s`, obtained by
splitting a measured 3.26 s objective call pro-rata across generated tokens. Substituting the
measured 12.87 s and leaving every other line of that table untouched:

| | s_SE = 2.8 s (as written) | s_SE = 12.87 s (measured) |
|---|---|---|
| attack arm, per target | 143–255 s | **375–849 s** |
| **n=80, attack arm only** | **3.2–5.7 GPU-h (central ≈4)** | **8.3–18.9 GPU-h (central ≈13.5)** |
| the plan's own reference, "the real attack, same n" | 13.1 GPU-h | 13.1 GPU-h |

At the measured unit the ablation costs **about the same as re-running the real attack** — which
is internally coherent (both evaluate a comparable number of distinct feasible strings) but
destroys the framing that the scrambled objective makes it cheap. See §4.3.

### 2.7 The judge-conditions run is **0.74 GPU-h**, not 3.11 — and that removes a risky edit

`judge_owed_conditions.md` §6.2 prices design J1 as 160 judge clusterings + 80 victim sampling
passes at a modelled **67 s/clustering** (a geometric-mean bracket over the 55 s and 6.1 s
anchors, both of which are now refuted, and both of which were taken at
`judge_batch_size=12` while the deployed run is at 6). The file says so itself: *"This is a
model, not a measurement. Replace it before quoting it."* Replacing it:

```
160 × 11.13 s (measured judge increment, batch 6)  +  80 × 11.21 s (generation)
  = 2,673 s = 0.74 GPU-h        vs  2.98–3.11 GPU-h modelled       (−76%)
```

The 12-target pilot in the same section (24 clusterings + 12 generations) falls from
~0.5 GPU-h to `24 × 11.13 + 12 × 11.21 = 402 s` — **~0.11 GPU-h, seven minutes**.

### 2.8 Tonight's queue: budgeted 9.6 h, will take **5.8 h**

| job | estimate, and where it came from | actual | delta |
|---|---|---|---|
| `rescore-benchmark` | none — it *is* the measurement | 90 s | — |
| `rescore-likelihoods` | pre-benchmark bracket **0.1–5.5 h**; benchmark then predicted **0.24 h** (0.22 + 0.02 load) | 907 s = **0.252 h** | **+5%** vs the benchmark ★ |
| `winners-curse-defb` | `START_HERE` "~15 min GPU" for 44 targets | 1880 s = **31.3 min**, 69 targets | +26% per target; +109% on the headline, because `--fresh_seed 1` re-scored all 69 rather than the 44 |
| `seps-transfer` | *"cheapest never-run capability"* — **no number at all** | 661 s = 0.18 h | unbudgeted |
| `n-scaling-N40` | 8.22 GPU-h (§2.2) | ≈4.8 h projected | −41% |
| **night total** | **"~9.6 h"** (script header) | **≈5.8 h** | **−3.8 h** |

`rescore_likelihoods.py` is the model the rest of the repo should copy: it refuses to emit a
point estimate (`cost_estimate()` returns *"a table, not a single number"*), labels its floor
anchor `MEASURED_GEN_TOKENS_PER_S = 80.0` as a hard pessimistic bound, ships `--benchmark` to
collapse the bracket, and the queue spends 90 seconds running it first. A 55× bracket became a
±5% prediction for ninety seconds of GPU. **This is the whole guard, already implemented once,
in one file.**

---

## 3. Inventory

`M` = measured, `Md` = modelled, `?` = no recoverable provenance. **Bold** = drives a live
decision. Anchors are numbered; a modelled figure names the anchor it inherits from.

### Anchors (everything else is derived from these)

| # | figure | where | class | provenance | status |
|---|---|---|---|---|---|
| A1 | **55 s / clustering** | critique_log 22 | M | K=8 probe, batch 12, 2026-08-02 (13 calls ≈ 12 min/target) | **SUPERSEDED → 24.0 s.** Measured at K=8 and applied to K=50 and K=180 |
| A2 | **24.0 s / clustering** | `null_control_cost_options.md` §1 | **M** | fit over the deployed run's own 11,915 s span | **current** ★ |
| A3 | **12.87 s / SE eval (N=10)** | this audit §2.1 | **M** | `winners_curse_ckpt_..._defb.jsonl`, 68 intervals, 136 evals | **current** ★ |
| A4 | **586.5 s / attack target** | this audit §2.5 | **M** | `wk9_defb` hide cell, final 28 targets | **current** ★, confirms the 568–607 bracket |
| A5 | 12.70 s/Q sampling loop; 1.49 s greedy; 11.21 s gen (by subtraction); 1.75 s/Q NLI | `n_scaling_plan.md` §2 | M | `run_all.log` 1907 q; `run_all_status.txt` 2000 q in 3509 s; `pipeline_check.md` | **current** |
| A6 | 2.8 s / SE eval | `null_objective_ablation_plan.md` §6 | Md | token-split of a measured 3.26 s objective call | **REFUTED by A3 (4.6×)** |
| A7 | 6.1 s / cheap-arm eval | critique_log 22 via `judge_owed_conditions.md` | Md | back-solved from "25 GPU-h for 80 × 185" | **REFUTED by A3 (2.1×)** |
| A8 | 73.9 s / eval at N=40; 29.4 at N=20 | `n_scaling_plan.md` §2 | Md | A5 + **linear**-in-N generation | **REFUTED by §2.2 (−39%)**; generation is flat, not linear |
| A9 | 67 s / judge clustering at batch 6 | `judge_owed_conditions.md` §6.2 | Md | geometric mean of A1 and A7 brackets, both taken at batch 12 | **REFUTED by §2.3 (6×)**; the file flags itself |
| A10 | `judge_batch_size = 6` | `src/se/judge.py:104-105` | **?** | docstring assertion that ~90 prompts OOM a 16 GB card with Llama+DeBERTa resident. No probe at 6/8/10/12 anywhere in the repo | unverified; and `probe_batched_judge.py`, the tool §9.1 recommends for this, is a **correctness** gate, not a throughput probe |
| A11 | "a ~10 h night" | `overnight_2026_08_13.sh:4` | **?** | never stated | the binding capacity constraint in the decision that started this audit |
| A12 | 0.52 s propose+gate; 85% benign gate pass | `null_control_cost_options.md` §1 | Md | declared as assumed, with a stated sensitivity (±2 s / ±28 s on 1349) | **good practice** — modelled, labelled, bounded |

### Derived figures, by file

| file | figure | class | from | re-derived | Δ |
|---|---|---|---|---|---|
| `critique_log.md` 22 | **228 GPU-h / 9.5 GPU-days** (judge, K=180) | Md | A1 | **98.7 GPU-h / 4.1 d** | **−57%** |
| `critique_log.md` 22 | **~25 GPU-h cheap arms — "affordable"** | Md | A7 | **52.9 GPU-h** | **+111%** |
| `critique_log.md` 26a | **~67 GPU-h null control** (55 clusterings × 55 s → ~50 min/target) | Md | A1 | **1191 s/target; 23–26 GPU-h** | **−62%** |
| `critique_log.md` 835 / 976 | hide 17→80 ≈ 12 GPU-h; FA re-run ≈ 13 GPU-h | Md | A4 | 10.3 / **13.0** | −14% / **0%** ✓ |
| `definitive_run_plan.md` | ~67 GPU-hours | Md | A1 | 23–26 | **−62%** |
| `definitive_run_plan.md` | ~875 s / SE attack; **n=80 × 2 cells ≈ 39 GPU-h** | Md | older-settings measurement | 586.5 s; **26.1 GPU-h** | −33% |
| `definitive_run_plan.md` | *"the null control is cheap … not the bottleneck — the attack is"* | Md | A1 | **false**: 1191 s/target vs 587 s/target — the null control is **2× the attack per target** | reversed |
| `START_HERE_overnight.md` | ~67 GPU-h; ~70 GPU-h for hide-under-null | Md | A1 | 23–26; ~25 | **−62%** |
| `START_HERE_overnight.md` | "~15 min GPU", 44 targets / 88 SE evals | Md | — | 1880 s / 69 targets | +26% per target |
| `START_HERE_overnight.md` | "33 days to 2026-09-15" | M-at-write | date arithmetic | **32 days today** | monotone in time; appears in ≥5 live docs |
| `overnight_2026_08_13.sh` | **"~60 GPU-h left against a ~10 h night"** | Md | A1 | **23–26 GPU-h** | **−60%**, and already corrected 12.5 h earlier |
| `overnight_2026_08_13.sh` | **"the four jobs below total ~9.6 h"** | Md | A8 + assorted | **5.83 h** | **−39%** |
| `n_scaling_plan.md` | 13.0 s/eval at N=10 | Md | A5 | **12.87** | **−1%** ✓ |
| `n_scaling_plan.md` | **8.22 GPU-h recommended buy**; 3.27 / 4.11 / 11.48 / 0.49 / 0.62 GPU-h variants | Md | A8 | **4.82–5.02** and pro-rata | **−39%** |
| `n_scaling_plan.md` | KV 0.46 GB at N=40 vs 5804 MB measured peak | Md | arithmetic | **corroborated** — N=40 is live, no OOM | ✓ |
| `null_objective_ablation_plan.md` | 568–607 s/target | **M** | `/tmp/defb_chain.log` (since lost) | 586.5 | ✓ |
| `null_objective_ablation_plan.md` | 3.26 s / objective call | M-derived | ÷181 | sound | ✓ |
| `null_objective_ablation_plan.md` | **3.2–5.7 GPU-h gate (central ≈4)**; **"the gate adds ≈6%"** | Md | A6 | **8.3–18.9 (central ≈13.5)**; **≈25–50% of the corrected queue** | **+240%** |
| `null_objective_ablation_plan.md` | "28 targets ≈ 4.7 GPU-h left" | Md | A4 | **4.56** | **−3%** ✓ |
| `null_control_cost_options.md` | **22.8–25.9 GPU-h remaining**; 1191/1349 s/target; 26–30 targets/night; 3.6 GPU-h at risk on a ckpt-key change; m=30/36 restart costs | **M** | A2 | — | **current** ★ |
| `null_control_cost_options.md` §6F | **"judge ≈ 88% of a clustering, ~85% of the run"** | Md | **A6** | **≤46%** | **−48pp** |
| `null_control_cost_options.md` §9 | "20% judge win ≈ 4 GPU-h"; "single-ordering saves ~12 GPU-h" | Md | §6F | ~2.3; ~5.6 | halved; **both conclusions survive** |
| `judge_owed_conditions.md` | **3.11 GPU-h standalone (ii)+(iii)**; 2.31 at batch 12; 0.5 GPU-h pilot | Md | A9 | **0.74**; **0.11** | **−76%** |
| `judge_owed_conditions.md` | "judge ≈ 49 s — about 90% of the cost" | Md | A1−A7 | 11.13 s, ≤46% | refuted |
| `judge_owed_conditions.md` | "~71 GPU-h ≈ 3-day queue; the standalone adds ~4%" | Md | A1 | matrix now 0 + 23–26 GPU-h; adds **~3%** | — |
| `judge_owed_conditions.md` | 4,400 clusterings ≈ 1.5 kB each ≈ 7 MB | Md | arithmetic | low stakes, unchecked | — |
| `judge_owed_conditions.md` | ~3–4 h blinded annotation; ~7 h/week cadence; 0 of 123 pairs done | Md / M | recorded cadence | the binding constraint is human, not GPU | ✓ |
| `power_under_ceiling.md` | "far under the 228 GPU-hours we escaped"; "N=20 costs ~2× the sampling of N=10" | Md | A1 / linear-N | 99 GPU-h; **~1.47×**, since generation is flat | — |
| `derived_paper_quantities.md` / `.py:65` | **228 GPU-hours → 9.5 GPU-days** as a pinned `Input` | Md | A1 | 98.7 → 4.1 | **−57%** |
| `paper/sections/experiments.tex:173` | **"$228$ GPU-hours, about nine and a half GPU-days"** | Md | A1 | **~99 GPU-h, ~4.1 GPU-days** | **−57%** — in the paper |
| `decisions.md` 2026-05-30 | 14.27 s/Q → 71 h for 17,944 q → 2000-q subset, "about 8 hours" | M → Md | sustained 100-q run | actual 22,406 s = **6.2 h** (`run_all_status.txt`) | −22%, direction pre-announced ✓ |
| `rescore_likelihoods.py` | 80 tok/s floor; **0.1–5.5 h bracket**; benchmark **0.22 GPU-h** | M / Md / **M** | declared bracket + 90 s probe | **0.252 h** | **+5%** ★ |

**Three items with no recoverable provenance:** A10 (`judge_batch_size 6`), A11 (the "~10 h
night"), and `seps-transfer`'s absence of any estimate at all — a job admitted to the queue as
"cheapest" with no number attached, which turned out to be true (661 s) by luck rather than by
measurement.

---

## 4. Decisions the measurement reverses

### 4.1 The one already corrected — the null control's deprioritisation

`overnight_2026_08_13.sh:4`: *"It has ~60 GPU-h left against a ~10 h night, so it yields
nothing by morning."* At 1191 s/target a 10 h night yields **26–30 of the 69 remaining
targets** — over a third of the cell. The premise was false when it was written and the
correction was on disk. `null_control_cost_options.md` §9.2 already says this.

### 4.2 ★ The paper discloses a deviation trigger that is 2.3× too large

`experiments.tex:173`. The budget correction moved from brute-force matching to the analytic
exceedance null, *triggered by* a 228 GPU-h / 9.5 GPU-day price tag. The real price is ~99
GPU-h / ~4.1 GPU-days against the remaining window to the arXiv target. **The deviation
survives** — four days of a
shared card, serialised behind the null control and the matrix, is a real constraint — but the
sentence as written overstates its own trigger by 2.3×, in the one paragraph whose stated
purpose is to let a reviewer verify the rule was not tuned to the result. *Do not quietly
patch 228 → 99: the honest fix is to state the measured figure and note that the decision was
taken on the modelled one.* Also fix `derived_paper_quantities.py:65`, whose `Input` carries a
`source` pointing at a log entry rather than at a measurement.

Second-order, and larger: entry 22's judge:cheap ratio of **9.1× is really 1.9×**, so the
"cheap arms answer the budget curve, the judge anchors one point" architecture rests on a
tenfold gap that is really twofold — and the "affordable" cheap-arm alternative is 2.2
GPU-days, not one night.

### 4.3 ★ The null-objective gate is not a 6% add-on — it is a second null control

`null_objective_ablation_plan.md` §6: *"The gate is ~4 GPU-h against a 72-GPU-h queue and 33
days; 'no time' will not be a defence."* At the measured SE-eval cost the gate is
**8.3–18.9 GPU-h, central ≈13.5** — roughly **25–50% of the corrected 23–26 GPU-h null
control**, and about the same as re-running the real attack at n=80. The ordering advice
(run it after the null control, with `--benign_from`) is unaffected and still right. What
changes is that it is now a **priority decision**, not a rounding error, and it competes
directly with the null control it is meant to audit. Cutting n on the gate (it is already
scoped at "~10-15 targets" in `definitive_run_plan.md` step 2b, versus n=80 in §6's costing)
is the obvious lever and should be decided explicitly rather than inherited.

### 4.4 ★ The judge-conditions run is cheap enough that the risky edit is not needed

`judge_owed_conditions.md` §6.1 argues that the *only* free path to conditions (ii) and (iii)
is to instrument `null_control.py` **before** the null control launches, because the standalone
fallback costs 3.11 GPU-h and *"the window closes when the null control launches."* Two things
make that urgency evaporate:

- the standalone run is **0.74 GPU-h** (§2.7) — about 45 minutes, ~3% of the corrected null
  control, and it can be run at any time afterwards;
- `null_control.py` is under an explicit no-edit rule while the chain can reach it
  (`START_HERE_overnight.md`), and `null_control_cost_options.md` §9.2 documents the specific
  trap: `ckpt_cfg` is an exact-match dict, so adding a field silently invalidates all 11
  completed targets and throws away 3.6 GPU-h with no error.

**Trading a 3.6 GPU-h silent-corruption risk to save 0.74 GPU-h is a bad trade.** It was a
plausible trade at 3.11 GPU-h. Recommendation: drop the instrumentation urgency, take the
standalone route, and let `null_control.py` stay frozen. (The 12-target pilot that §6.2 makes a
prerequisite is now seven minutes, so it costs nothing to keep.)

### 4.5 "The null control is cheap and not the bottleneck — the attack is" is now backwards

`definitive_run_plan.md:78`. Measured: **1191 s per null-control target against 586.5 s per
attack target.** The null control is the more expensive unit by 2×, and at 23–26 GPU-h remaining
against a completed matrix it is now the *only* large item on the queue. The sentence dates
from before the budget-matched (B2) re-spec multiplied the null control's per-target work; it
should be struck rather than adjusted.

### 4.6 Tonight has 3.8 GPU-h of slack that nothing is scheduled against

§2.8. The queue will finish around **04:50**, not ~08:30. At 1191 s/target that slack is
**~11 null-control targets**, or the whole 0.74 GPU-h judge-conditions run with three hours to
spare. Nothing is queued to use it. This is not a reversal of a decision so much as a decision
that was never made, because the capacity number (A11, "a ~10 h night") and the demand number
(9.6 h) were both unmeasured and happened to cancel.

### 4.7 Decisions the measurement does **not** reverse — stated because an audit that only finds problems is not credible

- **Finish the null control at m=50** (`null_control_cost_options.md` §9). Built on A2, the
  measured anchor. Stands.
- **Buy one N=40 pass and replay** (`n_scaling_plan.md` §8.1). The saving over
  measuring-every-budget-directly shrinks from 3.3 to ~2.2 GPU-h, and the replay argument was
  never about cost. Stands; it is running.
- **Ten minutes on `judge_batch_size` before relaunching.** Worth ~2.3 GPU-h, not ~4. Stands —
  but note A10: the number it would replace has *no* provenance, and
  `probe_batched_judge.py` does not measure throughput. Something else has to.
- **Single-ordering judge: not worth it.** Saves ~5.6 GPU-h, not ~12, and still costs a
  re-validation of the one judge figure the paper cites. Strengthened.
- **The 2026-05-30 subset decision** (`decisions.md`) — measured at 14.27 s/Q, projected 8 h,
  came in at 6.2 h, with the direction of the error pre-announced. This is the project doing it
  right, in week 2, and the same entry already records the lesson: *"The Monday projection …
  was based on a single-question warmup measurement and was wrong; Friday's sustained
  100-question number is the real baseline."* The failure this audit documents is the same
  failure, eleven weeks later, with the lesson already written down.

---

## 5. The guard

### 5.1 Verdict: mechanisable in three parts out of four — and the fourth is the one that bit us

| what | mechanisable? | why |
|---|---|---|
| **(a)** an operational figure in a live planning doc carries a `MEASURED` / `MODELLED` tag | **yes** — regex on numbers, attachment window, exactly `check_population_labels.py`'s shape | but it cannot start green (see 5.3), so it must be a **ratchet**, not a gate |
| **(b)** a known-dead anchor has reappeared | **yes**, and this is the high-value rule — zero baseline, zero ambiguity | this is literally what happened: `55 s` → `67 GPU-h` → `60 GPU-h` → a scheduling decision |
| **(c)** a modelled figure whose underlying job has since produced an artifact | **yes, but only if the figure declares its own trigger** | a checker cannot infer that `results/null_control_ckpt_defb.jsonl` supersedes "~67 GPU-h". It *can* enforce that a `MODELLED` tag names a path, and fail when that path appears on disk. Existence is binary and cheap |
| **(d)** **is this anchor the right anchor for this job** | **no. Not now, not ever.** | Nothing in the string `55 s` says it came from K=8. Nothing in `2.8 s` says it is a pro-rata token split of a call that also does 480 tokens of generation. Nothing in `73.9 s` says generation was assumed linear in N when it is flat. **Every failure in §2 is a type-(d) failure.** The only defence is that the tag *names the anchor in prose*, which makes it visible to a human in the same glance as the number |

So: a checker buys (b) and (c) outright, (a) as a ratchet, and **converts (d) from invisible to
merely un-automated** by forcing the anchor to be written down next to the number. That last
part is the real value, and it is worth saying plainly: the script's job is not to catch the
error, it is to make the error *legible*.

### 5.2 One rule that is fully mechanisable with zero false positives

A hard-coded countdown of the form *"N days to the arXiv target"* appears in five live
documents and is monotone in time — the exact shape the project already learned to distrust
for sample statistics (*"Ask 'monotone in n?' before any count enters a sentence"*). Every one
of them still says 33; it is 32 today. A checker can compute
`(target_date − today).days` and compare. No judgement, no window, no attachment logic.
Implemented as `stale-countdown`.

### 5.3 Why (a) cannot be a hard gate: most of these numbers are script-generated

`n_scaling_plan.md`, `null_control_cost_options.md`, `judge_owed_conditions.md`,
`null_objective_ablation_plan.md` and `derived_paper_quantities.md` are **emitted by scripts**.
Hand-tagging them is wrong — the next run overwrites the tags — and the fix belongs in the
generators. `n_scaling_grid.py` in particular is off-limits while the queue is on it. A
blanket "every GPU-h figure must be tagged" gate would therefore be red on arrival, across
files nobody can currently fix, and the repo already knows what happens next: *"A green test
suite next to a known-broken statistic reads as validation of it"* — and a permanently red one
reads as nothing at all.

Hence: **rule (a) is a per-file ratchet with an explicit debt register.** It fails when a file
gains an untagged figure, not because it has some. The register is a list, in the checker, of
the exact sites that are open today — which is the same device `check_population_labels.py`
uses for `SUPERSEDED`, and it worked there.

### 5.4 What is implemented

`scripts/check_operational_provenance.py`, tests in `tests/test_operational_provenance.py`
(57 tests, all passing). Five rules, scoped to **live planning documents**
(`docs/START_HERE_overnight.md`, `docs/definitive_run_plan.md`, `docs/framing_decision.md`,
`docs/revised_plan_wk9_17.md`, `results/*_plan.md`, `results/*_options.md`,
`results/derived_paper_quantities.md`, `results/judge_owed_conditions.md`,
`results/power_under_ceiling.md`, `paper/sections/*.tex`, `scripts/overnight_*.sh`).

**Out of scope, each for a stated reason.** `docs/critique_log.md` and
`results/OVERNIGHT_*.md`: append-only history, and rewriting history to satisfy a linter is
worse than the disease — the danger from the log was never that it *contains* a dead number
(entry 22's 55 s was correct for K=8) but that it gets *quoted forward*, and forward is where
the scope is. **This file too**, for the same reason: a register of dead anchors and their
replacements has to be able to name them, and scoping it in would mean the guard's own
evidence may not cite its own evidence.

1. **`dead-anchor`** — a literal from `DEAD_ANCHORS` (`55 s/clustering`, `228 GPU-h`,
   `~67 GPU-h`, `~60 GPU-h`, `73.9 s/eval`, `2.8 s` as an SE-eval unit, `6.1 s` as a
   cheap-arm unit, `67 s` as a judge-clustering unit) appearing **without a retirement marker
   in the enclosing paragraph**. Each entry carries its replacement, printed in the failure
   message — a guard that says "wrong" without saying "use this instead" gets worked around.
   Disambiguating context is matched on **both sides** of the number, because "a judge
   clustering costs 67 s" and "67 s per clustering" are the same claim and a lookahead-only
   rule blesses one of them.
2. **`untagged`** — an operational figure (`N GPU-h(ours)`, `N GPU-day(s)`, `N s/eval`,
   `N s/target`, `N s/clustering`, `N s/question`, `N s/Q`, `N min/target`, `N nights`) with no
   `MEASURED` / `MODELLED` / `UNMEASURED` tag in its sentence or table row. **Ratcheted**
   against `KNOWN_OPEN`; a file that drops *below* its baseline also fails, so the register
   cannot rot upward while the docs are cleaned.
3. **`anchorless-model`** — a `MODELLED` tag that does not name what it was modelled from
   (`from …` / `via …` / a path / a `critique_log NN` reference). This is the type-(d)
   mitigation: it does not check the anchor, it forces the anchor to be *written*.
4. **`supersede-trigger`** — a `MODELLED` tag may declare `supersede-when: <path>`. If that
   path exists on disk, the figure is owed a re-derivation and the check fails. This is
   "re-derive once any of that work has run", in the only form a script can enforce.
5. **`stale-countdown`** — `N days to YYYY-MM-DD` must equal today's actual difference.

Two implementation notes worth carrying forward, because both were near-misses:

- **The retirement window is the paragraph, not the sentence** (a correction reads across two
  sentences), and it stops at the paragraph (a "superseded" in a summary at the bottom of a
  400-line plan must not bless every live restatement above it). An early draft counted
  `correction` as a retirement marker — and `experiments.tex`'s paragraph contains *"the
  budget correction then moved …"*, so the widening silently laundered **the one dead anchor
  that reached the paper**. Pinned as
  `test_the_paragraph_window_does_not_launder_the_papers_dead_anchor`.
- **`strip_markup` must not eat `_`.** Blanking underscores turns
  `supersede-when: results/null_control_ckpt_defb.jsonl` into a path that does not exist,
  which silently disarms the only rule that fires on real evidence.

`main()` returns non-zero on any finding. The suite pairs every probe with a **control** — the
same claim written correctly — because a rule that flags everything is not a rule, and
`check_population_labels.py`'s first version failed exactly there.

### 5.5 First run: 28 findings, zero false positives

| file | rule | anchor | n |
|---|---|---|---|
| `paper/sections/experiments.tex` | dead-anchor | 228 GPU-h | 1 |
| `results/n_scaling_plan.md` | dead-anchor | 73.9 s/eval | 6 |
| `results/n_scaling_plan.md` | dead-anchor | ~67 GPU-h | 2 |
| `results/null_objective_ablation_plan.md` | dead-anchor | 2.8 s/SE-eval | 3 |
| `results/null_objective_ablation_plan.md` | dead-anchor | ~67 GPU-h | 2 |
| `results/null_control_cost_options.md` | dead-anchor | 2.8 s/SE-eval | 1 |
| `results/judge_owed_conditions.md` | dead-anchor | 55 s, 6.1 s, ~67 GPU-h | 3 |
| `results/derived_paper_quantities.md` | dead-anchor | 228 GPU-h | 2 |
| `results/power_under_ceiling.md` | dead-anchor | 228 GPU-h | 1 |
| `docs/START_HERE_overnight.md` | dead-anchor | ~67 GPU-h | 1 |
| `docs/definitive_run_plan.md` | dead-anchor | ~67 GPU-h | 1 |
| `scripts/overnight_2026_08_13.sh` | dead-anchor | ~60 GPU-h | 2 |
| four files | stale-countdown | 33 vs 32 days | 3 |

**None of these can be fixed from here** and that is the point of the ratchet: five of the
files are script-generated, `overnight_2026_08_13.sh` is on the GPU under a no-edit rule, and
`experiments.tex` needs a rewrite rather than a substitution. They are pinned in
`KNOWN_SITES`, so a *new* forward-quotation fails the suite while these stay visible as debt.
There is deliberately **no** `test_the_repo_is_green` — the repo is not green, and this
project's own rule says to pin the failure rather than assert around it.

The rule that caught the sharpest finding in this audit is `dead-anchor` on
`null_control_cost_options.md` §6F: the document that corrected the 67 GPU-h figure importing
the discredited 2.8 s/eval from the very file it was correcting. A person had already read
that document twice.

### 5.6 And the checklist, because the script does not cover (d)

Four lines, at the point of writing a cost — not a review gate, because review gates are what
failed here:

> 1. **Name the anchor in the sentence.** Not "≈4 GPU-h" — "≈4 GPU-h [MODELLED from
>    `null_objective_ablation_plan.md` §6's 2.8 s/eval]".
> 2. **State the anchor's own operating point.** K, N, batch size, which models were resident.
>    A1 was measured at K=8/batch 12 and spent on K=50/batch 6; A8 was measured at N=10 and
>    spent on N=40. Both would have been caught by one clause.
> 3. **Say what would supersede it.** A path. If that path already exists, you are not
>    modelling, you are declining to measure.
> 4. **Before spending it: does an hour of this job already exist on disk?** If yes, divide.
>    Three filesystem anchors and a division beat any model in this repo, every time.

And one process rule, for `docs/critique_log.md`'s "Process rules, learned the hard way":

> **Cost a job from the job, not from a probe of a smaller job.** A per-unit rate measured at
> one scale is a *bound*, not a rate, until it is re-measured at the scale you intend to spend
> at. Every operational number this project got wrong was a small-scale probe spent at large
> scale: a K=8 probe costing K=50, an N=10 rate costing N=40, a single-question warmup costing
> 17,944 questions. The last of those is in `decisions.md` from week 2.

---

## 6. What this audit could not check

- **A10.** No throughput measurement of the judge at any batch size exists. §2.3's 11.13 s is
  a *difference* of two measurements, not a direct one, and it assumes the null control's
  generation half costs what `winners_curse_reeval`'s does. Co-residency can only make the
  cheap half dearer, so 46% is an upper bound on the judge's share and the direction is safe —
  but the number itself wants twenty minutes on an idle card.
- **The wall/compute ratio.** Observed between 1.00× and 2.28× on the same chain. Nothing in
  the repo records device contention, so "GPU-h" cannot currently be converted to "will it
  finish tonight" with any stated error.
- **`/tmp/defb_chain.log` is gone** (WSL restart, 22:56 on 2026-08-13), so the hide cell's
  per-target timings are irrecoverable and §2.5 is a span/count average over a 28-target
  segment, not 28 timings.
- **§2.2's N=40 figure is an interim** — 43 of 400 evaluations, correct stratum only. The
  hallucinating stratum generates longer refusal-style answers and may cost more. Re-derive at
  completion; the direction of the −39% will not change (generation is flat and NLI is fixed
  by N), but the magnitude may.
- **`n_scaling_plan.md` cannot be corrected in place** — it is emitted by `n_scaling_grid.py`,
  which is off-limits while the queue is on it. The fix is a one-line change to that script's
  generation-scaling term, queued for when the device is idle.
