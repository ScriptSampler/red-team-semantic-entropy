# Gate ruling — uncommitted `paper/*.tex` edits, 2026-08-19

Strict-reviewer gate on the working-tree diff `git diff -- paper/` against HEAD `004a30b`.
Nothing here has been applied; no file outside this one was touched.

**Verdicts.** 1 APPROVE · 2 APPROVE WITH CONDITIONS · 3 **BLOCK** · 4 APPROVE WITH CONDITIONS ·
5 APPROVE WITH CONDITIONS. Blocked-claim quarantine: **CLEAN**.

The BLOCK is narrow: it is the N=20 paragraph in `discussion.tex`, and specifically the
significance argument inside it. Everything else is fixable in place.

---

## 0. The quarantine check (the thing that had to be clean, and is)

Every pattern from the prior gate's two BLOCKs, grepped over the **added** lines only
(`git diff -- paper/ | grep '^+'`, 130 lines):

| pattern | hits | pattern | hits |
| --- | --- | --- | --- |
| `0.746` | 0 | `0.738` | 0 |
| `11.0` | 0 | `14.5` | 0 |
| `13.2` | 0 | `24.0` | 0 |
| `25.5` | 0 | `0.145` | 0 |
| `0.126` | 0 | `pAUC` / `partial AUROC` | 0 |
| `46.7` | 0 | `5.19` | 0 |
| `GPU-h` | 0 | `0.704` | 0 |
| `TPR` | 0 | `true-positive` | 0 |

One `AUROC` occurrence in the added text (`methods.tex:88`), and it is not either blocked
claim — but it is a defect of its own, see item 2(a).

Worth recording that the temptation was real and was resisted: `results/n_scaling_grid.md`
section 3 puts TPR 11.0% next to the 5.0% operating point the paper now concedes, i.e. the
blocked number sits in the same table cell the approved number was lifted from, and it did
not travel. Likewise `results/post_overnight_claim_review.md` lines 240–260 contain a
ready-made Abstract replacement carrying `0.145` / `0.126` / `11.0` / `14.5`, and none of it
is in the diff. Good.

---

## 1. Winner's-curse `_def` → `_defb` — **APPROVE**

Verified line-by-line against `results/winners_curse_se_false_alarm.md` (regenerated
2026-08-13 23:44) and the two checkpoints. `wc -l`: `_def` = 60, `_defb` = 69, as claimed.

| paper | artifact | ✓ |
| --- | --- | --- |
| `44%` retention | `retention = 44.0%` | ✓ |
| `[23%, 64%]` | percentile bootstrap `[23.1%, 64.2%]`, artifact: "Only the whole-percent interval **[23%, 64%]** is supported by the resampling; the tenths are RNG noise" | ✓ |
| shrinkage `-0.341 [-0.469, -0.212]` | `-0.341 [-0.469, -0.212]` | ✓ |
| `+0.609` → `+0.268` nats | `+0.609` → `+0.268` | ✓ |
| `37` of the `69` | `37/69 (54%)` | ✓ |
| `r=0.48` | `corr = +0.482` | ✓ |

**The whole-percent reading is right, and the brief was right to make me check it.** The
artifact does not merely round; it states the endpoints are unstable across bootstrap seeds
(lower 23.0–24.3, upper 63.8–64.6) and rules the tenths out. Quoting `[23.1, 64.2]` would
have published two digits the resampling does not resolve. This is the correct call and the
opposite of the project's usual failure direction.

**The new Limitations sentence about the 11 excluded targets is independently verified.** I
read `data/cache/attacks/wk9_defb_snap/triviaqa_se_false_alarm.jsonl` directly: exactly 11 of
80 records have `best_query` string-identical to `question`, and those are exactly the 11 with
empty `feasible_objs`. "The search returned the original question, so there was no selection
to re-test" is an accurate description of the mechanism, not a paraphrase of critique_log 32's
weaker "found no feasible candidate".

### Nits (non-blocking)

- **N1.** The artifact's own "only the whole-percent interval is supported" is very slightly
  overstated on the *lower* endpoint — its stated seed wobble 23.0–24.3 straddles 23 and 24.
  The paper takes 23%, the conservative (wider) end. Correct choice; no action.
