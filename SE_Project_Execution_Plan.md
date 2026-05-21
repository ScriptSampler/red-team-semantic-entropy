# SE PROJECT EXECUTION PLAN
## Red-Teaming Semantic Entropy, week by week

**Sessions:** Mon/Wed/Fri 8-10am + Sun 10-11am review
**Window:** 21 May 2026 to 15 September 2026 (17 weeks)
**Hard deadline:** arXiv submission 15 September 2026, non-negotiable.

This file is mirrored from the source `.docx` execution plan. It's the operational source of truth for week-by-week work. Every Sunday review opens this file to find next week's three Mon/Wed/Fri entries.

---

## How to use this document

This is the operational plan for the research itself. It complements the Summer Research Plan (strategy and scope) and the Course Schedule (study). Use this one daily to track research execution.

Each week has a goal, a list of concrete deliverables, three Mon/Wed/Fri 2-hour sessions of work, and a Sunday review checkpoint. If at any Sunday review you cannot tick the deliverables, you're behind. Not by enough to panic in week 4, but enough to act on by week 6.

---

## PHASE 1: Setup + Replication (Weeks 1-4)

**Goal:** reproduce Farquhar et al.'s SE AUROC on TriviaQA within ±3pp.
**Hard stop condition:** 15 June. If replication fails, the rest of the paper has no foundation.

### Week 1: 15-21 May. Environment setup
- **Status (Week 1 deliverable, in progress as of 2026-05-21):** ROCm 6.3+ installed, PyTorch verified with HIP backend, `torch.cuda.is_available()` returns True, basic inference test passes on a small model.
- Deliverable: working Python environment in repo. `requirements.txt` with hard-pinned versions. README documents the setup. One commit tagged `env-ready`.

### Week 2: 22-28 May. Model + dataset loaded

**Mon 26 May 8-10**
- Download Llama 3.1 8B Instruct from HuggingFace. Cache locally.
- Test basic generation: prompt in, text out. Confirm 4-bit quantisation via bitsandbytes is working.
- Measure VRAM consumption. Should fit comfortably on 16GB.

**Wed 28 May 8-10**
- Download TriviaQA from HuggingFace datasets. Use the `rc.nocontext` split for SE replication.
- Write a loader that yields (question, answer) pairs.
- Inspect ~20 examples manually. Confirm format, look for edge cases.

**Fri 30 May 8-10**
- Wire model and dataset together. Generate 1 answer for 10 questions. Print outputs.
- Measure inference speed. How long for one generation? How long for 10 samples at 100 questions? Estimate full TriviaQA runtime.

**Sunday 31 May review checkpoint**
- [ ] Llama 3.1 8B Instruct running, 4-bit quantised, on local GPU.
- [ ] TriviaQA loader working, returning (q, a) pairs.
- [ ] End-to-end pipeline: question, model, answer.
- [ ] Inference cost estimate for full eval.
- If any are missing, don't move to Week 3. Spend Week 3 finishing setup.

### Week 3: 29 May to 4 Jun. SE implementation (sampling + NLI)

**Mon 2 Jun 8-10**
- Implement multi-sample generation. For each question, generate N=10 answers at temperature T=1.0.
- Store sample sets to disk. You'll re-use them for SE and SRE.
- Test on 50 questions. Inspect: are the samples meaningfully different?

**Wed 4 Jun 8-10**
- Load DeBERTa-large-MNLI from HuggingFace.
- Implement a bidirectional entailment check.
- Test on hand-crafted pairs ('Paris' and 'the capital of France' equivalent; 'Paris' and 'London' not).

**Fri 6 Jun 8-10**
- Implement clustering: group N=10 samples into semantic equivalence classes via NLI.
- Compute discrete entropy over cluster probabilities. Output: one entropy number per question.
- Sanity check on 20 questions.

**Sunday 7 Jun review checkpoint**
- [ ] N=10 sample generation working.
- [ ] Bidirectional NLI entailment check working.
- [ ] Clustering and entropy computation working.
- [ ] Qualitative sanity check passes.

### Week 4: 5-11 Jun. Full replication run

**Mon 9 Jun 8-10**
- Run SE evaluation on full TriviaQA test split (~11k questions). 12-36 hours of compute. Start Monday morning.
- Set up logging: progress every 100 questions, checkpoints every 1000.
- While it runs, read Farquhar et al. closely. Note exact AUROC and config.

