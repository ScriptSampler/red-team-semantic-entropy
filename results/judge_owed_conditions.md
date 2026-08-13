# Judge conditions (ii) and (iii): what they require, what is on disk, what needs the GPU

Written 2026-08-13. The owed list is `results/judge_validation.md` line 11. Condition (i) is
closed (deployed symmetric config, hard-neg 0.930 [0.900, 0.957], n=300) and (iv) is
discharged in the paper (`methods.tex` reports the NLI/exact bracket alongside). **(ii) and
(iii) are open, and (iii) has never been mentioned in the paper at all.**

Every number below is produced by `scripts/judge_owed_conditions.py` (CPU only, stdlib only,
read-only over the caches). Regenerate with:

```
./.venv-wsl/bin/python scripts/judge_owed_conditions.py        # from WSL; the cache is inside it
```

Nothing here launches GPU work. Nothing here has been run on a GPU.

---

## 0. The answer in one table

| | what it needs | on disk now? | GPU | human |
|---|---|---|---|---|
| **(iii) under the judge** — the condition that matters | attack-side and benign-side cluster counts **under the judge** | **no** — the judge has never been run on the campaign, and the n=6 pass's per-target output was never checkpointed | **3.1 GPU-h** standalone, or **0** if the queued null control is instrumented first | none |
| **(iii)-preliminary under NLI** | paired cluster counts under the detector's own clusterer | **yes, exactly** — recovered by lattice inversion, n=80 paired, 0 mismatches in 2000 validation records | 0 | none |
| **(ii) machine half** | judge accuracy on messy real sampled pairs, with labels | **yes** — 90,000 real sampled pairs (mean 19.6 words) with an oracle-derived label on 74.5% of them | same 3.1 GPU-h run | none |
| **(ii) human half** | a bound on the oracle label's own error rate | protocol machinery exists (`equivalence_audit_protocol.md`), retargeting needed | 0 | ~3–4 h annotation |

**Headline:** (iii) is **not** answerable from cache in the form that decides the re-scoping
argument. A rigorous *preliminary* is answerable from cache and is reported in §3. The full
check costs **3.1 GPU-h [2.3–4.2]** standalone, or **zero** if the null control is
instrumented before it launches. (ii) is far closer to closed than the paper implies: the
messy real sampled pairs it asks for are already on disk, and 74.5% of them carry a free
label.

---

## 1. Why (iii) decides the sign of the whole re-scoping argument

The judge failed its pre-registered positive-recognition gate (0.650 against a required
0.8). It was re-scoped to false-alarm-only adjudication on this argument, which
`methods.tex` states as fact:

> Over-splitting inflates baseline entropy, which makes the judge *conservative* for the
> false-alarm direction (a surviving effect is understated).

That inference is valid **only if the over-splitting is uniform across conditions.** The
false-alarm attack explicitly searches for the paraphrase that maximises answer-set
diversity. That is precisely the regime in which a judge that fails to recognise 35% of
genuine aliases would split *more* — inflating the **attacked** score rather than the
baseline, making the measured effect *larger* than the truth, and inverting the
conservativeness claim into an anti-conservative one.

**The uniformity assumption is not stated anywhere in the paper.** `methods.tex` (~line 305)
and `limitations.tex` (~line 72) both assert the conservativeness conclusion with no
condition attached. Whoever owns those files should add the qualifier whether or not this
check ever runs; a conservativeness argument with no failure condition is not an argument.
That edit is outside this task's ownership and is not made here.

---

## 2. Is (iii) computable from data already on disk?

### 2.1 What the caches actually hold

Checked, not assumed:

| cache | holds | does **not** hold |
|---|---|---|
| `attacks/wk9_def{,b}/*.jsonl` | `entropy_before`, `entropy_after`, `best_query`, greedy `answer_under_q_prime`, `frac_correct_under_q_prime` | **no samples under q'**, no cluster assignments, no cluster counts, no judge output |
| `wk4_full_2000q/samples.jsonl` | the 10 benign sample **texts** per question, `samples_correct`, `accepted_forms` | nothing under q' |
| `wk4_full_2000q/entropy.jsonl` | `assignments`, `n_clusters`, `entropy_nats` — **NLI clusterer only** | no judge, no exact-match |
| the n=6 judge pass | `results/null_control_3arm_judge_n6.md`: three aggregate **mean moves** per arm | **no per-target record survives.** No `null_control_ckpt*.jsonl` exists on disk or anywhere in git history |

