# Heavy review 2 — panel chair's report

**Date:** 2026-08-31 · **Commit reviewed:** `32713f1` · **Artifact:** `paper/main.pdf` (39 pp.)
**Panel:** ten referees — six cold (stats, adversary, reader, methods, claims, repro), four delta
(regression, churn, hedge, artifact) — plus a defender assigned to refute every material finding.
**Chair's own work:** every finding below was re-derived by the chair independently of the referee
who raised it, on CPU, with no GPU work, no edits to tracked files, and `git status` clean at
`32713f1` before and after. Two findings below are the chair's, not the panel's.

---

## 1. The verdict

**The paper is sound and I would post it, after the repairs in §3 — six of which are
sentence-level.** Nothing here touches the headline. I re-derived the central claim from scratch by
exact integer arithmetic and it is exactly right: at N=10 the 42 integer partitions collapse to
**39** attainable entropies, **2** of them in the top tenth of [0, ln 10], the top two separated by
**0.138629436** nats, the maximum attained by exactly one partition, with three genuine collisions;
455 and 7 at N=20. The atom-equals-floor identity is correctly stated and correctly conditioned
("while the atom carries mass"). I rebuilt all 400 N=40 entropies from the raw 780-bit pairwise
verdict matrices in `results/n_scaling_ckpt.jsonl` with my own union-find and reproduced every
recorded value with **zero mismatches**, and from them every N=40 number in the Abstract: 0/200 at
ln 40, floor 4/200 = 2.0%, 10/200 = 5.0%, 12/200 = 6.0%. The exact BetaBinomial convolution behind
the claim statistic reproduces the paper's own printed cut (`S ≤ 11`, Pr = 0.0296, Pr(S ≤ 12) =
0.0501) to four decimals. The empirical arithmetic is, as four independent referees concluded, in
unusually good order.

What the repairs fix is a set of *statements about* those numbers: a power figure computed for a
design that was not the one run, a monotonicity result proved for a quantity that is not the floor,
a per-target parameter collapsed to its mean inside a convex function, a stale tense on the
adjudicator arm, seven promised measurements that are never delivered, an availability sentence
that is impossible as written, a missing fifth entry in a list of pre-registration deviations, and
a unit test asserting a number that is false. Two of these change a number a reader is told four
times to use. None changes the verdict, and I want that stated plainly: after ten referees and my
own re-derivation, **the non-rejection holds, the floor identity holds, and the lattice is exact.**

---

## 2. How this review differed from the last, and what that tells us

**Six referees read cold, with no knowledge of the prior review.** They converged, independently, on
the two things the last round had already touched — the power figure's provenance and the budget
parameter's identification — which is convergent evidence that those passages are genuinely hard to
read correctly rather than that one reviewer was fixated. Neither cold referee had seen
`heavy_review_2026_08_30.md`.

**The earlier fixes held.** The four delta referees, auditing what six correction rounds changed,
found **no arithmetic error introduced by any correction**. That is the single most reassuring
result on this page. Every quantity the rounds moved re-derives from raw artifacts: the feasibility
accounting (14,400 scored children, 4,703 gated = 32.7%, 3,058 passed = 0.6502), both budget bounds
(41 and 121), the whole exceedance sensitivity table including the A=89/90 crossing, the clamp
counts 0/2/22. Two corrections even improved on the ruling that ordered them. Six rounds of
parallel edits by ~60 agents did not produce a single number that disagrees with its source. That
is worth saying because it was the specific risk this review was convened to test.

**Two things are entirely new after six rounds, and one of them is mine.**

- **The realized design's power was never computed.** All ten referees, and every prior round,
  discussed 0.77 as a level-versus-oracle question. Nobody simulated the design that actually ran.
  I did (§3.1): it is **0.67**, not 0.77.
- **The N=40 attainable-value count is wrong, and ten referees reproduced the wrong value.** Four
  cold referees independently "confirmed" 14116. The true count is **14114** (§3.8). They
  reproduced it because they ran on this Windows box, where the repository's float-dedup tolerance
  splits two exact collisions. This is precisely the convergent-error mode a chair exists to catch,
  and it is why I re-derived rather than tallied.

**Five of the thirteen major findings were refuted** (§4) — a 38% refutation rate. That is the
evidence the panel was not manufacturing problems, and three of the five were refuted on grounds
the paper itself supplies, which is a compliment to the paper.

---

## 3. Surviving findings, ordered by how much a reader's belief moves

### 3.1 — The power figure 0.77 belongs to a design that was not run. The realized design has 0.67.

**Where.** `experiments.tex` at four sites, plus `introduction.tex` and `discussion.tex` — six
sites in the rendered PDF (lines 84, 976, 1055, 1059, 1119, 1720). The load-bearing ones: "a
non-rejection must be read against 0.77 rather than 0.84" and "At the deployed operating point this
design has power 0.77 against a two-fold effect at m=50."

