"""CPU-only logic tests for the paraphrase-averaging defense (src/se/defense.py).

No real models. The aggregation and variant-selection logic is pure and is
checked against hand-computable fixtures; the composed `defended_entropy` is
exercised with fakes standing in for Llama, DeBERTa and the SE pipeline, in the
same style as tests/test_attacks_logic.py. Run:

    .venv\\Scripts\\python.exe -m pytest tests/test_defense.py -q

This module was the only one under src/se with zero coverage while being cited
in the paper (Methods "Transfer and defense", Introduction contribution 5).
"""
from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se import defense as D
from se.defense import (
    AGGREGATES,
    DefendedResult,
    aggregate_entropy,
    defended_entropy,
    select_variants,
)


# ---- aggregate_entropy: hand-computable fixtures ---------------------------

def test_median_odd_count_is_the_middle_value():
    # sorted: 0.1, 0.4, 0.9 -> middle is 0.4
    assert aggregate_entropy([0.9, 0.1, 0.4], "median") == pytest.approx(0.4)


def test_median_even_count_averages_the_two_middles():
    # sorted: 1, 2, 3, 4 -> (2+3)/2 = 2.5. statistics.median interpolates; this
    # pins that choice, because after the equivalence gate drops a paraphrase
    # the variant count is routinely even.
    assert aggregate_entropy([4.0, 1.0, 3.0, 2.0], "median") == pytest.approx(2.5)


def test_mean_is_the_arithmetic_mean():
    assert aggregate_entropy([1.0, 2.0, 6.0], "mean") == pytest.approx(3.0)


def test_min_is_the_smallest():
    assert aggregate_entropy([1.0, 2.0, 6.0], "min") == pytest.approx(1.0)


def test_single_variant_every_aggregate_is_the_identity():
    # The degenerate case that matters in practice: the gate rejected every
    # paraphrase, so the "defended" score is exactly vanilla SE.
    for agg in AGGREGATES:
        assert aggregate_entropy([1.234], agg) == pytest.approx(1.234)


def test_unknown_aggregate_raises():
    with pytest.raises(ValueError, match="unknown aggregate"):
        aggregate_entropy([1.0, 2.0], "geometric")


def test_empty_input_raises_rather_than_returning_zero():
    # A silent 0.0 here would read as "perfectly confident" -- the most
    # dangerous possible failure value for an uncertainty detector.
    with pytest.raises(ValueError):
        aggregate_entropy([], "median")


# ---- the docstring's robustness claim, made falsifiable --------------------

def test_median_resists_a_single_adversarial_outlier_but_mean_does_not():
    """defense.py claims median is 'more robust than the mean to a single
    adversarial outlier'. Fixture: four honest variants at 1.0 nats and one
    adversarial variant driven to 0.0 (a Hide attack's target)."""
    honest = [1.0, 1.0, 1.0, 1.0]
    with_adversary = [0.0] + honest

    # median of [0,1,1,1,1] = 1.0 -- completely unmoved.
    assert aggregate_entropy(with_adversary, "median") == pytest.approx(1.0)
    # mean drops by exactly 1/5 of the outlier's displacement.
    assert aggregate_entropy(with_adversary, "mean") == pytest.approx(0.8)
    # min hands the attacker the answer outright.
    assert aggregate_entropy(with_adversary, "min") == pytest.approx(0.0)


def test_min_aggregate_is_maximally_vulnerable_to_the_hide_direction():
    """A Hide attack drives entropy DOWN, so `aggregate="min"` is monotone in
    the attacker's favour: the defended score can never exceed the attacker's
    own point. Documented as a property so nobody selects it for a Hide run."""
    honest = [1.5, 1.6, 1.4, 1.55]
    for adversarial in (1.0, 0.5, 0.0):
        combined = honest + [adversarial]
        assert aggregate_entropy(combined, "min") == pytest.approx(adversarial)
        assert aggregate_entropy(combined, "median") > adversarial


