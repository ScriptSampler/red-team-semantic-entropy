# B1: fair stratified-random pool vs extreme-entropy ablation

full pool strata: wrong=576, right=1424 (of 2000)

## Shared-pool invariant (detector-independent selection)
assert_shared_pool passed: two independent calls return identical ids.
selection reads correctness label + seed only, never entropy -> the SE and
SRE campaigns use the IDENTICAL 200 hide + 200 false-alarm ids.

## Entropy representativeness (fair pool vs full stratum)
mean / p10 / p50 / p90 of clean SE entropy (nats). Fair pool should MATCH
the full stratum; the ablation is deliberately skewed to the extremes.

| stratum | source | mean | p10 | p50 | p90 |
| --- | --- | --- | --- | --- | --- |
| wrong | fair pool | 1.843 | 1.218 | 2.025 | 2.303 |
| wrong | full stratum | 1.846 | 1.168 | 2.025 | 2.303 |
| right | fair pool | 1.380 | 0.325 | 1.498 | 2.164 |
| right | full stratum | 1.399 | 0.325 | 1.498 | 2.303 |

## Clean SE AUROC: fair pool vs extreme ablation (the headline contrast)
| pool | clean SE AUROC (95% CI) |
| --- | --- |
| fair (stratified-random) | 0.704 [0.653, 0.753] |
| extreme-entropy ablation | 1.000 [1.000, 1.000] |

The fair pool is the HONEST detector ranking on representative data. The
ablation's ~1.0 is the selection rule reflected back and was never real.
Post-attack AUROC (GPU recompute) will be measured against the fair number,
so the reported degradation shrinks — that is the point of clearing B1.