- **N2.** The Abstract's `44% [23%, 64%]` names no population. It is the winner's-curse
  subset — 69 of the 80 FA targets, themselves `right[:80]`, nested in the fair pool's
  correct stratum. This is inherited from the `45%` it replaces, not created here, but it is
  now the only unlabelled rate in the Abstract.

### One required follow-up that is NOT a paper edit

**`scripts/check_population_labels.py` is silently unarmed on these numbers, and I confirmed
it by reading the rule, not by trusting the report.** Lines 401–405 key the winner's-curse
rule on `45%`, `25%`, `65%`, `0.383`, `0.698`, `0.315`, `0.529`, `0.234`, `36 of 60` — the
retired set, every one. Line 255 defines the owning pool as "the 60 false-alarm targets" with
label pattern `\b60 false-alarm`; line 592 has `_STRATUM_OK = frozenset({15, 60, 80})` and
line 561 maps denominator `60` → winner's-curse subset. `69` is in neither.

So `population-label check: OK` is **vacuous for item 1**: the guard passed because it is
hunting values the paper no longer contains, and `37 of the 69` carries a denominator the
guard does not recognise. Re-key the rule to `44`/`23`/`64`/`0.341`/`0.609`/`0.268`/`0.469`/
`0.212`/`37 of the 69`, move `60` → `69` in `_STRATUM_OK` and the denominator map, and add a
`_def`-supersession pattern for the retired nine so they cannot come back. Until that lands,
every future edit to these eight sites is unpoliced. This is precisely critique_log 33 §12's
"a guard that goes quiet is worse than no guard", one iteration later.

---

## 2. Estimator scoping in `methods.tex` — **APPROVE WITH CONDITIONS**

All numbers check out against `results/rescore_likelihoods.md` and
`results/cluster_count_bound.md`:

| paper | artifact | ✓ |
| --- | --- | --- |
| at cap under length-normalised Eq.(5): `0.0% [0.0, 0.2]` | `farquhar_eq5_lennorm` 0/2000 = 0.0% [0.0%, 0.2%] | ✓ |
| discrete: `14.8% [13.3, 16.4]` | 295/2000 = 14.8% [13.3%, 16.4%] | ✓ |
| top tenth: `20.0% [18.3, 21.8]` vs `27.8% [25.9, 29.8]` | 399/2000 and 556/2000 | ✓ |
| Spearman `0.9892` | 0.9892 | ✓ |
| `K ≥ ⌈N^0.9⌉`, `K ≥ 8`, log 8 = 2.079 > 0.9 log 10 = 2.072 > log 7 = 1.946 | identical | ✓ |
| `58 of 200` correct = `29.0% [23.2, 35.6]` | 29.0%; I recomputed Wilson by hand: [23.15, 35.64] | ✓ |
| `115 of 200` hallucinating = `57.5% [50.6, 64.1]` | 57.5%; hand Wilson: [50.57, 64.15] | ✓ |

**Credit where due:** the paragraph quotes `K ≥ 8` and not `K ≥ 9`, which is exactly what
`cluster_count_bound.md` §3's "Reporting rule" demands ("K >= 9 is ours specifically, and
quoting it as though it were general would repeat the mistake this document exists to
correct"). Standing rule 8 honoured. The claim that this bound was not previously in the
paper is true — `grep` finds `N^{0.9}` and `\lceil` nowhere else in `paper/`.

### Conditions

**(a) — the sharpest one. `methods.tex:88` states unqualified what `limitations.tex:46`
states qualified, and the qualifier is load-bearing.**

> Methods (new): "so every AUROC in this paper stands under Eq.~(5)"
> Limitations (already in HEAD): "Every AUROC in this paper therefore stands under Eq.~(5)
> **as we compute it**" — immediately after disclosing that on raw sequence likelihoods "rank
> agreement with the discrete estimator collapses to $\rho{=}0.38$".

`rescore_likelihoods.md` reports **two** implementations of Eq. (5). Length-normalised gives
ρ = 0.9892; **raw gives ρ = 0.3812**, and `post_overnight_claim_review.md` §4.6 M4 says the
high-ρ consequence is "**true for the length-normalised variant only**". The artifact's own
prose: "length normalisation is the modelling choice that decides the answer... it is why
both variants are reported." Methods reports one variant and draws the general conclusion.
Restore the qualifier, or state ρ for both. This is the one clause I would have BLOCKed had
it not been correctly hedged 40 lines away in the same paper.

