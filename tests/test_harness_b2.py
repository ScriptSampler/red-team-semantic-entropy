"""B2 (external review §3): answer-invariance success logic. CPU-only.

Verifies the two pure helpers that gate attack success — entropy must move in
the intended direction AND the hallucination status must survive the paraphrase
(hide: model still wrong under Q'; false-alarm: model still right). No models.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.harness import _entropy_moved, _status_held


# ---- direction of the entropy move -----------------------------------------

def test_hide_requires_entropy_drop():
    assert _entropy_moved("hide", 2.0, 1.0, 0.25) is True     # dropped 1.0
    assert _entropy_moved("hide", 2.0, 1.9, 0.25) is False    # only 0.1 < 0.25
    assert _entropy_moved("hide", 1.0, 2.0, 0.25) is False    # rose, wrong way


def test_false_alarm_requires_entropy_rise():
    assert _entropy_moved("false_alarm", 1.0, 2.0, 0.25) is True
    assert _entropy_moved("false_alarm", 1.0, 1.1, 0.25) is False
    assert _entropy_moved("false_alarm", 2.0, 1.0, 0.25) is False


def test_move_threshold_is_inclusive():
    assert _entropy_moved("hide", 1.25, 1.0, 0.25) is True     # exactly 0.25


# ---- B2 status invariance: the core of the review §3 fix --------------------

def test_hide_status_held_only_if_still_wrong():
    # A hide "win" where the model became CORRECT under Q' is NOT a win: the
    # entropy fell because the hallucination vanished, not because it was hidden.
    assert _status_held("hide", correct_under_q_prime=False) is True   # still wrong -> held
    assert _status_held("hide", correct_under_q_prime=True) is False   # now right -> void


def test_false_alarm_status_held_only_if_still_right():
    assert _status_held("false_alarm", correct_under_q_prime=True) is True
    assert _status_held("false_alarm", correct_under_q_prime=False) is False


def test_success_is_conjunction_of_move_and_status():
    # Reproduce the harness gate: success <=> (moved AND feasible) AND status_held.
    def success(attack, e_before, e_after, feasible, correct_qp, delta=0.25):
        eaf = _entropy_moved(attack, e_before, e_after, delta) and feasible
        return bool(eaf and _status_held(attack, correct_qp))

    # hide: big drop, feasible, still wrong -> success
    assert success("hide", 2.0, 1.0, True, correct_qp=False) is True
    # same drop but model now correct under Q' -> NOT a success (B2 kills it)
    assert success("hide", 2.0, 1.0, True, correct_qp=True) is False
    # drop but infeasible paraphrase -> no success
    assert success("hide", 2.0, 1.0, False, correct_qp=False) is False
    # no move -> no success even if status held
    assert success("hide", 2.0, 1.95, True, correct_qp=False) is False
    # false-alarm: big rise, feasible, still right -> success
    assert success("false_alarm", 1.0, 2.0, True, correct_qp=True) is True
    # rise but model wrong under Q' -> the alarm is a true positive, not a false one
    assert success("false_alarm", 1.0, 2.0, True, correct_qp=False) is False
