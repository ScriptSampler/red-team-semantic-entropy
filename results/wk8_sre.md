# Week 8: SRE vs SE on 100 TriviaQA questions

> SUPERSEDED (pre-bugfix). These numbers came from a broken reformulation
> generator: it used greedy decoding, so the 3 reformulations were identical
> and collapsed to ~1 ("mean reformulations kept: 0.92"), degrading SRE to
> vanilla SE on a single variant with FEWER pooled samples than SE. That is why
> SRE (0.654) underperforms SE (0.749) here, opposite to the paper. Fixed in
> sre.py (generate_reformulations now samples); cache cleared so wk8 recomputes
> with the fix. Kept for the record.

questions: 60
greedy correct: 43/60

vanilla SE AUROC: 0.749  (paper 0.828)
SRE AUROC:        0.654  (paper 0.871)
SRE - SE:         -0.095  (paper +0.043)

mean SE entropy:  1.626
mean SRE entropy: 1.314
mean reformulations kept: 0.92

Note: SRE here uses NLI union-find clustering, not the paper's full
energy-based HSC. If AUROC is far below 0.871, that backend is the
first thing to revisit; the plan permits dropping SRE to future work.
