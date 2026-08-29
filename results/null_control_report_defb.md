# Null control, definitive: does the attack beat a budget-matched benign search?

**Campaign `_defb`, SE detector, false-alarm cell, 80/80 targets complete (run finished
2026-08-29 03:57). Analysis by `scripts/null_control_defb_report.py`; regenerable and
byte-identical on re-run.**

Convention for the paired net is the one locked in
`results/PREREG_noop_convention_2026_08_28.md` **before** the final 12 targets landed:
convention (d), the benign arm may decline. All four conventions are reported below
because that pre-registration requires it.

## 0. The answer in one paragraph

**No.** On the pre-committed claim statistic — the randomised-tie exceedance test, whose
null prices the attack's 181-candidate search budget into the comparison — the attack
produces *more* benign exceedances than the null expects in every arm, so the one-sided
p-value P(S <= s_obs) is far from significance: median p = 0.9392 (NLI),
1.0000 (exact), 1.0000
(judge) over 101 tie-break realisations, against a 0.05 threshold; in no arm and
under no realisation does the test reject. On the supplementary paired net under the locked
convention (d), the attack's advantage over a budget-matched benign search is
+0.1097 [+0.0626, +0.1612] nats in the detector's own NLI arm — positive but measured with the
clusterer the attack was optimised against — -0.0269 [-0.0637, +0.0146] nats under exact match, and
**-0.1729 [-0.3023, -0.0394] nats under the pre-registered independent LLM-judge adjudicator, an
interval lying entirely below zero.** The sign is negative: under the adjudicator the
optimised attack moves semantic entropy *less* than the best of 50 random feasible
paraphrases drawn at matched budget, by about 0.17 nats per target. The
campaign has 80 targets, but the paired net and the exceedance test both run on
n = 77 and convention (c) on
n = 69; those denominators are itemised in section 4 and
a reader must not read any of them as 80. The paper's claim of no attack effect is
supported, and strengthened: the effect is not merely absent under the independent
adjudicator, it is reversed.

## 1. Provenance and integrity of the inputs

| file | bytes | sha256 (first 16) | content |
|---|---|---|---|
| `results/null_control_ckpt_defb.jsonl` | 236,682 | `edaacc5806cf2d97` | 80 JSONL records, 80 unique question_ids |
| `results/diag_defb.json` | 350,708 | `88ba6de6f3b51981` | 80 records (`--dump_diag`) |
| `data/cache/attacks/wk9_defb_snap/triviaqa_se_false_alarm.jsonl` | 157,837 | `b3e8c1c283ea7789` | 80 campaign outcomes |

- Checkpoint: **80 records parsed, 80 unique question_ids, 0 torn lines**, file ends with a newline. Every record carries the same cfg.
- Single cfg across all 80 records: `{"K": 50, "embed_threshold": 0.82, "embedding_model": "", "judge_model": "Qwen/Qwen2.5-7B-Instruct", "n_seeds": 3}` (1 distinct cfg).
- All records are `detector=se`, `attack=false_alarm`: ['se'] / ['false_alarm'].
- Campaign outcomes are read from the in-repo snapshot `wk9_defb_snap` (2026-08-13). Its
  md5 was verified equal to the live WSL campaign file
  `/home/abhi/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl`
  (`24ffbc159468924cc922449a688aa4bc`, mtime 2026-08-12 07:02), so `recompute_fair.py` has
  **not** touched the false-alarm cell since the snapshot. This discharges owed item 1 of
  the pre-registration. (The neighbouring `triviaqa_se_hide.jsonl` *has* changed; it is not
  used here.)

## 2. The exceedance test — the pre-committed claim statistic

`docs/critique_log.md:1023` pre-commits the decision rule to the **randomised-tie**
exceedance test (`se.stats.exceedance_test` fed by `exceedance_counts_randomized`).
Under H0 the attack's N candidates and a target's m benign draws are exchangeable draws
from one distribution, so the number of benign draws reaching the attack's max is
`K_j ~ BetaBinomial(m_j; a=1, b=N)` with `E[K_j] = m_j/(N+1)`; the null of `S = sum_j K_j`
is obtained by exact convolution and the one-sided p-value is `P(S <= s_obs)`. **Fewer
exceedances than expected is evidence for the attack**, so a small p rejects H0 in the
attack's favour.

