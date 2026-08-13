# START HERE — current state, 2026-08-13 (after the overnight)

Supersedes every earlier version. If you are reading a copy dated 2026-08-12 or earlier, it
still lists **non-relaxability** as a finding that holds and quotes **"22 distinct values"**.
Both were killed overnight. Discard it.

**33 days to the 2026-09-15 arXiv target.** 263 tests pass, 27 citations resolve.

The overnight record is `docs/critique_log.md` entry **33**. Read it before touching a
number: three claims died in one night, and two of the refutations had been sitting in this
repo for days.

---

## What this paper is now

Not "we broke semantic entropy." It is a **measurement-validity paper about semantic
entropy**, with a paraphrase attack as the case study that exercises the protocol. That
reframe is deliberate and load-bearing: it means a null attack result does not kill the
paper, because the measurement findings stand either way.

**Novelty is narrow, and it got narrower overnight.** The false-alarm/inflation direction is
an established family (`rusert2025redherring` EMNLP 2025; `obadinma2024calibration` TMLR;
`khanmohammadi2026answerpreserving`, six days old when we found it). Constrained paraphrase
search is a standard primitive (`kaneko2026paa`, `liang2025seca`, `wang2026depo`).
Discreteness is `sun2026granularity`, in print. **Non-relaxability was the one part we still
called ours, and it is false** — see below. What remains is contribution (5): what a
sampling-based victim forces on the *evaluation*, plus the instantiation measurement.

---

## Findings that hold

1. **Ceiling saturation.** SE is capped at ln(10) = 2.3026 at N=10.
   **From the definitive `_defb` FA cell (n=80, complete):**
   - baseline already at ceiling: **8/80 = 10%**
   - at ceiling after attack: **42/80 = 52.5%**
   - attack-induced: **34/80 = 42.5%**
   - baseline in top tenth of range: **21/80 = 26.2%**
   - corr(headroom, move) **+0.71** (+0.68 on the uncensored n=38)

   The superseded `_def` figures were 39/80, 31/80 = 38.75%, +0.70/+0.67 (n=41). **The
   clean-baseline statistics are bit-identical across both runs** (hashed) — the
   ceiling finding does not depend on the attack instrumentation, which is the robustness
   check that matters. → `results/ceiling_saturation_finding.md` (bannered with both columns)

   **Do NOT quote a distinct-value count here.** See the retirement below.

2. **The lattice — the granularity claim, in its surviving form.** At N=10 semantic entropy
   takes **39 attainable values** (enumerate the p(10) = 42 partitions; 3 entropy
   coincidences), of which **only 2 lie in the top tenth of the range** (2.1640 and 2.3026).
   True by enumeration, independent of n, independent of population. So "a quarter of correct
   answers sit in the top tenth" means those targets occupy one of two points.
   → `results/fair_pool_granularity.md`

   **Consequence, and it is the sharpest sentence in the paper: 26% of the FA pool is
   unwinnable by construction.** The gap between the top two lattice points is **0.1386 nats**
   and the success criterion requires delta = 0.25, so every target at 2.163956 has less
   headroom than delta and **cannot register a success under any paraphrase**. The unwinnable
   set is not the 8/80 at the exact ceiling that Methods used to disclose — it is the whole top
   decile, **21/80 = 26.2% [17.9, 36.8]**, and at delta = 0.25 the two sets coincide exactly
   (the next lattice point down leaves 0.277 nats). No delta >= 0.139 recovers the 21; no
   delta > 0 recovers the 8. **Read every FA success rate against a denominator a quarter of
   which could never have succeeded.**

3. **Crowding, measured on the VALID population** (the score-independent fair pool, CPU-only
   recompute, Wilson intervals):
   - correct stratum (n=200): **9.5% [6.2, 14.4]** at the ceiling, **21.5% [16.4, 27.7]** in
     the top tenth
   - hallucinating stratum (n=200): **27.5% [21.8, 34.1]** and **44.5% [37.8, 51.4]**
   - pooled (n=400): 18.5% and 33.0% — but **any pooled figure is a function of the class
     balance you assume** (the fair pool is 50/50; the real rate is 71% correct; at natural
     prevalence on n=2000 it is 14.8% / 27.8%). **Prefer the per-stratum rows.**

