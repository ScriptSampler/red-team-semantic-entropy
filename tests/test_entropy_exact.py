"""Tests for the independent (exact-match) clusterer — finding 14. Hermetic."""
from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from se.entropy import (
    cluster_samples_exact, cluster_and_score_exact,
    cluster_samples_embedding, cluster_and_score_embedding,
)


def test_exact_clusters_by_normalized_string():
    samples = ["Paris", "paris.", "PARIS", "London", "london"]
    a = cluster_samples_exact(samples)
    assert a[0] == a[1] == a[2]     # Paris variants -> one cluster
    assert a[3] == a[4]             # London variants -> another
    assert a[0] != a[3]


def test_exact_entropy_extremes():
    same = cluster_and_score_exact(["Paris", "paris", "PARIS"])
    assert same.n_clusters == 1 and same.entropy_nats == 0.0
    diff = cluster_and_score_exact(["a", "b", "c", "d"])
    assert diff.n_clusters == 4
    assert abs(diff.entropy_nats - math.log(4)) < 1e-9


def test_exact_clusterer_takes_no_nli():
    # Structural guarantee it is independent of the DeBERTa NLI (finding 14).
    assert "nli" not in inspect.signature(cluster_samples_exact).parameters


# ---- embedding-cosine clusterer (the reframe-(b) adjudicator) ----------------

_VECS = {
    "Paris": [1.0, 0.0, 0.0],
    "the capital of France, Paris": [0.99, 0.10, 0.0],   # paraphrase of Paris
    "London": [0.0, 1.0, 0.0],
    "the UK capital London": [0.10, 0.99, 0.0],           # paraphrase of London
}


def _fake_embed(strings):
    return np.array([_VECS[s] for s in strings])


def test_embedding_merges_paraphrases_not_surface_only():
    samples = ["Paris", "the capital of France, Paris", "London", "the UK capital London"]
    a = cluster_samples_embedding(samples, _fake_embed, threshold=0.9)
    assert a[0] == a[1]          # Paris + its paraphrase merge (unlike exact-match)
    assert a[2] == a[3]          # London + its paraphrase merge
    assert a[0] != a[2]          # Paris vs London stay apart
    cs = cluster_and_score_embedding(samples, _fake_embed, threshold=0.9)
    assert cs.n_clusters == 2


def test_embedding_threshold_controls_granularity():
    samples = ["Paris", "the capital of France, Paris"]
    # a very high threshold refuses to merge the near-but-not-identical vectors
    strict = cluster_samples_embedding(samples, _fake_embed, threshold=0.999)
    assert strict == [0, 1]
    # a lenient threshold merges them
    lenient = cluster_samples_embedding(samples, _fake_embed, threshold=0.9)
    assert lenient == [0, 0]


def test_embedding_clusterer_takes_no_nli():
    assert "nli" not in inspect.signature(cluster_samples_embedding).parameters
