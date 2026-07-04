"""Review-compliant reporting for attack campaigns (external review B4 + B2 nits).

Turns AttackOutcome records into the tables the review requires:
  - bootstrap CIs on every rate (B4);
  - the ATTRITION from the old entropy-only success to the B2 invariance-gated
    success (how many "wins" the answer-invariance check removed);
  - the ANSWER-FLIP subcategory (B2 nit 1): would-be wins voided because the
    model's correctness flipped under Q' — weak evidence the paraphrase shifted
    meaning, which feeds the NLI-fidelity / construct-validity concern (B5);
  - OPERATING-POINT flips at a clean-data threshold (B5/§6).

Torch-free on purpose: it reads already-computed AttackOutcome fields, so it is
unit-testable on synthetic outcomes without a GPU or the sample cache.

B2 nit 2 is baked in: `status_held` is only ever read among outcomes where
`entropy_and_feasible` is true; attacks that never triggered the Q' re-check do
not dilute the held/flip rates.
"""
from __future__ import annotations

from ..stats import (
    CI, rate_ci, operating_point, flips_at_threshold, success_rate_over_cutoffs,
)


def _intended_move(o) -> float:
    """Signed entropy move in the attack's intended direction (positive = helped
    the attacker): hide wants entropy DOWN, false-alarm wants it UP."""
    return (o.entropy_before - o.entropy_after) if o.attack == "hide" \
        else (o.entropy_after - o.entropy_before)


def summarize_cell(outcomes, *, cutoffs=(0.0, 0.1, 0.25, 0.5, 1.0)) -> dict:
    """Per-cell summary (one attack type, one detector). Single class, so the
    operating point is NOT computed here — see matrix_operating_point."""
    if not outcomes:
        return {"n": 0}
    attack = outcomes[0].attack
    detector = outcomes[0].detector
    n = len(outcomes)

    feasible = [bool(o.feasible) for o in outcomes]
    entropy_only = [bool(o.entropy_and_feasible) for o in outcomes]  # OLD criterion
    gated = [bool(o.success) for o in outcomes]                       # NEW (B2)

    # B2 nit 2: status is only meaningful among entropy_and_feasible outcomes.
    ef = [o for o in outcomes if o.entropy_and_feasible]
    n_ef = len(ef)
    held = sum(1 for o in ef if o.status_held)
    # B2 nit 1: answer-flip = would-be win voided by a correctness flip under Q'.
    answer_flip = sum(1 for o in ef if not o.status_held)

    n_entropy_only = sum(entropy_only)
    attrition = n_entropy_only - sum(gated)   # >= 0 by construction

    # B7 finding 16: the detector's SAMPLED fraction-correct under Q' (mean over the
    # re-checked outcomes), reported beside the greedy status. -1 = not computed.
    fracs = [getattr(o, "frac_correct_under_q_prime", -1.0) for o in ef]
    fracs = [f for f in fracs if f >= 0.0]
    mean_frac_correct_qp = (sum(fracs) / len(fracs)) if fracs else float("nan")

    # B7 finding 16 (critic entry 14, carry-forward b): a SAMPLED-status success gate.
    # The greedy status can disagree with the T=1.0 set the detector clusters, so a FA
    # "still correct" (or hide "still wrong") should hold on the MAJORITY of samples,
    # not just the greedy answer. Only defined when frac was computed (else conservative).
    def _sampled_held(o) -> bool | None:
        f = getattr(o, "frac_correct_under_q_prime", -1.0)
        if f < 0.0:
            return None
        return (f > 0.5) if attack == "false_alarm" else (f <= 0.5)
    have_frac = any(_sampled_held(o) is not None for o in outcomes)
    gated_sampled = [bool(o.entropy_and_feasible and _sampled_held(o) is True) for o in outcomes]
    success_gated_sampled = rate_ci(gated_sampled) if have_frac else None

    moves = [_intended_move(o) for o in outcomes]
    feas_moves = [m for m, f in zip(moves, feasible) if f]

    return {
        "attack": attack, "detector": detector, "n": n,
        "feasible_rate": rate_ci(feasible),
        "success_entropy_only": rate_ci(entropy_only),     # old (pre-B2) headline
        "success_gated": rate_ci(gated),                   # B2 headline
        "n_entropy_only": int(n_entropy_only),             # exact count (not rate*n)
        "attrition_count": int(attrition),
        "attrition_rate_of_would_be":
            (attrition / n_entropy_only) if n_entropy_only else 0.0,
        "n_entropy_and_feasible": n_ef,
        "status_held_rate_among_ef": (held / n_ef) if n_ef else float("nan"),
        "answer_flip_count": int(answer_flip),
        "answer_flip_rate_among_ef": (answer_flip / n_ef) if n_ef else float("nan"),
        "mean_frac_correct_qp": mean_frac_correct_qp,   # sampled status (finding 16)
        "success_gated_sampled": success_gated_sampled, # finding 16 gate (None if no frac)
        "mean_move_feasible":
            (sum(feas_moves) / len(feas_moves)) if feas_moves else float("nan"),
        "success_over_cutoffs": success_rate_over_cutoffs(moves, feasible, cutoffs),
    }