**(b) — population label on the n=2000 figures.** The paragraph says "our $2000$ cached
sample sets" and "the same questions" and never names the pool. These are
natural-prevalence figures over 1424 correct + 576 hallucinating
(`cluster_count_bound.md` §5, "Full labelled pool — natural prevalence"). Two hazards:
`27.8%` is *also* the retired attacked-subset pooled top-decile rate (27/97, critique_log 33
§6), and the same paper quotes the fair pool's correct-stratum top-decile at 21.5% six
pages earlier. Critique_log 33 §6 is explicit that "any pooled crowding number is a function
of the class balance you assume". Name it: "our $2000$-question replication pass ($1424$
correct, $576$ hallucinating, natural prevalence)", as Limitations already does at line 22.

**(c) — precision.** `\rho{=}0.9892` against Limitations' `\rho{=}0.99` for the same
statistic. At n=2000 with ρ≈0.99 the standard error is ≈5e-4, so the fourth digit is inside
the noise, and the two sites now disagree cosmetically about the same number. Use 0.99 at
both.

**(d) — the paragraph is a near-duplicate of `limitations.tex:36-48` and drops that
paragraph's caveats.** `post_overnight_claim_review.md` §4.7 L1 required retaining the
artifact's disclosed provenance gaps (top_p, quant type, dtype and model revision unpinned;
the cache stores decoded strings not token ids, so teacher forcing scores the *canonical*
tokenization; 17/20,000 samples retokenise past the generation budget). Limitations does not
carry them either. Now that the claim is bolded in Methods as a main-text result, at least
one of the two sites must.

---

## 3. The N=20 row in `discussion.tex` — **BLOCK**

The facts are right. The inference built on them is not, and it is the inference that makes
the row quotable.

Numbers first, all verified: floor 9.5% [6.2, 14.4] at N=10 and 3.0% [1.4, 6.4] at N=20 match
`n_scaling_grid.md` §1; the empty atom at N=40 I recomputed myself from
`results/n_scaling_ckpt.jsonl` (0/200 correct answers reach ln 40 = 3.6889; the maximum
observed correct score is 3.6196, a gap of 0.069 nats) and 0/200 Wilson = [0.0, 1.88] → 1.9 ✓;
firing points 1 → 4 → 14 ✓ (I initially counted 16 at N=40 before deduplicating tied FPRs —
the artifact counts distinct achievable rates, which is correct, and 14 is right); achieved
5.0% at N=40 = 10/200 ✓; `+2.5 points [-2.5, +7.0]` traces to
`post_overnight_claim_review.md` §3.1 ✓; "every one of the 20 replicates above the direct
estimate" follows from the artifact's stated replicate range 10.0–14.5 against 9.5 ✓.

### Blocker 3.1 — "about $2^{-20}$ under a sign test" is a p-value computed under a null nobody holds, and I measured how wrong it is

> "Every one of the $20$ replicates landed *above* the direct estimate, which is about
> $2^{-20}$ under a sign test: systematic upward bias, not an interval touched at its edge."

The sign-test null being rejected is "the subset-replay distribution's **median equals
9.5%**". That is not in doubt and needs no test: `n_scaling_grid.md` §2 already computes the
subset-averaged ceiling-atom mass **exactly** — 0.120 at k=10 — as a deterministic function
of the recorded verdict matrix. Rejecting a hypothesis the artifact has already settled
arithmetically at p = 2^-20 is dressing a constant in a significance test.

The question that matters is the other one: **is the directly measured 9.5% an unusual draw
from the replay distribution?** I answered it. Reading the C(40,2)=780 verdict bits per target
out of `n_scaling_ckpt.jsonl` and replaying random k-subsets (all-singletons ⟺ the induced
subgraph is edgeless), on the 200 correct answers:

| k | replicates | mean | median | sd | 2.5 / 97.5 pct | min | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 500 | 12.02% | 12.0% | 1.51 pp | 9.0% / 15.0% | 7.0% | 16.0% |
| 20 | 500 | 3.14% | 3.0% | 0.99 pp | 1.5% / 5.0% | 0.5% | 6.0% |

(k=10 mean 12.02% and k=20 mean 3.14% reproduce the artifact's exact §2 curve, 0.120 and
0.031, so the replay is faithfully reimplemented.)

