> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.

# Week 10: full attack result matrix

Label convention: positive class is the hallucination case.
Hide campaign questions are model-wrong (label 1); False-alarm are
model-right (label 0). Clean AUROC uses pre-attack entropy, attacked
AUROC uses the adversarial paraphrase's entropy.

## triviaqa x se
pool: 15 hide (wrong) + 15 false-alarm (right) = 30
clean AUROC:    1.000
attacked AUROC: 0.787
degradation:    +0.213
Hide success rate:        87%
False-alarm success rate: 80%

## triviaqa x sre
pool: 15 hide (wrong) + 15 false-alarm (right) = 30
clean AUROC:    0.742
attacked AUROC: 0.176
degradation:    +0.567
Hide success rate:        73%
False-alarm success rate: 80%

## squad x se: no campaign files yet, skipped

## squad x sre: no campaign files yet, skipped

## Summary table
| dataset | detector | clean AUROC | attacked AUROC | degradation |
| ------- | -------- | ----------- | -------------- | ----------- |
| triviaqa | se | 1.000 | 0.787 | +0.213 |
| triviaqa | sre | 0.742 | 0.176 | +0.567 |

AUROC numbers reported: 4 (target 12+)

If SRE degrades less than SE under the same attacks, that is the
'SRE is more robust' story. If both collapse, that is the headline
vulnerability result. Either is a publishable finding.
