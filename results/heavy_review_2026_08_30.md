# Heavy review — panel chair's report, 2026-08-30

Reviewer: panel chair, consolidating ten lenses and one defence round.
Subject: `paper/main.pdf` (34 pp., HEAD `fab9df1`) and the repository as its artifact.
Nothing was edited, nothing was committed, nothing ran on the GPU. Scratch work lives in the
session scratchpad; every number below was re-derived by the chair from raw artifacts with
independent code unless the line says otherwise.

---

## 1. The verdict

**The science is sound and the headline is correct. The paper is not yet correct, and I would
not post it as it stands — but every fix is a text edit, none requires a new run, and the whole
list is a morning's work.** I re-derived the measurement-validity spine from the raw caches with
my own code and it reproduces exactly: 1424 greedy-correct answers, 150 of them at the `ln 10`
ceiling, 10.53% → the printed 10.5% [9.0, 12.2]; the 42 partitions of 10 mapping to 39 distinct
entropies with exactly 2 in the top decile and a 0.1386-nat top gap; 0/200 at `ln 40` with the
cheapest firing threshold at 4/200 = 2.0% and the 5%-budget threshold landing at exactly
10/200 = 5.0%; the whole null-control table, cell for cell, including the exceedance test at
*p* = 0.939 / 1.000 / 1.000. The central claim — that at N=10 the discrete estimator's ceiling
atom *is* the achievable false-alarm floor, so a 5% budget is unavailable however well the score
ranks — survived every attack the panel could construct, and I could not break it either. The
refusal to interval the N=40 floor is a correct call, not a hedge. What holds the paper back is
four things, none of which touches that spine: the floor is a function of the equivalence oracle
as well as the model and the corpus, and two sentences say otherwise while the paper's own
Table 1 prints the contradicting numbers; one of the three "concordant" non-rejections is
structurally incapable of rejecting, so it cannot corroborate anything; the null's search budget
A is counted on the wrong side of the feasibility gate, which does not change the verdict but
does falsify three sentences about the direction and robustness of the result; and Methods states
as pending an experiment that finished on 2026-08-13. Two further one-word errors in Methods
invert the threshold-selection rule and the direction of a fidelity bound. Separately, and
independently of the paper: the repository as it stands cannot reproduce Tables 1 and 2 for
anyone who clones it, and the paper contains no availability statement of any kind.

---

## 2. What was checked

**Re-derived by the chair, from raw data, with independent code (not read off any `results/*.md`):**

| Quantity | Source | Result |
|---|---|---|
| Ceiling atom on the superset | `~/.cache/.../wk4_full_2000q/relabeled.jsonl` | 1424 correct, **150 at `ln 10`** = 10.53%; Wilson [9.04, 12.24] → paper's 10.5% [9.0, 12.2] ✓ |
| Same, other strata | same | 295/2000 at cap; 145/576 hallucinating ✓ |
| N=10 lattice | exhaustive integer partitions | 42 → **39** distinct; 2 in top decile; top gap 0.138629 ✓ |
| N=20 / N=40 lattice | same | 627 → 455, 7 in top decile; 37338 → 14 114 ✓ |
| N=40 floor grid | `results/n_scaling_ckpt.jsonl` (400 rows) | **0/200 at `ln 40`**; top clean 3.619565 with 4/200 = 2.0%, TPR 6.0%; 5%-budget τ = 3.515593 at exactly 10/200 = 5.0%, TPR 11.0% ✓ |
| Wilson intervals | own implementation | 0/200 → [0, 1.885] (paper 1.9); 10/200 → 5.0% [2.74, 8.96] (paper [2.7, 9.0]); 4/80 → 5.0% [1.96, 12.16] ✓ |
| Prevalence arithmetic | 28.8% prevalence, FPR 10.53%, TPR 25.17% | 148 alerts, PPV 49.2%, 216 missed ✓ |
| Table 1 saturation row | `results/diag_defb.json` | clean/attacked = 10.0/52.5, 46.2/70.0, 1.2/10.0 ✓ |
| Table 1 exceedance block | `null_control_ckpt_defb.jsonl` + campaign snapshot; own transcription of the randomised-tie rule, own BetaBinomial convolution | Σm = 3704 over n = 77, E[S] = 20.3516 → 20.4; NLI median S = 28, *p* = 0.9392 → **0.939** ✓; n_eff = 3704/30 − 1 = 122.5 ✓; exact and judge *p* = 1.000 ✓ |
| NLI decomposition | same | 2 strict exceedances + 25.96 tie credit = E[S \| data] 27.96 |
| Denominators | same | m = 50 × 71, plus {1, 26, 27, 27, 35, 38}, plus 3 empty arms (`qb_565`, `qz_3393`, `qb_2689`) → n = 77 ✓ |
| Winner's curse | both checkpoints | `_defb` (n=69) → 44.0% [23.2, 63.9] = the paper's figure; `_def` (n=60) → **45.2% [24.8, 65.3]** |
| Hide cell status | live campaign dir | **80 rows, 80 unique ids**, all with `entropy_after` and `n_objective_calls` = 181; mean Δ −0.6593; 44 successes; **4 at the entropy floor** |
| Feasibility accounting | `src/se/attacks/optimizer.py` + campaign file | `best_obj`/`best_query` update is inside `if fr.feasible:`; pooled gate pass rate 3058/4703 = **0.650** |
| Test power by arm | own Monte Carlo, 20 000 draws | deployed cut is **reject iff S ≤ 11** at A = 181; under a ceiling-saturating attack, P(reject) = 0.56 (NLI), **0.0000** (exact), 1.000 (judge) |
| Threshold rule | `src/se/stats.py:940` vs `methods.tex:314` | code says *smallest* τ with achieved FPR ≤ budget; paper says *largest* |
| Artifact tracking | `git ls-files`, `git check-ignore` | `null_control_ckpt_defb.jsonl`, `diag_defb.json`, `n_scaling_ckpt.jsonl`, `data/cache/**` all **untracked** |