Two consequences, both load-bearing.

**The attacked side has no surviving text.** `se/attacks/harness.py` (lines 158–174) *does*
generate the 10 samples under q' — it needs them for the status re-check — and then keeps
only the greedy string and the correct-fraction. `AttackOutcome` has no samples field. Those
generations are gone and must be re-created.

**The n=6 judge pass gives no preliminary.** The task brief allowed for the possibility that
it stored per-arm cluster counts. It did not. `_arms()` in `null_control.py` returns
`entropy_nats` only, from all four clusterers, and the checkpoint stores *moves* — signed
differences of two entropies. A difference of entropies is not on the entropy lattice and
cannot be inverted to a cluster count. There is no n=6 judge cluster-count number to report,
with or without a caveat.

### 2.2 What *is* recoverable: inverting the entropy lattice

At N=10 the discrete entropy is a near-injective function of the cluster-size partition, so
a stored `entropy_nats` recovers the cluster count K without re-running anything.

- p(10) = **42** partitions map onto **39** distinct entropies.
- The 3 coincidences are enumerated exactly:
  `H=1.088899975: (6,2,1,1) vs (4,3,3)` → K ∈ {3,4};
  `H=1.609437912: (4,2,1,1,1,1) vs (2,2,2,2,2)` → K ∈ {5,6};
  `H=1.748067349: (4,1,1,1,1,1,1) vs (2,2,2,2,1,1)` → K ∈ {6,7}.
- **Every coincidence is ambiguous by exactly one cluster.** An ambiguous inversion still
  bounds K to within 1, so there is no case in which the inverter is uninformative.

**Validated, not asserted.** `wk4_full_2000q/entropy.jsonl` stores both `entropy_nats` and
`n_clusters`, giving 2000 independent checks:

| n | K recovered exactly | ambiguous, true K in the candidate set | **mismatch** | off-lattice |
|---|---|---|---|---|
| 2000 | 1748 (87.4%) | 252 (12.6%) | **0** | 0 |

On the campaign cells the ambiguity is smaller still, because the *benign* side needs no
inversion at all: the campaign's `entropy_before` is bit-identical to the cached clean score
for the same `question_id` (80/80 on the FA cell, 59/59 on hide), so K_benign is read
straight from `n_clusters`. Only the attacked side is inverted, and it is ambiguous on 6 of
80 FA targets.

---

## 3. The preliminary that the cache *does* support (NLI arm, n=80)

**⚠ THIS IS NOT THE JUDGE, AND MUST NOT BE LIFTED INTO THE PAPER AS IF IT WERE.** It is the
detector's own NLI clusterer — the confounded arm, and the arm the attack was optimised
against. It measures **exposure**: how far the attack moves the clustering regime. It says
nothing directly about whether the judge's over-splitting is condition-uniform.

Paired within target, `wk9_defb`:

| cell | n | mean K benign → attacked | paired ΔK [95% bootstrap] | +/0/− | sign test | mean move |
|---|---|---|---|---|---|---|
| se_false_alarm | 80 | 6.01 → 8.30 | **+2.288 [+1.788, +2.788]** | 55 / 23 / 2 | p = 2.3e-14 | +0.5256 nats |
| se_hide | 59 | 7.25 → 4.81 | **−2.441 [−2.949, −1.949]** | 0 / 10 / 49 | p = 3.6e-15 | −0.5381 nats |

(`wk9_def` gives +2.263 [+1.775, +2.750] and −2.327 on its n=55 hide snapshot; the FA figure
is stable across the two runs to 0.03 clusters. The hide cell was still being appended to
during this session — it read 58 records at one point and 59 minutes later. Read the cell
size from the JSONL.)

**What this licenses.** The false-alarm attack adds **+2.29 clusters** to a 10-sample set,
55 of 80 targets moving up and only 2 down. That is a large regime shift, and it is the
exposure a differentially-over-splitting judge would amplify. It sets the scale the judge
check has to be powered against; it does not substitute for it.

