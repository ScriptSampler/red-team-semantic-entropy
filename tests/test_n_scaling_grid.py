"""The budget-scaling experiment, asserted as arithmetic and as machinery.

`scripts/n_scaling_grid.py` decides how a GPU-day is spent and then reports a grid that
the paper's central claim will be read against. Everything in it that does not need a GPU
is pinned here:

  1. THE LATTICE. The counts the plan quotes (39/455/14116 attainable values, 2/7/42 in
     the top tenth) are enumeration, and the last step of the scale is exactly 2 ln 2 / N
     -- a closed form the plan asserts and the paper is invited to quote.
  2. THE COUPLING. {all N distinct} is contained in {any k of them distinct}, per
     realisation, for a union-find-over-pairwise clusterer. This is the whole of "the
     floor cannot rise with N", and it is a containment, so it is checked as one -- on the
     project's REAL clusterer, not on a stand-in.
  3. THE REPLAY. The subset machinery is the reason one N=40 pass yields every smaller
     budget. If replaying the recorded verdicts does not reproduce the detector's own
     score, every derived budget in the report is fiction.
  4. THE COST MODEL. Quadratic in the sample count, monotone, and -- the claim the plan
     rests on -- N=40 costs MORE than four times N=10. Plus the rule that no hours figure
     may be printed without the n it assumed.
  5. THE LOOP. Checkpoint, resume, and tolerance of a torn line, driven with a fake
     scorer.
  6. THE GRID at N=20/40, including that the floor is the FIRST FIRING POINT and not the
     ceiling atom -- they coincide only while the atom is non-empty, and the report row
     read the atom under a "floor" header until N=40 emptied it -- and that averaging k
     runs cannot push the atom below the deterministic-saturation mass.
  7. THE REPORT'S OWN PROSE, where it carries a rule or a borrowed number. A decision rule
     that licenses retiring results, and a value copied out of another file, are both
     things that go stale silently in a generated document that reads as current.

CPU only: no GPU, no model, no sample cache, no network.
"""
from __future__ import annotations

import math
import re
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import n_scaling_grid as NS                                             # noqa: E402
from se.entropy import cluster_and_score, cluster_samples               # noqa: E402
from se.stats import attainable_fprs, operating_point                   # noqa: E402


# ============================================================== 1. the lattice
@pytest.mark.parametrize("n,size,top10", [(10, 39, 2), (20, 455, 7), (40, 14116, 42)])
def test_lattice_counts_the_plan_quotes(n, size, top10):
    st = NS.lattice_stats(n)
    assert st["size"] == size
    assert st["n_top10"] == top10


@pytest.mark.parametrize("n", [5, 10, 13, 20, 40])
def test_last_step_of_the_scale_is_exactly_two_ln2_over_N(n):
    """The highest attainable value below ln N is the partition (2,1,...,1), so the top
    gap is 2 ln 2 / N. The plan states this as a closed form; here it is against the
    enumeration."""
    st = NS.lattice_stats(n)
    assert st["top_gap"] == pytest.approx(2.0 * math.log(2) / n, rel=1e-12)
    assert st["top_gap_closed_form"] == pytest.approx(st["top_gap"], rel=1e-12)


def test_the_top_of_the_scale_is_where_the_lattice_stays_sparse():
    """The whole surviving granularity claim: the lattice explodes with N but the top
    tenth of the range does not keep up, and the last step shrinks only like 1/N."""
    s10, s20, s40 = (NS.lattice_stats(n) for n in (10, 20, 40))
    assert s40["size"] / s10["size"] > 300          # ~362x overall
    assert s40["n_top10"] / s10["n_top10"] < 25     # 21x in the top tenth
    assert s10["top_gap"] / s40["top_gap"] == pytest.approx(4.0)   # exactly 1/N


def test_9dp_rounding_is_safe_where_the_claims_live():
    """The N=10 report rounds to 9 dp before building the grid. At N=40 the lattice is
    dense enough that two attainable values DO merge at 9 dp -- the plan says so, and says
    none of them is in the top tenth. Both halves are asserted, because the second is what
    licenses reusing the same rounding rule at N=40."""
    assert NS.lattice_stats(10)["merged_at_9dp"] == 0
    assert NS.lattice_stats(20)["merged_at_9dp"] == 0
    assert NS.lattice_stats(40)["merged_at_9dp"] > 0
    for n in (10, 20, 40):
        st = NS.lattice_stats(n)
        assert st["merged_at_9dp_in_top10"] == 0
        assert st["min_gap_top10"] > 1e-6


