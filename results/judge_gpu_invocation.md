# How to run the owed judge GPU job (conditions ii and iii) — 2026-08-29

**Scope of this file.** It answers one question: *what is the exact command that closes judge
conditions (ii) and (iii)?* Written read-only. **Nothing here was run on the GPU, no GPU work
was launched, no script was edited, no file outside this one was written, and no STOP file of
any spelling was created.** Every claim below is tagged **MEASURED** (an artifact and the
measurement are named), **DERIVED** (arithmetic from measured inputs, shown inline), or
**ASSUMED** (the assumption is named). An untagged number would be the failure mode this
project has already paid for.

---

## 0. The answer, first

**No script in this repository closes (ii) or (iii).** All five candidates were opened and
read; every one is disqualified for a specific reason given in §2. The honest deliverable is
therefore in two halves:

1. **§3 — the exact command**, for a script that **must first be written**
   (`scripts/judge_conditions_run.py`, ~2 files, spec in §4). It does not exist today.
2. **§2 — the commands that do exist and what each would actually do**, including one that
   silently clobbers the file pinning the judge's 0.93.

**Do not launch anything tonight.** Two preconditions in §7 are decisions, not flags, and one
of them (the pre-registered margin Δ\*) must be fixed **before** the run, in writing, or the
result is unusable no matter how the GPU behaves.

**One thing got cheaper since 2026-08-13 and nobody has noticed** (§8): the completed null
control makes the judge's **cluster counts** on all 80 targets, both conditions, recoverable
from disk for **zero GPU**. That closes δ_K — the demoted, descriptive statistic — and it is
worth computing on CPU before the GPU run, because it is a free prior on what the GPU run will
find. It does **not** close (ii) or (iii); those need the sample texts, which are gone.

---

## 1. What (ii) and (iii) are, verified against the source

**MEASURED**, `results/judge_validation.md`, final paragraph — the file's own owed list:

> (ii) validate on messy real sampled pairs, not just clean gold aliases; (iii) a
> differential-over-splitting check (attack vs benign cluster counts must not diverge)

The design that closes both is **J1**, `results/judge_owed_conditions.md` §6.2, with estimands
pre-registered in §4.1–§4.4 and §7 of that file:

| statistic | what it needs | on disk after the null control? |
|---|---|---|
| **δ_bias** (primary) = mean_t[bias^att − bias^ben], bias = H(J) − H(J with oracle-positive pairs force-merged) | judge **cluster assignments** + `samples_correct`, both conditions | **no** — assignments never stored |
| **δ_φ** = per-pair false-split-rate difference | judge **per-pair verdicts** + oracle labels | **no** |
| **δ_α** = order-asymmetry rate difference (`ab != ba`) | the **ab/ba disagreement flags** | **no** — computed then discarded in `make_batched_judge_fn` |
| **δ_K** (descriptive, never a claim statistic) | cluster **counts** only | **YES, free — see §8** |
| **(ii) machine half** | judge accuracy on real sampled pairs, per condition | benign side yes, attacked side **no** |

§5.4 of `judge_owed_conditions.md` is right and load-bearing: **(ii) and (iii) are one
experiment.** φ^benign and φ^attacked are the same measurement made twice; δ_φ is their
difference. They must not be scheduled separately.

---

## 2. The candidate scripts, each opened and each disqualified

### 2.1 `scripts/judge_owed_conditions.py` — **the trap I was warned about; confirmed**

Its own header, line 36: `NO GPU. NO MODEL. Standalone stdlib so it runs while the device is
busy.` It produces the entropy lattice, the inverter validation, the **NLI-only**
(iii)-preliminary, the (ii) inventory, and **the cost model**. It is the document generator for
`results/judge_owed_conditions.md`. **It is not the measurement.** Running it consumes no GPU
and closes nothing.

Two further hazards in it, both real:
- `--tags` **defaults to `wk9_def,wk9_defb`** (`:331`) — it reads the **superseded** campaign by
  default and prints its numbers next to the live ones. Its output is safe only because it
  labels every row with the tag it came from.
- `--out` writes wherever it is pointed. Default is `""` (writes nothing). Leave it empty.

### 2.2 `scripts/validate_judge.py` — closes condition **(i)**, and **clobbers the 0.93**