**What is wrong.** `scripts/power_sim_deployed.py` hard-codes `N_TARGETS = 80` and a uniform
`M_GRID` including 50. That design has 4,000 benign draws and an analytic cut of `S ≤ 13` at
achieved level 0.0437. The run that happened is **n = 77** with six short arms
(m ∈ {1, 26, 27, 27, 35, 38}) and 3,704 draws, whose cut is `S ≤ 11` at achieved level **0.0296** —
a number the paper computes itself, in the same section, and never connects to the power figure.

**Chair's re-derivation** (`one_target` imported verbatim from the paper's own DGP; headroom from
the attack cache, n = 80, mean 0.825563, 8 zero-headroom targets; scale 0.12 calibrated as the
script calibrates it; 8,000 trials, three seeds):

| design | cut | achieved level | power @ 2x |
|---|---|---|---|
| n=80, uniform m=50 (what 0.77 is) | S ≤ 13 | 0.0437 | 0.766 / 0.772 / 0.767 |
| **n=77, shipped m-vector (what ran)** | **S ≤ 11** | **0.0296** | **0.668 / 0.665 / 0.673** |

Monte-Carlo SE ≈ 0.005; the gap is ~20 SE. The mechanism is entirely the discrete cut: at a *fixed*
cut of 13 the realized design is *stronger* (0.838), because its E[S] is lower. It is the analytic
null's integer granularity dropping the cut to 11 that costs the power.

**Failure scenario.** A referee or operator follows the paper's own instruction — "a non-rejection
must be read against 0.77" — and concludes a doubling of the attacker's effective search budget
would have been caught about three times in four. It would have been caught about two times in
three. The miss probability is 33%, not 23% — a 43% relative increase in Type II error.

**The sting.** 0.67 is, to two decimals, the power of the m=30 design the same paragraph says was
*rejected as too weak*: "chosen over a cheaper m=30 (power 0.67 …) because … the design must be
able to see a small one." The run delivered the design the paper declined.

**Fix.** Re-run `power_sim_deployed.py` with the shipped `m_j` vector at n=77 and quote the result.
One sentence discharges it: *"The confirmatory run's arm lengths give a cut of S ≤ 11 at achieved
level 0.0296 rather than the design's S ≤ 13 at 0.0437; power against a two-fold effect at the
realized design is 0.67, and that is the number the non-rejection must be read against."* Then
change the six sites. Cost: one script run, six edits. No claim is lost — the paper's framing
("this bounds what could have been seen") is unchanged, only the bound.

---

### 3.2 — "The floor is non-increasing in N, which we prove rather than measure" is false as stated.

**Where.** `discussion.tex:171-177` and `limitations.tex:211`.

**What is wrong.** The coupling argument is valid and proves exactly one thing: the **ceiling-atom
mass** Pr(all N samples pairwise inequivalent) is non-increasing in N. The paper defines the
**floor** as the smallest non-zero achievable false-alarm rate. Those coincide *only while the atom
carries mass* — a condition the paper states correctly three paragraphs later and then does not
carry back into the proof. Once the atom empties, the floor is the mass of a different lattice
point and the coupling says nothing about it.

**Chair's exact counterexample** (rational arithmetic, no floats). Take a question type whose model
puts equal mass on exactly K meanings, i.i.d. draws, and a perfect clusterer — the paper's own
clusterer class. The floor is the mass of the top attainable score, i.e. of the most balanced
partition:

| K | N | floor (exact) | decimal |
|---|---|---|---|
| 10 | 10 | 567/1562500 = 10!/10^10 | 0.00036288 |
| 10 | **11** | 6237/3125000 | **0.00199584** |
| 10 | 12 | 168399/31250000 | 0.00538877 |
| 3 | 3 | 2/9 | 0.2222 |
| 3 | **4** | 4/9 | **0.4444** |

The floor **rises** by a factor of 5.5 from N=10 to N=11 and 15x by N=12. Raising the budget can
increase the false-alarm floor.

**Failure scenario.** A reader takes "we prove rather than measure" as licence to extrapolate past
N=40 — which is precisely the use Limitations puts it to, since it is offered there as the one
thing that *can* be said where measurement stops. The paper's own N=40 row is inside the regime the
proof does not cover: at-cap mass 0/200, floor 4/200 = 2.0%. The single mathematical claim in the
paper is the one that does not hold in the regime the paper's data occupies.

