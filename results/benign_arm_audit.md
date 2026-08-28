# Benign-arm audit: short and empty benign arms in `null_control_ckpt_defb.jsonl`

Audit date 2026-08-28. Read-only against the LIVE checkpoint (68 complete records at read
time, run still in progress). Nothing was written to the checkpoint, no GPU work was run,
`scripts/null_control.py` was not edited.

---

## VERDICT

The concern as stated is **a disclosure item, not a claim-level defect**. Three separate
findings, ordered by severity:

| # | Finding | Severity |
|---|---|---|
| 1 | **Empty benign arms** (3 targets) | **Non-issue.** Legitimate — no feasible paraphrase exists for those questions. Correctly dropped everywhere. The `nan` is cosmetic. |
| 2 | **Partial benign arms** (6 targets) | **Disclosure item.** Real bias in the stated direction, but worth **+0.008 nats (NLI) / +0.012 nats (judge)** on the paired net — second decimal, crosses no interval. It does not touch the claim statistic at all. |
| 3 | **No-op targets scored against a null that cannot decline** (found en route, not in the brief) | **CLAIM-LEVEL DEFECT.** Worth **+0.052 to +0.067 nats** on the NLI paired net — 6.6x to 8.5x finding 2 — and it decides whether the adjudicator's interval covers zero. |

**The concern is right in sign and wrong in magnitude, and it points at the smaller of two
adjacent problems.** The mechanism the brief describes is real, but the asymmetry that
actually matters is not "the benign arm drew fewer than K" — it is "on 11 targets the
attack was allowed to return the original question and the benign arm was not."

---

## Corrections to the framing I was given

Verified against the artifacts; the brief was accurate on the data but understated in
three places and wrong in one.

1. **All three empty-arm targets have `attack_move` all zeros**, not just `qb_2689`.
   `qb_565`, `qz_3393` and `qb_2689` are all exactly `+0.000` in nli/exact/judge.
2. **The `nan` in the log came from `qz_3393` and `qb_2689`**, at
   `dashboard/overnight_20260814.log:133` and `:228`. Not `qb_2689` alone.