**One further cache-computable quantity, and it cuts the other way.** On the benign side the
NLI clusterer merges only **11.8 of 45** pairs per FA target. Pairs that a clusterer merges
are the only pairs on which a false *split* is possible at all; the attack, by raising K,
reduces that count further. If the true partition behaved like the NLI one, the attacked side
would offer *fewer* false-split opportunities, which is the conservative direction. **This
argument cannot be relied on**, because it is exactly the NLI partition whose validity
finding 14 exists to question, and the attacked side has no independent partition on disk to
check it against. It is recorded here so that it is not later mistaken for evidence.

---

## 4. Designing (iii) properly

"Cluster counts must not diverge" is not yet an estimand. Taken literally it is guaranteed to
fail: the attack's *purpose* is to raise the cluster count, and §3 measures it doing so by
+2.29. Any statistic that treats a raw attack-vs-benign cluster-count difference as the
failure signal will fail on a perfect judge. The estimand has to isolate the **judge's
error**, not the real change in answer diversity, and it has to be **paired within target**,
because targets differ enormously in intrinsic answer diversity (K ranges 1–10 with an IQR of
[4, 9] on this stratum).

### 4.1 Primary estimand: differential over-splitting bias, in nats

For target *t* and condition *c* ∈ {benign, attacked}, on the same N = 10 budget:

- **A^c(t)** — the 10 sampled answers.
- **J^c(t)** — the deployed judge's union-find clustering of A^c(t).
- **O^c(t)** — the same clustering with every **oracle-positive** pair force-merged
  (union-find again). Two samples are oracle-positive when the span oracle says *both* name
  the gold answer, so both give the same answer to the question. O is J with its split-side
  errors repaired, as far as the oracle can see them.
- **bias^c(t) = H(J^c(t)) − H(O^c(t)) ≥ 0** — the nats of entropy that the judge's
  over-splitting contributes. Non-negative because merging clusters strictly reduces Shannon
  entropy.

> **δ_bias = mean over targets of [ bias^attacked(t) − bias^benign(t) ]**, in nats.

Paired percentile bootstrap over targets (20,000 draws, seed 0), with an exact sign test and
a Wilcoxon signed-rank as corroboration.

**Orientation, fixed now:** **δ_bias > 0 means the judge inflates the attacked side more than
the baseline** — the measured false-alarm effect is *overstated*, and the conservativeness
argument is inverted.

Why this estimand and not a cluster-count difference: it is on the **nats scale of the actual
decision**, so its magnitude is directly comparable to the effect it could manufacture; it is
identified (it does not need a second clusterer as a proxy control); and it is invariant to
the genuine increase in answer diversity, because the genuine increase appears in both H(J)
and H(O) and cancels.

**Scope, stated up front:** `bias` sees **split-side error only**. It cannot see false
*merges* — the judge collapsing two genuinely different answers — because nothing certifies
"these two wrong answers differ" at scale. That is the correct scope: the entire
conservativeness argument is a claim about over-splitting. It also means a small δ_bias is
**not** a clean bill of health for the judge in general, only for the specific failure mode
the re-scoping rests on.

### 4.2 The pre-registered margin, derived rather than asserted

A non-significant difference from an underpowered test is not evidence of uniformity, so the
rule is an **equivalence / non-inferiority** rule with the margin fixed before any data
exists.

- Reference effect: the paired mean false-alarm move on the population the claim is about,
  **+0.5256 nats** (n = 80, `wk9_defb`, NLI arm, cache-measured).
- **Margin Δ\* = 20% of the reference effect = 0.1051 nats.** The fraction, 20%, is what is
  pre-registered; if the paper's headline false-alarm effect changes when the null control
  lands, Δ\* is recomputed as 20% of *that* number and the change is disclosed. The fraction
  may not be revised after seeing δ_bias.
- On the empirical scale of this pool (0.1984 nats per cluster, measured over K = 5…10 on the
  2000-question pool), Δ\* corresponds to **0.53 clusters** — a useful sanity anchor, not a
  second criterion.

**Rationale for 20%:** a differential that could manufacture up to a fifth of the reported
effect is the largest one that leaves the qualitative conclusion standing after disclosure. A
differential large enough to manufacture the *whole* effect is roughly δ_bias ≈ +0.53 nats,
about 2.6 clusters — five times the margin, so the test is not being asked to resolve a
hair's breadth.

### 4.3 The decision rule, and the direction that forces withdrawal

Implemented as `noninferiority_verdict()` and unit-tested:

