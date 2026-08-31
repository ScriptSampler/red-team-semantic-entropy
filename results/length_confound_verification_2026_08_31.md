# Independent verification of `results/length_confound_probe.md` (2026-08-31)

Verifying the analysis rescued in `6fbec9a`, written 2026-08-13, never reviewed.
**Nothing in `paper/` was changed.** Section 6 proposes edits; it does not apply them.

## 0. How this was verified

Re-derived from the cache and the source, **not** by running the probe scripts. The probe
scripts were run afterwards, once, as a cross-check, and every place that happened is
labelled.

- Cache: `~/.cache/se-research/samples/wk4_full_2000q/{samples,entropy,relabeled}.jsonl`
  and `attacks/wk9_defb/triviaqa_se_false_alarm.jsonl`, on the **WSL** filesystem
  (there is no Windows-side copy). Copied read-only to a scratch dir; originals untouched.
- Interpreter `.venv/Scripts/python.exe`. AUROC from `sklearn.metrics.roc_auc_score`,
  Spearman from `scipy.stats.spearmanr` — independent implementations of the same
  estimands, not the probe's hand-rolled `auroc`/`spearman`.
- `se.attacks.select._stratum_ids` was re-implemented from the source rather than imported
  (`se.scoring` pulls `se.data` -> `datasets` -> `pandas`, which does not import in this
  venv). `normalize_answer` was transcribed verbatim from `src/se/scoring.py:49-57` and the
  transcription was diffed against the file.
- **No GPU work. Nothing was launched.** Total cost: CPU only.

