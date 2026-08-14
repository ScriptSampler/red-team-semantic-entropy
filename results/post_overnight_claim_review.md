# Post-overnight claim review — what the paper can honestly claim on 2026-08-14

Prepared for human review. **No `.tex` file was edited.** Every number below is either read
from an artefact in `results/` or recomputed here; the recomputation scripts are named in
§8 and every figure is reproducible from `results/n_scaling_ckpt.jsonl` plus the Week-4
cache with no GPU.

Three results landed overnight. Two go against the current headline. The blunt summary:

- **The Abstract's flagship sentence is false as written and has to be scoped to N=10.**
  It is rescued, not gutted, and the rescue is stronger than the original.
- **The ceiling finding is now demonstrably estimator-specific.** That was argued in
  Methods and is now measured. It costs the paper generality it was already hedging
  against, and it promotes the cluster-count bound to load-bearing.
- **The winner's-curse numbers move by about a point.** Nothing turns on it.
- **The stronger claim underneath is real, but not the one proposed.** It holds in the
  low-false-alarm region and *fails* over the full range. Stated correctly it is better
  than the broken claim. Stated as proposed it would be wrong and a referee would catch it.

---

## 1. THE HEADLINE QUESTION: is there a stronger claim underneath?

**Proposed claim.** "At a fixed false-alarm budget the detection rate is flat to slightly
worse as the sample budget grows (TPR 27.5% at N=10, 25.5% at N=20, 24.0% at N=40) —
buying more samples buys finer granularity and NOT better discrimination."

**Verdict: HOLDS in the operating region, FAILS as a general statement, and the three
numbers quoted are not a like-for-like comparison.** All three defects are fixable and the
repaired claim is stronger. Taken in the order asked.

### 1.1 Is the comparison like-for-like? — **No, and the defect is not the one anticipated.**

The worry was that the achieved FPRs differ (9.5 / 10.0 / 10.0). That turns out to be the
*minor* problem. Matched at exactly 9.5% on the randomised frontier the three numbers are
27.5 / 25.5 / 24.0 — i.e. the quoted sequence already *is* the matched-achieved sequence.
The achieved-rate mismatch costs essentially nothing.

**The real defect is a source confound.** 27.5% comes from the *direct* Week-4 N=10 cache.
25.5% and 24.0% come from *replays* of the N=40 checkpoint. Replaying N=10 out of the same
checkpoint — the only like-for-like N=10 available — gives **22.6%** (median over 20 subset
draws; 25.9% on replicate 0), not 27.5%.

| N=10, at a matched 9.5% achieved FPR | TPR |
| --- | --- |
| direct (Week-4 cache) | 27.5% |
| replay of the N=40 run, median of 20 subset draws | 22.6% |
| paired difference (direct − replay) | **−4.9 pts [−12.6, +7.5]** |

The direct-versus-replay gap on the very statistic in question is **−4.9 points**. The
entire N=10→N=40 budget effect being claimed is **−3.5 points**. The measurement artefact is
larger than the effect. Read like-for-like — replay throughout — the sequence is
**22.6 → 25.5 → 24.0**, which is not monotone and is not a decline.

> **Do not quote 27.5 / 25.5 / 24.0 as a trend.** It is a direct measurement followed by two
> replays, and the step between the two sources is bigger than the step being claimed.

### 1.2 Are the differences inside sampling error? — **Yes. The honest verb is "does not improve", never "gets worse".**

Paired bootstrap, 4,000 resamples, resampling the 200 correct and 200 hallucinating targets
jointly (all budgets are scored on the *same* targets — ID match verified, see §8) **and**
resampling the subset draw, so both variance components are inside every interval.
TPR is read off the randomised frontier so grids that do not align can still be compared.

| matched FPR | direct N=10 | replay N=10 | replay N=20 | measured N=40 |
| --- | --- | --- | --- | --- |
| 5.0% | 14.5% [9.6, 25.0] | 11.9% [9.0, 20.6] | 14.6% [10.6, 23.7] | 13.2% [10.5, 23.1] |
| 9.5% | 27.5% [18.2, 36.3] | 22.6% [17.1, 35.2] | 25.5% [19.7, 37.0] | 24.0% [19.7, 35.8] |
| 10.0% | 28.3% [19.2, 37.2] | 23.8% [18.0, 36.3] | 26.7% [20.7, 38.2] | 25.1% [20.7, 37.0] |
| 20.0% | 43.7% [36.1, 54.8] | 45.8% [35.6, 59.6] | 48.6% [39.4, 62.2] | 47.8% [40.1, 63.1] |

Every paired difference straddles zero. The widest low-FPR one:

- @9.5%, direct N=10 → measured N=40: **−0.035 [−0.085, +0.074]**
- @10%, direct N=10 → measured N=40: **−0.031 [−0.081, +0.075]**
- @5%, direct N=10 → measured N=40: **−0.012 [−0.073, +0.067]**
- @20%, direct N=10 → measured N=40: **+0.041 [−0.025, +0.145]** — sign *reverses*

**So: "does not improve", and say so in those words.** The data does not license "gets
worse" at any budget, and at 20% the point estimate goes the other way. Anyone writing
"slightly worse" is over-reading a null.

### 1.3 Does it hold at 20%, and at 5%? — **Yes at both, and 5% is the strongest cell.**

- **20%:** flat, with the point estimate drifting *up* (43.7 → 48.6 → 47.8). Claim
  "does not improve" and nothing more.
- **5%:** this is where the finding is sharpest, because the deterministic and the
  randomised readings say the same thing from opposite directions.

| budget | deterministic `at_most` 5% | achieved | TPR |
| --- | --- | --- | --- |
| N=10 (direct) | flags nothing | 0.0% | **0.0%** |
| N=20 (replay) | available | 2.8% | 8.8% [0.0, 21.0] |
| N=40 (measured) | available | 5.0% | **11.0% [4.5, 21.5]** |

Quadrupling the sample budget converts a 5% operating point from *non-existent* to
*existent* — and the operating point it creates catches 11% of hallucinations, which is
**less than the 14.5% the N=10 randomised rule already delivered at the same 5%.** The
budget buys the operator a deterministic rule they can audit; it buys them no detection.