**Wed 11 Jun 8-10**
- Inspect results.
- Compute AUROC. How well does SE rank correct vs incorrect answers?
- Compare to Farquhar et al.'s published AUROC. Calculate delta.

**Fri 13 Jun 8-10**
- Write `replication_results.md`: your AUROC, their AUROC, delta, configuration.
- If within ±3pp, tag commit `phase-1-complete`.
- If outside ±3pp, audit. Likely culprits: NLI model variant, sampling temperature, sample count, prompt formatting.

**Sunday 15 Jun review checkpoint. PHASE 1 STOP CONDITION.**
- [ ] SE replicated within ±3pp on TriviaQA.
- [ ] `replication_results.md` committed.
- [ ] `methodology.md` draft started.
- If failed: STOP. Do not proceed to Phase 2. Spend 1 extra week debugging. If still failing by 22 June, the project pivots, not the timeline.

---

## PHASE 2: Attack Development (Weeks 5-10)

**Goal:** demonstrate that adversarial paraphrasing degrades both SE and SRE AUROC. By end of phase, a 12+ AUROC numbers matrix.

### Week 5: 12-18 Jun. Fork SECA, understand

**Mon 16 Jun 8-10**
- Clone github.com/Buyun-Liang/SECA.
- Read README, paper appendix, core attack code. Understand the optimisation loop, NLI constraint, zeroth-order gradient estimation.
- Get their example running end-to-end on a bundled example.

**Wed 18 Jun 8-10**
- Strip down SECA's code. Minimum subset: attack loop + constraint check + NLI verifier.
- Replace the target model with your Llama 3.1 8B setup.
- Confirm SECA's original objective works on one TriviaQA example.

**Fri 20 Jun 8-10**
- Commit `forked-seca-baseline`.
- Spec the modification: write down exactly what new objective replaces SECA's. (Hide attack: minimise SE on incorrect answers.)
- Implement a stub for the new objective.

**Sunday 21 Jun review checkpoint**
- [ ] SECA fork operational.
- [ ] Hide attack objective specified and stubbed.

### Week 6: 19-25 Jun. Hide attack implementation

**Mon 23 Jun 8-10**
- Implement Hide attack: given Q the model answers incorrectly, find paraphrase Q' minimising SE(Q') while NLI confirms Q ≡ Q'.
- Connect to SECA's optimisation loop.

**Wed 25 Jun 8-10**
- Run Hide attack on 10 examples where the base model is wrong.
- For each, did SE drop? Did NLI confirm equivalence?
- Debug. If SE doesn't drop, is the gradient flowing? If NLI rejects everything, is the constraint too strict?

**Fri 27 Jun 8-10**
- Iterate. Get Hide attack to over 50% success on 10 test examples.
- Document parameter choices.

**Sunday 28 Jun review checkpoint**
- [ ] Hide attack code written, runs end-to-end.
- [ ] Success on at least 5/10 test cases.

### Week 7: 26 Jun to 2 Jul. False-alarm attack

**Mon 30 Jun 8-10**
- Mirror Hide code: given Q the model answers correctly, find paraphrase Q' maximising SE(Q') while NLI confirms equivalence. Flip the objective sign.

**Wed 2 Jul 8-10**
- Run False-alarm on 10 examples where the model is correct.
- Same debugging loop.

**Fri 4 Jul 8-10**
- Iterate. False-alarm over 50% success.
- Document parameter choices.

**Sunday 5 Jul review checkpoint**
- [ ] False-alarm code written, runs end-to-end.
- [ ] Success on at least 5/10 test cases.
- [ ] Both attacks committed at tag `attacks-prototyped`.

### Week 8: 3-9 Jul. SRE implementation

**Mon 7 Jul 8-10**
- Read Tong et al. (arXiv 2509.17445). SRE generates multiple input paraphrases, runs SE on each, then aggregates.
- Implement the input-paraphrasing step.

**Wed 9 Jul 8-10**
- Implement SRE aggregation on top of existing SE.
- Run SRE on 100 TriviaQA examples. Compute AUROC.
- Compare to Tong et al.

**Fri 11 Jul 8-10**
- Debug if SRE doesn't reproduce.
- Tag `sre-implemented`.