Cache sanity, established first: 2000 records in each of the three files, perfect id
intersection, exactly 10 samples per question, `entropy_nats` bit-identical between
`entropy.jsonl` and `relabeled.jsonl`, and `1424` correct / `576` hallucinating under the
span oracle. (`greedy_correct` disagrees between the two files on 20 questions — that is the
B3 relabel, and everything below uses `relabeled.jsonl`, as the paper's own scripts do.)

## 1. Verdicts

| # | claim | verdict | confidence |
|---|---|---|---|
| 1 | Length baseline 0.634 fair / 0.631 full; SE 0.704 / 0.694; paired deltas +0.0698 [+0.0236, +0.1193] and +0.0627 [+0.0407, +0.0860] | **CONFIRMED** — every figure to 4 dp | very high |
| 1b | The fair pool is the population the paper's 0.704 is measured on | **CONFIRMED** — reproduces the published CI exactly | very high |
| 2a | Repo pairs bare answer strings at `src/se/entropy.py:41` | **CONFIRMED** | very high |
| 2a | Kuhn/Farquhar concatenate the question before the NLI call | **UNVERIFIABLE FROM THE REPOSITORY** (corroborated externally — see §3.2) | see §3.2 |
| 2b | Repo: `max_new_tokens=48`, no brevity instruction, 19.6 words, 25.4% cap-truncated | **CONFIRMED** | very high |
| 2b | Source setting yields answers averaging **~15 characters**, so this repo is "roughly an order of magnitude longer" | **REFUTED** (see §3.3) | high |
| 3 | Separation survives length control: 0.6439 / 0.6375 / 0.6373 at 5/10/20 bins; 0.6559 fair at 5 | **CONFIRMED**, and the stratification is done correctly | very high |
| 4 | Exact-match on first-sentence text reaches 0.7625 full / 0.7918 fair, beating the deployed NLI clusterer | **CONFIRMED** | very high |
| 4b | It does not contradict `methods.tex` "exact-match saturates" | **CONFIRMED** in substance; the line reference is stale | high |
| 4c | "A meaningful share of the 0.694-vs-0.828 gap is plausibly the generation regime" | **NOT SUPPORTED** — see §3.4 | — |
| 5 | Spearman corr(mean length, K) = +0.666; split-rate-by-length gradient | **CONFIRMED** to 4 dp | very high |
| 6 | The attack-side length question "cannot be answered from cache" | **PARTLY REFUTED** — the cache licenses more than the report claims (§4.2) | high |

## 2. Claim-by-claim detail

### 2.1 Claim 1 — the length baseline. CONFIRMED.

First, the population. `scripts/fair_pool_check.py` builds the fair pool through
`campaign_pool -> select_stratified -> _stratum_ids`, `N=200` per stratum, `SEED=0`,
reading `greedy_correct` from `relabeled.jsonl` and never any score. Re-implementing that
rule gives 400 ids. Scored the way `fair_pool_check._clean_auroc` scores them — wrong
stratum first, `relabeled.jsonl` entropies, `n_boot=3000`, `seed=0`:

```
0.7043 [0.6525, 0.7526]      the paper publishes 0.704 [0.653, 0.753]
```

That is an exact reproduction, including both interval endpoints. (Building the same 400
questions in right-first order gives the same point estimate and [0.6553, 0.7546]; the
bootstrap index stream depends on array order. The probe's convention — `entropy.jsonl`
scores, `n_boot=2000` — gives 0.7043 [0.6567, 0.7546], which is what the probe reported.)
The 80 false-alarm targets in `wk9_defb` are exactly the first 80 of the right stratum, which
independently confirms `experiments.tex:70`'s "prefix of the fair pool's 200 correct answers".

So the length baseline is being compared against the paper's own number on the paper's own
population. Now the numbers:

| | full pool (n=2000) | fair pool (n=400) |
|---|---|---|
| semantic entropy | **0.6937** [0.6695, 0.7172] | **0.7043** [0.6567, 0.7546] |
| mean generation length alone | **0.6311** [0.6065, 0.6567] | **0.6344** [0.5795, 0.6879] |
| paired delta (SE − length), observed | **+0.0626** | **+0.0699** |
| paired delta, bootstrap CI | **[+0.0407, +0.0860]** | **[+0.0236, +0.1193]** |

Every figure the report gives. The deltas are stable across bootstrap seeds 0/1/7
(full: [+0.0407,+0.0860], [+0.0400,+0.0851], [+0.0398,+0.0852]). Because the fair pool is a
200/200 *stratified* design, I also ran a stratified paired bootstrap that resamples within
strata: **+0.0699 [+0.0233, +0.1155]** — the same answer. Mean words per sample is 18.76 in
the correct stratum against 21.63 in the hallucinating stratum, a gap of +2.87 words.

**So SE does significantly beat the trivial length heuristic, on both pools.** The paper is
not in trouble. But the margin is 7 AUROC points on the pool the headline is quoted on, and
a length baseline that scores 0.634 is not something a referee will let pass unstated.

**One thing the report did not test, which strengthens the paper's hand.** If length were
carrying signal SE misses, combining them would beat SE. It does not. A rank-sum of SE and
mean length scores 0.6772 on the full pool against SE's 0.6937 — **−0.0164 [−0.0286,
−0.0053], significantly worse**; on the fair pool −0.0183 [−0.0436, +0.0058]. And the rank
residual (SE minus length) still separates at 0.571. Length is a degraded proxy for what SE
measures, not a complementary signal. That is the sentence that makes the disclosure safe to
publish.

### 2.2 Claim 2a — question-conditioning. Repo side confirmed; source side out of scope for the repo.

`src/se/entropy.py:41` is exactly as quoted:

```python
pairs = [(samples[i], samples[j]) for i, j in combinations(range(n), 2)]
```

Stronger than the report says: `cluster_samples(samples, nli, batch_size)` has **no
question parameter at all**, and `NLI.bidirectional_equivalent_batch` (`src/se/nli.py:83-97`)
just flattens the pairs both ways. Question-conditioning is not merely omitted, it is
structurally unreachable from this call path. `methods.tex:7-9` describes the clustering as
"$y_i$ and $y_j$ share a cluster iff each entails the other under the NLI model", which
matches the code.

**On what the source method does, the repository contains no evidence.** The `annote` fields
for `kuhn2023semantic` and `farquhar2024detecting` in `paper/related_work.bib` are both
marked "verified against the full text 2026-08-13", but both are about the *estimator*
(Eq. 4 vs Eq. 5 vs discrete) and neither mentions entailment input construction. There is no
local PDF or extract of either paper. A repo-wide grep for "concatenat" finds exactly one
hit outside vendored code: the probe report itself. **On the repository's evidence alone this
claim is UNVERIFIABLE and must not be asserted.** See §3.2 for an external check.