**Fix.** Two sentences, no data. State what is proved — the atom mass is non-increasing, hence the
floor is non-increasing *while the atom carries mass* — and say that once the atom empties
monotonicity becomes an empirical question, which the measured ladder answers affirmatively at
N=10 → 20 → 40 and does not settle beyond it. This is strictly stronger writing than what is there,
because it makes the N=40 row do work rather than sit outside a theorem.

---

### 3.3 — The "hard lower bound" A=41 is a Jensen error; the honest bound is four times more adverse.

**Where.** `experiments.tex`, "The budget A is not identified": *"against an expectation rising from
20.4 to 30.4 to 88.2, so both stand more than fourfold above it at the hard lower bound"*, and
Table 1's row "median p at A=41 (lower bound)".

**What is wrong.** A is per-target — "the number of candidates the reported maximum actually ranges
over" — and the paper derives its lower bound per target (A_j = recorded feasible set + 1), then
reports only the **mean, 41**, and runs the test with that scalar. But E[K_j] = m_j/(A_j+1) is
convex in A_j, and the per-target A_j span 1 to 132 (quartiles 1 / 8 / 33 / 66). Jensen guarantees
the scalar understates the null expectation.

**Chair's re-derivation** from `triviaqa_se_false_alarm.jsonl` joined to the checkpoint on the 77
test targets (mean A_j = 40.7143, matching the paper's "41"):

| null | E[S] | exact-match p at S=390 | judge p at S=654 | NLI p at S=31 |
|---|---|---|---|---|
| scalar A = 41 (as printed) | **88.19** | 1.000 | 1.000 | < 0.001 |
| per-target A_j (honest) | **349.04** | **0.802** | 1.000 | < 0.001 |

Thirteen targets with A_j ≤ 5 supply 228 of the 349; seven with A_j = 1 and m = 50 supply 25 each.

**Failure scenario.** A reader takes the row labelled "lower bound" as the least favourable
admissible budget and concludes two of three arms sit robustly fourfold above their null even in
the worst case. Under the honest version of that same bound, exact-match sits at 1.12x (not >4x)
and its p is 0.80, not 1.000.

**What survives, and it matters.** The **adjudicator's p stays 1.000** under the honest per-target
null. The invariance the verdict actually rests on is intact. This is a margin-and-margin-only
correction.

**Fix.** Either run the test with the per-target A_j vector and report E[S] = 349 with p = <0.001 /
0.802 / 1.000, replacing "more than fourfold above it" with the adjudicator-only statement the
paragraph already relies on; or keep the scalar and state explicitly that it is a plug-in mean
inside a convex function and therefore *not* the conservative bound, giving the honest number
alongside. The first is better and costs one script run.

---

### 3.4 — A fifth pre-registered condition is missing from the list of four deviations, and the mechanism it existed to check is present in the code and undisclosed.

**Where.** `experiments.tex`, "Decision rule (single, pre-registered, with disclosed deviations)":
*"Four deviations from the original pre-registration are disclosed…"* through *"a reader is
entitled to check that the rule was not tuned to the result."*

**What is missing.** `docs/critique_log.md` entry 23 pre-commits, verbatim: *"The exact test is
PRIMARY iff the null-objective ablation's mean exceedance count Kbar falls within [0.5x, 2.0x] of
the theoretical m/(N+1)."* That ablation was never run. `results/null_objective_ablation.md` does
not exist; the only artifact is a **one-target** checkpoint from 2026-08-03 under a superseded
schema, and `results/null_objective_ablation_plan.md` says so in its own Status line ("**not
run**"). `se.stats.exceedance_test`'s docstring still reads *"Read that ablation before trusting
this test."* The paper never mentions the ablation — I grepped all eight `.tex` sources and the
rendered PDF; zero hits for "null-objective".

**And the asymmetry it was designed to detect is real.** `src/se/attacks/optimizer.py:104` calls
`proposer.propose(p_query, …)` on the **beam parent**, so from round 2 onward attack candidates are
second-, third-, …-order rewrites. `scripts/null_control.py:176` (`_benign_moves_arms`) calls
`proposer.propose(question, …)` on the **original**, so every benign draw is single-hop. The
exceedance null assumes the two are exchangeable draws from one distribution. The paper's own
paragraph "Where the exceedance null is, and is not, correctly specified" enumerates three
mis-specifications and this is not among them; the words "multi-hop", "single-hop" (in this sense)
and "beam parent" appear nowhere in the paper.

**Failure scenario.** A reviewer audits the pre-registration exactly as the paper invites, reads
four disclosed deviations, and concludes the primary statistic was used as pre-registered. It was
used as primary under a condition that was never evaluated, guarding an assumption the code visibly
strains.

**Note on scope.** The panel's defender showed the conclusion is invariant to the asymmetry even at
its worst case, and I accept that: this is a disclosure finding, not a result finding. It is also
the finding most likely to be raised by a hostile referee, because the audit trail is the paper's
own advertised strength.

**Fix.** Add the fifth deviation with its trigger and its status: the exact test's primacy was
pre-registered conditional on an exchangeability gate that was not run; state the multi-hop /
single-hop asymmetry in one sentence in the null-specification paragraph; state the direction
argument. This *strengthens* the paper — it is the same "we flag rather than bury" move the section
already makes four times.

---

### 3.5 — Methods says the adjudicator arm has only ever been a pipeline check. It has been run on all 80 targets, and the same paragraph says so.

**Where.** `methods.tex:392-395`: *"Re-clustering the answer samples under this validated judge has
so far been exercised only on a preliminary n=6 machinery-validation pass, which establishes that
the judge arm runs end-to-end and reports correctly, and nothing else."*

**What is wrong.** `results/null_control_ckpt_defb.jsonl` holds 80 records, every one with
`cfg.judge_model = "Qwen/Qwen2.5-7B-Instruct"` and judge values in `baseline`, `attack_move`,
`benign[]` and `seed[]`. Chair's re-derivation: judge baseline mean **0.648125** against NLI's
**1.477022**, with **27** judge baselines at exactly 0.0 against NLI's **4** — the very numbers
printed at `methods.tex:387-388`, nine lines *above* the sentence, and derivable only from an n=80
judge re-clustering. Thirteen lines *below* it the same paragraph says the question "was therefore
left to the confirmatory run under the validated judge … which completed on 2026-08-29."

**Failure scenario.** A referee reads Methods — where contribution (4) is established and where the
paper explains why the judge is the adjudicator — and learns the judge arm has only ever been a
six-target pipeline check. They then reach Experiments and find the entire non-rejection rested on
it. The natural conclusion is that the paper rests its verdict on unvalidated machinery. It does
not; a stale tense says it does.

**Fix.** One sentence. Change to the past-perfect and scope it: *"At the time the re-scope was
decided, re-clustering under this judge had been exercised only on a preliminary n=6
machinery-validation pass … The confirmatory run has since re-clustered every target's samples
under it; the diagnostics above are from that run."*

---

### 3.6 — Seven measurements are promised in the present tense and never reported.

**Where.** Methods (six) and Limitations (one). Verified against the **rendered PDF**, not the
source: 39 pages, seven sections, no appendix, References at PDF line 2124.

| promise | PDF line | reported anywhere? |
|---|---|---|
| "the success-rate curve over a sweep of delta" | 674 | no |
| "the status-gated success rate alongside the weaker entropy-only rate so the attrition … is explicit" | 680 | no |
| "this count alongside every false-alarm success rate" | 700 | no |
| "Beyond the aggregate score shift we report operating-point flips" | 708 | no |
| "the AUROC degradation is reported with a paired bootstrap confidence interval" | 726 | no |
| "not assumed away but measured directly, in the answer-flip subcategory of the evaluation below" | 584 | no (1939 restates it qualitatively, with no number) |
| "we report both the greedy status and the fraction of the detector's own samples that are correct under q'" | 1949 (**Limitations**) | no |

`grep "success rate"` over the whole rendered text returns exactly three hits: two of these
promises and one bibliography entry. `grep "flips"` returns the two promises and one qualitative
restatement.

**Chair's provenance check, which settles what these are.** `paper/paper_draft.docx` (tracked,
2026-07-09) contains verbatim: *"We report the status-gated success rate alongside the weaker
entropy-only rate so the attrition is explicit"* and *"AUROC degradation is reported with a paired
bootstrap CI that resamples questions jointly."* Its own status banner reads *"The Experiments
section is intentionally empty: no numbers are reported until the confirmatory n≥80 run
completes."* These sentences are survivors of the July framing, when the paper was going to report
an attack evaluation. The paper became a measurement-validity paper; the promises did not move.

**Failure scenario.** The most damaging is the Methods one at PDF 584. A reader finishes the Threat
model believing the feasibility gate's approximation of answer-invariance is discharged empirically
later — "not assumed away but measured directly." It is not measured anywhere. The gate is the
mechanism the entire attack half depends on, and its residual fidelity is asserted to be measured
and is not. The Limitations one is worse in kind, because Limitations is where a reader goes
specifically to learn what the paper did *not* do.

**Fix.** Delete or demote all seven to the conditional/future ("would report", "we do not report").
Purely subtractive; no number changes. This is the cheapest finding on the page and one of the two
most likely to be caught by a real referee.

---

### 3.7 — The availability statement is impossible as written, and omits the file the second headline depends on.

**Where.** `paper/main.tex`, Data and Code Availability (PDF line ~2115): *"Every measured rate here
is computed from a sample cache of 2000 TriviaQA rc.nocontext questions with **ten**
Llama-3.1-8B-Instruct generations each, 4.75 MB … the null control's per-target checkpoints are
written into the tree and then excluded from it."*

**What is wrong.** The entire N=40 ladder — the Abstract's second headline — comes from a different
run. `results/n_scaling_ckpt.jsonl`: 400 records, **`n_samples: 40` on all 400**, 200 correct + 200
hallucinating, timestamps 2026-08-13T23:57 → 2026-08-14T04:45, 2,423,028 bytes, **gitignored**
(`.gitignore:102`) and untracked. A ten-generation cache cannot produce an N=40 measurement, so the
sentence is not imprecise but impossible. The same paragraph names only the null-control
checkpoints as excluded, so this file is not named at all.

`ARTIFACT_AVAILABILITY.md` contains both halves of the contradiction: line 225 correctly lists
`results/n_scaling_ckpt.jsonl` as excluded, and line ~314 says *"the only thing standing between a
reproducer and the headline is a decision to upload it [the 4.75 MB cache]."* The paper inherited
the wrong half.

**Failure scenario.** A referee assessing reproducibility concludes one 4.75 MB file is all that
stands between them and every empirical number, and that publishing it alone makes the empirical
half checkable. They then cannot rebuild 0/200 at ln 40, the 2.0% floor, 5.0% [2.7, 9.0],
6.0% [3.5, 10.2], or either replayed rung — every one of which needs the 2.42 MB N=40 checkpoint.

**Fix.** One clause. *"Every N=10 rate here is computed from a sample cache of 2000 … ten
generations each, 4.75 MB; the N=40 ladder is computed from a separate run of forty generations
over the fair pool's 400 targets, `results/n_scaling_ckpt.jsonl`, 2.42 MB, likewise outside the
distributed tree."* While there: `ARTIFACT_AVAILABILITY.md` still opens by saying the paper has no
availability statement and is 34 pages. It now has one and is 39. That document is where the paper
sends referees.

---

### 3.8 — NEW, chair's finding. The N=40 attainable-value count is 14114, not 14116, and the test that pins it asserts the false value and fails on Linux.

**Where.** `tests/test_n_scaling_grid.py:53`
(`@pytest.mark.parametrize("n,size,top10", [(10, 39, 2), (20, 455, 7), (40, 14116, 42)])`),
`results/n_scaling_plan.md` (four sites), and — indirectly — the paper's own availability claim that
the N=20 and N=40 counts "are an enumeration over integer partitions, pinned on CPU in seconds
against an independent implementation."

**What is wrong.** Two partitions have equal entropy **iff** the integer prod(c^c) is equal, since
H = ln N − (1/N)·ln prod(c^c). Enumerating the 37,338 partitions of 40 and comparing that exact
integer gives **14114** distinct values. `scripts/fair_pool_granularity.py:113` dedupes on
`round(partition_entropy(p), 12)` instead. Two exactly-equal pairs differ by 4.44e-16 in float and
straddle a 1e-12 rounding boundary on some platforms:

```
prod c^c = 374144419156711147060143317175368453031918731001856
           (32,4,1,1,1,1) and (32,2,2,2,2)     -> 0.77766129576216558 vs ...603
prod c^c = 4369708577465148405404324615439184577547452014336
           (31,4,1,1,1,1,1) and (31,2,2,2,2,1) -> 0.88890993452595835 vs ...879
```

**Chair's cross-platform confirmation:**

| interpreter | repo's 12-dp dedup | exact prod(c^c) |
|---|---|---|
| Windows CPython 3.11 (`.venv`) | **14116** | 14114 |
| WSL Ubuntu-24.04 CPython 3.12.3 | **14114** | 14114 |

`pytest tests/test_n_scaling_grid.py -k lattice` **passes here (7 passed)** and asserts 14116. On
the Linux clone `attainable_lattice(40)` returns 14114 values and the assertion **fails**. 39 and
455 are correct; 42 in the top tenth is correct.

**Failure scenario.** A referee clones to Linux — the ordinary case — and runs the suite the README
names. The paper's flagship no-data-required claim, the one thing advertised as reproducible from a
bare clone in seconds, produces a red test. They now doubt the enumeration, which is in fact the
soundest thing in the paper. Meanwhile `results/n_scaling_plan.md`, which the availability
paragraph calls a report of record, prints 14116 four times.

**Why ten referees missed it.** Four cold referees reported reproducing 14116 — all on this Windows
box, all against the same float-tolerance implementation.
`results/morning_review_2026_08_19.md:766` already logged the platform split on 2026-08-19 and
mis-triaged it: *"interpreter-dependent, not a bug … Do not send anyone hunting an enumeration
bug."* It is not an enumeration bug; it is a **dedup-tolerance bug**, and 14116 is the wrong branch.

**Fix.** Change `attainable_lattice` to key on the exact integer prod(c^c) (returning the float
value of one representative per key), update the test literal to 14114 and `n_scaling_plan.md`'s
four sites, and delete the "interpreter-dependent, not a bug" note. **No number in the paper
changes** — 14116 appears nowhere in `paper/`. This is an artifact repair, not an erratum.

---

### 3.9 — The README reinstates two claims the paper deleted, at the URL the paper prints.

**Where.** `README.md:73` and `:77-79`, in the repository the paper's new availability section
directs referees to by URL.

**What is wrong.** Both sentences are true only at A=181, which the paper now establishes is an
*upper* bound on an unidentified parameter:

- `:73` — "That null is priced against the attacker's own search budget (~181 candidate evaluations
  per target…)".
