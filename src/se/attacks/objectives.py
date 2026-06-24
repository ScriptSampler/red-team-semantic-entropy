"""Attack objectives over the SE / SRE detectors.

The optimiser maximises a scalar. Direction is encoded here:

  Hide attack: the model answers the question wrong, and we want the
  detector to miss it, i.e. drive the entropy DOWN. Objective = -entropy,
  so maximising it minimises entropy.

  False-alarm attack: the model answers correctly, and we want the
  detector to cry wolf, i.e. drive the entropy UP. Objective = +entropy.

Each objective caches scores per query string within one attack so the
optimiser's repeated evaluation of the same candidate is cheap. SE
evaluation is the expensive inner call (N samples + an O(n^2) NLI pass),
so the cache matters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from .. import model as M
from ..config import GenConfig
from ..nli import NLI
from ..se_pipeline import semantic_entropy
from ..sre import self_reflective_entropy


Detector = Literal["se", "sre"]


def _entropy_of(query: str, lm: M.LoadedModel, nli: NLI, detector: Detector,
                gen_cfg: GenConfig, sre_kwargs: dict) -> float:
    if detector == "se":
        return semantic_entropy(query, lm, nli, gen_cfg).entropy_nats
    return self_reflective_entropy(query, lm, nli, **sre_kwargs).entropy_nats


@dataclass
class ObjectiveBundle:
    """A ready-to-optimise objective plus a readable score function.

    fn is what the optimiser maximises. entropy(query) returns the raw
    entropy for reporting, regardless of attack direction.
    """
    fn: Callable[[str], float]
    entropy: Callable[[str], float]
    direction: str  # "minimise_entropy" (Hide) or "maximise_entropy" (False-alarm)


def make_objective(
    attack: Literal["hide", "false_alarm"],
    lm: M.LoadedModel,
    nli: NLI,
    *,
    detector: Detector = "se",
    gen_cfg: GenConfig | None = None,
    sre_kwargs: dict | None = None,
) -> ObjectiveBundle:
    gen_cfg = gen_cfg or GenConfig()
    sre_kwargs = sre_kwargs or {}
    cache: dict[str, float] = {}

    def entropy(query: str) -> float:
        if query not in cache:
            cache[query] = _entropy_of(query, lm, nli, detector, gen_cfg, sre_kwargs)
        return cache[query]

    if attack == "hide":
        def fn(query: str) -> float:
            return -entropy(query)
        direction = "minimise_entropy"
    elif attack == "false_alarm":
        def fn(query: str) -> float:
            return entropy(query)
        direction = "maximise_entropy"
    else:
        raise ValueError(f"unknown attack: {attack}")

    return ObjectiveBundle(fn=fn, entropy=entropy, direction=direction)
