"""Two confirmed statistical defects, fixed 2026-08-13. CPU-only, no models, no cache.

DEFECT 1 — `se.stats.operating_point` returned `np.quantile(neg, 1 - target_fpr)` while its
docstring promised an FPR <= target. On an atom-valued score (semantic entropy has a large
atom at the log(N) ceiling) the achieved FPR was 3-6x the target; it also missed on
continuous scores whenever the interpolation index (1-t)(n-1) is integral.

DEFECT 2 — the tie multiplicity `b` in `exceedance_counts_randomized` had no upper clamp,
and `exceedance_test` never saw `b`, so nothing could cross-check it. Over-stating b is the
anti-conservative direction: it is the same failure class as the 99.6%-false-positive bug of
critique_log 28.

These are SIMULATION tests, not shape tests. The 99.6% bug survived both code review and
unit tests, so each defect is asserted by measuring the quantity that was wrong (achieved
FPR; H0 rejection rate) rather than by inspecting the code path.
"""
from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import betabinom

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import (                                              # noqa: E402
    OperatingPoint, attainable_fprs, exceedance_counts_randomized, exceedance_test,
    exceedance_test_over_seeds, flips_at_threshold, operating_point,
)

CAP = math.log(10)


def _achieved(neg, thr) -> float:
    """The FPR the detector really runs at: it flags when score >= thr."""
    return float(np.mean(np.asarray(neg, dtype=float) >= float(thr)))


def _negatives(rng, n, atom_frac):
    """Clean correct-answer scores: a continuous body plus an atom at the log(10) ceiling."""
    v = rng.uniform(0.0, CAP * 0.98, n)
    v[rng.random(n) < atom_frac] = CAP
    return v


# =============================================================== DEFECT 1: operating_point

def test_achieved_fpr_never_exceeds_target_across_ceiling_atoms():
    """THE regression, by simulation. Atom fraction 0 -> 0.6, 300 trials each.

    Measured with the OLD quantile rule (2000 trials, n=200, target 0.10): mean achieved FPR
    0.100 / 0.108 / 0.200 / 0.299 / 0.400 / 0.600 at atom fractions 0 / 0.10 / 0.20 / 0.30 /
    0.40 / 0.60, i.e. the achieved rate simply tracked the atom mass once the atom covered
    the target quantile. Nothing below may exceed the target, ever.
    """
    rng = np.random.default_rng(0)
    for q in (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.60):
        worst = 0.0
        for _ in range(300):
            neg = _negatives(rng, 200, q)
            op = operating_point([0] * len(neg), neg, target_fpr=0.10)
            worst = max(worst, _achieved(neg, op.threshold))
            assert op.achieved_fpr == pytest.approx(_achieved(neg, op.threshold)), \
                "the reported achieved FPR must be the one the detector realises"
        assert worst <= 0.10 + 1e-12, f"atom fraction {q}: achieved FPR reached {worst}"


def test_achieved_fpr_never_exceeds_target_across_sample_sizes():
    """The continuous-score half of defect 1: np.quantile interpolates BETWEEN order
    statistics, and when the index (1-t)(n-1) is integral the threshold lands ON one and
    `>=` flags it. Old rule at target 0.10: n=5 -> 0.200, n=41 -> 0.122, n=61 -> 0.1148,
    n=301 -> 0.103."""
    rng = np.random.default_rng(1)
    for n in (3, 5, 11, 20, 41, 61, 80, 100, 200, 301):
        for _ in range(60):
            neg = _negatives(rng, n, 0.0)
            op = operating_point([0] * n, neg, target_fpr=0.10)
            assert op.achieved_fpr <= 0.10 + 1e-12, f"n={n}"
            assert op.achieved_fpr == pytest.approx(_achieved(neg, op.threshold))


def test_achieved_fpr_never_exceeds_target_across_targets():
    """Same guarantee across the whole target sweep report.py uses, at a heavy atom."""
    rng = np.random.default_rng(2)
    for t in (0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.50, 1.0):
        for _ in range(60):
            neg = _negatives(rng, 120, 0.30)
            op = operating_point([0] * len(neg), neg, target_fpr=t)
            assert op.achieved_fpr <= t + 1e-12, f"target {t}"