**The direct 9.5% sits at the 3.6th percentile of the replay distribution (6.6% at-or-below),
not beyond it.** Under a null in which 9.5% is a ~5th-percentile draw, the probability that
20 consecutive replicates all land above it is 0.95²⁰ ≈ **0.36** — an ordinary event. The
`2^-20` figure is an artefact of having run 20 replicates rather than 500, and of comparing
them to a fixed constant instead of to their own dispersion. Delete the sign test.

### Blocker 3.2 — the stated bias *direction* is contradicted by the paper's own next sentence, and there is no mechanism for it

> "Replay *over*states the floor, so the true $N{=}20$ floor is probably below $3.0\%$ ...
> the bias runs against our own claim" — followed, two sentences later, by — "the
> direct-versus-replay gap conflates subsetting error with any drift between the two
> generation runs, and we have not run the clean $N{=}10$ pass on the current machine that
> would separate them."

The second sentence removes the licence for the first. `post_overnight_claim_review.md` §3.2
is unambiguous: "Neither component is separately identified." And there is no candidate
mechanism on the subsetting side — a k-subset of an i.i.d. N-draw *is* an i.i.d. k-draw, and
the replay re-runs the identical union-find over the identical pairwise verdicts
(`n_scaling_grid.py` docstring, "REUSE, NOT REIMPLEMENTATION"), so subsetting has no route to
inflate the atom. That leaves drift between the June Week-4 cache and the 2026-08-13 N=40 run
as the live explanation, and under drift the sign of the N=20 error is **unknown**.

Note also that the plan's *pre-registered* bias direction (`n_scaling_plan.md` §5, "the
subset's own clustering is FINER... every entry below is a LOWER bound on the atom") is about
the e_k(c)-over-the-N=10-clustering method, **not** about verdict-matrix replay, and points
the other way. Importing it here would be a second error.

The paper currently says "The direction of that bias is what makes the row quotable." If the
direction is not established, the stated justification for quoting the row is not
established. Either withdraw the direction claim and quote the row purely descriptively
(which the paragraph is already entitled to do — it says load-bearing claims route through
N=40), or state the direction as conditional on the gap being subsetting rather than drift,
and say the condition is untested.

### Blocker 3.3 — the floor sequence reads 9.5 → 3.0 → 0.0, with 0.0% in floor position

> "the ceiling-atom floor falls from $9.5\%$ ... at $N{=}10$ to $3.0\%$ ... at $N{=}20$; at
> $N{=}40$ ... the atom is empty ($0.0\%$ [$0.0$, $1.9$])"

Each clause is individually true, but the parenthetical occupies the slot the other two
floors occupy, so the sentence reads as a floor falling to zero. **The actual smallest
achievable non-zero false-alarm rate at N=40 is 4/200 = 2.0% [0.8, 5.0]** (my recomputation;
see §A below). Given that the paper's entire operating-point thesis is about which
false-alarm rates exist, publishing a sequence whose last term is 0.0% is the one misreading
this paragraph cannot afford. Quote the N=40 floor.

### Also fix while in there (see §B for the ruling)

Point estimate and interval at N=20 are both single-replicate artefacts.

---

## 4. The pre-registration paragraph — **APPROVE WITH CONDITIONS**

Verified against `results/n_scaling_plan.md` §5. Predicted bands 3.5–5.3% at N=20 and
1.2–2.4% at N=40 ✓. The "sits ON the 5% boundary the paper's claim turns on" remark is in the
plan verbatim ✓. The quoted reversal commitment — "if it comes in far below, the finding
becomes 'here is the budget that buys a 5% false-alarm rate'" — is verbatim from the plan ✓.
Measured 3.0% and 0.0% are both strictly below their bands, so **"at or below their predicted
bands" is accurate**, and choosing that phrasing over "inside" was the right call.

### Conditions

**(a) The N=20 half of this paragraph does not disclose that N=20 is a replay.** The
disclosure arrives one paragraph later. A pre-registration was made about what a
*measurement* would show; it is being scored against a replay. Say so in this paragraph, in
four words.

**(b) "the branch that fired is the one that was written down" over-claims on N=20.** The
plan defined two branches, "far above" and "far below". At N=40 (0.0% against 1.2–2.4%) the
branch fired cleanly. At N=20, 3.0% against a 3.5–5.3% band, with the row's own interval
[1.4, 6.4] covering the whole band, is neither far above nor far below — it is a miss inside
the noise. Scope the vindication to N=40, where it is earned.

