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

import dataclasses
import statistics
from dataclasses import dataclass

from . import model as M
from .config import GenConfig
from .nli import NLI
from .scoring import normalise
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
    # The defense's premise is that averaging SE over paraphrases cancels
    # independent sampling noise. A fixed seed would reset the RNG identically
    # for every variant and correlate the draws, defeating that. Force seed=None
    # so each variant samples independently.
    var_gen = dataclasses.replace(gen_cfg, seed=None)

    # Dedupe: proposer.propose returns the input unchanged on a degenerate
    # generation, which would otherwise re-add the original (already in variants)
    # and bias the aggregate toward the original's entropy.
    variants = [question]
    seen = {normalise(question)}
    for cand in proposer.propose_many(question, lm, k_paraphrases):
        key = normalise(cand)
        if key in seen:
            continue
        if require_equivalent and not nli.bidirectional_equivalent(question, cand):
            continue
        seen.add(key)
        variants.append(cand)

    ents = [semantic_entropy(v, lm, nli, var_gen).entropy_nats for v in variants]
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
