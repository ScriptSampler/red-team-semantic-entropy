# Review outcome: SEP / defense / transfer code (2026-06-25, overnight)

An adversarial 3-dimension review with independent verification ran over the new
experiment code before it consumes GPU time. It returned 7 confirmed findings and
0 false positives (the reviewer pre-dismissed several non-bugs). All were real and
all were fixed; none had run yet, so no results were affected.

## Critical (data integrity / validity)
- **C1 wk_defense.py** — vanilla attack effect mixed a freshly-recomputed SE(Q)
  with the cached SE(Q'). Now uses cached `entropy_before`/`entropy_after` for
  both sides, so the baseline the defense is measured against is consistent.
- **C2 wk_seps_transfer.py** — the binarization threshold (median) was computed on
  the full set then split, leaking held-out entropies into the label definition.
  Threshold is now computed on the training entropies only.
- **C3 wk_seps_transfer.py** — the 70/30 split took the first 70% of entropy.jsonl
  in file (sample) order. Added a seeded permutation so the split is random and
  reproducible.

## High (experiment validity)
- **H1 defense.py** — every paraphrase variant sampled SE with the same fixed
  seed=0, correlating the RNG draws and defeating the noise-averaging the defense
  is supposed to demonstrate. Variant sampling now forces seed=None.
- **H2 defense.py** — a degenerate paraphrase (proposer returns the input
  unchanged) re-added the original, biasing the median toward it. Variants are now
  deduped by normalised text.

## Medium (strength-of-claim / observability)
- **M1 wk_defense.py** — reduction reported as ratio-of-means (outlier-dominated).
  Now reports the per-question paired reduction (median + mean).
- **M2 wk_seps_transfer.py** — single-class held-out set silently skipped the AUROC
  line. Now logs the undefined case.

All fixes verified by re-running the CPU logic suite (20 passing) and recompiling.
The reviewer correctly dismissed several false positives (feature/label alignment,
campaign filename matching, numpy bool .mean(), dataclass field round-trip).
