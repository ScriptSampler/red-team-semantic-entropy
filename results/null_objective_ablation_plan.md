# Null-objective beam ablation — the exceedance test's validity gate

**Written 2026-08-13, BEFORE any ablation data exists.** Everything below that could be
argued either way after seeing a result is fixed here first: the band, its arithmetic, the
contamination correction, and what the paper must say if the gate fails. Entry 23a's lesson
applies — *a bar without a population and a decision quantity is not a pre-commitment*.

Status: **not run.** `results/null_objective_ablation.md` does not exist; the only artifact
is `results/null_objective_ablation_ckpt_def.jsonl`, one target, written 2026-08-03 under a
now-superseded record schema. Table 1 in `paper/sections/experiments.tex` has a seed-noise
band and a benign band and **no null-objective arm**, while the same section asserts
exchangeability outright and `se.stats.exceedance_test`'s docstring says *"Read that ablation
before trusting this test."* It currently points at a script that has never produced a result.

---

## 1. What the gate tests

The claim statistic is the randomised-tie exceedance test. Its H0 is that a target's
`A ≈ 181` attack candidates and its `m = 50` benign draws are **exchangeable draws from one
distribution F_j**. That is the whole basis for pricing the attacker's search budget
analytically instead of by brute force, and it is not obviously true:

`optimizer.optimize` seeds round 1 with three copies of the ORIGINAL question, so round-1
children are single-hop rewrites — the same generating process as every benign draw in
`null_control._benign_moves_arms`. From round 2 the parents are previously-accepted
candidates, so later candidates are second-, third-, …-order rewrites. Two opposing failure
modes, net sign empirical (critique_log 23):

| mode | mechanism | direction |
|---|---|---|
| multi-hop drift | late candidates more dispersed for reasons unrelated to optimisation | **ANTI-conservative** |
| beam clustering | the beam revisits a small region, fewer effective draws | conservative |

The gate removes the optimisation signal while holding the search procedure fixed, so
whatever remains is procedure, not signal.

---

## 2. What `scripts/null_objective_ablation.py` actually does

**The design is right.** It calls `optimizer.optimize` — the *same function the attack calls*
— with the same `max_iteration=20`, `candidate_size_M=3`, `top_N=3`, the same
`proposer.propose`, the same `feasibility.check` against the ORIGINAL, and replaces only the
objective with `hash01`, an md5 of the candidate string mapped to [0,1). The beam therefore
concentrates exactly as it would on a fixed noisy landscape, with zero detector signal. That
is what entry 23 designates as the validity gate, and the script implements it.

**But as committed on 2026-08-12 it did not compute the gate's quantity, and three defects
would have biased it. All three are fixed in this session; none required GPU.**

1. **It computed the wrong statistic.** It reported the paired nats difference
   `mean(null_beam_max − random_max)` with a ±0.05-nat verdict. Entry 23's pre-commitment is
   on the **mean exceedance count Kbar against m/(A+1)** — a rank quantity, on the scale the
   test actually uses. The nats comparison is the older B2 framing (entry 21) and is now kept
   as a labelled *secondary diagnostic*. `gate_summary()` computes the gate.
2. **It deduplicated the beam before counting ties.** `beam_cands = dict.fromkeys(seen)`
   collapsed 181 objective calls to 73 distinct strings on the one target on disk. But the
   deployed null counts `A = 181` **calls**, and `optimizer` records `n_feasible_at_best` per
   gated candidate, duplicates included. A deduplicated `b` against a non-deduplicated `A`
   inflates the tie credit `1/(b+1)`, enlarges K, and makes the gate look conservative when
   it is not. Fixed: distinct strings are gated and scored once (the expensive part), then
   expanded back over the calls.
3. **The two arms were not budget-matched.** The diffuse arm drew `len(beam_cands)` raw
   candidates — 73, not 181 — and then deduplicated *again* before the feasibility gate,
   while the beam arm had already had 181 raw draws. On the one target on disk that produced
   a max over 22 beam candidates against a max over 6 diffuse ones, a ~4x asymmetry that
   mechanically favours the beam. Fixed: the benign arm is now generated exactly as
   `null_control._benign_moves_arms` generates it (single-hop, gated, duplicates kept, m
   feasible or 5m tries), and `--benign_from results/diag_defb.json` reads the null control's
   own lists instead, which is preferred — the gate is then evaluated against the very arm
   the claim statistic will consume.

