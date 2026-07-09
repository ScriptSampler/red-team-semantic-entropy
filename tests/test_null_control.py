"""Tests for the three-band null-control aggregation (finding 13 / DoD). CPU-only.

Validates the pure arithmetic that places the attack move as a percentile within the
full benign-move distribution and orders the seed / benign / attack bands — without
the GPU scoring path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "scripts"))

import null_control
from null_control import summarize_bands, _percentile_below, _move, survival_ratio


def test_seed_band_excludes_baseline_seed(monkeypatch):
    # BUG regression (verify workflow): `before` is generated at gen.seed=0, so a seed-0
    # draw in the seed band reproduces it exactly -> a structural 0.0 that deflates the
    # noise floor. The band must use seeds 1..n_seeds, never 0.
    seen = []
    monkeypatch.setattr(null_control, "_arms",
                        lambda q, pair, gen, ef, thr, jf=None, seed=None: (seen.append(seed) or (0.0, 0.0, None, None)))
    null_control._seed_moves_arms("q", (1.0, 1.0, None, None), "hide", None, None, 3, None, 0.82)
    assert 0 not in seen
    assert seen == [1, 2, 3]


def test_move_direction():
    assert _move("hide", 2.0, 1.0) == 1.0          # hide wants entropy DOWN
    assert _move("false_alarm", 1.0, 2.0) == 1.0   # false-alarm wants it UP
    assert _move("hide", 1.0, 2.0) == -1.0         # wrong direction -> negative


def test_percentile_below():
    assert _percentile_below(0.5, [0.1, 0.2, 0.3]) == 1.0
    assert _percentile_below(0.25, [0.1, 0.2, 0.3, 0.4]) == 0.5
    assert _percentile_below(0.0, [0.1, 0.2]) == 0.0


def test_bands_attack_clearly_beats_benign():
    attack = [1.0, 1.2]
    benign = [[0.1, 0.2, 0.3], [0.2, 0.3, 0.4]]
    seed = [[0.0, 0.05], [0.0, 0.03]]
    s = summarize_bands(attack, benign, seed)
    assert s["n"] == 2
    assert s["mean_attack_move"] > s["mean_benign_move"] > s["mean_seed_move"]
    assert s["beats_benign_p90_ci"].point == 1.0
    assert s["beats_benign_max_ci"].point == 1.0
    assert abs(s["mean_attack_percentile"] - 1.0) < 1e-9
    assert s["net_vs_benign_mean_ci"].point > 0


def test_bands_attack_within_benign_distribution():
    # attack sits in the middle of the benign spread -> not in the tail, net ~0
    attack = [0.25, 0.25]
    benign = [[0.0, 0.1, 0.2, 0.3, 0.4, 0.5]] * 2
    seed = [[0.0, 0.1]] * 2
    s = summarize_bands(attack, benign, seed)
    assert s["beats_benign_p90_ci"].point == 0.0
    assert 0.3 < s["mean_attack_percentile"] < 0.7


def test_p90_and_max_success_can_differ():
    # attack beats the benign 90th percentile (~0.45) but NOT the benign max (0.5):
    # the strict max-vs-max metric is stricter and budget-biased toward the attack.
    attack = [0.46]
    benign = [[0.0, 0.1, 0.2, 0.3, 0.4, 0.5]]
    seed = [[0.0]]
    s = summarize_bands(attack, benign, seed)
    assert s["beats_benign_max_ci"].point == 0.0
    assert s["beats_benign_p90_ci"].point == 1.0


def test_survival_ratio_full_survival():
    # embedding net == NLI net per target -> ratio ~1 (attack survives independent encoder)
    sr = survival_ratio([1.0, 0.8, 1.2], [1.0, 0.8, 1.2], n_boot=500)
    assert abs(sr.point - 1.0) < 1e-9
    assert sr.lo <= 1.0 <= sr.hi + 1e-9


def test_survival_ratio_collapse():
    # embedding net ~0 while NLI net large -> ratio ~0 (attack was NLI-clusterer artifact)
    sr = survival_ratio([1.0, 0.8, 1.2], [0.0, 0.02, 0.0], n_boot=500)
    assert sr.point < 0.1


def test_survival_ratio_none_on_empty():
    assert survival_ratio([], [1.0, 2.0]) is None
    assert survival_ratio([1.0], []) is None


def test_benign_over_seed_flags_reframe_b():
    # benign paraphrasing moves the score clearly more than reseeding does
    attack = [1.0]
    benign = [[0.3, 0.4, 0.5]]
    seed = [[0.0, 0.05, 0.02]]
    s = summarize_bands(attack, benign, seed)
    assert s["benign_over_seed_ci"].point == 1.0
