"""Null-objective beam ablation (critique_log 21, B2 — required by the critic).

QUESTION. The budget-matched benign floor draws ~180 RANDOM feasible paraphrases per
target. But the real optimiser's 180 candidates are not diffuse-random: the beam
concentrates proposals around high-scoring parents, and under H0 (the objective carries
no signal about the detector) that concentration chases high-NOISE candidates. If the
concentrated candidate set reaches higher entropy-move maxima than a diffuse set of the
same size, then the diffuse random-180 floor UNDER-estimates the null and the
budget-matched control alone over-claims the attack (anti-conservative).

DESIGN (paired per target, self-contained):
  arm CONCENTRATED  run the IDENTICAL optimiser (same beam width, budget, proposer,
                    NLI feasibility gate) with a NULL objective — a deterministic hash of
                    the candidate string, i.e. a fixed pure-noise landscape with zero
                    detector signal (exactly H0: fixed value per candidate, no meaning).
                    Record every proposed candidate; keep the NLI-feasible ones; score
                    each at the standard seed-0 config; MAX intended move = null-beam-max.
  arm DIFFUSE       the same number of proposer draws taken directly from the original
                    question (no beam recursion), feasibility-gated, scored identically;
                    MAX intended move = random-max. (This is the budget-matched floor's
                    generating process.)
  verdict           paired mean(null-beam-max − random-max) with bootstrap CI over
                    targets. CI ~ 0  -> the diffuse budget-matched floor is a safe null.
                    CI > 0 materially -> the null-objective beam-max is the required floor.

SCOPE. Scored under the NLI clusterer (+ exact-match, free): the attack optimises the
NLI-entropy objective, so the H0 selection concern lives in NLI-objective space; the
clusterer-attribution question is separate (the 4-arm null control). ~10 targets a few
hours on GPU; per-target checkpoint JSONL makes it resumable.

  ./.venv-wsl/bin/python scripts/null_objective_ablation.py --tag _def --n_targets 10
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
from se.stats import bootstrap_ci                      # noqa: E402


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_def")
    ap.add_argument("--n_targets", type=int, default=10)
    ap.add_argument("--max_iteration", type=int, default=20, help="beam iterations (match the attack)")
    ap.add_argument("--candidate_size_M", type=int, default=3, help="children per parent (match)")
    ap.add_argument("--top_N", type=int, default=3, help="beam width (match)")
    ap.add_argument("--checkpoint", default="auto",
                    help="'auto' -> results/null_objective_ablation_ckpt<tag>.jsonl; '' off")
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
    done: dict[str, dict] = {}
    if ckpt_path is not None and ckpt_path.exists():
        for line in ckpt_path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done[r["question_id"]] = r
            except Exception:
                continue
        print(f"[ckpt] {len(done)} target(s) already done", flush=True)

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
        beam_cands = [q for q in dict.fromkeys(seen) if q != o.question]
        beam_feas = [q for q in beam_cands if feasibility.check(q, o.question, pair.nli).feasible]
        beam_moves = [score(q)[0] - base_nli for q in beam_feas]   # FA: intended move = rise
        null_beam_max = max(beam_moves) if beam_moves else None

        # --- arm DIFFUSE: same budget of proposer draws from the ORIGINAL -----------
        proposer.seed_proposer(_stable_seed("diffuse:" + o.question_id))
        diffuse = [proposer.propose(o.question, pair.lm) for _ in range(len(beam_cands) or budget)]
        diff_feas = [q for q in dict.fromkeys(diffuse)
                     if q != o.question and feasibility.check(q, o.question, pair.nli).feasible]
        diff_moves = [score(q)[0] - base_nli for q in diff_feas]
        random_max = max(diff_moves) if diff_moves else None

        rec = {
            "question_id": o.question_id, "question": o.question,
            "real_attack_move": o.entropy_after - o.entropy_before,
            "n_beam_cands": len(beam_cands), "n_beam_feasible": len(beam_feas),
            "n_diffuse": len(diffuse), "n_diffuse_feasible": len(diff_feas),
            "null_beam_max": null_beam_max, "random_max": random_max,
            "beam_moves": beam_moves, "diffuse_moves": diff_moves,
        }
        records.append(rec)
        if ckpt_path is not None:
            ckpt_path.parent.mkdir(parents=True, exist_ok=True)
            with ckpt_path.open("a", encoding="utf-8") as cf:
                cf.write(json.dumps(rec, default=float) + "\n")
                cf.flush()
        print(f"  {o.question_id}: null-beam-max "
              f"{'n/a' if null_beam_max is None else f'{null_beam_max:+.3f}'} "
              f"({len(beam_feas)}/{len(beam_cands)} feasible) vs random-max "
              f"{'n/a' if random_max is None else f'{random_max:+.3f}'} "
              f"({len(diff_feas)} feasible) | real attack {rec['real_attack_move']:+.3f}",
              flush=True)

    s = paired_summary(records)
    L = ["# Null-objective beam ablation (critique_log 21, B2)", "",
         f"n={s['n']} paired FA targets; per-arm budget ~{budget} candidates; NLI-clusterer "
         "scoring at the standard seed-0 config (the objective the attack optimises).", "",
         "Per target: null-beam-max (concentrated proposals, hash objective) vs random-max "
         "(diffuse proposals, same budget) vs the real attack's move (context only):", ""]
    for r in sorted(records, key=lambda r: r["question_id"]):
        nb = "n/a" if r.get("null_beam_max") is None else f"{r['null_beam_max']:+.3f}"
        rm = "n/a" if r.get("random_max") is None else f"{r['random_max']:+.3f}"
        L.append(f"- {r['question_id']}: null-beam {nb} · random {rm} · "
                 f"real attack {r['real_attack_move']:+.3f}")
    L += ["", f"**VERDICT**: {s['verdict']}"]
    out = RESULTS_DIR / "null_objective_ablation.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
