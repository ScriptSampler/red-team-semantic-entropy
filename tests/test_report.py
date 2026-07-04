"""Tests for review-compliant campaign reporting (B4 + B2 nits). CPU-only.

Synthetic AttackOutcome stand-ins; no models, no cache.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.report import (
    summarize_cell, matrix_operating_point, matrix_operating_point_sweep,
    matrix_answer_flip_breakdown, render_cell_md,
)


@dataclass
class FakeOutcome:
    attack: str
    detector: str
    entropy_before: float
    entropy_after: float
    feasible: bool
    entropy_and_feasible: bool
    success: bool
    status_held: bool
    correct_under_q_prime: bool = False   # only read by the matrix answer-flip split
    frac_correct_under_q_prime: float = -1.0   # sampled status (finding 16); -1 = not computed


def _hide_cell():
    # 5 hide outcomes with known bookkeeping:
    #   feasible      = [T,T,T,F,T] -> 4/5
    #   entropy_only  = [T,T,F,F,T] -> 3   (the OLD criterion)
    #   gated success = [T,F,F,F,T] -> 2   (B2)
    #   attrition     = 3 - 2 = 1
    #   answer_flip   = 1 (the entropy+feasible outcome whose status did NOT hold)
    return [
        FakeOutcome("hide", "se", 2.0, 1.0, True,  True,  True,  True),   # real win
        FakeOutcome("hide", "se", 2.0, 1.0, True,  True,  False, False),  # voided: answer flip
        FakeOutcome("hide", "se", 2.0, 1.9, True,  False, False, True),   # feasible, tiny move
        FakeOutcome("hide", "se", 2.0, 0.5, False, False, False, True),   # infeasible
        FakeOutcome("hide", "se", 2.0, 1.2, True,  True,  True,  True),   # real win
    ]


def test_summarize_cell_counts_and_rates():
    s = summarize_cell(_hide_cell())
    assert s["n"] == 5
    assert abs(s["feasible_rate"].point - 0.8) < 1e-9
    assert abs(s["success_entropy_only"].point - 0.6) < 1e-9    # 3/5
    assert abs(s["success_gated"].point - 0.4) < 1e-9           # 2/5
    assert s["attrition_count"] == 1
    assert s["n_entropy_and_feasible"] == 3
    assert s["answer_flip_count"] == 1
    assert abs(s["status_held_rate_among_ef"] - 2 / 3) < 1e-9
    assert abs(s["answer_flip_rate_among_ef"] - 1 / 3) < 1e-9
    assert abs(s["attrition_rate_of_would_be"] - 1 / 3) < 1e-9
    # mean intended move among feasible = mean(1.0, 1.0, 0.1, 0.8) = 0.725
    assert abs(s["mean_move_feasible"] - 0.725) < 1e-9


def test_status_only_read_among_entropy_and_feasible():
    # B2 nit 2: a never-re-checked outcome (entropy_and_feasible False) with
    # status_held False must NOT leak into the answer-flip / held stats.
    cell = _hide_cell() + [
        FakeOutcome("hide", "se", 2.0, 1.95, True, False, False, False),
    ]
    s = summarize_cell(cell)
    assert s["n"] == 6
    assert s["n_entropy_and_feasible"] == 3          # unchanged
    assert s["answer_flip_count"] == 1               # the extra False does not count
    assert abs(s["status_held_rate_among_ef"] - 2 / 3) < 1e-9


def test_cutoff_curve_is_monotone():
    s = summarize_cell(_hide_cell())
    rates = [r for _, r in s["success_over_cutoffs"]]
    assert all(rates[i] >= rates[i + 1] for i in range(len(rates) - 1))
    assert rates[0] == 0.8       # cutoff 0 -> every feasible outcome counts (4/5)


def test_empty_cell():
    assert summarize_cell([])["n"] == 0
    assert render_cell_md({"n": 0}) == ["(no outcomes)"]


def test_matrix_operating_point_flips():
    hide = [FakeOutcome("hide", "se", cb, ca, True, True, True, True)
            for cb, ca in [(0.5, 0.1), (0.6, 0.6), (0.7, 0.7)]]   # o1 flips down
    fa = [FakeOutcome("false_alarm", "se", cb, ca, True, True, True, True)
          for cb, ca in [(0.1, 0.5), (0.2, 0.2), (0.3, 0.3)]]     # o1 flips up
    f = matrix_operating_point(hide, fa, target_fpr=0.1)
    assert abs(f["threshold"] - 0.28) < 1e-9
    assert f["n_hide"] == 3 and f["hide_flagged_to_unflagged"] == 1
    assert f["n_false_alarm"] == 3 and f["fa_unflagged_to_flagged"] == 1
    assert abs(f["hide_flip_rate"] - 1 / 3) < 1e-9
    assert abs(f["fa_flip_rate"] - 1 / 3) < 1e-9


def test_finding16_sampled_gate():
    # FA cell: sampled fraction-correct decides "still right" (>0.5), among ent+feasible.
    def fo(frac):
        return FakeOutcome("false_alarm", "se", 1.0, 2.0, True, True, True, True,
                           correct_under_q_prime=True, frac_correct_under_q_prime=frac)
    cell = [fo(0.9), fo(0.3), fo(0.8)]        # 0.9 & 0.8 held; 0.3 not -> 2/3
    s = summarize_cell(cell)
    assert s["success_gated_sampled"] is not None
    assert abs(s["success_gated_sampled"].point - 2 / 3) < 1e-9


def test_finding16_none_without_frac():
    # default FakeOutcomes carry frac = -1 -> the sampled gate is not defined
    s = summarize_cell(_hide_cell())
    assert s["success_gated_sampled"] is None


def test_render_cell_md_smoke():
    lines = render_cell_md(summarize_cell(_hide_cell()))
    body = "\n".join(lines)
    assert "invariance-gated" in body
    assert "answer-flip" in body


def test_render_guards_empty_entropy_and_feasible():
    # n > 0 but NO outcome moved entropy -> n_ef == 0. Must not print "nan%".
    cell = [FakeOutcome("hide", "se", 2.0, 1.98, True, False, False, True)
            for _ in range(3)]
    s = summarize_cell(cell)
    assert s["n"] == 3 and s["n_entropy_and_feasible"] == 0
    body = "\n".join(render_cell_md(s))
    assert "nan%" not in body.lower()
    assert "n/a" in body


def test_matrix_answer_flip_breakdown_splits_by_direction():
    # hide: 2 entropy+feasible, one became correct under Q' (status not held).
    hide = [
        FakeOutcome("hide", "se", 2.0, 1.0, True, True, False, False, correct_under_q_prime=True),
        FakeOutcome("hide", "se", 2.0, 1.0, True, True, True, True, correct_under_q_prime=False),
    ]
    # false_alarm: 2 entropy+feasible, one became wrong under Q' (status not held).
    fa = [
        FakeOutcome("false_alarm", "se", 1.0, 2.0, True, True, False, False, correct_under_q_prime=False),
        FakeOutcome("false_alarm", "se", 1.0, 2.0, True, True, True, True, correct_under_q_prime=True),
    ]
    b = matrix_answer_flip_breakdown(hide, fa)
    assert b["hide_became_correct"] == 1 and b["hide_ef_n"] == 2
    assert b["fa_became_wrong"] == 1 and b["fa_ef_n"] == 2
    assert abs(b["hide_became_correct_rate"] - 0.5) < 1e-9
    assert abs(b["fa_became_wrong_rate"] - 0.5) < 1e-9


def test_operating_point_sweep_covers_fprs():
    hide = [FakeOutcome("hide", "se", cb, ca, True, True, True, True)
            for cb, ca in [(0.5, 0.1), (0.6, 0.6), (0.7, 0.7)]]
    fa = [FakeOutcome("false_alarm", "se", cb, ca, True, True, True, True)
          for cb, ca in [(0.1, 0.5), (0.2, 0.2), (0.3, 0.3)]]
    sweep = matrix_operating_point_sweep(hide, fa)
    assert [row["target_fpr"] for row in sweep] == [0.05, 0.10, 0.20]
    assert all(row["n_negatives_for_threshold"] == 3 for row in sweep)