def test_permitted_spacing_names_the_binding_constraint():
    """The free upper bound on grid quality. At N=10 the lattice binds (39 < 200
    negatives); by N=20 the sample size binds globally; the top tenth stays
    lattice-bound at every budget considered."""
    p10 = NS.permitted_fpr_spacing(10, 200)
    p20 = NS.permitted_fpr_spacing(20, 200)
    p40 = NS.permitted_fpr_spacing(40, 200)
    assert p10["binding_constraint"] == "lattice"
    assert p20["binding_constraint"] == "sample size"
    assert p40["binding_constraint"] == "sample size"
    for p in (p10, p20, p40):
        assert p["binding_constraint_top10"] == "lattice"
        assert p["finest_spacing"] == 1.0 / p["max_operating_points"]
    # ...and it does get better with N, which is the honest half of the story
    assert p40["finest_spacing_top10"] < p20["finest_spacing_top10"] \
        < p10["finest_spacing_top10"]


# ============================================================== 2. the coupling
def _relation_nli(equiv: set[frozenset]):
    """A fake NLI answering from an explicit pairwise relation, over index sentinels."""
    class R:
        def bidirectional_equivalent_batch(self, pairs, batch_size=64):
            return [frozenset((NS._sentinel_index(a), NS._sentinel_index(b))) in equiv
                    for a, b in pairs]
    return R()


def test_all_N_distinct_is_contained_in_all_k_distinct_on_the_real_clusterer():
    """The coupling bound, per realisation, through `se.entropy.cluster_samples` itself.

    Not a proxy: a random symmetric relation is fed to the project's own union-find, and
    the containment is checked for every subset size. If this ever fails, "raising N can
    only lower the floor" is false and the plan's section 4 must be withdrawn."""
    rng = np.random.default_rng(0)
    n = 12
    for _ in range(200):
        equiv = {frozenset((i, j)) for i, j in combinations(range(n), 2)
                 if rng.random() < 0.12}
        nli = _relation_nli(equiv)
        full = cluster_samples([NS._sentinel(i) for i in range(n)], nli)
        all_distinct_full = len(set(full)) == n
        for k in (2, 4, 6, 9):
            idx = sorted(rng.permutation(n)[:k].tolist())
            sub_equiv = {frozenset((a, b)) for a, b in combinations(range(k), 2)
                         if frozenset((idx[a], idx[b])) in equiv}
            sub = cluster_samples([NS._sentinel(i) for i in range(k)],
                                  _relation_nli(sub_equiv))
            all_distinct_sub = len(set(sub)) == k
            assert not (all_distinct_full and not all_distinct_sub), \
                "a subset of an all-distinct set was not all-distinct"


def test_saturation_rate_is_non_increasing_in_the_budget():
    """The marginal consequence: P(saturate at N) is non-increasing in N."""
    rng = np.random.default_rng(1)
    rates = {}
    for k in (5, 10, 20, 40):
        hits = 0
        for _ in range(600):
            p = rng.dirichlet(np.full(25, 0.5))
            hits += len(set(rng.choice(len(p), size=k, p=p).tolist())) == k
        rates[k] = hits / 600
    assert rates[5] >= rates[10] >= rates[20] >= rates[40]


def test_transversal_probability_is_a_lower_bound_and_exact_at_k_equals_n():
    """`esp_transversal_prob` is the induced-partition event, which the plan uses for its
    free prediction and labels a LOWER bound. Both properties are checked: it agrees with
    brute force over all subsets, and at k=n it is exactly the all-distinct indicator."""
    for sizes in ([1] * 6, [3, 2, 1], [4, 4, 2], [2, 2, 2, 2, 2]):
        n = sum(sizes)
        cluster_of = [c for c, s in enumerate(sizes) for _ in range(s)]
        for k in range(1, len(sizes) + 1):
            brute = sum(1 for sub in combinations(range(n), k)
                        if len({cluster_of[i] for i in sub}) == k)
            assert NS.esp_transversal_prob(sizes, k) == pytest.approx(
                brute / math.comb(n, k))
        assert NS.esp_transversal_prob(sizes, n) == pytest.approx(
            1.0 if len(sizes) == n else 0.0)
        # monotone non-increasing in k, which is what makes it a decay curve
        vals = [NS.esp_transversal_prob(sizes, k) for k in range(1, len(sizes) + 1)]
        assert all(a >= b - 1e-12 for a, b in zip(vals, vals[1:]))


