# CORRECTIONS — independent verification overturns two of tonight's conclusions

An independent 4-agent verification re-derived every number in tonight's findings from the
raw JSONL. **Every arithmetic figure reproduced exactly — not one raw calculation was
wrong.** The damage is entirely in *denominators, estimands, and derived claims*. Seven
flaws are invalidating. Read this before quoting anything from tonight.

---

## ⚠ C9/C11 — THE BIG ONE: my "conservative" tie rule is wrong by construction, and it is
what produced the degeneracy. **The N=20 verdict is therefore NOT safe.**

I adopted `ties="conservative"` (a benign draw that *equals* the attack max counts as an
exceedance) as the safe choice, and the critic approved it. It is not conservative — it is a
**~61× overcorrection**.

Under exchangeability the credit for ties is itself a random variable: with `a` benign draws
tied at the top and `b` attack candidates also at that value, T ~ BetaBinomial(a; 1, b), so
E[T] = a/(b+1). Crucially **b ≥ 1 always**, because the attack's own maximum is one of the
tied values — so the maximum defensible credit is a/2, never a. On our saturated targets the
measured mean b is **60.4**, so counting all `a` ties overcounts by roughly 61×.

That manufactured artifact is what made the test degenerate. With a correct
(randomized/exchangeable) tie rule the test is **calibrated and powerful at N=10**:

| tie rule | m=30 | m=50 | m=60 |
|---|---|---|---|
| conservative (what I used) | power 0.00 | 0.00 | 0.00 |
| exchangeable/randomized | **0.403** | **0.823** | **0.993** |

And the corrected rule at **N=10, m=30 (0.403 / 0.823 / 0.993)** beats lifting to **N=20
under the broken rule (0.46 / 0.77)** — **at zero GPU cost**.

**Consequences:**
- "Increasing m makes it worse" (in `power_under_ceiling.md`) is **backwards**. Under the
  corrected rule power *rises* with m: 0.535 → 0.778 → 0.800 at 2× for m = 30/50/60.
- The verdict "FA is not identifiable at any feasible N" does **not** follow. The obstacle
  was the statistic, not the ceiling. `results/n20_verdict.md` and
  `results/power_under_ceiling.md` are **superseded pending a re-run with the corrected rule**.
- The N=20 pilot result itself stands (headroom gain is genuinely only +0.11 median); what
  falls is the inference drawn from it.
- **C10:** the score is atomic *everywhere*, not just at the ceiling — SE over N=10 lives on
  a 39-point lattice; P(two draws tie) = 0.203, of which only 41% is the ceiling atom. So
  ties matter for **hide** too, which I wrongly treated as immune.

## ⚠ C3/C4/C5 — the dynamic-range claims are overstated

- **C3 (invalidating):** I wrote that d = 0.28 "is what AUROC 0.704 looks like". That is
  false *and backwards*: d = 0.28 ⇒ AUROC = Φ(d/√2) = **0.579**, which is exactly the 0.579
  measured on this pool; AUROC 0.704 ⇒ d = **0.758**. Worse, `fa_n80_milestone.md`
  explicitly warned against reconciling the attacked-subset AUROC with the fair-pool 0.704 —
  and I then did precisely that.
- **C4 (invalidating):** the +0.184-nat class separation is **not significant** — bootstrap
  95% CI **[−0.136, +0.488]**, permutation p = 0.296. It is a sample statistic from n=17
  wrong answers, not "a fixed property of the detector". On the repo's own fair-pool strata
  it is **+0.463** nats, 2.5× larger.
- **C5 (invalidating):** the headline "the attack moves ~2.8× the detector's whole signal"
  has bootstrap CI **[−24.19, +28.48]** (12.6% of draws negative). Censoring-corrected
  (Tobit): **2.13×**; on fair-pool strata: **1.13×**. Honest statement: **roughly one class
  separation, not three.**
- **C6/C7:** the wrong-answer group is censored *2.4× more* than the correct group (23.5% vs
  10% at cap) — an omission that biases the separation downward; and all 22 distinct values
  come from the 80 correct targets, with the 17 wrong targets contributing 10 values, every
  one a subset.

## C1/C2 — ceiling finding: the arithmetic is right, two denominators are wrong

- **C1:** 49% is the *total* at-ceiling rate. **Attack-induced** saturation is
  **31/80 = 38.75%** (8 targets were already pinned and never moved).
- **C2:** "66% mean / 83% median of headroom consumed" was computed on **n=72**, silently
  dropping the 8 zero-headroom targets, and the estimand was never stated. On the 41
  **uncensored** targets it is **mean 39.9%, median 38.6%**.
- **Confirmed and strengthened:** corr(headroom, move) = +0.71 (_defb; _def gave +0.70) holds *within the uncensored
  subset* (+0.67), so it is not a censoring artifact. The strongest number in that document.

## What survives unchanged

The ceiling exists and is measured correctly (~~39/80 at ln(10) exactly~~ **42/80 at ln(10)
exactly** — 39/80 is the superseded `wk9_def` count; the definitive instrumented `_defb` cell
gives **42/80 = 52.5%** at the cap after attack and **34/80 = 42.5%** attack-induced
[`figures/ceiling_figures_stats.json`, `results/ceiling_saturation_finding.md`]; 8/80 baselines
pinned, all with move exactly 0.000 and zero successes — that one is unchanged under `_defb`);
the beta-binomial null derivation
is correct (verified to 3e-13 against scipy, and by Monte Carlo across gamma/Cauchy/exponential);
the headroom–success relationship is real; the N=20 headroom-gain measurement is real; and
the winner's-curse re-evaluation design is sound (its number is still partial at n=10/80).

## Required next actions, in order

1. **Implement the exchangeable/randomized tie rule** in `se.stats.exceedance_counts`
   (E[T] = a/(b+1), which needs the count of attack candidates tied at the max, so the
   attack-side tie count must be recorded too). Re-run all power simulations.
2. **Re-open the N=20 verdict** with the corrected statistic before any framing rests on it.
3. Fix C3/C4/C5 in `dynamic_range_finding.md` — replace "2.8× the signal" with the
   censoring-corrected ~2.1× *and its CI*, drop the AUROC reconciliation entirely, and
   report the separation with its interval and permutation p.
4. Restate C1/C2 with explicit denominators and a named estimand.
