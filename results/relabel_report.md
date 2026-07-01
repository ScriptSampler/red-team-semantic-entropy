# Relabel report: cached Phase-1 pool under the new oracle

cached questions: 2000 samples, 2000 entropy

## Label flips: old substring -> new span (greedy correctness)
old correct rate: 1440/2000 (72.0%)
new correct rate: 1424/2000 (71.2%)
flipped correct->wrong (over-credit removed): 18
flipped wrong->correct (under-credit recovered): 2
total labels changed: 20 (1.0%)

## Clean SE AUROC on the FULL 2000-question pool (circularity-free)
Label = greedy WRONG (positive/hallucination class); score = SE entropy.
No entropy-based selection: this is the detector's real ranking power.

| oracle | correct rate | clean AUROC |
| --- | --- | --- |
| substring (old) | 72.0% | 0.697 |
| span (new primary) | 71.2% | 0.694 |
| strict EM | 0.4% | 0.561 |

Phase-1 replication reference: 0.787 (all-samples label). A full-pool
clean AUROC in the ~0.75-0.80 band confirms the 1.000 from the attack
matrix was pure selection artifact, per external review B2/§2.

## Article-in-title scan (normalize_answer strips a/an/the)
gold canonical answers beginning with an article: 123 of 2000
  - 'A boojum' -> normalises to 'boojum'
  - 'The Kentuckian' -> normalises to 'kentuckian'
  - 'A manticore' -> normalises to 'manticore'
  - 'The Crow' -> normalises to 'crow'
  - 'The Staple Singers' -> normalises to 'staple singers'
  - 'The Full Monty' -> normalises to 'full monty'
  - 'The Hague' -> normalises to 'hague'
  - 'The Little Sparrow' -> normalises to 'little sparrow'
Residual: these lose the leading article (SQuAD-standard behaviour). Aliases
usually include the article-free form, so span match still succeeds; the risk
is only distinct entities differing solely by an article, which is rare.

## Alias-set richness (provenance: TriviaQA Aliases + NormalizedAliases)
accepted forms per question: mean 17.1, median 11, min 1, max 194
questions with a SINGLE accepted form (under-credit risk): 91 (4.5%)
Loader se.data.load_triviaqa combines row['answer']['aliases'] and
['normalized_aliases']; a mean well above 1 confirms the full set is loaded.

## Entity-ambiguity (single-token gold; string oracle can over-match)
questions whose every accepted form is a single token: 98 (4.9%)
  of those, currently labelled WRONG (hide-pool candidates): 29
For hide targets, over-matching would mislabel a wrong answer as right and
DROP it from the pool (shrinks, not corrupts). If this fraction is large, the
model-graded judge stops being deferrable.

Relabeled correctness written to /home/abhi/.cache/se-research/samples/wk4_full_2000q/relabeled.jsonl (consumed by the B1 sampler).
