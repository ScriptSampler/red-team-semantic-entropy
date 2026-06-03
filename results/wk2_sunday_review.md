# Week 2 Sunday review, 31 May 2026

Per the recurring discipline section of the plan. Three blocks: concurrent-work check, deliverable review, next-week planning.

## Concurrent-work check (arXiv, 15 min)

Searches run: "semantic entropy adversarial", "Buyun Liang", "Vidal LLM", "red team hallucination detection".

Adjacent papers from 2025 to mid 2026:

| Paper | Stance | Threat to project framing |
| --- | --- | --- |
| Liang et al. 2510.04398 SECA (NeurIPS 2025) | attack, but on the base model not on the detector | none, this is the planned fork target |
| Farquhar et al. (Semantic Entropy, Nature 2024) | detector paper, no adversarial evaluation | none, the project tests this detector |
| Tong et al. 2509.17445 SRE | detector paper, defensive paraphrasing | none, the project tests this detector |
| Kossen et al. 2406.15927 Semantic Entropy Probes | cheaper SE variant, no adversarial eval | none, listed in plan related work |
| Semantic Energy 2508.14496 | alternative UQ method | none, listed in plan related work |
| Hallucination Detection on a Budget 2504.03579 | efficient Bayesian SE estimator | none, no adversarial framing |
| Adaptive Bayesian SE 2603.22812 | adaptive sampling for SE | none, efficiency focus, no adversarial eval |
| Vipulanandan et al. 2601.20026 (ICLR 2026) | new SE variant via quantum tensor networks | none, no adversarial eval |
| Zhang et al. 2601.00348 Robust UQ for Factual Generation | defensive UQ robust to "non-canonical or adversarial" inputs | low, defends UQ, does not propose attacks; useful related-work citation showing the same vulnerability is recognised |
| Oh et al. 2602.05073 UQ in LLM Agents | survey and framework | none, broad survey, mentions adversarial misuse but does not implement |
| Effective Rank-based UQ 2510.08389 | alternative UQ method | none |

Verdict: no preprint currently demonstrates adversarial paraphrasing attacks against SE or SRE under a semantic-equivalence constraint, with a Hide and False-alarm split, on TriviaQA and SQuAD. The project's contribution is still distinctive.

Two papers worth citing as related-work signal that the field is aware of the vulnerability without having attacked it directly:
- Zhang et al. 2601.00348 frames adversarial inputs as a known problem for UQ robustness.
- Oh et al. 2602.05073 lists adversarial misuse of UQ as an open challenge.

## Deliverable review (30 min)

Week 2 Sunday checkpoint:
- [x] Llama 3.1 8B Instruct running, 4-bit quantised, on local GPU. Peak VRAM 5.67 GB of 15.81 GB. See results/model_check.md.
- [x] TriviaQA loader working, returning (q, a) pairs. 17,944 validation examples. See results/triviaqa_inspect.md.
- [x] End-to-end pipeline: question, model, answer. Greedy 7 of 10 correct on first 10 validation questions. See results/pipeline_check.md.
- [x] Inference cost estimate for full eval. Sustained 14.27 s per question at N=10 over 100 questions. Projects to 71 h for full validation, over the plan's 36 h ceiling.

All four green. The throughput finding triggers the plan's pre-authorised mitigation; documented in docs/decisions.md.

Other Week 2 outcomes:
- Repo on GitHub at ScriptSampler/red-team-semantic-entropy (private).
- Commits authored as ScriptSampler. env-ready tag at the Phase 1 Week 1 deliverable commit.
- Documentation pass on README, setup notes, and script comments.

No slippage. Schedule is intact.

## Next-week planning (15 min)

Week 3 (29 May to 4 Jun) per the plan is SE implementation. Three sessions:

- Mon 2 Jun: multi-sample generation already exists as se.model.generate_samples. Add storage of sample sets to disk (the SE and SRE steps will re-use them). Test on 50 questions, inspect for sample diversity especially on incorrect-prediction questions.
- Wed 4 Jun: DeBERTa-large-MNLI loaded, bidirectional entailment check implemented, tested on hand-crafted pairs.
- Fri 6 Jun: clustering by semantic equivalence, discrete entropy per question, sanity check on 20 questions to confirm high-entropy on wrong answers and low-entropy on correct.

Adjustments to the Week 3 plan based on what Week 2 surfaced:

- max_new_tokens for sample generation will start at 48 rather than 64. The 64 budget produced rambling outputs in Friday's run, inflating throughput numbers. 48 is closer to the median TriviaQA answer length plus context.
- Sample sets stored as JSONL on the WSL filesystem, not on /mnt/i, to avoid the slow boundary.
- Add a rough correctness flag to the sample storage so Week 4 can compute per-question entropy alongside per-question correctness without rerunning the model.

Phase 1 stop condition: replicate Farquhar SE AUROC within plus or minus three percentage points on TriviaQA by Sunday 15 June. Week 4 will run a 2000-question subset at N=10, projected wall-clock around 8 hours.
