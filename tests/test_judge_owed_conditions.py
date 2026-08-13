"""Tests for scripts/judge_owed_conditions.py.

Everything here is synthetic or enumerative: no cache, no GPU, no WSL. The cache-reading
path is exercised by running the script, not by the suite, because the caches live inside
WSL and the suite runs on the Windows interpreter.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "judge_owed_conditions",
    Path(__file__).resolve().parents[1] / "scripts" / "judge_owed_conditions.py")
joc = importlib.util.module_from_spec(_SPEC)
sys.modules["judge_owed_conditions"] = joc
_SPEC.loader.exec_module(joc)


# ---------------------------------------------------------------------------
# A. the lattice
# ---------------------------------------------------------------------------
def test_partition_count_is_p10():
    assert len(list(joc.partitions_of(10))) == 42
    assert all(sum(p) == 10 for p in joc.partitions_of(10))
    assert all(list(p) == sorted(p, reverse=True) for p in joc.partitions_of(10))


def test_lattice_has_39_values_and_3_coincidences():
    """The paper's granularity claim (results/fair_pool_granularity.md) as a test."""
    lat = joc.build_k_lattice(10)
    assert len(lat) == 39
    coll = joc.lattice_collisions(lat)
    assert len(coll) == 3


def test_every_coincidence_is_ambiguous_by_exactly_one_cluster():
    """Load-bearing: it is why an ambiguous inversion still bounds K to within 1."""
    for _h, _parts, ks in joc.lattice_collisions(joc.build_k_lattice(10)):
        assert max(ks) - min(ks) == 1


def test_n20_lattice_matches_the_repo_s_own_455():
    """docs/START_HERE_overnight.md: N=20 gives 455 attainable values against 39 at N=10."""
    assert len(joc.build_k_lattice(20)) == 455


def test_inverter_round_trips_every_partition_of_10():
    lat = joc.build_k_lattice(10)
    for p in joc.partitions_of(10):
        cands = joc.invert_cluster_count(joc.entropy_of_counts(p), lat)
        assert cands is not None
        assert len(p) in cands
        assert len(cands) <= 2


def test_inverter_returns_none_off_lattice():
    lat = joc.build_k_lattice(10)
    # 0.5 nats is not attainable by any partition of 10.
    assert joc.invert_cluster_count(0.5, lat) is None


def test_entropy_matches_the_shipped_discrete_entropy():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from se.entropy import discrete_entropy
    for assignments in ([0] * 10,
                        list(range(10)),
                        [0, 0, 0, 0, 0, 1, 1, 2, 3, 4],
                        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]):
        counts = [assignments.count(c) for c in sorted(set(assignments))]
        assert joc.entropy_of_counts(counts) == pytest.approx(discrete_entropy(assignments))


def test_validate_inverter_counts_exact_ambiguous_and_mismatch():
    lat = joc.build_k_lattice(10)
    h_exact = joc.entropy_of_counts([5, 2, 1, 1, 1])        # K=5, unique
    h_amb = joc.entropy_of_counts([2, 2, 2, 2, 2])          # collides with (4,2,1,1,1,1)
    recs = [{"entropy_nats": h_exact, "n_clusters": 5},
            {"entropy_nats": h_exact, "n_clusters": 7},     # wrong -> mismatch
            {"entropy_nats": h_amb, "n_clusters": 5},       # in the candidate set
            {"entropy_nats": h_amb, "n_clusters": 9},       # not in it -> mismatch
            {"entropy_nats": 0.5, "n_clusters": 3}]         # off-lattice
    v = joc.validate_inverter(recs, lat)
    assert (v["n"], v["exact"], v["ambiguous"], v["mismatch"], v["off_lattice"]) == (5, 1, 1, 2, 1)


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def test_paired_bootstrap_is_deterministic_and_brackets_the_mean():
    d = [1, 2, 3, -1, 0, 2, 4, 1]
    a = joc.paired_bootstrap_ci(d, seed=7, n_boot=2000)
    b = joc.paired_bootstrap_ci(d, seed=7, n_boot=2000)
    assert a == b
    m, lo, hi = a
    assert m == pytest.approx(sum(d) / len(d))
    assert lo < m < hi


def test_paired_bootstrap_rejects_empty():
    with pytest.raises(ValueError):
        joc.paired_bootstrap_ci([])


def test_sign_test_known_values():
    assert joc.sign_test_p(5, 5) == pytest.approx(1.0)
    assert joc.sign_test_p(5, 0) == pytest.approx(2 * 0.5 ** 5)
    assert joc.sign_test_p(0, 0) == 1.0
    assert joc.sign_test_p(55, 2) < 1e-12          # the observed FA cell
    assert joc.sign_test_p(2, 55) == joc.sign_test_p(55, 2)