| verdict | condition | consequence |
|---|---|---|
| **FAIL** | 95% CI lower bound **> 0**, **or** point estimate **≥ +0.1051 nats** | **The judge is withdrawn as false-alarm adjudicator.** |
| **PASS** | 95% CI upper bound **< +0.1051 nats** | Conservativeness is *certified*, not merely un-refuted. (iii) closes. |
| **INCONCLUSIVE** | anything else, including a wide interval centred on zero | **Not a pass.** The judge stays one arm of a bracket. |

**What FAIL costs, concretely** — pre-committed now, so it cannot be renegotiated later:
the judge stops being the finding-14 adjudicator; the false-alarm claim reverts to the
NLI/exact-match bracket already reported under condition (iv); the null control's judge arm
becomes a disclosed diagnostic; and every sentence that cites 0.93 as *licensing*
adjudication — `introduction.tex` ~142, `experiments.tex` ~54, `discussion.tex` ~194,
`conclusion.tex` ~55 — is re-scoped to "validated on clean gold aliases; used as one arm of a
bracket". The 0.93 number itself is unaffected; what changes is what it licenses.

### 4.4 Secondary statistics, all free with the same run

1. **δ_φ — the per-pair false-split rate difference.** φ^c = P(the judge splits a pair | the
   pair is oracle-positive, condition c), target-clustered bootstrap. Same orientation. This
   is the mechanism underneath δ_bias and is the number to quote in prose.
2. **δ_α — the order-asymmetry rate difference.** The deployed judge is symmetric by
   construction: `judge(a,b) AND judge(b,a)`. Every pair on which the two orderings disagree
   is therefore a **split decided by an arbitrary tie-break**, not by a semantic judgement.
   α^c = P(ab ≠ ba). **δ_α needs no labels at all** — no oracle, no human, no reference
   clusterer — and it is the cleanest possible evidence that the attack is driving the judge
   into its unstable regime. Both orderings are already computed and then discarded by
   `make_batched_judge_fn`; logging the disagreement costs nothing.
3. **δ_K — the cluster-count difference-in-differences** against the exact-match clusterer.
   **Reported descriptively, never tested.** A clusterer with a *constant* merge fraction
   mechanically produces a non-zero additive DiD, so this statistic has a null that is not
   zero and it is not a valid test. It is here because it is the literal reading of the
   phrase "cluster counts must not diverge", and it needs to be visibly present and visibly
   demoted rather than silently dropped.

**Multiplicity, and which way it points.** Any one of δ_bias, δ_φ, δ_α returning FAIL forces
withdrawal, with **no multiplicity correction**. This is deliberate and it is the strict
direction: the check exists to catch a problem, not to discover an effect, so the family-wise
error that matters is failing to catch one. Correcting these three towards non-detection
would defeat the purpose of running them.

---

## 5. Condition (ii): validation on messy real sampled pairs

### 5.1 The gap is real, and larger than "messy"

The 0.93 was measured on clean gold-alias pairs — `Broncos` / `Denver Broncos`. The deployed
decision is over model samples generated at `max_new_tokens=48, T=1.0`, and on disk those are
**mean 19.6 words, median 17, max 46; 99.0% are longer than three words**. They are full
sentences with hedges and asides. The judge's own prompt opens *"Two short answers to the same
trivia question are given"* and its six few-shot exemplars are all one-to-three-word entities.
**The deployed inputs are off-distribution for the validated prompt.** That is a nameable
validity gap, not a formality, and it is the strongest single reason (ii) should not be waved
through.

### 5.2 Where the labels come from — and most of them are free

There is no gold standard for "are these two model outputs the same meaning", but there is a
usable proxy that costs nothing and is already the paper's own correctness rule. For each
question the cache stores `samples_correct[i]`, the word-boundary span oracle's verdict that
sample *i* names the gold answer. Over pairs:

- **oracle-positive** — both name the gold answer, so both give the *same answer to the
  question*. This is an **answer-equivalence** label, which is exactly what the judge's prompt
  asks about.
- **oracle-hard-negative** — exactly one names the gold answer, so the other does not: a
  genuine non-equivalent pair in messy sampled prose.
- **unlabelled** — neither does. They may agree on a wrong answer or disagree; nothing
  labels them.

What is available, counted:

