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


# --------------------------------------------------------------- the gate (critique_log 23)

import json                                                          # noqa: E402
import numpy as np                                                   # noqa: E402
import pytest                                                        # noqa: E402

A = 181


def _gate_recs(n, benign_fn, *, b=1, mx=1.0):
    return [{"question_id": f"q{j}", "null_beam_max": mx, "b_null": b,
             "benign_moves": benign_fn(j)} for j in range(n)]


def test_gate_centre_is_m_over_A_plus_one_and_uses_the_ACHIEVED_m():
    """The band's centre must track the benign draws a target actually got, not the m that
    was requested: `_benign_moves_arms` gives up after 5m tries, so a low-feasibility target
    can return fewer than m and would otherwise fail the band for the wrong reason."""
    full = noa.gate_summary(_gate_recs(10, lambda j: [0.0] * 50), A)
    assert full["expected_S"] == pytest.approx(10 * 50 / (A + 1))
    short = noa.gate_summary(_gate_recs(10, lambda j: [0.0] * (50 if j % 2 else 20)), A)
    assert short["expected_S"] == pytest.approx(5 * (50 + 20) / (A + 1))
    assert short["m_total"] == 350


def test_gate_passes_under_a_true_null():
    rng = np.random.default_rng(0)
    recs = []
    for j in range(40):
        a = rng.gamma(2.0, 1.0, A)
        mx = float(a.max())
        recs.append({"question_id": f"q{j}", "null_beam_max": mx,
                     "b_null": int((a == mx).sum()),
                     "benign_moves": [float(x) for x in rng.gamma(2.0, 1.0, 50)]})
    g = noa.gate_summary(recs, A)
    assert 0.5 <= g["ratio"] <= 2.0
    assert g["verdict"].startswith("PASS")


def test_gate_fails_low_when_the_null_beam_beats_benign_more_than_chance():
    # null-arm max far above every benign draw on every target -> zero exceedances
    g = noa.gate_summary(_gate_recs(40, lambda j: list(np.linspace(0.0, 0.5, 50)), mx=9.9), A)
    assert g["observed_S_mean"] == 0.0
    assert g["ratio"] == 0.0
    assert g["verdict"].startswith("FAIL-LOW")


def test_gate_fails_high_and_points_at_the_duplication_offset():
    # benign draws routinely beat the null-arm max -> far more exceedances than m/(A+1)
    g = noa.gate_summary(_gate_recs(40, lambda j: [5.0] * 50, mx=0.1), A)
    assert g["ratio"] > 2.0
    assert g["verdict"].startswith("FAIL-HIGH")
    assert "duplication" in g["verdict"]


def test_gate_needs_both_arms():
    assert noa.gate_summary([], A)["n"] == 0
    assert noa.gate_summary([{"question_id": "q", "null_beam_max": None, "b_null": 1,
                              "benign_moves": [0.1]}], A)["n"] == 0
    assert noa.gate_summary([{"question_id": "q", "null_beam_max": 0.5, "b_null": 1,
                              "benign_moves": []}], A)["n"] == 0


def test_load_benign_from_diag_reads_null_controls_dump(tmp_path):
    p = tmp_path / "diag.json"
    p.write_text(json.dumps([
        {"question_id": "a", "benign": {"nli": [0.1, 0.2], "exact": [0.3]}},
        {"question_id": "b", "benign": {"nli": [0.4, None, 0.5]}},   # judge arm can be sparse
        {"question_id": "c", "benign": {"nli": []}},                 # dropped, not a KeyError
        {"question_id": "d"},
    ]), encoding="utf-8")
    got = noa.load_benign_from_diag(p)
    assert got == {"a": [0.1, 0.2], "b": [0.4, 0.5]}
    assert noa.load_benign_from_diag(p, arm="exact") == {"a": [0.3]}
