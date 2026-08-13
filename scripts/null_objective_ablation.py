"""Null-objective beam ablation — THE VALIDITY GATE for the exceedance test.

QUESTION. The claim statistic (`se.stats.exceedance_test`) assumes that under H0 a target's
A ~ 181 attack candidates and its m benign draws are EXCHANGEABLE draws from one F. They are
not obviously so. `optimizer.optimize` proposes children of the ORIGINAL question only in
round 1; from round 2 the parents are previously-accepted candidates, so late candidates are
second- and third-order rewrites, while every benign draw in `null_control` is a single-hop
rewrite of the original. Two opposing failure modes, net sign empirical (critique_log 23):
  multi-hop drift    late candidates are more dispersed for reasons unrelated to
                     optimisation -> the null under-states the attack arm -> ANTI-conservative
  beam clustering    the beam revisits a small region -> fewer effective draws -> conservative
The exposure is large and already measured with no GPU: on the `_defb` FA cell at least
91.8% of the tie multiplicity b (which divides the tie credit 1/(b+1)) provably comes from
round >= 2, and 46% of targets set their maximum in a multi-hop round.
See `scripts/round_drift_analysis.py` and `results/null_objective_ablation_plan.md`.

DESIGN (paired per target, self-contained). Hold the search PROCEDURE fixed and remove only
the optimisation signal:
  arm CONCENTRATED  the IDENTICAL optimiser (same beam width, budget, proposer, NLI
                    feasibility gate) with a NULL objective — a deterministic hash of the
                    candidate string: a fixed pure-noise landscape with zero detector signal.
                    Every proposed candidate is recorded AS A MULTISET (duplicates are real:
                    the proposer decodes greedily, so it repeats itself, and the deployed
                    null counts A = 181 CALLS, not distinct strings). Feasible candidates are
                    scored at the standard seed-0 config; the maximum is `null_beam_max` and
                    the number of feasible calls achieving it is `b_null` — the same quantity
                    the optimiser records as `n_feasible_at_best`.
  arm DIFFUSE       benign draws generated exactly as `null_control._benign_moves_arms` does
                    (single-hop from the original, feasibility-gated, duplicates KEPT, m
                    feasible or 5m tries), or read straight from the null control's own
                    `--dump_diag` file with `--benign_from`, which is preferred: the gate is
                    then evaluated against the very lists the claim statistic will use.

THE GATE (critique_log 23, pre-committed before any ablation data):
  Feed (null_beam_max, benign list, b_null) to the randomised-tie exceedance test and read
  the mean exceedance count Kbar against the theoretical m/(A+1). PASS iff the ratio lies in
  [0.5, 2.0]. Materially BELOW -> the null-objective beam beats benign more than chance ->
  the theoretical null is anti-conservative -> fall back to the prefix statistic or to an
  empirical null built from this ablation's own K distribution. ABOVE -> conservative.
  ⚠ The ratio is CONTAMINATED by the arms' different duplication rates, which inflate it
  under a true null with no drift at all (measured: 1.4x at 73 distinct attack strings of
  181, 2.6x at 40 — `scripts/duplication_level_sim.py`). So the gate is read against a
  duplication-adjusted centre computed from THIS RUN's own distinct-string counts, which is
  why `n_beam_unique` / `n_diffuse_unique` are recorded. Do not read the raw ratio.
  The paired nats comparison (`paired_summary`) is retained as a SECONDARY diagnostic; it
  was the original B2 framing and it is not the pre-committed gate quantity.

SCOPE. Scored under the NLI clusterer: the attack optimises the NLI-entropy objective, so
the H0 selection concern lives in NLI-objective space; clusterer attribution is a separate
question (the 4-arm null control). ~2.5-4.5 min/target (the objective is free, so this is
~4x cheaper per target than the real attack); per-target checkpoint JSONL makes it resumable.

  ./.venv-wsl/bin/python scripts/null_objective_ablation.py --tag _defb --n_targets 80 \
      --m 50 --benign_from results/diag_defb.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR          # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR            # noqa: E402
from se.stats import (bootstrap_ci, exceedance_counts_randomized,   # noqa: E402
                      exceedance_test)

# Records written before the multiset fix (2026-08-13) deduplicated the beam before counting
# the tie multiplicity, so their b is not the quantity the exceedance test needs. Resuming
# across that change would silently mix two definitions of b, which is exactly the failure
# the `_def` -> `_defb` retag existed to prevent — so old records are refused, loudly.
SCHEMA = 2


def hash01(q: str) -> float:
    """Deterministic pure-noise objective: md5(query) -> [0, 1). Zero detector signal;
    fixed per candidate, so the beam concentrates exactly as it would on a fixed noisy
    landscape (the H0 the critic asked us to bound)."""
    return int(hashlib.md5(q.encode("utf-8")).hexdigest()[:8], 16) / float(0xFFFFFFFF)


def paired_summary(records: list[dict]) -> dict:
    """Paired verdict across targets. Each record: {null_beam_max, random_max, ...}.
    Skips targets where either arm produced no feasible candidate (max is None)."""
    pairs = [(r["null_beam_max"], r["random_max"]) for r in records
             if r.get("null_beam_max") is not None and r.get("random_max") is not None]
    if not pairs:
        return {"n": 0, "diff_ci": None, "verdict": "no paired data"}
    diffs = [a - b for a, b in pairs]
    ci = bootstrap_ci(diffs, np.mean)
    if ci.lo > 0.05:
        verdict = ("BEAM INFLATES UNDER H0: the concentrated null-objective beam reaches "
                   "higher maxima than diffuse random search of the same budget "
                   f"(paired diff {ci.point:+.3f} [{ci.lo:+.3f}, {ci.hi:+.3f}] nats). The "
                   "diffuse budget-matched floor UNDER-estimates the null — use the "
                   "null-beam-max as the floor (or subtract this inflation).")
    elif ci.hi < 0.05 or (ci.lo <= 0 <= ci.hi):
        verdict = ("SAFE: null-objective beam-max ~ diffuse random-max (paired diff "
                   f"{ci.point:+.3f} [{ci.lo:+.3f}, {ci.hi:+.3f}] nats). Beam concentration "
                   "does not materially inflate the max under H0; the diffuse "
                   "budget-matched benign-max floor stands.")
    else:
        verdict = (f"MARGINAL (paired diff {ci.point:+.3f} [{ci.lo:+.3f}, {ci.hi:+.3f}]): "
                   "report both floors and read the attack against the more conservative.")
    return {"n": len(pairs), "diff_ci": ci, "verdict": verdict}


# --------------------------------------------------------------------------- THE GATE


def gate_summary(records: list[dict], A: int, *, band=(0.5, 2.0), n_seeds: int = 51) -> dict:
    """The entry-23 pre-committed gate: is Kbar within [0.5x, 2.0x] of m/(A+1)?

    Each record supplies the null-objective arm's maximum, its tie multiplicity b, and that
    target's benign move list. Under H0-with-exchangeability the randomised-tie exceedance
    count has E[K_j] = m_j/(A+1) EXACTLY, atoms included: with random tie-breaking each of
    the A+1 relevant draws is equally likely to rank top. So the band's centre survives the
    conservative -> randomised tie-rule change unaltered; what it does NOT survive is a
    per-target m_j that falls short of the requested m, so the ratio is taken against
    sum_j m_j/(A+1) rather than against n * m/(A+1).

    Averaged over `n_seeds` tie-break realisations because K is randomised; the SPREAD is
    reported and each individual draw is what the test itself consumes (averaging is only
    safe here because this is a descriptive ratio, not a p-value — see the warning in
    `exceedance_counts_randomized`)."""
    rows = [r for r in records
            if r.get("null_beam_max") is not None and (r.get("benign_moves") or [])]
    if not rows:
        return {"n": 0, "verdict": "no gate data (need null_beam_max + a benign list)"}
    amax = [float(r["null_beam_max"]) for r in rows]
    blists = [[float(x) for x in r["benign_moves"]] for r in rows]
    bmul = [max(1, int(r.get("b_null") or 1)) for r in rows]
    m_tot = sum(len(bl) for bl in blists)
    expected = m_tot / (A + 1)

    obs, ps = [], []
    for s in range(int(n_seeds)):
        counts = exceedance_counts_randomized(amax, blists, bmul, n_attack_candidates=A, seed=s)
        res = exceedance_test(counts, A)
        obs.append(res["observed"])
        ps.append(res["p_value"])
    obs_mean = float(np.mean(obs))
    ratio = obs_mean / expected if expected else float("nan")
    lo, hi = band
    if ratio < lo:
        verdict = ("FAIL-LOW — the null-objective beam beats the benign arm MORE than chance "
                   f"(Kbar ratio {ratio:.2f} < {lo}). The theoretical null is "
                   "ANTI-CONSERVATIVE: the exceedance test may not be the primary statistic. "
                   "Fall back per the pre-commitment.")
    elif ratio > hi:
        verdict = (f"FAIL-HIGH — Kbar ratio {ratio:.2f} > {hi}. The theoretical null is "
                   "CONSERVATIVE. Check the duplication offset FIRST (n_beam_unique): a true "
                   "null with no drift already produces ~1.4x at 73 distinct strings of 181.")
    else:
        verdict = (f"PASS — Kbar ratio {ratio:.2f} within [{lo}, {hi}]; exchangeability is "
                   "not detectably violated at this n. Read against the duplication offset.")
    return {
        "n": len(rows), "A": A, "m_total": m_tot,
        "expected_S": expected, "observed_S_mean": obs_mean,
        "observed_S_range": (int(min(obs)), int(max(obs))),
        "Kbar": obs_mean / len(rows), "Kbar_expected": expected / len(rows),
        "ratio": ratio, "band": band,
        "p_median": float(np.median(ps)), "p_range": (float(min(ps)), float(max(ps))),
        "mean_b_null": float(np.mean(bmul)),
        "verdict": verdict,
    }


def load_benign_from_diag(path: Path, arm: str = "nli") -> dict[str, list[float]]:
    """question_id -> benign move list, from `null_control.py --dump_diag`. Preferred over
    re-drawing: the gate is then evaluated against the very lists the claim statistic uses."""
    recs = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, list[float]] = {}
    for r in recs:
        vals = ((r.get("benign") or {}).get(arm)) or []
        vals = [float(v) for v in vals if v is not None]
        if vals:
            out[r["question_id"]] = vals
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_def")
    ap.add_argument("--n_targets", type=int, default=10)
    ap.add_argument("--max_iteration", type=int, default=20, help="beam iterations (match the attack)")
    ap.add_argument("--candidate_size_M", type=int, default=3, help="children per parent (match)")
    ap.add_argument("--top_N", type=int, default=3, help="beam width (match)")
    ap.add_argument("--checkpoint", default="auto",
                    help="'auto' -> results/null_objective_ablation_ckpt<tag>.jsonl; '' off")
    ap.add_argument("--m", type=int, default=50,
                    help="benign draws per target; must equal the null control's --K")
    ap.add_argument("--benign_from", default="",
                    help="null_control --dump_diag JSON; use ITS benign lists instead of "
                         "re-drawing (preferred: the gate then uses the claim's own arm)")
    ap.add_argument("--no_diffuse", action="store_true",
                    help="skip drawing a benign arm (only valid with --benign_from)")
    args = ap.parse_args()

    from se.attacks.harness import load_pair, read_outcomes, _stable_seed
    from se.attacks import proposer, feasibility
    from se.attacks.optimizer import optimize
    from se.se_pipeline import semantic_entropy
    from se.entropy import cluster_and_score_exact

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    f = campaign_dir / "triviaqa_se_false_alarm.jsonl"
    outcomes = sorted(read_outcomes(f), key=lambda o: o.question_id)[: args.n_targets]
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    pair = load_pair()
    budget = 1 + args.max_iteration * args.candidate_size_M * args.top_N  # objective calls
    print(f"[load] {len(outcomes)} FA targets; per-arm budget ~{budget} candidates", flush=True)

    ckpt_path = (RESULTS_DIR / f"null_objective_ablation_ckpt{args.tag}.jsonl"
                 if args.checkpoint == "auto" else (Path(args.checkpoint) if args.checkpoint else None))
    benign_by_qid = (load_benign_from_diag(Path(args.benign_from)) if args.benign_from else {})
    if args.benign_from:
        print(f"[benign] {len(benign_by_qid)} target(s) from {args.benign_from}", flush=True)
    elif args.no_diffuse:
        raise SystemExit("--no_diffuse needs --benign_from: the gate has no benign arm otherwise")

    done: dict[str, dict] = {}
    stale = 0
    if ckpt_path is not None and ckpt_path.exists():
        for line in ckpt_path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if int(r.get("schema") or 1) < SCHEMA:
                stale += 1
                continue
            done[r["question_id"]] = r
        print(f"[ckpt] {len(done)} target(s) already done", flush=True)
        if stale:
            print(f"[ckpt] ⚠ IGNORING {stale} pre-schema-{SCHEMA} record(s): their b was "
                  f"counted over DEDUPLICATED candidates, which is not the tie multiplicity "
                  f"the exceedance test consumes. Re-run those targets.", flush=True)

    # entropy cache per unique query string (proposer repeats itself; both arms share it)
    ent_cache: dict[str, tuple[float, float]] = {}

    def score(q: str) -> tuple[float, float]:
        """(nli_entropy, exact_entropy) at the standard seed-0 config."""
        if q not in ent_cache:
            res = semantic_entropy(q, pair.lm, pair.nli, gen)
            ent_cache[q] = (res.entropy_nats, cluster_and_score_exact(res.samples).entropy_nats)
        return ent_cache[q]

    records = list(done.values())
    for o in outcomes:
        if o.question_id in done:
            continue
        base_nli, base_exact = score(o.question)

        # --- arm CONCENTRATED: identical beam, null (hash) objective -----------------
        seen: list[str] = []

        def null_obj(q: str) -> float:
            seen.append(q)
            return hash01(q)

        proposer.seed_proposer(_stable_seed("ablate:" + o.question_id))
        optimize(o.question, null_obj, pair.lm, pair.nli,
                 max_iteration=args.max_iteration, candidate_size_M=args.candidate_size_M,
                 top_N=args.top_N)
        # THE MULTISET IS THE UNIT, NOT THE SET. `seen` is every objective CALL, and the
        # deployed null counts A = 181 calls; the optimiser likewise counts b over calls
        # (`n_feasible_at_best` is incremented per gated candidate, duplicates included).
        # Deduplicating here — as this script did until 2026-08-13 — under-counts b against
        # a null that does not, which inflates the tie credit 1/(b+1) and makes the gate
        # look conservative when it is not. Gate and score each DISTINCT string once (the
        # expensive part), then expand back over the calls.
        beam_calls = [q for q in seen if q != o.question]
        beam_uniq = list(dict.fromkeys(beam_calls))
        feas_ok = {q: feasibility.check(q, o.question, pair.nli).feasible for q in beam_uniq}
        beam_moves = [score(q)[0] - base_nli for q in beam_calls if feas_ok[q]]
        null_beam_max = max(beam_moves) if beam_moves else None
        b_null = (sum(1 for v in beam_moves if abs(v - null_beam_max) <= 1e-9)
                  if null_beam_max is not None else 0)

        # --- arm DIFFUSE: the benign arm, generated as null_control generates it --------
        # Single-hop from the ORIGINAL, feasibility-gated, DUPLICATES KEPT, m feasible or
        # 5m tries (`null_control._benign_moves_arms`). The old version drew only as many
        # raw candidates as the beam had DISTINCT ones (73 vs 181 on the one target on
        # disk) and then deduplicated, so the two maxima were taken over budgets differing
        # by ~4x — an asymmetry that mechanically favours the beam.
        diff_moves: list[float] = []
        n_diffuse_tries, diffuse_uniq = 0, set()
        if args.benign_from and o.question_id in benign_by_qid:
            diff_moves = list(benign_by_qid[o.question_id])
            benign_src = "diag"
        elif args.no_diffuse:
            benign_src = "missing"
        else:
            benign_src = "drawn"
            proposer.seed_proposer(_stable_seed("diffuse:" + o.question_id))
            while len(diff_moves) < args.m and n_diffuse_tries < args.m * 5:
                n_diffuse_tries += 1
                cand = proposer.propose(o.question, pair.lm)
                if cand == o.question or not feasibility.check(cand, o.question,
                                                               pair.nli).feasible:
                    continue
                diffuse_uniq.add(cand)
                diff_moves.append(score(cand)[0] - base_nli)
        random_max = max(diff_moves) if diff_moves else None

        rec = {
            "schema": SCHEMA,
            "question_id": o.question_id, "question": o.question,
            "real_attack_move": o.entropy_after - o.entropy_before,
            "real_b": int(getattr(o, "n_feasible_at_best", 0) or 0),
            "n_beam_calls": len(beam_calls), "n_beam_unique": len(beam_uniq),
            "n_beam_feasible_unique": sum(1 for v in feas_ok.values() if v),
            "n_beam_feasible_calls": len(beam_moves),
            "n_diffuse_tries": n_diffuse_tries, "n_diffuse_unique": len(diffuse_uniq),
            "benign_source": benign_src,
            "null_beam_max": null_beam_max, "b_null": b_null, "random_max": random_max,
            "beam_moves": beam_moves, "diffuse_moves": diff_moves,
            "benign_moves": diff_moves,          # what gate_summary consumes
        }
        records.append(rec)
        if ckpt_path is not None:
            ckpt_path.parent.mkdir(parents=True, exist_ok=True)
            with ckpt_path.open("a", encoding="utf-8") as cf:
                cf.write(json.dumps(rec, default=float) + "\n")
                cf.flush()
        print(f"  {o.question_id}: null-beam-max "
              f"{'n/a' if null_beam_max is None else f'{null_beam_max:+.3f}'} "
              f"(b={b_null}; {len(beam_moves)} feasible calls, {len(beam_uniq)} distinct of "
              f"{len(beam_calls)}) vs random-max "
              f"{'n/a' if random_max is None else f'{random_max:+.3f}'} "
              f"(m={len(diff_moves)}, {benign_src}) | real attack "
              f"{rec['real_attack_move']:+.3f} (b={rec['real_b']})", flush=True)

    s = paired_summary(records)
    g = gate_summary(records, budget)
    uniq = [r["n_beam_unique"] / max(1, r["n_beam_calls"]) for r in records
            if r.get("n_beam_calls")]
    L = ["# Null-objective beam ablation — the exceedance test's validity gate", "",
         f"n={g.get('n', 0)} FA targets; attack-arm budget A={budget} objective calls; "
         f"m={args.m} benign draws/target; NLI-clusterer scoring at the standard seed-0 "
         "config (the objective the attack optimises).", "",
         "## THE GATE (critique_log 23, pre-committed)", ""]
    if g.get("n"):
        L += [f"- expected exceedances under H0: S = sum m_j/(A+1) = **{g['expected_S']:.2f}** "
              f"(Kbar = {g['Kbar_expected']:.4f} per target)",
              f"- observed (mean over 51 tie-break seeds): S = **{g['observed_S_mean']:.2f}** "
              f"(range {g['observed_S_range'][0]}-{g['observed_S_range'][1]}), "
              f"Kbar = {g['Kbar']:.4f}",
              f"- **ratio {g['ratio']:.2f}**, band [{g['band'][0]}, {g['band'][1]}]",
              f"- mean tie multiplicity b of the NULL arm: {g['mean_b_null']:.1f}",
              f"- exceedance-test p on the null arm (should NOT be small): median "
              f"{g['p_median']:.3f}, range [{g['p_range'][0]:.3f}, {g['p_range'][1]:.3f}]",
              "",
              f"**VERDICT**: {g['verdict']}", ""]
    else:
        L += [f"- {g['verdict']}", ""]
    if uniq:
        L += ["## Duplication offset (read the ratio against this, not against 1.0)", "",
              f"- distinct beam strings per call: mean {float(np.mean(uniq)):.2f} "
              f"(min {min(uniq):.2f}, max {max(uniq):.2f}) of A={budget}",
              f"- mean distinct benign strings: "
              f"{float(np.mean([r.get('n_diffuse_unique', 0) for r in records])):.1f}",
              "- feed these to `scripts/duplication_level_sim.py` to get the ratio a TRUE "
              "null with no drift produces at these rates, and read the gate against that.",
              ""]
    L += ["## Secondary diagnostic — the original B2 nats comparison", "",
          "Per target: null-beam-max (concentrated proposals, hash objective) vs random-max "
          "(diffuse proposals, matched budget) vs the real attack's move (context only):", ""]
    for r in sorted(records, key=lambda r: r["question_id"]):
        nb = "n/a" if r.get("null_beam_max") is None else f"{r['null_beam_max']:+.3f}"
        rm = "n/a" if r.get("random_max") is None else f"{r['random_max']:+.3f}"
        L.append(f"- {r['question_id']}: null-beam {nb} (b={r.get('b_null', 0)}) · "
                 f"random {rm} · real attack {r['real_attack_move']:+.3f}")
    L += ["", f"**Secondary verdict (NOT the gate)**: {s['verdict']}"]
    out = RESULTS_DIR / "null_objective_ablation.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