4. **NEW — the censoring is asymmetric, and it cuts in the detector's favour.** The
   hallucinating stratum is censored 2.9x harder at the cap and 2.1x harder in the top tenth,
   non-overlapping intervals at n=200 per stratum. The ln(10) cap compresses the class the
   detector exists to flag, which **biases the clean AUROC (0.704) DOWNWARD**. In the Abstract.

5. **Winner's curse — complete at n=60.** +0.698 → +0.315 nats on re-scoring. Shrinkage
   **−0.383 [−0.529, −0.234]**, CI excludes zero. Retention **45.2% [25.0%, 64.9%]**, now
   computed by `retention_ci()` from a paired percentile bootstrap (it had no producing code
   until 2026-08-13; the hand-written interval was right). Keep the two statements apart:
   *that* there is inflation is established; *how much* is not. 36/60 keep a positive move,
   r = +0.46. **These are `_def` numbers and WILL move under `_defb`** — see Owed #2.
   → `results/winners_curse_partial.md`

6. **Judge.** Deployed symmetric config: hard-neg **0.930 [0.900, 0.957] n=300**, positives
   0.650 [0.593, 0.703], e5 near-chance at 0.51. `results/judge_validation.md` says
   explicitly: *"this number is the DEPLOYED config (symmetric) — cite THIS one."*
   **0.884 / 0.700 are the SUPERSEDED ASYMMETRIC run.** A critic gate flagged 0.93 as drift
   on 2026-08-12; that ruling was wrong and was overruled, and the overrule was sustained.
   Do not "fix" it back.

7. **Replication — quote 0.694, not 0.787.** The paper had validated the pipeline on the
   *all-samples-correct* label (AUROC 0.787 vs the published 0.828), which is **coupled to the
   score**: all-samples calls a question correct iff all ten samples are correct, and SE is the
   entropy of the clustering of those same ten. The operative convention everywhere else in the
   paper is greedy alias-aware span, which gives **0.694** on the same cached run; the gap to
   the published number is 0.134 and the old NLI-backend attribution is dropped as unevidenced.
   The fair pool's 0.704 [0.653, 0.753] **contains 0.694 and excludes 0.787**.

8. **Statistics, as of the 2026-08-13 audit.** No Type-I violation in the shipped exceedance
   test (measured level 0.020–0.043 at nominal 0.05). The median-N misspecification in
   `null_control` is **conservative** (1/(N+1) is convex). `exceedance_test_over_seeds` is
   structurally the old averaging bug (median(p) == p(median S) exactly) but **fails safe**;
   keep it as spread only.

**Overturned — do not cite:**
- **NON-RELAXABILITY. Withdrawn 2026-08-13 as FALSE.** N=20 gives **455** attainable values
  against 39 at N=10 (~12x); granularity is relaxable. The pilot measured fractional
  *headroom*, not granularity, and the claim's stated mechanism is the estimator-bias account
  we cite approvingly (`mccabe2025alphabet` / `pan2026shade`). The honest residue: doubling N
  takes the **top decile from 2 points to 7**, so the lattice is sparsest exactly where the
  false-alarm claim lives. Supersedes the entry-31 contribution-(5) rewrite.
- **"22 DISTINCT VALUES". Retired 2026-08-13, entirely.** It is a sample size, monotone in n:
  E[distinct] for a random 80 from the same stratum is **23.0**, so 22 is the **37th
  percentile**; the same population gives 28 at n=200 and 35 at n=2000. Re-scoping it from 97
  targets to 80 (my first fix) was also wrong — the campaign union count was already 24 while
  I was editing. Replaced everywhere by the lattice (finding 2).
- The N=20 verdict's original conclusion, "zero power / FA not identifiable", and the
  class-separation-vs-noise claim (that used the quarantined pool).

---

## THE TWO POPULATIONS — the project's most-repeated error

**THEY ARE NESTED, NOT SEPARATE — read this before writing the word "separate".**
`_stratum_ids(want, seed, labels)` seed-shuffles a stratum and `select_stratified` takes
`[:n]`, so both pools are prefixes of the SAME seed-0 shuffle. Verified against the real
campaign ids: the 80 FA targets are exactly `right[:80]` (80/80, in order) — i.e. **40% of the
fair pool's correct stratum**; the hide targets are exactly `wrong[:n]`, prefix-verified at
every size checked. Recorded clean scores are bit-identical to the fair pool's (max |Δ| = 0).
Every attacked target is *inside* the fair pool.