def test_transversal_bound_never_exceeds_the_true_subset_ceiling_probability():
    """The direction of the bound, on real verdict matrices: counting transversals of the
    FULL clustering can only under-count the subsets that are genuinely all-singletons."""
    rng = np.random.default_rng(4)
    n = 9
    for _ in range(60):
        bits = "".join("1" if rng.random() < 0.15 else "0"
                       for _ in range(math.comb(n, 2)))
        cs = cluster_and_score([NS._sentinel(i) for i in range(n)], NS.ReplayNLI(bits, n))
        from collections import Counter
        sizes = sorted(Counter(cs.assignments).values(), reverse=True)
        for k in (2, 3, 4):
            lower = NS.esp_transversal_prob(sizes, k)
            truth = NS.subset_ceiling_prob(bits, n, k, rng, n_mc=10_000)
            assert lower <= truth + 1e-9


# ================================================================ 3. the replay
def test_replaying_the_full_verdict_matrix_reproduces_the_detectors_own_score():
    """The load-bearing assumption of the whole design. If this fails, no budget below the
    one actually run may be reported."""
    rng = np.random.default_rng(2)
    for n in (6, 10, 20):
        for _ in range(20):
            latent = rng.integers(0, 4, size=n).tolist()
            equiv = {frozenset((i, j)) for i, j in combinations(range(n), 2)
                     if latent[i] == latent[j]}
            direct = cluster_and_score([NS._sentinel(i) for i in range(n)],
                                       _relation_nli(equiv))
            bits = NS.verdict_bits([frozenset((i, j)) in equiv
                                    for i, j in combinations(range(n), 2)])
            replayed = NS.score_subset(bits, n, list(range(n)))
            assert replayed.entropy_nats == direct.entropy_nats
            assert replayed.n_clusters == direct.n_clusters


def test_subset_replay_equals_clustering_that_subset_from_scratch():
    """A subset's score must be what the detector would have produced from those samples
    alone -- including when a merge in the full set travelled through an excluded sample,
    which is exactly the case that makes a subset FINER than the restriction."""
    rng = np.random.default_rng(3)
    n = 10
    for _ in range(80):
        equiv = {frozenset((i, j)) for i, j in combinations(range(n), 2)
                 if rng.random() < 0.2}
        bits = NS.verdict_bits([frozenset((i, j)) in equiv
                                for i, j in combinations(range(n), 2)])
        idx = sorted(rng.permutation(n)[:5].tolist())
        sub_equiv = {frozenset((a, b)) for a, b in combinations(range(5), 2)
                     if frozenset((idx[a], idx[b])) in equiv}
        expect = cluster_and_score([NS._sentinel(i) for i in range(5)],
                                   _relation_nli(sub_equiv))
        got = NS.score_subset(bits, n, idx)
        assert got.entropy_nats == expect.entropy_nats
        assert got.n_clusters == expect.n_clusters


def test_replay_refuses_a_verdict_string_of_the_wrong_length():
    with pytest.raises(ValueError):
        NS.ReplayNLI("0" * 10, 10)                 # C(10,2) = 45, not 10


def test_the_gpu_scorer_records_a_replayable_matrix_for_the_score_it_returns(monkeypatch):
    """The GPU path itself, with the two models faked out.

    This is the one seam that could fail silently after hours of GPU: `semantic_entropy`
    is called for the score while a proxy records the NLI verdicts, and the two must
    describe the same clustering. Everything below the fake generator is the project's
    real code -- `se.se_pipeline.semantic_entropy`, `se.entropy.cluster_and_score`,
    `se.entropy.cluster_samples`."""
    import se.attacks.harness as H
    import se.model as M
    import se.se_pipeline as SP

    n = 12
    latent = [0, 0, 1, 2, 2, 2, 3, 4, 5, 6, 7, 7]
    texts = [f"answer-{m}" for m in latent]

    class FakeNLI:
        def bidirectional_equivalent_batch(self, pairs, batch_size=64):
            return [a == b for a, b in pairs]

    class FakePair:
        lm = object()
        nli = FakeNLI()

    monkeypatch.setattr(H, "load_pair", lambda *a, **k: FakePair())
    monkeypatch.setattr(M, "generate_samples", lambda lm, q, cfg: list(texts))
    monkeypatch.setattr(SP.M, "generate_samples", lambda lm, q, cfg: list(texts))

    out = NS.make_gpu_scorer()("a question?", n, 0)
    assert len(out.bits) == math.comb(n, 2)
    assert out.n_clusters == len(set(latent))
    assert out.seconds_total >= 0.0 and out.seconds_nli >= 0.0
    replay = NS.score_subset(out.bits, n, list(range(n)))
    assert replay.entropy_nats == pytest.approx(out.entropy_nats), \
        "the recorded verdicts do not reproduce the score they were recorded alongside"
    assert replay.n_clusters == out.n_clusters