def test_median_breaks_once_the_attacker_controls_half_the_variants():
    """The robustness is a breakdown-point property, not magic: with d=4
    paraphrases the aggregate has 5 entries, so 3 adversarial entries move the
    median all the way. This bounds what the defense can promise."""
    honest = [1.0, 1.0]
    adversarial = [0.0, 0.0, 0.0]
    assert aggregate_entropy(honest + adversarial, "median") == pytest.approx(0.0)


# ---- select_variants: pure, no NLI model -----------------------------------

def _first_word_equivalent(a: str, b: str) -> bool:
    """Stand-in gate: equivalent iff the first lowercased word matches."""
    return a.lower().split()[:1] == b.lower().split()[:1]


def test_original_is_always_the_first_variant():
    sel = select_variants("Who wrote Hamlet?", [])
    assert sel.variants == ["Who wrote Hamlet?"]
    assert sel.n_candidates == 0


def test_degenerate_paraphrase_equal_to_the_input_is_dropped():
    """H2 from docs/phase2plus_review.md: proposer.propose returns the input
    unchanged on a degenerate generation. Re-adding it would double-count the
    original and drag the median toward it."""
    q = "Who wrote Hamlet?"
    sel = select_variants(q, [q, "Hamlet was written by whom?"])
    assert sel.variants == [q, "Hamlet was written by whom?"]
    assert sel.n_rejected_duplicate == 1


def test_dedupe_is_on_normalised_text_not_raw_text():
    # normalise() lowercases, strips punctuation and drops articles, so these
    # three collapse to one variant.
    q = "Who wrote the Hamlet?"
    sel = select_variants(q, ["who wrote Hamlet", "WHO WROTE THE HAMLET!"])
    assert len(sel.variants) == 1
    assert sel.n_rejected_duplicate == 2


def test_repeated_distinct_candidate_is_added_once():
    q = "Who wrote Hamlet?"
    para = "Hamlet was written by whom?"
    sel = select_variants(q, [para, para, para])
    assert sel.variants == [q, para]
    assert sel.n_rejected_duplicate == 2


def test_gate_rejects_non_equivalent_paraphrases():
    q = "Who wrote Hamlet?"
    sel = select_variants(
        q,
        ["Who penned Hamlet?", "When was Hamlet written?"],
        is_equivalent=_first_word_equivalent,
    )
    assert sel.variants == [q, "Who penned Hamlet?"]
    assert sel.n_rejected_gate == 1


def test_no_gate_keeps_everything_distinct():
    q = "Who wrote Hamlet?"
    cands = ["Who penned Hamlet?", "When was Hamlet written?"]
    sel = select_variants(q, cands, is_equivalent=None)
    assert sel.variants == [q] + cands
    assert sel.n_rejected_gate == 0


def test_gate_rejecting_everything_degenerates_to_the_original_alone():
    """The silent-failure case the added counters exist to surface: if the gate
    drops every paraphrase, the 'defended' score is vanilla SE and any measured
    effect reduction is attributable to re-sampling, not to the defense."""
    q = "Who wrote Hamlet?"
    sel = select_variants(
        q, ["When was it written?", "Where was it staged?"],
        is_equivalent=_first_word_equivalent,
    )
    assert sel.variants == [q]
    assert sel.n_rejected_gate == 2


def test_gate_is_evaluated_against_the_original_not_the_previous_variant():
    """Drift guard, mirroring optimizer.optimize: every candidate is compared
    to the ORIGINAL, so equivalence cannot accumulate error across variants."""
    seen_premises = []

    def recording_gate(a: str, b: str) -> bool:
        seen_premises.append(a)
        return True

    q = "Who wrote Hamlet?"
    select_variants(q, ["A", "B", "C"], is_equivalent=recording_gate)
    assert seen_premises == [q, q, q]


# ---- defended_entropy composed, with fakes ---------------------------------

class FakeLM:
    """Placeholder; the proposer and SE pipeline are both stubbed out."""


class FakeNLI:
    def __init__(self, verdicts: dict[str, bool] | None = None, default: bool = True):
        self.verdicts = verdicts or {}
        self.default = default
        self.calls: list[tuple[str, str]] = []

    def bidirectional_equivalent(self, a: str, b: str) -> bool:
        self.calls.append((a, b))
        return self.verdicts.get(b, self.default)