That is the cleanest statement of the finding in the whole review, and it is the one the
Abstract should carry.

### 1.4 Is AUROC flat over the whole range? — **NO. This is where the proposed claim breaks.**

| source | AUROC |
| --- | --- |
| direct N=10 | 0.704 [0.654, 0.753] |
| replay N=10 | 0.718 [0.661, 0.772] (replicate range 0.695–0.742) |
| replay N=20 | 0.738 [0.687, 0.787] (replicate range 0.724–0.750) |
| measured N=40 | **0.746 [0.697, 0.792]** |

- direct N=10 → measured N=40: **+0.041 [+0.006, +0.077] — excludes zero.**
- replay N=10 → measured N=40: +0.028 [−0.011, +0.066] — does not exclude zero.

The two available comparisons disagree, and the one that clears zero is the one carrying
the source confound of §1.1. But the point estimate rises monotonically under every reading,
and **the paper cannot claim AUROC is flat.** A referee with the checkpoint would find this
in an afternoon.

**Where the gain lives is the interesting part, and it rescues the claim.** Standardised
partial AUC by false-alarm band (0.5 = chance within the band):

| source | AUROC | FPR ≤ 5% | ≤ 10% | ≤ 20% | 20–50% | 50–100% |
| --- | --- | --- | --- | --- | --- | --- |
| direct N=10 | 0.704 | 0.072 | 0.145 | 0.249 | 0.636 | 0.927 |
| N=10 | 0.695 | 0.068 | 0.136 | 0.252 | 0.596 | 0.931 |
| N=20 | 0.742 | 0.074 | 0.132 | 0.241 | **0.703** | **0.967** |
| N=40 | 0.746 | 0.069 | 0.126 | 0.234 | **0.717** | **0.967** |

Paired differences, direct N=10 → measured N=40, both variance components:

- pAUC over FPR ≤ 5%: **−0.004 [−0.046, +0.045]** — flat
- pAUC over FPR ≤ 10%: **−0.019 [−0.080, +0.043]** — flat
- pAUC over FPR ≤ 20%: **−0.015 [−0.080, +0.055]** — flat
- the whole AUROC gain sits in the 20–100% band, where no operator runs.

> **The repaired claim, and it is stronger than the one proposed:**
> *A larger sample budget does improve semantic entropy as a ranker — AUROC rises from
> 0.704 to 0.746 between N=10 and N=40 — but the entire improvement lies at false-alarm
> rates above 20%. Inside the operating region the detector does not improve at all:
> partial AUROC below a 10% false-alarm rate is 0.145 at N=10 and 0.126 at N=40
> (difference −0.019 [−0.080, +0.043]), and detection at every matched false-alarm rate
> we can compare is unchanged. What the budget buys is a finer grid of operating points,
> not better discrimination where an operator has to stand.*

This survives the "just raise N" rebuttal **better** than the version proposed, because it
concedes the rebuttal's premise (yes, AUROC improves) and shows the concession is
irrelevant. It also avoids the trap of claiming a flat AUROC that the data contradicts.

### 1.5 An additional finding worth its own sentence

**The deterministic TPR at a stated false-alarm budget is not estimable at n = 200.**

| | point | bootstrap 95% |
| --- | --- | --- |
| direct N=10, deterministic TPR at a 10% budget | 27.5% | **[0.0%, 33.5%]** |
| replay N=10, same | 0.0% | **[0.0%, 33.0%]** |

The statistic is bimodal: it collapses to zero on every resample where the floor happens to
land above 10%. At N=10 a 10% budget sits on a knife-edge, so what an operator gets is
close to a coin flip on whether the floor falls below their budget. This is a genuine
operational finding — and it is also why §1.2 uses the randomised frontier rather than the
deterministic rule for the *comparison*.

### 1.6 The mechanism, which the cluster-count bound supplies

Why doesn't a bigger budget help in the operating region? Because the top of the scale
recedes as fast as the sample fills it. `K ≥ ceil(N^0.9)` is necessary for a top-decile
score under any normalised weighting; the share of clean correct answers meeting it **falls**
with N:

| N | K_min | correct K ≥ K_min | hallucinating K ≥ K_min | gap |
| --- | --- | --- | --- | --- |
| 5 | 5 | 30.0% [24.1, 36.7] | 59.0% [52.1, 65.6] | +29.0 |
| 10 | 8 | 32.5% [26.4, 39.3] | 57.0% [50.1, 63.7] | +24.5 |
| 20 | 15 | 20.5% [15.5, 26.6] | 44.0% [37.3, 50.9] | +23.5 |
| 40 | 28 | 17.0% [12.4, 22.8] | 35.0% [28.7, 41.8] | +18.0 |

Mean K/N on the correct stratum: 0.68 → 0.57 → 0.46 → 0.38. The samples do not stay
mutually distinct as the budget grows, so the top of the range empties out at the same rate
the grid refines. That is the mechanism behind §1.2 and it is measured, not conjectured.

---

## 2. THE OPERATOR CLAIM: how to scope it without gutting it

### 2.1 What the data forces

`results/n_scaling_grid.md` §1 reports the floor as the ceiling-atom mass. **That column is
mis-specified at N=40 and the row as printed overstates the paper's problem.** At N=40 no
clean correct answer reaches the cap (max observed 3.6196 against ln 40 = 3.6889), so the
at-cap mass is 0/200 — but 0% is not an achievable non-zero false-alarm rate. The smallest
one is set by the top *observed* value:

| budget | at-cap mass (the identity) | **smallest achievable non-zero FPR** | TPR there |
| --- | --- | --- | --- |
| N=10 direct | 19/200 = 9.5% [6.2, 14.4] | 9.5% | 27.5% |
| N=20 replay | 6/200 = 3.0% [1.4, 6.4] | 3.0% | 9.5% |
| N=40 measured | 0/200 = 0.0% [0.0, 1.9] | **4/200 = 2.0% [0.8, 5.0]** | 6.0% |