Records written before the fix are refused on resume (`SCHEMA = 2`) with a loud message,
rather than silently mixing two definitions of `b`. The existing `_def` checkpoint therefore
does **not** count toward the run.

**Scope limit worth stating in the paper.** A hash objective is a *strict*-H0 ablation: it
removes even the weak inheritance a real no-signal objective would have (entropy is a genuine
per-question property, so a real-objective beam would still concentrate on
genuinely-high-entropy regions of paraphrase space). That is the correct null for the
exchangeability question — but it means the gate bounds procedure-induced drift, not "the
attack is doing nothing."

---

## 3. The exposure, measured with NO GPU

`scripts/round_drift_analysis.py`, run on the complete `_defb` FA cell (n=80,
`~/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl`). It uses only
`trajectory_best_obj`, `feasible_objs` and `n_feasible_at_best`.

**Identification.** `feasible_objs` is appended in iteration order but carries no round
labels, and after the trajectory plateaus every entry equals the running max, so exact
per-round counts are *not* identified. What is identified is a bound, and it is sharp: each
iteration proposes exactly `top_N × candidate_size_M = 9` children, and no tie member can
predate the round `t0` that first achieved the max (a feasible candidate at the final max
would have raised the trajectory). Hence `#ties from rounds ≥ r ≥ max(0, b − 9(r − t0))`.
`min_entries_from_round` computes the exact minimum by DP over every segmentation consistent
with the trajectory, which is never looser. The DP finds a consistent segmentation for all 69
targets that have feasible candidates — i.e. the record and the optimiser's documented
behaviour agree — and is strictly tighter than the counting bound on 15 of them.

| quantity | value |
|---|---|
| targets | 80 (11 with no feasible candidate; 69 with ties) |
| max first set in **round 1** (single-hop) | **28.7 %** |
| max first set in **round ≥ 2** (multi-hop) | **46.2 %** (median first-max round 1; tail to round 18) |
| never improved on the clean score | 25.0 % |
| mean trajectory rises | 1.35 of 20 rounds |
| mean tie multiplicity `b` | 37.7 (median 27, max 131) |
| targets with `b > 9`, so ties are *forced* multi-hop | 48 / 69 = **69.6 %** |
| tie mass provably from round ≥ 2 | **2390 / 2604 = 91.8 %** (lower bound) |
| …on the 42 saturated targets, where ties bite | 1997 / 2145 = **93.1 %** |
| feasible-candidate mass provably from round ≥ 2 | 2599 / 3058 = 85.0 % |
| targets with *no* multi-hop exposure at all (max single-hop AND b ≤ 9) | **5 / 80** |
| mean tie credit `1/(b+1)` | 0.0926, vs 0.1420 if b were capped at one round's proposals (**1.5x**; **2.1x** on saturated targets) |

**Reading.** The exchangeability assumption is not a technicality here. It is load-bearing
for at least 92 % of the tie multiplicity — the quantity that divides the evidence — and for
the maximum itself on nearly half the targets. Five of eighty targets are clean of the
concern.