class _FakeSE:
    """Stands in for se_pipeline.semantic_entropy: a fixed entropy per query."""

    def __init__(self, table: dict[str, float]):
        self.table = table
        self.queries: list[str] = []
        self.gen_cfgs: list[object] = []

    def __call__(self, question, lm, nli, gen_cfg=None, **kw):
        self.queries.append(question)
        self.gen_cfgs.append(gen_cfg)

        class _R:
            entropy_nats = self.table[question]

        return _R()


@pytest.fixture
def patched(monkeypatch):
    """Install stubs for the two GPU entry points and hand them back."""

    def install(candidates: list[str], entropies: dict[str, float]):
        monkeypatch.setattr(
            D.proposer, "propose_many",
            lambda question, lm, n, **kw: list(candidates[:n]),
        )
        fake_se = _FakeSE(entropies)
        monkeypatch.setattr(D, "semantic_entropy", fake_se)
        return fake_se

    return install


def test_defended_entropy_is_the_median_over_original_plus_paraphrases(patched):
    q = "Who wrote Hamlet?"
    cands = ["Who penned Hamlet?", "Hamlet is by whom?", "Which author wrote Hamlet?"]
    ents = {q: 2.0, cands[0]: 0.5, cands[1]: 1.0, cands[2]: 3.0}
    fake_se = patched(cands, ents)

    res = defended_entropy(q, FakeLM(), FakeNLI(), k_paraphrases=3)

    assert isinstance(res, DefendedResult)
    # variants scored in order: original first.
    assert fake_se.queries == [q] + cands
    assert res.per_variant_entropy == [2.0, 0.5, 1.0, 3.0]
    # median of [2, 0.5, 1, 3] = (1 + 2)/2 = 1.5
    assert res.defended_entropy == pytest.approx(1.5)
    assert res.n_variants == 4
    assert res.effective_d == 3
    assert not res.degenerate


def test_defended_entropy_forces_unseeded_sampling_per_variant(patched):
    """H1 from docs/phase2plus_review.md: a fixed seed resets the RNG
    identically for every variant, correlating the draws and defeating the very
    noise-averaging the defense is supposed to demonstrate."""
    from se.config import GenConfig

    q = "Q"
    cands = ["P1", "P2"]
    fake_se = patched(cands, {q: 1.0, "P1": 1.0, "P2": 1.0})

    defended_entropy(q, FakeLM(), FakeNLI(), k_paraphrases=2,
                     gen_cfg=GenConfig(n_samples=10, seed=0))

    assert len(fake_se.gen_cfgs) == 3
    assert all(g.seed is None for g in fake_se.gen_cfgs)
    # everything else is carried through unchanged
    assert all(g.n_samples == 10 for g in fake_se.gen_cfgs)


def test_gate_rejection_is_recorded_and_shrinks_effective_d(patched):
    q = "Q"
    cands = ["good", "bad"]
    fake_se = patched(cands, {q: 1.0, "good": 2.0})
    nli = FakeNLI(verdicts={"good": True, "bad": False})

    res = defended_entropy(q, FakeLM(), nli, k_paraphrases=2)

    assert fake_se.queries == [q, "good"]     # "bad" was never scored
    assert res.n_variants == 2
    assert res.effective_d == 1
    assert res.n_rejected_gate == 1
    assert res.n_candidates == 2
    assert res.k_requested == 2


def test_all_paraphrases_rejected_degenerates_to_vanilla_se(patched):
    """The result that must never be silently reported as a defense result."""
    q = "Q"
    fake_se = patched(["bad1", "bad2"], {q: 1.75})
    nli = FakeNLI(default=False)

    res = defended_entropy(q, FakeLM(), nli, k_paraphrases=2)

    assert res.degenerate
    assert res.effective_d == 0
    assert res.n_rejected_gate == 2
    assert res.defended_entropy == pytest.approx(1.75)   # == vanilla SE
    assert fake_se.queries == [q]