| population | pairs | oracle-positive | oracle-hard-negative | unlabelled |
|---|---|---|---|---|
| whole clean pool (2000 q) | 90,000 | 51,914 (57.7%) | 15,098 (16.8%) | 22,988 (25.5%) |
| the FA-80 targets | 3,600 | 2,748 (76.3%) | 633 (17.6%) | 219 (6.1%) |

The gold-alias validation used n=300 per stratum. **Both strata are available at that size
without generating a single token**, on real messy sampled pairs, on the exact population the
claim is about. The positive stratum is abundant; the hard-negative stratum is thinner and
concentrated (633 pairs across 37 of the 80 targets), so a matched n=300 hard-negative draw
must either accept clustering in 37 targets or top up from the wider correct stratum, and say
which.

**The unlabelled 25.5% is a real hole**, and it is the hole that matters most for the *hide*
direction, where both samples are typically wrong. Nothing short of human labelling touches
it. The judge is already scoped away from hide, so this is a limitation to disclose rather
than to close.

### 5.3 A caution that must travel with these labels

Answer-equivalence is **not** the relation the detector's clusterer implements. Measured on
the same cached data: the NLI clusterer **splits 63.5% [63.1%, 63.9%]** of oracle-positive
pairs pool-wide, and **66.4% [64.7%, 68.2%]** on the FA-80 targets. Two 20-word generations
can both name the gold answer and still fail to bidirectionally entail each other, because
each carries content the other does not.

Read this correctly: it is **not** a bug report against the NLI clusterer, and it must not be
put in the paper on this document's authority. It is the gap between "same answer" and
"bidirectional entailment of full generations" at a 48-token generation length. It matters
here for one reason only — **it fixes what the (ii) validation is measuring.** Scoring the
judge against oracle-positive labels scores it as an *answer*-equivalence oracle, which is
what its prompt asks for and what the independent-clusterer argument needs. It would be
wrong to read the resulting positive-recognition number as directly comparable to the NLI
clusterer's behaviour. (The magnitude of that gap deserves separate scrutiny by whoever owns
the clustering analysis; it is out of scope here.)

### 5.4 (ii) and (iii) are the same experiment

Apply the oracle labels **separately by condition** and (iii)'s identified estimand falls out
of (ii)'s data: φ^benign and φ^attacked are the same measurement made twice, and δ_φ is their
difference. One run closes the machine half of both. They should not be scheduled separately.

### 5.5 Can (ii) be done without a second human?

**The machine half, yes — completely.** No human is needed to score the judge against
oracle-derived labels on real sampled pairs.

**The human half, no — and it should not be skipped.** The oracle label has its own error
rate: a sample can contain the gold span while denying it ("it was *not* David Seville"),
which mislabels a true negative as positive. Worse for the differential estimand,
**contamination cancels out of δ only if the contamination rate is itself condition-uniform**
— which is a version of the very assumption under test. So the audit must sample **both**
conditions, and that requirement is not optional.

The economical design is to **audit the disagreements, not the population.** Only pairs where
the judge and the oracle disagree can change φ; a random census of agreements is mostly
wasted. Proposed sheet: **100 judge-vs-oracle disagreements (50 per condition) + 50 agreement
controls + 10 catch trials = 160 pairs**, which at the existing protocol's measured 60–90 s
per pair is **~3–4 hours across four sessions**, plus a washout before a 30% re-annotation
round.

**The machinery already exists and transfers.** `scripts/prepare_equivalence_audit.py` and
`results/equivalence_audit_protocol.md` were built for **question** equivalence, and the
transferable parts are the hard parts: the blinding contract (`ANNOTATOR_COLS`, enforced by
tests), randomised A/B orientation, post-shuffle pair ids, a separate key file, catch trials
built from excluded material, the 30% round-2 test–retest with new ids, the κ-plus-prevalence
reporting rule, and the session-hygiene caps. What needs rewriting is §1 and the worked
examples in §3, which are all about question scope and presupposition and do not apply to
answer pairs. **The sampler itself must not be edited** — it is owned elsewhere and its
blinding contract is under test. A sibling script for answer pairs is the right shape.

---

## 6. What the GPU run costs, exactly

### 6.1 The cheapest path is zero, and it expires

