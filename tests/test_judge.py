"""Tests for the LLM-judge equivalence oracle logic (parse + symmetric wrap). Hermetic."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.judge import _parse_yes_no, make_judge_fn


def test_parse_yes_no():
    assert _parse_yes_no("Yes") is True
    assert _parse_yes_no("yes, the same") is True
    assert _parse_yes_no("No.") is False
    assert _parse_yes_no("No, different entities") is False
    assert _parse_yes_no("") is False                 # conservative default
    assert _parse_yes_no("well, no — but arguably yes") is False   # 'no' precedes 'yes'
    assert _parse_yes_no("definitely yes not no") is True          # 'yes' precedes 'no'


def test_make_judge_fn_symmetric_agreement():
    calls = []
    judge = make_judge_fn(lambda p: (calls.append(p) or "yes"), symmetric=True)
    assert judge("a", "b") is True
    assert len(calls) == 2                              # both orderings queried


def test_make_judge_fn_symmetric_disagreement_is_conservative():
    # 'yes' for (a,b) but 'no' for (b,a) -> not equivalent (an equivalence relation must
    # be order-invariant; disagreement is resolved conservatively as not-equivalent).
    def gen(p):
        return "yes" if "Answer 1: a" in p else "no"
    judge = make_judge_fn(gen, symmetric=True)
    assert judge("a", "b") is False


def test_make_judge_fn_asymmetric_single_query():
    calls = []
    judge = make_judge_fn(lambda p: (calls.append(p) or "no"), symmetric=False)
    assert judge("a", "b") is False
    assert len(calls) == 1