**(c) The pre-registered *direction of error* did not hold, and the paragraph should say so.**
The plan states in bold that its predictions are LOWER bounds on the atom and therefore
"optimistic about relaxation". Both measurements came in **below** the already-optimistic
bands. So the prediction was wrong twice, in the direction the plan had ruled out. That is a
small, honest, interesting fact and it costs the paper nothing; presenting a two-for-two
band miss as confirmation, and omitting that the stated error direction was itself falsified,
costs credibility if a reviewer opens the plan.

---

## 5. Headline scoping at four sites — **APPROVE WITH CONDITIONS**

All four survive a `grep` for the unscoped form. `main.tex:43` is preceded by "At that
standard $N{=}10$" with a resolvable antecedent one sentence up; `discussion.tex:52` carries
"At $N{=}10$" inline; `introduction.tex:81` and `conclusion.tex:13` use "at that sample
budget", and in both cases the paragraph opens with "At the standard $N{=}10$" / "At $N{=}10$",
so the deixis resolves. No unscoped survivor anywhere in `paper/`.

### Conditions

**(a) `main.tex:44` — "running the same fair pool out to $N{=}40$" has no antecedent, and the
population it names is the wrong one.** The only population the Abstract has introduced at
that point is "$1424$ clean correct answers", which is the superset, **not** the fair pool.
The fair pool (400 items; 200 correct) is never introduced in the Abstract. So "the same"
points at nothing, and points at it across a population boundary the paper spends two
sections keeping apart. This is a population error in the Abstract — the exact site class of
critique_log 31's "population sites four AND five". Write "running the fair pool's $200$
correct answers out to $N{=}40$", as `introduction.tex:82` correctly does.

**(b) "at an achieved $5.0\%$" is quoted bare at three sites** (`main.tex:45`,
`introduction.tex:83-84`, `discussion.tex:142`) and "a $5\%$ operating point exists" bare at a
fourth (`conclusion.tex:22`). It is 10/200 on the fair pool's correct stratum; Wilson
**[2.7%, 9.0%]**. The paper excludes a 5% budget at N=10 by insisting on a Wilson *lower*
bound (6.2% and 9.0%); it cannot then concede the point at N=40 without an interval and stay
symmetric. Charter rubric 4 requires an interval on every reported number. Attach it at least
in the Discussion, and prefer "an achieved $5.0\%$ on the fair pool's $200$ correct answers".

**(c) `conclusion.tex:21-22` — "the cap carries no mass at all" is an unqualified absence
claim from a zero count.** Discussion states the same fact correctly as "$0.0\%$ [$0.0$,
$1.9$]". Conclusion should not be the looser of the two. (This is not the "accepting a null
from an overlapping interval" error — the analytic argument does most of the work here — but
it is the same reflex.)

---

## A. Is `results/n_scaling_grid.md` §1 wrong about the N=40 floor? — **CONFIRMED, and a paper claim depends on it**

Yes, and I found the line that does it. `scripts/n_scaling_grid.py:1517-1521`:

```python
k_cap, n_cap = ceiling_atom(neg, b)
nxt = f"{firing[1]['fpr']:.1%}" if len(firing) > 1 else "-"
log(f"| {b} | {src} | {len(neg)} | {fmt_prop(k_cap, n_cap)} | {nxt} | ...")
```

The column headed **"floor = min non-zero FPR"** is filled with `ceiling_atom(...)`, and the
column headed **"next FPR"** is filled with `firing[1]` — the *second* firing point. At N=10
and N=20 the at-cap mass *is* `firing[0]`, so the row is coherent by coincidence. At N=40 the
at-cap mass is 0/200, which is not a firing point at all, so `firing[0]` is printed nowhere
and the row silently skips it.

I recomputed the grid from `results/n_scaling_ckpt.jsonl` (200 correct, 200 hallucinating,
n_samples=40, CPU only):

| τ | FP | FPR | TP | TPR |
| --- | --- | --- | --- | --- |
| 3.6196 | 4 | **2.00%** | 12 | 6.00% |
| 3.6065 | 5 | 2.50% | 13 | 6.50% |
| 3.5718 | 8 | 4.00% | 16 | 8.00% |
| 3.5156 | 10 | 5.00% | 22 | 11.00% |

