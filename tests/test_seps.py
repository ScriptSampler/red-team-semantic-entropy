"""CPU-only tests for the SEP probe logic and binarization. No GPU/model."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.seps import SEPProbe, binarize_entropy


def test_binarize_median_default():
    e = np.array([0.0, 1.0, 2.0, 3.0])
    lab = binarize_entropy(e)  # median 1.5 -> [0,0,1,1]
    assert lab.tolist() == [0, 0, 1, 1]


def test_binarize_explicit_threshold():
    e = np.array([0.1, 0.5, 0.9])
    lab = binarize_entropy(e, threshold=0.5)  # >= 0.5 -> 1
    assert lab.tolist() == [0, 1, 1]


def test_sep_probe_learns_separable_signal():
    rng = np.random.RandomState(0)
    # Two clusters: low-entropy near 0, high-entropy near 5 on feature 0.
    n = 200
    low = rng.normal(0.0, 0.5, size=(n, 4))
    high = rng.normal(5.0, 0.5, size=(n, 4))
    X = np.vstack([low, high])
    y = np.array([0] * n + [1] * n)
    probe = SEPProbe.train(X, y)
    scores = probe.score(X)
    # High-entropy rows should score higher on average than low-entropy rows.
    assert scores[n:].mean() > scores[:n].mean()
    # And the probe should separate them well.
    from sklearn.metrics import roc_auc_score
    assert roc_auc_score(y, scores) > 0.95


def test_sep_probe_score_shape_and_range():
    rng = np.random.RandomState(1)
    X = rng.normal(size=(10, 6))
    y = (X[:, 0] > 0).astype(int)
    probe = SEPProbe.train(X, y)
    s = probe.score(X)
    assert s.shape == (10,)
    assert np.all((s >= 0) & (s <= 1))
