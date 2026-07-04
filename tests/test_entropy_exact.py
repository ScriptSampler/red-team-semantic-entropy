"""Tests for the independent (exact-match) clusterer — finding 14. Hermetic."""
from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.entropy import cluster_samples_exact, cluster_and_score_exact


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