def matrix_operating_point(hide_outcomes, fa_outcomes, *, target_fpr: float = 0.1) -> dict:
    """Operating-point flips at a clean-data threshold (external review §6/B5).

    Needs BOTH classes so it is matrix-level, not per-cell: hide targets are the
    positives (model wrong), false-alarm targets the negatives (model right).
    clean score = entropy_before, attacked score = entropy_after. The threshold
    is set on the CLEAN negatives to a target FPR, then flips are counted."""
    labels = [1] * len(hide_outcomes) + [0] * len(fa_outcomes)
    clean = [o.entropy_before for o in hide_outcomes] + [o.entropy_before for o in fa_outcomes]
    attacked = [o.entropy_after for o in hide_outcomes] + [o.entropy_after for o in fa_outcomes]
    thr = operating_point(labels, clean, target_fpr=target_fpr)
    flips = flips_at_threshold(labels, clean, attacked, thr)
    flips["target_fpr"] = target_fpr
    # The threshold at a low FPR is set on few negatives -> noisy; surface it.
    flips["n_negatives_for_threshold"] = len(fa_outcomes)
    return flips


def matrix_operating_point_sweep(hide_outcomes, fa_outcomes,
                                 *, fprs=(0.05, 0.10, 0.20)) -> list[dict]:
    """Operating-point flips across a small FPR sweep (critic guidance on §6): a
    detector is a threshold family, not a point. Headline is 0.10; 0.05 sets the
    threshold on few negatives (noisy at n~200) and should be read with care."""
    return [matrix_operating_point(hide_outcomes, fa_outcomes, target_fpr=f)
            for f in fprs]


def matrix_answer_flip_breakdown(hide_outcomes, fa_outcomes) -> dict:
    """Split the answer-flip subcategory by DIRECTION at the matrix level (B2 nit
    1, critic guidance): the two directions are NOT symmetric evidence.

    hide -> became correct under Q' is the stronger meaning-shift signal (the NLI
    gate passed a Q' the model itself answers correctly, i.e. treats differently),
    and is the primary candidate for equivalence-gate leakage (B5). false_alarm ->
    became wrong is the mirror. Counted only among entropy_and_feasible outcomes
    (B2 nit 2)."""
    hide_ef = [o for o in hide_outcomes if o.entropy_and_feasible]
    fa_ef = [o for o in fa_outcomes if o.entropy_and_feasible]
    hide_became_correct = sum(1 for o in hide_ef if o.correct_under_q_prime)
    fa_became_wrong = sum(1 for o in fa_ef if not o.correct_under_q_prime)
    return {
        "hide_became_correct": int(hide_became_correct),
        "hide_ef_n": len(hide_ef),
        "hide_became_correct_rate":
            (hide_became_correct / len(hide_ef)) if hide_ef else float("nan"),
        "fa_became_wrong": int(fa_became_wrong),
        "fa_ef_n": len(fa_ef),
        "fa_became_wrong_rate":
            (fa_became_wrong / len(fa_ef)) if fa_ef else float("nan"),
    }


def _fmt_ci(ci: CI) -> str:
    return f"{ci.point:.3f} [{ci.lo:.3f}, {ci.hi:.3f}]"


def render_cell_md(summary: dict) -> list[str]:
    """Markdown lines for one cell summary. Leads with the B2-gated success and
    shows the entropy-only number beside it so the attrition is legible."""
    if summary.get("n", 0) == 0:
        return ["(no outcomes)"]
    s = summary
    n_ef = s["n_entropy_and_feasible"]
    # Guard the empty-entropy+feasible cell so a degenerate (e.g. all-infeasible)
    # cell does not emit "nan%" into a paper table.
    if n_ef:
        flip_str = (f"{s['answer_flip_count']}/{n_ef} of entropy+feasible "
                    f"({s['answer_flip_rate_among_ef']:.0%})")
    else:
        flip_str = "0/0 entropy+feasible (n/a — no re-checked attacks)"
    lines = [
        f"**{s['detector'].upper()} / {s['attack']}** (n={s['n']})",
        "",
        f"- success (B2 invariance-gated, greedy): {_fmt_ci(s['success_gated'])}",
        (f"- success (finding 16, sampled status): {_fmt_ci(s['success_gated_sampled'])}"
         if s.get("success_gated_sampled") is not None else
         "- success (finding 16, sampled status): n/a (frac not computed)"),
        f"- success (entropy-only, pre-B2): {_fmt_ci(s['success_entropy_only'])}",
        f"- attrition from B2: {s['attrition_count']} of {s['n_entropy_only']} "
        f"would-be wins ({s['attrition_rate_of_would_be']:.0%})",
        f"- of those, answer-flip subcategory (meaning-shift suspect): {flip_str}",
        (f"- sampled fraction-correct under Q' (finding 16): "
         f"{s['mean_frac_correct_qp']:.0%}"
         if s.get("mean_frac_correct_qp") == s.get("mean_frac_correct_qp")  # not nan
         and s.get("mean_frac_correct_qp", -1) >= 0 else
         "- sampled fraction-correct under Q' (finding 16): n/a (not yet computed)"),
        f"- feasible paraphrase rate: {_fmt_ci(s['feasible_rate'])}",
        f"- mean intended entropy move (feasible): {s['mean_move_feasible']:.3f} nats",
    ]
    return lines
