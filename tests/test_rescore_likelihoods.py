"""The three semantic-entropy estimators, against hand-computable fixtures.

CPU only, no model, no GPU: everything here is the pure arithmetic of
`scripts/rescore_likelihoods.py`. The fixtures are chosen so each one pins a property
that distinguishes the estimators, because the whole point of the re-scoring pass is
that our ceiling/lattice claims are properties of ONE of them:

  * discrete and Farquhar Eq. (5) are bounded by log N;
  * Kuhn Eq. (4) is NOT, and must be able to exceed it;
  * Eq. (5) collapses onto discrete exactly when the likelihoods are flat, which is the
    invariant that makes any observed difference attributable to the likelihood spread.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec: @dataclass resolves annotations via
    # sys.modules[cls.__module__], which is None for an unregistered module.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


R = _load("rescore_likelihoods")

LOG10 = math.log(10)
SINGLETONS = list(range(10))              # 10 clusters of size 1
ONE_CLUSTER = [0] * 10                    # 1 cluster of size 10
FIVE_PAIRS = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
SKEWED = [0] * 6 + [1, 2, 3, 4]           # sizes 6,1,1,1,1


# --------------------------------------------------------------- the anchor fixture
def test_uniform_singletons_give_exactly_log10_under_discrete():
    """10 singleton clusters -> H = log 10 exactly, the attainable maximum at N=10."""
    assert R.discrete_entropy_estimator(SINGLETONS) == pytest.approx(LOG10, abs=1e-12)


def test_uniform_singletons_give_exactly_log10_under_eq5_with_equal_weights():
    """Same clustering, EQUAL likelihoods -> Eq. (5) must also return exactly log 10.

    This is the anchor: the two estimators are only allowed to differ because of
    likelihood SPREAD, so at zero spread they must coincide to machine precision."""
    for ll in (-1.0, -12.5, -60.0, 0.0):
        logliks = [ll] * 10
        assert R.farquhar_eq5_entropy(SINGLETONS, logliks) == pytest.approx(
            LOG10, abs=1e-12)


def test_eq5_equals_discrete_whenever_likelihoods_are_flat():
    """Flat likelihoods make p(C_k) = n_k / N for ANY clustering, not just singletons."""
    for assign in (SINGLETONS, ONE_CLUSTER, FIVE_PAIRS, SKEWED,
                   [0, 0, 0, 1, 1, 2, 3, 3, 3, 3]):
        flat = [-7.25] * len(assign)
        assert R.farquhar_eq5_entropy(assign, flat) == pytest.approx(
            R.discrete_entropy_estimator(assign), abs=1e-12)


# ------------------------------------------------------- Kuhn Eq. (4) is unbounded
def test_kuhn_eq4_can_exceed_log_n():
    """THE point of separating the estimators: Eq. (4) has no log N ceiling.

    10 singletons each with log p = -20 gives -(1/10) * sum(-(-20)) = 20 nats, which is
    8.7x the log 10 = 2.30 that both other estimators cannot exceed."""
    logliks = [-20.0] * 10
    h = R.kuhn_eq4_entropy(SINGLETONS, logliks)
    assert h == pytest.approx(20.0, abs=1e-12)
    assert h > LOG10
    # ... and unboundedly so: halve the likelihood and the score keeps climbing.
    assert R.kuhn_eq4_entropy(SINGLETONS, [-500.0] * 10) == pytest.approx(500.0)


def test_kuhn_eq4_matches_log10_only_for_the_one_special_likelihood():
    """With p(s) = 1/10 for each singleton, Eq. (4) coincidentally returns log 10.

    Worth pinning precisely because it is a coincidence: it is the surprisal of 1/10,
    not a ceiling. Nudge the likelihood and the number leaves the interval [0, log N]."""
    assert R.kuhn_eq4_entropy(SINGLETONS, [-LOG10] * 10) == pytest.approx(LOG10, abs=1e-12)
    assert R.kuhn_eq4_entropy(SINGLETONS, [-LOG10 - 0.5] * 10) > LOG10


def test_kuhn_eq4_is_unnormalised_single_cluster_is_not_zero():
    """A single cluster has zero ENTROPY but a positive surprisal. Discrete and Eq. (5)
    both give exactly 0; Eq. (4) gives -log(sum of the members' likelihoods)."""
    logliks = [-5.0] * 10
    assert R.discrete_entropy_estimator(ONE_CLUSTER) == pytest.approx(0.0, abs=1e-15)
    assert R.farquhar_eq5_entropy(ONE_CLUSTER, logliks) == pytest.approx(0.0, abs=1e-12)
    expected = 5.0 - LOG10                      # -log(10 * e^-5)
    assert R.kuhn_eq4_entropy(ONE_CLUSTER, logliks) == pytest.approx(expected, abs=1e-12)


# ------------------------------------------------------------ Eq. (5) obeys log K
@pytest.mark.parametrize("seed", range(12))
def test_eq5_never_exceeds_log_k(seed):
    """Eq. (5) is the entropy of a normalised K-vector, so H <= log K <= log N. Random
    clusterings and wildly spread likelihoods (including ones that underflow a naive
    exp) must not break it."""
    import random
    rng = random.Random(seed)
    n = 10
    assign = [rng.randrange(1, n + 1) for _ in range(n)]
    logliks = [rng.uniform(-120.0, 0.0) for _ in range(n)]
    k = len(set(assign))
    h = R.farquhar_eq5_entropy(assign, logliks)
    assert -1e-12 <= h <= math.log(k) + 1e-9
    assert h <= LOG10 + 1e-9


def test_eq5_handles_extreme_underflow_without_dropping_clusters():
    """Likelihoods at e^-700 underflow float64 if exponentiated directly; the log-space
    implementation must still see two clusters and return log 2 for an even split."""
    logliks = [-700.0] * 10
    assert R.farquhar_eq5_entropy([0] * 5 + [1] * 5, logliks) == pytest.approx(
        math.log(2), abs=1e-12)


def test_eq5_concentrates_when_one_cluster_dominates():
    """A cluster 1000 nats more likely than the rest takes essentially all the mass, so
    Eq. (5) collapses to ~0 even though the discrete estimator sees 10 clusters at
    log 10. This is the mechanism by which likelihood weighting could destroy the
    pile-up -- the reason the re-scoring pass exists."""
    logliks = [0.0] + [-1000.0] * 9
    assert R.discrete_entropy_estimator(SINGLETONS) == pytest.approx(LOG10)
    assert R.farquhar_eq5_entropy(SINGLETONS, logliks) == pytest.approx(0.0, abs=1e-9)


def test_eq5_two_clusters_matches_hand_computed_binary_entropy():
    """Hand-checkable: two clusters with total weights e^0 and e^-1 give
    p = (1/(1+e^-1), e^-1/(1+e^-1)) and H = -p log p - q log q."""
    logliks = [0.0, -1.0]
    z = 1.0 + math.exp(-1.0)
    p, q = 1.0 / z, math.exp(-1.0) / z
    expected = -(p * math.log(p) + q * math.log(q))
    assert R.farquhar_eq5_entropy([0, 1], logliks) == pytest.approx(expected, abs=1e-14)


def test_eq5_sums_likelihoods_within_a_cluster():
    """Cluster probability is the SUM over members, not the max or the mean. Two
    members at e^-1 each must weigh the same as one member at 2*e^-1."""
    a = R.farquhar_eq5_entropy([0, 0, 1], [-1.0, -1.0, math.log(2 * math.exp(-1.0))])
    assert a == pytest.approx(math.log(2), abs=1e-12)


# ------------------------------------------------------------- length normalisation
def test_length_normalise_divides_by_token_count():
    assert R.length_normalise([-10.0, -6.0], [5, 2]) == [-2.0, -3.0]


def test_length_normalise_sends_zero_length_to_minus_inf_not_a_crash():
    out = R.length_normalise([-10.0, -3.0], [0, 3])
    assert out[0] == -math.inf and out[1] == pytest.approx(-1.0)


def test_length_normalisation_reverses_which_sample_dominates():
    """The reason Kuhn 3.3 exists. Raw likelihood favours the short sample; per-token
    likelihood favours the long one, and the two give different cluster weightings."""
    logliks = [-6.0, -10.0]          # sample 0 is likelier overall
    n_tokens = [2, 10]               # but far less likely per token
    assert logliks[0] > logliks[1]
    ln = R.length_normalise(logliks, n_tokens)
    assert ln[0] < ln[1]
    raw = R.farquhar_eq5_entropy([0, 1], logliks)
    norm = R.farquhar_eq5_entropy([0, 1], ln)
    assert raw != pytest.approx(norm)


def test_length_normalisation_is_a_no_op_when_all_lengths_are_equal_for_eq5():
    """Equal lengths scale every log-likelihood by the same constant. That is NOT a
    no-op for Eq. (5) in general -- rescaling logits sharpens the softmax -- so this
    pins the actual behaviour rather than an assumed invariance."""
    logliks = [-8.0, -4.0, -16.0]
    ln = R.length_normalise(logliks, [4, 4, 4])
    assert ln == [-2.0, -1.0, -4.0]
    assert R.farquhar_eq5_entropy([0, 1, 2], ln) > R.farquhar_eq5_entropy(
        [0, 1, 2], logliks)


def test_all_estimators_agree_with_the_individual_functions():
    logliks = [-3.0, -4.0, -5.0, -6.0, -7.0, -8.0, -9.0, -10.0, -11.0, -12.0]
    n_tokens = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    got = R.all_estimators(SINGLETONS, logliks, n_tokens)
    assert got["discrete"] == pytest.approx(R.discrete_entropy_estimator(SINGLETONS))
    assert got["farquhar_eq5"] == pytest.approx(
        R.farquhar_eq5_entropy(SINGLETONS, logliks))
    assert got["kuhn_eq4"] == pytest.approx(R.kuhn_eq4_entropy(SINGLETONS, logliks))
    ln = R.length_normalise(logliks, n_tokens)
    assert got["farquhar_eq5_lennorm"] == pytest.approx(
        R.farquhar_eq5_entropy(SINGLETONS, ln))
    assert got["kuhn_eq4_lennorm"] == pytest.approx(R.kuhn_eq4_entropy(SINGLETONS, ln))


def test_discrete_matches_the_shipped_implementation():
    """The rescoring script reimplements the discrete estimator so all three sit side by
    side; it must not drift from `se.entropy.discrete_entropy`, which produced every
    number currently in the paper."""
    from se.entropy import discrete_entropy
    for assign in (SINGLETONS, ONE_CLUSTER, FIVE_PAIRS, SKEWED,
                   [0, 1, 1, 2, 2, 2, 3, 3, 3, 3]):
        assert R.discrete_entropy_estimator(assign) == pytest.approx(
            discrete_entropy(assign), abs=1e-15)


# ------------------------------------------------------------------ report summaries
def test_estimator_stats_counts_cap_top_decile_and_distinct():
    cap, td = R.CAP, R.TOP_DECILE
    values = [cap, cap, cap - 1e-12, td, td - 1e-6, 0.5, 0.5, 0.5]
    s = R.estimator_stats(values)
    assert s["n"] == 8
    assert s["at_cap"] == 3                 # the 1e-12 shortfall is inside TOL
    assert s["above_cap"] == 0
    assert s["top_decile"] == 4             # three at-cap plus the exact td
    assert s["distinct"] == 4               # cap, td, td-1e-6, 0.5


def test_estimator_stats_separates_at_cap_from_strictly_above_cap():
    """The diagnostic that shows a ceiling claim does not transfer: Kuhn scores land
    strictly above log N, discrete scores never can."""
    s = R.estimator_stats([R.CAP + 5.0, R.CAP + 0.001, R.CAP, 1.0])
    assert s["at_cap"] == 3 and s["above_cap"] == 2


def test_spearman_is_one_under_a_monotone_reweighting():
    """A reweighting that changes every value but no ordering leaves every AUROC in the
    paper intact -- so rank agreement, not value agreement, is the decision-relevant
    comparison."""
    a = [0.1, 0.4, 0.9, 1.7, 2.3]
    b = [x ** 3 + 1.0 for x in a]
    assert R.spearman(a, b) == pytest.approx(1.0, abs=1e-12)
    assert R.spearman(a, [-x for x in a]) == pytest.approx(-1.0, abs=1e-12)


def test_spearman_averages_ties():
    """Discrete scores are heavily tied (39 attainable values at N=10), so tie handling
    is not an edge case here -- it is the common case."""
    assert R.spearman([1.0, 1.0, 2.0, 3.0], [1.0, 1.0, 2.0, 3.0]) == pytest.approx(1.0)


# --------------------------------------------------------------------- manifest audit
def _wk4_manifest() -> dict:
    """The real Week-4 manifest shape, as written by scripts/wk4_sample.py."""
    return {
        "phase": "A",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "load_in_4bit": True,
        "n_samples": 10,
        "temperature": 1.0,
        "max_new_tokens": 48,
        "seed": 0,
        "split": "validation",
        "n_questions_target": 2000,
        "n_questions_completed_this_run": 1907,
        "elapsed_seconds_this_run": 23340.087370081,
    }


def test_audit_accepts_the_required_pins_the_wk4_manifest_does_carry():
    a = R.audit_generation_settings(_wk4_manifest())
    assert a.ok
    assert a.present["model_id"] == "meta-llama/Llama-3.1-8B-Instruct"
    assert a.present["temperature"] == 1.0


def test_audit_flags_the_quantisation_settings_the_wk4_manifest_omits():
    """These are the ones that actually matter for a logit and are simply not there."""
    a = R.audit_generation_settings(_wk4_manifest())
    missing = {k for k, _ in a.missing_desirable}
    assert {"top_p", "bnb_4bit_quant_type", "bnb_4bit_use_double_quant",
            "compute_dtype", "model_revision"} <= missing


def test_audit_flags_a_manifest_that_describes_only_the_last_resumed_run():
    a = R.audit_generation_settings(_wk4_manifest(), n_records=2000)
    assert any("assembled across multiple runs" in w for w in a.warnings)


def test_audit_notes_the_temperature_one_identity():
    a = R.audit_generation_settings(_wk4_manifest())
    assert any("sampling distribution IS the model distribution" in w for w in a.warnings)


def test_audit_warns_when_temperature_is_not_one():
    m = _wk4_manifest()
    m["temperature"] = 0.7
    a = R.audit_generation_settings(m)
    assert any("temperature correction" in w for w in a.warnings)


def test_audit_warns_when_top_p_truncates():
    m = _wk4_manifest()
    m["top_p"] = 0.9
    a = R.audit_generation_settings(m)
    assert any("nucleus truncation breaks" in w for w in a.warnings)


def test_audit_fails_when_a_required_pin_is_absent():
    m = _wk4_manifest()
    del m["model_id"]
    a = R.audit_generation_settings(m)
    assert not a.ok
    assert "model_id" in {k for k, _ in a.missing_required}


def test_the_real_wk4_manifest_matches_the_fixture_shape():
    """If the on-disk manifest is reachable, confirm the fixture is not fiction."""
    p = R.SAMPLES_DIR / "manifest.json"
    if not p.exists():
        pytest.skip("WSL cache not mounted on this side")
    real = json.loads(p.read_text())
    assert set(real) == set(_wk4_manifest())


# --------------------------------------------------------------------------- costing
def test_cost_estimate_arithmetic():
    rows = R.cost_estimate(20_000, 1_575_000, throughputs=[1000.0], load_seconds=60.0)
    assert len(rows) == 1
    assert rows[0]["seconds"] == pytest.approx(1_575_000 / 1000.0 + 60.0)
    assert rows[0]["gpu_hours"] == pytest.approx(rows[0]["seconds"] / 3600.0)
    assert rows[0]["seconds_per_question"] == pytest.approx(rows[0]["seconds"] / 2000)


def test_cost_estimate_is_monotone_in_throughput():
    rows = R.cost_estimate(20_000, 1_575_000)
    hours = [r["gpu_hours"] for r in rows]
    assert hours == sorted(hours, reverse=True)


# --------------------------------------------------------------- checkpoint recovery
def test_load_checkpoint_survives_a_torn_final_line(tmp_path):
    """Per-question checkpointing means a kill mid-write leaves a partial JSON line.
    Resuming must skip it, not abort the run."""
    p = tmp_path / "ckpt.jsonl"
    p.write_text(
        json.dumps({"question_id": "a", "loglik": [-1.0]}) + "\n"
        + json.dumps({"question_id": "b", "loglik": [-2.0]}) + "\n"
        + '{"question_id": "c", "loglik": [-3',
        encoding="utf-8")
    got = R.load_checkpoint(p)
    assert set(got) == {"a", "b"}


def test_load_checkpoint_on_a_missing_file_is_empty_not_an_error(tmp_path):
    assert R.load_checkpoint(tmp_path / "nope.jsonl") == {}


def test_load_checkpoint_last_write_wins_for_a_repeated_id(tmp_path):
    p = tmp_path / "ckpt.jsonl"
    p.write_text(json.dumps({"question_id": "a", "loglik": [-1.0]}) + "\n"
                 + json.dumps({"question_id": "a", "loglik": [-9.0]}) + "\n",
                 encoding="utf-8")
    assert R.load_checkpoint(p)["a"]["loglik"] == [-9.0]


# ----------------------------------------------------------------- degenerate inputs
def test_empty_assignments_are_zero_everywhere():
    assert R.discrete_entropy_estimator([]) == 0.0
    assert R.farquhar_eq5_entropy([], []) == 0.0
    assert R.kuhn_eq4_entropy([], []) == 0.0


def test_eq5_raises_rather_than_silently_returning_zero_when_all_weights_vanish():
    with pytest.raises(ValueError):
        R.farquhar_eq5_entropy([0, 1], [-math.inf, -math.inf])


def test_kuhn_raises_on_a_zero_weight_cluster():
    with pytest.raises(ValueError):
        R.kuhn_eq4_entropy([0, 1], [0.0, -math.inf])


# ------------------------------------------------- teacher forcing: index arithmetic
# score_question() is the only part of the GPU path with a plausible silent bug: an
# off-by-one in "position j predicts token j+1" would shift every log-likelihood by one
# token and quietly corrupt both likelihood-weighted estimators. These stubs exercise
# it on CPU with no model download -- a perfect next-token predictor MUST score ~0, and
# a slice shifted by one would score ~ -20 per token instead.

VOCAB = 32
_torch = pytest.importorskip("torch")


class _StubTok:
    """Character-level tokenizer, deterministic and invertible enough for the test."""
    pad_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "<" + messages[0]["content"] + ">"

    def __call__(self, text, add_special_tokens=True):
        return {"input_ids": [1 + (ord(c) % (VOCAB - 1)) for c in text]}


class _StubModel:
    """Returns logits that put mass `peak` on the token that actually comes next."""

    def __init__(self, peak=20.0, shift=0):
        self.peak, self.shift = peak, shift
        self.device = "cpu"

    def __call__(self, input_ids=None, attention_mask=None):
        b, t = input_ids.shape
        logits = _torch.zeros((b, t, VOCAB))
        for i in range(b):
            for pos in range(t - 1):
                nxt = int(input_ids[i, pos + 1 + self.shift]) if \
                    pos + 1 + self.shift < t else 0
                logits[i, pos, nxt] = self.peak
        return type("Out", (), {"logits": logits})()


class _StubLM:
    def __init__(self, model):
        self.model = model
        self.tokenizer = _StubTok()


def test_score_question_scores_a_perfect_next_token_predictor_at_about_zero():
    lm = _StubLM(_StubModel())
    out = R.score_question(lm, "abc", ["hello", "hi"])
    assert out["n_tokens"] == [5, 2]
    for ll, t in zip(out["loglik"], out["n_tokens"]):
        assert ll == pytest.approx(0.0, abs=1e-4), (
            "a perfect predictor must score ~0; a shifted slice would score ~-20/token")


def test_score_question_off_by_one_would_be_caught():
    """Guard on the guard: with the stub's peak deliberately misaligned by one
    position, the score must collapse -- proving the previous test has teeth."""
    lm = _StubLM(_StubModel(shift=1))
    out = R.score_question(lm, "abc", ["hello"])
    assert out["loglik"][0] < -50.0


def test_score_question_ignores_padding_for_the_shorter_sequence():
    """Right padding plus an attention mask: the short sample's log-likelihood must be
    exactly its own, not contaminated by the longer row's padded tail."""
    lm = _StubLM(_StubModel())
    both = R.score_question(lm, "abc", ["hello", "hi"])
    alone = R.score_question(lm, "abc", ["hi"])
    assert both["loglik"][1] == pytest.approx(alone["loglik"][0], abs=1e-5)


def test_score_question_reports_prompt_length_and_empty_samples():
    lm = _StubLM(_StubModel())
    out = R.score_question(lm, "abc", ["hi", ""])
    assert out["prompt_tokens"] == 5           # "<abc>"
    assert out["n_tokens"] == [2, 0]
    assert out["loglik"][1] == -math.inf       # zero-token sample carries no weight


def test_score_question_loglik_scales_with_length_under_a_uniform_model():
    """With flat logits every token costs exactly log V, so the log-likelihood is
    -T log V. This pins that exactly T completion positions are gathered -- no prompt
    token leaks in, and no token is dropped."""
    class _Flat:
        device = "cpu"

        def __call__(self, input_ids=None, attention_mask=None):
            return type("Out", (), {
                "logits": _torch.zeros((*input_ids.shape, VOCAB))})()

    out = R.score_question(_StubLM(_Flat()), "abc", ["hello", "hi"])
    for ll, t in zip(out["loglik"], out["n_tokens"]):
        assert ll == pytest.approx(-t * math.log(VOCAB), abs=1e-4)