**Checked by the panel and relayed here, not independently re-derived by the chair:** the
citation audit against live arXiv/PMLR/PMC sources (17 of 27 entries); the three-clone
reproduction runs and the pytest counts; the full 34-page visual read; the pre-registration
timeline audit against `docs/critique_log.md`.

**Not checked by anyone:** whether the alias-aware span oracle behind `greedy_correct`
mislabels (it defines the 1424 and is unverifiable from disk, as the paper says); whether the
judge's clustering of *sampled answers* is accurate (the paper flags this as owed); anything
requiring GPU re-generation.

---

## 3. Surviving findings

Ordered by how much a reader's belief moves if they are right.

### F1 — The floor is a function of the equivalence oracle, and two sentences say it is not

**Where.** `discussion.tex:138-141` ("That frequency is a property of the model and the question
distribution, not of the estimator's arithmetic"); `limitations.tex:205-208` (the same clause,
plus the scope list "It is one model family in one quantisation on one dataset"). The
unqualified claim is at `main.tex:220-221`, `introduction.tex:90-92`, `discussion.tex:66-68`,
`conclusion.tex:13-14`.

**The finding.** The ceiling-atom mass — and therefore the floor, by the paper's own identity —
depends on three inputs, not two: the model, the question distribution, and the bidirectional
equivalence oracle that decides what counts as "N mutually distinct meanings". The paper scopes
every other axis meticulously (discrete vs Eq. (5), N=10 vs N=40, fair pool vs superset,
deterministic vs randomised rules) and never scopes this one; both sentences above positively
enumerate the determinants and exclude it.

**Why the defence failed.** The paper's own Table 1 already prints the refutation. On the *same
80 samples*, with only the equivalence relation varying, the clean ceiling-saturation rate is
**46.2% (exact-match), 10.0% (shared NLI), 1.2% (LLM judge)** — I recomputed all three from
`results/diag_defb.json` (37, 8 and 1 baselines at `ln 10` out of 80) and they match the table
to the digit. That is a 37-fold swing that crosses the 5% line. Under the judge oracle a 5%
budget on these targets is *feasible*; the Abstract says it cannot be. The defender re-derived
the same counts and conceded.

**Concrete failure scenario.** An operator needs a 5% false-alarm budget at N=10. They read the
Abstract and Conclusion, then read Limitations to learn what could make their case different,
and are told the axes are model family, quantisation and dataset, and that the floor is a
property of the model and the question distribution. They conclude the obstruction transfers to
their deployment. If their deployment clusters with an LLM judge rather than DeBERTa-MNLI, the
paper's own data says the atom is 1.2% and their budget is available.

**Honest bound on the finding.** These rates are measured on the 80 attacked false-alarm
targets, not the 1424. They establish that the oracle moves the atom, not the value of a
judge-oracle floor on the superset. Note that the NLI rate on the 80 (10.0%) tracks the fair
pool's 9.5% and the superset's 10.5%, which is why the transfer argument is credible. Note also
the legitimate counter-argument the fix should answer: semantic entropy is *defined* with
bidirectional-NLI clustering, and `limitations.tex:129-130` says so. The claim is not wrong for
SE-as-defined; it is unscoped, and the paper's own independent-oracle programme is the reason a
reader will not read it as scoped.