def test_noninferiority_verdict_truth_table():
    v = joc.noninferiority_verdict
    # interval wholly above zero -> refuted, whatever the margin
    assert v(0.02, 0.30, 0.16, margin=0.5) == "FAIL"
    # point estimate alone reaches the margin -> refuted even with a straddling CI
    assert v(-0.10, 1.20, 0.55, margin=0.5) == "FAIL"
    # interval rules out a differential as big as the margin -> certified
    assert v(-0.30, 0.20, -0.05, margin=0.5) == "PASS"
    # too wide to certify, not clear enough to refute -> the default
    assert v(-0.90, 0.90, 0.10, margin=0.5) == "INCONCLUSIVE"


def test_noninferiority_inconclusive_is_not_a_pass():
    """A wide interval centred on zero must NOT license the judge."""
    assert joc.noninferiority_verdict(-2.0, 2.0, 0.0, margin=0.53) == "INCONCLUSIVE"


def test_noninferiority_rejects_nonpositive_margin():
    for bad in (0.0, -0.1):
        with pytest.raises(ValueError):
            joc.noninferiority_verdict(-1.0, 1.0, 0.0, margin=bad)


# ---------------------------------------------------------------------------
# exposure and the (ii) inventory
# ---------------------------------------------------------------------------
def test_within_cluster_pairs():
    assert joc.within_cluster_pairs([0] * 10) == 45
    assert joc.within_cluster_pairs(list(range(10))) == 0
    assert joc.within_cluster_pairs([0, 0, 0, 1, 1, 2, 3, 4, 5, 6]) == 3 + 1


def test_oracle_pair_strata_partitions_all_pairs():
    for sc in ([True] * 10,
               [False] * 10,
               [True] * 5 + [False] * 5,
               [True, False, True, True, False, True, False, True, True, True]):
        s = joc.oracle_pair_strata(sc)
        assert s["total"] == math.comb(10, 2) == 45
        assert s["positive"] + s["hard_neg"] + s["unlabelled"] == 45
    assert joc.oracle_pair_strata([True] * 10)["positive"] == 45
    assert joc.oracle_pair_strata([False] * 10)["unlabelled"] == 45
    assert joc.oracle_pair_strata([True] * 5 + [False] * 5)["hard_neg"] == 25


def test_false_split_rate_only_scores_oracle_positive_pairs():
    sc = [True, True, True, False, False]
    # samples 0,1 merged; 2 alone -> of the 3 positive pairs, 1 merged and 2 split.
    assert joc.false_split_rate([0, 0, 1, 2, 3], sc) == (1, 2)
    # a clusterer that merges everything never false-splits.
    assert joc.false_split_rate([0] * 5, sc) == (3, 0)
    # no positive pairs -> nothing to score.
    assert joc.false_split_rate([0, 1, 2, 3, 4], [False] * 5) == (0, 0)


def test_wilson_ci_brackets_the_point_and_handles_the_ends():
    lo, hi = joc.wilson_ci(30, 100)
    assert lo < 0.30 < hi
    assert joc.wilson_ci(0, 0) == (0.0, 1.0)
    assert joc.wilson_ci(0, 50)[0] == 0.0
    assert joc.wilson_ci(50, 50)[1] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# the cost model
# ---------------------------------------------------------------------------
def test_prompts_per_clustering_is_the_symmetric_pair_count():
    assert joc.PROMPTS_PER_CLUSTERING == 90


def test_batch12_is_the_anchor_so_its_bracket_is_degenerate():
    a = joc.judge_clustering_seconds(12, regime="compute")
    b = joc.judge_clustering_seconds(12, regime="overhead")
    assert a == pytest.approx(b)
    assert a == pytest.approx(joc.SEC_PER_JUDGE_CLUSTERING_B12)


def test_halving_the_batch_can_only_cost_more_and_central_sits_between():
    lo = joc.judge_clustering_seconds(6, regime="compute")
    hi = joc.judge_clustering_seconds(6, regime="overhead")
    mid = joc.judge_clustering_seconds(6, regime="central")
    assert lo < mid < hi
    # 90 prompts: 8 chunks at 12, 15 chunks at 6.
    assert hi == pytest.approx(joc.SEC_PER_JUDGE_CLUSTERING_B12 * 15 / 8)


def test_gpu_cost_shape_and_monotonicity():
    c = joc.gpu_cost(80, batch_size=6)
    assert c["judge_clusterings"] == 160
    assert c["victim_sampling_passes"] == 80
    assert c["compute"] < c["central"] < c["overhead"]
    # the whole standalone run is small next to the ~67 GPU-h null control it queues behind
    assert c["overhead"] < 6.0
    assert joc.gpu_cost(80, batch_size=6)["central"] > joc.gpu_cost(80, batch_size=12)["central"]
    assert joc.gpu_cost(40, batch_size=6)["central"] < c["central"]


def test_skipping_regeneration_only_removes_the_victim_passes():
    with_gen = joc.gpu_cost(80, batch_size=6, regenerate_attacked=True)
    without = joc.gpu_cost(80, batch_size=6, regenerate_attacked=False)
    assert without["victim_sampling_passes"] == 0
    assert without["central"] < with_gen["central"]
    assert (with_gen["central"] - without["central"]) * 3600 == pytest.approx(
        80 * joc.SEC_PER_EVAL_CHEAP_ARMS)