def test_require_equivalent_false_skips_the_gate_entirely(patched):
    q = "Q"
    cands = ["a", "b"]
    patched(cands, {q: 1.0, "a": 2.0, "b": 3.0})
    nli = FakeNLI(default=False)   # would reject everything if consulted

    res = defended_entropy(q, FakeLM(), nli, k_paraphrases=2,
                           require_equivalent=False)

    assert nli.calls == []
    assert res.n_variants == 3
    assert res.defended_entropy == pytest.approx(2.0)   # median of [1, 2, 3]


def test_zero_paraphrases_is_vanilla_se_not_a_crash(patched):
    q = "Q"
    patched([], {q: 0.9})
    res = defended_entropy(q, FakeLM(), FakeNLI(), k_paraphrases=0)
    assert res.degenerate
    assert res.defended_entropy == pytest.approx(0.9)


def test_aggregate_is_validated_before_any_gpu_work(monkeypatch):
    """An unknown aggregate used to raise only AFTER paying for K paraphrases
    and up to K+1 SE evaluations -- ~70 GPU-seconds thrown away per call."""
    called = []
    monkeypatch.setattr(D.proposer, "propose_many",
                        lambda *a, **k: called.append("propose") or [])
    monkeypatch.setattr(D, "semantic_entropy",
                        lambda *a, **k: called.append("se"))

    with pytest.raises(ValueError, match="unknown aggregate"):
        defended_entropy("Q", FakeLM(), FakeNLI(), aggregate="typo")

    assert called == []


def test_mean_and_min_aggregates_compose_end_to_end(patched):
    q = "Q"
    cands = ["a", "b", "c"]
    ents = {q: 2.0, "a": 0.0, "b": 1.0, "c": 1.0}
    patched(cands, ents)

    mean_res = defended_entropy(q, FakeLM(), FakeNLI(), k_paraphrases=3,
                                aggregate="mean")
    assert mean_res.defended_entropy == pytest.approx(1.0)

    min_res = defended_entropy(q, FakeLM(), FakeNLI(), k_paraphrases=3,
                               aggregate="min")
    assert min_res.defended_entropy == pytest.approx(0.0)


# ---- the property the experiment actually turns on -------------------------

def test_averaging_alone_cannot_reduce_an_effect_that_is_pure_signal(patched):
    """Sanity anchor for the falsifiable claim. If every paraphrase of Q' shares
    the adversarial entropy (the attack found a robust semantic region, not a
    lucky phrasing), the defense returns exactly the attacked value and the
    measured reduction is 0. The defense can only help when the paraphrases
    DISAGREE with the adversarial point."""
    q_adv = "Qadv"
    cands = ["p1", "p2", "p3"]
    patched(cands, {q_adv: 0.2, "p1": 0.2, "p2": 0.2, "p3": 0.2})

    res = defended_entropy(q_adv, FakeLM(), FakeNLI(), k_paraphrases=3)
    assert res.defended_entropy == pytest.approx(0.2)
    assert res.effective_d == 3          # the defense DID run; it just did not help


def test_defense_reverts_a_lone_adversarial_phrasing(patched):
    """The complementary case: Q' is a narrow adversarial point whose own
    paraphrases sit back at the honest entropy. The median reverts fully."""
    q_adv = "Qadv"
    cands = ["p1", "p2", "p3"]
    patched(cands, {q_adv: 0.2, "p1": 1.5, "p2": 1.6, "p3": 1.4})

    res = defended_entropy(q_adv, FakeLM(), FakeNLI(), k_paraphrases=3)
    # median of [0.2, 1.5, 1.6, 1.4] = (1.4 + 1.5)/2 = 1.45
    assert res.defended_entropy == pytest.approx(1.45)


def test_statistics_median_matches_the_manual_definition_on_the_fixtures():
    """Guard against a future refactor swapping in a different median
    convention (e.g. median_low), which would silently change every number."""
    for xs in ([1.0], [1.0, 2.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]):
        srt = sorted(xs)
        n = len(srt)
        manual = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
        assert aggregate_entropy(xs, "median") == pytest.approx(manual)
        assert not math.isnan(statistics.median(xs))
