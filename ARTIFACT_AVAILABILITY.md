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

This file exists because the paper does not say any of it. There is no data-availability,
code-availability or artifact statement in `paper/main.pdf` (34 pages). Searching the
extracted PDF text and the LaTeX sources for `availab`, `artifact`, `reproduc`, `github`,
`zenodo` and `supplement` returns only body prose -- "sequence probabilities are not
available", "so each estimate is reproducible", and so on. A reader has no way to learn that
the numbers depend on a 4.75 MB cache that is not in the repository, and no way to learn
where that cache is. **Adding an availability statement to the paper is a separate, owed
edit; this file does not substitute for it.** A draft is in section 8.

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
| Attainable values at N=40 / in its top tenth | same | **14116** / **42** |
| Test suite | `.venv/Scripts/python.exe -m pytest -q` | **2 failed, 1221 passed, 17 skipped** in 66 s, with no cache present |

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

## 7. `results/equivalence_audit_key.csv` -- do not publish it yet

**Measured.** The key is 63,224 B, **tracked**, and holds 160 rows: 123 from round 1 and 37
from round 2, across strata `win` (94), `subthreshold` (39), `flip` (17) and `catch` (10).
Its columns include `question_id`, `source_file`, `attack`, `detector`, `success`,
`status_held`, `entropy_before`, `entropy_after` and `delta` -- that is, the complete outcome
of every pair, alongside the questions themselves.

It is tracked deliberately. `.gitignore` carries an explicit negation with a rationale:

```
# the equivalence-audit sheet, key and labels are EVIDENCE, not derived output.
# results/*.csv above would have silently excluded them, which breaks the
# transparency-in-place-of-inter-annotator-kappa argument the protocol rests on.
!results/equivalence_audit*.csv
```

That argument is correct *at the end of the audit*. It is being applied at the wrong time.

**The problem.** `results/equivalence_audit_protocol.md` says two things that are currently
both violated:

- Its file table, before section 1: "`results/equivalence_audit_key.csv` | un-blinding key.
  **Move it out of the working directory now**, before section 1." It is instead in the
  working directory *and* in version control, three lines below the blinded sheet in `ls`.
- Section 7d: "Publish the protocol, the blinded sheet, the key, and the filled labels
  together, so a reader can re-judge any pair themselves." **There are no filled labels.**
  Both sheets are empty -- 0 of 123 round-1 rows and 0 of 37 round-2 rows have anything in
  `equivalent_yes_no_unsure`. The paper agrees the audit is outstanding:
  `paper/sections/conclusion.tex:75` and `paper/sections/limitations.tex:96,139,160,167` all
  say a human equivalence audit is owed.

The protocol also records, in its own limitations, that "blinding is self-imposed. One person
owns the repository, the key, and the sheet. The file layout makes the honest path the easy
one; it cannot enforce it," and that "the annotator is the paper's author and is not
disinterested."

Put those together: the only annotator has not yet annotated; the blind is self-imposed and
depends entirely on that annotator not opening one file; and that file is committed to a
repository about to be made public. Publishing it now does not merely risk the blind -- it
makes the blind **unrecoverable**, because a public git object cannot be unseen, and no
reader will afterwards be able to distinguish an audit done blind from one done after the key
was public. The protocol's transparency-instead-of-kappa substitution is precisely what
collapses if that distinction is lost.

**Recommendation.**

1. **Do not include `equivalence_audit_key.csv` in the public artifact release.** Not the
   repository, not the release asset, not the data host.
2. **Move it out of the working tree now**, as the protocol's own first instruction says, and
   `git rm --cached` it. Note that it has already been committed, so it is in the history of
   the private repository -- if that history is what gets published, the key is public
   whatever the current tree says. If preserving the blind matters, publish from a fresh or
   squashed history.
3. **Keep the blinded sheets and the protocol tracked**: `equivalence_audit.csv`,
   `equivalence_audit_round2.csv`, `equivalence_audit_protocol.md`,
   `equivalence_audit_design.md`. Publishing the instrument and the empty sheets *before* the
   audit is exactly right -- it pre-registers the decision rule, and none of those four files
   un-blinds anything.
4. **Publish the key together with the filled labels, in the same release, once the audit is
   done.** That is what section 7d actually asks for, and it is the only form in which the
   substitution of transparency for agreement statistics does any work.
5. Until then, the paper should say the audit is owed **and** that the key is deliberately
   withheld until it is discharged. Silence on the second half invites the reading that it was
   withheld because the result was unwelcome.

This is the one item in this document where the honest answer is: ship less, not more.

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
| `paper/` (all) | **No data-, code- or artifact-availability statement anywhere in 34 pages.** The primary defect this document responds to. |
| `results/figures/headline_auroc.json`, `.png` | Superseded pre-B1 numbers (clean SE AUROC 1.000, n=30) tracked with no SUPERSEDED banner, contradicting the 0.704 of record. |
| repo root | No `LICENSE` when this was written; one has since been added concurrently but is **untracked**, and it covers the code, not the data bundle. |
| `README.md` | Was eleven weeks stale (deadline, Status, "sample sets"); **rewritten concurrently**, uncommitted. Its new Limitations section omits the cache's size, which is the number that makes the problem look solvable. |
| `src/se/cache_check.py` docstring | Asserts a "2026-07-02 loss of `~/.cache/se-research`" that `docs/critique_log.md` entry 8 retracts as a false alarm. |
| `src/se/sampling.py` | `DEFAULT_SAMPLES_DIR` has no env-var override, leaving twelve of fourteen consumer scripts unable to read a relocated cache. |
| `.gitignore` | Excludes all three inputs named in `results/null_control_report_defb.md`'s own provenance table, while three superseded `_def` siblings remain tracked. |
| `wk4_full_2000q/manifest.json` (cache) | Describes a 1907-question run for a 2000-row directory (the resume is unrecorded), and omits the `gen` block that the current `_write_manifest` would write. |

---

*Every measurement in this document was taken on 2026-08-30 at commit `fab9df1`, on CPU, in
`Ubuntu-24.04` and the Windows `.venv`. No GPU work was run. Nothing was committed or pushed.*