- `:77-79` — "no draw in any arm reaches 0.05, and at the median the observed exceedance count sits
  *above* its null expectation — the direction against the attack."

The second is false in the shared-NLI arm below A≈131, and the median p crosses 5% near A=90 —
which the paper states and the README does not. Commit `59b5003` deleted the equivalent sentence
from `introduction.tex` and, in the same commit, added these to the README.

**Also.** `README.md` line ~82 states "The design has power 0.77 against a two-fold effect" — the
same figure as §3.1, so this line needs the §3.1 fix too.

**Failure scenario.** A referee follows the printed URL, lands on the artifact of record, reads that
no draw in any arm reaches the cut and that the total sits above expectation in the direction
against the attack — and carries a claim into their assessment that the paper spent a full page
retracting nineteen pages earlier.

**Fix.** Three clauses in the README: qualify both statements with "at the budget upper bound
A=181", add "the shared-NLI arm's p is not identified over the defensible range [41,181] and
crosses 5% near A=90", and change 0.77 to the §3.1 number.

---

### 3.10 — Repository hazards that must clear before the URL is public

Three items, none of which is a numerical error, all of which are worse for shipping than for being
wrong.

**(a) The un-blinding key is tracked.** `results/equivalence_audit_key.csv` (63 KB, 170 rows) maps
`pair_id` → `question_id`, attack direction, `success`, `entropy_before`, `entropy_after`, `delta`
for the same `pair_id`s as the two blinded sheets `equivalence_audit.csv` (123 rows) and
`equivalence_audit_round2.csv` (37 rows) — **whose annotation columns are entirely empty**. The
audit's own protocol, `results/equivalence_audit_protocol.md:15`, says of that key: *"un-blinding
key. **Move it out of the working directory now**, before §1."* It is in the working directory and
in git history, which makes it irreversible. The paper (PDF 1944) says this audit *"is needed before
the meaning-preserving claim is fully established."* Anyone who performs it from this clone performs
it un-blinded.
**Fix:** run the audit from a checkout that does not contain the key, and state the ordering in the
paper. Nothing can un-publish it from history, so the honest move is disclosure.