**Sunday 12 Jul review checkpoint**
- [ ] SRE running end-to-end.
- [ ] SRE AUROC roughly matches Tong et al.

### Week 9: 10-16 Jul. Phase 2 mid-check + scale-up

⚠️ 15 Jul is the Phase 2 mid-check. By Sun 12 Jul, both attacks should be working on prototype scale and SRE should be implemented. If not, this is audit week.

**Mon 14 Jul 8-10**
- Scale up attack experiments. 200 questions the model gets wrong (Hide) and 200 right (False-alarm).
- Begin full-scale attack runs (days, not hours).

**Wed 16 Jul 8-10**
- Inspect intermediate results.
- Implement aggregation: turn 200 attack outcomes into an AUROC degradation number.

**Fri 18 Jul 8-10**
- Draft figure plans while runs continue. AUROC bar chart, attack success vs perturbation budget, qualitative examples.

**Sunday 19 Jul review checkpoint**
- [ ] Full-scale runs initiated.
- [ ] Aggregation logic in place.
- [ ] Figure plan drafted.

### Week 10: 17-23 Jul. Full result matrix

**Mon 21 Jul 8-10**
- Hide vs vanilla SE on TriviaQA: number.
- Hide vs vanilla SE on SQuAD: number.
- Hide vs SRE on TriviaQA: number.
- Hide vs SRE on SQuAD: number.

**Wed 23 Jul 8-10**
- Same 2×2 for False-alarm.
- Plus baselines: SE and SRE AUROC under naive paraphrasing.
- 12+ AUROC numbers total.

**Fri 25 Jul 8-10**
- Generate the headline figure: bar chart of AUROC by method and attack condition.
- Sanity check the story.

**Sunday 26 Jul review checkpoint**
- [ ] Full result matrix complete.
- [ ] Headline figure drafted.
- [ ] Qualitative failure-mode analysis started.

### Week 11: 24-30 Jul. Analysis + Phase 2 close-out

**Mon 28 Jul 8-10**
- Qualitative analysis. 10 successes and 10 failures per attack type. Look for patterns.

**Wed 30 Jul 8-10**
- Write failure-mode notes into `methodology.md`.
- Clean the repo. Everything committed, documented, reproducible.
- Tag `phase-2-complete`.

**Fri 1 Aug 8-10**
- Buffer day, or start the literature-engagement section of the writeup early.

**Sunday 2 Aug review checkpoint. PHASE 2 COMPLETE.**
- [ ] Both attacks against both methods on both benchmarks.
- [ ] 12+ AUROC numbers documented.
- [ ] Qualitative failure-mode analysis written.
- [ ] Repo tagged `phase-2-complete`.

---

## PHASE 3: Writeup (Weeks 12-14)

**Goal:** complete first draft. Imperfect is fine. By 25 Aug, all sections written.

### Week 12: 31 Jul to 6 Aug. Skeleton + Related Work

**Mon 4 Aug.** Set up the LaTeX repo (NeurIPS or arXiv template). Outline 8 sections. 2-3 sentences per section.
**Wed 6 Aug.** Draft Related Work. Distinguish from SECA, PR-CP, SRE, SEPs, Semantic Energy. ~600-800 words.
**Fri 8 Aug.** Finish Related Work. Cite manager set up.

**Sunday 9 Aug review**
- [ ] Skeleton in place.
- [ ] Related Work complete.

### Week 13: 7-13 Aug. Methods + Experiments

**Mon 11 Aug.** Methods section. Recap SE and SRE. Define the attacks formally. NLI verification. ~800 words.
**Wed 13 Aug.** Experiments setup and main results table. Polish the headline figure and sub-figures.
**Fri 15 Aug.** Finish Experiments. Verify all numbers match `results/`. Failure-mode subsection.

**Sunday 16 Aug review**
- [ ] Methods complete.
- [ ] Experiments complete.
- [ ] All figures generated and embedded.

### Week 14: 14-20 Aug. Intro, Discussion, Limitations, Conclusion

**Mon 18 Aug.** Introduction. Hook: deployed safety mechanisms haven't been adversarially evaluated. ~600 words.
**Wed 20 Aug.** Discussion and Limitations honestly (single model family, English-only, compute budget).
**Fri 22 Aug.** Conclusion ~200 words. Abstract last, under 250 words.

