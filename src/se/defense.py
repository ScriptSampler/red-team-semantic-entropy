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

STRUCTURE. The function is split so the part that decides *what* gets averaged
and *how* is pure and unit-testable without a GPU:

    select_variants(...)   which inputs enter the aggregate (dedupe + gate)
    aggregate_entropy(...) how their scores combine
    defended_entropy(...)  the GPU composition of the two, plus the scoring

Only the last one needs a model. See tests/test_defense.py.
"""
from __future__ import annotations

import dataclasses
import statistics
from dataclasses import dataclass
from typing import Callable, Sequence

from . import model as M
from .config import GenConfig
from .nli import NLI
from .scoring import normalise
from .se_pipeline import semantic_entropy
from .attacks import proposer


# Supported aggregation rules. Validated BEFORE any generation happens: an
# unknown name used to raise only after paying for K paraphrases and up to K+1
# SE evaluations (~70 GPU-seconds per call, ~160 calls in the driver).
AGGREGATES = ("median", "mean", "min")


@dataclass
class DefendedResult:
    question: str
    defended_entropy: float
    per_variant_entropy: list[float]
    n_variants: int
    aggregate: str
    # Observability (added with the test suite): without these, a run in which
    # the equivalence gate rejected every paraphrase is indistinguishable from
    # one where the defense averaged properly -- in both cases the reported
    # number is just a defended_entropy, but in the first the "defense" silently
    # degraded to vanilla SE on a single input and any measured effect
    # reduction is attributable to re-sampling alone.
    k_requested: int = 0
    n_candidates: int = 0        # paraphrases the proposer returned
    n_rejected_duplicate: int = 0
    n_rejected_gate: int = 0

    @property
    def effective_d(self) -> int:
        """Paraphrases that actually entered the aggregate (excludes the original)."""
        return self.n_variants - 1

    @property
    def degenerate(self) -> bool:
        """True when nothing was averaged: the score equals vanilla SE."""
        return self.n_variants <= 1


@dataclass
class VariantSelection:
    variants: list[str]
    n_candidates: int
    n_rejected_duplicate: int
    n_rejected_gate: int


def aggregate_entropy(entropies: Sequence[float], aggregate: str = "median") -> float:
    """Combine per-variant entropies into the defended score. Pure.

    "median" is the default because it is the only one of the three that is
    insensitive to a single adversarial outlier: moving one variant's entropy
    arbitrarily far cannot move the median of >=3 variants past its neighbours,
    whereas it moves the mean by delta/n and can capture the min outright.
    """
    if aggregate not in AGGREGATES:
        raise ValueError(f"unknown aggregate: {aggregate}")
    if not entropies:
        raise ValueError("aggregate_entropy: no entropies to aggregate")
    if aggregate == "median":
        return float(statistics.median(entropies))
    if aggregate == "mean":
        return float(statistics.mean(entropies))
    return float(min(entropies))


def select_variants(
    question: str,
    candidates: Sequence[str],
    *,
    is_equivalent: Callable[[str, str], bool] | None = None,
) -> VariantSelection:
    """Decide which inputs enter the aggregate. Pure given `is_equivalent`.

    The original question is always the first variant. A candidate is dropped
    if it normalises to something already selected (the proposer returns the
    input unchanged on a degenerate generation, which would otherwise re-add
    the original and bias the aggregate toward its entropy), or if
    `is_equivalent` is given and rejects it (a deployed defender would not
    average in a paraphrase that changed the meaning).

    Note the gate is applied BEFORE a candidate joins `seen`, so a rejected
    candidate repeated verbatim is re-submitted to the gate. That costs a
    duplicate NLI call but cannot change the selection; it is preserved as-is
    so the deduplication semantics match the reviewed (H2) behaviour exactly.
    """
    variants = [question]
    seen = {normalise(question)}
    n_dup = 0
    n_gate = 0
    for cand in candidates:
        key = normalise(cand)
        if key in seen:
            n_dup += 1
            continue
        if is_equivalent is not None and not is_equivalent(question, cand):
            n_gate += 1
            continue
        seen.add(key)
        variants.append(cand)
    return VariantSelection(
        variants=variants,
        n_candidates=len(candidates),
        n_rejected_duplicate=n_dup,
        n_rejected_gate=n_gate,
    )


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
    # Validate before spending any GPU time (see AGGREGATES).
    if aggregate not in AGGREGATES:
        raise ValueError(f"unknown aggregate: {aggregate}")

    gen_cfg = gen_cfg or GenConfig()
    # The defense's premise is that averaging SE over paraphrases cancels
    # independent sampling noise. A fixed seed would reset the RNG identically
    # for every variant and correlate the draws, defeating that. Force seed=None
    # so each variant samples independently.
    var_gen = dataclasses.replace(gen_cfg, seed=None)

    candidates = proposer.propose_many(question, lm, k_paraphrases)
    sel = select_variants(
        question, candidates,
        is_equivalent=nli.bidirectional_equivalent if require_equivalent else None,
    )

    ents = [semantic_entropy(v, lm, nli, var_gen).entropy_nats for v in sel.variants]
    return DefendedResult(
        question=question,
        defended_entropy=aggregate_entropy(ents, aggregate),
        per_variant_entropy=ents,
        n_variants=len(sel.variants),
        aggregate=aggregate,
        k_requested=k_paraphrases,
        n_candidates=sel.n_candidates,
        n_rejected_duplicate=sel.n_rejected_duplicate,
        n_rejected_gate=sel.n_rejected_gate,
    )