It scores the judge on `_alias_strata()` from `calibrate_embed_threshold.py`: **TriviaQA gold
aliases**, i.e. `Broncos` / `Denver Broncos`. That is precisely the population (ii) exists to
move away from — `judge_owed_conditions.md` §5.1 measures the deployed inputs at **mean 19.6
words, median 17, 99.0% longer than three words** (MEASURED, cached samples). Wrong population,
and no condition contrast at all, so it cannot touch (iii).

**Clobber warning, and it is the sharpest one on this page.** `validate_judge.py:88` does
`out = RESULTS_DIR / "judge_validation.md"; out.write_text(...)` — an **unconditional
overwrite** of the file that pins the deployed judge at 0.93 [0.90, 0.96]. The strata are
seeded (`random.Random(0)`) and the judge decodes greedily (`do_sample=False`), so it is
*intended* to reproduce; that is **ASSUMED**, not measured, and it has never been re-run to
confirm it. `results/judge_validation.md` is git-tracked and currently clean (MEASURED:
`git status --porcelain` shows only `results/null_control_report.md` modified), so an accidental
overwrite is recoverable with `git checkout --`. **Do not run this script.** Condition (i) is
already closed and the number is already pinned — `scripts/check_population_labels.py` guards
`0\.93(?!\d)` in a `judge_val`-owned 420-character window.

### 2.3 `scripts/probe_batched_judge.py` — a **correctness** gate, not a measurement