**(b) A superseded draft asserting the retracted result ships in `paper/`.**
`paper/paper_draft.docx` (2026-07-09, tracked) carries a different title and an Abstract asserting
*"a preliminary evaluation finds that an optimised paraphrase attack moves the detector … in both
the hallucination-hiding and the under-explored false-alarm direction."* It does carry a status
banner marking its figures preliminary, which mitigates. It is unreferenced by any file and unlisted
in the README's inventory of `paper/`.
**Fix:** delete it, or move it to `docs/superseded/` with a one-line banner.

**(c) Retracted-result files ship with no supersession banner.**
`results/wk6_hide_attack.md:22` and `results/wk7_false_alarm.md:22` both end
`## Verdict: PASS (9/10 = 90%)`. `results/figures/headline_auroc.json` reports
`"triviaqa/se": {"clean": 1.0, …, "n": 30}` — the circular-selection clean AUROC of 1.000 that the
paper's entire protocol contribution exists to refute.
**Fix:** a one-line banner at the top of each: *"Superseded. This used score-dependent target
selection; see §Experiments and `results/fair_pool_report.md`."*

---

## 4. Refuted findings — what is not a problem

Five major findings were put to a defender and fell. I re-checked each; the refutations hold.

**(R1) "The power figure is simulated under a DGP the paper says does not hold in the adjudicator
arm."** *(cold-methods)* — The premises are true (`one_target` does draw `2 x 181` candidates in the
scored arm; `resolve_headroom` does read NLI-arm `entropy_before`). The inference fails: the
defender showed the conclusion invariant on four independent checks. Note this is a **different**
finding from §3.1, which the defender could not refute and which I confirmed under the paper's own
DGP rather than a surrogate. The arm-labelling concern is cosmetic; the design mismatch is not.