def test_the_documented_failure_case_is_now_honest():
    """The concrete case from the pre-registration: a score taking few values, where the
    achievable FPR grid steps straight over the target. The 'at most' answer must be the
    grid point below the target and must SAY it is 9.5%, not 10%."""
    # 200 negatives: 19 at the ceiling (9.5%), 24 at the next atom down (-> 21.5% cumulative)
    neg = np.concatenate([np.full(19, CAP), np.full(24, 2.1640), np.full(157, 1.0)])
    op = operating_point([0] * len(neg), neg, target_fpr=0.10)
    assert op.threshold == pytest.approx(CAP)
    assert op.achieved_fpr == pytest.approx(19 / 200)          # 9.5%, not 10%
    assert op.honours_contract is True
    # The old rule's answer, still reachable BY NAME, and self-labelled as over target.
    old = operating_point([0] * len(neg), neg, target_fpr=0.10, mode="nominal_quantile")
    assert old.threshold == pytest.approx(2.1640)
    assert old.achieved_fpr == pytest.approx(43 / 200)         # 21.5% — the realised rate
    assert old.honours_contract is False
    # ...and 'closest' picks 9.5% over 21.5% because |0.095-0.10| < |0.215-0.10|.
    near = operating_point([0] * len(neg), neg, target_fpr=0.10, mode="closest")
    assert near.achieved_fpr == pytest.approx(19 / 200)
    # 'closest' never degenerates: at a 1% target it still returns a FIRING threshold, and
    # says plainly that 9.5% is nine times what was asked for.
    tiny = operating_point([0] * len(neg), neg, target_fpr=0.01, mode="closest")
    assert tiny.threshold == pytest.approx(CAP)
    assert tiny.achieved_fpr == pytest.approx(19 / 200)
    assert tiny.honours_contract is False and tiny.flags_nothing is False


def test_degenerate_when_the_top_atom_outweighs_the_target():
    """If 30% of negatives sit at the ceiling and you ask for 10%, no FIRING threshold
    qualifies. The contract still has to hold: the honest answer is 'never fire', announced
    as such, with the nearest real operating point reported beside it."""
    neg = np.concatenate([np.full(30, CAP), np.linspace(0.0, 2.0, 70)])
    op = operating_point([0] * len(neg), neg, target_fpr=0.10)
    assert op.threshold == float("inf")
    assert op.achieved_fpr == 0.0 and op.flags_nothing is True
    assert op.honours_contract is True
    # the nearest rate the detector could actually run at, so the zero row is readable
    assert op.closest_attainable_fpr == pytest.approx(0.30)
    assert "flags nothing" in str(op)


def test_attainable_grid_is_exactly_the_reachable_fprs():
    neg = [0.1, 0.2, 0.2, 0.3]
    vals, fprs = attainable_fprs(neg)
    assert list(vals[:-1]) == [0.1, 0.2, 0.3] and vals[-1] == float("inf")
    assert list(fprs) == [1.0, 0.75, 0.25, 0.0]
    # every grid point is the FPR the detector would truly realise at that threshold
    for v, f in zip(vals, fprs):
        assert _achieved(neg, v) == pytest.approx(f)
    # FPR is non-increasing in the threshold, which is what makes 'first <= target' correct
    assert all(fprs[i] >= fprs[i + 1] for i in range(len(fprs) - 1))


def test_threshold_is_an_attainable_value_not_an_interpolation():
    """The mechanism behind defect 1: 0.28 is not a score any negative can take, so its
    realised FPR is an accident of where `>=` lands."""
    neg = [0.1, 0.2, 0.3]
    old = operating_point([0] * 3, neg, target_fpr=0.10, mode="nominal_quantile")
    assert old.threshold == pytest.approx(0.28) and old.achieved_fpr == pytest.approx(1 / 3)
    fixed = operating_point([0] * 3, neg, target_fpr=1 / 3)
    assert fixed.threshold in (0.3,)
    assert fixed.achieved_fpr == pytest.approx(1 / 3)


def test_operating_point_is_not_silently_a_float():
    """`float(op)` is the threshold, but the object must not slip into arithmetic where a
    caller then quotes a nominal FPR nobody checked."""
    op = operating_point([0, 0, 1], [0.1, 0.2, 0.9], target_fpr=0.5)
    assert isinstance(op, OperatingPoint)
    assert float(op) == op.threshold
    with pytest.raises(TypeError):
        _ = op + 1.0
    assert "achieved FPR" in str(op)