The `next FPR` column in that report shows 2.5% for N=40, which is the *second* firing
point; the first (2.0%) is missing from the table entirely. **Fix the generator before this
number reaches a draft** — as printed, the N=40 row reads "you can have any false-alarm rate
down to zero", which is false.

The substantive consequence is a scope change, not a rescue: at N=40 the floor stops being
an *identity* and becomes an ordinary order statistic. The sentence "that floor is an
identity, not a measurement we happened to make" is true only while the ceiling atom is
non-empty, i.e. at N=10 and N=20 on this population. It must be scoped.

### 2.2 The pre-registration protects you here — use it

`results/n_scaling_plan.md` §5, written before the GPU was touched, predicted the floor at
N=20 at **3.5%–5.3%** and at N=40 at **1.2%–2.4%**, and pre-committed: *"if it comes in far
below, the finding becomes 'here is the budget that buys a 5% false-alarm rate'. Both are
results. This paragraph exists so that neither can be written after the fact."*

Measured: N=20 → 3.0%; N=40 → smallest achievable non-zero FPR 2.0%, squarely inside the
predicted N=40 band. **The branch that fired was pre-registered.** Say so in the paper. It
converts "our headline broke overnight" into "we predicted where it would break and it broke
there", which is a materially different thing for a reviewer to read.

(One subtlety worth a footnote: the *atom* at N=40 came in at 0.0%, below the predicted
1.2–2.4% band, while the *achievable floor* came in at 2.0%, inside it. The prediction was
about the atom; it under-shot on the atom and hit on the operational quantity.)

### 2.3 The claim to make

N=10 is the deployed budget in the three works that define this line — that is the load-
bearing framing, and the paper is entitled to say so. **Owed check before submission:**
verify per-paper that Kuhn et al. (2023), Farquhar et al. (2024) and Kossen et al. (2024)
each run N=10, with a page or table cite for each. I could not verify this from the repo and
the whole re-scope rests on it.