**What this cannot do, and why the GPU run is still required.** A round effect in the
*values* would be uninterpretable: it is exactly as consistent with the optimiser working
(H1, the thing we hope for) as with drift (H0 violated). Only switching the objective off
separates them. Two further blocks: `feasible_objs` is a running-record subset (every entry
is ≥ its round's entry threshold, and 0 of 3058 fall below the clean score), so raw
round-to-round value comparisons are confounded by a rising truncation threshold; and
candidate *strings* are never persisted, so textual drift and per-round gate pass-rates are
not recoverable from any completed run.

---

## 4. A second exchangeability violation, found while costing this — and it contaminates the band

`proposer.propose` decodes **greedily**. Diversity comes only from randomising the
instruction (10 verbs × 8 styles × 5 templates), so for a fixed parent the reachable
candidate set is small and repeats. The two arms then duplicate at very different rates,
because they have different numbers of parents: the attack draws from up to 3 fresh parents
per round over 20 rounds, the benign arm from the *same* original question every time. The
one ablation target on disk: **73 distinct strings from 181 attack calls; 6 feasible benign
survivors**.

`scripts/duplication_level_sim.py` measures this rather than arguing it (critique_log 26's
standing rule). H0 true by construction — one shared F per target, values iid per *distinct*
candidate, replicated to each arm's call count. n=80, A=181, m=50, 250–300 trials:

| distinct attack strings | distinct benign | H0 level @0.05 | Kbar / expected |
|---|---|---|---|
| 181 (none) | 50 (none) | 0.023 | 1.00 |
| 181 | 6 | 0.084 | 1.02 |
| 145 | 6 | 0.064 | 1.07 |
| 109 | 6 | 0.048 | 1.19 |
| **73 (measured)** | **6 (measured)** | **0.028** | **1.39** |
| 55 | 6 | 0.016 | 1.88 |
| **52** | 6 | — | **≈ 2.0 — band edge** |
| 40 | 6 | 0.008 | 2.57 |
| 30 | 6 | 0.004 | 3.92 |

Three consequences, all pre-specified here:

1. **The deployed test's Type-I level survives.** Attack-arm duplication is *conservative*
   (level falls as distinctness falls); only benign-arm collapse alone is mildly
   anti-conservative (0.084). At the measured rates the net is 0.028. No change to the claim
   statistic is indicated.
2. **Do not "fix" this by passing A_eff instead of 181.** Feeding A = 73 re-centres the ratio
   to 1.01 but drives the H0 level to **0.136**. The conservatism at A = 181 is protective.
3. **The gate ratio is contaminated, and in the direction that HIDES drift.** A true null
   with zero drift already reads 1.39 at the measured rates. A genuine anti-conservative
   drift that would put the true ratio at 0.7 would be observed at 0.7 × 1.39 ≈ 0.97 —
   dead centre of the band. **The raw ratio must not be read against 1.0.** The ablation
   records `n_beam_unique` / `n_diffuse_unique` for exactly this; the gate is read against a
   centre obtained by running `duplication_level_sim.py` at the run's own observed rates.
   If the beam yields fewer than ~52 distinct strings of 181, the band's upper edge is
   breached by duplication alone and FAIL-HIGH carries no information about drift.

---

## 5. The acceptance band, recomputed

Entry 23 pre-committed: *"the null-objective ablation's mean exceedance count Kbar falls
within [0.5x, 2.0x] of the theoretical m/(N+1)."*

**The wording is ambiguous and must be pinned before use.** `N` in `exceedance_test`'s
docstring is `n_attack_candidates`; `N` everywhere else in this project is the per-question
sample budget (10). Read the second way the target is 50/11 = 4.545 — **16.5x different**.
The paper already fixed the collision by writing `A` (*"A ≈ 181 … distinct from the
per-question sample budget N = 10"*). **The band is on m/(A+1).** This is entry 23a's lesson
recurring in the same entry it was written in.

Deployed design: `m = 50` (null control `--K 50`, pre-committed entry 26a), `A = 181`
(= 1 + 20·3·3; `n_objective_calls` is 181 on all 80 `_defb` targets), `n = 80`.

```
E[K_j]  = m/(A+1)      = 50/182            = 0.274725
band    = [0.5x, 2.0x]                     = [0.137363, 0.549451]
E[S]    = n·m/(A+1)    = 80·0.274725       = 21.98      band on S = [10.99, 43.96]
Var[K_j]= m·A·(A+m+1)/((A+1)²(A+2))        = 0.3464     sd(S) = sqrt(80·0.3464) = 5.26
```

**What changed since entry 23, and whether the band still means what it meant:**

- **m: unchanged** at 50 (entry 23 paired m=50 with N=20; entry 26a re-committed m=50 at
  N=10; the running chain uses `--K 50`). **A: unchanged** at 181.
- **Tie rule conservative → randomised: the centre is unchanged in form, and only now
  correct.** Under exchangeability with randomised tie-breaking each of the A+1 relevant
  draws is equally likely to rank top, so E[K_j] = m/(A+1) **exactly, atoms included**. Under
  the conservative rule entry 23 assumed, every tied benign draw counts, so at the measured
  52.5 % saturation rate the true E[K_j] would have sat far above m/(A+1) and the band was
  mis-centred from the day it was written. The tie-rule change repaired the band; it did not
  invalidate it.
- **TIGHTENING (new, pre-specified): the ratio is taken against `Σ_j m_j/(A+1)`, not against
  `n·m/(A+1)`.** `_benign_moves_arms` gives up after `5m` tries, so a low-feasibility target
  returns fewer than 50 draws — and the one ablation target on disk yielded 6 feasible from
  73, so this is a live risk, not hypothetical. Without the tightening a short benign arm
  fails the band for a reason that has nothing to do with exchangeability. Implemented in
  `gate_summary()`; pinned by `test_gate_centre_is_m_over_A_plus_one_and_uses_the_ACHIEVED_m`.
- **TIGHTENING (new, pre-specified): the ratio is read against the duplication-adjusted
  centre of §4, not against 1.0.**

**The gate's own resolving power, stated before the data.** At n=80 the 0.5x edge sits
**2.09 sd** below E[S] and the 2.0x edge 4.18 sd above. The band therefore detects a
*halving* of the exceedance rate but **will not resolve a 20–30 % anti-conservative bias**
(a true ratio of 0.8 is 0.84 sd; 0.7 is 1.25 sd). Reaching 3 sd on the lower edge needs
n ≈ 165, which the n=80 FA cell cannot supply. **A PASS means "no gross violation at n=80",
and must be reported in those words** — entry 23 already flagged that 10 targets were
underpowered (E[S] ≈ 1.65); 80 targets give E[S] = 22.0, which is adequate for the band edge
and no more.

---

## 6. Cost

**CORRECTED 2026-08-31, and the correction runs against this plan's own interest.** This
section used to derive `s_SE ≈ 2.8 s` per N=10 semantic-entropy evaluation by dividing a
per-target wall clock by 181 objective calls and splitting the quotient pro-rata by
generated-token count. That constant is refuted. It is wrong by 4.6x and it was wrong in the
cheap direction, so the ablation is **more** expensive than this section claimed, not less.
§6.3 records what broke and why the wall clock it was derived from is nevertheless still
correct. `results/operational_number_audit.md` §2.1 and §2.6 refuted the same constant
independently and arrived at a different total; §6.5 reconciles the two and says which is
right.

### 6.1 The constants, each measured directly

| constant | value | provenance |
|---|---|---|
| `s_SE` — one N=10 SE evaluation | **13.0 s** | MEASURED, 11.2 s generation + 1.8 s NLI. MEASURED generation, from `results/run_all.log`: `wk4_sample.py` sustained 12.51–12.80 s/Q over 1907 questions doing one greedy plus one N=10 batch of 48 new tokens, less the 1.49 s greedy mean of `results/pipeline_check.md`. MEASURED NLI, from `results/run_all_status.txt`: `wk4_cluster.py` clustered 2000 questions in 3509 s = 1.75 s/Q (90 forward passes at N=10), cross-checked at 1.84 s/Q in `results/wk3_fri_entropy.md`. |
| `s_prop` — one `proposer.propose` | **1.5 s** [1.0–2.0] | One greedy `M.generate_one`, batch of 1, `max_new_tokens=64`, stopping at EOS (`src/se/attacks/proposer.py`). Anchored on the 1.49 s greedy mean (n=10) in `pipeline_check.md`. **The least well-measured constant here, and at 180 calls per target the second-largest line — see §6.4 and §6.5.** |
| `s_gate` — one `feasibility.check` | **0.05 s** | `nli.bidirectional_equivalent` is ONE DeBERTa batch of 2 pairs, not 2 sequential passes. The N=10 clusterer does 90 passes in 1.8 s = 0.02 s per pass; the balance is fixed per-call overhead. Immaterial at any value below 0.15 s. |

`s_SE = 13.0 s` is if anything optimistic: `pipeline_check.md` timed the N=10 batch *alone* at
14.27 s per question over 100 questions in Week 2 [MEASURED]. 13.0 s is the Week-4 figure,
and it is the same constant `results/n_scaling_plan.md` §2 uses, so the two files now agree.

### 6.2 The ablation, per target

**The objective being free saves less than it looks like it should**, because the ablation
pays for SE evaluations on a *different* set than the attack does. The attack scores every
distinct candidate (the objective IS the SE eval); the ablation scores only the distinct
candidates that pass the gate (`scripts/null_objective_ablation.py` gates `beam_uniq` first,
then `score()` runs behind `ent_cache`). The saving is the distinct-but-infeasible strings —
and nothing more.

| component | count | unit | subtotal |
|---|---|---|---|
| baseline SE eval | 1 | 13.0 s | 13 s |
| beam proposer calls | 180 | 1.5 s | **270 s** |
| in-optimiser gates (running-max records under a continuous hash; above H₁₈₁ ≈ 5.8, because the threshold rises only on gate-passing candidates) | ~6–20 | 0.05 s | under 1 s |
| gate over DISTINCT beam strings | 73–145 | 0.05 s | 4–7 s |
| SE evals over DISTINCT FEASIBLE strings | 22–58 | 13.0 s | **286–754 s** |
| **attack arm, per target** | | | **573–1045 s (9.6–17.4 min)** |
| benign arm if re-drawn (up to 250 proposals, up to 50 SE evals) | | | +470–880 s |

The `73–145` and `22–58` brackets are unchanged and are **not** symmetric evidence: 73
distinct strings and 22 distinct-feasible are *measured*, on target `dpql_1059` in
`results/null_objective_ablation_ckpt_def.jsonl`; 145 and 58 are a hypothetical upper bracket.

**A floor that needs neither bracket.** 180 proposer calls plus one baseline eval is
**283 s/target = 6.3 GPU-h at n=80** [MODELLED from `s_prop` and `s_SE` in §6.1, both measured
there] even if every candidate were a duplicate and none were feasible. That floor alone
exceeds the whole 3.2–5.7 GPU-h range this section used to quote [MODELLED from the refuted
pro-rata token split], which is superseded.

| configuration | n=80 |
|---|---|
| attack arm only, `--benign_from results/diag_defb.json` (**recommended**) | **12.7–23.2 GPU-h; plan on ≈ 18** [MODELLED from §6.1's measured units] |
| with the benign arm re-drawn | 23–43 GPU-h [MODELLED from the same units] |
| *(reference)* the real attack, same n | 13.1 GPU-h [MEASURED from the `_defb` re-run's wall clock] |

Plan on ≈18 GPU-h [MODELLED from §6.1's measured units], not on the 12.7 low end: the low
end assumes the *measured* target's distinct rate holds everywhere, and that target is n=1.

### 6.3 What broke, and why the wall clock it was derived from is still right

The old derivation made two errors that compound.

**E1 — 181 objective calls are not 181 SE evaluations.** `objectives.make_objective` builds a
per-target `cache: dict[str, float]` and `entropy()` consults it before evaluating
(`src/se/attacks/objectives.py`), so an objective call on a repeated candidate string is a
dict lookup. The proposer decodes greedily (§4), so repeats are the common case, not the
exception. Dividing a target's wall clock by 181 therefore yields an amortised **per-call**
rate, which is the per-eval rate divided by the duplication factor.

**E2 — a per-call average cannot be split by generated-token count.** That split assumes every
component runs on every call. The proposer does (180 of 181); the SE eval runs only on
distinct strings; the gate only on the calls that clear `>= best_obj`.

Corrected, the identity for the deployed hide cell is

```
T  =  U·s_SE  +  180·s_prop  +  C·s_gate  +  r·(s_SE + s_greedy)
```

with `U` = distinct candidate strings, `C = 53.9` (mean `n_feasibility_checks` over the 80
`_defb` hide targets), `r = 59/80 = 0.74` (the fraction firing the B2 re-check in
`src/se/attacks/harness.py`, one extra SE eval plus a greedy) and `s_greedy = 1.5 s`. Both `C`
and `r` are re-derived here from the COMPLETED 80-target hide cell rather than the 52-record
snapshot this file was first written against: `C = 53.91`, `r = 59/80` exactly. At
T = 568–607 s/target [MEASURED from the hide cell's own wall clock] this gives **U ≈ 22–25
distinct strings of 181**, a 12–14 % distinct rate over that target's 181 objective calls.
Even setting `s_prop = 0`, which is impossible, gives a hard bound of **U ≤ 46**.

So the total is fine. Both MEASURED: 568–607 s/target on the hide cell and the ~13 GPU-h over
80 targets of the `_defb` FA re-run, and the hide cell's own remaining-time estimate stands
with them. Only the **decomposition** was wrong. That is exactly the part the ablation's cost
table is built from, because the ablation changes the mix: it pays the proposer in full and
the objective not at all.

### 6.4 What the remaining uncertainty actually is

The dominant term is no longer `s_SE`. It is the **distinct-feasible-string count `F`**, worth
286–754 s per target [MODELLED from §6.1], with `180·s_prop = 270 s` second. Both are measured by the run itself
from target 1 (`n_beam_unique`, `n_beam_feasible_unique`), so the first checkpoint line settles
the budget — check it before committing the remaining 79 targets.

Two notes on the benign row: the ablation's `ent_cache` is shared between the arms and the
baseline, so a benign candidate that also appeared in the beam is scored once and the
+470–880 s row is an upper bound; and the row spans a wide range because the measured yield
was poor (6 feasible from 73 tries on `dpql_1059`), so the arm may hit the 5m-try cap having
bought few evals.

### 6.5 Reconciliation with `operational_number_audit.md` §2.6 — read this before quoting either

Two documents in this repo now correct the same dead constant and land on different totals,
and the difference is not a disagreement about the measurement. It is a disagreement about how
much of the old derivation to throw away.

| | audit §2.6 | this section |
|---|---|---|
| `s_SE` | 12.87 s [MEASURED from the deployed null control's clustering] | 13.0 s [MEASURED per §6.1] |
| `s_prop` | 0.37 s, carried over unchanged | 1.5 s, re-anchored on a measured greedy |
| `s_gate` | 0.15 s, carried over unchanged | 0.05 s, re-derived from the batch shape |
| attack arm, per target | 375–849 s | 573–1045 s |
| **n=80, attack arm only** | **8.3–18.9 GPU-h** (central 13.5) | **12.7–23.2 GPU-h** (plan ≈ 18) — both MODELLED from the unit rows above |

The two `s_SE` values agree to 1 %. **The entire gap is the proposer term**: 180 calls times
(1.5 − 0.37) s is 203 s per target, which is 4.5 GPU-h at n=80 [MODELLED from §6.1], and
8.3 + 4.5 = 12.8 against 23.2 at the top. Nothing else moves.

**This section's figure is the one to use, and the reason is provenance, not preference.** The
audit says explicitly that it substituted the measured `s_SE` while "leaving every other line
of that table untouched". But `s_proposer = 0.37 s` and `s_NLI = 0.15 s` are not independent
measurements that happened to survive: they are the *other two outputs of the very pro-rata
token split that produced the refuted 2.8 s*. Rejecting the split for one of its three outputs
and keeping the other two is not available. §6.1 re-anchors both on things that were measured
directly — a greedy `generate_one` at 1.49 s and a 2-pair DeBERTa batch — and the proposer
term is the larger of the two by two orders of magnitude.

**Consequence, flagged and not edited here.** `results/schedule_2026_08_26.md` item 7 and Cut 5
carry the audit's figure and not this one. If this section is right they under-price the gate
by exactly the proposer term isolated above, and Cut 5 saves correspondingly more. Both files
are owned elsewhere; this is a pointer, not a change.

### 6.6 Two consequences outside this section — flagged, not fixed here

1. **`scripts/null_objective_ablation.py`'s module docstring** carried the superseded figure
   [superseded, MODELLED from the refuted token split] *"~2.5-4.5 min/target (the objective
   is free, so this is ~4x cheaper per target than the real attack)"*. Both halves were wrong
   from the same root cause — 9.6–17.4 min, and
   comparable to the real attack rather than four times cheaper. Corrected in place on
   2026-08-31; recorded here because a fixed number that is only fixed in one file regresses.
2. **§4's duplication table may be read at the wrong row.** Its level and contamination figures
   are quoted at *"73 (measured) | 6 (measured)"*, using the hash-objective ablation target's
   distinct count as a stand-in for the **deployed attack's**. §6.3 bounds the deployed attack
   at `U ≤ 46` distinct strings of 181 and centres it at 22–25 — nearer §4's `30 | 6` row (H0
   level 0.004, ratio 3.92) than its `73 | 6` row (0.028, ratio 1.39). If that holds, the
   deployed test is *more* conservative than §4 states and the gate's duplication offset is
   larger. It does not change §4's directional conclusions (attack-arm duplication is
   conservative; do not pass `A_eff`), and it does not change the gate itself, which is read
   against the **null arm's** own measured rate. Left for the §4 owner, with the note that the
   ablation measures both rates directly and settles it.

### 6.7 Against the queue, as the queue stands now

The blocking runs this section was written against have finished. The `_defb` hide cell is
complete at 80/80 (`data/cache/attacks/wk9_defb_snap` plus the live cache), and the
confirmatory null control is complete at 80/80 (`results/null_control_report_defb.md`). The
gate is therefore no longer a ~6 % surcharge on a running queue — that framing is superseded
along with the constant that produced it. It is a standalone buy of roughly 18 GPU-h [MODELLED from §6.1] against
whatever calendar remains, which is between a half and a full day of device time.

**Ordering, if it is run at all.** It needs `results/diag_defb.json` for `--benign_from`, and
that file now exists, so the extra benign arm (a further 10–20 GPU-h [MODELLED from §6.1]) is
avoidable and should be avoided. A gate evaluated against a *different* benign arm than the
claim uses is worth much less, and at the corrected price the `--benign_from` route is not a
preference — it is most of the reason the gate is affordable at all. **But see §6.8: the
question is now whether to run it, not when.**

### 6.8 Is this gate still owed? — assessment added 2026-08-31

Recorded here because a line item of this size should not stay on a schedule by inertia. The
assessment is that **it is no longer owed as a validity gate**, on four grounds, and the fourth
is the one that decides it.

1. **The decision it was to gate has already been taken and disclosed.** The gate existed to
   decide whether the exceedance test could be primary. `paper/sections/experiments.tex` now
   discloses the omission as the fifth pre-registration deviation, in the paper's own words:
   the ablation was never run, the exact test was used as primary anyway, and no trigger
   licenses that. Running the ablation now cannot un-take the decision.
2. **Running it after the outcome is known is worse than the disclosure already shipped.** The
   confirmatory result is in and the paper reports a non-rejection in every arm. A
   pre-registered conditional gate evaluated after the outcome is exactly what the surrounding
   paragraph invites the reader to check for.
3. **The claim is a non-rejection, so the asymmetry cannot manufacture it.** The
   mis-specification the gate would price runs in an unknown direction; the anti-conservative
   branch pushes toward rejection, and the test did not reject. The paper states the bound it
   does have — the adjudicator's total stands above its null expectation at every budget in
   [41,181], at worst by a factor of 1.9.
4. **The gate is known to be insensitive to the violation that is actually present.** This is
   decisive. The arms duplicate at wildly different rates (73 distinct of 181 attack calls
   against 6 distinct benign), which contaminates the gate ratio *in the direction that hides
   drift*: a true null with zero drift already reads 1.39, so a genuine 0.7 ratio would be
   observed at about 0.97 — dead centre of the [0.5, 2.0] acceptance band. The gate as
   pre-registered would PASS a violated assumption. Buying an uninformative PASS at §6.2's price
   is not a defensible spend.

**What is lost by cutting it**, stated so the cut is not sold as free: the ablation is the only
instrument that would *measure* the net sign of the multi-hop asymmetry rather than bound it,
and the paper currently says the sign is unknown. A referee who demands a measurement rather
than a bound is not answered by this section. Per point 4, however, they would not be answered
by the gate as designed either — the duplication contamination would have to be corrected
first, which is a redesign and not a run.

**Recommendation: take Cut 5 in `results/schedule_2026_08_26.md` now, on the argument above,
rather than waiting for its 2026-09-15 date trigger.** The pre-committed fallback in §7 is
free and already satisfied: `trajectory_best_obj` is on disk for all 80 targets. Note that this
recommendation only became available at the corrected price. At the superseded price the §7
pre-commitment below reads as an argument *against* cutting, because when the gate is that
cheap "no time" really is the only objection available. At §6.2's price, for a PASS that cannot
fail, the objection is no longer time.

---

## 7. Pre-committed consequence of each outcome

*A validity gate whose failure has no pre-specified consequence is not a gate.* Written
before the run; the trigger is the measured ratio after the §4 and §5 adjustments.

### FAIL-LOW — adjusted ratio < 0.5
The null-objective beam beats the benign arm more than chance. The analytic null is
**anti-conservative** and the exceedance test **cannot be the primary statistic**.

- **Primary fallback: the PREFIX statistic**, already the pre-registered fallback (entry 22),
  already ruled assumption-light by the critic (entry 23): attack-max over the first m
  candidates vs benign-max over m, paired, budget-matched *by construction* — it needs no
  exchangeability assumption at all. **It costs zero new GPU:** `trajectory_best_obj[t]` is
  the best achieved using the first `1 + 9t` candidates, so the m≈50 prefix is `traj[5]`
  (46 candidates) or `traj[6]` (55), recorded on every `_defb` target. A gate failure
  therefore does not cost the paper a re-run — say so, it is the reason the fallback was
  pre-registered.
- **Companion:** an empirically-calibrated null built from this ablation's own K
  distribution (entry 23's second option), reported as such.
- **Paper changes (main text, not an appendix — B3 discipline):** Table 1's exceedance rows
  demote to *diagnostic*; the prefix statistic becomes the claim row. §"The claim statistic"
  states the gate result, the measured ratio, and logs this as **triggered deviation #5**,
  alongside #1 e5→judge, #2 individual→budget-matched, #3 budget-matched→exact
  beta-binomial, #4 FA→hide scope. The exchangeability sentence must be rewritten from an
  assertion to a *tested and rejected* assumption.

### FAIL-HIGH — adjusted ratio > 2.0
The null is conservative. Entry 23 allows the test "as-is with that noted", **but only after
§4**: at fewer than ~52 distinct beam strings the upper edge is breached by duplication
alone. So:
- If the *unadjusted* ratio is high and the *adjusted* ratio is inside the band → **PASS**,
  and the duplication offset is reported as the reason the raw number looked extreme.
- If the adjusted ratio is still > 2.0 → use the test as-is and state that the reported
  p-value is an **upper bound** and n_eff a **lower bound** on the effect.

### PASS — adjusted ratio in [0.5, 2.0]
Report it. A passed gate that is not in the paper is not a gate. Table 1 gains a
**null-objective row** (null-arm Kbar, ratio, and the duplication offset) and the caption
says the exchangeability assumption was tested, at what n, and with what resolving power —
in the §5 words: *no gross violation at n=80; a 20–30 % bias is not resolvable at this n*.

### NOT RUN before the arXiv date
Pre-committed now so it cannot be decided later: **the exceedance test must not be presented
as the primary statistic on an untested assumption.** Lead with the prefix statistic (free,
§7 FAIL-LOW), report the exceedance test as a labelled companion, and state the exposure from
§3 — 91.8 % of the tie multiplicity is provably multi-hop — as the reason the untested
assumption matters. The gate is **12.7–23.2 GPU-h** [MODELLED from the measured units in §6.1],
re-derived on 2026-08-31 from a mis-derived ~4 that is now superseded. The pre-commitment above
is unchanged and this is the sentence it turns on: at the old price "no time" was the only
objection available, so the pre-commitment was written to refuse it. At the corrected price the
objection is no longer time — it is §6.8, which finds the gate insensitive to the violation
actually present and recommends cutting it on that ground rather than on cost. **A cut taken on
§6.8's argument satisfies this pre-commitment; a cut taken because the queue got busy does
not.**

---

## 8. Run recipe and pre-flight checklist

```bash
# AFTER the null control has written results/diag_defb.json
./.venv-wsl/bin/python scripts/null_objective_ablation.py \
    --tag _defb --n_targets 80 --m 50 \
    --benign_from results/diag_defb.json --no_diffuse
```

- [ ] the chain is idle — this loads Llama + DeBERTa and will contend for the 16 GB device
- [ ] `results/diag_defb.json` exists and its benign arm is the NLI arm at `--K 50`
- [ ] `results/null_objective_ablation_ckpt_def.jsonl` is NOT reused (schema 1; refused
      automatically, but confirm the "IGNORING n pre-schema-2 record(s)" line appears if the
      `_def` tag is ever passed)
- [ ] resumable per target; killing it costs one target
- [ ] afterwards: feed the reported `n_beam_unique` / `n_diffuse_unique` to
      `scripts/duplication_level_sim.py` and read the ratio against **that** centre, not 1.0
- [ ] the run also settles, for free, the two things §3 could not: the distinct-string rate
      per arm, and (by re-running `round_drift_analysis.py` on the null arm) whether the
      multi-hop tie mass under a null objective matches the 91.8 % seen under the real one

**Producing code for every number in this file**
`scripts/round_drift_analysis.py` (§3) · `scripts/duplication_level_sim.py` (§4) ·
`se.stats.exceedance_test` / `exceedance_counts_randomized` (§5) ·
`scripts/null_objective_ablation.py::gate_summary` (§7) · `tests/test_round_drift.py` and
`tests/test_null_objective_ablation.py` (21 tests; full suite 337 passing, 2026-08-13).