def test_the_clusterer_still_asks_for_pairs_in_combinations_order():
    """The recorder zips the returned verdicts against `combinations(range(n), 2)`. That
    is an assumption about `se.entropy.cluster_samples`, so it is pinned here rather than
    trusted: if the pair order ever changes, every stored verdict matrix silently becomes
    a permutation of itself."""
    seen = []

    class Recorder:
        def bidirectional_equivalent_batch(self, pairs, batch_size=64):
            seen.extend(pairs)
            return [False] * len(pairs)

    n = 7
    cluster_samples([NS._sentinel(i) for i in range(n)], Recorder())
    assert [(NS._sentinel_index(a), NS._sentinel_index(b)) for a, b in seen] == \
        list(combinations(range(n), 2))


# ============================================================= 4. the cost model
def test_nli_term_is_exactly_quadratic_and_N40_is_not_four_times_N10():
    """The claim the buy rests on: clustering scores every pair in both directions, so the
    NLI term is N(N-1) and N=40 costs strictly more than 4x N=10."""
    assert NS.nli_passes(10) == 90 and NS.nli_passes(20) == 380
    assert NS.nli_passes(40) == 1560
    assert NS.t_nli(40) / NS.t_nli(10) == pytest.approx(1560 / 90)
    assert NS.t_eval(40) > 4.0 * NS.t_eval(10)
    assert NS.t_eval(20) > 2.0 * NS.t_eval(10)


@pytest.mark.parametrize("scenario", NS.SCENARIOS)
def test_every_scenario_agrees_at_the_anchor_and_is_monotone(scenario):
    assert NS.t_eval(10, scenario) == pytest.approx(NS.t_eval(10), rel=1e-12)
    vals = [NS.t_eval(n, scenario) for n in (5, 10, 20, 40, 80)]
    assert all(a < b for a, b in zip(vals, vals[1:]))


def test_the_bracket_actually_brackets_the_central_estimate():
    for n in (20, 40, 80):
        assert (NS.t_eval(n, "amortised") <= NS.t_eval(n, "linear")
                <= NS.t_eval(n, "loaded"))


def test_no_hours_figure_may_be_printed_without_its_n():
    """A sibling script's cost figure went stale three times in one session because the
    hours were quoted without the n. Every line this module emits with "GPU-h" in it must
    carry an "n=" too -- asserted over the whole --estimate-only output, not just over
    `cost_line`."""
    assert "n=" in NS.cost_line("x", 200, 7200.0)

    lines: list[str] = []

    class A:                                    # the argparse namespace estimate_only uses
        budgets = [10, 20, 40]
        n_per_stratum = 200
        strata = "both"
        checkpoint = str(REPO / "results" / "does_not_exist_n_scaling.jsonl")

    NS.cost_section(lines.append, A.budgets, A.n_per_stratum, True, None)
    hours_lines = [ln for ln in lines if "GPU-h" in ln]
    assert hours_lines, "the cost section printed no hours at all"
    for ln in hours_lines:
        assert "n=" in ln, f"hours without an n: {ln!r}"


def test_measured_throughput_reads_the_checkpoint_back():
    recs = [{"n_samples": 40, "seconds_total": 70.0, "seconds_nli": 30.0},
            {"n_samples": 40, "seconds_total": 80.0, "seconds_nli": 32.0},
            {"n_samples": 20, "seconds_total": 30.0, "seconds_nli": 7.0}]
    m = NS.measured_throughput(recs)
    assert m[40]["n_evals"] == 2 and m[40]["s_total"] == pytest.approx(75.0)
    assert m[20]["s_nli"] == pytest.approx(7.0)


# =================================================================== 5. the loop
def _targets(k: int):
    return [("correct", f"q{i}", f"question {i}?") for i in range(k)]


def test_checkpoint_resume_does_no_work_twice(tmp_path):
    ck = tmp_path / "ck.jsonl"
    calls = {"n": 0}
    base = NS.make_fake_scorer()

    def counting(question, n_samples, seed):
        calls["n"] += 1
        return base(question, n_samples, seed)

    first = NS.run_measurement(_targets(6), 12, 0, ck, counting, log=lambda *_: None)
    assert calls["n"] == 6 and len(first) == 6

    again = NS.run_measurement(_targets(6), 12, 0, ck, counting, log=lambda *_: None)
    assert calls["n"] == 6, "a completed target was re-scored on resume"
    assert len(again) == 6
    assert ({r["entropy_nats"] for r in first} == {r["entropy_nats"] for r in again})

    # a different budget is different work, not a resume
    NS.run_measurement(_targets(6), 8, 0, ck, counting, log=lambda *_: None)
    assert calls["n"] == 12


