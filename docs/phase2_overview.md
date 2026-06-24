# Phase 2 overview: attack development (Weeks 5-11)

This documents the code built for Phase 2 and the order to run it. The code
is complete and the pure logic is unit-tested (tests/test_attacks_logic.py);
the result numbers come from GPU runs you trigger, because the attacks are
multi-day on a single 16 GB card and the plan gates them on Phase 1 passing.

## What was forked and what we changed

We forked github.com/Buyun-Liang/SECA into `vendor/SECA/` and read its real
implementation. `vendor/` is gitignored (it carries its own git history and a
large image); re-create it with:

```bash
git clone https://github.com/Buyun-Liang/SECA.git vendor/SECA
git -C vendor/SECA checkout 33a4d771b0896feae823f9bcb00edf703cb3175a
```
 SECA attacks MMLU multiple-choice: its objective is the
target LLM's log-confidence on a wrong answer token, and its feasibility
gate is an LLM judge. We reuse SECA's zeroth-order beam search but swap two
pieces:

- **Objective**: semantic entropy instead of MC-token confidence. The Hide
  attack minimises SE on a question the model answers wrong; the False-alarm
  attack maximises SE on one it answers right.
- **Equivalence constraint**: bidirectional DeBERTa NLI entailment instead of
  an LLM judge. This is the constraint the SECA paper formalises and what our
  plan specifies, and it matches how SE itself clusters answers.

## Module map (src/se)

| Module | Role |
| --- | --- |
| `se_pipeline.py` | `semantic_entropy(question)` — the detector the attacks fool |
| `sre.py` | Self-Reflective Entropy (Tong et al.): reformulate, pool, cluster, one entropy |
| `attacks/proposer.py` | Llama-based paraphrase generator (open-ended QA port of SECA's) |
| `attacks/feasibility.py` | NLI bidirectional equivalence gate + no-op/length guards |
| `attacks/optimizer.py` | objective-agnostic zeroth-order beam search (SECA port) |
| `attacks/objectives.py` | Hide / False-alarm objectives over SE or SRE |
| `attacks/select.py` | pick model-wrong (Hide) / model-right (False-alarm) targets |
| `attacks/harness.py` | load both models, run resumable attack batches, score success |

## Run order

| Week | Script | Produces | Compute |
| --- | --- | --- | --- |
| 5 | `wk5_seca_explore.py` | fork-operational smoke test | minutes |
| 6 | `wk6_hide_attack.py` | Hide vs SE on 10 wrong questions | ~1-2 h |
| 7 | `wk7_false_alarm.py` | False-alarm vs SE on 10 right questions | ~1-2 h |
| 8 | `wk8_sre.py` | SRE vs SE AUROC on 100 questions | ~2-3 h |
| 9 | `wk9_scaleup.py` | scale-up campaigns (200+200 per dataset/detector) | days |
| 10 | `wk10_matrix.py` | the 12+ AUROC matrix (no models, reads caches) | minutes |
| 11 | `wk11_analysis.py` | qualitative failure-mode analysis (reads caches) | minutes |

Week 9 is the bottleneck. Run one campaign at a time, each resumable:

```bash
python scripts/wk9_scaleup.py --attack hide        --detector se  --dataset triviaqa --n 200
python scripts/wk9_scaleup.py --attack false_alarm --detector se  --dataset triviaqa --n 200
python scripts/wk9_scaleup.py --attack hide        --detector sre --dataset triviaqa --n 200
python scripts/wk9_scaleup.py --attack false_alarm --detector sre --dataset triviaqa --n 200
# then the four SQuAD equivalents
```

## RAM and VRAM

The attack inner loop scores each candidate paraphrase through the SE
pipeline, so Llama (4-bit, ~5.5 GB) and DeBERTa NLI (~1.5 GB) must be
resident together: ~7 GB VRAM, fits the 16 GB card. Unlike the Week 4
replication this phase cannot split the models across processes. Keep an eye
on system RAM (vmmemWSL) during the multi-day Week 9 campaigns; each campaign
is checkpointed so it survives a kill.

## Honest deviations

- **SRE clustering** uses exact-normalised pre-merge + NLI union-find, not the
  paper's full energy-based hybrid clustering. If Week 8 AUROC lands far from
  the paper's 0.871 on TriviaQA, that backend is the first thing to revisit.
  The plan permits dropping SRE to future work if it does not reproduce.
- **SRE reformulation filter** uses NLI non-contradiction rather than the
  paper's sentence-embedding cosine band, to avoid a third resident model.
- Attack **success** is defined per-question as a feasible paraphrase moving
  entropy by >= 0.25 nats in the intended direction. The paper-level metric is
  the AUROC degradation in `wk10_matrix.py`; the per-question rate is the
  prototype gate the plan uses in Weeks 6-7.
