"""Tests for the null/noise-floor aggregation (finding 13 tooling). CPU-only.

Validates the pure arithmetic that turns per-target (attack move, benign-floor move)
pairs into the net-of-floor headline numbers, without the GPU scoring path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "scripts"))

from null_control import summarize_null, _move


def test_move_direction():
    assert _move("hide", 2.0, 1.0) == 1.0          # hide wants entropy DOWN
    assert _move("false_alarm", 1.0, 2.0) == 1.0   # false-alarm wants it UP
    assert _move("hide", 1.0, 2.0) == -1.0         # wrong direction -> negative


def test_attack_beats_floor():
    atk = [1.0, 1.2, 0.9]
    null = [0.2, 0.3, 0.1]
    s = summarize_null(atk, null, [0.1, 0.1, 0.1])
    assert s["n"] == 3
    assert abs(s["mean_attack"] - (3.1 / 3)) < 1e-9
    assert abs(s["mean_null"] - 0.2) < 1e-9
    assert s["net_success_ci"].point == 1.0        # all nets > 0
    assert s["net_ci"].point > 0                    # net effect clearly positive


def test_attack_within_floor_is_not_success():
    # attack move does NOT exceed the benign floor -> not success net of floor
    atk = [0.3, 0.2]
    null = [0.5, 0.4]
    s = summarize_null(atk, null, [float("nan"), 0.2])
    assert s["net_success_ci"].point == 0.0
    assert s["net_ci"].point < 0
    assert abs(s["mean_seed_std"] - 0.2) < 1e-9    # nan dropped from the noise band


def test_mixed_partial_success():
    atk = [1.0, 0.1, 0.8, 0.05]
    null = [0.2, 0.3, 0.2, 0.4]        # targets 0,2 beat floor; 1,3 do not
    s = summarize_null(atk, null, [0.1] * 4)
    assert abs(s["net_success_ci"].point - 0.5) < 1e-9