def test_a_torn_final_line_does_not_lose_the_run(tmp_path):
    """The machine is shared and the process can be killed mid-write."""
    ck = tmp_path / "ck.jsonl"
    NS.run_measurement(_targets(4), 10, 0, ck, NS.make_fake_scorer(), log=lambda *_: None)
    with ck.open("a", encoding="utf-8") as f:
        f.write('{"question_id": "q9", "n_samp')          # killed mid-write
    recs = NS._read_jsonl(ck)
    assert len(recs) == 4
    calls = {"n": 0}
    base = NS.make_fake_scorer()

    def counting(q, n, s):
        calls["n"] += 1
        return base(q, n, s)

    NS.run_measurement(_targets(4), 10, 0, ck, counting, log=lambda *_: None)
    assert calls["n"] == 0


def test_fake_scored_records_are_labelled_so_a_later_report_cannot_launder_them(tmp_path):
    """`--report-only` runs long after the run and has only the checkpoint to go on. If the
    checkpoint does not say the scorer was fake, a smoke run's numbers land in
    results/n_scaling_grid.md under the real filename."""
    ck = tmp_path / "ck.jsonl"
    NS.run_measurement(_targets(3), 10, 0, ck, NS.make_fake_scorer(),
                       log=lambda *_: None, scorer="fake")
    assert all(r["scorer"] == "fake" for r in NS._read_jsonl(ck))
    NS.run_measurement(_targets(3), 12, 0, ck, NS.make_fake_scorer(), log=lambda *_: None)
    assert {r["scorer"] for r in NS._read_jsonl(ck)} == {"fake", "gpu"}


def test_records_carry_everything_a_later_budget_question_needs(tmp_path):
    ck = tmp_path / "ck.jsonl"
    NS.run_measurement(_targets(3), 16, 0, ck, NS.make_fake_scorer(), log=lambda *_: None)
    for r in NS._read_jsonl(ck):
        assert len(r["verdict_bits"]) == math.comb(16, 2)
        assert r["seconds_total"] > 0 and "seconds_nli" in r
        assert r["max_new_tokens"] == NS.MAX_NEW_TOKENS
        # the stored score is reproducible from the stored verdicts, forever
        assert NS.score_subset(r["verdict_bits"], 16, list(range(16))).entropy_nats == \
            pytest.approx(r["entropy_nats"])


def test_budget_scores_are_deterministic_across_processes(tmp_path):
    """Subset draws are seeded from a STABLE hash. `hash()` on a str is salted per
    interpreter, so using it would make every replayed grid unreproducible."""
    ck = tmp_path / "ck.jsonl"
    recs = NS.run_measurement(_targets(5), 20, 0, ck, NS.make_fake_scorer(),
                              log=lambda *_: None)
    a = NS.budget_scores(recs, 8, "correct", replicate=0)
    b = NS.budget_scores(recs, 8, "correct", replicate=0)
    c = NS.budget_scores(recs, 8, "correct", replicate=1)
    assert a == b
    assert a != c or len(a) == 0
    assert NS._stable_hash("dpql_1059") == NS._stable_hash("dpql_1059")
    # scoring AT the recorded budget returns the measured number untouched
    at_n = NS.budget_scores(recs, 20, "correct")
    assert at_n == {r["question_id"]: r["entropy_nats"] for r in recs}


# ==================================================== 6. the grid at larger budgets
def _atomic(n_neg: int, k_at_cap: int, budget: int, rng):
    cap = math.log(budget)
    lat = [v for v in NS.lattice(budget) if v < cap - 1e-9]
    body = rng.choice(lat, size=n_neg - k_at_cap)
    return np.round(np.concatenate([np.full(k_at_cap, cap), body]), NS.DP)


@pytest.mark.parametrize("budget,k", [(20, 8), (40, 3), (20, 1), (40, 19)])
def test_the_floor_is_the_ceiling_atom_WHILE_THE_ATOM_IS_NON_EMPTY(budget, k):
    """Note the scope in the name: every case here has k >= 1 at the cap. The identity
    holds only there, and reading this test as "the floor IS the atom" unqualified is
    what put the atom in the floor column of the report. See the k=0 test below."""
    rng = np.random.default_rng(budget + k)
    neg = _atomic(200, k, budget, rng)
    vals, fprs = attainable_fprs(neg)
    assert min(f for f in fprs if f > 0) == pytest.approx(k / 200)
    assert NS.ceiling_atom(neg, budget) == (k, 200)
    op = operating_point(np.zeros(200, int), neg, target_fpr=k / 200 / 2, mode="at_most")
    assert op.flags_nothing, "a budget below the atom must not be honoured by firing"


