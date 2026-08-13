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

Measured anchors: the live hide cell is running at **568–607 s/target** (`/tmp/defb_chain.log`:
5/41 in 2842 s, 10/41 in 6070 s), consistent with the `_defb` FA re-run's ~13 GPU-h / 80 and
with `definitive_run_plan.md`'s ~875 s at the older settings. At 181 objective calls that is
**3.26 s per objective call**. Splitting it by generated tokens (SE eval = 10 × 48 = 480 new
tokens; proposer = 64; NLI gate = 2 short forward passes): **s_SE ≈ 2.8 s, s_proposer ≈ 0.37 s,
s_NLI ≈ 0.15 s**.

**The ablation's objective is free** — that is the whole saving. Per target:

| component | count | unit | subtotal |
|---|---|---|---|
| beam proposer calls | 181 | 0.37 s | 67 s |
| in-optimiser gates (records under a continuous hash ≈ H₁₈₁ ≈ 5.8) | ~6 | 0.15 s | 1 s |
| gate over DISTINCT beam strings | 73–145 | 0.15 s | 11–22 s |
| SE evals over DISTINCT feasible strings | 22–58 | 2.8 s | 62–163 s |
| baseline SE eval | 1 | 2.8 s | 3 s |
| **attack arm, per target** | | | **144–256 s (~2.5–4.3 min)** |
| benign arm if re-drawn (≤250 proposals, ≤50 SE evals) | | | +90–200 s |

| configuration | n=80 |
|---|---|
| attack arm only, `--benign_from results/diag_defb.json` (**recommended**) | **3.2–5.7 GPU-h, central ≈ 4** |
| with the benign arm re-drawn | 5–10 GPU-h |
| *(reference)* the real attack, same n | 13.1 GPU-h |
| *(reference)* the definitive null control | ~67 GPU-h |

The dominant uncertainty is the distinct-string rate, which the run measures for itself.

**Against the queue.** Hide cell: 52/80 done, **28 targets ≈ 4.7 GPU-h left**. Then the null
control, **~67 GPU-h**. Queue ≈ 72 GPU-h ≈ 3.0 days; the gate adds **≈ 6 %**. 33 days remain
to the 2026-09-15 target.

**Ordering: run it AFTER the null control, before Table 1 is filled.** It needs
`results/diag_defb.json` for `--benign_from`, and a gate evaluated against a *different*
benign arm than the claim uses is worth much less. Running it first would cost the extra
benign arm (+2–4.5 GPU-h) and buy nothing: a FAIL does not invalidate the null control's
data, because the pre-registered fallback (§7) consumes the same benign lists.

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
assumption matters. The gate is ~4 GPU-h against a 72-GPU-h queue and 33 days; "no time" will
not be a defensible reason.

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
