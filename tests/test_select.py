"""Tests for the score-independent stratified sampler (B1). Hermetic."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import inspect

from se.attacks.select import (
    _stratum_ids, campaign_pool, assert_detector_blind, select_examples,
)


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


# ---- B1 enforcement: SE and SRE cells share the pool by construction ----------

def test_selection_functions_are_detector_blind():
    # The enforcement DoD: no selection function may expose a detector parameter,
    # so the SE and SRE cells CANNOT diverge. Structural, not behavioural.
    assert_detector_blind()   # raises if violated
    assert "detector" not in inspect.signature(campaign_pool).parameters
    assert "detector" not in inspect.signature(select_examples).parameters


def test_campaign_pool_squad_routes_through_seeded_label_fresh():
    # squad has no cache -> campaign_pool must call label_fresh(want, n, seed),
    # forwarding the seed and NEVER a detector. Hermetic: fake the callback.
    seen = []
    def fake_label_fresh(want, n, seed):
        seen.append((want, n, seed))
        return [f"{want}-{seed}-{i}" for i in range(n)]
    out = campaign_pool("squad", "wrong", 3, seed=7, label_fresh=fake_label_fresh)
    assert seen == [("wrong", 3, 7)]      # seed forwarded, no detector in the call
    assert out == ["wrong-7-0", "wrong-7-1", "wrong-7-2"]


def test_se_and_sre_squad_cells_draw_identical_pool():
    # Directly model the two call sites (critic DoD 1): an "SE cell" and an "SRE
    # cell" both call campaign_pool with the same (dataset, want, n, seed). Since
    # campaign_pool has no detector arg, the calls are identical -> same pool.
    def fake_label_fresh(want, n, seed):
        return [f"q{want}{seed}_{i}" for i in range(n)]
    se_cell = campaign_pool("squad", "wrong", 4, seed=0, label_fresh=fake_label_fresh)
    sre_cell = campaign_pool("squad", "wrong", 4, seed=0, label_fresh=fake_label_fresh)
    assert se_cell == sre_cell


def test_campaign_pool_squad_requires_label_fresh():
    # Fail loud rather than silently fall back to a different selection rule.
    try:
        campaign_pool("squad", "wrong", 3, seed=0)
    except ValueError as e:
        assert "label_fresh" in str(e)
    else:
        raise AssertionError("expected ValueError when squad label_fresh missing")
