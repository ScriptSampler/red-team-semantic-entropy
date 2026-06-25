"""A simple defense: input-paraphrase-averaged semantic entropy.

The attacks find one adversarial paraphrase Q' (equivalent to Q) whose SE is
moved. A natural defense is for the detector to not trust a single phrasing:
given whatever input it receives, it generates K paraphrases of that input,
computes SE on each plus the original, and aggregates. If the attacker's Q' is
a narrow adversarial point, its own paraphrases revert toward the true
uncertainty, so the aggregate is harder to move.

This is deliberately the same family of idea as SRE's input reformulation, so
the experiment doubles as evidence on whether SRE's built-in reformulation
makes it intrinsically harder to attack than vanilla SE (our SE-vs-SRE transfer
numbers speak to the same question from the other side).

aggregate = "median" by default: more robust than the mean to a single
adversarial outlier among the paraphrases.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from . import model as M
from .config import GenConfig
from .nli import NLI
from .se_pipeline import semantic_entropy
from .attacks import proposer


@dataclass
class DefendedResult:
    question: str
    defended_entropy: float
    per_variant_entropy: list[float]
    n_variants: int
    aggregate: str


def defended_entropy(
    question: str,
    lm: M.LoadedModel,
    nli: NLI,
    *,
    k_paraphrases: int = 4,
    aggregate: str = "median",
    gen_cfg: GenConfig | None = None,
    require_equivalent: bool = True,
) -> DefendedResult:
    """Aggregate SE over the input plus K paraphrases of it.

    If require_equivalent, paraphrases that are not bidirectionally NLI
    equivalent to the input are dropped (a deployed defender would not want to
    average in a paraphrase that changed the meaning). The original input is
    always included.
    """
    gen_cfg = gen_cfg or GenConfig()
    variants = [question]
    for cand in proposer.propose_many(question, lm, k_paraphrases):
        if require_equivalent and not nli.bidirectional_equivalent(question, cand):
            continue
        variants.append(cand)

    ents = [semantic_entropy(v, lm, nli, gen_cfg).entropy_nats for v in variants]
    if aggregate == "median":
        agg = float(statistics.median(ents))
    elif aggregate == "mean":
        agg = float(statistics.mean(ents))
    elif aggregate == "min":
        agg = float(min(ents))
    else:
        raise ValueError(f"unknown aggregate: {aggregate}")

    return DefendedResult(
        question=question,
        defended_entropy=agg,
        per_variant_entropy=ents,
        n_variants=len(variants),
        aggregate=aggregate,
    )
