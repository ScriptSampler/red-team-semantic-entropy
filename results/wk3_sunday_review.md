# Week 3 Sunday review, 7 June 2026

## Concurrent-work check (15 min)

Re-ran the plan-mandated searches against arXiv plus a couple of "adversarial paraphrase + SE" variants, looking for anything published since the 31 May review.

Adjacent papers from May to June 2026:

| Paper | Stance | Threat |
| --- | --- | --- |
| Wu et al. 2605.26158 Furina | jailbreak attack on LLM safety alignment via uncertainty amplification | none, different target (safety / refusal), evaluated on HarmBench not TriviaQA |
| Liao et al. 2503.20504 Vision-Amplified Semantic Entropy | SE variant for medical VQA | none, different modality |
| Various 2506+ SE variants (Evidential SE, Pairwise SS, SeSE) | new detector methods, no adversarial eval | none, useful related work; could be cited as "the field continues to propose SE refinements without testing adversarial robustness" |

Verdict: no new adversarial-attack paper against SE or SRE since last week. Furina is the closest near-miss in vocabulary but its target is safety alignment, not hallucination detection. The user's contribution is still distinctive.

## Deliverable review (30 min)

Week 3 Sunday checkpoint:
- [x] N=10 sample generation working. 50 questions collected, JSONL on Linux fs.
- [x] Bidirectional NLI entailment check working. 11 to 14 of 16 hand-crafted pairs correct depending on strictness reading.
- [x] Clustering + entropy computation working. Mean cluster count 6.6, mean entropy 1.63 nats.
- [x] Qualitative sanity check passes. AUROC 0.705 on 50 questions, entropy gap 0.422 nats between right and wrong cases.

All four green. No slippage.

Schedule check: today is 7 Jun in-plan, Phase 1 stop-condition is 15 Jun. One Week 4 session sits between us and that deadline. 8 days of buffer including the stop-condition Sunday.

## Next-week planning (15 min)

Week 4 is the Phase 1 replication run. Per docs/decisions.md, it uses a 2000 question subset at N=10 instead of full validation. The plan's structure is one session for the long run, one for AUROC computation and audit, one for the writeup.

### Memory-conscious adjustments

The user flagged RAM as a constraint. Two changes from the obvious one-script approach:

1. **Two-phase pipeline.** Sample first with only Llama loaded (~5.5 GB VRAM). Cluster after, with only DeBERTa-NLI loaded (~1.5 GB VRAM). Each phase is its own Python process so the model is unloaded between them.
2. **Resumable sampling.** Checkpoint after every 100 questions to JSONL. If the run is interrupted, the next invocation skips question_ids already recorded.

This also keeps system RAM lower because vmmemWSL only holds one model's tokeniser, activations, and CPU offload at a time.

### Week 4 scripts to write Monday

- `scripts/wk4_sample.py`. Phase A. Loads Llama 4-bit, iterates over the first 2000 TriviaQA validation questions, writes one record per question to `~/.cache/se-research/samples/wk4_full_2000q/samples.jsonl`. Resumable. Estimated wall clock about 8 hours at the Friday throughput of 14 s per question, but with the Monday tighter max_new_tokens=48 setting it should come in lower.
- `scripts/wk4_cluster.py`. Phase B. Loads DeBERTa-large-MNLI, reads the samples JSONL, computes clusters and entropy per question, writes `~/.cache/se-research/samples/wk4_full_2000q/entropy.jsonl`. Estimated 1 to 2 hours at the Friday 1.84 s per question.
- `scripts/wk4_auroc.py`. Phase C. No models. Reads entropy.jsonl, computes AUROC against greedy correctness, against the all-samples-correct convention, and against majority-sample correctness. Writes `results/replication_results.md` with the headline number and the comparison to Farquhar et al.

### Week 4 session shape

- Mon 9 Jun. Build the three scripts, sanity-run wk4_sample.py on first 50 questions (about 12 minutes) to confirm resumability and storage layout, then kick off the full run. Background it.
- Wed 11 Jun. Sampling done (or near done). Run wk4_cluster.py.
- Fri 13 Jun. Run wk4_auroc.py. Compare to Farquhar. Write the audit if outside ±3pp.
- Sun 15 Jun. Phase 1 stop-condition Sunday review.

### Risks for Week 4

- Sampling longer than projected. Mitigation already in the plan: drop to N=5 or shrink subset further.
- WSL memory pressure during long run. Mitigation: two-phase split, no NLI loaded during sampling.
- AUROC outside ±3pp of Farquhar. Mitigation: spend Week 5 debugging instead of starting Phase 2. Buffer time exists.
- Correctness label convention. The Monday data showed tc_69 (Octopussy) where greedy was wrong but 8 of 10 samples were right; the all-samples-correct or majority-sample label may diverge from greedy by several points of AUROC. The Phase C script reports all three so the audit can pick the right comparison to Farquhar.

Phase 1 stop condition unchanged: replicate Farquhar SE AUROC within plus or minus three percentage points on TriviaQA by Sunday 15 June.
