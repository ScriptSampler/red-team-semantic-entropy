"""Semantic clustering and discrete entropy.

Given the N samples for a question, group them into semantic
equivalence classes by union-find over bidirectional NLI entailment,
then compute the Shannon entropy of the cluster size distribution.

This is the Farquhar et al. semantic-entropy primitive. A higher
entropy means the model produced more genuinely different answers
across samples, which they interpret as higher uncertainty about the
underlying fact.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from .nli import NLI


@dataclass
class ClusterResult:
    assignments: list[int]      # cluster id per sample, in [0, n_clusters)
    n_clusters: int
    entropy_nats: float
    entropy_bits: float


def cluster_samples(samples: list[str], nli: NLI, batch_size: int = 64) -> list[int]:
    """Return a cluster id for each sample.

    Two samples land in the same cluster if NLI argmaxes both directions
    of the pair to entailment. Union-find collapses transitive closures
    (a-b and b-c equivalent forces a-c into the same cluster too).
    """
    n = len(samples)
    if n <= 1:
        return list(range(n))

    pairs = [(samples[i], samples[j]) for i, j in combinations(range(n), 2)]
    equiv = nli.bidirectional_equivalent_batch(pairs, batch_size=batch_size)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for k, (i, j) in enumerate(combinations(range(n), 2)):
        if equiv[k]:
            union(i, j)

    roots = [find(i) for i in range(n)]
    remap: dict[int, int] = {}
    out: list[int] = []
    for r in roots:
        if r not in remap:
            remap[r] = len(remap)
        out.append(remap[r])
    return out


def discrete_entropy(assignments: list[int], base: str = "nats") -> float:
    """Shannon entropy of the cluster size distribution."""
    if not assignments:
        return 0.0
    counts = Counter(assignments)
    total = sum(counts.values())
    log = math.log if base == "nats" else math.log2
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * log(p)
    return h


def cluster_and_score(samples: list[str], nli: NLI,
                      batch_size: int = 64) -> ClusterResult:
    assignments = cluster_samples(samples, nli, batch_size=batch_size)
    return ClusterResult(
        assignments=assignments,
        n_clusters=len(set(assignments)),
        entropy_nats=discrete_entropy(assignments, "nats"),
        entropy_bits=discrete_entropy(assignments, "bits"),
    )


def cluster_samples_exact(samples: list[str]) -> list[int]:
    """INDEPENDENT clusterer (external review B5 / audit finding 14): group samples
    by canonical-normalized string equality — NO NLI model. Used to separate "the
    paraphrase genuinely changed the model's answer distribution" from "the shared
    DeBERTa NLI is self-inconsistent": same model outputs, a different equivalence
    relation. Deliberately stricter than NLI (it will not merge paraphrases of one
    answer), so it is a lower-bound clusterer, not a drop-in replacement."""
    from .scoring import normalize_answer
    remap: dict[str, int] = {}
    out: list[int] = []
    for s in samples:
        key = normalize_answer(s)
        if key not in remap:
            remap[key] = len(remap)
        out.append(remap[key])
    return out


def cluster_and_score_exact(samples: list[str]) -> ClusterResult:
    """ClusterResult under the independent exact-match clusterer (no NLI)."""
    assignments = cluster_samples_exact(samples)
    return ClusterResult(
        assignments=assignments,
        n_clusters=len(set(assignments)),
        entropy_nats=discrete_entropy(assignments, "nats"),
        entropy_bits=discrete_entropy(assignments, "bits"),
    )


def cluster_samples_embedding(samples: list[str], embed_fn, threshold: float = 0.85) -> list[int]:
    """INDEPENDENT, semantically-aware clusterer (finding 14 adjudicator, critic entry
    14): group samples whose sentence-embedding cosine similarity >= threshold, via the
    same union-find skeleton as the NLI clusterer. `embed_fn(samples) -> array (n, d)`.

    The encoder must be a model whose training is independent of the DeBERTa-large-MNLI
    the detector uses (e.g. a sentence-transformer). This arm neither shares the NLI's
    confound (unlike the detector's own clusterer) nor over-counts surface form (unlike
    exact-match, which splits "Broncos" from "Denver Broncos"), so it is the arm that
    adjudicates the "SE fragile to any paraphrase" reframe."""
    import numpy as np
    n = len(samples)
    if n <= 1:
        return list(range(n))
    embs = np.asarray(embed_fn(samples), dtype=float)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = embs / norms
    sims = unit @ unit.T

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= threshold:
                union(i, j)

    roots = [find(i) for i in range(n)]
    remap: dict[int, int] = {}
    out: list[int] = []
    for r in roots:
        if r not in remap:
            remap[r] = len(remap)
        out.append(remap[r])
    return out


def cluster_and_score_embedding(samples: list[str], embed_fn,
                                threshold: float = 0.85) -> ClusterResult:
    """ClusterResult under the independent embedding-cosine clusterer."""
    assignments = cluster_samples_embedding(samples, embed_fn, threshold)
    return ClusterResult(
        assignments=assignments,
        n_clusters=len(set(assignments)),
        entropy_nats=discrete_entropy(assignments, "nats"),
        entropy_bits=discrete_entropy(assignments, "bits"),
    )


def cluster_samples_judge(samples: list[str], judge_fn) -> list[int]:
    """INDEPENDENT clusterer via an injected PAIRWISE equivalence judge (finding-14/15
    adjudicator of last resort, critic entry 16). `judge_fn(a, b) -> bool`. The judge
    must be a model that is BOTH independent of the victim (not the Llama that produced
    the samples — else circular) AND independent of the DeBERTa-MNLI (else it re-imports
    finding-14's confound), and must be SELF-VALIDATED (its own agreement with labeled
    paraphrase pairs reported) before it can adjudicate. Same union-find skeleton as the
    NLI clusterer; O(n^2) judge calls. Because sentence embedders proved near-chance on
    the adversarial case (AUROC 0.51 on hard short-answer negatives), a strong LLM-judge
    is the remaining candidate independent oracle."""
    n = len(samples)
    if n <= 1:
        return list(range(n))

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if judge_fn(samples[i], samples[j]):
                union(i, j)

    roots = [find(i) for i in range(n)]
    remap: dict[int, int] = {}
    out: list[int] = []
    for r in roots:
        if r not in remap:
            remap[r] = len(remap)
        out.append(remap[r])
    return out


def cluster_and_score_judge(samples: list[str], judge_fn) -> ClusterResult:
    """ClusterResult under the injected pairwise LLM-judge equivalence oracle."""
    assignments = cluster_samples_judge(samples, judge_fn)
    return ClusterResult(
        assignments=assignments,
        n_clusters=len(set(assignments)),
        entropy_nats=discrete_entropy(assignments, "nats"),
        entropy_bits=discrete_entropy(assignments, "bits"),
    )