The queued null control (`--K 50 --n_seeds 3`, FA only, n=80) performs **55 judge clusterings
per target = 4,400 clusterings**, on both attacked and budget-matched benign inputs, and
throws away everything but four floats per clustering. Persisting `res.samples`, the four
assignment vectors, and the per-pair ab/ba disagreement flags — roughly **1.5 KB per
clustering, ~7 MB total** — would deliver δ_bias, δ_φ, δ_α and δ_K **for zero additional GPU
time**, on the *budget-matched* contrast that is the paper's actual decision statistic rather
than the weaker q-vs-q' contrast a standalone run can afford.

Two constraints, both from `docs/START_HERE_overnight.md`:

- `null_control.py` is **owned elsewhere and must not be edited while the chain can reach
  it** — Python reads the script at invocation, so an edit now lands days later as a crash or
  as silent garbage. This has to be queued alongside the two edits already waiting for an
  idle device, not applied.
- **The window closes when the null control launches.** If it starts un-instrumented, the
  4,400 clusterings are spent and (iii) costs the standalone 3.1 GPU-h afterwards.

Minimal instrumentation spec, for whoever owns the file: in `_arms()`, return the
`ClusterResult.assignments` from all four clusterers alongside the entropies, plus
`res.samples` and — from `make_batched_judge_fn` — the count of pairs where `ab != ba`; write
them into the existing per-target checkpoint record. No change to any computation, no change
to any verdict, no extra forward pass. Oracle labels are then derived offline on CPU via
`se.scoring.is_acceptable`.

### 6.2 The standalone run, if the window is missed

Design **J1** — paired q vs q' on the 80 FA targets:

- **Benign arm: no generation at all.** The samples are cached as text for **80/80** FA
  targets (and 59/59 hide). 80 judge clusterings.
- **Attacked arm:** the q' samples were discarded, so regenerate 10 samples per target under
  the recorded `best_query` at the pinned `GenConfig(max_new_tokens=48, T=1.0, n=10, seed=0)`,
  then 80 judge clusterings.
- **Run it in two passes** — victim-only generation first, writing to cache; judge-only
  afterwards. This avoids the victim/DeBERTa/judge co-residency that forced
  `judge_batch_size` down to 6 in the first place, and may allow the judge pass back up to 12.

**Total: 160 judge clusterings + 80 victim sampling passes.**

| judge_batch_size | s / clustering | GPU-h (central) | bracket |
|---|---|---|---|
| 6 (the deployed, co-resident setting) | 67 | **3.11** | 2.31 – 4.21 |
| 12 (achievable if the judge runs alone) | 49 | **2.31** | 2.31 – 2.31 |

**Provenance of these seconds, and its weakness.** Two measured anchors, both
`docs/critique_log.md` entry 22: a full evaluation with the batched judge is ~55 s
(13 evaluations ≈ 12 min/target), and the cheap arms alone are ~6.1 s (25 GPU-h for
80 × 185 evaluations). The judge clustering is the difference, **~49 s — about 90% of the
cost**. **Both anchors were taken at `judge_batch_size=12`.** Nothing in this repository
measures the judge at 6. Halving the batch takes 90 prompts from 8 chunks to 15; the bracket
spans the two things that can be true (pure compute-bound → unchanged; pure overhead-bound →
×15/8), and the central figure is their geometric mean. **This is a model, not a
measurement.** Replace it before quoting it: time 20 clusterings on cached benign samples —
about 25 minutes — and the bracket collapses to a number.

**Power is not yet known, and cannot be asserted.** The per-target variance of δ_bias has
never been observed. Run a **12-target pilot (24 clusterings + 12 generations ≈ 0.5 GPU-h)**,
estimate the paired SD, and confirm n=80 resolves Δ\* = 0.1051 nats before committing the
rest. If it does not, the honest outcome is INCONCLUSIVE at n=80, reported as such — the
margin is not widened to manufacture a pass.

### 6.3 Against the queue

Matrix ~4 GPU-h remaining, then the null control at ~67 GPU-h: a **~71 GPU-h ≈ 3-day** queue,
against 33 days to 2026-09-15. The standalone (ii)+(iii) run at **3.1 GPU-h adds ~4%**. The
instrumented alternative adds **0%** and yields a better contrast. There is no compute
argument for leaving (iii) unrun; the only real cost is the ordering risk in §6.1.

---

## 7. Pre-registration block

Fixed 2026-08-13, before any judge run on either condition.