So the first firing point at N=40 is **4/200 = 2.0% [0.8, 5.0]** (Wilson, hand-checked), and
the artifact's "next FPR = 2.5%" is the *second*. Independently corroborated by the same
report's own §3 (`40 | 1% | ... | closest achieved 2.0% over budget | TPR 6.0%`) and by
`post_overnight_claim_review.md` line 246, which already writes "the achievable floor falls
to $2.0\%$ [$0.8$, $5.0$]". Two committed artifacts already contain the right number; §1 is
the outlier.

**Does a paper number depend on it? Yes — Blocker 3.3.** No *quantity* in the paper is
literally wrong, but `discussion.tex:136-139` reproduces the artifact's row structure and so
reproduces its implication: a floor sequence terminating at 0.0%. Fix the artifact
(`floor` column should print `firing[0]` and the at-cap mass should get its own column) and
add 2.0% [0.8, 5.0] to the Discussion. Also worth noting the two are close: the N=40 floor's
interval upper bound (5.0%) touches the conceded 5% operating point exactly, which is a more
interesting sentence than the one the paper currently writes.

---

## B. Is the N=20 interval `[1.4, 6.4]` understated? — **CONFIRMED, and the point estimate is affected too**

`post_overnight_claim_review.md` §3.3 says it outright: "That is a Wilson interval on
replicate 0 only; it carries target-sampling variance and not subset-choice variance. With
both components: **median 2.75%, [0.5%, 5.5%]**, replicate range [1.5%, 4.0%]. Every replayed
row in that report has the same defect."

I measured the missing component rather than taking that on trust. Over 500 independent
20-subset replays of the N=40 verdict matrix on the fair pool's 200 correct answers: mean
3.14%, median 3.0%, **sd 0.99 pp**, 2.5/97.5 percentiles [1.5%, 5.0%], full range
[0.5%, 6.0%]. Subset-choice dispersion alone is therefore comparable in magnitude to the
Wilson half-width the paper currently quotes as the whole uncertainty.

**Ruling: the paper must not quote `3.0% [1.4, 6.4]`.** And the fix is not only the interval —
`3.0%` is itself replicate 0, i.e. a number that would change if the script were re-run with a
different seed, which is standing rule 3 ("a statistic that moves while you type it").
Preferred repair, in order:

1. **Best:** quote the artifact's own §2 value, **3.1%**, which is the *exact* subset-averaged
   ceiling-atom mass — deterministic, seed-free, and already committed
   (`n_scaling_grid.md` §2, correct row, k=20 = 0.031). My MC reproduces it to 0.0004.
   Pair it with a bootstrap over targets *and* subset draws.
2. **Acceptable:** quote `post_overnight_claim_review.md`'s combined figure, median 2.75%
   [0.5%, 5.5%], and cite it.
3. **Minimum:** keep 3.0% but state it is one replicate and that the interval omits
   subset-choice variance.

Note the wider interval is not merely wider — it is *shifted down* (2.75/3.1 vs 3.0; upper
5.5 vs 6.4). Adopting it slightly strengthens the concession, so there is no self-interest
argument for keeping the narrow one.

The same defect infects "firing points ... **four** ... at $N{=}20$" in the same sentence
(`discussion.tex:140-141`) — `n_scaling_grid.md` §1 labels the whole N=20 row "replay of
N=40, replicate 0". If the 3.0% is re-derived, re-derive the 4 with it.

---

## C. Tests and guards

```
pytest -q  ->  3 failed, 717 passed, 1 skipped, 1 warning in 10.67s
```

**The failure set is identical to the stated baseline.** All three failures are in
`tests/test_operational_provenance.py`, all three fire on `scripts/overnight_2026_08_14.sh`:
`test_the_open_sites_are_exactly_the_pinned_ones`,
`test_the_guard_is_currently_red_and_that_is_the_finding`,
`test_the_ratchet_baselines_match_the_repo_today` (`ratchet drift:
[('scripts/overnight_2026_08_14.sh', 'untagged', '')]`). No paper-related test fails, and no
test asserts against `paper/` content, so the suite is not evidence for or against this diff.

*Bookkeeping discrepancy, non-blocking:* passes are 717 against the stated baseline of 704.
The only new test file in the tree is untracked `tests/test_progress_monitor.py`, which
contributes 42. 704 + 42 = 746 ≠ 717, so the 704 baseline is not reproducible from this
working tree — presumably taken mid-session. Flagging so nobody later reads the delta as a
regression.