**Fix.** (i) In both sentences, name the third determinant: "…a property of the model, the
question distribution *and the equivalence oracle*, rather than of the estimator's arithmetic."
(ii) Add the oracle to the `limitations.tex:205-208` scope list. (iii) One sentence in Discussion
cross-referencing the Table 1 saturation row as three measurements of the same atom under three
oracles, with the 46.2 / 10.0 / 1.2 spread. No new data; the numbers are already in the paper.

---

### F2 — The exact-match arm cannot reject for any attack, so its *p* = 1.000 corroborates nothing

**Where.** `experiments.tex:274` ("The rule returns a non-rejection, and it does so in every
arm"), Table 1 rows at `:120-127`, `introduction.tex:49-53` ("fails to reject in every clustering
arm… the observed exceedance count sits above its null expectation in all three"),
`conclusion.tex:57-60`, and `methods.tex:361-362` ("we report the NLI and exact-match bracket
*alongside* the judge so no conclusion rests on the re-scoped oracle alone").

**The finding.** At A = 181 with the campaign's own m_j, the deployed test rejects iff S ≤ 11
(exact convolution: P(S ≤ 11) = 0.0296, P(S ≤ 12) = 0.0501 — I reproduce both). In the
exact-match arm, 1461 of the 3704 benign draws sit at their target's own `ln 10` ceiling, which
the attack cannot exceed. S is minimised when the attack is pinned at the ceiling on every
target; simulating that configuration 20 000 times with the campaign's measured tie
multiplicities gives **E[S] = 149.9, sd 9.9, minimum observed 114** — an order of magnitude above
the rejection region. The exact-match arm's *p* = 1.000 is a structural certainty, not a
measurement.

**Why the defence failed.** It did not contest the mechanism, and the escape hatch is closed
numerically: to bring the tie credit from 1461 tied draws down to 11 you would need mean
b ≥ 132, against a measured mean of 40.4 on that arm. The finding survived with two of the
reviewer's secondary numbers corrected.

**Concrete failure scenario.** A referee reads "the observed exceedance count sits above its null
expectation in all three [arms], which is the direction against the attack" and treats it as
three semi-independent confirmations across clusterers. One of the three could not have come out
any other way, for any attack whatsoever.

**The good news, which the fix should keep.** The same computation on the other arms: under a
ceiling-saturating attack the judge arm rejects with probability **1.000** and the NLI arm with
probability 0.56. The pre-registered adjudicator is genuinely informative, and its non-rejection
(S = 646 against any plausible E[S] ≤ 31) is overwhelming. The bracket is real; it has two arms,
not three.

**Fix.** State in Experiments that the exact-match arm's rejection region is empty on this data
(S ≥ 114 under the most attack-favourable configuration, against a cut of S ≤ 11), so its
*p* = 1.000 is reported for completeness and carries no evidential weight. Drop "in all three"
and "in every arm" from the Introduction and Conclusion in favour of the NLI-and-judge bracket.
Rewrite `methods.tex:361-362`, which currently rests the independence argument on a column that
cannot move. Adding the per-arm power-against-saturation figures (0.56 / 0.00 / 1.00) would turn
a weakness into a strength.

---

### F3 — The search budget A is counted pre-gate while the benign count m is counted post-gate

**Where.** `experiments.tex:154-157` ("Here A is the attacker's search budget, meaning the number
of scored evaluations the maximum ranges over. It takes the value A ≈ 181"); Table 1's
`A = 181` header and its E[S], n_eff and "0/101" rows; `experiments.tex:278-291`;
`introduction.tex:51-53`; `conclusion.tex:58-60`.

**The finding.** The two sides of the exchangeability null are counted differently. The benign
m = 50 are *post-gate*: `scripts/null_control.py:174-178` rejection-samples until it has 50
paraphrases that pass feasibility (capped at 250 attempts; on three targets all 250 failed,
which is why n = 77). The attack's reported maximum is *also* post-gate — in
`src/se/attacks/optimizer.py:133-145` the `best_obj = c.obj; best_query = c.query` update sits
inside `if fr.feasible:`, so an infeasible candidate can never be the reported value; I confirmed
on the campaign file that `entropy_after == max(feasible_objs)` to 1e-12 on every target that has
feasible candidates. But A is set to 181, the *pre-gate* count of scored evaluations. The gate is
nowhere near a no-op: the pooled pass rate among candidates the optimiser actually checked is
3058/4703 = **0.650**.

**Why it matters, quantitatively.** The error runs in the direction that favours the paper's own
conclusion: A too large ⇒ E[K] = m/(A+1) too small ⇒ the null expects fewer benign exceedances ⇒
the observed total looks more anti-attack ⇒ *p* too large ⇒ non-rejection too easy. My own
transcription of the test (it reproduces the paper's numbers exactly at A = 181), NLI arm,
median S = 28 over 101 tie draws:

| A | E[S] | *p* at median S | *p* range | draws ≤ 0.05 |
|---|---|---|---|---|
| **181 (as shipped)** | 20.35 | **0.9392** | [0.298, 1.000] | **0/101** |
| 145 (gate pass 0.80) | 25.37 | 0.7172 | [0.079, 0.998] | 0/101 |
| 127.7 | 28.78 | 0.5004 | [0.027, 0.986] | 1/101 |
| **118 (measured pass 0.650)** | 31.10 | **0.3604** | [0.012, 0.963] | **2/101** |
| 100 | 36.67 | 0.1286 | [0.002, 0.827] | 14/101 |

**What survives and what does not.** The verdict survives: the median *p* does not approach 0.05
anywhere in the plausible range, and the judge arm — the pre-registered adjudicator — is
untouched (*p* = 1.000 at every A). Three claims do not survive:

1. "the observed exceedance total is *above* its null expectation in all three arms, which is the
   direction *against* the attack" — at the measured feasible budget the NLI arm's total (28) is
   *below* its expectation (31.1). Same sentence at `introduction.tex:52-53` and
   `conclusion.tex:58-60`.
2. Table 1's "draws reaching *p* ≤ 0.05 = 0/101" and "range [0.229, 1.000]", and the prose "no
   realisation anywhere near the 5% cut" / "bottoms out at 0.229, still more than four times the
   5% cut" — at A = 118 the range starts at 0.012 and 2 of 101 draws cross the cut.
3. "its 181 scored evaluations behave like n_eff ≈ 122 random feasible paraphrases, which is
   fewer than the budget it spent" — this compares a count of *feasible* paraphrases against a
   count of *scored evaluations*. Against the feasible budget (~118) the search is worth
   marginally more, not fewer.

**Why the defence failed.** The defender refuted the reviewer's dramatic framing and one of the
reviewer's constants, and conceded the core. I re-derived the core independently and it holds.

**Fix.** Either (a) recompute the headline with A measured on the feasible side and report the
0.650 gate rate, or (b) keep A = 181, state explicitly that it is an *upper bound* on the budget
the maximum ranges over, add a sensitivity row (A = 118 at the measured gate rate) to Table 1,
and delete the three claims above. (b) is cheaper and arguably more honest, since the per-target
feasible count is only partially observed — the gate is applied lazily, so only 4703 of 14 480
candidates were ever checked. Note that the paper's own two sentences make the mismatch visible
to any reader: it says the m = 50 are "passed through the same feasibility gate" four lines from
where it defines A as "the number of scored evaluations".

---

### F4 — Methods says the hide cell is still filling. It completed on 2026-08-13

**Where.** `methods.tex:209-211` ("Hide targets, by contrast, reach their floor only rarely. We
deliberately attach no count to that last statement here: the hide cell is still filling against
its planned 80, so any figure we quote for it goes stale between drafts"); the same premise is
reused at `:225` ("the hide arm is additionally still incomplete against its planned 80") and at
`:240-244`, where the cross-stratum AUROC comparison is withheld because the hide arm "is still
filling".

**The finding.** `~/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_hide.jsonl`
(mtime **2026-08-13 07:21**) holds **80 rows with 80 unique question ids**, each carrying
`entropy_after` and `n_objective_calls` = 181. Mean Δ = −0.6593, 44 successes, and **4 targets
reach the entropy floor** — 4/80 = 5.0%, Wilson [2.0, 12.2]. The repo's own snapshot
(`data/cache/attacks/wk9_defb_snap/`) has 52 hide rows and its `SNAPSHOT.txt` records that the
file was "being APPENDED to by a live run at snapshot time", which is why a reader of the repo
copy would agree with the paper and be wrong. The paper's substantive statement ("reach their
floor only rarely") is *true*; the reason it gives for attaching no number is *false*, and has
been for 17 days.

**Why the defence failed.** It could not be refuted. The defender pinned provenance by
reproducing the paper's own false-alarm counts (42 finishing at the ceiling, 8 beginning there,
13 one lattice point below, the 0.139-nat gap) from the sibling file in the same live directory,
so the directory the paper reads from is the directory holding the complete hide cell.

**Concrete failure scenario.** A reader concludes the hide-side floor count does not yet exist
and so cannot ask why it is not shown. It exists, it is stable, and it is 4 of 80. The same
applies to the cross-stratum AUROC comparison withheld at `:240-244` on the same false premise.

**Why this one matters beyond its size.** The commit two before HEAD is titled *"paper: the run
finished five days before the paper noticed."* This is the same failure, a second time, in the
same document. Whatever process caught the first instance did not sweep for the second.

**Fix.** Replace the withholding clause with the count: "Hide targets, by contrast, reach their
floor only rarely — 4 of 80 (5.0%, Wilson [2.0, 12.2])." Fix `:225`, and decide on the merits
whether to add the cross-stratum comparison now that the pooling obstacle is gone. Then grep the
whole paper once more for status claims about any run.

---

### F5 — The threshold-selection rule is stated inverted, and as written it would break the headline

**Where.** `methods.tex:314-316`: "We therefore select τ as the **largest** threshold whose
*achieved* clean false-positive rate is at or below the stated budget."

**The finding.** The detector flags when H ≥ τ, so FPR(τ) is non-increasing in τ and
{τ : FPR(τ) ≤ budget} is an upper set. Its *largest* element is the never-firing threshold. The
rule as written returns τ = ∞ at every budget. The code does the right thing —
`src/se/stats.py:940` documents `at_most` as "smallest threshold whose achieved FPR is
<= target_fpr" — and it is the code that produced the paper's numbers: on the N=40 grid I
re-derived, the smallest τ with FPR ≤ 5% is 3.515593, achieving exactly 5.0% (10/200) with
TPR 11.0%, which is the paper's 5.0% [2.7, 9.0] operating point.

**Concrete failure scenario.** A reader implementing the stated rule gets τ = ∞ at every budget
and every N, concludes the obstruction is universal rather than specific to N=10 with a loaded
ceiling atom, and cannot reproduce the paper's own 5.0% achieved point at N=40 — the number the
Abstract uses to show the obstruction has gone.

**Fix.** One word: *largest* → *smallest*.

---

### F6 — The direction of the fidelity bound is reversed, and Limitations states it correctly

**Where.** `methods.tex:318-320`: the answer-flip subcategory collects "candidates for
equivalence-gate leakage and **lower-bound the fidelity** of the NLI constraint."
`limitations.tex:163-167` says of the same subcategory that it "is a *lower* bound on how often
the gate admits a non-equivalent paraphrase."

**The finding.** A lower bound on leakage is an **upper** bound on fidelity. The two statements
contradict each other; Limitations is right.

**Concrete failure scenario.** A reader of Methods takes the answer-flip count as a floor on how
faithful the equivalence gate is ("at least this good") when it is a ceiling ("at most this
good"). That inverts the direction of the caveat on the paper's central threat-model assumption —
that the attack's paraphrases preserve meaning.

**Fix.** "…and **upper**-bound the fidelity of the NLI constraint" (or "lower-bound the leakage
of").

---

### F7 — The paper has no availability statement, and the artifacts behind Tables 1 and 2 are not in the repository

**Where.** The whole PDF; `.gitignore:47` (`data/cache/`), `:48` (`results/*.json`), `:102`
(`results/*.jsonl`); repo root has no `LICENSE`.

**The finding.** I grepped `main.tex` and all seven section files for
`availab|github|repositor|artifact|licen|zenodo|url|http|href|doi.org|acknowledg`: every hit is
either a package option or an unrelated prose use of "available". There is no repository URL, no
data statement, no licence, no appendix. Separately, the four artifacts that back the paper's two
tables and its N-scaling ladder are all untracked: `results/null_control_ckpt_defb.jsonl`,
`results/diag_defb.json`, `results/n_scaling_ckpt.jsonl`, and everything under `data/cache/`
including the campaign snapshot. Every N=10 headline number is computable only from
`~/.cache/se-research/samples/wk4_full_2000q/`, which lives outside the repository tree entirely.

**Concrete failure scenario.** A referee wants to check 10.5% [9.0, 12.2]. The PDF gives them
nothing to clone. If they obtain the repository anyway, `scripts/null_control_defb_report.py`
dies on `FileNotFoundError` and the scripts that would rebuild the floor grid resolve their input
only through hard-coded absolute paths into the author's home directory.

**Fix.** Add a Data and Code Availability paragraph with a URL and a commit hash; add a
`LICENSE`; and see §6 for which files must be un-ignored for that URL to mean anything.

---

### F8 — The repository ships the superseded winner's-curse checkpoint and gitignores the definitive one

**Where.** `scripts/winners_curse_reeval.py:387` (`--tag` default `_def`) and its docstring at
`:24`, `:28`; `.gitignore:102`; `results/winners_curse_se_false_alarm.md`.

**The finding.** `git ls-tree HEAD results/` contains
`winners_curse_ckpt_se_false_alarm_def.jsonl` (60 records). The definitive `_defb` file (69
records) matches `results/*.jsonl` in `.gitignore` and is absent from any clone. The committed
report is the `_defb` one — I recomputed both: `_defb` gives retention 44.0% [23.2, 63.9],
matching the report's 44.0% [23.1, 64.2] and the Abstract's "44% [23%, 64%]"; `_def` gives
**45.2% [24.8, 65.3]**. The script's argparse default and both documented no-GPU usage lines say
`--tag _def`, and the report's provenance line names its source with a wildcard, so nothing in
the repo flags `_def` as superseded.

**Concrete failure scenario.** A reproducer runs the documented no-GPU rebuild, it exits 0, and
`results/winners_curse_se_false_alarm.md` is silently overwritten with n = 60 and retention
45.2% [25%, 65%] — numbers that disagree with the paper with no indication which is right. The
disagreement is small enough not to change a conclusion, which is exactly what makes it hard to
notice.

**Fix.** Track `_defb` (a `!` exception in `.gitignore`), change the argparse default and the
docstring to `_defb`, and either delete `_def` or rename it with a `SUPERSEDED_` prefix.

---

### F9 — README asserts the framing the paper retracted

**Where.** `README.md` (last touched 2026-06-25, 202 commits before HEAD).

**The finding.** README:14 calls the false-alarm attack "the headline"; README:18 says a
perturbation fooling both detectors "is evidence against the *paradigm* of sampling-based
uncertainty detection"; README:6 gives the target as "an arXiv preprint by 15 September 2026"
(settled at 2026-10-01). The Status section stops at Week 3. The paper's actual position is that
the attack shows no effect and the contribution is measurement validity.

**Concrete failure scenario.** A reader of the artifact concludes the work demonstrates a
paradigm-level attack, then finds `results/wk7_false_alarm.md` reporting 9/10 false-alarm success
with no superseded banner, and takes away "the attack works at 90%" — the uncontrolled, pre-B1
number the paper's whole null-control apparatus exists to retract.

**Fix.** Rewrite the README to the paper's position; add the SUPERSEDED banner that
`attack_matrix.md` and the `wk9`/`wk11` files already carry to `wk6_hide_attack.md` and
`wk7_false_alarm.md`.

---

### F10 — "the same population yields 28 at n=200 and 35 at n=2000" — those are two different populations

**Where.** `introduction.tex:119`.

**The finding.** From `results/fair_pool_granularity.md`: 28 distinct realised values is the
**fair pool's correct stratum, n = 200** (line 80); 35 is the **full labelled pool, n = 2000**,
correct *and* hallucinating (line 82). "The same population" is the phrase doing the work — the
argument is that the count is monotone in sample size *for a fixed population*, so it measures
the sample rather than the estimator. As written, a checker finds the two numbers come from
different populations and the argument loses its force. The repository has a guard,
`scripts/check_population_labels.py`, whose entire purpose is to catch this class of error; it
does not cover this sentence.

**Fix.** "…the correct stratum yields 28 at n = 200 and the full labelled pool 35 at n = 2000…",
or substitute the same-population rarefaction curve the source file already tabulates.

---

### F11 (relayed — verified by the related-work referee against primary sources, not by me)

- `related_work.tex:22-25` attributes to Kernel Language Entropy a **brittleness** argument. KLE's
  argument is **coarseness**: hard equivalence classes cannot express degrees of semantic
  similarity. A referee who opens arXiv:2405.20003 finds the opposite framing and concludes the
  attack's premise has borrowed a justification its source does not give. *Fix:* re-attribute, or
  cite the coarseness claim for what it is.
- The structural scaffolding of the headline — a finite achievable-size grid, the randomised test
  that reaches the chords, the convex hull — is classical detection theory, and the paper cites no
  classical statistics anywhere (`grep` for `neyman|lehmann|romano|provost|fawcett|conformal`
  across the paper returns zero; all 27 bib entries are 2023-2026 ML papers). A referee reads the
  correct randomisation analysis in Discussion with no citation and concludes either unawareness
  or over-claiming. *Fix:* one Related Work sentence and two citations (Lehmann & Romano §3.2 for
  randomised tests; a discrete-ROC reference for the hull).
- `related_work.bib`, `rossolini2026worstcase`: the title field is wrong; the real arXiv:2601.14519
  has a different title. *Fix:* correct the entry.
- `related_work.tex`, "What the estimator can and cannot express": McCabe et al. explicitly
  **disclaim** the finite-sample-bias mechanism as theirs, and Sun et al.'s abstract already covers
  the sampling-budget axis the paper presents as its twist. *Fix:* two clauses.

---

### Checked, real, and consequence-free — recorded so a later referee does not re-raise them

- **The tie multiplicity `b` is measured on the NLI objective and reused for all three arms.**
  `scripts/null_control_defb_report.py:146` computes `tie_b` once from `n_feasible_at_best`,
  outside the arm loop, and `src/se/stats.py`'s own docstring insists b "MUST be MEASURED, not
  estimated". For the exact and judge arms it is neither, and the direction of the error inflates
  *p*. But both arms' S exceeds the cut by more than the entire tie credit (exact: 220 strict
  exceedances alone; judge: 470), so no plausible b changes either verdict. Worth one sentence of
  disclosure, no more.
- `experiments.tex:340` prints **29%** where the source gives 29.8% (and, three lines later,
  "30%"). It rounds the wrong way. Cosmetic.
- Two referees' N=40 distinct-value enumerations differ by 2 (14 114 vs 14 116, a
  rounding-tolerance artefact). The paper does not quote the number. No action.

---

## 4. Refuted findings — apparent problems that are not problems

Listed so the author does not spend time on them, and as the panel's own audit trail.

1. **"Power 0.77 is measured on the shared-NLI arm and is ~0 on the adjudicator arm."**
   **Refuted on its central number.** The defender re-ran the shipped DGP
   (`scripts/power_sim_deployed.py`) with the headroom vector swapped arm by arm from
   `results/diag_defb.json`'s per-target baselines; the power is not arm-specific in the way
   claimed, and the paragraph at `experiments.tex:358-364` that the reviewer cited as support says
   the opposite of what they read into it. No action.

2. **"The exceedance excess is manufactured by proposer duplication; a zero-drift null already
   reads 1.44-1.49."** **Refuted.** That figure is one uncalibrated default cell of
   `scripts/duplication_level_sim.py`, and it mis-states the quantity the deployed test consumes
   by 3.6×. The defender decomposed the actual NLI excess: 2 strict exceedances plus 25.96 in tie
   credit = 27.96, exactly the observed median of 28 — I reproduce both numbers independently. The
   excess is tie credit, not duplication drift. No action. *(F3 above reaches a similar-sounding
   conclusion by a completely different and verifiable route; do not conflate them.)*

3. **"The Contributions block is a 1,901-word single paragraph and a referee will lose the
   thread."** **Refuted as a finding**, though the measurement is accurate. The defender showed
   the failure scenario is contradicted by page 1 and that two load-bearing assertions in the
   finding are false. It is a style preference, not a defect. Breaking the paragraph up is a free
   choice, not a correction.

4. **The headline itself, attacked from six directions.** The lattice; the atom-equals-floor
   identity and its "for as long as the ceiling carries mass" conditioning; the randomised-rule
   concession (p = 0.05/0.095 = 0.526 → TPR 14.5%, and (0.095, 0.275) genuinely being the
   maximal-slope hull vertex); the nesting of the attacked pool inside the fair pool; the superset
   argument. **All survived.** I re-derived the lattice, the identity's arithmetic and the N=40
   grid myself and reached the same place.

5. **The refusal to quote an interval on the N=40 2.0% floor.** Repeatedly probed as a possible
   hedge. **It is a correct call**: 0/200 at the cap means the atom is empty, and 4/200 at the next
   lattice point is an achieved rate, not an estimate of a population floor, because nothing in 200
   draws bounds the probability of 39-distinct-in-40. Leave it alone.

6. **Pre-registration discipline.** The no-op convention's disclosure; the 68-of-80 lock; the
   correction of the prereg's own transcription errors in rows (b)/(c); the statement of the missed
   n ≥ 80 in Methods rather than only Limitations; the verification that convention (d) is the
   least attack-favourable of five in all three arms. **All checked, all real.** This part of the
   paper is a model of the practice.

---

## 5. What a reproducer can and cannot do with the public repository today

**Can**, on a bare clone with no GPU:

- Re-derive every pinned paper quantity computed from committed Markdown inputs:
  `scripts/derived_paper_quantities.py` runs to exit 0 and regenerates
  `results/derived_paper_quantities.md` identically.
- Run both guards: `scripts/check_population_labels.py` (8 paper files, 16 rules, 78 number
  patterns) and the operational-provenance check.
- Re-run the power simulations and the analytic tie-rule level
  (`power_sim_{deployed,empirical,randomized}.py`, `tie_rule_analytic_level.py`) to byte-identical
  output.
- Run the test suite: ~1220 pass, 17 skip, 3 fail (the third failure is itself an artefact of the
  missing files).
- Read every report in `results/` and all 38 entries of the withdrawal ledger.

**Cannot:**

- Reproduce **Table 1 or Table 2**. `results/null_control_ckpt_defb.jsonl` and
  `results/diag_defb.json` are untracked and `data/cache/` is ignored wholesale, so
  `scripts/null_control_defb_report.py` dies on `FileNotFoundError`.
- Reproduce the **N=10 headline** (10.5% [9.0, 12.2], the empirical half of the lattice story, the
  fair-pool grid, the clean AUROC). These need `~/.cache/se-research/samples/wk4_full_2000q/`
  (~4.8 MB), outside the repo tree; the consuming scripts fall back to four hard-coded absolute
  paths under the author's home directory and exit when none resolves.
- Reproduce the **N=40 ladder**: `results/n_scaling_ckpt.jsonl` is untracked.
- Reproduce the paper's **winner's-curse interval**: the definitive checkpoint is ignored and the
  default tag points at the superseded one (F8).
- **Find the repository at all** from the paper: there is no URL in the PDF (F7).

The honest summary is that the repository publishes its *conclusions* and withholds its
*measurements*. The analysis code is all there and is unusually well documented; the inputs it
needs are not.

---

## 6. Repository actions needed before this is public

1. Un-ignore and commit the five load-bearing artifacts, with `!` exceptions in `.gitignore`:
   `results/null_control_ckpt_defb.jsonl`, `results/diag_defb.json`,
   `results/n_scaling_ckpt.jsonl`, `results/winners_curse_ckpt_se_false_alarm_defb.jsonl`, and
   `data/cache/attacks/wk9_defb_snap/` (with its `SNAPSHOT.txt`). A few MB in total.
2. Ship the Week-4 sample cache — at minimum `relabeled.jsonl` and `entropy.jsonl` (~0.9 MB
   together) — or a release asset, and point the resolvers at it. Without this the headline is not
   checkable by anyone.
3. Replace the hard-coded `\\wsl.localhost` / `/home/abhi` fallback paths with the
   `resolve_labels()` pattern `achievable_fpr_grid.py` already implements (a `--labels` flag plus
   an `SE_RELABELED_JSONL` env var). At least ten scripts encode the author's username.
4. Fix `scripts/winners_curse_reeval.py`: default tag `_defb`, docstring usage lines `_defb`, and
   mark or delete `_def`.
5. Add SUPERSEDED banners to `results/wk6_hide_attack.md` and `results/wk7_false_alarm.md`, the two
   pre-B1 files that still report the retracted 9/10 result unqualified.
6. Rewrite `README.md` (F9), and add a `LICENSE`.
7. Add the Data and Code Availability paragraph to the paper, naming the repository and the commit
   (F7).
8. Refresh the campaign snapshot in `data/cache/attacks/wk9_defb_snap/` so its hide file carries
   the complete 80 records, or note in `SNAPSHOT.txt` that the live cell has since completed —
   otherwise the repo copy corroborates the false statement in F4.

---

## 7. Residual uncertainty — what this panel could not settle

1. **The feasible search budget is only partially observed, so F3's correction has a range, not a
   value.** The optimiser gates lazily: only 4703 of 14 480 candidates were ever
   feasibility-checked, and those were the high-objective ones, which are plausibly the least
   likely to pass. The true A therefore lies somewhere in [118, 181] and my 0.650 pass rate is an
   estimate on a non-random subset. *What would settle it:* record feasibility on *every*
   candidate, or run a few hundred ungated feasibility checks on the stored candidate strings —
   CPU-only NLI work, no generation — which would pin the null's centre exactly. Failing that, a
   per-target A_j instead of a scalar, since the three empty benign arms prove the gate rate varies
   enormously across targets.

2. **Whether the judge-oracle floor on the 1424 is really below 5%.** F1 rests on 80 targets. The
   judge's clean at-cap rate is 1/80, a Wilson interval of [0.2%, 6.7%] — it straddles the 5%
   line. *What would settle it:* re-cluster the existing Week-4 samples for the 1424 correct
   answers under the judge. The samples are cached; this is judge inference only, no generation,
   but it is not free.

3. **Whether the judge clusters *sampled answers* correctly at all.** The paper is admirably candid
   that the 0.93 validation is on clean gold-alias pairs and that on real samples the judge
   under-splits (27/80 baselines collapsed to one cluster against NLI's 4). The adjudicator arm —
   the load-bearing arm, once F2 removes the exact-match column — rests on an oracle validated on a
   proxy. *What would settle it:* the human equivalence audit the paper itself says is owed. This
   is the single largest open risk in the secondary contribution, and the paper already says so.

4. **The span oracle behind `greedy_correct`.** The 1424 denominator and the
   correct/hallucinating split are defined by an alias-aware span match whose own error rate is,
   as Limitations says, unverifiable from disk. Everything I verified in §1, I verified
   *conditional on that labelling*. *What would settle it:* a hand-labelled sample of a few hundred,
   with an agreement estimate.

5. **What I did not verify myself.** The 17 citations checked against live sources were checked by
   the related-work referee; the three-clone reproduction and the pytest counts were run by the
   repro referee. I re-derived the tracking facts (F7, F8) with `git ls-files` and `git
   check-ignore`, but not the clone-and-run behaviour. If any item in §5's "cannot" list bears on a
   decision, re-run it.
