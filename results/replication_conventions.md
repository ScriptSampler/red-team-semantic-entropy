# Replication AUROC: the full (oracle x convention) grid

Producing script: `scripts/replication_conventions.py`. One code path, one source: the
cached Phase-1 pool (raw generation text + NLI-clustered SE entropy). The entropy is
independent of the correctness oracle, so only the LABEL moves across this grid.

pool: 2000 questions (samples n=2000, entropy n=2000)
label = NOT correct (hallucination is the positive class); score = SE entropy, nats.
CIs are 2000-replicate percentile bootstrap over questions, seed 0.

## The six cells the paper needs

| oracle | convention | correct rate | AUROC | 95% CI |
| --- | --- | --- | --- | --- |
| substring | greedy | 1440/2000 (72.0%) | **0.6971** | [0.6725, 0.7211] |
| substring | majority | 1400/2000 (70.0%) | **0.7296** | [0.7060, 0.7522] |
| substring | all_samples | 810/2000 (40.5%) | **0.7868** | [0.7651, 0.8081] |
| span | greedy | 1424/2000 (71.2%) | **0.6937** | [0.6692, 0.7172] |
| span | majority | 1381/2000 (69.0%) | **0.7292** | [0.7051, 0.7521] |
| span | all_samples | 752/2000 (37.6%) | **0.7898** | [0.7685, 0.8113] |

## Supplementary: strict exact-match oracle, and the cached labels

`cached` = the `greedy_correct` / `samples_correct` booleans stored in samples.jsonl at
sampling time (the substring oracle of that day). These are what wk4_auroc.py scored,
so they are the row that must reproduce `results/replication_auroc.json`.

| oracle | convention | correct rate | AUROC | 95% CI |
| --- | --- | --- | --- | --- |
| strict | greedy | 8/2000 (0.4%) | 0.5615 | [0.3953, 0.7342] |
| strict | majority | 3/2000 (0.1%) | 0.7618 | [0.5808, 0.9803] |
| strict | all_samples | 0/2000 (0.0%) | nan | [nan, nan] |
| cached | greedy | 1440/2000 (72.0%) | 0.6977 | [0.6732, 0.7218] |
| cached | majority | 1401/2000 (70.0%) | 0.7296 | [0.7060, 0.7524] |
| cached | all_samples | 813/2000 (40.6%) | 0.7868 | [0.7648, 0.8081] |

## Reconciliation: cached labels vs a fresh substring recompute

greedy labels that disagree: **4** of 2000
per-sample labels that disagree: **33** of 20000

Stored `results/replication_auroc.json` (gitignored, so this may be absent on a
fresh clone) vs the `cached` row recomputed here:

| convention | stored JSON | recomputed from cached labels | delta |
| --- | --- | --- | --- |
| greedy | 0.697729 | 0.697729 | +0.00e+00 |
| majority | 0.729648 | 0.729648 | +0.00e+00 |
| all_samples | 0.786788 | 0.786788 | +0.00e+00 |

If the cached row reproduces the JSON but the fresh `substring` row does not, the
difference is the oracle CODE having changed since sampling (`normalize_answer` now
DELETES punctuation rather than replacing it with a space), not a scoring bug. The
disagreement counts above size that effect directly.

## What this means for the paper

Span-oracle spread (the number experiments.tex calls the convention span): 0.0962 (0.6937 to 0.7898).
Substring-oracle spread: 0.0897.
Gap from the operative span/greedy figure to the published 0.828: 0.1343. Gap from the span/all-samples figure: 0.0382.

The all-samples convention is the one mechanically coupled to the score (a
ten-of-ten-correct sample set is likelier to be semantically homogeneous, hence
low-entropy), so its AUROC is partly the score scored against itself. It is reported
here for completeness, not as the headline.