- `N = 181` attack candidates per target: `n_objective_calls` is **exactly 181 on all 80 targets** (min = max = median), so the heterogeneous-N caveat in
  `exceedance_counts_randomized`'s docstring does not bite here.
- Tie multiplicity `b_j = n_feasible_at_best` (clamped to >= 1): min 1, max 131. At the measured b, max b <= N, so **no target was clamped** in the
  headline row and the p-values are not degraded toward the disqualified strict rule.
  (The `b x 2` sensitivity row below does clamp; its count is shown there.)

| arm | n_targets | observed S | expected E[S] | p (seed 0) | p median over 101 seeds | p range | frac p<=0.05 | n_eff |
|---|---|---|---|---|---|---|---|---|
| nli | 77 | 30 | 20.35 | 0.9704 | **0.9392** | [0.2291, 0.9998] | 0.000 | 122.5 |
| exact | 77 | 383 | 20.35 | 1.0000 | **1.0000** | [1.0000, 1.0000] | 0.000 | 8.7 |
| judge | 77 | 636 | 20.35 | 1.0000 | **1.0000** | [1.0000, 1.0000] | 0.000 | 4.8 |

**What this licenses.** Nothing in the attack's favour, in any arm. The observed
exceedance total is *above* its null expectation everywhere (NLI 30 vs 20.4; exact 383 vs 20.4; judge 636 vs 20.4), which
is the direction *against* the attack, and no tie-break realisation out of 101 produced p <= 0.05 in any arm. The paper may state that the pre-committed
test does not reject the null that the optimiser's guidance carries no signal. It may not
state a positive attack effect on this statistic, and it does not need to.

`n_eff` reads as *"the beam search is worth this many random paraphrases"*: in the NLI arm
the 181-candidate optimiser is worth about 122 random
draws, i.e. **less than its own budget**; under the judge it is worth about
5. The estimator is method-of-moments and upward-biased
when the mean count is small, so treat it as indicative only.

**Disagreement between tie rules, disclosed as `critique_log` 26 requires.** The two
disqualified fixed tie rules are reported as diagnostics only:

| arm | strict (b > a): p, obs | conservative (b >= a): p, obs | randomised (pre-committed) |
|---|---|---|---|
| nli | 0.0000, 2 | 1.0000, 508 | 0.9392, 30 |
| exact | 1.0000, 222 | 1.0000, 1695 | 1.0000, 383 |
| judge | 1.0000, 472 | 1.0000, 1757 | 1.0000, 636 |