**(R2) "0.77 is a shared-NLI operating characteristic applied to the adjudicator arm without a
label."** *(cold-claims)* — Same fate, same reason. The producing artifacts do take NLI-arm inputs
(I confirmed `results/fa80_headroom.md`: n=80, mean 0.825563, 8 zero-headroom, matching Table 1's
10.0%/52.5% NLI column exactly). The empirical claim that this changes the number does not survive.

**(R3) "The verdict names incompatible bases in two paragraphs."** *(delta-churn)* — Built on a
misquotation. `experiments.tex:270-274` names **both** re-scored arms — "and so is the exact-match
arm's … so **both** stand more than fourfold above it" — eight lines before the passage the finding
quoted as naming the adjudicator alone. I read the paragraph; the defender is right.

**(R4) "The paper says quadrupling the budget buys the operating point when its own data says
doubling suffices."** *(delta-hedge)* — `grep -rn "quadrupl" paper/` returns **exactly one** hit
(`discussion.tex:259`); the Abstract, Introduction and Conclusion state no budget multiple, so the
"stated four times" premise is false. More importantly I tested the underlying claim myself. My
replay of the N=40 verdict matrices onto random 20-subsets reproduces the paper's N=20 floor (3.15%
against the printed 3.1%) and the N=10 rung (12.1% against 12.0%) — but the **spread across
replicates is 2/200 to 10/200 (1.0% to 5.0%)**, and a single-replicate Wilson on 6/200 is
**[1.4, 6.4]**, not below 5%. The pre-registered criterion is *not* met at N=20 on a
single-replicate interval. The paper's caution is correct, and `discussion.tex:324-353` already
reasons through exactly this replicate-versus-question variance question and reaches the right
answer. This is the paper being careful, not timid.