1. **Estimand.** δ_bias = mean_t [ bias^attacked(t) − bias^benign(t) ], nats, paired within
   target; bias^c(t) = H(judge clustering) − H(judge clustering with oracle-positive pairs
   force-merged).
2. **Population.** The 80 FA targets of `wk9_defb/triviaqa_se_false_alarm.jsonl` — a prefix
   of the fair pool's correct stratum, *nested* inside it, not a separate population.
3. **Test.** Paired percentile bootstrap over targets, 20,000 draws, seed 0; exact sign test
   and Wilcoxon signed-rank as corroboration.
4. **Orientation.** Positive = the judge splits relatively more on the attacked side =
   anti-conservative.
5. **Margin.** Δ\* = 20% of the reported false-alarm effect. Currently 0.20 × 0.5256 =
   **0.1051 nats** (≈ 0.53 clusters at 0.1984 nats/cluster). The *fraction* is what is fixed;
   recomputing Δ\* against a revised headline effect is permitted and must be disclosed.
   Revising the fraction after seeing data is not.
6. **Verdict.** FAIL if CI lower bound > 0 or point ≥ Δ\*. PASS if CI upper bound < Δ\*.
   Otherwise INCONCLUSIVE — **which is not a pass.**
7. **Corroborating failures.** δ_φ and δ_α are evaluated under the same rule. **Any one FAIL
   forces withdrawal**, uncorrected for multiplicity.
8. **Consequence of FAIL.** As set out in §4.3, in full, now rather than later.
9. **δ_K DiD** is descriptive and is never a claim statistic.
10. **What is *not* pre-registered as a pass condition:** a small δ_bias certifies the
    split-side failure mode only. It does not license the judge for the hide direction, and
    it does not close (ii)'s human half.

---

## 8. Honest assessment: is (ii) closable before 2026-09-15?

**Machine half: yes, comfortably.** 3.1 GPU-h (or 0), plus a day of CPU analysis. It produces
the judge's positive-recognition and hard-negative accuracy on real messy sampled pairs from
the deployed population, per condition, with target-clustered intervals — a strictly better
validation than the gold-alias 0.93 it supplements.

**Human half: yes in principle, and it is the binding constraint.** ~3–4 hours of blinded
annotation plus a washout and a re-annotation round. But there are now **two** unrun human
audits competing for one annotator: this one, and the **question**-equivalence audit whose
sheet has been built and sits at **0 of 123 pairs annotated** (`results/equivalence_audit.csv`).
At the recorded working cadence — Mon/Wed/Fri 08:00–10:00 plus Sunday 10:00–11:00, ~7 h/week,
~33 h left before the deadline — the two audits together consume **20–25% of all remaining
working time**, against six other owed items.

**If one must be dropped, drop this one.** The question audit substantiates the word
*meaning-preserving* in the paper's title; the answer audit bounds the noise on a label that
is only used to validate one arm of a bracket. The fallback for (ii) is defensible and should
be written now rather than improvised in September: report the machine half in full, report
the oracle-label failure modes qualitatively with hand-inspected examples, and state in
Limitations that the label's error rate is unbounded. That closes (ii) *as a measurement* and
leaves *one* disclosed assumption, which is a strictly better position than the current one,
where the deployed prompt has never met a deployed input.

**(iii) has no human component at all.** It is bounded entirely by GPU scheduling, and by
whether the null control is instrumented before it launches.

---

## 9. Provenance

- Producing code: `scripts/judge_owed_conditions.py` — CPU only, stdlib only, read-only over
  the caches, no GPU, no model, no re-clustering. Tests: `tests/test_judge_owed_conditions.py`
  (23 tests, including the 39-value lattice, the 3 coincidences, an N=20 cross-check against
  the repo's own 455, and the full verdict truth table).
- Caches read: `~/.cache/se-research/samples/wk4_full_2000q/{samples,entropy}.jsonl` and
  `~/.cache/se-research/samples/attacks/wk9_{def,defb}/triviaqa_se_*.jsonl`, inside WSL.
- Nothing in this document was produced on a GPU, and no GPU work was launched.
- Files **not** touched, by ownership: any `.tex`, `null_control.py`, `recompute_fair.py`,
  `check_population_labels.py`, `wk_defense.py`, `prepare_equivalence_audit.py`,
  `achievable_fpr_grid.py`, `n_scaling_grid.py`, `rescore_likelihoods.py`,
  `cluster_count_bound.py`.