def test_flips_at_threshold_reports_the_achieved_fpr_from_its_own_negatives():
    labels = [1, 1, 0, 0, 0, 0]
    clean = [0.9, 0.8, 0.1, 0.2, 0.3, 0.4]
    attacked = [0.1, 0.8, 0.1, 0.2, 0.3, 0.95]
    op = operating_point(labels, clean, target_fpr=0.25)
    f = flips_at_threshold(labels, clean, attacked, op)
    assert f["achieved_fpr"] == pytest.approx(_achieved(clean[2:], f["threshold"]))
    assert f["achieved_fpr"] <= 0.25 + 1e-12
    assert f["target_fpr"] == 0.25 and f["fpr_contract_honoured"] is True
    # a bare float still works, and still gets an honest achieved_fpr
    g = flips_at_threshold(labels, clean, attacked, 0.35)
    assert g["achieved_fpr"] == pytest.approx(0.25)


def test_no_negatives_is_undefined_not_zero():
    op = operating_point([1, 1], [0.4, 0.6], target_fpr=0.1)
    assert op.threshold == float("inf") and op.n_negatives == 0
    assert math.isnan(op.achieved_fpr)


def test_bad_arguments_raise():
    with pytest.raises(ValueError):
        operating_point([0, 1], [0.1, 0.2], target_fpr=1.5)
    with pytest.raises(ValueError):
        operating_point([0, 1], [0.1, 0.2], target_fpr=float("nan"))
    with pytest.raises(ValueError):
        operating_point([0, 1], [0.1, 0.2], mode="quantile")


# ============================================================ DEFECT 2: tie multiplicity b

def _null_cdf(m: int, n_targets: int, N: int) -> np.ndarray:
    """CDF of S = sum_j K_j under exceedance_test's exact null (all m_j equal)."""
    pmf = np.asarray(betabinom.pmf(np.arange(m + 1), m, 1, N), dtype=float)
    pmf = pmf / pmf.sum()
    dist = np.array([1.0])
    for _ in range(n_targets):
        dist = np.convolve(dist, pmf)
    return np.cumsum(dist)


def _h0_draw(rng, q, N, m, T):
    """T exchangeable H0 targets with a ceiling atom of mass q.

    Attack = N draws, benign = m draws, each at the ceiling w.p. q else Uniform(0,1).
    Returns (strict, tied, b_true) — b_true is the honest tie multiplicity.
    """
    n_cap_att = rng.binomial(N, q, T)
    at_cap = n_cap_att >= 1
    A = np.where(at_cap, 1.0, rng.beta(N, 1, T))          # max of N uniforms ~ Beta(N,1)
    b_true = np.where(at_cap, np.maximum(n_cap_att, 1), 1)
    n_cap_ben = rng.binomial(m, q, T)
    tied = np.where(at_cap, n_cap_ben, 0)
    strict_cont = rng.binomial(np.maximum(m - n_cap_ben, 0), np.clip(1.0 - A, 0.0, 1.0))
    strict = np.where(at_cap, 0, n_cap_ben + strict_cont)
    return strict, tied, b_true


def _h0_level(q, m, f, *, clamp, N=181, T=80, trials=400, alpha=0.05, seed=1234):
    """Rejection rate under H0 when b is over-stated by the factor f."""
    cdf = _null_cdf(m, T, N)
    rng = np.random.default_rng(seed)
    rej = 0
    for _ in range(trials):
        strict, tied, b_true = _h0_draw(rng, q, N, m, T)
        b = np.maximum(1, np.round(b_true * f).astype(int))
        if clamp:
            b = np.minimum(b, N)
        s = int((strict + rng.binomial(tied, 1.0 / (b + 1.0))).sum())
        if (cdf[s] if s < len(cdf) else 1.0) <= alpha:
            rej += 1
    return rej / trials


def test_unclamped_b_inflation_is_the_documented_catastrophe():
    """Establish the defect is real before asserting the fix. With b over-stated 2x the
    exact test rejects a TRUE null 85% of the time at nominal 5%; 4x rejects always.

    This is the direction that produced the project's 99.6% false-positive rate, so it is
    pinned here as a fact about the statistic, not left implicit in the fix.
    """
    assert _h0_level(0.05, 80, 1, clamp=False) <= 0.06      # honest b: conservative
    assert _h0_level(0.05, 80, 2, clamp=False) > 0.5
    assert _h0_level(0.05, 80, 4, clamp=False) > 0.95