| | fair pool | attacked pool |
|---|---|---|
| composition | 200 correct + 200 hallucinating | 80 correct (FA, complete) + the hide arm, **still growing** — 43 wrong as of the 01:08 2026-08-13 recompute, target 80 |
| relation | the wider sample | **a prefix of it**, one stratum per direction |
| AUROC | **0.704** [0.653, 0.753] | 0.579 **[0.416, 0.728]** — contains 0.704 |
| separation | 0.463 nats, d ≈ 0.76 | 0.184 nats, d = 0.28 — **QUARANTINED** |
| carries | claims about "the detector" | ceiling statistics on the FA arm |

⚠ **"97 targets = 80 correct + 17 wrong" is a `_def`-era snapshot and is now wrong.** The
hide arm was 17 when that figure entered the paper, 41 when critique_log 32 was written, 43 at
the last recompute, and it is heading for 80. **Any statistic with 97 in its denominator is
stale by construction.** Read the cell size from the JSONL; do not copy a number from here.

**Why the quarantine still holds — and the reason has changed.** Not because the attacked
pool is a different set of questions (it is not), but because it is a *selected sub-sample of
a single correctness stratum per direction*, truncated on the hide side, and the sample the
optimiser ran on. Within-stratum frequencies (ceiling) belong there; correct-vs-hallucinating
contrasts do not.

**Do NOT say the attacked pool "separates worse".** It is a score-independent sub-sample of
the same strata, so 0.579 estimates the *same* quantity as 0.704 and its CI [0.416, 0.728]
comfortably contains it. The gap is sampling error over ~1/30 as many ranked pairs.