def test_an_empty_ceiling_atom_does_not_mean_a_zero_floor():
    """REGRESSION. The published N=40 row read "0/200 = 0.0% [0.0%, 1.9%]" under a header
    saying "floor = min non-zero FPR", because the cell was filled with `ceiling_atom`.
    At N=10 and N=20 some negative sits at the cap, so the atom and the floor coincide and
    the row was right by coincidence; at N=40 the atom is empty and the real floor is the
    largest score strictly below ln 40. Zero in the floor column reads as "a sub-1%
    operating point may exist", and none does."""
    rng = np.random.default_rng(40)
    neg = _atomic(200, 0, 40, rng)                    # nothing at the cap
    rows = NS.grid_for(neg, np.array([math.log(40)]))
    firing = [r for r in rows if r["fires"]]

    assert NS.ceiling_atom(neg, 40) == (0, 200), "this fixture must have an empty atom"
    assert firing, "an empty atom must still leave firing thresholds"
    assert firing[0]["fpr"] > 0, "the floor is a NON-ZERO achievable rate"
    assert firing[0]["k_fp"] >= 1

    c = NS.floor_cells(neg, rows, 40)
    assert c["at_cap_k"] == 0
    assert c["floor_k"] == firing[0]["k_fp"]
    assert c["floor_fpr"] == pytest.approx(firing[0]["fpr"])
    assert c["floor"] != c["at_cap"], "the floor cell must not be the at-cap cell"
    assert not c["floor"].startswith("0/200"), "the atom leaked back into the floor column"
    assert c["atom_is_empty_so_floor_differs"]


@pytest.mark.parametrize("budget,k", [(20, 8), (40, 3), (40, 0), (20, 0)])
def test_the_floor_cell_is_always_the_first_firing_point(budget, k):
    """The invariant the report row depends on, atom or no atom: the floor cell is the
    first firing point, the next cell is the second, and the at-cap cell is the atom."""
    rng = np.random.default_rng(1000 + budget + k)
    neg = _atomic(200, k, budget, rng)
    rows = NS.grid_for(neg, np.array([math.log(budget)]))
    firing = [r for r in rows if r["fires"]]
    c = NS.floor_cells(neg, rows, budget)

    # The COUNT and the RATE are the invariant; whether an interval rides along with them
    # is decided separately, by the atom -- see the test below.
    assert c["floor"].startswith(f"{firing[0]['k_fp']}/200 = {firing[0]['fpr']:.1%}")
    assert c["at_cap"] == NS.fmt_prop(k, 200)
    assert c["next"] == f"{firing[1]['fpr']:.1%}"
    # the floor can never be below the atom, and equals it exactly when the atom is there
    assert c["floor_k"] >= k
    assert (c["floor_k"] == k) == (k > 0)


@pytest.mark.parametrize("budget,k", [(20, 8), (40, 3), (40, 0), (20, 0)])
def test_the_floor_carries_an_interval_only_while_the_ceiling_atom_has_mass(budget, k):
    """The 2026-08-19 ruling, as an executable rule rather than a note.

    While the atom carries mass the floor IS the atom: a binomial proportion at ln N, a
    threshold fixed before the data, and Wilson prices it. Once the atom empties, the
    threshold becomes the top score this pool happened to reach, and whether THAT is the
    top of the population's support is not determinable at n=200: if it is not, a larger
    pool reaches a higher rung and reports a smaller floor; if it is, the floor is an
    ordinary population proportion. The estimand is therefore NOT IDENTIFIED, and that is
    why the cell must print no interval (`results/n40_floor_estimator_ruling.md` sec. 13).

    This docstring previously gave the first branch as the unconditional reason and cited
    "53.7% Wilson / 0.00% bootstrap" as measured coverage full stop. Both are properties
    of the calibrated Ewens population; under the zero branch the same simulation gives
    95.06% and 100% (ruling sec. 8.4). The assertions below never depended on either
    figure -- they check the presence and absence of an interval, which the ruling leaves
    unchanged -- so only the rationale moved.

    Both directions are asserted: an interval must appear when k > 0 and must NOT appear
    when k == 0. A one-directional version of this test would pass on a cell that never
    printed an interval at all."""
    rng = np.random.default_rng(1000 + budget + k)
    neg = _atomic(200, k, budget, rng)
    rows = NS.grid_for(neg, np.array([math.log(budget)]))
    c = NS.floor_cells(neg, rows, budget)

    atom_empty = (k == 0)
    assert c["atom_is_empty_so_floor_differs"] is atom_empty
    if atom_empty:
        assert "[" not in c["floor"], (
            f"the floor cell {c['floor']!r} carries an interval with an EMPTY ceiling "
            "atom. Both candidates were withdrawn on measured coverage; see "
            "results/n40_floor_estimator_ruling.md.")
        assert "no interval" in c["floor"], c["floor"]
    else:
        assert c["floor"] == NS.fmt_prop(c["floor_k"], 200), (
            "with a non-empty atom the floor is a count at a threshold fixed in advance "
            "and keeps its Wilson interval.")
    # The at-cap cell keeps its interval either way: ln N is fixed a priori.
    assert "[" in c["at_cap"]