Checks `batched verdict == unbatched verdict` on 18 hand-written short-entity pairs. Writes
nothing (stdout only). Needs the GPU and **loads Qwen twice** (its own header: "~10 GB at
4-bit" — twice that on a 16 GB card is a live OOM risk; **ASSUMED**, no probe on record).
Produces neither (ii) nor (iii). `results/operational_number_audit.md` A10 is explicit that it
"does not measure throughput" either. **Optional; see §7.4 — I recommend skipping it.**

### 2.4 `scripts/null_control.py` — no flag can do this, and the free window is spent

**MEASURED**, the complete argparse (`:254`–`:281`, eleven flags): `--tag --only --K --n_seeds
--max_targets --embedding_model --embed_threshold --judge_model --judge_batched
--judge_batch_size --dump_diag --checkpoint`. **There is no `--dump_judge_detail` and nothing
resembling one.** `results/schedule_2026_08_26.md` §1.2 discusses "adding `--dump_judge_detail`"
as a hypothetical edit, not an existing flag; it does not exist.

`_arms()` (`:139`–`:158`) returns **four floats** and drops `res.samples` and every
`ClusterResult.assignments`. `--dump_diag` does not help: I read `results/diag_defb.json`
(80 records) and it carries **exactly the checkpoint's fields** — `baseline`, `attack_move`,
`benign`, `seed`, four arms each, all scalars and lists of scalars. No assignments, no samples,
no ab/ba flags. **MEASURED.**

Three independent reasons this route is closed:
- **Editing `null_control.py` is forbidden** by the standing constraint, and by
  `judge_owed_conditions.md` §6.1 on ownership grounds.
- **The checkpoint keys reuse on the whole cfg dict** (`:338`). Any cfg change makes all 80
  completed records non-matching and restarts at target 1 — at the measured 1196.58 s/target
  (`schedule_2026_08_26.md` §1.1, 20 intervals) that is **26.6 GPU-h** thrown away to save 0.74.
- **The window described in §6.1 has already closed.** The run finished at 03:57 today with 80
  targets; the 4,400 judge clusterings it could have instrumented are spent.

### 2.5 `scripts/null_control_cost_options.py` — CPU costing

Header line 3: "Read-only. Launches NO GPU work." Writes
`results/null_control_cost_options.md`. Reads the **Windows-side snapshot**
`data/cache/attacks/wk9_defb_snap/` (`:67`). Nothing to do with (ii)/(iii).

---

## 3. The exact command

**This command does not work today. `scripts/judge_conditions_run.py` must be written first
(§4).** I have specified it so that the command below is the contract the script is written
against, rather than the other way round.

Run inside WSL, from the repo root, on a free GPU, in three passes:

```bash
wsl -d Ubuntu-24.04
cd "/mnt/i/GITHUBPROJECTS/SE Research"
export HF_HOME=/home/abhi/.cache/huggingface

# ---- PASS 0: pilot, 12 targets, ~7 min. Do not skip. ------------------------
./.venv-wsl/bin/python scripts/judge_conditions_run.py \
    --tag _defb \
    --only false_alarm \
    --stage all \
    --max_targets 12 \
    --judge_model Qwen/Qwen2.5-7B-Instruct \
    --judge_batched \
    --judge_batch_size 6 \
    --verify_entropy_after \
    --samples_out  data/cache/judge_cond/qprime_samples_defb.jsonl \
    --checkpoint   results/judge_cond_ckpt_defb.jsonl \
    --out          results/judge_conditions_pilot.md

# ---- PASS 1: victim generation under q', 80 targets, Llama+DeBERTa only -----
./.venv-wsl/bin/python scripts/judge_conditions_run.py \
    --tag _defb \
    --only false_alarm \
    --stage generate \
    --verify_entropy_after \
    --samples_out  data/cache/judge_cond/qprime_samples_defb.jsonl \
    --checkpoint   results/judge_cond_ckpt_defb.jsonl

# ---- PASS 2: judge clustering, 160 clusterings, Qwen alone -----------------
./.venv-wsl/bin/python scripts/judge_conditions_run.py \
    --tag _defb \
    --only false_alarm \
    --stage judge \
    --judge_model Qwen/Qwen2.5-7B-Instruct \
    --judge_batched \
    --judge_batch_size 6 \
    --samples_in   data/cache/judge_cond/qprime_samples_defb.jsonl \
    --detail_out   results/judge_cond_detail_defb.jsonl \
    --checkpoint   results/judge_cond_ckpt_defb.jsonl

# ---- PASS 3: analysis, CPU only, no model, re-runnable ---------------------
./.venv-wsl/bin/python scripts/judge_conditions_run.py \
    --stage analyse \
    --detail_in    results/judge_cond_detail_defb.jsonl \
    --margin_frac  0.20 \
    --effect_nats  <SEE §7.1 — MUST BE FIXED IN WRITING BEFORE PASS 1> \
    --n_boot 20000 --seed 0 \
    --out          results/judge_conditions_result.md
```

### What each flag is for

| flag | why |
|---|---|
| `--tag _defb` | selects `~/.cache/se-research/samples/attacks/wk9_defb` — `null_control.py:286` shows the mapping is literally `"wk9" + tag`. **This is the trap; see §5.** |
| `--only false_alarm` | the judge is scoped to FA only (`judge_validation.md`: over-splitting is conservative for FA, **not** for hide). The hide cell is un-adjudicable by this oracle and costs GPU for a number that cannot be used. Same reasoning as `run_definitive_chain.sh:8-15`. |
| `--stage generate\|judge\|analyse\|all` | the two-pass split `judge_owed_conditions.md` §6.2 asks for: it avoids Llama+DeBERTa+Qwen co-residency, which is what forced `judge_batch_size` down to 6 in the first place. `analyse` needs no GPU and can be re-run freely. |
| `--max_targets 12` | the pilot §6.2 pre-registers, to estimate the paired SD of δ_bias before committing the rest. **DERIVED cost: 24 × 11.13 + 12 × 11.21 = 401.6 s ≈ 6.7 min.** |
| `--judge_model Qwen/Qwen2.5-7B-Instruct` | the deployed judge. Identical string to the null control's and to `judge_validation.md`'s. |
| `--judge_batched` | one GPU batch per clustering. Verdict-identical to unbatched (that is `probe_batched_judge.py`'s claim) and ~10–20× faster. The null control ran with it; matching it keeps the config identical. |
| `--judge_batch_size 6` | the deployed value. `overnight_2026_08_14.sh:8-10` records *why*: a documented HSA allocator failure at 12. 6 is known-good. **Do not "optimise" this** — §7.4. |
| `--verify_entropy_after` | the acceptance test in §6.3. Costs one NLI clustering per target (**DERIVED: 80 × 1.75 s = 140 s**) and is the only evidence the regenerated q′ samples are the ones the campaign scored. |
| `--samples_out` / `--samples_in` | the q′ sample cache that joins pass 1 to pass 2. Under `data/cache/`, which `.gitignore` already covers. |
| `--detail_out` / `--detail_in` | per-target assignments + per-pair verdicts + ab/ba flags — the raw material for δ_bias, δ_φ, δ_α. **The thing whose absence is the entire problem.** |
| `--checkpoint` | per-target resume; see §6. |
| `--margin_frac 0.20` | the **fraction** is what §7 of `judge_owed_conditions.md` pre-registers. It may not be revised after seeing data. |
| `--effect_nats` | the reference effect Δ\* is 20% of. **Open decision — §7.1.** |
| `--n_boot 20000 --seed 0` | pre-registered: paired percentile bootstrap, 20,000 draws, seed 0. |
| `--out` | the report. Distinct filenames for pilot and full run so the pilot cannot overwrite the result. |

### Symmetric config — confirmed, and it is the default

`judge_validation.md` pins **0.93 [0.90, 0.96], n=300, symmetric**. **MEASURED**:
`src/se/judge.py:95-97` — `load_judge(model_id=..., max_new_tokens=3, load_in_4bit=True,
symmetric: bool = True, batched=False, judge_batch_size=12)`. `validate_judge.py:44` passes
`symmetric=not args.asymmetric` → **True** by default; `null_control.py:308` passes **no
`symmetric` argument at all** → also **True**. So the validated config, the deployed config, and
the default are the same object. **The new script must call `load_judge` without a `symmetric`
argument and must not expose an `--asymmetric` flag**, so there is no way to run the wrong one
by accident. δ_α is only meaningful under the symmetric judge anyway: it counts pairs where the
two orderings disagree, which under `symmetric=True` are exactly the splits decided by an
arbitrary tie-break.

---

## 4. What has to be written

`scripts/judge_conditions_run.py`, new file, plus `tests/test_judge_conditions_run.py`.
It must **not** import from or edit `null_control.py`. It should import the estimator helpers
that already exist and are already unit-tested in `scripts/judge_owed_conditions.py`:
`noninferiority_verdict`, `paired_bootstrap_ci`, `sign_test_p`, `oracle_pair_strata`,
`false_split_rate`, `wilson_ci`, `build_k_lattice`, `invert_cluster_count`. Re-implementing any
of those is how a second arithmetic defect gets in.

Required behaviour, stage by stage:

- **`generate`** — for each FA target, read `best_query` from the campaign JSONL; call
  `se.se_pipeline.semantic_entropy(best_query, pair.lm, pair.nli, GenConfig(max_new_tokens=48,
  temperature=1.0, top_p=1.0, n_samples=10, seed=0), example=ex)`; persist `res.samples` **and**
  `res.samples_correct` (the latter is what supplies the free oracle labels). Under
  `--verify_entropy_after`, assert `res.entropy_nats == entropy_after` and record the result
  per target rather than crashing.
- **`judge`** — for the **benign** arm read the cached clean samples from
  `~/.cache/se-research/samples/wk4_full_2000q/samples.jsonl` (**no generation**); for the
  **attacked** arm read the pass-1 cache. Cluster both with the batched judge, and persist, per
  target and per condition: `assignments`, `n_clusters`, `entropy_nats`, `samples`,
  `samples_correct`, and the **per-pair `(i, j, ab, ba)` verdicts**. The ab/ba flags require the
  batched judge to surface both orderings — `make_batched_judge_fn` (`se/judge.py:68-93`)
  computes both and returns only their conjunction, so the new script must call the underlying
  `generate_batch_fn` itself rather than the wrapped predicate. **This is the only non-obvious
  piece of engineering in the whole job.**
- **`analyse`** — CPU only. Build `O^c(t)` by force-merging oracle-positive pairs, compute
  δ_bias, δ_φ, δ_α, δ_K, run the bootstrap/sign/Wilcoxon, and print
  `noninferiority_verdict(...)` per statistic. Report **all four** statistics even when the
  primary passes, per §7.7 of the pre-registration: any one FAIL forces withdrawal, uncorrected.

**Do not add a `--fresh_seed` or any reseeding option.** The point of `seed=0` is that it
reproduces the campaign's own attacked samples; see §6.3.

---

## 5. The campaign tag, and how I verified it

**The tag is `_defb` → `wk9_defb`.** Four independent checks, three of them empirical:

1. **The mapping is literal.** `null_control.py:286`: `campaign_dir = DEFAULT_SAMPLES_DIR /
   "attacks" / f"wk9{args.tag}"`. So `--tag _defb` → `~/.cache/se-research/samples/attacks/wk9_defb`.
   **MEASURED** (source read).
2. **The repo's own linter names both.** `scripts/check_population_labels.py:1853-1854`:
   `SUPERSEDED_RUN = "wk9_def"` / `CURRENT_RUN = "wk9_defb"`. **MEASURED.**
3. **The completed null control is bolted to `wk9_defb`, not to `wk9_def`.** Both cells hold
   **80 rows and the same 80 `question_id`s**, and both have `entropy_before` identical on
   80/80 — so identity checks on ids or on the baseline **cannot** tell them apart. The
   attacked side can. Reconstructing the null control's attacked NLI entropy as
   `baseline.nli + attack_move.nli` and comparing it to each campaign's `entropy_after`:

   | campaign | matches (tol 1e-9) |
   |---|---|
   | `wk9_defb` | **80 / 80** |
   | `wk9_def` | 69 / 80 |

   **MEASURED**, this session, read-only over `results/null_control_ckpt_defb.jsonl` and both
   cache files.
4. **The trap is quantified, and it is worse than "a wrong label".** The two cells share all 80
   `question_id`s but **`best_query` differs on 44 of 80** (MEASURED). A J1 run pointed at
   `_def` would therefore regenerate samples under **retired paraphrases on 55% of targets**,
   produce a plausible-looking 80-row output, and match on every id — the failure would be
   invisible to any id-based or n-based check. `results/CORRECTIONS_2026-08-02.md:79` and
   `results/ceiling_saturation_finding.md:4` both flag `wk9_def` as superseded.

**Bonus, and it discharges an owed item.** `PREREG_noop_convention_2026_08_28.md` §6 says the
audit behind it read the Windows snapshot `data/cache/attacks/wk9_defb_snap/` (2026-08-13) and
owes a re-check against the live directory. For the **FA cell** that re-check passes: the
snapshot and the live WSL file are **byte-identical** (md5 `24ffbc159468924cc922449a688aa4bc`
both, MEASURED). The **hide** cell is *not* identical (`0a58c2d7…` live vs the snapshot's
partial 52-record copy), so the owed re-check still stands for hide — which J1 does not touch.

---

## 6. Inputs, outputs, resumability

### 6.1 Every path it reads (all read-only)

| path | why | mutated? |
|---|---|---|
| `~/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl` | `best_query`, `entropy_before`, `entropy_after`, `question_id` (80 rows) | **no** |
| `~/.cache/se-research/samples/wk4_full_2000q/samples.jsonl` | the benign arm's 10 sample texts + `samples_correct`. **Coverage verified: 80 of 80 FA targets present** (MEASURED) | **no** |
| `~/.cache/se-research/samples/wk4_full_2000q/entropy.jsonl` | benign `n_clusters` under NLI, for δ_K's control arm | **no** |
| `results/null_control_ckpt_defb.jsonl` | `baseline.judge` per target, for the §6.3 acceptance test | **no — read only, per the standing constraint** |
| `~/.cache/huggingface` | Llama-3.1-8B-Instruct, deberta-large-mnli, Qwen2.5-7B-Instruct — **all three present, 33 GB** (MEASURED). No download, no network | **no** |

### 6.2 Every path it writes — nothing existing is touched

| path | mode | note |
|---|---|---|
| `data/cache/judge_cond/qprime_samples_defb.jsonl` | **append**, per target | new dir; `.gitignore` already covers `data/cache/` |
| `results/judge_cond_detail_defb.jsonl` | **append**, per target/condition | new file |
| `results/judge_cond_ckpt_defb.jsonl` | **append**, per target | new file |
| `results/judge_conditions_pilot.md` | overwrite | new file, pilot only |
| `results/judge_conditions_result.md` | overwrite | new file |

**No existing artifact is opened for writing.** In particular the run must **never** write
`results/judge_validation.md` (that is `validate_judge.py`'s output — §2.2),
`results/judge_owed_conditions.md`, `results/null_control_report.md`,
`results/null_control_ckpt_defb.jsonl`, or `results/diag_defb.json`. The new filenames were
chosen to collide with nothing: `ls results/` confirms none of the five exist today (MEASURED).

### 6.3 The acceptance test — run it before believing any δ

Two checks that cost almost nothing and that catch the two ways this run can be silently wrong:

- **Attacked side.** `--verify_entropy_after` asserts the regenerated q′ samples reproduce the
  campaign's `entropy_after` under NLI. This is credible because generation is deterministic
  given `(question, seed)`: `se/model.py:102-103` does `torch.manual_seed(gen.seed)` on every
  call, and the null control **independently reproduced** the campaign's `entropy_before` on
  **80/80** targets days later (MEASURED: `baseline.nli == entropy_before`, 80/80, tol 1e-12).
  That is the strongest available evidence that a fresh `seed=0` draw reproduces a stored one.
  It is evidence, not proof — a driver or library change between then and now could break it,
  which is exactly why the assertion is in the run rather than in this document.
- **Benign side.** The judge entropy of the cached clean samples must equal
  `baseline.judge` from `null_control_ckpt_defb.jsonl` on all 80 targets. The null control
  already computed precisely this quantity. If it disagrees, the judge config drifted and the
  run is void.

A run that fails either check should stop, not be reported.

### 6.4 Resumable, and the cost of an interruption

Not automatically — **the checkpoint has to be part of the spec**, which is why it is in §4.
With it, following `null_control.py`'s own pattern (append one JSON line per completed unit,
skip on resume, cfg recorded in each record):

| interrupted during | lost |
|---|---|
| pass 0 (pilot) | ≤ 34 s (one target: 11.21 gen + 2 × 11.13 judge) — **DERIVED** |
| pass 1 (generate) | ≤ **11.2 s**, one target's generation |
| pass 2 (judge) | ≤ **11.1 s**, one clustering |
| pass 3 (analyse) | nothing — CPU, idempotent, re-runnable |

**The two-pass split is what makes this cheap.** A crash at the end of a single-pass run would
lose the generations too. And unlike the null control, the checkpoint here **must not key reuse
on a hash of the whole cfg** — key it on `(question_id, condition, stage)` plus the judge model
id and batch size, so that adding an unrelated flag later does not invalidate 80 completed
records the way `null_control.py:338` would. That defect cost this project a 26.6 GPU-h
hostage; do not reproduce it.

### 6.5 Cost

**DERIVED** from `results/operational_number_audit.md` §2.3/§2.7 anchors:

```
160 judge clusterings x 11.13 s  =  1,780.8 s     (2 conditions x 80 targets)
 80 victim generations x 11.21 s =    896.8 s
                                   ---------
                                    2,677.6 s  =  0.744 GPU-h
+ 80 NLI verifications x 1.75 s  =    140.0 s
                                   ---------
                                    2,817.6 s  =  0.78 GPU-h  with the acceptance test
```

**A small arithmetic slip, flagged for the record:** `operational_number_audit.md` §2.7 writes
this sum as **2,673 s**; it is **2,677.6 s**. 0.2%, immaterial to every decision, and both round
to 0.74 GPU-h — but the line is tagged with measured inputs, so the arithmetic should be right.

**How much to trust 0.74.** The 11.13 s judge increment is itself **DERIVED** as
`24.0 − 12.87` (§2.3 of that audit), where 12.87 s was measured *without* Qwen co-resident;
the audit argues correctly that this makes 11.13 an **upper bound** on the judge increment. In
pass 2 Qwen runs alone, with no Llama or DeBERTa competing for the 16 GB, so the real figure
should be **at or below** 11.13. The 11.21 s generation figure is anchor A5, obtained by
subtraction from a Phase-1 sampling loop — tagged M in the audit, but a subtraction. **I would
quote 0.74–0.78 GPU-h as an upper bound and expect the run to come in under it.** It is ~4.6%
of one observed overnight launch (7.37 h, MEASURED, `schedule_2026_08_26.md` §1.1). Cost is not
the constraint here; §7.1 is.

---

## 7. Preconditions

### 7.1 **The margin Δ\* must be re-fixed, in writing, before pass 1. This is the blocker.**

The pre-registration (`judge_owed_conditions.md` §7.5) fixes the **fraction** at 20% and permits
— indeed requires — recomputing Δ\* against a revised headline effect, **with disclosure**, but
forbids revising the fraction after seeing data. Δ\* = 0.1051 nats was 20% of **+0.5256 nats**.
I re-derived that reference effect: mean `entropy_after − entropy_before` over the 80 FA targets
of `wk9_defb` = **+0.5256** (MEASURED, this session — it reproduces exactly).

**But the null control landed this morning and the headline moved.** `null_control_report.md`
now reports the budget-matched paired net at **+0.183 nats** (NLI), and
`PREREG_noop_convention_2026_08_28.md` §0 puts the locked convention (d) NLI net at **+0.1061
[+0.0549, +0.1638]** at n=65. Which number is "the reported false-alarm effect" decides Δ\*:

| candidate reference effect | Δ\* = 20% | ≈ clusters (at 0.1984 nats/cluster) |
|---|---|---|
| +0.5256 — raw campaign FA move, the original anchor | **0.1051** | 0.53 |
| +0.183 — budget-matched paired net as printed today | **0.0366** | 0.18 |
| +0.1061 — convention (d), judge-relevant, n=65 | **0.0212** | 0.11 |

The third is **5× tighter** than the one §6.2's power note was written against, and that note
already said the per-target SD of δ_bias "has never been observed" and that power at n=80 is
"not yet known, and cannot be asserted". **Under the tightest margin, INCONCLUSIVE is the likely
outcome**, and INCONCLUSIVE is explicitly *not a pass* (§4.3).

This is a ruling, not a flag, and it belongs to whoever owns the pre-registration. My reading —
offered as a reading, not a decision — is that Δ\* should stay anchored to **+0.5256**, because
the conservativeness argument the judge is being validated for is an argument about **the
false-alarm effect the paper reports as the attack's move**, not about the null-controlled net;
δ_bias asks how many nats of that move the judge could have manufactured. But the choice must be
made and written down **before** the run, because the pilot in pass 0 exists to decide whether
n=80 resolves Δ\*, and it cannot do that without knowing Δ\*.

### 7.2 The null control's output is a precondition — but only for §7.1 and §6.3

The run does not consume the null control's data as input to any estimand. It consumes it in
two other ways: the headline effect that sets Δ\* (§7.1), and `baseline.judge` as the benign
acceptance test (§6.3). Both are satisfied — the run completed at 03:57 today with 80 rows
(MEASURED: 80 lines, 80 unique `question_id`s, in `results/null_control_ckpt_defb.jsonl`).

### 7.3 Cache cells, all verified present

- `wk9_defb/triviaqa_se_false_alarm.jsonl`: **80 rows, 80 unique ids, `feasible` true on 80,
  `best_query` non-empty on 80** (MEASURED).
- `wk4_full_2000q/samples.jsonl`: 2000 rows, and **all 80 FA targets present** (MEASURED). This
  is what makes the benign arm cost zero generations.
- All three model repos in `~/.cache/huggingface/hub` (MEASURED). Set
  `HF_HOME=/home/abhi/.cache/huggingface` as every other wrapper in the repo does, or the run
  will try to re-download 33 GB.

### 7.4 Judge config — reproduce it exactly, and resist the temptation to tune

`--judge_model Qwen/Qwen2.5-7B-Instruct`, symmetric (the default — §3), `load_in_4bit=True`,
`max_new_tokens=3`, `do_sample=False`, `--judge_batched`, `--judge_batch_size 6`. That is the
config behind the 0.93 **and** behind the null control's judge arm.

Two temptations to name and refuse:

- **Raising the batch size in pass 2.** `judge_owed_conditions.md` §6.2 speculates the judge
  "may allow batch size back up to 12" once it runs alone. It might. But 12 is the value with a
  **documented HSA allocator failure** (`overnight_2026_08_14.sh:8-10`), the 11.13 s/clustering
  anchor is measured at 6, and changing it makes the (ii)/(iii) run's judge config differ from
  the null control's, which is the one thing §7.4 exists to prevent. The whole job is 45
  minutes. **Stay at 6.**
- **Running `probe_batched_judge.py` first.** It re-validates batched≡unbatched, which the
  completed 4,400-clustering null control has already relied on. It loads Qwen **twice** on a
  16 GB card. I would skip it; if it is run anyway, run it alone, and treat an OOM as an
  environment fact rather than a verdict on the judge.

### 7.5 Nothing here needs a second human

(iii) has no human component. (ii)'s **machine** half has none either — the oracle labels come
free from `samples_correct` via `se.scoring.is_acceptable`. (ii)'s **human** half (a 160-pair
blinded sheet, ~3–4 h) is a separate item, is not closed by this command, and
`judge_owed_conditions.md` §8 already recommends dropping it in favour of the question-equivalence
audit if only one can run. **This command closes the machine half of (ii) and all of (iii).
Whoever writes the paper must not describe it as closing (ii) outright.**

---

## 8. What became free since 2026-08-13, and what did not

`judge_owed_conditions.md` §2.1 argues that the null control's checkpoint "stores *moves* —
signed differences of two entropies. A difference of entropies is not on the entropy lattice and
cannot be inverted to a cluster count." **That is true of the move alone and false of the
checkpoint**, because the checkpoint also stores `baseline`, so the attacked entropy is
recoverable by addition. Running the repo's own validated inverter
(`judge_owed_conditions.build_k_lattice` / `invert_cluster_count`) over the judge arm of
`results/null_control_ckpt_defb.jsonl` (**MEASURED**, this session, CPU, read-only):

| judge-arm entropies | exactly identified | ambiguous by 1 cluster | off-lattice |
|---|---|---|---|
| baseline (benign, n=80) | **78** | 2 | **0** |
| attacked (n=80) | **70** | 10 | **0** |
| benign draws (n=3,704) | **3,509** | 195 | **0** |

**Zero off-lattice out of 3,864** — the inversion is well-posed on this data, and every
ambiguity is ambiguous by exactly one cluster.

**What that closes: δ_K, under the judge, on the budget-matched contrast, for zero GPU.** That
is strictly better than the q-vs-q′ δ_K the GPU run can produce, and it is more than §2.1 says
is possible. **What it does not close: everything that matters.** δ_bias needs H(O) — the
clustering with oracle-positive pairs force-merged — which needs **assignments**, not counts;
δ_φ needs per-pair verdicts; δ_α needs the ab/ba flags. None are on disk. And δ_K is
pre-registered as **descriptive, never a claim statistic** (§4.4.3, §7.9), precisely because a
clusterer with a constant merge fraction produces a non-zero additive DiD mechanically.

**Recommendation:** compute δ_K on CPU **before** the GPU run and read it as a free prior on
what the run will find, on the explicit understanding that it can never be reported as a
verdict. It costs minutes and no device time. It is not part of the command in §3 and would be a
separate, CPU-only, read-only piece of work.

---

## 9. Confidence, and what I could not verify without running it

**High confidence (verified from primary sources this session):**
- No existing script closes (ii) or (iii). Every candidate opened and read end to end.
- The tag is `_defb`; verified four ways including a 80/80-vs-69/80 empirical discriminant.
- `null_control.py` has no flag that emits the required detail; `diag_defb.json` carries the
  checkpoint's fields and nothing more.
- The benign arm needs zero generation: 80/80 FA targets have cached sample text.
- The symmetric judge is the default in `load_judge`, so the validated config and the deployed
  config are the same object.
- `validate_judge.py` unconditionally overwrites `results/judge_validation.md`.
- The judge arm's cluster counts are recoverable from disk with zero off-lattice failures.

**Medium confidence:**
- **0.74–0.78 GPU-h.** DERIVED from two anchors, one of them (11.13 s) itself a subtraction and
  argued to be an upper bound, the other (11.21 s) also a subtraction. I expect an over-estimate
  and would not be surprised by ±30%. Pass 0 collapses this bracket in seven minutes — **run the
  pilot and re-derive from its own wall clock before quoting any figure downstream.**
- **The regeneration reproduces the campaign's attacked samples.** Strongly supported (80/80
  reproduction of `entropy_before` by an independent run days later) but seed reproducibility
  across a driver or library change is not something a file can establish.