3. **The `embed` list is length 0 on all 68 targets, by design** — the run was launched
   with `embedding_model=""` (confirmed in every record's `cfg`), so the embedding arm is
   inactive and `null_control.py:426` never appends it. "All four lists length 0" reads as
   4-of-4 anomalous; it is 3-of-3 anomalous plus one arm that was never run.
4. **`qb_6105` is not merely a short arm — it is a fourth degenerate target.** Its
   `attack_move` is all zeros too, and it belongs with the empty three, not with the
   partial five. Treating it as "a partial arm at k=1" is what makes the k=1 bias term
   look alarming; it is really a no-op target that happened to scrape one benign draw.

---

## 1. Mechanism

**The attempts cap at `scripts/null_control.py:174`, binding against the feasibility gate.**

```python
168  def _benign_moves_arms(question, before, attack, pair, gen, K, seed, ...):
172      proposer.seed_proposer(seed)
174      while len(nm) < K and tries < K * 5:      # <-- 250 attempts at K=50
175          tries += 1
176          cand = proposer.propose(question, pair.lm)
177          if not feasibility.check(cand, question, pair.nli).feasible:
178              continue
```

The loop has exactly two exits: `len(nm) == K`, or `tries == 250`. Line 177 is the **only**
`continue`. Therefore `m < 50` is equivalent to "the gate rejected exactly `250 - m` of 250
proposals", and `m/250` is that question's benign feasibility pass rate.

The three candidate mechanisms in the brief that are **ruled out** by reading the code:

- **Not a swallowed exception.** There is no `try`/`except` anywhere in
  `_benign_moves_arms`. An exception would propagate out of the target loop before the
  record is appended (`null_control.py:412-415`), so a short list cannot be an
  exception artifact — the record's existence proves the loop exited normally.
- **Not deduplication.** Nothing dedupes. `proposer.propose_many`'s docstring states
  "Duplicates are allowed"; the benign loop appends every feasible candidate including
  repeats. Duplicates cost GPU time but cannot shorten an arm.
- **Not a cap alone.** The cap is necessary but not sufficient — it only bites because
  the gate's rejection rate on these questions exceeds 80%.

**Why the gate rejects so hard on specific questions.** `proposer.propose`
(`src/se/attacks/proposer.py:78-104`) decodes **greedily** — `M.generate_one`, `do_sample=False`
(documented at `proposer.py:12-19`). All candidate diversity comes from randomising the
instruction: 10 verbs x 8 styles x 5 templates = 400 distinct prompts, and many collapse to
the same output. So the reachable candidate set per question is small, deterministic, and
fixed. `feasibility.check` then rejects on three grounds
(`src/se/attacks/feasibility.py:44, 54, 59`): identical-to-original after normalisation,
length ratio outside [0.4, 2.5], or failure of bidirectional NLI entailment. A question
whose small reachable set lands entirely inside those rejection regions yields an empty arm
**deterministically**, not by unlucky sampling.

Observed benign pass rates (`m/250`):

| target | m | pass rate | attack-side feasibility (`n_feasibility_passed`/`n_feasibility_checks`) |
|---|---|---|---|
| qb_565 | 0 | 0.0% | 0/180 |
| qz_3393 | 0 | 0.0% | 0/175 |
| qb_2689 | 0 | 0.0% | 0/5 |
| qb_6105 | 1 | 0.4% | 0/71 |
| qz_1745 | 26 | 10.4% | 41/51 |
| dpql_250 | 27 | 10.8% | 9/71 |
| qz_4576 | 27 | 10.8% | 6/61 |
| qb_2922 | 35 | 14.0% | 4/15 |
| qb_2833 | 38 | 15.2% | 20/43 |

---

## 2. Legitimate, or a bug?

**Two different phenomena, and the brief merges them.**

### 2a. The four degenerate arms are the known-legitimate case. Not a bug.

`qb_565`, `qz_3393`, `qb_2689`, `qb_6105` are **exactly** the targets where the optimiser
also found nothing: `best_query == question` and `n_feasible_at_best == 0` for all four.
This is the same phenomenon `scripts/winners_curse_reeval.py:433` excludes
("optimiser found nothing; no selection to re-test"), now visible on the benign side.

The evidence is strong because the two arms fail independently and agree:

- `qb_565`: 0 of 180 attack-side feasibility checks passed, **and** 0 of 250 benign.
- `qz_3393`: 0 of 175, **and** 0 of 250.
- `qb_6105`: 0 of 71, **and** 1 of 250.
- `qb_2689`: 0 of 5 (weak on its own), **and** 0 of 250 benign (decisive).

These questions have no feasible paraphrase **under this proposer and this gate**. That is
a property of the question, and an empty arm is the correct representation of it.

**The implication runs one way only, and this matters.** Of the 10 no-op targets present in
the checkpoint, only these 4 have degenerate benign arms. The other six — `qb_6190`,
`qb_7207`, `qb_723`, `qb_7262`, `qz_2444`, `tc_2256` — got a full 50 benign draws. So
"optimiser found nothing" does **not** imply "no feasible paraphrase exists"; for six of
them the benign sampler found 50. Do not use the empty arm as a proxy for the no-op set,
or vice versa.

### 2b. The five genuine partial arms are a budget artifact. Also not a bug, but not the same thing.

`qz_1745` (26), `qb_2833` (38), `qb_2922` (35), `qz_4576` (27), `dpql_250` (27) are all
`success: True` with a real `best_query != question` and `n_feasible_at_best` of 38, 4, 4,
5 and 9. Nothing is infeasible about them. They are moderately hard to paraphrase, the
gate passed ~10-15%, and the 250-attempt cap bound before K=50 was reached.

This is a **shortfall against the declared budget**, and the project already pre-committed
to how it is handled (`docs/critique_log.md:1020-1021`):

> If compute forces a smaller m, the shortfall is REPORTED as such — m is not re-chosen
> after seeing results, and no other m may be substituted post hoc.

By the project's own pre-registration these six are a reporting obligation, not a defect.
The obligation is currently unmet (see §4).

---

## 3. Quantifying the short-arm bias

**Method.** The 59 targets with m=50 are the donor set. For each donor, subsample k of its
50 benign moves without replacement (3000 reps), take the max, average to get E[max_k];
the deficit is `max_50 - E[max_k]`. Mean over the 59 donors. This uses the observed benign
distributions from the targets that do have 50, as the brief asked.

(A bootstrap from each partial target's *own* m draws was tried first and discarded: the
plug-in bootstrap cannot estimate a maximum, because a resampled max can never exceed the
observed max. It returns a deficit of ~0 by construction. The donor method above is the
correct one.)

**E[max_50] - E[max_k], mean over 59 donors, nats:**

| k | NLI | judge |
|---|---|---|
| 1 | +0.4238 | +0.5242 |
| 26 | +0.0235 | +0.0677 |
| 27 | +0.0217 | +0.0639 |
| 35 | +0.0115 | +0.0368 |
| 38 | +0.0088 | +0.0283 |
| 50 | 0 | 0 |

**Why it is so small.** These benign move distributions are extremely discrete. Median
**5 distinct values** among 50 draws under NLI (min 1, max 12); **3** under the judge. And
on average **28.4%** (NLI) / **26.6%** (judge) of a target's 50 draws sit *exactly at* that
target's maximum. With ~28% of the mass at the max, the chance that 26 draws all miss it is
0.716^26 ~ 2e-4. The max is effectively attained by k=26. The winner's-curse intuition —
"max of 26 is systematically below max of 50" — is correct for a continuous score and
nearly vacuous for one this saturated.

**Applied to the six actual partial targets:**

| arm | sum of deficits | spread over the paired net (n=65) |
|---|---|---|
| NLI | +0.5111 nats | **+0.0079 nats** |
| judge | +0.7847 nats | **+0.0121 nats** |

**Materiality, against today's provisional intervals (68/80, NOT for the paper):**

- NLI paired net `+0.1926 [+0.1088, +0.2784]`. Half-width 0.0848. The inflation of
  **+0.0079** is **9.3% of the half-width and 4.1% of the point estimate**. De-biased:
  `+0.1847`. Still clear of zero.
- Judge paired net `-0.1515 [-0.3038, +0.0018]`. De-biased: `-0.1636` — the correction
  moves it **away** from zero on the negative side, i.e. **against** the attack. For the
  adjudicator arm the short-arm bias is in the conservative direction.

**And 83% of the NLI deficit (0.4238 of 0.5111) is the single k=1 target `qb_6105`** — which,
per §2a, is a no-op target whose presence in the paired net is a separate and larger
problem. Excluding it, the five genuine partial arms are worth **+0.0013 nats** on the NLI
paired net. That is the third decimal.

**Answer to the question as posed: +0.008 nats (NLI), +0.012 nats (judge). Not material.**

---

## 4. What the analysis actually does

**Empty arms are DROPPED — consistently, deliberately, and everywhere. Never zero-filled,
never NaN-propagated.** Five guard sites:

| site | guard |
|---|---|
| `scripts/null_control.py:83` | `if benign:` — guards `beats_bmax`, `beats_bp90`, `pctiles`, `net_vs_bmean` |
| `src/se/stats.py:824` | `pairs = [(a, max(b)) ... if b]` — `paired_max_net` |
| `src/se/stats.py:436` | `if not bl: continue` — `exceedance_counts` |
| `src/se/stats.py:597` | `if not bl: continue` — `exceedance_counts_randomized` |
| `src/se/stats.py:778` | `[... for k, m in counts if m > 0]` — `exceedance_test` |

The skip is intentional and tested: `tests/test_budget_matched.py:52-56`, comment
"targets with empty benign lists are skipped, not crashed".

**The `nan` is cosmetic.** It arises at `scripts/null_control.py:419`, inside the per-target
progress `print`, from `np.mean(bnl)` over an empty list. It is not stored (the record at
`:405-412` stores the empty list itself) and it does not reach any statistic. The numpy
"invalid value encountered in scalar divide" warning is the same event. No NaN reaches a
mean.

**Partial arms are NOT dropped, and for the claim statistic that is correct by construction.**

`exceedance_test` (`src/se/stats.py:739-810`) is the pre-committed decision-rule statistic
(`docs/critique_log.md:1023`: "the decision rule's statistic is the randomized-tie
exceedance test"). Its null is

> K_j ~ BetaBinomial(m_j; a=1, b=N), E[K_j] = m_j/(N+1)

with **each target's own m_j**, carried through as the second element of every `(k_j, m_j)`
pair. `exp = sum(m/(N+1) for _, m in counts)` at `:781`, and the exact convolution at
`:785-789` uses `betabinom.pmf(np.arange(m+1), m, 1, N)` per target with that target's own
m. A short arm therefore reduces that target's expected exceedance count and its weight in
the convolution; it **does not bias the test**. Calibration holds; only power falls. The six
partial targets contribute 0.846 of the total expected 17.055.

**This is the central refutation of the concern.** The claim statistic is not a
max-vs-max comparison and never was. `paired_max_net` is explicitly labelled
"(supplementary)" at `null_control.py:466`, and `beats_benign_max` is labelled
"comparison only / budget-biased" at `:84`. The July episode the brief cites (critique_log
13, then 21) was superseded twice: entry 21 replaced the percentile with the paired
benign-max, and entry 26 replaced *that* with the exceedance test. The partial arms bite
only on the statistics the repo has already demoted.

Statistics that are **unaffected** by short arms: `net_vs_bmean` and `_per_target_nets`
use `np.mean(benign)`, which is unbiased in m (merely noisier). So the net-vs-benign-mean
and the survival ratio carry no short-arm bias at all.

Statistics that **are** biased low by short arms: `paired_max_net`, `beats_benign_max`, and
`np.percentile(benign, 90)`. All quantified in §3, all supplementary.

### The disclosure gap is real, and it is the "second is worse" case

- **Disclosed** for the claim statistic: `null_control.py:489` prints
  `n_targets={rnd['n_targets']} (of {len(outcomes)} in cell)`. Correct and explicit.
- **NOT disclosed** for `paired_max_net`: `stats.py:827` computes `n`, and
  `null_control.py:464-469` prints only the CI and the sign test. The reader never learns
  the subtrahend's denominator.
- **NOT disclosed** for the whole `summarize_bands` block: the section header at
  `null_control.py:444` reads `## SE / false_alarm  (n=80)`, while the four lines beneath it
  — p90 rate, max rate, mean percentile, net-vs-mean — are computed over the non-empty
  subset. `summarize_bands` returns `"n": len(attack_moves)` (all targets) but the rates are
  built from the guarded subset at `:83-87`, and neither number is printed.

That second and third bullet are exactly the failure mode the brief names: a silent drop
that changes the effective n without disclosing it. It is real. It affects the supplementary
statistics only.

---

## 5. Effective n

Pre-registration: n >= 80 per stratum (`docs/critique_log.md` entries 13 and 21).

| convention | n today (68 complete) | n projected at 80 |
|---|---|---|
| targets attacked | 68 | 80 |
| contribute to any benign-referenced statistic (non-empty arm) | **65** | ~76-77 |
| ...and at the full declared budget m=50 | **59** | ~70 |
| excluding no-op targets, matching `winners_curse_reeval.py:433` | **58** | **69** |

**The honest denominator is 69, not 80** — and the paper already uses exactly that number
for the neighbouring analysis: `paper/sections/limitations.tex:111` states "The re-scored
set is the 69 of the 80 false-alarm targets on which the optimiser found a paraphrase at
all; on the other 11 the search returned the original question". The null control does not
currently apply that denominator, and the discrepancy is not disclosed anywhere.

**The pre-registered n >= 80 is not met by the null control under any of the four
conventions.** That is a disclosure obligation regardless of which convention is adopted.

**What the paper must disclose:**

1. The effective n for every benign-referenced statistic, separately from the 80 attacked.
2. That 3 (projected ~3-4) targets have no benign comparison because no feasible paraphrase
   exists for those questions, with the joint evidence (0/180 and 0/250 for `qb_565`, etc.).
3. That 6 targets fell short of the declared K=50, with their actual m — the standing
   pre-commitment at `critique_log.md:1020-1021` already requires this.
4. That the attempt cap is `K*5`, so a shortfall means a gate pass rate below 20%, and that
   the shortfall is therefore informative about the question rather than random.

---

## 6. The defect the brief did not ask about, which is larger than the one it did

**On no-op targets the attack is scored on an action the null is forbidden from taking.**

`scripts/null_control.py` does not apply the exclusion that
`scripts/winners_curse_reeval.py:433` applies. On the 10 no-op targets present,
`attack_move` is exactly `+0.000` in every arm — not because the attack achieved nothing
measurable, but because `best_query == question`, so `before == after` by construction.

Meanwhile the benign arm **cannot** draw the no-op: `feasibility.py:44` rejects any
candidate identical to the original (`require_different=True`, and it is the first check).
So the attack has an option in its action set — decline, return the original, score 0 —
that the null is structurally prohibited from exercising. When a target's benign moves are
all negative, the attack "wins" that target by having done nothing:

| target | m | attack_move | benign_max (NLI) | paired net |
|---|---|---|---|---|
| qb_6190 | 50 | +0.0000 | -1.8344 | **+1.8344** |
| qb_6105 | 1 | +0.0000 | -1.0044 | **+1.0044** |
| qb_723 | 50 | +0.0000 | -0.6661 | **+0.6661** |
| tc_2256 | 50 | +0.0000 | -0.3296 | **+0.3296** |
| qb_7262 | 50 | +0.0000 | -0.1910 | **+0.1910** |
| qz_2444 | 50 | +0.0000 | -0.1910 | **+0.1910** |
| qb_7207 | 50 | +0.0000 | -0.1386 | **+0.1386** |

**Effect on the paired net** (provisional, 68/80):

| arm | A. as-is | B. no-op neutralised* | C. no-op excluded |
|---|---|---|---|
| NLI | +0.1926 [+0.1088, +0.2784] | +0.1256 [+0.0654, +0.1936] | +0.1407 [+0.0765, +0.2136] |
| exact | +0.0176 [-0.0357, +0.0890] | -0.0076 [-0.0461, +0.0399] | -0.0085 [-0.0538, +0.0448] |
| **judge (adjudicator)** | **-0.1515 [-0.3038, +0.0018]** | **-0.1868 [-0.3290, -0.0373]** | **-0.1987 [-0.3569, -0.0330]** |

\* B allows the benign arm the same decline option: `benign_max -> max(benign_max, 0)` on
no-op targets only. n stays 65.

- NLI: the as-is convention inflates the net by **+0.052 to +0.067 nats** — **27% to 35% of
  the point estimate**, and **6.6x to 8.5x** the short-arm bias the brief asked about.
- exact: **sign flip**, +0.0176 to -0.0085.
- judge: the convention **decides whether the adjudicator's interval covers zero**. As-is it
  includes zero ("no effect detected"); under either fix it excludes zero on the negative
  side ("benign paraphrasing significantly beats the attack"). That is claim-level. It does
  not create an attack claim — the sign is negative either way — but it changes what the
  paper can say about the adjudicator.

**Effect on the exceedance claim statistic.** The 7 no-op targets with a non-empty benign
arm contribute an expected 1.65 to E[S], against observed K of:

| arm | observed K from no-op targets | expected | direction |
|---|---|---|---|
| NLI | **0** | 1.65 | pushes S below its null mean -> **ANTI-CONSERVATIVE** (toward rejecting H0, favouring the attack) |
| exact | 52 | 1.65 | conservative |
| judge | 69 | 1.65 | conservative |

Arm-dependent, and anti-conservative in precisely the permissive NLI arm — where all benign
draws fall below the attack's structural 0, so each no-op target donates a free
zero-exceedance and 1.65 of unearned expected count.

This also **violates the exceedance test's stated exchangeability assumption**
(`stats.py:753-757`: "a target's N attack candidates and its m benign draws are exchangeable
draws from one distribution F_j"). On a no-op target the attack's reported value is not a
draw from F_j at all — F_j is the feasible-paraphrase distribution, and the gate guarantees
it can never produce the no-op.

Current exceedance p-values are 0.98-1.00 in every arm (obs 28 vs exp 17.1 for NLI; the
attack is nowhere near rejecting the null), so **nothing is being wrongly claimed today**.
The mechanism is live and would matter at a borderline result.

**The counter-argument, which must be weighed before acting.** Dropping the 11 no-op
targets removes 11 attack *failures* from the denominator, and would inflate any success
*rate* computed over the survivors. Option C is outcome-adjacent selection. **Option B
(neutralise, keep n=80) is the assumption-matched fix**: it makes the two arms play the same
game by giving the null the same decline option, without changing the denominator. Whichever
is adopted must be pre-registered *before* the run completes, not chosen after seeing which
way it moves the judge interval — the project has an explicit standing rule against
post-hoc statistic selection (critique_log entry 26, and the B3 lesson in entry 21).

---

## Provenance and limits of this audit

- Checkpoint read defensively at 199,836 bytes / 68 complete records, 0 torn. A later read
  caught a torn 69th line mid-write, confirming the run is live; **only complete records
  were parsed**, and the parser skips unparseable lines exactly as `_ckpt_load` does.
  All 68 share one `cfg`: `K=50, n_seeds=3, judge=Qwen/Qwen2.5-7B-Instruct,
  embedding_model="", embed_threshold=0.82`.
- Outcomes read from `data/cache/attacks/wk9_defb_snap/triviaqa_se_false_alarm.jsonl`
  (80 records, snapshot 2026-08-13T01:29:21Z). **The live campaign directory is
  `/home/abhi/.cache/se-research/samples/attacks/wk9_defb` inside WSL and was NOT read** —
  the snapshot's `SNAPSHOT.txt` records n_records=80 for the false-alarm cell and its sha256,
  but I did not verify the live file still matches. If `recompute_fair.py` has touched the
  false-alarm cell since 2026-08-13, the `n_feasible_at_best` and `best_query` values here
  need re-checking.
- `N = 181` used as the attack budget throughout (`n_objective_calls` is 181 on every
  target inspected, so median = 181).
- **Every number in §3 and §6 is provisional**: computed on 68 of 80 targets while the run
  is live. They establish direction and order of magnitude. None of them is a paper number.
- No GPU work, no pytest run, no writes outside this file. `scripts/null_control.py`,
  `paper/`, and the checkpoint were not modified.