**`scripts/check_population_labels.py`** — `OK (8 files, 12 rules, 60 number patterns, 11
superseded-run patterns, 15 growing-cell patterns over 7 frozen counts)`, exit 0. As
established in item 1, this OK is vacuous on the winner's-curse numbers, and it is also silent
on 5.0%, 2.0%, 3.0%, 14.8%, 20.0% and 27.8%, none of which are guarded. It caught nothing here
and could not have.

**`scripts/check_operational_provenance.py`** — exit 1, 28 problems, **none in `paper/`**.
The set is the known dead-cost-anchor backlog (`~67 GPU-h`, `228 GPU-h`, `73.9 s/eval`,
`2.8 s`, `55 s`, `6.1 s`) across `docs/START_HERE_overnight.md`, `docs/definitive_run_plan.md`,
`results/derived_paper_quantities.md`, `results/judge_owed_conditions.md`,
`results/n_scaling_plan.md`, `results/null_control_cost_options.md`,
`results/null_objective_ablation_plan.md`, `results/power_under_ceiling.md`,
`scripts/overnight_2026_08_13.sh`, plus the untagged trio in
`scripts/overnight_2026_08_14.sh`. Also three stale-countdown hits ("33 days to 2026-09-15;
it is 27 today") — the checker's arithmetic is right for 2026-08-19. Pre-existing; not this
diff's problem.

---

## D. Smaller things, for the punchlist

- **D1.** The Abstract is now **~247 words**, up from ~216 at HEAD, against the in-file
  comment "% ~200 words (critic gate, 2026-08-13)". The comment is now false about its own
  file. Either trim or update the comment; a file asserting a stale fact about itself is a
  documented failure mode here.
- **D2. Value collision:** `discussion.tex:164` writes "a $12.0\%$ median over $20$ subset
  replays" on the fair pool's correct stratum. `results/fair_pool_granularity.md:119` records
  a different `12.0% [8.2%, 17.2%]` for the *same* population — the share of that stratum at
  the lattice point 2.1640. The paper's phrasing disambiguates, so this is a watch item, not a
  defect; the population linter is structurally unable to see it (same pool, same digits,
  different quantity).
- **D3.** `discussion.tex:177-184` drops the retired clause "and it is not evidence about the grid
  either way" from the N=20 pilot sentence. Correct to drop now that the grid is measured; no
  action.
- **D4.** `introduction.tex:89-91` scopes the identity to "at $N{=}10$ it does, and at $N{=}40$
  it does not" and omits N=20, where the cap does still carry mass (3.0%).
  `post_overnight_claim_review.md` §4.5 N2 recommended naming all three. Cosmetic.
- **D5.** `methods.tex:105` forward-references `Section~\ref{sec:limitations}`, which exists
  (`limitations.tex:3`). ✓ `sec:discussion` and `sec:experiments` likewise resolve. No broken
  refs introduced. Not compile-tested — no LaTeX toolchain checked in this session.

---

## E. What I would need to see to clear the BLOCK

1. `discussion.tex` — delete the `$2^{-20}$` sign test (Blocker 3.1).
2. `discussion.tex` — withdraw or condition "Replay *over*states the floor... the bias runs
   against our own claim", since the paper's own next sentence says the gap is not identified
   (Blocker 3.2).
3. `discussion.tex` — quote the N=40 first firing point, 2.0% [0.8, 5.0], so the floor
   sequence does not terminate at 0.0% (Blocker 3.3 / §A).
4. `discussion.tex` — replace the replicate-0 N=20 pair with the subset-averaged 3.1% (or
   2.75% [0.5, 5.5]) and re-derive the "four" firing points with it (§B).

Conditions under items 2, 4 and 5 are not blockers but should land in the same pass; 2(a) —
the unqualified "every AUROC stands under Eq.~(5)" — is the one I would most expect a hostile
reviewer to find, because the refutation is 40 lines away in the same paper.

*Not done, deliberately:* nothing in `paper/`, `scripts/` or `docs/` was modified; no GPU work
was run; `null_control.py` (PID 473) was not touched. All recomputation in §A and §B was
pure-CPU replay of committed checkpoints in a scratch directory.
