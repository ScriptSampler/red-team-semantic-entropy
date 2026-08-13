"""Round-provenance analysis of the attack's candidate set — NO GPU, from data on disk.

WHY. The randomised-tie exceedance test (`se.stats.exceedance_test`) assumes that under H0
a target's A ~ 181 attack candidates and its m benign draws are EXCHANGEABLE. They are not
obviously so: `optimizer.optimize` proposes children of the ORIGINAL question only in round
1; from round 2 the parents are previously-accepted candidates, so later candidates are
second-, third-, ... order rewrites, while every benign draw in `null_control` is a
single-hop rewrite of the original. If multi-hop candidates are more dispersed for reasons
unrelated to optimisation, the null is anti-conservative.

`scripts/null_objective_ablation.py` settles that empirically and needs GPU. This module
answers the part that needs NONE: given only `trajectory_best_obj`, `feasible_objs` and
`n_feasible_at_best` from a completed campaign, HOW MUCH of the statistic's input is
multi-hop at all? Two quantities carry the exceedance test:

  * the attack MAX — set in the round where `trajectory_best_obj` last rises. If that is
    round 1, the winning candidate is a single-hop rewrite of the original, drawn from
    exactly the benign generating process, and the exchangeability worry cannot touch it.
  * the tie multiplicity b (`n_feasible_at_best`) — each benign draw tied at the max earns
    credit 1/(b+1), so b divides the evidence. An over-stated b is the documented
    anti-conservative direction (`exceedance_counts_randomized`: H0 level 0.85 at 2x b).

IDENTIFICATION. `feasible_objs` is appended in iteration order but carries no round labels,
and after the trajectory plateaus every entry equals the running max, so the exact per-round
counts are NOT identified from values alone. What IS identified is a bound, and it is sharp
enough to matter: each iteration proposes exactly `top_N * candidate_size_M` = 9 children, so
at most 9 entries can come from any one round. With t0 = the round that first achieved the
max (no tie member can predate it — a feasible candidate at the final max would have raised
the trajectory), at most 9*(r - t0) tie members lie in rounds [t0, r), hence

    #tie members from rounds >= r  >=  max(0, b - 9*(r - t0)).

`min_entries_from_round` computes the exact minimum by DP over all segmentations consistent
with the trajectory, which is never looser than that counting bound and is often tighter.

WHAT THIS CANNOT DO. It cannot say whether multi-hop candidates are distributionally
DIFFERENT — only how much of the statistic rests on them. A round effect in the values would
be uninterpretable anyway: it is exactly as consistent with the optimiser working (H1, the
thing we hope for) as with drift (H0 violated). Separating those two requires the objective
to be switched off, which is the GPU ablation. Read this as sizing the exposure, not as the
gate. See results/null_objective_ablation_plan.md.

    python scripts/round_drift_analysis.py --cell false_alarm --tag _defb
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TOL = 1e-9
PER_ROUND = 9          # top_N (3) * candidate_size_M (3): children proposed each iteration


# --------------------------------------------------------------------------- identification


def first_max_round(traj: list[float], *, tol: float = TOL) -> int:
    """1-based iteration in which the running best FIRST reached its final value.

    `traj[0]` is the clean baseline and `traj[t]` the best after iteration t, so a return of
    0 means the optimiser never improved on the original and there is no attack candidate at
    the max. Returns 1 when the max was set by a single-hop rewrite of the original — the
    case in which the exchangeability question does not touch the max at all."""
    if not traj:
        return 0
    best = max(traj)
    for t, v in enumerate(traj):
        if v >= best - tol:
            return t
    return 0


def counting_bound(b: int, t0: int, r: int, *, per_round: int = PER_ROUND) -> int:
    """Lower bound on tie members from rounds >= r, from the per-round proposal cap alone.

    No tie member predates t0 (a feasible candidate at the final max would have raised the
    trajectory), and rounds t0..r-1 hold at most `per_round` each."""
    if r <= t0:
        return int(b)
    return max(0, int(b) - per_round * (r - t0))


def _round_transitions(objs: list[float], traj: list[float], *, per_round: int, tol: float):
    """Valid (prefix_before, prefix_after) block boundaries for each 1-based round.

    Round r consumes a contiguous block of `objs`; every entry must be >= traj[r-1] (the
    `c.obj >= best_obj` filter used the round's ENTRY value of best_obj) and the block's max,
    taken with traj[r-1], must equal traj[r]. Returns trans[r] = {p: [q, ...]}."""
    n_rounds = len(traj) - 1
    L = len(objs)
    # prefix maxima of arbitrary windows: L is small (<= a few hundred), so scan directly.
    trans: list[dict[int, list[int]]] = [dict() for _ in range(n_rounds + 1)]
    for r in range(1, n_rounds + 1):
        lo, hi = traj[r - 1], traj[r]
        for p in range(L + 1):
            outs = []
            run_max = -math.inf
            for q in range(p, min(p + per_round, L) + 1):
                if q > p:
                    v = objs[q - 1]
                    if v < lo - tol:
                        break
                    run_max = max(run_max, v)
                if abs(max(run_max, lo) - hi) <= tol:
                    outs.append(q)
            if outs:
                trans[r][p] = outs
    return trans


def min_entries_from_round(objs, traj, r_min: int, *, predicate=None,
                           per_round: int = PER_ROUND, tol: float = TOL) -> int | None:
    """Exact minimum, over every segmentation of `objs` consistent with `traj`, of the number
    of entries satisfying `predicate` that land in a round >= `r_min`.

    Returns None when no consistent segmentation exists (which would mean the record and the
    optimiser's documented behaviour disagree — worth knowing, so it is not silenced).
    `predicate` defaults to counting every entry."""
    pred = predicate or (lambda v: True)
    L, n_rounds = len(objs), len(traj) - 1
    trans = _round_transitions(objs, traj, per_round=per_round, tol=tol)
    # cost[p:q] under this round = entries matching the predicate, charged only if r >= r_min
    marks = [1 if pred(v) else 0 for v in objs]
    cum = [0]
    for m in marks:
        cum.append(cum[-1] + m)

    INF = math.inf
    dp = [INF] * (L + 1)
    dp[0] = 0.0
    for r in range(1, n_rounds + 1):
        nxt = [INF] * (L + 1)
        charge = r >= r_min
        for p, outs in trans[r].items():
            if dp[p] == INF:
                continue
            for q in outs:
                c = dp[p] + ((cum[q] - cum[p]) if charge else 0)
                if c < nxt[q]:
                    nxt[q] = c
        dp = nxt
    return None if dp[L] == INF else int(dp[L])


# --------------------------------------------------------------------------- per target


def analyse_target(rec: dict, *, per_round: int = PER_ROUND, tol: float = TOL,
                   n_samples: int = 10, exact_dp: bool = True) -> dict:
    """Round-provenance summary for one AttackOutcome record."""
    traj = [float(x) for x in (rec.get("trajectory_best_obj") or [])]
    objs = [float(x) for x in (rec.get("feasible_objs") or [])]
    b_rec = int(rec.get("n_feasible_at_best") or 0)
    out: dict = {
        "question_id": rec.get("question_id"),
        "n_rounds": max(0, len(traj) - 1),
        "n_feasible": len(objs),
        "b_recorded": b_rec,
        "improved": bool(rec.get("improved")),
    }
    if not traj:
        out["status"] = "no trajectory"
        return out
    best = max(traj)
    t0 = first_max_round(traj)
    b_derived = sum(1 for v in objs if abs(v - best) <= tol)
    out.update({
        "clean_obj": traj[0],
        "best_obj": best,
        "move": best - traj[0],
        "first_max_round": t0,
        "b_derived": b_derived,
        "b_matches_record": b_derived == b_rec,
        "n_traj_rises": sum(1 for a, c in zip(traj, traj[1:]) if c > a + tol),
        "saturated": best >= math.log(n_samples) - 1e-6,
        "max_is_single_hop": t0 == 1,
        "never_improved": t0 == 0,
    })
    # exposure of the tie set to multi-hop candidates
    out["tie_min_multihop_count"] = counting_bound(b_derived, max(t0, 1), 2, per_round=per_round)
    out["feas_min_multihop_count"] = max(0, len(objs) - per_round)
    # t0 == 0 (the optimiser never improved) still segments: the "max" is the clean score and
    # candidates tying it are real tie-set members, so the DP must run there too.
    if exact_dp and objs:
        out["tie_min_multihop_dp"] = min_entries_from_round(
            objs, traj, 2, predicate=lambda v: abs(v - best) <= tol, per_round=per_round, tol=tol)
        out["feas_min_multihop_dp"] = min_entries_from_round(
            objs, traj, 2, per_round=per_round, tol=tol)
    return out


def summarise(rows: list[dict], *, m: int = 50, A: int = 181,
              per_round: int = PER_ROUND) -> dict:
    """Aggregate the per-target rows into the numbers the plan quotes."""
    live = [r for r in rows if r.get("b_derived") is not None and r.get("n_rounds")]
    n = len(live)
    if not n:
        return {"n": 0}
    tied = [r for r in live if r["b_derived"] > 0]

    def frac(pred, pool=live):
        return (sum(1 for r in pool if pred(r)) / len(pool)) if pool else float("nan")

    def best_bound(r, key_dp, key_count):
        dp = r.get(key_dp)
        return max(int(r[key_count]), int(dp)) if dp is not None else int(r[key_count])

    tie_mh = [best_bound(r, "tie_min_multihop_dp", "tie_min_multihop_count") for r in tied]
    b_all = [r["b_derived"] for r in tied]
    tot_b, tot_mh = sum(b_all), sum(tie_mh)
    mean_b = tot_b / len(tied) if tied else 0.0
    # tie credit now, vs the credit a single-hop-only candidate pool could ever produce
    credit_now = sum(1.0 / (max(1, b) + 1) for b in b_all) / len(tied) if tied else float("nan")
    credit_sh = (sum(1.0 / (min(max(1, b), per_round) + 1) for b in b_all) / len(tied)
                 if tied else float("nan"))
    return {
        "n": n,
        "n_with_ties": len(tied),
        "frac_never_improved": frac(lambda r: r["never_improved"]),
        "frac_max_single_hop": frac(lambda r: r["max_is_single_hop"]),
        "frac_max_multi_hop": frac(lambda r: r["first_max_round"] >= 2),
        "median_first_max_round": sorted(r["first_max_round"] for r in live)[n // 2],
        "mean_traj_rises": sum(r["n_traj_rises"] for r in live) / n,
        "frac_saturated": frac(lambda r: r["saturated"]),
        "mean_b": mean_b,
        "max_b": max(b_all) if b_all else 0,
        "total_b": tot_b,
        "total_tie_multihop_min": tot_mh,
        "frac_tie_mass_multihop_min": tot_mh / tot_b if tot_b else float("nan"),
        "frac_targets_tie_forced_multihop": frac(lambda r: r["b_derived"] > per_round, tied),
        "mean_tie_credit_now": credit_now,
        "mean_tie_credit_single_hop_cap": credit_sh,
        "tie_credit_ratio": (credit_sh / credit_now) if credit_now else float("nan"),
        "b_record_mismatches": sum(1 for r in live if not r.get("b_matches_record", True)),
        # Only targets that HAVE feasible candidates are segmented; a missing key means the
        # DP was never asked, which is not the same as "no consistent segmentation exists".
        # Conflating the two would silently report a model/record disagreement that isn't one.
        "dp_infeasible": sum(1 for r in live
                             if r["n_feasible"] and r.get("tie_min_multihop_dp") is None),
        "n_no_feasible": sum(1 for r in live if not r["n_feasible"]),
        # the pre-committed gate's arithmetic, restated at the deployed design
        "m": m, "A": A,
        "expected_K_per_target": m / (A + 1),
        "band_lo": 0.5 * m / (A + 1),
        "band_hi": 2.0 * m / (A + 1),
        "expected_S_total": n * m / (A + 1),
    }


# --------------------------------------------------------------------------- cli


def load_cell(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="", help="explicit JSONL; overrides --tag/--cell")
    ap.add_argument("--tag", default="_defb")
    ap.add_argument("--cell", default="false_alarm", choices=["false_alarm", "hide"])
    ap.add_argument("--detector", default="se")
    ap.add_argument("--m", type=int, default=50, help="benign draws per target (null control K)")
    ap.add_argument("--A", type=int, default=181, help="attack candidate count in the null")
    ap.add_argument("--no_dp", action="store_true", help="skip the exact segmentation DP")
    ap.add_argument("--json_out", default="")
    args = ap.parse_args()

    if args.path:
        p = Path(args.path)
    else:
        from se.sampling import DEFAULT_SAMPLES_DIR
        p = (DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
             / f"triviaqa_{args.detector}_{args.cell}.jsonl")
    recs = load_cell(p)
    rows = [analyse_target(r, exact_dp=not args.no_dp) for r in recs]
    s = summarise(rows, m=args.m, A=args.A)

    print(f"[cell] {p}  n={len(recs)}")
    print(f"  targets analysed            {s['n']}")
    print(f"  never improved              {s['frac_never_improved']:.1%}")
    print(f"  MAX set in round 1 (1-hop)  {s['frac_max_single_hop']:.1%}")
    print(f"  MAX set in round >= 2       {s['frac_max_multi_hop']:.1%}  "
          f"(median first-max round {s['median_first_max_round']})")
    print(f"  mean trajectory rises       {s['mean_traj_rises']:.2f} of 20 rounds")
    print(f"  saturated at log N          {s['frac_saturated']:.1%}")
    print(f"  mean tie multiplicity b     {s['mean_b']:.1f}   (max {s['max_b']})")
    print(f"  b > {PER_ROUND} => ties MUST be multi-hop: {s['frac_targets_tie_forced_multihop']:.1%} "
          f"of tied targets")
    print(f"  tie mass provably multi-hop {s['total_tie_multihop_min']}/{s['total_b']} = "
          f"{s['frac_tie_mass_multihop_min']:.1%}  (lower bound)")
    print(f"  mean tie credit 1/(b+1)     {s['mean_tie_credit_now']:.4f}  vs single-hop-capped "
          f"{s['mean_tie_credit_single_hop_cap']:.4f}  ({s['tie_credit_ratio']:.1f}x)")
    print(f"  b vs record mismatches      {s['b_record_mismatches']}")
    print(f"  E[K] per target = m/(A+1)   {s['expected_K_per_target']:.4f}  "
          f"band [{s['band_lo']:.4f}, {s['band_hi']:.4f}]  "
          f"E[S] over {s['n']} targets = {s['expected_S_total']:.1f}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"summary": s, "targets": rows}, indent=1),
                                       encoding="utf-8")
        print(f"[json] wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
