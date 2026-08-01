"""Tests for the null-objective beam ablation's pure logic. CPU-only, no models."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "null_objective_ablation",
    Path(__file__).resolve().parents[1] / "scripts" / "null_objective_ablation.py")
noa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(noa)


def test_hash01_deterministic_and_bounded():
    qs = ["Who won?", "Who was the winner?", "x" * 500, ""]
    for q in qs:
        v = noa.hash01(q)
        assert 0.0 <= v <= 1.0
        assert v == noa.hash01(q)                    # deterministic
    assert noa.hash01("a") != noa.hash01("b")        # not constant


def _rec(i, nb, rm):
    return {"question_id": f"q{i}", "null_beam_max": nb, "random_max": rm}


def test_paired_summary_safe_when_equal():
    recs = [_rec(i, 0.30 + 0.01 * i, 0.30 + 0.01 * i) for i in range(8)]
    s = noa.paired_summary(recs)
    assert s["n"] == 8
    assert s["verdict"].startswith("SAFE")


def test_paired_summary_flags_beam_inflation():
    # beam consistently ~0.3 nats above diffuse -> inflation flagged
    recs = [_rec(i, 0.55 + 0.02 * i, 0.25 + 0.02 * i) for i in range(8)]
    s = noa.paired_summary(recs)
    assert s["diff_ci"].lo > 0.05
    assert s["verdict"].startswith("BEAM INFLATES")


def test_paired_summary_skips_missing_arms_and_empty():
    recs = [_rec(0, None, 0.3), _rec(1, 0.4, None), _rec(2, 0.31, 0.30)]
    s = noa.paired_summary(recs)
    assert s["n"] == 1                                # only the complete pair
    assert noa.paired_summary([])["verdict"] == "no paired data"
