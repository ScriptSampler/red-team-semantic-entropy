"""Round-provenance bounds + the duplication H0-level simulator. CPU-only, no models."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rda = _load("round_drift_analysis")
dls = _load("duplication_level_sim")


# --------------------------------------------------------------------- first_max_round


def test_first_max_round_identifies_the_hop_count():
    assert rda.first_max_round([1.0, 1.0, 1.0]) == 0        # never improved
    assert rda.first_max_round([1.0, 1.5, 1.5]) == 1        # single-hop max
    assert rda.first_max_round([1.0, 1.2, 1.7, 1.7]) == 2   # multi-hop max
    assert rda.first_max_round([]) == 0


def test_counting_bound_arithmetic():
    # b=30 ties, max first set in round 1, 9 proposals/round -> >= 21 must be multi-hop
    assert rda.counting_bound(30, 1, 2) == 21
    assert rda.counting_bound(30, 1, 4) == 3
    assert rda.counting_bound(30, 1, 10) == 0
    # no tie member can predate the round that set the max, so if that round is >= 2
    # then EVERY tie member is multi-hop
    assert rda.counting_bound(30, 3, 2) == 30
    assert rda.counting_bound(30, 3, 4) == 21


# ------------------------------------------------------- the DP, against a faithful replay


def _replay(children_by_round, feasible, base):
    """Reproduce optimizer.optimize's bookkeeping exactly: `improved_children` filters on the
    round's ENTRY best, the feasibility loop appends every gate-passer to feasible_objs and
    raises the running best as it goes, and the trajectory records the best per round.
    Returns (traj, feasible_objs, true_round_of_each_entry)."""
    best = base
    traj = [base]
    objs, rounds = [], []
    for r, children in enumerate(children_by_round, start=1):
        entry_best = best
        for i, o in enumerate(children):
            if o < entry_best:
                continue
            if not feasible(r, i):
                continue
            objs.append(o)
            rounds.append(r)
            if o >= best:
                best = o
        traj.append(best)
    return traj, objs, rounds


def test_dp_is_a_valid_lower_bound_on_random_replays():
    rng = np.random.default_rng(7)
    for trial in range(30):
        base = 0.5
        n_rounds = 6
        children = [[float(np.round(rng.uniform(0.0, 2.3), 4)) for _ in range(9)]
                    for _ in range(n_rounds)]
        keep = rng.random((n_rounds + 1, 9)) < 0.6
        traj, objs, rounds = _replay(children, lambda r, i: bool(keep[r][i]), base)
        if not objs:
            continue
        t0 = max(1, rda.first_max_round(traj))
        for r_min in (2, 3, 5):
            got = rda.min_entries_from_round(objs, traj, r_min)
            truth = sum(1 for rr in rounds if rr >= r_min)
            assert got is not None, f"trial {trial}: no segmentation consistent with the replay"
            assert got <= truth, f"trial {trial}: DP bound {got} exceeds the truth {truth}"
            # and it is never LOOSER than the pure counting bound over the same entries
            assert got >= rda.counting_bound(len(objs), 1, r_min)


def test_dp_matches_the_truth_when_the_trajectory_pins_every_round():
    # strictly increasing trajectory with one feasible child per round -> unique segmentation
    children = [[0.1 * (r + 1) + 0.1] + [0.0] * 8 for r in range(5)]
    traj, objs, rounds = _replay(children, lambda r, i: i == 0, 0.05)
    assert objs == pytest.approx([0.2, 0.3, 0.4, 0.5, 0.6])
    for r_min in (1, 2, 3, 4, 5):
        assert rda.min_entries_from_round(objs, traj, r_min) == sum(1 for rr in rounds
                                                                    if rr >= r_min)


def test_dp_reports_none_when_no_segmentation_exists():
    # 10 entries all at the max but only one round of 9 proposals: impossible
    assert rda.min_entries_from_round([1.0] * 10, [1.0, 1.0], 1) is None
    # ...and possible with two rounds
    assert rda.min_entries_from_round([1.0] * 10, [1.0, 1.0, 1.0], 2) is not None


def test_dp_never_undercuts_the_counting_bound_on_a_plateau():
    """The case that matters on real data: the max is set in round 1 and then 40 candidates
    tie it, so at most 9 can be single-hop."""
    b = 40
    traj = [0.5] + [2.3026] * 20
    objs = [2.3026] * b
    got = rda.min_entries_from_round(objs, traj, 2, predicate=lambda v: True)
    assert rda.counting_bound(b, 1, 2) == 31
    assert got >= 31


# --------------------------------------------------------------- per-target / aggregate


def test_analyse_target_and_summarise():
    rec = {"question_id": "q1", "trajectory_best_obj": [0.5, 2.3026] + [2.3026] * 19,
           "feasible_objs": [2.3026] * 40, "n_feasible_at_best": 40, "improved": True}
    row = rda.analyse_target(rec)
    assert row["first_max_round"] == 1 and row["max_is_single_hop"]
    assert row["b_derived"] == 40 and row["b_matches_record"]
    assert row["saturated"]
    assert row["tie_min_multihop_count"] == 31
    assert row["tie_min_multihop_dp"] >= 31

    s = rda.summarise([row], m=50, A=181)
    assert s["expected_K_per_target"] == pytest.approx(50 / 182)
    assert s["band_lo"] == pytest.approx(0.5 * 50 / 182)
    assert s["band_hi"] == pytest.approx(2.0 * 50 / 182)
    assert s["frac_tie_mass_multihop_min"] >= 31 / 40
    # capping b at one round's worth of proposals would multiply the tie credit
    assert s["tie_credit_ratio"] == pytest.approx((1 / 10) / (1 / 41))


def test_summarise_separates_no_feasible_from_no_segmentation():
    empty = rda.analyse_target({"question_id": "q0", "trajectory_best_obj": [0.5] * 21,
                                "feasible_objs": [], "n_feasible_at_best": 0})
    s = rda.summarise([empty])
    assert s["n_no_feasible"] == 1
    assert s["dp_infeasible"] == 0        # never asked != inconsistent


# ------------------------------------------------------------------- duplication simulator


def test_multiplicities_conserve_the_call_count():
    rng = np.random.default_rng(0)
    for total, k in ((181, 73), (50, 6), (10, 40), (5, 5)):
        c = dls._multiplicities(total, k, rng)
        assert c.sum() == total
        assert len(c) == min(k, total)
        assert (c >= 1).all()


def test_arm_values_replicate_distinct_draws():
    rng = np.random.default_rng(0)
    v = dls._arm_values(181, 73, 0.0, math.log(10), rng)
    assert len(v) == 181
    assert len(set(np.round(v, 12))) <= 73        # at most `uniq` distinct values


def test_reference_cell_is_calibrated_and_duplication_inflates_kbar():
    """Both halves in one run to keep the suite fast. Under no duplication the deployed test
    sits at/below nominal and Kbar matches m/(A+1); heavy ATTACK duplication pushes Kbar up
    (conservative) — which is why a Kbar above the entry-23 band is not evidence of drift."""
    ref = dls.simulate_level(n_targets=20, trials=40, uniq_a=181, uniq_b=50, seed=3)
    assert ref["level"] <= 0.15
    assert ref["Kbar_ratio"] == pytest.approx(1.0, abs=0.25)
    dup = dls.simulate_level(n_targets=20, trials=40, uniq_a=40, uniq_b=6, seed=3)
    assert dup["Kbar_ratio"] > ref["Kbar_ratio"] * 1.5
    assert dup["level"] <= ref["level"] + 1e-9        # duplication of the ATTACK arm is conservative
