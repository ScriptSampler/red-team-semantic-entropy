# LLM-judge self-validation (Qwen/Qwen2.5-7B-Instruct)

> **B3 re-spec (critique_log 21), disclosed.** The numbers below are from a prior run; the
> deployed null-control config is the **symmetric** judge, so a symmetric re-run is OWED to
> lock ONE cited number (this file shows hard-neg **0.884**; the paper text has cited
> **0.92** — that inconsistency must not survive; cite the deployed-config number). The
> pre-registered gate (hard>=0.8 AND pos>=0.8) is NOT met (pos 0.700), so a bare "usable"
> verdict would be a silent override. See the dual verdict below.

Accuracy (95% CI) on domain-matched short-answer strata (the set that disqualified e5). The judge may adjudicate finding 14 ONLY IF hard-negative accuracy is high (e5 was ~0.51 AUROC here). CAVEAT: these strata are clean gold aliases; the judge will cluster messy real answer SAMPLES (hedges, sentences) — validate on realistic sampled pairs too, and cross-check the judge against a human sample (finding 15) before trusting it as the sole oracle.

- positives (aliases -> SAME):          0.700 [0.640, 0.756]  (n=250)
- easy negatives (distant -> NOT):      1.000 [1.000, 1.000]  (n=250)
- HARD negatives (near-miss -> NOT):    0.884 [0.844, 0.924]  (n=250)  <-- CRITERION

PRE-REGISTERED gate (hard>=0.8 AND pos>=0.8): **FAIL** — pos 0.700 < 0.8.

HARD-NEG-PRIMARY re-spec for FALSE-ALARM adjudication (critique_log 21, B3): **USABLE for FA**
(hard-neg 0.884 >= 0.8). OUTCOME-TRIGGERED DEVIATION, disclosed: the pos shortfall is
over-splitting of genuine aliases (partly TriviaQA label noise the judge correctly rejects),
which is CONSERVATIVE for false-alarm (it inflates baseline entropy, so a surviving FA effect
is understated) but NOT for hide (it would OVERSTATE hide); scope this oracle to FA only.

STILL OWED before the paper may cite the judge as sole adjudicator (all four):
1. re-run on the DEPLOYED (symmetric) config to lock ONE hard-neg number; reconcile 0.884 vs 0.92;
2. validate on messy real sampled pairs, not just clean gold aliases;
3. a differential-over-splitting check — attack vs benign cluster counts must not diverge;
4. report the NLI/exact-match bracket ALONGSIDE, so no headline rests solely on this oracle.
