# LLM-judge self-validation (Qwen/Qwen2.5-7B-Instruct, symmetric)

Accuracy (95% CI) on domain-matched short-answer strata (the set that disqualified e5). The judge may adjudicate finding 14 ONLY IF hard-negative accuracy is high (e5 was ~0.51 AUROC here). CAVEAT: these strata are clean gold aliases; the judge will cluster messy real answer SAMPLES (hedges, sentences) — validate on realistic sampled pairs too, and cross-check the judge against a human sample (finding 15) before trusting it as the sole oracle.

- positives (aliases -> SAME):          0.650 [0.593, 0.703]  (n=300)
- easy negatives (distant -> NOT):      1.000 [1.000, 1.000]  (n=300)
- HARD negatives (near-miss -> NOT):    0.930 [0.900, 0.957]  (n=300)  <-- CRITERION

PRE-REGISTERED gate (hard>=0.8 AND pos>=0.8): FAIL — pos 0.650 < 0.8.

HARD-NEG-PRIMARY re-spec for FALSE-ALARM adjudication (critique_log 21, B3): USABLE for FA (hard-neg 0.930 >= 0.8). OUTCOME-TRIGGERED DEVIATION, disclosed: the pos shortfall is over-splitting of genuine aliases, CONSERVATIVE for false-alarm (inflates baseline entropy -> a surviving FA effect is understated) but NOT for hide; scope this oracle to FA only. STILL OWED before the paper cites it as sole adjudicator: (i) this number is the DEPLOYED config (symmetric) — cite THIS one, not a mixed sym/asym pair; (ii) validate on messy real sampled pairs, not just clean gold aliases; (iii) a differential-over-splitting check (attack vs benign cluster counts must not diverge); (iv) report the NLI/exact-match bracket ALONGSIDE so no headline rests solely on this.
