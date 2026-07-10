"""Tests for scripts/prepare_equivalence_audit.py — synthetic outcomes, no models."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "prepare_equivalence_audit",
    Path(__file__).resolve().parent.parent / "scripts" / "prepare_equivalence_audit.py")
pea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pea)


def _recs():
    recs = []
    for i in range(20):
        recs.append({"question_id": f"fa{i}", "attack": "false_alarm", "detector": "se",
                     "question": f"q{i}", "best_query": f"q'{i}",
                     "answer_under_q_prime": "A", "correct_under_q_prime": True,
                     "status_held": True, "delta": 0.3, "success": i % 2 == 0})
    for i in range(6):
        recs.append({"question_id": f"hd{i}", "attack": "hide", "detector": "se",
                     "question": f"h{i}", "best_query": f"h'{i}",
                     "answer_under_q_prime": "B", "correct_under_q_prime": False,
                     "status_held": True, "delta": -0.3, "success": True})
    return recs


def test_load_success_filters(tmp_path):
    p = tmp_path / "triviaqa_se_false_alarm.jsonl"
    import json
    p.write_text("\n".join(json.dumps(r) for r in _recs()), encoding="utf-8")
    wins = pea.load_success([p])
    assert all(w["success"] for w in wins)
    assert len(wins) == 10 + 6           # 10 FA successes (even i) + 6 hide successes


def test_sample_is_deterministic_and_stratified():
    wins = [r for r in _recs() if r["success"]]
    a = pea.sample_audit(wins, n=8, seed=0)
    b = pea.sample_audit(wins, n=8, seed=0)
    assert [r["question_id"] for r in a] == [r["question_id"] for r in b]  # deterministic
    assert len(a) == 8
    attacks = {r["attack"] for r in a}
    assert "false_alarm" in attacks and "hide" in attacks  # both strata represented
    # a different seed generally reorders the draw
    c = pea.sample_audit(wins, n=8, seed=1)
    assert [r["question_id"] for r in a] != [r["question_id"] for r in c] or len(wins) <= 8


def test_sample_caps_at_available():
    wins = [r for r in _recs() if r["success"]]
    got = pea.sample_audit(wins, n=1000, seed=0)
    assert len(got) == len(wins)          # cannot exceed the pool


def test_write_csv_has_blank_human_cols(tmp_path):
    wins = [r for r in _recs() if r["success"]]
    rows = pea.sample_audit(wins, n=5, seed=0)
    out = tmp_path / "audit.csv"
    pea.write_csv(rows, out)
    header, *data = out.read_text(encoding="utf-8").splitlines()
    for col in pea.HUMAN_COLS:
        assert col in header
    assert len(data) == 5
    # human columns are trailing-empty on every data row
    assert all(line.rstrip().endswith(",,") or line.endswith(",") for line in data)
