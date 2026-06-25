# Phase 1 replication results: SE on TriviaQA

## Configuration
- model: meta-llama/Llama-3.1-8B-Instruct, 4-bit nf4, bf16 compute
- NLI: microsoft/deberta-large-mnli, bidirectional argmax entailment
- dataset: TriviaQA rc.nocontext validation, first 2000 questions
- generation: N=10 samples at T=1.0, max_new_tokens=48, seed=0
- entropy: Shannon over cluster sizes, natural log

## Coverage
questions scored: 2000 of 2000 targeted

## Distribution stats
entropy nats: mean 1.528, median 1.643, min 0.000, max 2.303
cluster count: mean 6.26, median 6, max 10

## Correctness label rates
greedy_correct:        1440 of 2000 (72.0%)
all_samples_correct:   813 of 2000 (40.6%)
majority_correct:      1401 of 2000 (70.0%)

## AUROC
Positive class is the hallucination case (the boolean is False).

| label convention | AUROC | pass (in [0.78, 0.86])? |
| --- | --- | --- |
| greedy_correct | 0.698 | no |
| all_samples_correct | 0.787 | yes |
| majority_correct | 0.730 | no |

## Right vs wrong entropy gap
- greedy_correct: right=1440 mean 1.400, wrong=560 mean 1.855, gap 0.455 nats
- all_samples_correct: right=813 mean 1.119, wrong=1187 mean 1.807, gap 0.688 nats
- majority_correct: right=1401 mean 1.374, wrong=599 mean 1.886, gap 0.512 nats

## Stop-condition audit
Phase 1 stop condition: replicate the literature SE AUROC within ±3pp.
Reference: Tong et al. report SE TriviaQA (no context) AUROC 0.828 for
Llama-3-8B. Target window for this replication is 0.78 to 0.86.

If any of the three AUROC labels lands in [0.78, 0.86], tag phase-1-complete.
If all three fall outside, see Friday's audit notes.