**Sunday 23 Aug review**
- [ ] All 8 sections drafted.
- [ ] Abstract written.

### Week 15: 21-27 Aug. Phase 3 deadline + optional defence

⚠️ 25 August is the hard deadline for the first draft. If the draft isn't done by Mon 25 Aug, ship attacks-only.

**Mon 25 Aug.** First-draft completion review. End-to-end read.
**Wed 27 Aug.** Optional defence stretch goal, or self-edits.
**Fri 29 Aug.** Continue.

**Sunday 30 Aug review**
- [ ] First draft complete.
- [ ] Decision: defence included or skipped.

---

## PHASE 4: Polish + Submit (Weeks 16-17)

**Goal:** arXiv preprint live by 15 September.

### Week 16: 28 Aug to 3 Sep. Self-review + external review

**Mon 1 Sep.** Self-review pass 1 (morning, fresh).
**Wed 3 Sep.** Self-review pass 2 (afternoon, tired). Apply pass-1 fixes.
**Fri 5 Sep.** Self-review pass 3 (evening). Send the draft to external reviewers: Northumbria tutor, OATML-adjacent contacts, cold-email a postdoc you cite if needed.

**Sunday 6 Sep review**
- [ ] Three self-review passes done.
- [ ] Draft sent externally.

### Week 17: 4-10 Sep. External feedback + final polish

**Mon 8 Sep.** Apply external feedback. If multiple readers flag the same paragraph, prioritise rewriting it.
**Wed 10 Sep.** Final figures sharp, citations resolve, no TODO markers, repo public with clean README. Acknowledgements: Dr Maisnam, tutor, reviewers.
**Fri 12 Sep.** arXiv endorsement secured. Cold-email a postdoc whose work you cite. Prepare submission: title, authors, abstract, categories (cs.CL primary, cs.LG secondary).

**Sunday 13 Sep review**
- [ ] External feedback applied.
- [ ] arXiv endorsement secured.
- [ ] Submission package ready.

### Mon 15 September. ARXIV SUBMISSION.
- Pre-submit checklist: authors and affiliations correct, abstract under 250 words, code repo public with MIT license, all citations resolve, figures readable in greyscale, no TODOs, acknowledgements complete.
- Submit. arXiv URL goes into the Oxford application materials.

---

## Recurring discipline (every week, every phase)

### Sunday Weekly Review (10:00 to 11:00)
- **15 min, concurrent work check.** Search arXiv for "semantic entropy adversarial", "Buyun Liang", "Vidal LLM", "red team hallucination detection". If a competing preprint drops, raise immediately and reassess framing.
- **30 min, progress review.** Run through this week's deliverable checkboxes. What got done, what's blocking. Notes into repo.
- **15 min, next-week planning.** Confirm the next week's plan still holds. If you slipped, decide whether to absorb the slip or compress later weeks.

### Per-session ritual
- Open with "what am I doing today and why?", one sentence, plain English.
- Close with a 2-line commit message capturing what you did. If you didn't commit anything, write a 2-line note in a daily log.
- 30-min stuck rule: write down what you're stuck on and switch tasks.

---

## Risks and mitigations

### Weeks 1-4, setup risks
- **ROCm or PyTorch breaks.** Mitigation: Colab Pro fallback.
- **Inference too slow.** Mitigation: reduce N=10 to N=5, reduce eval set to a 2000-question subset.

### Weeks 5-11, attack risks
- **SECA doesn't port cleanly.** Mitigation: re-implement the optimisation from the paper. 3 days max, then escalate.
- **Attacks don't converge.** Mitigation: more iterations, bigger budget, relax NLI threshold. If still failing by Week 9, the threat model needs rethinking. Raise.
- **SRE harder than expected.** Mitigation: ship attacks against vanilla SE only. SRE becomes future work.

### Weeks 12-14, writing risks
- **Writing slower than expected.** Mitigation: skip the defence stretch goal.
- **Results don't tell a clean story.** Mitigation: reframe honestly. Mixed-evidence papers are publishable.

### Weeks 15-17, submission risks
- **No arXiv endorser.** Mitigation: start cold-emailing in Week 14.
- **External reviewers don't respond.** Mitigation: submit anyway based on your own three passes.

---

## Final note

Single non-negotiable: 15 September arXiv submission. Everything else is negotiable in service of that deadline.