**(R5) "Limitations tells the reader to treat every number as a preliminary effect size."**
*(delta-hedge)* — `limitations.tex:196` is the **only** use of "cells" in that file, and "cell" is
the paper's own term of art for an attack-campaign direction x stratum cell (cf. `methods.tex:209`
"the attacked cells", `:216` "The hide cell has closed at its planned 80"). The sentence is
scope-restricted. At most a clarity nit; not a finding.

**Also tested and discarded by referees, and spot-checked by me:** monotonicity of the *lattice* in
N attacked with an exact rational counterexample (holds); randomised operating points (p = 0.526,
TPR 14.5% — reproduces); non-threshold deterministic rules; a benign-paraphrase invariance
violation; suppressed transfer results; four candidate under-claims. **The Abstract's population
labelling** — flagged as a minor by cold-reader — I checked directly and it is fine: it says
"1424 clean correct answers" and "the fair pool's 200 correct answers", naming both populations
explicitly at every number.

---

## 5. Is the paper under-claiming?

**No — and I looked hard, because six adversarial rounds is exactly how a paper ends up asserting
nothing.** The hedge referee's four candidate under-claims all failed, two on the defender's
evidence and two on mine (§4, R4 especially: I re-derived the N=20 rung from raw verdict bits and
the data genuinely does not carry the stronger claim). The paper's rule — *"an interval that covers
zero is reported as covering zero, never as null"* — is honoured everywhere the panel checked, and
the nested-sample and paired-versus-unpaired comparisons all run in the conservative direction. Two
claims were killed on their merits earlier in the project and are correctly dead.

Two observations, neither an under-claim:

**The one residual mis-statement runs the *other* way.** §3.1 is an *over*-claim of power: the paper
tells the reader four times to read the non-rejection against 0.77 when the honest figure is 0.67. A
paper this careful about not overstating an effect should not be overstating its ability to have
detected one. Fixing §3.1 makes the paper *more* conservative, and it is the only place I found
where the hedging points in the wrong direction.

**The real cost of six rounds is length, not timidity.** 28,817 words of body text over 36 pages
before references, with "39 attainable values" restated 10 times across 9 sections, "0.139 nats"
9 times, the 0.93-vs-0.51 oracle validation 13 times, "a 5% budget" 12 times, and 102 first-person
clauses of the form "we say / disclose / claim no / decline". The novel result is compact and
beautiful — the score is the entropy of an integer partition of N, so at N=10 it lives on 39 points
with an atom at the top, and the atom's mass *is* the floor. That result is currently delivered at a
word count that will cost it readers. cold-reader, who could not break a single number and tried
hard, recommends acceptance **after a substantial cut**, and independently reports getting lost in
two specific places: the search-budget identification argument (pp. 17-21, four passes and a scratch
table to track which arm is valid at which A under which of three tie rules across four
denominators) and the replay/provenance ladder (pp. 25-28). Both would be helped more by a table
than by more prose. That is an editorial judgement for the author, not a referee's finding, and I
record it as such.

---

