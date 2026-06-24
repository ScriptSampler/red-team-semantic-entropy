"""Adversarial paraphrasing attacks against SE and SRE detectors.

Ported from the SECA optimisation loop (Liang et al., NeurIPS 2025,
github.com/Buyun-Liang/SECA) but with two substitutions for this project:

  - Objective. SECA maximises the target LLM's confidence on a wrong
    multiple-choice token. We swap in semantic entropy: the Hide attack
    minimises SE on a question the model answers incorrectly, the
    False-alarm attack maximises SE on a question it answers correctly.
  - Equivalence constraint. SECA uses an LLM judge for feasibility. We use
    bidirectional DeBERTa NLI entailment, which is the constraint the SECA
    paper formalises and what this project's plan specifies.

Modules:
  proposer     LLM paraphrase generator for open-ended QA
  feasibility  NLI bidirectional equivalence gate
  optimizer    objective-agnostic zeroth-order beam search
  objectives   Hide and False-alarm objectives over SE / SRE
"""