**Proposed Abstract replacement** (for the two sentences beginning "Every threshold above
that maximum..."). Long form:

> Every threshold above that maximum flags nothing, so the lowest false-alarm rate a firing
> threshold can have *is* the chance that a clean correct answer yields $N$ mutually
> distinct meanings — $10.5\%$ [$9.0$, $12.2$] over $1424$ clean correct answers. At the
> $N{=}10$ that Kuhn et al., Farquhar et al. and Kossen et al. all deploy, an operator who
> specifies a $5\%$ false-alarm budget cannot have one, however well the score ranks.
> Quadrupling the budget to $N{=}40$ buys the missing operating point — the achievable floor
> falls to $2.0\%$ [$0.8$, $5.0$] — but not the detection it was wanted for. Matched at
> equal false-alarm rates, detection does not improve: partial AUROC below a $10\%$
> false-alarm rate is $0.145$ at $N{=}10$ against $0.126$ at $N{=}40$, and a $5\%$ budget at
> $N{=}40$ catches $11.0\%$ [$4.5$, $21.5$] of hallucinations where the $N{=}10$ randomised
> rule already reached $14.5\%$. More samples buy a finer grid, not a better detector, in
> the region where an operator has to stand.

Short form, if the ~200-word budget binds:

> ... $10.5\%$ [$9.0$, $12.2$] over $1424$ clean correct answers. At the standard $N{=}10$
> an operator who specifies a $5\%$ false-alarm budget cannot have one, however well the
> score ranks; at $N{=}40$ they can, and it catches $11.0\%$ [$4.5$, $21.5$] of
> hallucinations — no more than the randomised rule at $N{=}10$ already offered. The sample
> budget buys grid resolution, not discrimination, in the region an operator occupies.

Both state the limit **in the Abstract**, as required, and both convert the concession into
the second finding rather than a caveat.

---

## 3. WHAT THE SUBSETTING CONTROL DOES TO CONFIDENCE

### 3.1 The control passes, but not tightly enough to license a trend

Direct N=10 (Week-4 cache) against replayed N=10 (20 subset draws of the N=40 run), on the
same 200+200 targets, paired:

| statistic | direct | replay (median) | paired difference |
| --- | --- | --- | --- |
| floor | 9.5% | 12.0% (range 10.0–14.5) | +2.5 pts [−2.5, +7.0] |
| AUROC | 0.704 | 0.718 (range 0.695–0.742) | +0.014 [−0.033, +0.059] |
| TPR @ 9.5% | 27.5% | 22.6% | −4.9 pts [−12.6, +7.5] |
| pAUC ≤ 10% | 0.145 | 0.113 | −0.032 [−0.103, +0.045] |

Every interval covers zero, so the control **passes** on the stated criterion. But the point
biases are +26% relative on the floor and −4.9 points on TPR — and as §1.1 showed, the TPR
bias exceeds the budget effect it would be used to establish. **The control licenses the
existence claims and not the trend claims.**

### 3.2 Two unidentified components, and one missing control

The direct-vs-replay gap conflates **subsetting error** with **generation drift**: the
Week-4 cache was generated in June, the N=40 checkpoint on 2026-08-13, on a session whose
library state is not pinned against the earlier one. `scripts/n_scaling_grid.py` has a
"drift control" that fires only when N=10 is *directly re-measured on the same box* — and it
was not, so the report emits the subsetting control instead. Neither component is
separately identified. A fresh direct N=10 pass on the current box would separate them for
roughly one-quarter of the N=40 cost and is the single highest-value cheap run outstanding.

### 3.3 The published N=20 interval is understated

`results/n_scaling_grid.md` quotes N=20 floor **3.0% [1.4%, 6.4%]**. That is a Wilson
interval on replicate 0 only; it carries target-sampling variance and not subset-choice
variance. With both components: **median 2.75%, [0.5%, 5.5%]**, replicate range
[1.5%, 4.0%]. Every replayed row in that report has the same defect.

### 3.4 How much weight the N=20 row can carry — recommendation

**Report N=20 as an estimate, explicitly labelled "replayed, not measured", with a
two-component interval. Do not let any claim rest on it that a direct measurement could
overturn.**

The one thing it *can* carry is the claim that costs the paper something: *a 5% budget is
honourable at N=20*. That is robust across all 20 subset draws (worst-case floor 4.0% < 5%),
and a replayed number that damages your own headline is safe to quote in a way that a
replayed number supporting it would not be. Asymmetric standards are correct here.

**And the paper does not need N=20 anyway.** The Abstract concession can be sourced entirely
to the **directly measured N=40 row** (floor 2.0%, 5% budget honourable at achieved 5.0%,
TPR 11.0%). Route the headline through N=40, demote N=20 to a supporting row in the
Discussion table, and the load-bearing claim rests on a direct measurement throughout.
Do that.

---

## 4. CLAIM-BY-CLAIM TABLE

Status key: **DIES** (must be removed or reversed) / **SCOPE** (true only under an added
qualifier) / **SURVIVES** (unchanged) / **STRENGTHENS** (now better supported) /
**NUMBER** (wording fine, figure changes).

### 4.1 Abstract (`paper/main.tex`, lines 34–50)

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| A1 | "at the standard $N{=}10$ it takes only $39$ values, with an atom at the maximum" | **SURVIVES** | unchanged (39 and the atom re-verified) |
| A2 | "the lowest false-alarm rate a firing threshold can have *is* the chance that a clean correct answer yields $N$ mutually distinct meanings—$10.5\%$ [$9.0$, $12.2$]" | **SCOPE** | append "…at $N{=}10$"; the identity is vacuous once the atom empties (it is empty at $N{=}40$) |
| A3 | "An operator who specifies a $5\%$ false-alarm budget cannot have one, however well the score ranks." | **DIES as written** | see §2.3 — scope to $N{=}10$, then add the $N{=}40$ result as the second finding |
| A4 | "retains only $45\%$ [$25\%$, $65\%$] of the apparent effect" | **NUMBER** | "$44\%$ [$23\%$, $64\%$]" (whole-percent only; the tenths are RNG noise per the artefact) |
| A5 | "roughly half of an uncorrected result is selection on sampling noise" | **SURVIVES** | unchanged |
| A6 | "The confirmatory attack evaluation is under way; we claim no attack effect here." | **SURVIVES** | unchanged |

### 4.2 Introduction — contribution bullets (`sections/introduction.tex`)

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| C1 | "(1) **A measurement-validity result about *discrete* semantic entropy**" | **STRENGTHENS** | unchanged framing; the discrete scoping is now *measured* rather than argued (§4.6) — say so |
| C2 | "That half is shared with the likelihood-weighted Eq.~(5), which normalises to a categorical distribution over the same clusters and so inherits the same ceiling" | **STRENGTHENS** | now measured: Eq. (5) length-normalised puts $0/2000$ strictly above $\log N$; Kuhn Eq. (4) puts $94.0\%$ [$92.9$, $95.0$] strictly above it. Quote both. |
| C3 | "the achievable clean false-positive rates below one in four are $0\%$, $9.5\%$ … and $21.5\%$ … an operator who specifies a $5\%$ false-alarm budget cannot have one" | **SCOPE** | "…at $N{=}10$. At $N{=}40$, directly measured on the same $200$ correct answers, the achievable floor falls to $2.0\%$ [$0.8$, $5.0$] and a $5\%$ budget becomes available — catching $11.0\%$ [$4.5$, $21.5$] of hallucinations, against the $14.5\%$ a randomised rule at $N{=}10$ already reached." |
| C4 | "That floor is an identity, not a measurement we happened to make: every threshold above $\ln N$ flags nothing…" | **SCOPE** | add: "The identity binds only while the ceiling carries mass. At $N{=}40$ no clean correct answer reaches $\ln 40$, so the atom is empty and the floor reverts to an ordinary order statistic — $2.0\%$ [$0.8$, $5.0$] — set by the largest score observed rather than by the cap." |
| C5 | "Raising $N$ relaxes this ($N{=}20$ affords $455$ points, seven of them in the top tenth), but buys less usable headroom than the cap implies" | **STRENGTHENS** | lattice counts re-verified (455/7 at $N{=}20$; 14,114/42 at $N{=}40$). Replace the hedge with the measurement: "and we now measure what it buys — a finer grid and no additional detection below a $20\%$ false-alarm rate (§Discussion)." |
| C6 | "$21$ of our $80$ correct targets cannot register a success at any usable $\delta$" | **SURVIVES** | unchanged (discrete, $N{=}10$, attack pool) |
| C7 | "(2) … only $45\%$ of the apparent effect survives ($95\%$ CI $[25\%, 65\%]$)" | **NUMBER** | "$44\%$ ($95\%$ CI $[23\%, 64\%]$)" |
| C8 | "the shrinkage is $-0.383$ nats with a $95\%$ CI of $[-0.529, -0.234]$" | **NUMBER** | "$-0.341$ nats, $95\%$ CI $[-0.469, -0.212]$" |
| C9 | "(3) … versus $0.704$ [$0.653$, $0.753$] on the fair pool" | **SURVIVES**, newly robust | unchanged; optionally add "and $0.703$ [$0.652$, $0.753$] under the length-normalised Eq. (5) on identical clusterings" |
| C10 | "(5) … at $N{=}10$ the estimator's attainable lattice has $39$ points, and its top two lie $0.139$ nats apart" | **SURVIVES** | unchanged |
| C11 | "(4) the LLM-judge … $0.93$ vs. $0.51$" | **SURVIVES** | unchanged |

### 4.3 Discussion (`sections/discussion.tex`)

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| D1 | "An operator who specifies a $5\%$ false-alarm budget cannot have one: the only threshold that honours it is the one that never fires" (¶ *The achievable false-alarm rates…*) | **SCOPE** | prefix "At $N{=}10$,"; then cross-reference the budget-scaling paragraph rather than restating the general claim |
| D2 | "A $10\%$ budget we do *not* claim to exclude … the floor is about one correct answer in ten and a $10\%$ budget sits on the boundary of feasibility" | **STRENGTHENS** | add the new evidence for the boundary: "How narrow that boundary is can be quantified. The deterministic true-positive rate an operator obtains at a $10\%$ budget is not estimable at $n{=}200$: its bootstrap interval is [$0.0\%$, $33.5\%$], because the statistic collapses to zero on every resample whose floor lands above the budget. At $N{=}10$ what a $10\%$ budget delivers is close to a coin flip on whether the floor falls beneath it." |
| D3 | **The whole ¶ "Does a larger sample budget fix it?"** — "Not settled: whether the grid becomes usably *fine* near the operating region… We have no clean $N{=}20$ scores on the fair pool… Settling it needs one clean pass at $N{=}20$ over the same correct stratum, which we have not run." | **DIES — rewrite entirely** | This is now the paper's second finding, not an open question. Draft below (§4.4). |
| D4 | "the sharpest way to put the finding is … 'discrete semantic entropy offers an operator no false-alarm rate between zero and roughly one correct answer in ten'" | **SCOPE** | "…at the $N{=}10$ this literature deploys, and buying the missing rate with a larger budget buys nothing else" |
| D5 | "the natural rebuttal—use an estimator with more range—concedes the point" | **STRENGTHENS** | add the companion, which is now measured: "The other natural rebuttal—use more samples—does not concede but is answered: the budget buys the operating point and not the detection." |
| D6 | "$0.275 \times 0.095 = 2.6\%$ of pairs, bounding the downward bias at $0.013$" | **SURVIVES** | unchanged ($N{=}10$, discrete) |
| D7 | "on the fair pool $27.5\%$ of hallucinating answers sit there against $9.5\%$ of correct ones" | **SURVIVES** | unchanged |
| D8 | Figure caption `fig:achievable-roc` — "a $5\%$ budget costs a true-positive rate of $14.5\%$ against the $27.5\%$ available at this fair pool floor" | **SURVIVES**, gains a use | unchanged, but this $14.5\%$ is now the benchmark the $N{=}40$ deterministic $11.0\%$ is measured against — flag the connection in the text |
| D9 | "On $15$ saturated targets re-scored at $N{=}20$ … That is a measurement of *headroom*, not of the grid, and it is not evidence about the grid either way" | **SURVIVES**, demoted | keep the caveat, but it is no longer the only $N{=}20$ evidence; subordinate it to the new paragraph |
| D10 | "the ceiling behind this reading is shared with the likelihood-weighted estimator, but the lattice … is not" | **STRENGTHENS** | now measured on identical clusterings — cite `results/rescore_likelihoods.md` rather than arguing it |

### 4.4 Proposed replacement for the "Does a larger sample budget fix it?" paragraph

> **Does a larger sample budget fix it?** We ran the budget out to $N{=}40$ on the same
> $200$ correct and $200$ hallucinating answers, recording the full pairwise equivalence
> matrix so that every smaller budget is recoverable exactly by replaying the verdicts on
> random subsets. Two things happen, and only one of them is the fix the question intends.
> The grid does become fine: the achievable floor falls from $9.5\%$ [$6.2$, $14.4$] at
> $N{=}10$ to $3.0\%$ at $N{=}20$ and $2.0\%$ [$0.8$, $5.0$] at $N{=}40$, the count of
> firing operating points at or below a $10\%$ false-alarm budget rises from one to four to
> fourteen, and the $5\%$ budget that $N{=}10$ cannot honour at all is honoured at $N{=}40$
> at an achieved $5.0\%$. Both floors below $N{=}40$ landed inside the band we pre-registered
> before the run (§Methods), including the $N{=}20$ figure that costs us the unqualified
> form of the claim above.
>
> What does not happen is any gain in detection where an operator stands. Matched at equal
> achieved false-alarm rates, the true-positive rate is unchanged: at a $5\%$ rate,
> $14.5\%$ at $N{=}10$ against $13.2\%$ at $N{=}40$; at $9.5\%$, $27.5\%$ against $24.0\%$;
> at $20\%$, $43.7\%$ against $47.8\%$ — every paired difference covering zero on a
> bootstrap that resamples targets and subset draws jointly. Partial AUROC below a $10\%$
> false-alarm rate is $0.145$ at $N{=}10$ and $0.126$ at $N{=}40$, a difference of
> $-0.019$ [$-0.080$, $+0.043$]. The deterministic $5\%$ operating point that $N{=}40$
> creates catches $11.0\%$ [$4.5$, $21.5$] of hallucinations — no more than the $14.5\%$ a
> randomised rule at $N{=}10$ already reached without any additional sampling at all.
>
> The detector does improve with the budget, and we state it rather than let a reader find
> it: AUROC rises from $0.704$ [$0.654$, $0.753$] at $N{=}10$ to $0.746$ [$0.697$, $0.792$]
> at $N{=}40$. The whole of that improvement is outside the operating region. Decomposed by
> false-alarm band, the standardised partial AUROC over $[0, 0.20]$ is flat ($0.249$ against
> $0.234$) while the band above $20\%$ rises from $0.818$ to $0.874$. A larger sample budget
> makes semantic entropy a better ranker in the half of the ROC no deployment can use.
>
> The mechanism is that the top of the scale recedes as fast as the sample fills it. A
> top-decile score needs $K \geq \lceil N^{0.9} \rceil$ distinct meaning clusters under any
> normalised weighting, and the share of clean correct answers meeting that condition falls
> with the budget — $32.5\%$ at $N{=}10$, $20.5\%$ at $N{=}20$, $17.0\%$ at $N{=}40$ — while
> the mean fraction of samples landing in distinct clusters falls from $0.57$ to $0.38$. The
> grid refines and the population retreats from its top end at the same time.
>
> Two limits on the above. Only $N{=}40$ is directly measured; $N{=}10$ and $N{=}20$ are
> replays of random subsets of that run, checked against the directly measured $N{=}10$
> cache, which they reproduce within sampling error (floor $9.5\%$ direct against a
> $12.0\%$ subset-replay median, difference $+2.5$ points [$-2.5$, $+7.0$]) but with point
> biases comparable to the budget effects themselves — so we read the replayed rows as
> estimates and route every claim above through the directly measured $N{=}40$ row where one
> exists. And the direct-versus-replay comparison conflates subsetting error with any drift
> between the two generation runs; we have not run the clean $N{=}10$ pass on the current
> machine that would separate them.

### 4.5 Conclusion (`sections/conclusion.tex`)

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| N1 | "an operator who specifies a $5\%$ false-alarm budget cannot have one, because the only threshold that honours it never fires" | **SCOPE** | "at the $N{=}10$ this literature deploys, an operator who specifies a $5\%$ false-alarm budget cannot have one…" |
| N2 | "That floor is an identity rather than a measurement, since every threshold above $\ln N$ flags nothing" | **SCOPE** | add "while the cap carries mass, which at $N{=}10$ and $N{=}20$ it does and at $N{=}40$ it does not" |
| N3 | "A $5\%$ budget is excluded at $95\%$ confidence on both populations; a $10\%$ budget is on the boundary and we claim no more than that." | **SCOPE** | append "…at $N{=}10$. At $N{=}40$ a $5\%$ budget exists and buys $11.0\%$ [$4.5$, $21.5$] detection, which is no more than the $N{=}10$ randomised frontier already offered — the budget purchases grid resolution, not discrimination." |
| N4 | "about half of its apparent effect is selection on estimator noise" | **SURVIVES** | unchanged (44% retention still rounds to "about half" lost) |
| N5 | "it separates correct from hallucinating answers moderately well, at AUROC $0.704$ [$0.653$, $0.753$]" | **SURVIVES** | unchanged; if the budget finding enters the Conclusion, note $0.746$ at $N{=}40$ so the two are not in apparent tension |
| N6 | "the lattice, and so the grid of achievable false-alarm rates, is particular to the discrete variant" | **STRENGTHENS** | now measured |

### 4.6 Methods (`sections/methods.tex`) — the estimator result

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| M1 | "Eq.~(5) attains its own maximum only when the normalised cluster likelihoods are exactly equal, an event of measure zero, so it has no ceiling *atom*" | **STRENGTHENS — argument becomes measurement** | "…and re-scoring our own $2000$ cached sample sets under Eq. (5) with the generating model's own sequence likelihoods, holding the clustering fixed, confirms it directly: $0/2000$ [$0.0$, $0.2$] questions sit at the cap under length-normalised Eq. (5) against $295/2000 = 14.8\%$ [$13.3$, $16.4$] under the discrete estimator." |
| M2 | "Whether the empirical *crowding* near the cap survives the substitution is unsettled, and we report a simulation rather than assert it either way (Limitations)" | **DIES — it is now settled** | "The empirical crowding survives the substitution in weakened form: the share of questions in the top tenth of the range is $27.8\%$ [$25.9$, $29.8$] under the discrete estimator and $20.0\%$ [$18.3$, $21.8$] under length-normalised Eq. (5). The atom does not survive at all. So the range is genuinely crowded near the cap under both estimators, and only the discrete one turns that crowding into a floor." |
| M3 | (new, owed) Kuhn Eq. (4) scope | **STRENGTHENS** | "Kuhn's Eq. (4) scores $94.0\%$ [$92.9$, $95.0$] of the same $2000$ questions *strictly above* $\log N$ on identical clusterings, so no ceiling-derived claim in this paper — including the cluster-count bound — says anything about it. We measured this rather than inferring it from the definition." |
| M4 | (new, owed) rank agreement | **SCOPE** | Spearman $\rho$ against discrete is $0.989$ for length-normalised Eq. (5) but $0.381$ for raw Eq. (5). Under the pre-fixed decision table, high $\rho$ means every AUROC stands and only the saturation arithmetic is estimator-specific — **true for the length-normalised variant only.** Measured fair-pool AUROC: discrete $0.704$ [$0.654$, $0.754$], Eq. (5) length-normalised $0.703$ [$0.652$, $0.753$], Eq. (5) raw $0.625$ [$0.571$, $0.680$], Kuhn Eq. (4) $0.666$ [$0.615$, $0.718$], Kuhn length-normalised $0.741$ [$0.692$, $0.789$]. State that the AUROC claim is stable under the estimator the victim paper designates as its main method, and that length normalisation — not Eq. (5) itself — is the modelling choice that decides it. |
| M5 | "the exact-saturation counts, the hard-tie handling in the exceedance test, and … the finite grid of achievable false-alarm rates and the non-zero floor beneath it all presuppose integer cluster sizes" | **SURVIVES** | unchanged, now with a citation to the measurement |

### 4.7 Limitations (`sections/limitations.tex`)

| # | Current wording | Status | Proposed replacement |
| --- | --- | --- | --- |
| L1 | "Settling it needs the real weights: re-scoring our stored samples under the generating model's own sequence likelihoods would decide it directly… **That script is written; it has not been run, and we report nothing from it here.**" | **DIES** | It has been run. Replace the closing of that paragraph with the measured result, and move the simulation ($s$-sweep) to a supporting role: the simulation predicted the atom dies at any positive spread and near-cap crowding decays smoothly; the real weights confirm both. Retain the provenance gaps the artefact discloses (top_p, quant type, dtype, model revision not pinned; 0.085% of samples retokenise past the generation budget) as the residual caveat. |
| L2 | "Across the $60$ false-alarm targets … from $+0.698$ to $+0.315$ nats" | **NUMBER** | "Across the $69$ false-alarm targets … from $+0.609$ to $+0.268$ nats" |
| L3 | "the shrinkage is $-0.383$ nats with a bootstrap interval of $[-0.529, -0.234]$" | **NUMBER** | "$-0.341$ nats, $[-0.469, -0.212]$" |
| L4 | "retention … $45\%$ $[25\%, 65\%]$" | **NUMBER** | "$44\%$ $[23\%, 64\%]$" — quote whole percents only; the artefact states the tenths are RNG noise across bootstrap seeds |
| L5 | "$36$ of $60$ targets keep a positive move and the two measurements correlate at $r{=}0.46$" | **NUMBER** | "$37$ of $69$ targets ($54\%$) keep a positive move and the two measurements correlate at $r{=}0.48$" |
| L6 | (new, owed) budget scope | **ADD** | A short limitation: the budget-scaling result rests on one directly measured budget ($N{=}40$) with the rest replayed from its verdict matrix, on one model, one dataset and $n{=}200$ per stratum; and the direct-versus-replay check cannot separate subsetting error from generation drift. |

### 4.8 Experiments (`sections/experiments.tex`)

| # | Current wording | Status | Note |
| --- | --- | --- | --- |
| E1 | "on the resulting fair pool the clean detector scores AUROC $0.704$ [$0.653$, $0.753$]" | **SURVIVES** | unchanged |
| E2 | replication AUROC $0.694$ / $0.729$ / $0.790$ against published $0.828$ | **SURVIVES** | unaffected |
| E3 | Table `tab:nullcontrol` placeholders | **SURVIVES** | unaffected; still pending the confirmatory run |
| E4 | "Discrete semantic entropy is bounded above by $\log N$ … benign paraphrases reach that ceiling too, so the score has an *atom*" | **SURVIVES** | unchanged, but the tie machinery is now explicitly discrete-only — cross-reference M1 |

---

## 5. CAN THE CLUSTER-COUNT BOUND CARRY MORE WEIGHT?

**Yes — promote it, and the case is stronger than `results/cluster_count_bound.md` makes it,
because that document only measures it at N=10.**

What it now has going for it:

1. **It is the only ceiling-derived claim invariant to the weighting.** It follows from
   $H \leq \log K$, which holds for any normalised weighting, so it covers the discrete
   estimator *and* Farquhar Eq. (5) — the victim paper's designated main method. The
   overnight rescore is what makes this matter: the lattice claim is now measurably dead
   under Eq. (5), and the bound is what is left standing.
2. **The contrast is large and stable across every sample budget** (new measurement, §1.6):
   correct-vs-hallucinating gap in $\Pr(K \geq \lceil N^{0.9}\rceil)$ of +29.0 / +24.5 /
   +23.5 / +18.0 points at N = 5 / 10 / 20 / 40. It is not an N=10 artefact.
3. **It supplies the mechanism for the budget finding**, which no other quantity in the
   paper does. The share of correct answers that can even reach the top decile *falls* with
   N (32.5% → 20.5% → 17.0%). That is why the grid refining does not help.
4. **It is cheap to verify and hard to argue with** — CPU only, no model, recomputed from
   raw cluster assignments with zero mismatches against the cache.

What limits it, and must be stated:

- **It is necessary, not sufficient, and barely attainable at the margin.** Only $2.0 \times
  10^{-6}$ of the $K{=}8$ weighting simplex clears the top decile. `cluster_count_bound.md`
  §2 is right that the *working* requirement is $K \geq 9$ and only $K \geq 8$ is provable
  without committing to an estimator. Quote $K \geq 8$; the reporting rule in that document
  is correct and should be obeyed.
- **It says nothing about Kuhn Eq. (4)** — and the overnight rescore now gives that a
  number (94.0% strictly above $\log N$) instead of leaving it as an inference.
- **It is a statement about the top decile, not about the operator's floor.** It cannot
  substitute for the false-alarm-grid result; it explains and generalises it.

**Recommendation.** Move the bound out of a supporting role and into contribution (1) as the
variant-proof half of the measurement-validity result, with the lattice/grid material
explicitly labelled as the discrete-specific half. The proposed sentence in
`cluster_count_bound.md` §8 is good and I would ship it close to as-is, with one addition:
extend it with the budget series from §1.6 above, because "the condition gets harder to meet
as N grows" is the sentence that closes the "just raise N" escape route at the level of
mechanism rather than of measurement.

---

## 6. IS THE PAPER STRONGER OR WEAKER THAN YESTERDAY?

**Stronger. Clearly, and not as consolation.**

What was lost, stated plainly:

- The unqualified 5%-budget claim is gone. It was the single most quotable sentence in the
  Abstract and it is now a sentence with a condition attached.
- The ceiling finding is confirmed as estimator-specific rather than merely hedged as such.
  The paper was already scoping this honestly in Methods and Limitations, so the loss is
  smaller than it looks — but "we suspect this does not transfer" and "we measured it and
  it does not transfer" are different papers, and the second one has a narrower headline.
- One Limitations paragraph is now false ("that script has not been run") and one Discussion
  paragraph is now obsolete.

What was gained:

- **A second finding of the same kind as the first**, and arguably better: at a fixed
  false-alarm rate the detector does not improve with the sample budget, and the AUROC gain
  the budget does buy lies entirely at false-alarm rates above 20%. This is a claim about
  the detector's tradeoff, not its arithmetic, and the two obvious rebuttals — "raise N",
  "use a different estimator" — are now both answered rather than one.
- **A mechanism**, via the cluster-count bound's budget series, where before there was a
  measurement without one.
- **A pre-registered break.** The floor at N=20 landed where `n_scaling_plan.md` §5 said it
  would, in a document that pre-committed to exactly this reversal. Very few papers can show
  a reviewer the paragraph that predicted their own headline would break.
- **The estimator scoping is now evidence rather than a caveat**, and it comes with the
  reassurance that matters most: the paper's AUROC (0.704) is essentially identical under
  Eq. (5) length-normalised (0.703). The thing that dies is the saturation arithmetic; the
  thing that survives is the detector characterisation.

The honest framing for the paper is that the headline narrowed and the contribution
broadened. A finding that holds at one budget and is explained at all of them is worth more
than a finding that holds at one budget and is silent about the rest.

**One thing to be genuinely worried about.** The claim "an operator cannot have a 5%
false-alarm budget" was doing a lot of rhetorical work, and "an operator cannot have one at
the budget everyone deploys, and buying it changes nothing" is a longer sentence that lands
less hard. The mitigation is to make §1.3's comparison — 11.0% at N=40 against 14.5% the
randomised N=10 rule already gave — the memorable number. It is a better number than the one
it replaces because it is a *comparison* rather than an absence.

### Does the re-scope-and-retitle recommendation still stand?

**Yes, and more strongly than when it was made.**

`docs/framing_decision.md` recommended Option B (protocol-led) over Option A (attack-led) on
the grounds that B does not depend on a risky adjudication and turns "we could not cleanly
adjudicate" into the central result. Nothing overnight touches that reasoning, and two
things reinforce it:

- The current title — *"Crying Wolf, Carefully: What It Takes to Evaluate Paraphrase Attacks
  on Sampling-Based Hallucination Detectors"* — is a protocol title, and the protocol
  contributions (score-independent selection, answer-invariance criterion, budget-priced
  null, independent judge, winner's-curse correction) are **entirely untouched** by all
  three overnight results. The parts of the paper that moved are the measurement parts. A
  protocol-led paper absorbs a narrowed measurement finding without structural damage; an
  attack-led paper would not have.
- The measurement finding has gone from one claim about one budget to a claim about the
  budget/granularity tradeoff. That is more naturally a *measurement-validity* contribution
  than an attack contribution, which pushes further toward B.

**One title-level suggestion, offered and not pressed.** The current title does not signal
the measurement finding at all, and that finding is now two-thirds of what the paper
delivers while the attack evaluation is still pending. A subtitle carrying it would help,
e.g. *"…: Measurement Limits and Evaluation Controls for Semantic Entropy"*. I would not
retitle around the budget result specifically until the confirmatory attack run lands and
the final balance of the paper is known — that is a decision for after the run, not before.

---

## 7. ERRATA AND OWED WORK FOUND WHILE DOING THIS

Ordered by how much damage each would do if it reached a referee.

1. **`results/n_scaling_grid.md` §1, N=40 row is mis-specified.** The column headed
   "floor = min non-zero FPR" prints the ceiling-atom mass, which at N=40 is 0/200. The
   actual minimum non-zero achievable FPR is 4/200 = 2.0% [0.8, 5.0]. The "next FPR" column
   prints 2.5%, the *second* firing point, so the first is absent from the table. At N=10
   and N=20 the two definitions coincide, so the bug only surfaces at N=40 — where it makes
   the row read "any false-alarm rate down to zero is available". Fix
   `scripts/n_scaling_grid.py` before this number is quoted anywhere.
2. **Every replayed row in `n_scaling_grid.md` carries a one-component interval.** The
   Wilson interval is computed on replicate 0 and omits subset-choice variance. N=20 floor
   is 3.0% [1.4, 6.4] as printed; with both components it is 2.75% [0.5, 5.5], replicate
   range [1.5, 4.0]. Either add the second component or label the interval as
   target-sampling only.
3. **The drift control never fired.** `n_scaling_grid.py` emits the drift control only when
   N=10 is directly re-measured on the same box; it was not, so subsetting error and
   generation drift between the June cache and the August run are unidentified. A clean
   direct N=10 pass on the current machine (roughly a quarter of the N=40 cost) separates
   them and is the highest-value cheap run outstanding.
4. **The N=10 citation claim is unverified.** The re-scope rests on "N=10 is the budget
   Kuhn, Farquhar and Kossen all use". I could not verify this from the repository. Get a
   page or table cite for each of the three before the Abstract sentence ships.
5. **`farquhar_eq5` raw has Spearman ρ = 0.381 against discrete.** Per the decision table
   fixed before the data, low ρ means AUROC results would need re-deriving under Eq. (5).
   The report explains the raw variant's behaviour as an expected large-spread artefact and
   the length-normalised variant preserves order (ρ = 0.989), so the paper is fine — but
   this is the one place where the overnight summary was more comfortable than the artefact.
   State explicitly that the AUROC claim is robust under length-normalised Eq. (5) and that
   length normalisation is the modelling choice doing the work. Measured AUROCs are in §4.6
   M4 so the paper can show rather than assert it.
6. **`figures/fig_achievable_roc*` and `fig1_ceiling*` are N=10-only.** If the budget
   finding enters the Discussion, the achievable-ROC figure wants a companion panel at
   N=20/N=40, or at minimum a caption line confining it to N=10.
7. **Abstract word count.** It was cut to ~200 words on 2026-08-13. The long-form
   replacement in §2.3 adds roughly 55 words. Use the short form unless the budget has moved.

---

## 8. REPRODUCTION

All numbers new to this document come from two scratch scripts run against committed
artefacts; nothing was written into `results/` except this file.

- Inputs: `results/n_scaling_ckpt.jsonl` (400 records, N=40, full pairwise verdict matrices),
  `\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research\samples\wk4_full_2000q\relabeled.jsonl`
  (Week-4 direct N=10 scores and span-oracle labels),
  `results/rescore_likelihoods_scores.csv`, `results/cluster_count_bound.md`,
  `results/winners_curse_se_false_alarm.md`, `results/n_scaling_plan.md` §5.
- Replay path: the project's own `se.entropy.cluster_and_score` driven by a recorded-verdict
  NLI stub, and the same `budget_scores` subset-selection RNG as
  `scripts/n_scaling_grid.py`, so replayed scores are bit-identical to that report's.
- **Population check passed:** the 200 correct and 200 hallucinating question ids in the
  N=40 checkpoint are *identical* to `_stratum_ids("right"/"wrong", seed=0)[:200]`, i.e. to
  the Week-4 fair pool. Every cross-budget and direct-vs-replay comparison above is
  therefore paired on the same targets, which is what licenses the paired intervals.
- Interpreter: `.venv/Scripts/python.exe` (the repo venv; the bare Windows Python lacks
  `transformers`, which `se.entropy` imports transitively).
- Bootstrap: 4,000 resamples, seed 0, stratified over the 200 negatives and 200 positives
  jointly, with the subset replicate resampled alongside where a budget is replayed
  (R = 20 subset draws at N=10 and N=20; N=40 is measured and has one).
- TPR "matched at an achieved rate" is read off the upper convex hull of the achievable
  points — the randomised-rule frontier — because the deterministic grids at different
  budgets do not align and the deterministic statistic is discontinuous (§1.5). Deterministic
  `at_most` values are reported alongside wherever an operator-facing number is quoted.

Scratch scripts (not committed):
`…/scratchpad/budget_tradeoff.py`, `budget_tradeoff2.py`, `budget_tradeoff3.py`.
Fold the parts worth keeping into `scripts/n_scaling_grid.py` — specifically the matched-FPR
TPR comparison, the band-decomposed pAUC, and the two-component interval — so the report
regenerates them rather than depending on scratch files.
