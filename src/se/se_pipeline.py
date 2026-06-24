"""Unified semantic-entropy callable.

Weeks 2 and 3 built the pieces (sampling in se.model, clustering and
entropy in se.entropy, correctness in se.scoring). The attack objectives
in Phase 2 need a single function that maps a question to its SE score in
one call, holding both Llama and the NLI model resident.

semantic_entropy(question, ...) returns an SEResult with the entropy, the
cluster count, the sample strings, and (when a TriviaQAExample is given)
the per-sample correctness. This is the detector the attacks try to fool:
the Hide attack drives entropy down on a wrong question, the False-alarm
attack drives it up on a right one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import torch

from . import model as M
from .config import GenConfig
from .data import TriviaQAExample
from .entropy import cluster_and_score
from .nli import NLI
from .scoring import is_acceptable


@dataclass
class SEResult:
    question: str
    entropy_nats: float
    n_clusters: int
    n_samples: int
    samples: list[str] = field(default_factory=list)
    greedy: str | None = None
    greedy_correct: bool | None = None
    samples_correct: list[bool] | None = None


@torch.no_grad()
def semantic_entropy(
    question: str,
    lm: M.LoadedModel,
    nli: NLI,
    gen_cfg: GenConfig | None = None,
    *,
    example: TriviaQAExample | None = None,
    compute_greedy: bool = False,
) -> SEResult:
    """Sample N answers, cluster by NLI equivalence, return the entropy.

    If example is given, also label each sample (and optionally the greedy
    answer) for correctness against the accepted answer forms. The attack
    objectives need entropy; the eval harness also needs correctness.
    """
    gen_cfg = gen_cfg or GenConfig()
    samples = M.generate_samples(lm, question, gen_cfg)
    cs = cluster_and_score(samples, nli)

    greedy = None
    greedy_correct = None
    if compute_greedy:
        greedy_cfg = GenConfig(
            max_new_tokens=gen_cfg.max_new_tokens,
            temperature=gen_cfg.temperature,
            top_p=gen_cfg.top_p,
            n_samples=1,
            seed=gen_cfg.seed,
        )
        greedy = M.generate_one(lm, question, greedy_cfg)
        if example is not None:
            greedy_correct = is_acceptable(greedy, example)

    samples_correct = None
    if example is not None:
        samples_correct = [is_acceptable(s, example) for s in samples]

    return SEResult(
        question=question,
        entropy_nats=cs.entropy_nats,
        n_clusters=cs.n_clusters,
        n_samples=len(samples),
        samples=samples,
        greedy=greedy,
        greedy_correct=greedy_correct,
        samples_correct=samples_correct,
    )