def test_h0_level_is_at_or_below_nominal_when_b_is_honest():
    """The calibration that actually exists: with a correct b the exact test is at or below
    its nominal level at every ceiling-atom mass and benign budget. Everything else in this
    section is about what happens when b is NOT correct."""
    for q, m in ((0.0, 80), (0.05, 80), (0.05, 30), (0.20, 80), (0.50, 80)):
        lvl = _h0_level(q, m, 1, clamp=False)
        assert lvl <= 0.05 + 1e-9, f"q={q} m={m}: H0 level {lvl} with an honest b"


def test_clamping_b_to_n_does_not_restore_calibration():
    """MEASURED FACT, pinned so a future reader does not mistake the clamp for a fix.

    b ~ Binomial(N, q) on saturated targets, so at a 5% atom the honest b is ~9 against
    N=181 and a 2x over-statement never comes near the clamp: the clamp fires on 0% of
    targets and the level stays at 0.87. Where it does fire (q=0.5) it still leaves ~0.92,
    because b=N drives the tie credit 1/(b+1) to zero — that is the STRICT rule, itself
    disqualified at H0 level 0.995 under a ceiling.

    Same idiom as tests/test_flip_test.py: assert the failure, so a silent "fix" that
    quietly re-uses the clamp as a calibration argument cannot slip through unvalidated.
    """
    # invisible to the clamp: 2x inflation of a small honest b
    assert _h0_level(0.05, 80, 2, clamp=True) > 0.5
    # visible to the clamp, and still nowhere near nominal
    assert _h0_level(0.50, 80, 4, clamp=True) > 0.5


