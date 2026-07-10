"""Tests for scripts/diagnose_benign_floor.py — synthetic per-target records, no models."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "diagnose_benign_floor",
    Path(__file__).resolve().parent.parent / "scripts" / "diagnose_benign_floor.py")
dbf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dbf)


def _rec(i, base_judge, benign_judge, benign_nli=(-0.02, 0.0)):
    return {
        "detector": "se", "attack": "false_alarm", "question_id": f"q{i}",
        "baseline": {"nli": 0.5, "exact": 0.2, "embed": 0.4, "judge": base_judge},
        "attack_move": {"nli": 0.4, "exact": 0.05, "embed": 0.3, "judge": 0.37},
        "benign": {"nli": list(benign_nli), "exact": [-0.06], "embed": [-0.05],
                   "judge": [benign_judge]},
        "seed": {"nli": [-0.08], "exact": [-0.06], "embed": [-0.05], "judge": [-0.08]},
    }


def test_h_split_signature():
    # baseline_judge = 0.5 + gap (gap = 0.1*i > 0); benign_judge = -0.5*gap (neg. corr with gap)
    recs = [_rec(i, 0.5 + 0.1 * i, -0.5 * (0.1 * i)) for i in range(1, 9)]
    d = dbf.diagnose(recs)
    assert d["n"] == 8
    assert d["arms"]["judge"]["benign_floor"] < 0          # a real negative floor
    assert d["baseline_gap_judge_minus_nli"]["lo"] > 0     # judge splits baseline more
    assert d["corr_benign_judge_vs_gap"] < -0.2            # benign_judge falls with the gap
    assert d["verdict"].startswith("H_split")


def test_h_noise_when_floor_straddles_zero():
    # benign_judge symmetric around 0 -> floor CI straddles 0 -> H_noise-leaning
    recs = [_rec(i, 0.5 + 0.1 * i, 0.3 if i % 2 else -0.3) for i in range(1, 9)]
    d = dbf.diagnose(recs)
    assert d["verdict"].startswith("H_noise")


def test_empty_and_missing_arm():
    assert dbf.diagnose([], "se", "false_alarm")["verdict"] == "no data"
    # a record whose embed benign list is empty must be skipped for embed, not crash
    recs = [_rec(i, 0.5 + 0.1 * i, -0.05 * i) for i in range(1, 5)]
    for r in recs:
        r["benign"]["embed"] = []
    d = dbf.diagnose(recs)
    assert "embed" not in d["arms"]        # skipped cleanly
    assert "judge" in d["arms"]            # judge still analysed
