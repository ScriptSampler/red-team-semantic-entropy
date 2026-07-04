# Embedding-threshold calibration (intfloat/e5-base-unsupervised)

Threshold to FREEZE before the definitive embedding arm (critic entry 15/16). AUROC = the encoder's paraphrase-discrimination power on disjoint labeled pairs. The TriviaQA-aliases set is DOMAIN-MATCHED (short factoid spans, the actual clustering task); the sentence sets (STS-B/PAWS) test general/adversarial sentence similarity.

## TriviaQA-aliases (SHORT ANSWER — the real clustering task)
positives=1500, easy_neg=1500, hard_neg=1500

### pos vs EASY negatives (distant answers — trivial)  (n=3000, paraphrase=1500)
- paraphrase-discrimination AUROC: 0.833
- Youden-J cosine threshold: 0.718  (J=0.603); band [0.688, 0.748]

### pos vs HARD negatives (REHABILITATION CRITERION — near-miss shared-token/numeric)  (n=3000, paraphrase=1500)
- paraphrase-discrimination AUROC: 0.512
- Youden-J cosine threshold: 0.838  (J=0.161); band [0.808, 0.868]

> Rehabilitation (critic entry 16): e5 is a usable finding-14 adjudicator ONLY IF the pos-vs-HARD AUROC is high. A high pos-vs-easy AUROC does NOT rehabilitate it — that is the STS-B/easy regime; the attack produces the HARD (word-preserving, meaning-shifted) case. If pos-vs-HARD is near-chance, the adjudicator must be a victim- and NLI-independent, self-validated LLM-judge (definitive-run).

### STS-B (sentence)  (n=653, paraphrase=264)
- paraphrase-discrimination AUROC: 0.989
- Youden-J cosine threshold: 0.856  (J=0.912); band [0.826, 0.886]

### PAWS (sentence, hard negatives)  (n=1500, paraphrase=655)
- paraphrase-discrimination AUROC: 0.633
- Youden-J cosine threshold: 0.992  (J=0.224); band [0.962, 1.022]