This error has been found at **seven** sites. Sites 1–3 were fixed manually; sites 4 and 5
(Conclusion, "on the same pool"; Discussion, by adjacency) were found by the verification
sweep; **site 6 was found by the automated linter, in text written the same hour.** Site 7
(2026-08-13) is the "separate populations" framing corrected here — it reached a
*pre-registration* (critique_log 32's tau rationale, since struck through), which the linter
cannot catch because it checks that numbers name a pool, not that a claimed relation between
pools is true.

**`scripts/check_population_labels.py` runs in the test suite, and was rewritten on
2026-08-13** after an audit showed the first version caught **1 of 14** constructed errors
(the rewrite catches 14/14, with all 16 controls clean). It now enforces **attachment**, not
mere presence: every guarded number has an owning pool, and a foreign label that binds more
tightly is an error. It also guards **run provenance** (`_def` numbers surviving into `_defb`
text) — three such bugs were found by hand that night. It anchors on NUMBERS, never phrases:
a manual grep for "fair pool" missed `conclusion.tex` because the source reads `\emph{fair}
pool`. **What it still cannot catch is listed in its module docstring** — read that list
before trusting a green run; numbers written as words are in it, which is why prose still
needs a human read.

---

## Running now

Intended chain, with auto-restart (`scripts/run_definitive_chain.sh`):

```
recompute_fair.py --only se_false_alarm,se_hide --n 80 --tag _defb
  -> null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3
       --judge_batched --judge_batch_size 6 --dump_diag results/diag_defb.json
```

- **The null control is FALSE-ALARM ONLY.** The paper evaluates only that direction under the
  null control and the judge is validated for it only (over-splitting is conservative for FA,
  not for hide). Running the hide cell there costs ~70 GPU-h for an unused, un-adjudicable
  number. The MATRIX stage still runs both cells.
- **Do not assert which process is live — read it.** The script was written at 00:31 on
  2026-08-13; the chain running before that was a bare `A && B`. Check `/tmp/defb_chain.log`
  and the process list before claiming either.
- **FA cell: 80/80 COMPLETE.** Hide cell: in progress. Null control: not started (~67 GPU-h).
- Per-target cache at `~/.cache/se-research/samples/attacks/wk9_defb/` **inside WSL, not in
  the repo** — repo-scoped searches will find nothing and that is not evidence of failure.
- Fully resumable: `recompute_fair.py` skips completed qids. Killing it costs one target.
- **`recompute_fair.py` writes its report only at the very end** (single `write_text`). Watch
  the per-target JSONL for progress, not `results/`.
- **Nothing may edit `null_control.py` or `recompute_fair.py` while the chain can still reach
  them.** Python reads the script at *invocation*, so an edit now lands on the null control
  days from now, as a crash or as silent garbage. Two edits are queued for when it is idle:
  print achieved FPR in `recompute_fair`'s sweep table, and pass `n_attack_candidates` on
  `null_control`'s single-draw path.

---

## Owed, in priority order

1. **Task #24 — judge conditions (ii) and (iii)**, which `judge_validation.md` itself lists
   as unmet "before the paper cites it as sole adjudicator": validation on messy real
   sampled pairs (current 0.93 is clean gold aliases), and a differential-over-splitting
   check (attack vs benign cluster counts must not diverge). **Needs GPU.** The Abstract is
   scoped for now, not closed.
2. **Winner's curse under `_defb`** — ~15 min GPU, quantified, not launched. Only 25 of
   `_defb`'s 69 moved targets share a `best_query` with an already-fresh-scored `_def` target;
   **44 need fresh scoring (88 SE evals)**. The `_defb` selection-time mean is already +0.609
   over 69 targets against +0.698 over 60, so **the Abstract's shrinkage and retention will
   both move.** Cheap, but it competes with the hide cell for the device.
3. **Task #27 — the definitive null control.** The gate on the attack verdict.
4. **Table 1 fill-in.** Caption already names the population; attach n per row as written.
   The linter is watching this table specifically.
5. **Human equivalence audit** — harness exists (`prepare_equivalence_audit.py`), unrun.
6. **Regenerate `fair_recompute_report.md`** from `_defb` when the matrix finishes.
7. **If the crossing test is ever promoted** from disclosed secondary diagnostic to a claim
   statistic: re-fix tau on a genuinely disjoint split (the held-out 120, or the 1,224 correct
   items outside the fair pool), say which was used, and fix the arm-exchangeability problem
   first — `feasible_objs` is a running-record subset (0 of 3058 recorded candidates fall
   below their target's clean score), so any p from it is an upper bound on the evidence. It
   also needs the null control's benign arm to exist at all.
8. **A negative control for the nesting check.** `verify_nesting` asserts the prefix property
   but nothing demonstrates the assertion failing at another seed, so it is unproven as
   non-vacuous.

*(Closed 2026-08-13: the three unverified citations — Calibration Attacks, "ConfSmooth", DEPO
— are verified from primary sources and in the bib as `obadinma2024calibration`,
`martinezmartinez2026uat` and `wang2026depo`. "ConfSmooth" is not a paper: it is an ATTACK
inside the UAT paper, not the defence the sweep claimed. Fair-pool granularity is done:
`results/fair_pool_granularity.md`.)*

---

## Process rules, learned the hard way

- **Check every gate ruling against the committed artifact before applying it.** The critic
  was wrong once (the judge number) and applying it on authority would have shipped an error.
- **Before claiming two samples are independent, read the selector.** Not the names, not the
  design intent — the code. That claim reached a pre-registration before anyone checked it.
- **Ask "monotone in n?" before any count enters a sentence.** A statistic that moves while
  you type it is a sample statistic. "22 distinct values" entered on 2026-08-03 and survived
  ten days, through two audits, because nobody asked.
- **Grep your own artifacts for the counterexample before publishing the claim.** The number
  that refuted non-relaxability sat in `CORRECTIONS_2026-08-02.md:43` for eleven days.
- **Never assert a property of your own script from memory.** Two errors on 2026-08-13 were
  descriptions of code written the same week and not re-read.
- **Sweep on numbers, not phrases.** LaTeX markup defeats phrase matching.
- **A green test suite next to a known-broken statistic reads as validation of it.** Pin the
  failure or delete the test (`flip_test`, and the b clamp, are both pinned as failures).
- **Verify agent claims yourself.** A literature sweep called `zheng2026matchedctrl` a
  structural twin of our budget-matched control; reading it showed it is a format-matched
  control for VLM test-time scaling. Every bib `annote` records who verified what, when.
- **Do not assert run state — read it.** Both directions have burned us: a stale "FA 58/80"
  reported to the user, and a false "nothing has been written in 9 hours" that was a
  repo-scoped search missing the WSL cache.
- **Unmeasured claims are the worst failure mode.** The Abstract asserted that benign
  rephrasing reaches the ceiling comparably to the attack. Never measured — and this log's
  lines 826 (entry 24) and 1126 (entry 28) had *pre-committed* not to say it until it was.
