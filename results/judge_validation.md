# LLM-judge self-validation (Qwen/Qwen2.5-7B-Instruct)

Accuracy (95% CI) on domain-matched short-answer strata (the set that disqualified e5). The judge may adjudicate finding 14 ONLY IF hard-negative accuracy is high (e5 was ~0.51 AUROC here). CAVEAT: these strata are clean gold aliases; the judge will cluster messy real answer SAMPLES (hedges, sentences) — validate on realistic sampled pairs too, and cross-check the judge against a human sample (finding 15) before trusting it as the sole oracle.

- positives (aliases -> SAME):          0.390 [0.337, 0.443]  (n=300)
- easy negatives (distant -> NOT):      1.000 [1.000, 1.000]  (n=300)
- HARD negatives (near-miss -> NOT):    0.883 [0.847, 0.917]  (n=300)  <-- CRITERION

Verdict: NOT usable -> keep the NLI/exact-match bracket.
