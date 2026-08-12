"""Tests for scripts/crossing_test.py — the operating-point crossing diagnostic.

Covers the four things that can silently go wrong: (1) tau computed off the fair-pool
clean scores, including the discreteness that makes the nominal FPR unattainable;
(2) crossing counts on a fixture whose answer is known by hand; (3) the 11/80 empty
`feasible_objs` targets; (4) that a missing input RAISES rather than degrading into a
default threshold or a fabricated benign arm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import crossing_test as CT  # noqa: E402


# --------------------------------------------------------------------------- fixtures

def _row(qid, before, after, objs, **kw):
    r = {"question_id": qid, "attack": "false_alarm", "detector": "se",
         "entropy_before": before, "entropy_after": after, "feasible_objs": list(objs),
         "n_feasible_at_best": 1, "n_objective_calls": 181,
         "success": bool(objs), "status_held": True}
    r.update(kw)
    return r


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def fixture_rows():
    """Four targets with a hand-computable answer at tau = 2.0, rule '>='.

      t1  objs [1.0, 2.0, 2.5]        -> 2 of 3 cross (2.0 counts under '>=')
      t2  objs [1.5, 1.9]             -> 0 of 2
      t3  objs [2.3, 2.3, 2.3, 2.3]   -> 4 of 4
      t4  objs []                     -> empty: dropped, or 1 candidate under 'original'
                                         (entropy_before 1.2, which does NOT cross)
      totals over the three non-empty: 6 crossings of 9 candidates.
    """
    return [
        _row("t1", 1.0, 2.5, [1.0, 2.0, 2.5]),
        _row("t2", 1.5, 1.9, [1.5, 1.9]),
        _row("t3", 1.6, 2.3, [2.3, 2.3, 2.3, 2.3]),
        _row("t4", 1.2, 1.2, []),
    ]


# ------------------------------------------------------------------- tau computation

def test_tau_is_the_fair_pool_quantile():
    """tau must be the clean-score threshold at the target FPR, on CORRECT answers."""
    scores = np.arange(100, dtype=float)          # 0..99, continuous-ish
    info = CT.compute_tau(scores, target_fpr=0.10)
    assert info["tau"] == pytest.approx(np.quantile(scores, 0.9))
    assert info["realised_fpr"] == pytest.approx(0.10, abs=0.02)
    assert info["tau_is_interior"] is True


def test_realised_fpr_uses_the_deployed_ge_convention():
    scores = np.array([0.0, 1.0, 2.0, 3.0])
    assert CT.realised_fpr(scores, 2.0, "ge") == pytest.approx(0.5)
    assert CT.realised_fpr(scores, 2.0, "gt") == pytest.approx(0.25)


def test_discrete_scores_make_the_nominal_fpr_unattainable():
    """The finding this script exists to surface: with a coarse score grid the quantile
    rule's realised FPR is nowhere near the nominal one, so the nominal must never be
    quoted. Ten items at three values: the 90th-percentile threshold flags 20%, not 10%."""
    scores = np.array([1.0] * 5 + [2.0] * 3 + [3.0] * 2)
    info = CT.compute_tau(scores, target_fpr=0.10)
    assert info["tau"] == pytest.approx(3.0)
    assert info["realised_fpr"] == pytest.approx(0.2)      # NOT 0.10
    assert info["n_distinct"] == 3


def test_atoms_collapse_last_bit_float_noise():
    """Real bug this guards: identical cluster partitions summed in a different order give
    entropies 1e-16 apart, which split one atom into two apparent thresholds. Real atoms on
    this score are ~0.05 nats apart, so collapsing at 1e-9 loses nothing."""
    v = 2.0253262207700673
    scores = [v, np.nextafter(v, 1.0), np.nextafter(v, 0.0), 1.5]
    assert CT.atoms(scores) == pytest.approx([1.5, np.nextafter(v, 0.0)])
    assert len(CT.attainable_grid(scores)) == 2


def test_a_candidate_exactly_at_tau_counts_despite_float_noise():
    """Without the tolerance a candidate one ULP below tau would be scored as not crossing
    even though it is the same attainable value."""
    tau = 2.1639556568820564
    assert CT.crosses(np.nextafter(tau, 0.0), tau, "ge") is True
    assert CT.crosses(tau, tau, "ge") is True
    assert CT.crosses(np.nextafter(tau, 1.0), tau, "gt") is False    # same atom, not above
    assert CT.crosses(tau + 0.05, tau, "gt") is True                 # a genuinely higher atom


def test_attainable_grid_and_smallest_threshold_at_most_fpr():
    scores = np.array([1.0] * 5 + [2.0] * 3 + [3.0] * 2)
    grid = CT.attainable_grid(scores)
    assert grid == [(1.0, 1.0), (2.0, 0.5), (3.0, 0.2)]
    assert CT.smallest_threshold_at_most_fpr(scores, 0.5) == pytest.approx(2.0)
    assert CT.smallest_threshold_at_most_fpr(scores, 0.01) is None   # unattainable -> None


def test_crossing_collapses_into_saturation_when_the_ceiling_is_the_only_flaggable_value():
    """The failure mode that voids the diagnostic: if nothing between tau and log(10) is
    attainable, 'crossed' just means 'saturated' and the censoring is back."""
    scores = np.array([1.0] * 6 + [2.0] * 2 + [CT.CAP] * 2)
    assert CT.crossing_is_saturation(scores, CT.CAP, "ge") is True
    assert CT.crossing_is_saturation(scores, 2.0, "gt") is True     # only the cap is above
    assert CT.crossing_is_saturation(scores, 2.0, "ge") is False    # 2.0 itself flags too
    assert CT.flagged_atoms(scores, 2.0, "ge") == pytest.approx([2.0, CT.CAP])


def test_tau_at_the_ceiling_is_flagged():
    """When the only <=target-FPR threshold is log(10), censoring-immunity is gone and the
    script must say so rather than proceed silently."""
    scores = np.array([1.0] * 8 + [CT.CAP] * 2)
    info = CT.compute_tau(scores, target_fpr=0.25)
    assert info["at_most_is_ceiling"] is True


def test_fair_pool_scores_come_from_the_shared_selection_rule(tmp_path):
    """tau must be built on the SAME score-independent id draw the campaign used, so the
    two cannot drift. Scores must be read only for `greedy_correct` items."""
    labels = [{"question_id": f"q{i}", "entropy_nats": float(i),
               "greedy_correct": (i % 2 == 0)} for i in range(20)]
    p = _write_jsonl(tmp_path / "relabeled.jsonl", labels)
    ids, scores = CT.fair_pool_clean_scores(p, n=5, seed=0, want="right")
    assert len(ids) == len(scores) == 5
    assert all(int(q[1:]) % 2 == 0 for q in ids)               # correct answers only
    assert [float(int(q[1:])) for q in ids] == list(scores)    # score follows the id
    from se.attacks.select import _stratum_ids, load_labels
    assert ids == _stratum_ids("right", 0, load_labels(p))[:5]  # identical to the campaign


# --------------------------------------------------------------------- crossing counts

def test_crossing_counts_on_a_known_fixture(fixture_rows):
    per = CT.crossing_counts(fixture_rows, tau=2.0, compare="ge")
    got = {t["question_id"]: (t["attack_crossed"], t["attack_n"]) for t in per}
    assert got == {"t1": (2, 3), "t2": (0, 2), "t3": (4, 4), "t4": (0, 0)}
    used = [t for t in per if t["attack_n"] > 0]
    assert sum(t["attack_crossed"] for t in used) == 6
    assert sum(t["attack_n"] for t in used) == 9


def test_crossing_rule_gt_excludes_the_boundary(fixture_rows):
    per = CT.crossing_counts(fixture_rows, tau=2.0, compare="gt")
    got = {t["question_id"]: t["attack_crossed"] for t in per}
    assert got["t1"] == 1        # 2.0 no longer counts, only 2.5
    assert got["t3"] == 4


def test_clean_already_flagged_is_reported(fixture_rows):
    per = CT.crossing_counts(fixture_rows, tau=1.55, compare="ge")
    flagged = {t["question_id"] for t in per if t["clean_already_flagged"]}
    assert flagged == {"t3"}     # entropy_before 1.6 >= 1.55


def test_ceiling_cannot_censor_the_count():
    """Three candidates pinned at the cap all count as crossings at an interior tau — the
    property the whole diagnostic rests on."""
    rows = [_row("s", 1.0, CT.CAP, [CT.CAP] * 3)]
    per = CT.crossing_counts(rows, tau=2.0, compare="ge")
    assert per[0]["attack_crossed"] == 3


# ------------------------------------------------------------------- empty feasible_objs

def test_empty_feasible_objs_are_dropped_by_default(fixture_rows):
    per = CT.crossing_counts(fixture_rows, tau=2.0, empty_policy="drop")
    t4 = next(t for t in per if t["question_id"] == "t4")
    assert t4["empty_feasible_objs"] is True
    assert (t4["attack_crossed"], t4["attack_n"]) == (0, 0)
    # and flip_test_conditional itself must drop the zero-size row
    ac, an, bc, bn = CT.assemble_arms(per, {"t1": (1, 10), "t2": (1, 10),
                                            "t3": (1, 10), "t4": (1, 10)})
    from se.stats import flip_test_conditional
    assert flip_test_conditional(ac, an, bc, bn)["n_targets"] == 3


def test_empty_feasible_objs_sensitivity_reenters_the_original_query(fixture_rows):
    per = CT.crossing_counts(fixture_rows, tau=2.0, empty_policy="original")
    t4 = next(t for t in per if t["question_id"] == "t4")
    assert (t4["attack_crossed"], t4["attack_n"]) == (0, 1)   # 1.2 does not cross
    assert t4["empty_feasible_objs"] is True                  # still labelled as empty
    per_hi = CT.crossing_counts([_row("t5", 2.4, 2.4, [])], tau=2.0, empty_policy="original")
    assert (per_hi[0]["attack_crossed"], per_hi[0]["attack_n"]) == (1, 1)


def test_unknown_empty_policy_raises(fixture_rows):
    with pytest.raises(ValueError):
        CT.crossing_counts(fixture_rows, tau=2.0, empty_policy="invent_one")


def test_below_clean_diagnostic_detects_a_censored_arm():
    """0 candidates below clean == the record-filter signature; a genuine sample shows some."""
    assert CT.n_candidates_below_clean([_row("a", 1.5, 2.0, [1.6, 1.8, 2.0])]) == 0
    assert CT.n_candidates_below_clean([_row("a", 1.5, 2.0, [1.1, 1.8, 2.0])]) == 1


# ----------------------------------------------------------------------- benign arm

def test_benign_moves_are_converted_to_absolute_scores(tmp_path):
    """null_control stores MOVES; for false_alarm move = after - before, so the absolute
    score is baseline + move. Getting this wrong would compare a delta against a level."""
    recs = [{"detector": "se", "attack": "false_alarm", "question_id": "t1",
             "baseline": {"nli": 1.0}, "benign": {"nli": [0.5, 1.2, 0.9]}}]
    p = _write_jsonl(tmp_path / "ckpt.jsonl", recs)
    out = CT.load_benign_crossings(p, tau=2.0, compare="ge")      # -> 1.5, 2.2, 1.9
    assert out == {"t1": (1, 3)}


def test_benign_reader_ignores_other_cells(tmp_path):
    recs = [{"attack": "hide", "question_id": "h1",
             "baseline": {"nli": 1.0}, "benign": {"nli": [1.5]}},
            {"attack": "false_alarm", "question_id": "t1",
             "baseline": {"nli": 1.0}, "benign": {"nli": [1.5]}}]
    p = _write_jsonl(tmp_path / "ckpt.jsonl", recs)
    assert set(CT.load_benign_crossings(p, tau=1.0)) == {"t1"}


def test_no_benign_arm_yields_no_test_rather_than_a_fake_one(fixture_rows):
    """With benign absent every row has m == 0, so the conditional test reports n_targets 0
    and a nan p-value. That is the required behaviour: no arm, no verdict."""
    from se.stats import flip_test_conditional
    per = CT.crossing_counts(fixture_rows, tau=2.0)
    res = flip_test_conditional(*CT.assemble_arms(per, None))
    assert res["n_targets"] == 0
    assert np.isnan(res["p_value"])


# ------------------------------------------------------------------ loud failure modes

def test_missing_attack_file_raises(tmp_path):
    with pytest.raises(CT.InputMissing):
        CT.load_attack_rows(tmp_path / "nope.jsonl")


def test_empty_attack_file_raises(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    with pytest.raises(CT.InputMissing):
        CT.load_attack_rows(p)


def test_uninstrumented_run_raises_rather_than_scoring_zero(tmp_path):
    """A pre-_defb run has no feasible_objs. Silently treating that as 'no crossings'
    would report a null result caused by missing instrumentation."""
    rows = [{"question_id": "t1", "attack": "false_alarm",
             "entropy_before": 1.0, "entropy_after": 2.0}]
    p = _write_jsonl(tmp_path / "old.jsonl", rows)
    with pytest.raises(CT.InputMissing, match="INSTRUMENTED"):
        CT.load_attack_rows(p)


def test_hide_cell_is_refused(tmp_path):
    """For hide the objective is -entropy; comparing it to an entropy tau inverts the test."""
    rows = [_row("t1", 2.0, 1.0, [-1.5, -1.2], attack="hide")]
    p = _write_jsonl(tmp_path / "hide.jsonl", rows)
    with pytest.raises(CT.InputMissing, match="false_alarm"):
        CT.load_attack_rows(p)


def test_missing_label_file_raises_instead_of_inventing_tau(tmp_path):
    with pytest.raises(CT.InputMissing):
        CT.fair_pool_clean_scores(tmp_path / "nope.jsonl")


def test_too_small_fair_pool_raises(tmp_path):
    labels = [{"question_id": f"q{i}", "entropy_nats": float(i), "greedy_correct": True}
              for i in range(3)]
    p = _write_jsonl(tmp_path / "relabeled.jsonl", labels)
    with pytest.raises(CT.InputMissing):
        CT.fair_pool_clean_scores(p, n=200)


def test_missing_benign_file_raises(tmp_path):
    with pytest.raises(CT.InputMissing):
        CT.load_benign_crossings(tmp_path / "nope.jsonl", tau=2.0)


def test_benign_file_with_no_usable_records_raises(tmp_path):
    p = _write_jsonl(tmp_path / "ckpt.jsonl",
                     [{"attack": "false_alarm", "question_id": "t1",
                       "baseline": {"nli": 1.0}, "benign": {"nli": []}}])
    with pytest.raises(CT.InputMissing):
        CT.load_benign_crossings(p, tau=2.0)


# ------------------------------------------------------------------------ end to end

def test_main_runs_and_declares_its_secondary_status(tmp_path, capsys):
    """The script must run on a self-contained fixture and must print, in its own output,
    that it is a disclosed secondary diagnostic and not the claim statistic."""
    rows = [_row("q0", 1.0, 2.5, [2.0, 2.5]), _row("q1", 1.2, 1.2, [])]
    ap = _write_jsonl(tmp_path / "attack.jsonl", rows)
    out = tmp_path / "res.json"
    assert CT.main(["--path", str(ap), "--tau", "2.0", "--json", str(out)]) == 0
    txt = capsys.readouterr().out
    assert "SECONDARY DIAGNOSTIC" in txt
    assert "NOT THE CLAIM STATISTIC" in txt
    assert "randomised-tie exceedance test" in txt
    assert "NOT AVAILABLE" in txt          # benign arm honestly reported absent
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["benign_available"] is False
    assert payload["n_empty_feasible_objs"] == 1
    assert payload["attack_crossings"] == 2
    assert payload["flip_test_conditional"]["n_targets"] == 0