## 6. State of the artifact

Reproducibility is the strongest part of this submission and the panel could not break the headline.
From three fresh clones the run order is unambiguous, every script and results file the README and
paper cite exists at its cited path, and every cache-dependent script fails loudly with an
actionable message rather than degrading into a plausible wrong number. The combinatorial half
reproduces from a bare clone against independent enumeration. `check_population_labels.py` exits 0;
`derived_paper_quantities.py` exits 0 with all literals verified; `winners_curse_reeval.py
--report_only` rebuilds its report byte-identically. Both `\includegraphics` targets exist with
their `_data.csv`, and `figures/README.md` correctly records the two deliberately unreferenced
figures.

**Must change before the repository is public:** §3.10 (a), (b), (c) — un-blinding key, superseded
July draft, unbannered retracted-result files — plus §3.8's test literal and §3.9's README claims.

**One environmental caveat for anyone reproducing on this machine.** `ARTIFACT_AVAILABILITY.md`
§3.1 states the hard-coded UNC fallback
`\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research` did not resolve when that document was
written. **It resolves from Python on this box now**, so `scripts/make_ceiling_figures.py` and
`scripts/achievable_fpr_grid.py` silently succeed from a nominally "bare" clone here and fail
correctly for a real reproducer. Anyone testing bare-clone behaviour must check the source line each
script prints, or they will certify a path that does not exist for the referee.

---

## 7. Residual uncertainty — what this panel could not check

1. **Anything requiring the GPU.** By instruction, nothing was regenerated. The 4.75 MB N=10 cache
   and the WSL model cache were taken as given; their SHA-256 digests in `ARTIFACT_AVAILABILITY.md`
   were not verified against a fresh run. If either cache is not what it claims, everything
   downstream moves and no amount of CPU re-derivation would show it.
2. **The judge's clustering of real sample pairs.** The paper says this validation is owed, and it
   is: the judge is validated on clean alias pairs and clusters sampled answers, where it
   under-splits (27 of 80 baselines collapsed to one cluster, against NLI's 4 — I confirmed both
   counts). The residual bias is anti-conservative and the paper says so. Only a GPU run settles it.
3. **The human equivalence audit.** Unperformed — both blinded sheets have zero annotations — so the
   meaning-preserving claim rests on the automated gate. The paper states this correctly.
4. **The power DGP itself.** My 0.67 in §3.1 is computed under the paper's own simulation model
   (exponential moves censored at empirical headroom). If that model is wrong, both 0.77 and 0.67
   are wrong together. What is *exact*, and independent of the model, is the cut: `S ≤ 13` at level
   0.0437 for the design versus `S ≤ 11` at 0.0296 for the run. The finding survives any DGP.
5. **Whether never-gated candidates would have passed the feasibility gate.** Unrecoverable by the
   paper's own statement — the run stores feasible candidates' scores but not ungated candidates'
   strings. So the true A is genuinely unidentified and §3.3 corrects the *stated* bound, not the
   underlying uncertainty. Instrumenting the optimiser to record ungated strings would settle it on
   any future run, and is the single cheapest change to the pipeline.
6. **Platform coverage.** Two interpreters (Windows CPython 3.11, WSL CPython 3.12.3) — enough to
   establish §3.8 and, together with the exact-integer proof, to settle which branch is correct. A
   macOS/ARM check would be free and is worth running before release.

---

## Summary of required edits

| # | Change | Cost |
|---|---|---|
| 3.1 | Recompute power at n=77 with the shipped m-vector; replace 0.77 at six sites (plus README) | 1 script run + 7 edits |
| 3.2 | Scope the monotonicity proof to the atom; say what the N=40 row then does | 2 sentences |
| 3.3 | Run the exceedance test at the per-target A_j, or label the scalar as a plug-in mean | 1 script run + 2 edits |
| 3.4 | Add the fifth pre-registered deviation; state the multi-hop/single-hop asymmetry | 3 sentences |
| 3.5 | Past-perfect the judge n=6 sentence | 1 sentence |
| 3.6 | Delete or demote seven undelivered "we report X" promises | 7 deletions |
| 3.7 | Name the N=40 checkpoint in the availability paragraph; refresh `ARTIFACT_AVAILABILITY.md` | 1 clause + 1 doc |
| 3.8 | Key `attainable_lattice` on exact prod(c^c); 14116 → 14114 in test + plan | 1 function + 5 literals |
| 3.9 | Qualify the two README claims to A=181; note the A≈90 crossing | 3 clauses |
| 3.10 | Untrack the un-blinding key; remove the July draft; banner three retracted-result files | repo hygiene |

**Recommendation: accept as a preprint after these edits.** None is a re-run of an experiment; the
two script runs use committed inputs and no GPU.
