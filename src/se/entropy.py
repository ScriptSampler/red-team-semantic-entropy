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