The strict rule 'rejects' in the NLI arm (p = 0.0000) and
that is an artifact, not a finding: it is disqualified at H0 level 0.995 precisely because
the score has an atom at the log(N) ceiling, and the benign arms here are extremely lumpy
(median 5 distinct values among 50 NLI draws, with
29.8% of draws sitting exactly at that target's maximum).
Counting only strict exceedances discards those ties and manufactures evidence. The
conservative rule is disqualified in the opposite direction (power 0.05). Neither may be
quoted as a result; the disagreement is exactly the ceiling-saturation signature the
project already documented, not the attack outperforming chance.

**Robustness to an error in the measured tie multiplicity b** (`exceedance_test_over_tie_scales`; scaling b up shrinks p, so this is the one-sided check
that matters):

| arm | b x 0.25 | b x 0.5 | b x 1 | b x 2 |
|---|---|---|---|---|
| nli | 1.0000 | 1.0000 | 0.9392 | 0.2291 |
| exact | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| judge | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| targets clamped to b=N | 0 | 0 | 0 | 10 |

No scale in the plausible range brings any arm near 0.05, so the non-rejection is a
property of the data and not of the optimiser's bookkeeping. The `b x 2` column clamps 10 targets to b = N, which raises
its p-value relative to an unclamped doubling; even so it stops at 0.2291 in the NLI arm, and the doubling
itself is already an implausible bookkeeping error given that b is read straight off the
instrumented optimiser.

**One assumption is violated and the violation is in the attack's favour.** The
exchangeability premise requires the attack's reported value to be a draw from the same
feasible-paraphrase distribution as the benign draws. On the no-op targets it is not: the
optimiser returned the original question, so `attack_move` is a structural 0, while
`feasibility.check(..., require_different=True)` rejects the no-op as its *first* test, so
the benign arm can never produce it. Those targets donate free zero-exceedances in the NLI
arm, pushing S down, i.e. **anti-conservatively, toward rejecting H0 in the attack's
favour**. Since the test does not reject even with that help, the violation changes no
conclusion here. It is unresolved and would matter at a borderline result.

## 3. The paired net, supplementary — all four conventions plus the audit's variant

The paired net is `attack_move_j - benign_max_j` averaged over targets, with a paired
bootstrap 95% interval (20,000 resamples of targets, seed 20260828). It is
**supplementary**; the claim statistic is section 2.

Conventions, stated precisely because two of them are easy to conflate:

- **(a) as-is** — `attack_move - benign_max`, no adjustment.
- **(b) no-op pairs neutralised** — the paired difference is set to 0 on every no-op
  target; n preserved.
- **(b')** the variant in `results/benign_arm_audit.md` §6 — `benign_max -> max(0, benign_max)`
  **on no-op targets only**; n preserved. (b) and (b') coincide on a target only when its
  benign max is <= 0; the number of no-op targets in the paired net whose benign max is
  **positive**, and which therefore separate the two, is 0 (nli), 1 (exact), 3 (judge).
- **(c) no-op targets excluded** — dropped from the average; n falls.
- **(d) benign may decline (LOCKED)** — `attack_move - max(0, benign_max)` on **every**
  target; n preserved.

### Headline — convention (d)

| arm | paired net (nats) | n | sign rate: `attack_move > max(0, benign_max)` |
|---|---|---|---|
| **nli** — NLI (the detector's own clusterer — shared, permissive bound) | **+0.1097 [+0.0626, +0.1612]** | 77 | +0.3506 [+0.2468, +0.4545] |
| **exact** — exact-match (independent, strict — over-splits on surface form) | **-0.0269 [-0.0637, +0.0146]** | 77 | +0.0649 [+0.0130, +0.1299] |
| **judge** — LLM judge Qwen2.5-7B-Instruct (independent — the PRE-REGISTERED adjudicator) | **-0.1729 [-0.3023, -0.0394]** | 77 | +0.1688 [+0.0909, +0.2597] |

The headline interval is a property of the data, not of one bootstrap seed. Re-running the
bootstrap at seeds 0, 1, 42 and 999999 as well as the pre-registered 20260828, and adding
two distribution-based tests that use no resampling at all:

| arm | envelope of the 5 bootstrap intervals | median paired diff | share of targets with a negative diff | one-sample t | Wilcoxon signed-rank |
|---|---|---|---|---|---|
| nli | [+0.0626, +0.1616] | +0.0000 | 2.6% | p = 4.09e-05 | p = 6.334e-05 |
| exact | [-0.0641, +0.0153] | +0.0000 | 18.2% | p = 0.1812 | p = 0.03771 |
| judge | [-0.3058, -0.0386] | -0.1386 | 51.9% | p = 0.01251 | p = 0.006912 |

The judge interval excludes zero under every seed and both non-bootstrap tests agree
(t p = 0.01251, Wilcoxon p = 0.006912). The exact
arm is the one place the two families disagree — its bootstrap and t intervals cover zero
while the signed-rank test does not (p = 0.03771) — because that arm's
differences are a spike at 0 with a long negative tail, so a rank test sees the asymmetry
that a mean does not. The exact arm is reported as covering zero, which is the conservative
reading and the one consistent with the pre-registered statistic.

### Sensitivity — the table the pre-registration requires

| convention | n (nli/exact/judge) | NLI | exact | judge (adjudicator) |
|---|---|---|---|---|
| (a) as-is | 77/77/77 | +0.1835 [+0.1141, +0.2624] | +0.0077 [-0.0443, +0.0683] | -0.1188 [-0.2544, +0.0188] |
| (b) no-op PAIRS neutralised to 0 | 77/77/77 | +0.1261 [+0.0719, +0.1859] | -0.0064 [-0.0434, +0.0355] | -0.1364 [-0.2662, -0.0031] |
| (b') benign may decline ON NO-OP TARGETS ONLY | 77/77/77 | +0.1261 [+0.0719, +0.1859] | -0.0136 [-0.0536, +0.0300] | -0.1486 [-0.2797, -0.0155] |
| (c) no-op targets excluded | 69/69/69 | +0.1408 [+0.0813, +0.2063] | -0.0071 [-0.0482, +0.0395] | -0.1522 [-0.3004, -0.0047] |
| **(d) benign may decline on EVERY target (LOCKED)** | 77/77/77 | +0.1097 [+0.0626, +0.1612] | -0.0269 [-0.0637, +0.0146] | **-0.1729 [-0.3023, -0.0394]** |

The convention decides whether the adjudicator's interval covers zero: under (a) it
includes zero, under (b), (b'), (c) and (d) it lies entirely below it. It never supports a
positive attack effect under the adjudicator. The locked convention (d) is the one **least**
favourable to the attack in all three arms, which is the direction that makes a post-hoc
choice non-self-serving.

### Why the correction exists

| arm | attack_move min | n targets with attack_move < 0 | n with benign_max < 0 | no-op targets in the paired net | their as-is contribution (nats, total) |
|---|---|---|---|---|---|
| nli | +0.0000 | 0 | 10 | 8 | +4.414 |
| exact | -0.4159 | 4 | 6 | 8 | +1.085 |
| judge | -0.9404 | 15 | 11 | 8 | +1.355 |

**A qualification the pre-registration does not make, and that a referee will find.** The
statement "`attack_move` is bounded below by zero because the optimiser can decline" is
true **only in the NLI arm** (minimum exactly +0.0000 over all 80
targets). The optimiser searches in NLI space; the exact and judge arms are independent
re-scorings of the query it chose, and there `attack_move` is negative on
4 and 15 targets respectively
(minima -0.4159 and -0.9404). The
action-set argument for convention (d) still holds in every arm — the attack's action set
contains the no-op, which scores exactly 0 in *all* arms because `best_query == question`
makes `before == after`, and the benign arm's action set does not — but (d) gives the benign
arm a *per-arm* decline decision while the attack's decline decision is taken on NLI alone.
In the exact and judge arms (d) is therefore mildly generous to the null, which is the
conservative direction for an attack claim and the anti-conservative direction for the
negative judge result reported here. Convention (c), which touches neither arm's action
set, gives the judge net -0.1522 [-0.3004, -0.0047]; the negative sign
does not depend on (d).

## 4. The denominators, which are four different numbers

| quantity | n | what it is |
|---|---|---|
| targets attacked in the cell | 80 | the campaign; `n >= 80` pre-registration met **here only** |
| exceedance test | 77 | targets with `m_j > 0`; the 3 empty benign arms contribute nothing and are silently dropped by `exceedance_counts_randomized` |
| paired net, (a)/(b)/(b')/(d) | 77 | targets with a non-empty benign arm |
| paired net, (c) | 69 | the above minus the 8 no-op targets that have a benign arm |
| benign arm at the full declared budget K=50 | 71 | the rest are short |

**Empty benign arm — 3 targets: `qb_565`, `qz_3393`, `qb_2689`.** The feasibility gate rejected all
`K*5 = 250` attempts (`scripts/null_control.py:174`), so these targets have no
benign maximum and no paired net. All three are also no-op targets — the optimiser found
no feasible paraphrase either (`n_feasible_at_best == 0`; verified: True) — which is joint evidence
that no feasible paraphrase of those questions exists, not that the sampler was unlucky.
They are excluded, not absorbed.

**Partial benign arm — 6 targets** with 1 <= m < 50: `qz_1745` (m=26), `qb_2833` (m=38), `qb_6105` (m=1), `qb_2922` (m=35), `qz_4576` (m=27), `dpql_250` (m=27).
Because the attempt cap is `K*5`, a shortfall means a gate pass rate below 20% and is
informative about the question rather than random. Estimated inflation of the paired net,
obtained by taking each of the 71 full arms and computing the exact expected maximum of a
uniformly random size-m subset:

| arm | bias, as-is (a) | bias, locked (d) | median distinct values in a 50-draw arm | share of draws at the arm's max |
|---|---|---|---|---|
| nli | +0.0064 | +0.0010 | 5 | 29.8% |
| exact | +0.0036 | +0.0036 | 3 | 45.1% |
| judge | +0.0095 | +0.0031 | 3 | 28.6% |

The bias is small because the benign score distributions are lumpy: with a median of only
5 distinct values among 50 NLI draws and 30% of draws already at the maximum, a maximum over 26 draws
almost always equals the maximum over 50. Under the locked convention (d) the bias is
smaller still, because the one severely short arm (`qb_6105`, m=1) has a negative benign
maximum that the `max(0, .)` truncation removes. This is a **disclosure, not a correction**:
the as-is bias is 9% of convention (a)'s NLI
CI half-width, and the locked-convention bias is 2%
of (d)'s. For the exceedance test a short arm costs power, not calibration, because the
null carries each target's own `m_j`.

**The pre-registered `n >= 80` is met by the campaign and by nothing else here.** Every
benign-referenced statistic runs on 77 or fewer targets. This belongs in Methods, not only
in Limitations.

**The `embed` arm does not exist in this campaign.** The run was launched with
`embedding_model=""`, so `attack_move.embed` is null and `benign.embed` is length 0 on all
80 records (verified: True). It must never be reported as a null result — there
is no measurement, not a measurement of no effect.

The no-op set is identified three independent ways that agree exactly on the same 11 targets: `best_query == question`, `improved == False`, and
`n_feasible_at_best == 0` (all three agree).

## 5. What `results/diag_defb.json` contains

**Nothing the checkpoint does not.** It is the `--dump_diag` dump of the identical
in-memory records: `scripts/null_control.py:429-430` appends the same `rec` object to a
list that `:544` serialises with `json.dumps(..., indent=2)`. Verified by canonicalising
both to sorted-key JSON:

- record count: 80 vs 80; same question_ids in the same order: True
- every record byte-identical after canonicalisation: **True**
- key sets identical: True — `attack, attack_move, baseline, benign, cfg, detector, question_id, seed`

The 350 KB versus the checkpoint's 237 KB is entirely `indent=2` whitespace. So it holds
no extra measurement, and the analysis above would be unchanged if it were deleted. What
*both* files carry, per target, is: the `baseline` entropy in each arm; the `attack_move`;
the full `benign` list of up to 50 move values per arm; and a `seed` band of 3
re-scorings of the *same* question under seeds 1-3, which is the pure N=10 estimator-noise
floor and is not otherwise reported. Its mean move, bootstrapped over targets rather than
over the 240 individual draws because the three draws within a target
are not independent, is
-0.0145 [-0.0973, +0.0701] (nli), +0.0259 [-0.0202, +0.0744] (exact), -0.0744 [-0.1511, +0.0040] (judge).
Every one of those intervals covers zero, so pure N=10 estimator noise has no direction
and the benign band and the attack are both read against a floor of 0. That is the
reassurance the seed band exists to provide, and it holds.

## 6. What does not reproduce in the pre-registration

The pre-registration's disclosure table (its section 0) was computed on the 68 targets then
visible. Recomputing the same four conventions on the first 68 checkpoint rows — the same
rows, in the same order, since the checkpoint is appended in completion order — gives:

| convention | n | NLI: recomputed / pre-reg | exact: recomputed / pre-reg | judge: recomputed / pre-reg | largest discrepancy |
|---|---|---|---|---|---|
| (a) | 65 | +0.1926 / +0.1926 | +0.0176 / +0.0176 | -0.1515 / -0.1515 | reproduces |
| (b) | 65 | +0.1256 / +0.1200 | -0.0076 / -0.0072 | -0.1773 / -0.1675 | **0.0098** |
| (b') audit variant | 65 | +0.1256 / n/a | -0.0076 / n/a | -0.1868 / n/a | not in the pre-reg |
| (c) | 58 | +0.1407 / +0.1432 | -0.0085 / -0.0086 | -0.1987 / -0.1998 | **0.0025** |
| (d) | 65 | +0.1061 / +0.1061 | -0.0169 / -0.0169 | -0.2042 / -0.2042 | reproduces |

**Rows (a) and (d) reproduce to four decimals. Rows (b) and (c) do not.** The NLI and judge
discrepancies (up to 0.0098 nats) are far too large to be rounding; one exact-arm cell
differs only in the last printed digit and could be. The recomputed (b') and (c) figures
match `results/benign_arm_audit.md` §6 exactly (+0.1256 / -0.0076 / -0.1868 and +0.1407 /
-0.0085 / -0.1987), so the audit is right and the pre-registration mis-transcribed it. Two
further slips travel with the same transcription:

- "Across the **11** no-op targets the contribution is +4.355 nats" — +4.355 is the NLI-arm
  total over the **7** no-op targets that had a benign arm at 68/80
  (recomputed: +4.3550). There were 10 no-op targets at 68/80,
  not 11; there are 11 at 80/80, of which 8
  have a benign arm, contributing +4.414 nats.
- "(c) ... drops n from 65 to **57**" — it dropped 65 to
  **58** at 68/80 (7 exclusions, not 8), and
  drops 77 to 69 here.

None of this disturbs the locked decision: (a) and (d) are the rows the choice was argued
from, they are correct, and the qualitative claim that the convention decides whether the
judge interval covers zero survives recomputation. The corrected sensitivity table is
section 3 above. The pre-registration's non-negotiable disclosure stands and is repeated
here: **it was written with 68 of 80 targets visible and after their effect on every
candidate convention had been computed. It was not blind.**

## 7. Verdict

**Does the attack beat a budget-matched benign search? No — and under the independent
adjudicator it loses to one.** On the pre-committed statistic the exceedance test does not
reject the null of no optimiser signal in any arm, at any of 101 tie-break realisations, with the observed exceedance count *above* its null
expectation everywhere; the attack's 181-candidate beam is worth about
122 random feasible paraphrases in the detector's own NLI
arm and about 5 under the judge, in both cases less than
the budget it spent. On the supplementary paired net under the pre-registered convention
(d), the net is +0.1097 [+0.0626, +0.1612] nats under the NLI clusterer the attack was optimised
against, -0.0269 [-0.0637, +0.0146] under exact match, and **-0.1729 [-0.3023, -0.0394] under the pre-registered
independent LLM judge — negative, with the whole 95% interval below zero**. Read with the
sign in front of it: the optimised attack raises semantic entropy by about
0.17 nats *less* per target than simply taking the best of 50
random feasible paraphrases, once the benign arm is priced at the same budget and granted
the same freedom to decline. The positive NLI
figure is the confounded arm — the attack maximised that clusterer's own score, so it is an
upper bound on the effect and not an independent measurement of it — and even there the
effect does not survive the claim statistic. The paper's position that there is no attack
effect is supported. A referee should read the negative judge net not as a defect in the
measurement but as its result: with the search budget priced into the null, the
adversarial optimiser under-performs random paraphrasing on the adjudicator that was
chosen in advance to judge it.

## 8. What was re-derived here, and what was taken on trust

Re-derived from the artefacts by this script, not inherited from any prior document:
checkpoint integrity and cardinality; the identity of `diag_defb.json` and the checkpoint;
the empty and partial benign arms and their sizes; the no-op set under three definitions;
`attack_move`'s per-arm minimum; the count of negative benign maxima; every exceedance
p-value, its counts and its tie audit; every paired net and bootstrap interval under every
convention at both 68 and 80 targets; the short-arm bias and the lumpiness statistics; and
the four rows of the pre-registration's own table.

Taken on trust, and each a place a referee could still dig:

1. **That the recorded numbers are the numbers the GPU produced.** Nothing here re-runs the
   detector; the entropies in the checkpoint are accepted as written. No GPU work was done.
2. **The live-vs-snapshot check is an md5 comparison of the false-alarm outcomes file**, run
   once, plus its unchanged mtime. The `hide` cell was not checked and is not used.
3. **`n_feasible_at_best` is the optimiser's own bookkeeping.** The exceedance test's tie
   credit depends on it and it is not independently verifiable from these artefacts; the
   `b`-scaling row is the substitute, and it holds.
4. **The judge clusterer's validity** (reported elsewhere at 0.93 symmetric agreement, with
   positive-recognition ~0.7, so it slightly over-splits) is assumed, not re-measured. An
   over-splitting judge adds noise to both arms, but the negative net is a difference
   between arms measured on the same generations, so it is not obviously an artefact of it.
5. **The exchangeability premise of the exceedance test** is assumed for the non-no-op
   targets. `scripts/null_objective_ablation.py` is the measurement that bears on it and
   was not re-run here.

---

Regenerate: `.venv/Scripts/python.exe scripts/null_control_defb_report.py` — deterministic,
byte-identical on re-run.
