"""Feasibility gate: is a candidate paraphrase a valid attack?

A candidate Q' is feasible against original Q if it is semantically
equivalent to Q. We use the project's bidirectional NLI check (both
directions must argmax to entailment), which is the SECA paper's
semantic-equivalence constraint and matches how SE clusters answers.

We add two cheap guards SECA's LLM-judge got for free but our NLI does not:
  - non-empty and actually different from Q (a no-op paraphrase is not an
    attack, though it is trivially "equivalent")
  - length sanity: reject candidates far longer or shorter than Q, which
    are usually the model drifting off-task rather than paraphrasing
"""
from __future__ import annotations

from dataclasses import dataclass

from ..nli import NLI
from ..scoring import normalise


@dataclass
class FeasibilityResult:
    feasible: bool
    equivalent: bool
    is_noop: bool
    length_ok: bool
    reason: str


def check(
    candidate: str,
    original: str,
    nli: NLI,
    *,
    min_len_ratio: float = 0.4,
    max_len_ratio: float = 2.5,
    require_different: bool = True,
) -> FeasibilityResult:
    cand_n = normalise(candidate)
    orig_n = normalise(original)

    is_noop = cand_n == orig_n
    if require_different and is_noop:
        return FeasibilityResult(False, True, True, True,
                                 "no-op: identical to original after normalisation")

    if not cand_n:
        return FeasibilityResult(False, False, False, False, "empty candidate")

    ratio = len(candidate) / max(1, len(original))
    length_ok = min_len_ratio <= ratio <= max_len_ratio
    if not length_ok:
        return FeasibilityResult(False, False, is_noop, False,
                                 f"length ratio {ratio:.2f} outside [{min_len_ratio}, {max_len_ratio}]")

    equivalent = nli.bidirectional_equivalent(original, candidate)
    if not equivalent:
        return FeasibilityResult(False, False, is_noop, length_ok,
                                 "not bidirectionally entailed with original")

    return FeasibilityResult(True, True, is_noop, length_ok, "feasible")
