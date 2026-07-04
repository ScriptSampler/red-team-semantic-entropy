# Embedding-threshold calibration (intfloat/e5-base-unsupervised)

Threshold to FREEZE before the definitive embedding arm (critic entry 15). AUROC = the encoder's paraphrase-discrimination power on disjoint labeled pairs.

## STS-B  (n=653, paraphrase=264)
- paraphrase-discrimination AUROC: 0.989
- Youden-J cosine threshold: 0.856  (J=0.912)
- suggested band: [0.826, 0.886] — run the null-control conclusion across it and show it does not swing.

## PAWS  (n=800, paraphrase=359)
- paraphrase-discrimination AUROC: 0.624
- Youden-J cosine threshold: 0.990  (J=0.213)
- suggested band: [0.960, 1.020] — run the null-control conclusion across it and show it does not swing.