### 2.3 Claim 2b — the generation configuration. Repo side confirmed exactly.

- `src/se/config.py:34-38`: `max_new_tokens: int = 48`, pinned across conditions, citing
  "external review §7". `manifest.json` of the wk4 cache records `max_new_tokens: 48`.
- `src/se/model.py:68-74`: the prompt is `[{"role": "user", "content": question}]` through
  the Llama 3.1 chat template. **No system message, no brevity instruction, no few-shot
  exemplars, no answer-extraction step.** `generate_samples` decodes the raw continuation and
  `.strip()`s it. That is the whole of it.
- Measured on the cache: **19.59 words** and **113.7 characters** per sample (median 17 words
  / 95 chars, p90 36 words, max 46 words).
- Cap-truncation: under the probe's own predicate (`[.!?]["')\]]*\s*$` absent) **5071/20000 =
  25.36%**, i.e. the report's 25.4%, reproduced exactly. Under a stricter last-character test
  it is 23.4%, under a looser one 28.4%; the phenomenon is robust to the predicate.

The report's "**19.6 words**", "**~110 characters**", "**a quarter of them cut mid-sentence**"
are all correct.

### 2.4 Claim 3 — the separation survives length control. CONFIRMED, and correctly done.

Questions binned by quantiles of mean sample length; AUROC computed only within a bin and
pooled over concordant pairs:

| bins | full pool | | fair pool |
|---|---|---|---|
| 2 | 0.6572 | | — |
| 5 | **0.6439** | | **0.6559** |
| 10 | **0.6375** | | 0.6489 |
| 20 | **0.6373** | | — |
| 40 | 0.6313 | | — |
| unstratified | 0.6937 | | 0.7043 |

Exactly the report's figures, and the sequence converges to ~0.63 rather than drifting, which
is what you want to see.

I ran two cross-checks the report did not, to confirm the stratification actually controls
what it claims to:

- **Stratify the length detector by length.** It should collapse to chance. It does:
  0.5454 at 5 bins, 0.5063 at 10, **0.5016 at 20**. So by 20 bins the control has removed
  essentially all of the length signal — and SE still scores 0.6373 there.
- **Stratify SE by a random variable.** It should return the unstratified number. It does:
  0.6914 at 5 bins, 0.6945 at 20.

The stratified AUROC means what the report says it means. **The separation is not a length
artefact.**

Two things worth carrying forward that the report did not surface. The per-bin AUROCs are
very uneven — 0.7952 in the shortest quintile against 0.6155–0.6354 in the other four — and
the hallucination rate itself climbs steeply with length:

| mean words | n | hallucination rate |
|---|---|---|
| [1.40, 13.50) | 392 | 9.9% |
| [13.50, 17.36) | 408 | 26.5% |
| [17.36, 21.10) | 396 | 34.1% |
| [21.10, 25.40) | 401 | 36.7% |
| [25.40, 40.90) | 403 | 36.5% |

That gradient is the confound stated in its plainest form, and it is the single most useful
number to put in the paper alongside the baseline.

The K>=8 gap survives in every band, exactly as reported: **+20.5%, +13.1%, +16.7%, +22.6%,
+17.3%**.

### 2.5 Claim 4 — verbosity depresses rather than inflates. CONFIRMED.

| detector | full pool | fair pool |
|---|---|---|
| NLI clusterer, full text (deployed) | 0.6937 | 0.7043 |
| exact-match, full text | 0.7240 (+0.0297 [+0.0083, +0.0503]) | 0.7579 (+0.0536 [+0.0137, +0.0957]) |
| **exact-match, first sentence** | **0.7625** (+0.0683 [+0.0453, +0.0900]) | **0.7918** (+0.0875 [+0.0468, +0.1322]) |
| exact-match, first 10 words | 0.7563 | 0.7869 |
| exact-match, first 5 words | 0.7265 | 0.7546 (interval covers zero) |

**0.7625 and 0.7918 reproduce to the digit.** The result is robust to the choice of
normaliser: substituting the probe's own cheap `norm()` for `se.scoring.normalize_answer`
moves it to 0.7607 / 0.7886, same ordering, same significance.

The report's caveats both hold. Exact-match genuinely does saturate — 52.55% of questions sit
at K=10 on full text — and it still out-ranks the NLI clusterer, which is the point. First-
sentence truncation *reduces* saturation to 43.35% (10-word truncation to 29.05%), against
the NLI clusterer's 14.75%. And the length gap does survive first-sentence truncation (+2.89
words) while collapsing under a hard word cap (+0.29 at 10 words, +0.02 at 5), exactly as
reported.

**Provenance defect, worth fixing.** The committed `length_confound_probe4.py` does **not**
reproduce the report's table: run today it prints 0.7215 / 0.7610 / 0.7552 (full) and
0.7528 / 0.7884 / 0.7841 (fair). The report's figures are the *tie-corrected* ones — round
the scores to 12 dp before the AUROC and you get 0.7240 / 0.7625 and 0.7579 / 0.7918 on the
nose. So the report's numbers are the better ones, and the scripts shipped with it are not
the scripts that produced them. Anyone re-running the committed code to check the report will
find a mismatch and not know why. See §4.1.

### 2.6 Claim 5 — the correlation and the gradients. CONFIRMED.

Spearman corr(mean length, K) = **+0.6662** (report: +0.666); +0.6817 within the correct
stratum, +0.5614 within the hallucinating stratum, +0.6536 on the fair pool. Spearman
corr(mean length, SE entropy) = +0.6578.

Reproduction and gradients, all exact:

| | reported | verified |
|---|---|---|
| whole-pool split rate | 32,957/51,914 = 0.635 | 0.6348 [0.631, 0.639] |
| FA-80 split rate | 1,826/2,748 = 0.664 | 0.6645 [0.647, 0.682] |
| split by max(words) 0-9 / 10-19 / 20-29 / 30-39 / 40+ | .157 / .447 / .818 / .926 / .948 | .1572 / .4466 / .8178 / .9262 / .9476 |
| by truncation, neither / one / both (n=35,415 / 12,557 / 3,942) | .522 / .874 / .888 | .5218 / .8743 / .8879 |
| identical text after normalisation | 0.002 (n=6,540) | 0.0013 (n=6,801 under the repo normaliser) |
| by gold length 1 / 2 / 3+ words | .611 / — / .696 | .6109 / .6560 / .6960 |

The report's cross-references also check out: `results/wk3_wed_nli_check.md` row 14 is
exactly the failure mode described ("additional consistent detail", expected equivalent,
neutral 0.00 one way / entailment 1.00 the other) at 11/16 hand-crafted accuracy, and
`docs/critic_charter.md:40` is about length *consistency across conditions*, which is a
different concern from length being confounded with the label.

## 3. Where the report is wrong, overstated, or now stale

### 3.1 Its line references into `paper/` are stale, and one of them misdescribes today's text

The paper has moved a long way since 2026-08-13.

- **`methods.tex:293`** is quoted as "exact-match saturates". Today line 293 is about
  $\delta$ headroom on the lattice. The "exact-match saturates" text is now
  **`methods.tex:363`**. The report's *substance* is right — that passage is about exact-match
  as an adjudicator of attack-induced change, not as a clean detector — but the pointer is wrong.
- **`limitations.tex:117-123`** is quoted as reporting SE at 0.694 against 0.828. Today that
  range is the winner's-curse retention paragraph (`44% [23%, 64%]`). The 0.694-vs-0.828
  discussion now lives at **`limitations.tex:240-244`** and **`experiments.tex:40-48`**.
- **`experiments.tex:9`** is quoted for "N=10 answers at temperature 1.0". That was correct on
  2026-08-13 (verified by checking out the last commit before 2026-08-14); it is now line 34.

### 3.2 The source-method claims cannot be settled inside this repository

Stated plainly, as required: **nothing in the repository establishes what Kuhn et al. or
Farquhar et al. do.** The report's quotation is not sourced to any artefact in the repo.

Because a wrong claim about a cited method would be worse than a missing one, I checked
externally. **This is not repository evidence and it is not the standard the brief set, so
treat it as a lead to confirm against the PDFs before it goes anywhere near the paper.**
Two independent retrievals:

- Farquhar et al., *Nature* 630 (2024), full text at PMC11186750, Methods, "Detecting
  confabulations in QA and math", entailment estimator: *"We template more simply, checking if
  DeBERTa predicts entailment between the concatenation of the question and one answer and the
  concatenation of the question and another answer."*
- Kuhn et al., arXiv:2302.09664 (ar5iv rendering): *"For each pair of sequences in our set of
  samples, s and s', we detect whether it is possible to infer the concatenation of the context
  and s from the concatenation of the context and s' and vice versa. To do this we concatenate
  each of the two question/answer pairs, and then concatenate them both together separated by a
  special token."*

Both corroborate the report's claim, and the second is close to word-for-word what the report
quotes. I did not obtain a raw text dump — these came through a summarising fetch, and one of
my four retrievals mis-attributed a paragraph, so a human read of the two PDFs is owed before
this is asserted in print. Caveat that survives even then: Kuhn's sentence appears in the
description of the general algorithm, and Farquhar's "we template more simply" sits in a
subsection contrasting the DeBERTa estimator with an LLM-prompted one — check the scope of
each before writing "the source method conditions on the question" without qualification.

### 3.3 The "~15 characters / an order of magnitude" claim is REFUTED

This is the report's most rhetorically forceful sentence and it does not hold. The same
external check gives, for Farquhar et al.'s main setting — the one that covers TriviaQA:

- prompt: *"Answer the following question in a single brief but complete sentence. Question:
  {question} Answer:"*
- length: *"sentence-length answers (96 ± 70 characters, mean ± s.d.)"*, covering TriviaQA,
  SQuAD, BioASQ, NQ-Open and SVAMP.

This repo's cached samples average **113.7 characters**. That is about **1.2x**, well inside
one standard deviation of the source distribution — **not an order of magnitude**. I could
find no support anywhere for "~15 characters"; it is plausibly the short-phrase supplementary
setting, or Kuhn et al.'s 10-shot `Q:/A:` format, but neither is what the report cites and
neither has a character count I could verify.

What survives, and is still worth disclosing:

- the source prompts for brevity and this repo issues no instruction at all;
- the source (per Kuhn) trims by stop-word pattern-matching rather than a hard token budget,
  whereas this repo hard-caps at 48 new tokens and **25.4% of samples end mid-sentence**.

The truncation is the real deviation. The mean length is not.

### 3.4 The bearing on the 0.828 gap is weaker than the report suggests

Two corrections. First, **0.828 is not Farquhar et al.'s number.** `results/replication_results.md:38`
records it as *Tong et al.* (the SRE paper, arXiv:2509.17445) reporting SE on TriviaQA
no-context for Llama-3-8B, and `limitations.tex:237-242` sits inside the "SRE fidelity" paragraph.
I have no evidence at all about Tong et al.'s generation configuration. Second, given §3.3,
"restore short answers" is not obviously the lever: this repo's answers are already comparable
in length to Farquhar's.

So the report's closing move in its §5 — "a meaningful share of that gap is plausibly the
generation regime" — is speculation that the evidence does not carry, and the paper's existing
refusal to attribute the gap (`experiments.tex:46-48`, "we have not run the ablation that would
separate the two") is the better position. **Do not weaken it on the strength of this finding.**

### 3.5 "Not disclosed anywhere" is no longer true of the token budget

The report's §7 says the 48-token cap "is not stated in the paper at all". That was correct on
2026-08-13 (checked against the tree at the last pre-2026-08-14 commit). It is **not correct
today**: `limitations.tex:61-62` now says the manifest "pins the model id, 4-bit loading, the
sample count, temperature 1.0, **a 48-token generation budget**, the seed and the split", and
`limitations.tex:84-85` already discusses terminal-punctuation rates across runs.

Still undisclosed today, confirmed by grep over `paper/sections/*.tex` and `paper/main.tex`:
the prompt format (no hits for brevity, prompt template, zero-shot or few-shot), the mean
generation length, the truncated share, the absence of question-conditioning, and the length
baseline.

## 4. Findings not in the report

### 4.1 The cached entropies carry floating-point tie noise

`methods.tex:289` states that at N=10 the discrete entropy is confined to **39** attainable
values. The 2000-question cache contains **52 distinct `entropy_nats` values**. Rounding to
12 decimals collapses them to 35 (<= 39, consistent), and the maximum spread inside a
rounded group is **4.4e-16**. The cause is `discrete_entropy` summing `-p log p` in `Counter`
insertion order, which depends on which cluster id appears first — so mathematically tied
scores are not bit-equal, and AUROC breaks ties that ought to be tied.

Size of the effect: **none at the precision anything is quoted to.** Full-pool SE moves
0.6937 -> 0.6943 (both round to the published 0.694); the fair pool's 0.7043 does not move at
all; the tie-corrected paired delta against length is +0.0632 [+0.0413, +0.0866] full and
+0.0699 [+0.0236, +0.1195] fair. **No paper number changes.**

One thing to check, though, since this paper leans hard on the lattice: among the 80
false-alarm targets, `entropy_before == log(10)` exactly is true for **0** of them, while
`|entropy_before - log(10)| < 1e-12` is true for **8** — which is the count `methods.tex:294`
publishes ("8 at the ceiling, 13 one point below", and I confirm 13 at 2.163956). The
published counts are right, but only because whatever computes them uses a tolerance. Any
tie-sensitive code path that uses exact equality would silently return zero. Worth a
one-line assertion in the tie machinery rather than a paper edit.

### 4.2 The attack cell licenses more than the report says, and it points the wrong way

The report parks the attack-side length question as unanswerable because "the attack cells
store scores, not the attacked generations". That is only three-quarters true.
`src/se/attacks/harness.py:158-169` stores **`answer_under_q_prime`, one greedy answer
generated under q'** at the pinned decode — populated whenever `entropy_and_feasible` is
true, which is **48 of the 80** false-alarm targets. On those 48:

| | |
|---|---|
| benign greedy answer | 15.35 words |
| greedy answer under q' | **19.40 words** |
| paired change | **+4.04 words** (median +1.0) |
| share where the answer got longer | **66.7%** |
| mean entropy move | +0.8430 nats |
| Spearman(length change, entropy move) | +0.0434 |
| Spearman(length under q', entropy_after) | +0.3730 |

The attacked generations **are** longer, on the subset where the attack moved entropy. That is
the direction of the worry, and it is the opposite of the reassuring sign the report reads off
`corr(benign length, entropy move) = -0.252` (which I reproduce exactly, n=80, and which is
-0.2858 on these 48).

Three things bound it, and none of them dissolves it: the 48 are *selected* on the attack
having worked, so this is conditional on success; a single greedy answer is not the ten
temperature-1.0 samples `entropy_after` is actually computed from; and within the subset there
is no dose-response (+0.04). Note also that q' is itself longer than q (+2.31 words paired),
which is a plausible common cause.

**This raises rather than lowers the value of the ~20 GPU-min re-generation costed in the
report's §6, and I would recommend running it** — it is now testing a hypothesis with
supporting cache evidence rather than a bare possibility, and it is the only item here that
could move an attack claim. Per the brief, **it was not launched.**

### 4.3 The length signal is subsumed, not complementary

Reported above in §2.1 and repeated here because it is the load-bearing reassurance: adding
length to SE makes the detector significantly **worse** (-0.0164 [-0.0286, -0.0053] full
pool). Whatever the length confound is doing, it is not hiding signal the paper is failing to
use.

## 5. What this does and does not do to the paper

Nothing here retracts anything. Specifically:

- **Clean AUROC 0.704 on the fair pool — stands.** Reproduced exactly, on a pool proven to be
  the same one, surviving length stratification at 0.656 and beating a length baseline by
  +0.0699 [+0.0236, +0.1193].
- **The ceiling / lattice / achievable-floor results — untouched.** They are arithmetic on the
  score's support and do not depend on what drives cluster granularity. §4.1 is a hygiene note,
  not a defect.
- **Cluster-count bound — stands**, with the qualification the report already gives: the *level*
  of K is strongly length-dependent (Spearman +0.666), so the empirical K distribution the bound
  is applied to is a property of the 48-token setting. The K>=8 gap itself survives in all five
  length bands.
- **Attack claims — one open item**, now with weak cache evidence pointing toward a length
  component (§4.2), and a cheap measurement that would settle it.
- **The 0.694-vs-0.828 gap — do not touch.** §3.4.

The exposure is not a wrong claim. It is that the paper's entire thesis is a
measurement-validity critique of semantic entropy, and it currently evaluates an undisclosed
variant of the method: no question-conditioning in the clusterer, and a generation regime the
source method does not use. A referee who notices that will ask why a paper about measurement
validity did not audit its own construct, and "our numbers were right" will not be a
sufficient answer. The two disclosures cost nothing and remove the whole attack surface.

## 6. Proposed edits — NOT APPLIED

All line numbers are against HEAD `6fbec9a`. Nothing in `paper/` was modified.

### 6.1 Add the length baseline where the 0.704 is characterised

**Where:** `experiments.tex`, immediately after line 59 ("...scores AUROC $0.704$ [$0.653$,
$0.753$], against the $1.0$ that score-dependent selection manufactures by construction").
This is the right site because the sentence is already making a "compared to what" argument.

**What to say** (numbers only; wording is the author's):

> A trivial baseline bounds this from below. Mean generation length alone, used as a
> hallucination score, reaches AUROC $0.634$ [$0.580$, $0.688$] on the same fair pool and
> $0.631$ [$0.607$, $0.657$] on the full labelled pool. Semantic entropy beats it on both,
> by $+0.070$ [$+0.024$, $+0.119$] and $+0.063$ [$+0.041$, $+0.086$] under a paired bootstrap
> that resamples questions jointly. Length is not a complementary signal: a rank-sum of the two
> scores is worse than semantic entropy alone ($-0.016$ [$-0.029$, $-0.005$] on the full pool).
> Controlling for length directly, by comparing correct against hallucinating answers only
> within length bins, leaves AUROC at $0.656$ on the fair pool and $0.644/0.638/0.637$ at
> $5$/$10$/$20$ bins on the full pool.

Also worth one clause somewhere in the same paragraph: on this cache the hallucination rate
rises from $9.9\%$ in the shortest length quintile to $36.5\%$ in the longest, which is why
the baseline is not near chance.

**Do not** put this in Limitations. It is a strengthening result — SE wins — and burying a
result that favours the paper in the limitations section reads as hedging.

### 6.2 Disclose both deviations, in Methods, not Limitations

**Where:** `methods.tex`, in or adjacent to the clustering description at lines 4-11, which
currently defines cluster membership without saying what the NLI model is shown.

**What to say:**

> Two details of our instantiation differ from the source description and we state them here.
> First, our clusterer passes the bare answer strings to the entailment model
> (\texttt{src/se/entropy.py}); the question is not concatenated to each generation before the
> check. Second, generation is zero-shot from the chat template with no instruction on answer
> length, capped at $48$ new tokens; the resulting samples average $19.6$ words
> ($114$ characters) and $25.4\%$ of them end without terminal punctuation, having reached the
> cap mid-sentence. Both are properties of our replication rather than of the method, and both
> plausibly affect cluster granularity, so every number in this paper should be read as
> characterising the estimator under this configuration.

Two constraints on the wording, both important:

1. **Do not characterise what Kuhn et al. or Farquhar et al. do until someone has read the
   PDFs.** §3.2 gives external quotes that support "the source concatenates the question", and
   they look solid, but they came through a summarising fetch and one retrieval mis-attributed
   a paragraph. Write the sentence as a statement about *our* implementation ("the question is
   not concatenated...") and add the comparative clause only after a human confirms the source
   text. A paper that critiques a method's measurement validity cannot afford a misquotation
   of that method.
2. **Do not write "an order of magnitude longer" or "~15 characters."** They are wrong (§3.3).
   If a comparison is wanted at all, the honest one is that Farquhar et al. report
   $96 \pm 70$ characters for their sentence-length setting against our $114$ — comparable in
   mean, differing in that they instruct brevity and we cap tokens.

### 6.3 Extend the existing generation-configuration paragraph

`limitations.tex:61-62` already pins the 48-token budget and 61-80 already audits what the
manifest fails to record. Two clauses belong there:

- the manifest does not record the prompt template either, and the template is recovered from
  `src/se/model.py` the same way the six unrecorded generation settings are;
- the measured consequence of the budget: 19.6 words / 114 characters mean, 25.4% cap-truncated.

That paragraph already carries the "under-recorded cache" argument; these make it complete and
cost nothing.

### 6.4 One sentence on K, where the cluster-count bound is used

Wherever `results/cluster_count_bound.md` feeds the paper: the *level* of K is strongly
length-dependent (Spearman corr(mean length, K) = $+0.666$), so the empirical K distribution
the bound is applied to is a property of the 48-token configuration; the bound itself is
arithmetic, and the K>=8 gap between strata survives in every length quintile
(+20.5, +13.1, +16.7, +22.6, +17.3 points).

### 6.5 Leave the 0.828 gap alone

`experiments.tex:46-48` and `limitations.tex:240-244` currently decline to attribute the
0.134 gap. **Keep that.** §3.4 shows the report's suggestion — that the generation regime
explains part of it — is not supported: 0.828 is Tong et al.'s figure and this repo's answers
are not materially longer than Farquhar's. The finding in item 4 does *not* license weakening
that refusal.

### 6.6 What to do with the exact-match-on-truncated-text result

This one is a judgement call and I would not put the AUROC table in the paper. It is a
clean-detection result about a *different* clusterer on *different* text, and the paper
already uses exact-match in a specific and carefully bounded role (`methods.tex:349-363`) as
the saturation-limited lower bound of an adjudication bracket. Introducing it as "a model-free
clusterer on truncated text beats the deployed one at 0.79" invites a reader to conflate the
two roles, and the paper has fought hard to keep them apart.

If it is used at all, the safe form is a single sentence in Limitations, in support of §6.2's
disclosure and nothing else: that the 48-token configuration is not merely a deviation but a
*costly* one, since exact-match clustering on first-sentence-truncated text separates the
strata better ($0.762$ full pool, $0.792$ fair) than the deployed NLI clusterer does on full
text — so the configuration is leaving detection power on the table rather than manufacturing
any. It closes off the obvious referee suspicion that the verbose setting inflates the result.

### 6.7 Repo hygiene, outside the paper

- `scripts/length_confound_probe4.py` as committed does not reproduce the report's §5 table
  (§2.5). Either round the entropies before the AUROC or annotate the report with the
  discrepancy, so the next reader is not left with an unexplained mismatch.
- `scripts/length_confound_probe3.py` stratifies each truncation arm by *its own* mean length.
  For the 10-word arm that variable is nearly constant, so the bins barely control anything;
  its "0.751" is not like-for-like with the full-text 0.663. Stratifying every arm by the same
  full-text mean length gives 0.663 (full text), 0.714 (first sentence), 0.724 (10 words)
  against the NLI clusterer's 0.644 — same ordering, honest control. Prefer these.
- `results/length_confound_probe.md` should be annotated with the stale line references
  (§3.1), the refuted "~15 characters" (§3.3), and the corrected attack-cell reading (§4.2)
  rather than left to be read as current.

## 7. Artefacts

Verification scripts and raw output are in the session scratchpad
(`verify.py`, `verify2.py`, `verify3.py` and their `*_output.txt`), not committed — they read
a scratch copy of the WSL cache and are reproducible from the source paths named in §0.
`verify2.py` section F is superseded by `verify3.py` section I: the first version counted
empty `answer_under_q_prime` strings as zero-word answers and reported a spurious *shortening*.
The corrected figures are the ones in §4.2 of this document.
