# START HERE — state as of Sun 2026-08-02 05:15

> ## ⚠ READ THIS FIRST (added 05:35, after independent verification)
> A 4-agent verification re-derived every number from raw data. **All arithmetic reproduced,
> but seven reasoning flaws are invalidating** — see `results/CORRECTIONS_2026-08-02.md`.
> **The headline verdict below is overturned:** the "conservative" tie rule is a ~61x
> overcorrection (exchangeable credit is a/(b+1) with b>=1; measured mean b=60.4), and *that*,
> not the ceiling, made the test degenerate. With a correct randomized rule the test is
> calibrated and powerful **at N=10** (0.40/0.82/0.99 at m=30/50/60) — better than the N=20 fix
> at zero GPU cost — and power RISES with m. So finding 2 ("more samples don't help ⇒ FA not
> identifiable") does **not** follow; the N=20 *measurement* stands, the *inference* falls.
> Finding 3's numbers are also overstated (separation not significant, p=0.296; "2.8x" is
> ~2.1x censoring-corrected with a CI spanning zero). **First task next session: implement the
> exchangeable tie rule and re-open the verdict.**


## The night rewrote what this paper is about

We set out to run the definitive judge experiment. We found instead that **the measurement
cannot support the claim we were trying to make — and that this is the stronger result.**
Four findings, each verified and gated through the critic:

1. **The FA attack saturates the metric.** Semantic entropy is capped at log(N); at N=10
   that is 2.3026 nats and **39/80 (49%) of attacked false-alarm targets finish exactly
   there**. 8/80 baselines already sit there (structurally unattackable). On the first
   ablation target the attack, a null-objective beam, and *plain random paraphrasing* all
   landed on exactly 2.3026. → `results/ceiling_saturation_finding.md`
2. **More samples do not fix it — the censoring is STRUCTURAL.** N=20 pilot on 15 saturated
   targets: baselines rise with N too, so realized headroom grows only **+0.11 median**
   (not the naive +0.693). Saturation 46% → 41%; the exceedance test stays **degenerate**
   (power 0.00 *and* H0 level 0.000 — it cannot reject under the null either).
   → `results/n20_verdict.md`, `results/power_under_ceiling.md`
3. **The detector has almost no dynamic range where the attack operates.** On clean data the
   whole correct-vs-wrong separation is **0.184 nats (Cohen's d = 0.28)**; 26% of *correct*
   answers already sit in the top decile of the scale; the estimator takes 22 distinct
   values. → `results/dynamic_range_finding.md`
4. **~2/3 of the raw FA effect is selection-on-noise.** Re-scoring the *selected* paraphrase
   at the same N with a fresh seed: mean move **+0.811 → +0.263, retention 32%** (n=10 of 80,
   run continuing). → `results/winners_curse_partial.md`

**The identifiable FA number** (ceiling-immune, verified valid despite the incomplete hide
cell because the threshold is set on the clean negatives): at a 10% clean-data FPR,
**31/80 = 39% [29%, 49%] of correct answers flip unflagged → flagged**. Still raw — the
benign floor must still say what fraction *random* paraphrasing flips.

## Do these next, in order

1. **Let the winner's-curse run finish** (`scripts/winners_curse_reeval.py`, checkpointed at
   `results/winners_curse_ckpt_se_false_alarm_def.jsonl`; re-run the same command to resume).
   Replace the n=10 retention figure with the n=80 one.
2. **Finish the hide cell** (17 → 80, ~12 GPU-h):
   `recompute_fair.py --only se_hide --n 80 --tag _def`. Hide is uncensored (0/17 at the
   floor, 1.661 nats headroom vs FA's 0.826) and is where the pre-registered rule can
   actually execute. **Pre-commit hide's detectable-effect floor BEFORE the data lands** — my
   simulation says hide is functional but only detects large effects (power 0.04–0.08 at 2×,
   0.25–0.40 at 5×–10×, m=50).
   ⚠ **The B3 judge re-spec is FA-ONLY.** Over-splitting is conservative for FA but
   *overstates* hide. Either re-validate the judge for hide or report hide attribution via
   the NLI/exact **bracket only**. Do not let hide silently inherit the FA-scoped judge.
3. **Quantify how often BENIGN paraphrases reach the ceiling** (from the `--dump_diag` benign
   lists). If they reach it often, the sharpest honest claim is that **inducing a false alarm
   needs no adversarial optimisation at all** — evidenced rather than asserted. OWED.
4. Resume the null-objective ablation (paused 1/10, checkpointed) — now the validity gate for
   the exchangeability null; run the check on the cheap NLI arm with many more targets.

## Framing (critic-approved)

FA-led **survives**, with the lead claim reframed: not "we attack FA and here is the effect
size" but "**FA is where the detector has no headroom** — 49% saturation, 26% of clean
correct answers already in the top decile, whole-class separation 0.184 nats — so inducing
false alarms is easy *and* unmeasurable in the detector's own units." The defense against
"that's a dodge" is that we *proved* the censoring is structural rather than a budget
artifact. `framing_decision.md` predates the saturation finding, so the reframe follows the
evidence.

**Forking-path risk to manage:** "led with FA → FA unmeasurable → rule scope moved to hide"
reads as direction-shopping unless the whole timestamped sequence is in the **main text**:
FA-led choice → ceiling discovery → pre-committed power bar → verdict → scope move.

## Locked / pre-committed (do not re-litigate)
- Judge = **0.93 [0.90, 0.96], n=300**, symmetric deployed config; pre-registered gate FAILS
  on positives (0.65), disclosed in Methods main text, FA-only scope, bracket alongside.
- Ties: conservative primary, mid-p secondary, strict = disqualified diagnostic.
- No cross-direction comparisons in nats (FA has half of hide's headroom) — a Methods section.
- Four **triggered deviations** logged (critique_log 21–24): e5→judge; individual-benign→
  budget-matched-max; budget-matched-max→exact beta-binomial at pre-committed m; and rule
  scope FA→hide.

## Reference
`docs/critique_log.md` 21–24 (rulings + every pre-commitment, including 23a where I tightened
my own ambiguous bar *before* the data). `docs/paper_review_punchlist.md` (25-item review).
129 tests passing.
