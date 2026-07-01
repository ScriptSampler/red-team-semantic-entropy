"""Tests for the score-independent stratified sampler (B1). Hermetic."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.select import _stratum_ids


def _labels(entropies):
    # qid -> {greedy_correct, entropy_nats}; even ids wrong, odd ids right.
    return {f"q{i}": {"greedy_correct": (i % 2 == 1), "entropy_nats": e}
            for i, e in enumerate(entropies)}


def test_stratum_deterministic():
    labs = _labels([0.1 * i for i in range(20)])
    a = _stratum_ids("wrong", 0, labs)
    b = _stratum_ids("wrong", 0, labs)
    assert a == b


def test_stratum_respects_correctness():
    labs = _labels([0.1 * i for i in range(20)])
    wrong = _stratum_ids("wrong", 0, labs)
    right = _stratum_ids("right", 0, labs)
    assert all(labs[q]["greedy_correct"] is False for q in wrong)
    assert all(labs[q]["greedy_correct"] is True for q in right)
    assert set(wrong).isdisjoint(right)


def test_stratum_ignores_entropy():
    # Two label sets identical in correctness, DIFFERENT entropy -> same selection.
    labs_a = _labels([0.1 * i for i in range(20)])
    labs_b = _labels([9.9 - 0.1 * i for i in range(20)])   # entropy reversed
    assert _stratum_ids("wrong", 0, labs_a) == _stratum_ids("wrong", 0, labs_b)
    assert _stratum_ids("right", 3, labs_a) == _stratum_ids("right", 3, labs_b)


def test_stratum_seed_changes_order():
    labs = _labels([0.1 * i for i in range(40)])
    assert _stratum_ids("wrong", 0, labs) != _stratum_ids("wrong", 1, labs)