def test_a_denser_lattice_alone_does_not_make_the_grid_fine():
    """The point the plan makes about what the measurement can and cannot conclude: at
    N=40 the lattice has 14116 values, but if the population is piled on the cap the
    achievable grid is still 0 -> 22% -> ... . Coarseness at N=40 is a fact about the
    model, not about the estimator."""
    rng = np.random.default_rng(9)
    neg = _atomic(200, 44, 40, rng)
    rows = NS.grid_for(neg, np.array([math.log(40)]))
    from achievable_fpr_grid import n_firing_below
    assert n_firing_below(rows, 0.05) == 0
    assert n_firing_below(rows, 0.10) == 0
    assert [r for r in rows if r["fires"]][0]["fpr"] == pytest.approx(0.22)


def test_realised_scores_at_every_budget_lie_on_that_budgets_lattice():
    """A cheap guard that the run is scoring at the budget it thinks it is: a score off
    the lattice means the sample count is not what the report says."""
    for budget in (8, 12, 20):
        lat = {round(v, NS.DP) for v in NS.lattice(budget)}
        rng = np.random.default_rng(budget)
        scorer = NS.make_fake_scorer()
        for i in range(15):
            out = scorer(f"q{i}", budget, 0)
            assert round(out.entropy_nats, NS.DP) in lat


def test_averaging_k_subdivides_the_top_step_but_cannot_dissolve_a_hard_atom():
    """The reviewer's alternative, checked in both directions.

    Up: the mean of k scores has a finer top step, by exactly a factor of k.
    Down: the averaged score is at the cap iff every run saturates, so the residual atom
    is E[p^k] -- which is >= (E p)^k by Jensen and, crucially, never falls below the mass
    of questions that saturate deterministically."""
    comp = NS.averaging_comparison(10, (2, 4))
    for c in comp:
        assert c["top_step_nats"] == pytest.approx(2 * math.log(2) / (10 * c["k"]))
        assert c["cost_averaging_s"] < c["cost_single_run_s"], \
            "averaging must be the cheaper way to buy the same top-of-scale resolution"
        assert c["cap_averaging"] == pytest.approx(math.log(10))
        assert c["cap_single_run"] > c["cap_averaging"]

    # the hard floor: a population in which exactly 6% of questions saturate EVERY time
    # and the rest saturate with probability 0.3 -- averaging cannot get the atom below
    # 6%, however many runs are averaged.
    p = np.concatenate([np.full(600, 1.0), np.full(9400, 0.3)])
    for k in (1, 2, 4, 16):
        atom = float(np.mean(p ** k))
        assert atom >= 0.06 - 1e-12
        assert atom >= float(np.mean(p)) ** k - 1e-12          # Jensen
    assert float(np.mean(p ** 64)) == pytest.approx(0.06, abs=1e-6)


def test_averaging_lattice_is_finer_than_the_single_budget_lattice():
    assert NS.averaging_lattice_size(10, 1) == len(NS.lattice(10))
    assert NS.averaging_lattice_size(10, 2) > 10 * len(NS.lattice(10))
    assert NS.averaging_lattice_size(10, 5) is None      # refuses to enumerate 1e6 combos


def test_beta_binomial_prediction_is_monotone_and_bounded_by_the_coupling():
    """The plan's model-based extrapolation must obey the model-free bound it is printed
    next to: the predicted atom can only fall with N, and never above the N=10 value."""
    sizes = [[1] * 10, [2, 1, 1, 1, 1, 1, 1, 1], [5, 5], [3, 3, 2, 1, 1]]
    preds = [NS._beta_binomial_predictive(sizes, N) for N in (10, 20, 40, 80)]
    assert all(a >= b for a, b in zip(preds, preds[1:]))
    assert preds[0] <= 1.0 and preds[-1] >= 0.0