**What I could not verify without running it, and did not:**
1. **Whether the judge at batch 6 with Qwen alone actually costs 11.13 s.** No throughput probe
   of the judge exists at any batch size (`operational_number_audit.md` A10, unverified).
2. **Whether pass 2 fits in VRAM comfortably alone.** It should — Qwen alone at 4-bit against a
   16 GB card, no Llama, no DeBERTa — but the 6-vs-12 allocator behaviour has never been probed.
3. **The per-target SD of δ_bias, hence power at n=80.** Never observed. This is precisely what
   pass 0 exists to measure, and why it must not be skipped. If the pilot says n=80 does not
   resolve Δ\*, the pre-registered answer is to report **INCONCLUSIVE**, not to widen the margin.
4. **Whether δ_bias comes out positive.** If it does, §4.3 pre-commits the consequence: the judge
   is withdrawn as the false-alarm adjudicator, and four `.tex` sites re-scope. That cost is
   already written down and should not be renegotiated after the fact.

**Taken on trust, not re-derived:** the 1.75 s/target NLI figure (anchor A5); the 0.1984
nats/cluster slope used for the cluster-equivalents column in §7.1; the claim in
`judge_owed_conditions.md` §5.2 that 74.5% of pool pairs carry a free oracle label (I verified
the *cache* supports the labels, not the percentages); and the assertion that
`probe_batched_judge.py` previously passed — I found no artifact recording a pass, only three
files recommending its use.
