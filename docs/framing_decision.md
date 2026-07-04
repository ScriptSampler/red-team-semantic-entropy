# Framing decision — your call (2026-07-04, ~23:35 Sat)

Tonight's investigation resolved the deepest question in the project, and it forces a
choice about what the paper *claims*. This is a researcher's decision, not one I should
make unilaterally — here is everything you need to make it.

## What we now know (all critic-gated; n=6 is machinery-validation, not a result)

The false-alarm attack moves Semantic Entropy. The question is **whether that move is a
real change in the model's answer distribution, or an artifact of the NLI clusterer that
SE (and the attack's feasibility gate) share.** The 3-arm null control brackets it:

| clusterer | net (attack − benign) | what it means |
| --- | --- | --- |
| **shared NLI** (the detector's own) | **+0.636 [+0.239, +1.034]** | attack robustly beats benign paraphrasing — but this is the *confounded* measure |
| **exact-match** (independent, strict) | +0.140 [−0.004, +0.291] | effect largely collapses — but exact-match is saturated, can't adjudicate |
| **e5 embedding** (independent, semantic) | ~0 (degenerate) | **e5 can't adjudicate: AUROC 0.512 (chance) on hard near-miss answers** |

The adjudicator problem is **real and hard**: to tell "attack changed meaning" from "NLI
clustered differently," you need an independent oracle that can distinguish word-preserving
meaning-shifts (the adversarial case). Sentence embedders can't — e5 is near-chance on
exactly that case, in both the sentence domain (PAWS 0.633) and the short-answer domain
(hard-negative 0.512). The only remaining cheap-ish option is a **self-validated LLM-judge**
(a second model, not the victim Llama, not NLI-derived), which is a definitive-run item.

## The two framings

### Option A — attack-led ("we break Semantic Entropy")
Claim: meaning-preserving paraphrases defeat SE (induced false alarms + hidden hallucinations).
- **Requires** adjudicating the attack is real → a validated LLM-judge at n≥80 → **GPU-days +
  a second model + genuine risk the effect collapses** into the clusterer-artifact bracket.
- If the LLM-judge shows the effect survives: strong, but a crowded space (SECA/CORVUS-adjacent).
- If it collapses: the headline evaporates and you've spent the compute to disprove your own hook.

### Option B — protocol-led ("how to evaluate these attacks, and why prior claims are unsupported") — CRITIC-RECOMMENDED
Claim: we introduce a circularity-free, null-controlled evaluation protocol and use it to
show that **the standard shared-NLI evaluation cannot distinguish a real paraphrase attack
from a clusterer artifact**, that cheap independent oracles fail the adversarial case, and
therefore **prior single-NLI attack claims on SE are not adequately supported.** The attack
is a case study within the protocol; the negative/bracketed attribution *is* the finding.
- **Does not depend on the risky adjudication.** The adjudication *difficulty* is evidence FOR
  the contribution.
- Durable and honest; it makes the *next* person's attack claim harder to fake — a genuine
  service to the field.
- The attack still appears as a real secondary result: "the optimised attack robustly beats
  benign paraphrasing under the detector's own clusterer (net +0.636)" is true and
  interesting — it just isn't sufficient for "we changed the model's uncertainty."

## The critic's recommendation and mine
Both: **Option B.** Lead with the protocol; report the attack as a strong secondary result
inside the bracket; state the attribution is unresolved-and-bounded; make the LLM-judge the
one confirmatory experiment that could upgrade it to Option A later. Rationale: B is the
stronger, more defensible paper *regardless* of how the adjudication turns out, and it turns
tonight's "we couldn't cleanly adjudicate" from a weakness into the central result. A is a
bet that costs GPU-days to place and can lose.

## What each path needs next (definitive run)
- **Both:** n≥80/stratum attack matrix (the ~39 GPU-hour / optimiser-budget decision), the
  3-band null control at the calibrated bracket, finding-16 sampled-status.
- **B (minimum):** reframe the Introduction to lead with the protocol; report the NLI/exact
  bracket honestly; one genuine LLM-judge attempt (2nd model) so the bracket is "after trying
  the strongest tool," not a shrug.
- **A (additional):** the LLM-judge must *succeed* at n≥80 and show the effect survives.

## Decision for you
1. **Which framing** — A (attack-led, riskier) or B (protocol-led, critic + I recommend)?
2. **Second model for the LLM-judge** — do you have / want to load a non-Llama, non-NLI
   instruct model (or use an API, which is behind auth not available to me here)? This gates
   both the (a) claim and the finding-15 equivalence audit.
3. **Definitive-run compute** — optimiser budget vs n (see definitive_run_plan.md): full n=80
   (~39 GPU-h), or a cheaper optimiser / smaller n with honest wide CIs?

Nothing here is blocked on me; it's blocked on these three calls. I'll draft the Option-B
reframed Introduction + the honest finding-14 Methods paragraph next (clearly marked as a
proposed reframe you can accept or discard), so you can see what B reads like before deciding.