def test_clamping_b_can_only_raise_the_p_value():
    """The safety property the clamp DOES provide: it is monotone in the right direction.

    Smaller b -> larger tie credit 1/(b+1) -> larger K -> larger S -> larger P(S <= s).
    So clamping can never manufacture significance, whatever the input. Checked through the
    shipped functions on the same tie-break seed, so the comparison is paired."""
    rng = np.random.default_rng(5)
    for trial in range(25):
        T = 12
        am = [CAP] * T
        bl = [list(np.where(rng.random(20) < 0.4, CAP, rng.random(20))) for _ in range(T)]
        tb = [int(rng.integers(1, 900)) for _ in range(T)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loose = exceedance_test(
                exceedance_counts_randomized(am, bl, tb, seed=trial), 181)
            tight = exceedance_test(
                exceedance_counts_randomized(am, bl, tb, n_attack_candidates=181,
                                             seed=trial), 181)
        assert tight["observed"] >= loose["observed"]
        assert tight["p_value"] >= loose["p_value"] - 1e-12


def test_tie_scale_sensitivity_reports_whether_b_drives_the_verdict():
    """Since the clamp cannot detect a merely-wrong b, the honest defence is to show how the
    p-value moves under a plausible error in it. Scaling b UP must weakly shrink p."""
    from se.stats import exceedance_test_over_tie_scales
    rng = np.random.default_rng(11)
    T = 30
    am = [CAP] * T
    bl = [list(np.where(rng.random(30) < 0.3, CAP, rng.random(30))) for _ in range(T)]
    r = exceedance_test_over_tie_scales(am, bl, [20] * T, 181, n_seeds=7)
    ps = [row["p_median"] for row in r["scales"]]
    assert all(ps[i] >= ps[i + 1] - 1e-12 for i in range(len(ps) - 1)), \
        "p must be non-increasing as b is scaled up (less tie credit -> smaller S)"
    assert r["p_at_measured_b"] == ps[2]
    assert isinstance(r["survives_half_b"], bool)
    assert isinstance(r["verdict_hinges_on_b"], bool)


def test_scalar_budget_clamps_conservatively_and_warns():
    attack = [CAP] * 3
    benign = [[CAP] * 10] * 3
    with pytest.warns(UserWarning, match="tie multiplicity above their candidate count"):
        counts = exceedance_counts_randomized(attack, benign, [500, 2, 900],
                                              n_attack_candidates=181, seed=0)
    a = counts.tie_audit
    assert a["checked"] is True and a["n_clamped_high"] == 2
    assert a["max_b_requested"] == 900 and a["max_b_used"] == 181
    assert a["worst_b_over_n"] == pytest.approx(900 / 181)
    assert [j for j, _, _ in a["examples_b_gt_n"]] == [0, 2]


def test_per_target_budget_raises_because_b_gt_n_is_impossible():
    """A per-target candidate count is authoritative: b counts candidates AT the maximum, so
    b > N_j cannot happen and is a data-integrity error, exactly like flip_test_conditional's
    impossible-2x2 guard. A scalar budget may be a summary, so that one clamps instead."""
    with pytest.raises(ValueError, match="only N=4 attack candidates"):
        exceedance_counts_randomized([CAP], [[CAP] * 5], [9], n_attack_candidates=[4])
    # ...and the same numbers pass silently when the budget is honest
    ok = exceedance_counts_randomized([CAP], [[CAP] * 5], [4], n_attack_candidates=[4])
    assert ok.tie_audit["n_clamped_high"] == 0


def test_on_violation_overrides():
    with pytest.raises(ValueError):
        exceedance_counts_randomized([CAP], [[CAP]], [9], n_attack_candidates=4,
                                     on_violation="raise")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = exceedance_counts_randomized([CAP], [[CAP]], [9], n_attack_candidates=[4],
                                         on_violation="clamp")
    assert c.tie_audit["max_b_used"] == 4
    with pytest.raises(ValueError):
        exceedance_counts_randomized([CAP], [[CAP]], [9], on_violation="nope")
    with pytest.raises(ValueError, match="silently truncate"):
        exceedance_counts_randomized([CAP, CAP], [[CAP], [CAP]], [1, 1],
                                     n_attack_candidates=[181])


def test_exceedance_test_flags_b_above_its_own_null_N():
    """The live trigger: scripts/null_control.py builds b per target but uses a single MEDIAN
    budget as N, so b > N is expected for roughly half the targets. The counts cannot be
    repaired inside the test, so it must at least refuse to look valid."""
    counts = exceedance_counts_randomized([CAP] * 2, [[CAP] * 5] * 2, [400, 1], seed=0)
    assert counts.tie_audit["checked"] is False              # no budget was supplied
    with pytest.warns(UserWarning, match="EXCEEDS THIS TEST'S N"):
        res = exceedance_test(counts, 181)
    assert res["tie_multiplicity_valid"] is False
    assert any("ANTI-CONSERVATIVE" in w for w in res["warnings"])
    # and the clean case says so positively
    clean = exceedance_counts_randomized([CAP] * 2, [[CAP] * 5] * 2, [40, 1],
                                         n_attack_candidates=181, seed=0)
    ok = exceedance_test(clean, 181)
    assert ok["tie_multiplicity_valid"] is True and ok["warnings"] == []


def test_hand_built_counts_report_unknown_rather_than_valid():
    """A plain list carries no audit. That must read as 'not checked', never as 'checked and
    fine' — an unverifiable input is not a passing input."""
    res = exceedance_test([(3, 30)] * 5, 181)
    assert res["tie_multiplicity_valid"] is None
    assert res["tie_multiplicity_checked"] is False
    assert exceedance_test([], 181)["tie_multiplicity_valid"] is None


def test_over_seeds_clamps_without_being_asked():
    """exceedance_test_over_seeds knows N, so the clamp is live there with no caller change
    — this is what protects the null_control code path that cannot be edited right now."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = exceedance_test_over_seeds([CAP] * 20, [[CAP, CAP, 0.1]] * 20, [500] * 20, 181,
                                       n_seeds=9)
    assert r["n_tie_clamped"] == 20
    assert r["tie_audit"]["max_b_used"] == 181
    # clamping b DOWN gives more tie credit -> larger K -> larger p: the safe direction
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        unclamped = exceedance_test(
            exceedance_counts_randomized([CAP] * 20, [[CAP, CAP, 0.1]] * 20, [500] * 20,
                                         seed=0), 181)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clamped = exceedance_test(
            exceedance_counts_randomized([CAP] * 20, [[CAP, CAP, 0.1]] * 20, [500] * 20,
                                         n_attack_candidates=181, seed=0), 181)
    assert clamped["observed"] >= unclamped["observed"]
    assert clamped["p_value"] >= unclamped["p_value"]


def test_counts_object_is_still_just_a_list_for_every_existing_caller():
    """scripts/null_control.py pipes the counts straight into exceedance_test and cannot be
    edited while the chain runs, so the return must stay list-compatible."""
    counts = exceedance_counts_randomized([0.5], [[0.1, 0.6, 0.7]], [3], seed=0)
    assert isinstance(counts, list)
    assert counts == [(2, 3)]
    assert list(counts) == [(2, 3)] and len(counts) == 1
    assert exceedance_test(counts, 181)["n_targets"] == 1