# ========================================================== the report's prose and pointers
# `results/n_scaling_grid.md` is generated, so it reads as current no matter how old its
# reasoning is. Two things in it are therefore pinned here: the decision rule it used to
# carry, and the one number in it that is copied from another file rather than computed.
RC = REPO / "results" / "replay_control.md"
GRID_MD = REPO / "results" / "n_scaling_grid.md"

RETIRED_RULE = "no replayed budget in this report may be quoted"
RETIREMENT_MARKERS = ("WITHDRAWN", "used to close", "That rule is")


def _paragraphs(text: str) -> list[str]:
    return text.split("\n\n")


@pytest.mark.skipif(not GRID_MD.exists(), reason="report not generated in this tree")
def test_the_retired_subsetting_gate_never_reads_as_a_live_rule():
    """REGRESSION. The subsetting control used to close with: if the direct and replayed
    arms disagree beyond the Wilson interval, the subsetting is unsound and no replayed
    budget may be quoted. `results/replay_control.md` section 1 refutes the inference --
    the replicates are not coin flips about the direct value, so 20-of-20 on one side is a
    probability of a few tenths and not 2^-20.

    The rule may still be QUOTED, because a correction has to say what it corrects. What it
    may not do is stand unmarked. So the test is not "the string is absent" -- that would
    forbid the retraction along with the claim -- but "wherever the string appears, its
    own paragraph marks it as retired", which is the same window rule
    `test_operational_provenance.py` arrived at for the paper's dead cost anchors."""
    text = GRID_MD.read_text(encoding="utf-8")
    hits = [p for p in _paragraphs(text) if RETIRED_RULE in p]
    for p in hits:
        assert any(m in p for m in RETIREMENT_MARKERS), (
            "the retired subsetting gate appears in a paragraph that does not mark it "
            f"as retired, so it reads as the report's live rule:\n\n{p}")


@pytest.mark.skipif(not GRID_MD.exists(), reason="report not generated in this tree")
def test_the_report_carries_the_correct_account_and_points_at_the_control():
    """The replacement has to say the three things that make the retraction load-bearing,
    and it has to name the file that derives them -- grep returned zero cross-references
    between these two reports in either direction when the rule was found still standing."""
    text = GRID_MD.read_text(encoding="utf-8")
    assert "results/replay_control.md" in text, "the report must name the replay control"
    low = text.lower()
    assert "exchangeab" in low, "the unbiasedness argument is the exchangeability one"
    assert "union-find" in low, "unbiasedness needs the subset-clustering step, not just i.i.d."
    assert "correlates the replicates" in low or "correlated" in low
    assert "different parameters" in low, (
        "the two arms are unbiased for DIFFERENT generation runs; without that sentence "
        "the reader is left to decide which arm is the odd one out")


@pytest.mark.skipif(not RC.exists(), reason="replay control not generated in this tree")
def test_the_quoted_subset_averaged_floor_still_matches_replay_control():
    """The report prints the subset-averaged floor -- the number the PAPER quotes -- but
    does not compute it; `scripts/replay_control.py` owns it, and a second implementation
    of a printed number is how two files come to disagree unnoticed. So the copy is pinned
    to the source. If this fails, `results/replay_control.md` has moved and
    `NS.SUBSET_AVERAGED_FLOOR` is now a retired number sitting in a current-looking report:
    fix the constant, and check `paper/sections/discussion.tex` for the same value."""
    rows = dict(
        (int(m.group(1)), (m.group(2), m.group(3)))
        for m in re.finditer(
            r"^\|\s*replay N=(\d+)\s*\|\s*([\d.]+%)\s*\|\s*(\[[^\]]*\])\s*\|",
            RC.read_text(encoding="utf-8"), re.M)
    )
    assert rows, "no `replay N=<k>` floor row found in results/replay_control.md"
    for budget, quoted in NS.SUBSET_AVERAGED_FLOOR.items():
        assert budget in rows, (
            f"N={budget} is quoted in the grid report but no longer tabulated in "
            f"{RC.name}; the report is quoting a number its source has dropped")
        assert rows[budget] == quoted, (
            f"N={budget}: the grid report quotes {quoted} but {RC.name} now says "
            f"{rows[budget]}. The generated report is not the authority -- fix "
            f"NS.SUBSET_AVERAGED_FLOOR, then check paper/sections/discussion.tex")
