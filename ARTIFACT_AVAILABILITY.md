# Artifact availability

**Status: this repository, on its own, cannot rebuild the paper's headline numbers.**

Written 2026-08-30 against commit `fab9df1`. Every size, hash, count and rate below was
re-derived on this machine for this document; nothing is quoted on trust. Where a number is
reported by another file rather than measured here, it says so.

> **Concurrent edits.** While this was being written, other work landed in the working tree:
> a `LICENSE` was added, `README.md` was rewritten (it now carries a "Limitations of this
> artifact" section covering the same ground at summary level), and `.gitignore` was amended.
> Sections 4, 5.2, 5.3 and 6 were re-checked against the live tree afterwards and say what is
> true as of the re-check. All of those changes are still **uncommitted**, so any of them may
> yet be revised. This document and the new README are meant to complement, not duplicate:
> the README says *that* a clone cannot reproduce the headline; this file says exactly which
> bytes are missing, how many there are, where they are, and what to do about it.

This file exists because the paper did not say any of it. **That gap is now closed:
`paper/main.pdf` (41 pages) carries a Data and Code Availability section, added 2026-08-31
from the draft in section 8 below.** The two are meant to complement each other. The paper's
statement tells a reader that the headline depends on a cache which is not in the repository
and where to obtain it; this file says exactly which bytes are missing, how many there are,
and what a bare clone does and does not reproduce without them.

Recorded for provenance, because it is why this file has the shape it does: before that edit,
searching the extracted PDF text and the LaTeX sources for `availab`, `artifact`, `reproduc`,
`github`, `zenodo` and `supplement` returned only body prose -- "sequence probabilities are
not available", "so each estimate is reproducible", and so on. A reader had no way to learn
that the numbers depend on a 4.75 MB cache absent from the repository, and no way to learn
where that cache was.

---

## 1. The one-paragraph truth

The measurement-validity result has two halves. The **combinatorial** half -- that discrete
semantic entropy at N=10 can take only 39 values, only two of them in the top tenth of its
range, with an atom at the maximum ln 10 -- is pure enumeration over integer partitions, and
is reproducible from this repository with no data at all, in under a second, on any machine.
The **empirical** half -- that the atom's mass over clean correct answers is 10.5%
[9.0, 12.2] on n = 1424 -- is reproducible only from a Week-4 sample cache that lives
outside the repository tree, on the WSL Linux filesystem, and is not published anywhere. The
secondary paraphrase-attack and null-control results depend on that cache *and* on ten
further files that this repository generates but `.gitignore` excludes.

---

## 2. What is reproducible from a clone alone

Verified by running it. No GPU, no model, no network, no cache.

| Claim | How | Verified value |
|---|---|---|
| Attainable SE values at N=10 | enumerate partitions of 10, score each | **39** distinct (from p(10) = 42 partitions) |
| Values in the top tenth of the N=10 range (>= 0.9 ln 10 = 2.0723) | same | **2** -- 2.163956 and 2.302585 |
| The maximum is an atom | same | max = ln 10 = 2.302585, attained by exactly one partition: all ten samples in singleton clusters |
| Attainable values at N=20 / in its top tenth | same | **455** / **7** |
| Attainable values at N=40 / in its top tenth | exact integer criterion, see below | **14114** / **42** |
| Test suite | `.venv/Scripts/python.exe -m pytest -q` | **2 failed, 1221 passed, 17 skipped** in 66 s, with no cache present. Measured 2026-08-26; the suite has since grown to 1408 collected, and the cacheless condition has not been re-measured since. Re-run before quoting. |

The N=40 count is obtained by keying partitions on the integer product `prod(c^c)`, which
is equal for two partitions **iff** their entropies are equal. That is exact arithmetic and
needs no tolerance. The **14116** this table carried until 2026-08-31 came from rounding
scores to 12 decimal places, which is the default of `scripts/fair_pool_granularity.py`;
that route gives 14114 at 9 to 11 places and 14138 at 13, so it has no correct setting.

The two failures are the known-open `tests/test_operational_provenance.py` pair naming
`scripts/overnight_2026_08_14.sh`. That is the documented baseline, not a regression. Note
what the run implies for a reproducer: **the entire test suite is cache-independent**, so a
green test run is not evidence that the data pipeline works. It cannot be.

Also genuinely shipped and readable without the cache:

- `figures/fig_achievable_roc_data.csv` -- 65 rows, the plotted achievable-FPR/TPR grid for
  the fair pool (n = 200 correct and 200 hallucinating). The figure in the paper can be
  checked point by point against this file.
- `figures/fig_floor_budget_data.csv`, `figures/fig_floor_budget_stats.json`,
  `figures/ceiling_figures_stats.json`, `figures/fig1_ceiling_data.csv`,
  `figures/fig2_censoring_data.csv` -- plotted points and re-derivation records for the other
  figures. `fig_floor_budget_data.csv` repeats its population string in every row, which is
  the right pattern and should be copied elsewhere.
- 76 Markdown reports under `results/` and 16 under `docs/`. These *state* the numbers, with
  arithmetic and provenance, but they are transcripts of runs, not inputs to them. A
  reproducer can audit the reasoning; they cannot recompute anything from these files.

---

## 3. What needs the Week-4 cache, and where it is

### 3.1 Location

`src/se/sampling.py:29`

```python
DEFAULT_SAMPLES_DIR = Path(os.path.expanduser("~/.cache/se-research/samples"))
```

This resolves differently on the two interpreters the project uses:

| interpreter | resolves to | exists |
|---|---|---|
| WSL `Ubuntu-24.04` (`.venv-wsl`, the research runtime) | `/home/abhi/.cache/se-research/samples` | **yes** |
| Windows `.venv/Scripts/python.exe` | `C:\Users\Abhi\.cache\se-research\samples` | **no** |

The UNC share `\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\...` did not resolve from the
Windows interpreter when tested for this document, so the fallback path that
`scripts/achievable_fpr_grid.py` lists first is not currently working either. In practice
the cache is reachable from exactly one place: inside WSL.

### 3.2 Contents, measured

Under `/home/abhi/.cache/se-research/samples/` in `Ubuntu-24.04`. Sizes in bytes; hashes are
the first 16 hex digits of sha256.

**`wk4_full_2000q/` -- 4,750,014 B (4.75 MB / 4.53 MiB). Every N=10 headline number is
computed from this directory.**

| file | bytes | sha256[:16] | rows | what it is |
|---|---|---|---|---|
| `samples.jsonl` | 3,853,241 | `48d3caf41c455170` | 2000 | raw generations: `question_id`, `question`, `canonical_answer`, `accepted_forms`, `greedy`, `greedy_correct`, `samples` (10 per question), `samples_correct` |
| `entropy.jsonl` | 540,559 | `80c6f6ce80968e85` | 2000 | clustering output: `n_clusters`, `entropy_nats`, `entropy_bits`, `assignments` (the cluster index of each of the 10 samples), `samples_correct` |
| `relabeled.jsonl` | 355,900 | `5a2f549f11218f6b` | 2000 | span-oracle relabelling: `entropy_nats`, `greedy_correct` (SPAN), `greedy_correct_strict`, `greedy_correct_substr` (the retired SUBSTRING oracle), `single_token_gold` |
| `manifest.json` | 314 | `6b26ccffaa84ef5e` | -- | generation config, quoted in full below |

`entropy_nats` in `relabeled.jsonl` agrees with `entropy.jsonl` on all 2000 rows (0
mismatches, checked to 1e-12), so the two files are consistent and either can carry the
score.

**`attacks/` -- 500,313 B total, 11 files.** Attack and null-control campaign outcomes.

| path | bytes | sha256[:16] | role |
|---|---|---|---|
| `attacks/wk9_defb/triviaqa_se_false_alarm.jsonl` | 157,837 | `b3e8c1c283ea7789` | **the definitive false-alarm cell**, 80 targets |
| `attacks/wk9_defb/triviaqa_se_hide.jsonl` | 161,172 | `f396ad3075ed1ee7` | hide cell, `_defb` |
| `attacks/wk9/triviaqa_{se,sre}_{false_alarm,hide}.jsonl` | 26,103 | four files | superseded pilot cells -- but still the input `scripts/make_figures.py` and `scripts/wk11_analysis.py` read by default |
| `attacks/wk9_def/*.jsonl` | 142,879 | two files | superseded |
| `attacks/wk9_fair/triviaqa_se_false_alarm.jsonl` | 3,549 | -- | superseded |
| `attacks/wk6_hide.jsonl`, `attacks/wk7_false_alarm.jsonl` | 8,773 | two files | superseded; used only as worked examples in the audit protocol |

**`wk3_mon_50q/` -- 113,191 B, 3 files.** A 50-question Week-3 development pool. No paper
number depends on it.

Whole-cache total: **5,363,518 B (5.36 MB)**.

### 3.3 Provenance of `wk4_full_2000q`

`manifest.json`, verbatim:

```json
{
  "phase": "A",
  "model_id": "meta-llama/Llama-3.1-8B-Instruct",
  "load_in_4bit": true,
  "n_samples": 10,
  "temperature": 1.0,
  "max_new_tokens": 48,
  "seed": 0,
  "split": "validation",
  "n_questions_target": 2000,
  "n_questions_completed_this_run": 1907,
  "elapsed_seconds_this_run": 23340.087370081
}
```

Read the last group carefully before publishing it. The manifest describes **one run of 1907
questions in 6.48 hours**, but the directory holds 2000. It is the product of a resumed run,
and the manifest records only the final leg. Anyone shipping this cache should either
regenerate the manifest to describe the whole directory or state the resume in the
accompanying README. The manifest is also the only record of the sampler settings, and it
lacks the `gen` block that the current `_write_manifest` in `src/se/sampling.py` writes
(which would carry `top_p`) -- so it was written by an earlier version of that function and
under-describes its own directory in a second way.

Upstream inputs, neither of which ships: TriviaQA `rc.nocontext` validation split (17,944
examples, per `README.md`), and Llama 3.1 8B Instruct in 4-bit bitsandbytes. File mtimes:
`samples.jsonl` and `entropy.jsonl` are 2026-06-25; `relabeled.jsonl` is 2026-07-01, the
span oracle having been applied after the fact by `scripts/relabel_pool.py`.

**One correction to the record.** `src/se/cache_check.py` opens with "Motivated by the
2026-07-02 loss of `~/.cache/se-research`". There was no loss. `docs/critique_log.md` entry 8
and `results/OVERNIGHT_2026-07-02.md` both retract it as a false alarm caused by querying the
wrong WSL distro. The docstring still asserts the retracted version; see section 9.

### 3.4 What the cache is needed for, and the override problem

Fourteen scripts read `wk4_full_2000q`. Exactly **two** accept an override:

- `scripts/achievable_fpr_grid.py` -- `--labels` or `SE_RELABELED_JSONL`, plus a four-entry
  candidate-path list. This is the good pattern.
- `scripts/likelihood_weight_sensitivity.py` -- partial.

The other twelve -- `cluster_count_bound.py`, `fair_pool_check.py`,
`fair_pool_granularity.py`, `n_scaling_grid.py`, `replay_control.py`,
`replication_conventions.py`, `wk4_auroc.py`, `relabel_pool.py`, `judge_owed_conditions.py`,
`rescore_likelihoods.py`, `wk_seps_transfer.py`, `make_floor_budget_figure.py` -- take
`DEFAULT_SAMPLES_DIR` with no way to point them elsewhere.

**Shipping the cache is therefore not sufficient on its own.** A reproducer who unpacks the
archive anywhere other than `~/.cache/se-research/` will still be unable to run twelve of the
fourteen scripts. See section 6, item 4.

Only `relabeled.jsonl` (355,900 B) is needed for the headline floor. `samples.jsonl` is
needed only to re-run clustering from the raw generations. That asymmetry drives the
recommendation.

### 3.5 The headline number, re-derived here

From `relabeled.jsonl` alone, in WSL, CPU only:

| quantity | recomputed here | paper / report |
|---|---|---|
| rows | 2000 | 2000 |
| greedy-correct, SPAN oracle | **1424** | 1424 |
| greedy-correct, SUBSTRING oracle (retired) | **1440** | 1440 |
| correct answers at the cap, `entropy_nats == ln 10` | **150** | 150 |
| minimum non-zero achievable FPR | **150/1424 = 10.53%**, Wilson 95% **[9.04, 12.24]** | 10.5% [9.0, 12.2] |
| hallucinating answers at the cap | **145/576 = 25.17%**, Wilson 95% **[21.80, 28.87]** | 25.2% [21.8, 28.9] |
| correct answers with `n_clusters == 10` | **150** | -- (confirms the atom is exactly the all-singletons partition, not a coincidence of scores) |
| distinct entropy values realised across all 2000 | **35** | -- (of 39 attainable; four are never observed) |

The headline reproduces exactly. It reproduces *only* from a file that is not published.

---

## 4. Repository-side files the paper depends on that `.gitignore` excludes

These are generated into the repository tree and then excluded. They do not reach a clone.

| path | bytes | excluded by | what depends on it |
|---|---|---|---|
| `results/null_control_ckpt_defb.jsonl` | 236,682 | `results/*.jsonl` | **the 80/80 null control** -- the entire secondary claim |
| `results/diag_defb.json` | 350,708 | `results/*.json` | null-control diagnostics (`--dump_diag`) |
| `data/cache/attacks/wk9_defb_snap/triviaqa_se_false_alarm.jsonl` | 157,837 | `data/cache/` | the 80 campaign outcomes the null control is scored against |
| `data/cache/attacks/wk9_defb_snap/triviaqa_se_hide.jsonl` | 106,007 | `data/cache/` | hide cell, snapshot at 52/80; superseded by the WSL file, do not use |
| `data/cache/attacks/wk9_defb_snap/SNAPSHOT.txt` | 532 | `data/cache/` | the snapshot's own provenance record |
| `results/n_scaling_ckpt.jsonl` | 2,423,028 | `results/*.jsonl` | the N-scaling grid and the floor-budget figure |
| `results/rescore_likelihoods_ckpt.jsonl` | 635,450 | `results/*.jsonl` | likelihood-weight sensitivity |
| `results/rescore_likelihoods_scores.csv` | 148,561 | `results/*.csv` | same |
| `results/winners_curse_ckpt_se_false_alarm_defb.jsonl` | 19,703 | ~~`results/*.jsonl`~~ | winner's-curse re-evaluation, `_defb`. **No longer ignored** -- a concurrent `.gitignore` edit added `!results/winners_curse_ckpt_*.jsonl`. Still untracked, so it needs `git add` to actually ship. |
| `results/replication_auroc.json` | 274 | `results/*.json` | Phase-1 replication AUROC |

**All three inputs named in the null-control report's own provenance table are on this list.**
`results/null_control_report_defb.md` section 1 pins them by size and sha256 -- a model of
good practice -- and not one of the three ships. (I independently confirmed the in-repo
snapshot's hash, `b3e8c1c283ea7789`, matches the live WSL campaign file, so the snapshot is
faithful; it simply is not published.)

The exclusion looks unintended rather than deliberate. The `.gitignore` comment above the
`results/*.jsonl` rule reads "per-target resume checkpoints -- must survive `git clean -fd`",
which is a protection-from-deletion rationale, not a publication policy. Three sibling
checkpoints -- `null_objective_ablation_ckpt_def.jsonl`, `pilot_n20_ckpt_def.jsonl`,
`winners_curse_ckpt_se_false_alarm_def.jsonl` -- *are* tracked, presumably force-added before
the rule landed. The net effect is arbitrary: the **superseded** `_def` checkpoints ship and
the **definitive** `_defb` ones do not.

### 4.1 The counter-argument now in `.gitignore`, and why it does not survive section 6

The concurrent `.gitignore` edit adds a reasoned defence of keeping the other nine ignored:

> The rule above is right for run state [...] and every rebuild that consumes them ALSO needs
> `data/cache/`, which is ignored wholesale [...]. Shipping them would not make those rebuilds
> runnable from a clone; they would still exit non-zero on the missing cache, which is a loud,
> honest failure.

That is correct **as long as `data/cache/` stays ignored and the sample cache stays
unpublished** -- shipping a checkpoint whose consumer cannot start is indeed worse than not
shipping it, because it looks reproducible and is not.

But the premise is the thing section 6 proposes to change. Under bundle A or better, the
checkpoints' inputs *are* published, so the rebuilds do run, and the argument for excluding
them lapses. The two positions are not in conflict; they are answers to different questions.
The `.gitignore` note answers "should we ship checkpoints *given* that the cache is secret?"
(no). This document answers "should the cache be secret?" (also no). If the cache ships, the
checkpoints should follow it; if the decision is that the cache stays unpublished, the
`.gitignore` reasoning is right and these nine files should stay out.

I do not own `.gitignore`. This is a report, not a change.

---

## 5. Hazards in what *does* ship

### 5.1 A tracked file states a superseded clean AUROC of 1.000

`results/figures/headline_auroc.json` (323 B, tracked, dated 2026-06-26) contains:

```json
"triviaqa/se": { "clean": 1.0, "hide_only": 1.0,
                 "false_alarm_only": 0.967, "both": 0.787, "n": 30 }
```

The clean fair-pool AUROC of record is **0.704 [0.653, 0.753]**
(`results/fair_pool_report.md`). `results/OVERNIGHT_2026-07-02.md` records that these pre-B1
artifacts "were the only committed numbers" and that they were to receive SUPERSEDED
banners. `headline_auroc.json` and its sibling `headline_auroc.png` never got one: grepping
`results/` and `docs/` for `headline_auroc` returns only the generator
`scripts/make_figures.py`. A reproducer who clones the repository and opens the file named
`headline_auroc.json` finds a perfect detector and no warning anywhere.

This is the most misleading thing in the published tree, and it is 323 bytes.

### 5.2 The LICENSE -- fixed in flight, but only for the code

At the time this document was started there was no `LICENSE`, only `README.md`'s promise of
"MIT, to be added before public release in Week 17". A concurrent edit has since added one
(MIT, "Copyright (c) 2026 ScriptSampler"). It is **untracked**, so it still needs committing
before it protects anything.

That closes the code half and leaves the data half open. An MIT `LICENSE` at the repository
root does not obviously govern a tarball of TriviaQA questions and Llama-3.1-8B-Instruct
generations published as a release asset. See section 6, item 3.

### 5.3 README staleness -- fixed in flight

At the time this document was started, `README.md` still gave the deadline as 15 September
2026, stopped its Status section at Week 3 (before the Week-4 pass that produced every
headline number), described `results/` as containing "sample sets", and never mentioned the
sample cache. A concurrent rewrite (+333 / -39 lines, uncommitted) has corrected all four and
added a "Limitations of this artifact" section that states plainly that a clone cannot
reproduce the headline numbers from raw data.

Two things that section still leaves for this document to say. It reports the excluded
checkpoints' sizes but not the *cache's*, so a reader cannot tell whether the missing data is
5 MB or 5 GB. And it says "Regenerating them means re-running the GPU pipeline" -- true of the
cache's *origin*, but the operative fact is that regeneration is unnecessary: the cache exists,
it is 4.75 MB, and the only thing standing between a reproducer and the headline is a decision
to upload it.

### 5.4 The unblinding key ships, and the audit it blinds has not been done

See section 7. It needs its own answer.

---

## 6. Recommendation: what to publish alongside the paper

The tracked tree today is **5,310,643 B (5.31 MB)**, of which `paper/main.pdf` is 480 KB and
the four figure PNGs are 639 KB. `.git` is 13 MB. Those are the numbers the decision is
against.

### The three bundles, priced

| bundle | contents | bytes | growth of the tracked tree |
|---|---|---|---|
| **A -- minimal** | `relabeled.jsonl` + `manifest.json` + the ten excluded repo-side files of section 4 | **4,434,996** (4.43 MB) | +84% |
| **B -- full derived** | A + `entropy.jsonl` (adds the cluster assignments) | **4,975,555** (4.98 MB) | +94% |
| **C -- everything** | B + `samples.jsonl` + all of `attacks/` | **9,329,109** (9.33 MB) | +176% |

What each buys:

- **A** rebuilds every N=10 headline number: the 1424 denominator, the 150 at-cap count, the
  10.5% [9.0, 12.2] floor, the 25.2% ceiling TPR, the full achievable-FPR grid on both the
  n=200 fair pool and the n=1424 superset, *and* the 80/80 null control. It does not let
  anyone check the clustering.
- **B** additionally lets a reader verify that each score really is the entropy of the
  reported cluster partition, because the per-sample assignments are in `entropy.jsonl`.
  Given that the paper's central claim is *about the partition structure*, B is the first
  bundle at which a sceptic can check the claim rather than take the scores on faith. **This
  is the floor I would not go below.**
- **C** additionally lets someone re-run NLI clustering from the raw generations and re-derive
  the attack results. It is the only bundle that makes the attack case study reproducible at
  all. At 9.33 MB it is still trivially small by any standard -- smaller than one of the
  figure PNGs in most papers' supplements.

### Repository, release asset, or data host

**In the repository (`data/cache/`, un-ignored).** Best for the reproducer: one `git clone`
and everything works, no second step, no dead link, and the data is versioned alongside the
code that reads it. Costs: the tree roughly doubles at bundle B; every future clone carries it
forever; and, decisively, **git history is append-only** -- a mistake in the data is
permanent, and a later decision to unpublish requires rewriting history. Choose this if you
are confident the data is final and clearly licensable.

**As a GitHub release asset on the arXiv-submission tag.** The balanced option. The clone
stays small, the tarball gets its own checksum and download count, the paper cites a stable
URL like `.../releases/tag/arxiv-v1`, and a release asset **can be replaced or removed**,
which a committed file cannot. Costs: a second step for the reproducer, a risk of drifting
out of sync with the code, and a dependency on GitHub continuing to host it. Choose this if
you want to retain the ability to correct or withdraw the data.

**On a data host (Zenodo / OSF / Figshare).** Only this option yields a DOI, and only this one
carries a preservation commitment that outlives the GitHub account. Zenodo's GitHub
integration mints a DOI per release automatically, so in practice it is a layer on top of the
release asset rather than an alternative to it. Costs: another account, a metadata form, and
a version-of-record now living in two places. Choose this if the archival guarantee matters --
for a preprint that may be cited for years, it plausibly does.

**A default to argue with, not a decision.** Ship **bundle C** (9.33 MB -- at this size the
marginal cost of completeness is nil) as a **GitHub release asset mirrored to Zenodo for the
DOI**, and additionally commit **bundle A's ten repo-side files (4.08 MB)** into the
repository, since those are outputs of this project's own scripts, are already written into
the tree, and are excluded by a rule whose stated purpose was protecting them from
`git clean` rather than withholding them.

### Four things to do regardless of which option is chosen

1. **Put an availability statement in the paper.** Section 8 drafts one. Without it, none of
   the above is discoverable by a reader.
2. **Fix `results/figures/headline_auroc.json`** -- banner it, move it under a `superseded/`
   directory, or delete it. Publishing a file that says the detector is perfect, beside a
   paper that says 0.704, will cost more credibility than the whole cache is worth.
3. **Commit the LICENSE** (added concurrently, still untracked), **and decide separately how
   the *data* is licensed** -- an MIT file at the repository root does not self-evidently cover
   a release tarball of model generations. The code can be MIT.
   The cache contains TriviaQA questions (Apache-2.0 upstream) and Llama 3.1 8B Instruct
   generations, whose redistribution falls under the Llama 3.1 Community License, which
   carries attribution requirements for derived material. This is not a legal opinion; it is a
   flag that "MIT, to be added" does not cover a tarball of model outputs, and someone should
   read the licence before it goes up.
4. **Make the twelve hard-coded scripts overridable**, or the bundle is unusable in practice
   wherever it is downloaded to. The cheapest fix is a single env-var read in
   `src/se/sampling.py` -- `SE_SAMPLES_DIR`, falling back to the existing `expanduser`
   default -- which fixes all fourteen call sites at once and costs about three lines.
   `scripts/achievable_fpr_grid.py` already demonstrates the pattern. (I own neither `src/`
   nor `scripts/`; this is a recommendation.)

---

## 7. `results/equivalence_audit_key.csv`: sequester it now, publish it with the labels

### 7.1 Measured at commit `59b5003`, 2026-08-31, CPU only

| claim | measured |
|---|---|
| tracked | Yes. `git ls-files` lists it. Blob 63,063 B in commit `6d65384` (2026-08-13); working tree 63,224 B (the 161 B gap is CRLF in the checkout against LF in the object). |
| rows | **160 data rows in 171 physical lines.** Ten rows carry a newline inside a quoted field. It is not 171 rows; a line count overstates it by eleven. |
| distinct pairs | **123.** Round 1 is 123 pairs; round 2 is 37 re-presentations of round-1 pairs. 123 + 37 = 160. |
| columns | 20: `pair_id, round, stratum, orientation, round1_pair_id, question_id, source_file, attack, detector, question, best_query, success, entropy_and_feasible, status_held, correct_under_q_prime, frac_correct_under_q_prime, answer_under_q_prime, entropy_before, entropy_after, delta` |
| strata, round 1 | win 72, subthreshold 30, flip 13, catch 8. Reproduces the design manifest exactly. |
| strata, round 2 | win 22, subthreshold 9, flip 4, catch 2 |
| pool hashes | Both snapshot inputs re-hash to the sha256 recorded in `equivalence_audit_design.md`. The sheets are regenerable from the frozen snapshot. |
| blinded sheet | 7 columns: `pair_id, question_A, question_B` plus four empty annotation fields. **No outcome column, no stratum, no orientation.** Genuinely blind to outcome. |
| orientation randomised | Yes. 76 `q_first`, 84 `qprime_first`, and all 160 rows agree with the sheet. |
| annotated | **0 of 123 and 0 of 37**, in this tree and in all seven `.claude/worktrees` copies. `equivalence_audit_protocol.md` section 9 carries one log entry, the 2026-08-13 pre-registration, and no session rows. |

The tracking is deliberate. `.gitignore` carried an explicit negation with a rationale:

```
# the equivalence-audit sheet, key and labels are EVIDENCE, not derived output.
# results/*.csv above would have silently excluded them, which breaks the
# transparency-in-place-of-inter-annotator-kappa argument the protocol rests on.
!results/equivalence_audit*.csv
```

The argument is correct. It is being applied at the wrong time. Protocol section 7d asks for
"the protocol, the blinded sheet, the key, **and the filled labels**" in one release, and
there are no filled labels.

### 7.2 The key is not adjacent to the sheet, it is the sheet's answer

Three columns do specific, measurable damage, and each disables a named defence in the
protocol rather than merely leaking outcome.

1. **`stratum` names the catch trials.** Ten rows carry `stratum = catch`, and they are
   additionally the only ten rows with `attack`, `detector` and `success` blank, so the
   filter is trivial. Protocol section 7b calls the catch trials "the only part of the design
   that can detect a rubber-stamping annotator, which is precisely the failure test-retest
   cannot see." Section 5's first scoring rule makes them a validity gate: any catch trial
   not marked `no` voids its session. A key that names them removes the design's only
   defence against the one failure mode its other defences are blind to.

2. **`round1_pair_id` undoes the test-retest.** Protocol section 7a defends the retest with
   "new pair ids, an independent shuffle, and the A/B orientation flipped, so a pair cannot
   be recognised by its id, its position, or which column the original sat in", backed by a
   seven-day washout. Measured: all 37 round-2 rows carry a populated `round1_pair_id`, and
   all 37 have the orientation flipped relative to their twin. That column is a complete
   inverse of the three defences plus the washout, available in one join. Test-retest
   reliability is the protocol's **headline agreement number** in the absence of a kappa.

3. **`success`, `status_held` and `entropy_and_feasible` give the outcome outright.** The
   cross-tab is exact and deterministic: `win` is `success=True`; `flip` is
   `entropy_and_feasible=True, status_held=False`; `subthreshold` is
   `entropy_and_feasible=False`. Nothing needs to be inferred, and every headline quantity in
   protocol section 5 (`p_win`, `p_flip`, `p_subthreshold`, the invisible-to-automation cell)
   is a group-by away.

The sheets themselves are clean. Nothing here is a criticism of `equivalence_audit.csv` or
`equivalence_audit_round2.csv`, which should ship exactly as they are.

### 7.3 One blinding leak the key is not responsible for

The protocol's recommended paper wording claims the audit was run "blind to stratum and to
attack direction". Blind to stratum: measured true, the sheet carries no stratum. Blind to
attack direction: only weakly. Attacked queries run longer than the originals, so the naive
rule "the longer of the two is the paraphrase" identifies q' in **81 of 112** non-catch
round-1 pairs whose two sides differ in length, or **72.3%**, Wilson 95% [63.4%, 79.8%],
against a 50% chance baseline.

That is not fatal. Knowing which side is the paraphrase does not tell the annotator whether
the pair is equivalent, and the substitution test in protocol section 2 asks a question about
answer sets that does not depend on direction. But the claim as worded is stronger than the
instrument supports. Either soften it to "blind to stratum and to outcome", which is exactly
true, or report the 72.3% as a disclosed residual. This is a defect in
`results/equivalence_audit_protocol.md`, which this document does not own.

### 7.4 There are eight copies of the key inside the repository, not one

The protocol's first instruction, in the file table before section 1, is: "**Move it out of
the working directory now**, before section 1." Measured 2026-08-31, the working directory
holds eight copies:

| location | copies | bytes each |
|---|---|---|
| `results/equivalence_audit_key.csv` | 1 | 63,224 |
| `.claude/worktrees/*/results/equivalence_audit_key.csv` | 7 | 63,234 |

The seven worktrees total 31 MB and were held out of version control only by
`.git/info/exclude`, which is local to one clone and travels with nothing: not a push, not a
clone, not a release tarball. `git rm --cached` on the tracked copy touches none of the other
seven. The `.gitignore` edit accompanying this document moves those patterns into the
versioned file so the exclusion survives a clone. It does not delete the copies; that is a
manual step.

### 7.5 The pool the key describes is already stale, and a top-up is owed

Protocol section 8 item 2 recorded that "the hide cell was incomplete at snapshot time, 52 of
80 targets". That run has since finished. Measured on the live campaign file, read only, no
GPU:

| file | records | successes |
|---|---|---|
| snapshot `triviaqa_se_false_alarm.jsonl` | 80 | 44 |
| snapshot `triviaqa_se_hide.jsonl` | 52 | 28 |
| live `triviaqa_se_hide.jsonl` (2026-08-13 07:21) | 80 | 44 |

The 28 hide records added since the snapshot contain **16 further wins**. The finished
campaign therefore holds 88 wins, of which the audit's win stratum censuses 72. Protocol
section 6 rests real weight on that census: "the win stratum is censused (all of them), so
for the claim *of the wins in this paper, k were not meaning-preserving* there is **no
sampling error at all**." That is true of the 2026-08-13 snapshot and no longer true of the
campaign. As drawn, the audit covers 72 of 88 wins, 81.8%. Restoring the census claim needs
either the top-up batch of protocol section 8 item 2
(`--exclude_audited results/equivalence_audit_key.csv`, which is disjoint and does not
re-draw round 1) or a restatement of the population as the snapshot rather than the campaign.

This matters for the decision below, because it means the sheets have to be **touched again
before annotation starts anyway**. That regeneration is the natural and cheapest moment to
fix the key's location.

### 7.6 The options, and what each one costs

The key cannot be deleted: scoring the audit is a join on `pair_id`, and every quantity in
protocol section 5 comes out of its columns. The question is only where it lives, and when it
becomes public.

| option | what it does | what it costs |
|---|---|---|
| **A. Leave it, disclose it** | Ship the key with the paper. Add a Limitations sentence saying the key was in the working tree and in version control throughout. | Cheapest, and honest. But it converts the audit from blind to unverifiable, permanently. A reader cannot distinguish an audit done blind from one done with the answers open, and protocol section 7d's substitution of transparency for a kappa is precisely what collapses, because that substitution needs the reader to believe the labels were produced under the stated rule. |
| **B. Move it out of adjacency, keep tracking** | `git mv` it to, say, `results/private/`. | Cosmetic. Still in the working tree, still tracked, still published, still one `ls` away. It buys nothing, and it looks like it was meant to. Not viable alone. |
| **C. Untrack it now** | `git rm --cached`, move the file outside the repository, delete the seven worktree copies. | Correct, and incomplete on its own. The blob is in commit `6d65384` and reachable from every later commit, so publishing this history publishes the key whatever the tip says. |
| **D. C, plus publish a snapshot rather than the history** | Release the working tree at submission (arXiv ancillary files, a Zenodo tarball, or a fresh-history repository) instead of pushing the existing eleven-week history. | Makes C actually effective. Costs the public commit history, which for a solo preprint is a small loss and arguably a gain in legibility. Decide before the first public push; it is irreversible afterwards. |
| **E. Do the audit before submission** | 123 pairs at 60 to 90 s each is about 4 sessions and 3 to 4 hours, plus a 7-day washout, plus 37 retest pairs. | Dissolves the problem instead of managing it. With filled labels, protocol section 7d becomes correct as written and the key ships as evidence rather than as a hazard. 31 days remain to 2026-10-01 and the washout fits inside them. The top-up in 7.5 is owed regardless, so the sheets are being regenerated either way. |

### 7.7 Recommendation

**Take E, with D as the fallback, and disclose either way.**

1. **Regenerate the sheets with the top-up batch first** (7.5). The hide cell is complete, 16
   wins were never eligible for the draw, and the census claim depends on them. Use
   `--exclude_audited results/equivalence_audit_key.csv` so the second batch is disjoint and
   round 1 is not re-drawn.
2. **Move every copy of the key out of the repository before the first pair is read**: the
   tracked one and the seven in `.claude/worktrees`. Then `git rm --cached
   results/equivalence_audit_key.csv`. `.gitignore` has been amended so the file is ignored
   once untracked, which also protects it from `git clean -fd` if it is left on disk. The
   amendment is inert until the untrack is run, and its comment says so.
3. **Run the audit.** Log every session in protocol section 9 with timestamps and pair
   ranges, as protocol section 4 requires. That log is the only artefact that will let a
   reader date the annotation against the key's removal.
4. **Publish the key together with the filled labels** in one release, as protocol section 7d
   asks. At that point restore the plain negation in `.gitignore` and delete the re-ignore
   line; the comment there says so.
5. **If the audit does not happen before submission**, take D: do not push this history
   publicly. Publish a snapshot with the key withheld, and use disclosure (b) below.
6. **Disclose on every path.** Under E the disclosure is short and favourable. Under A or D
   it is the load-bearing sentence. Silence is the one option not available: the key's
   presence is recoverable from the repository by anyone who looks, and a reviewer who finds
   it unaided will read it as concealment rather than as the ordinary consequence of a
   one-person workflow.

What this does not fix, and what no option fixes: the annotator is the paper's author, the
blind is self-imposed, and the key has been in the working tree since 2026-08-13. Protocol
section 8 items 3 and 4 already say so. The recommendation reduces the exposure from
unbounded and public to bounded, dated and disclosed. It does not manufacture an
independence that never existed.

### 7.8 Disclosure text for the paper, ready to paste

Not applied. `paper/` is out of scope for this document. Both variants are pure ASCII, with
no em dashes and no `--`, to match the source tree. Insert after the Limitations paragraph
beginning "Equivalence is certified automatically, not by humans"
(`paper/sections/limitations.tex`), and pick one.

**(a) If the audit is completed before submission (recommended).** An addition, once labels
exist; it replaces nothing.

> The audit instrument was pre-registered before any pair was read: the decision rule, the
> sampling design, the blinded sheets and the un-blinding key were generated together and are
> released with this paper. Because a single annotator, who is also the author, produced the
> labels, the key was moved outside the repository before annotation began and restored only
> for scoring; session timestamps and pair ranges are logged in the protocol. We report
> intra-annotator test-retest reliability on a re-presented subsample in place of an
> inter-annotator agreement statistic, and we note that test-retest bounds self-consistency
> rather than correctness. A reader who wishes to re-judge any pair can do so from the
> released sheet and key.

**(b) If the key remains adjacent, or the audit is still outstanding at submission.** This is
the disclosure the paper needs if anything is left as it stands.

> The equivalence audit reported as owed above has been designed and pre-registered but not
> yet performed: both blinded sheets are released unannotated. Two limitations of that design
> should be stated plainly. First, the blind is self-imposed. A single annotator, who is also
> the author, owns the repository, the blinded sheet and the un-blinding key, and the key was
> version-controlled in the same directory as the sheet from the moment the instrument was
> generated. The protocol instructs the annotator to move it out of the working directory
> before reading any pair, but nothing in the design can enforce or evidence that, so a reader
> should treat the audit's blinding as a stated intention rather than as a verified property.
> Second, the key carries the stratum label, the per-pair outcome, and the mapping from each
> re-presented pair back to its original, so an annotator with the key in view would have
> access to the catch trials and to the test-retest linkage that the design relies on to
> substitute for an inter-annotator agreement statistic. We disclose this because the audit's
> evidential value rests on transparency in place of that statistic, and transparency about
> the instrument's own weaknesses is part of what is being substituted.

If (b) is used and the key is withheld from the release rather than published, append one
sentence:

> The un-blinding key is withheld from the artifact release until the audit is performed, and
> will be published together with the completed labels.

**(c) A rider for the Data and Code Availability section.** The section added to
`paper/main.tex` on 2026-08-31 is careful about what a clone can and cannot rebuild, and says
nothing about the audit artefacts. Whichever of (a) or (b) is used in Limitations, one
sentence belongs here too, because this is where a reader looks to find out what actually
ships:

> The pre-registered equivalence-audit protocol, its sampling design, and both blinded
> annotation sheets are in the repository; the un-blinding key that scores them is
> [released alongside the completed labels / withheld until the audit reported as owed in
> Section~
ef{sec:limitations} is complete].

---

## 8. A draft availability statement for the paper

Not applied. `paper/` is out of scope for this document and is under separate adjudication.
Offered so that the edit is a paste rather than a writing task. Fill the bracketed fields once
section 6 is decided.

> **Code and data availability.** Code, analysis scripts, per-report derivations, and the
> plotted data behind every figure are at
> `https://github.com/ScriptSampler/red-team-semantic-entropy`. The N=10 combinatorial results
> -- 39 attainable values, two of them in the top tenth of the range, an atom at ln 10 --
> are pure enumeration and reproduce from that repository with no data. The empirical results
> require the Week-4 sample cache: 2000 TriviaQA `rc.nocontext` validation questions, ten
> Llama-3.1-8B-Instruct samples each at temperature 1.0 and 4-bit quantisation, with cluster
> assignments and span-oracle labels, released as [ARCHIVE URL] ([X.X] MB). The 10.5% floor
> is computed from `relabeled.jsonl` alone. Attack and null-control campaign outcomes are in
> the same archive. The blinded equivalence-audit sheets and the audit protocol are in the
> repository; the unblinding key is withheld until the human audit reported as owed in
> Section [N] is complete, and will be released together with the filled labels.

---

## 9. Defects found in files this document does not own

Reported, not changed.

| where | what |
|---|---|
| `paper/` (all) | Was: no data-, code- or artifact-availability statement anywhere. **Closed in flight**: a `Data and Code Availability` section was added to `paper/main.tex` on 2026-08-31. It says nothing about the equivalence-audit artefacts; see section 7.8 (c). |
| `results/figures/headline_auroc.json`, `.png` | Superseded pre-B1 numbers (clean SE AUROC 1.000, n=30) tracked with no SUPERSEDED banner, contradicting the 0.704 of record. |
| repo root | No `LICENSE` when this was written. **Closed in flight**: `LICENSE` is now tracked (1,070 B, MIT). It still covers the code, not the data bundle; section 6 item 3 stands. |
| `README.md` | Was eleven weeks stale (deadline, Status, "sample sets"); rewritten and **now committed**. Its Limitations section still omits the cache's size, which is the number that makes the problem look solvable. |
| `src/se/cache_check.py` docstring | Asserts a "2026-07-02 loss of `~/.cache/se-research`" that `docs/critique_log.md` entry 8 retracts as a false alarm. |
| `src/se/sampling.py` | `DEFAULT_SAMPLES_DIR` has no env-var override, leaving twelve of fourteen consumer scripts unable to read a relocated cache. |
| `.gitignore` | Excludes all three inputs named in `results/null_control_report_defb.md`'s own provenance table, while three superseded `_def` siblings remain tracked. |
| `wk4_full_2000q/manifest.json` (cache) | Describes a 1907-question run for a 2000-row directory (the resume is unrecorded), and omits the `gen` block that the current `_write_manifest` would write. |
| `paper/sections/limitations.tex:175` | Says the answer-flip subcategory "collects the successful attacks in which the model's correctness flips under $q'$". `paper/sections/methods.tex:327` says the opposite and matches the data: they are "would-be successes **voided** by condition (iii) because the model's answer flipped". Measured in the audit key, `flip` is exactly `success=False, status_held=False, entropy_and_feasible=True`, disjoint from `win`. One of the two sentences is wrong. |
| `results/equivalence_audit_protocol.md` (section 7, recommended wording) | Claims the audit is "blind to stratum and to attack direction". Blind to stratum: true. Blind to direction: the longer-of-the-two rule picks $q'$ in 81 of 112 pairs, 72.3% [63.4%, 79.8%]. See section 7.3. |
| `results/equivalence_audit_protocol.md` section 6, `results/equivalence_audit_design.md` | The "census of all 72 wins, no sampling error at all" claim was true of the 2026-08-13 snapshot. The hide cell has since finished at 80 records and 44 wins, so the campaign holds 88 wins and the drawn census covers 72 of them, 81.8%. See section 7.5. |
| `.gitattributes` | Does not normalise `*.csv`, so the audit sheets' bytes depend on the cloner's `core.autocrlf`. Protocol section 8 item 5 requires the stimulus to stay byte-identical; the eight in-tree copies of the key already differ by 10 B for exactly this reason. |
| `.git/info/exclude` | Held 31 MB of `.claude/worktrees` out of the repository using a file that is local to one clone. Moved into `.gitignore` by this document. |

---

*Sections 1 to 6 and 8 were measured on 2026-08-30 at commit `fab9df1`. Section 7 and the
section 9 rows marked "in flight" were re-measured on 2026-08-31 at commit `59b5003`. All on
CPU, in `Ubuntu-24.04` and the Windows `.venv`. No GPU work was run. Nothing was committed or
pushed. The only files changed are `ARTIFACT_AVAILABILITY.md` and `.gitignore`; the
`git rm --cached` that section 7.7 item 2 calls for is proposed, not executed.*
