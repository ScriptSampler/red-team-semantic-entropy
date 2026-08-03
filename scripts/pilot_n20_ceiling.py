"""N=20 ceiling pilot (critic ruling, critique_log 23).

WHY THIS IS THE CRITICAL PATH. Semantic entropy over N samples is capped at log(N). At the
deployed N=10 the cap is 2.3026 nats and 49% of attacked false-alarm targets sit exactly on
it. A power simulation anchored to the empirical headroom distribution shows the exact
exceedance test has ZERO power under that saturation (saturated targets produce ties, ties
count against the attack under the conservative rule, and the statistic can never reject),
while at a lifted ceiling it recovers to 0.71/0.96 at m=50. So N=20 is not a refinement of
the effect size — it is the enabling condition for the FA analysis to work at all.

BUT the fix may not fix anything: if the attack simply drives the model to 20 distinct
answers, entropy saturates again at log(20)=2.9957 and N is not the answer. This pilot
measures which world we are in, cheaply, before committing to a 2x-cost full re-run.

DESIGN. Take targets that saturate at N=10, re-score the ORIGINAL and the ATTACKED query at
N=20 with the same seed, and report the new saturation rate plus the recovered headroom.
Per-target checkpointing; ~4 min/target.

    ./.venv-wsl/bin/python scripts/pilot_n20_ceiling.py --tag _def --n_targets 15
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR            # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR             # noqa: E402


def summarize(records: list[dict], n_new: int) -> dict:
    """Saturation at the OLD and NEW ceilings, over the pilot's targets."""
    cap_new = math.log(n_new)
    tol = 1e-6
    if not records:
        return {"n": 0}
    sat_new = sum(1 for r in records if r["entropy_after_new"] >= cap_new - tol)
    base_sat_new = sum(1 for r in records if r["entropy_before_new"] >= cap_new - tol)
    moves = [r["entropy_after_new"] - r["entropy_before_new"] for r in records]
    old_moves = [r["entropy_after_old"] - r["entropy_before_old"] for r in records]
    return {
        "n": len(records),
        "cap_new": cap_new,
        "saturated_at_new_cap": sat_new,
        "saturation_rate_new": sat_new / len(records),
        "baselines_at_new_cap": base_sat_new,
        "mean_move_new": sum(moves) / len(moves),
        "mean_move_old": sum(old_moves) / len(old_moves),
        "mean_headroom_new": sum(cap_new - r["entropy_before_new"] for r in records) / len(records),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_def")
    ap.add_argument("--n_targets", type=int, default=15)
    ap.add_argument("--n_samples", type=int, default=20, help="the LIFTED sample budget")
    ap.add_argument("--checkpoint", default="auto")
    args = ap.parse_args()

    from se.attacks.harness import load_pair, read_outcomes
    from se.se_pipeline import semantic_entropy

    campaign = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    outs = read_outcomes(campaign / "triviaqa_se_false_alarm.jsonl")
    cap_old = math.log(10)
    # Target exactly the population the ceiling censors.
    sat = [o for o in outs if o.entropy_after >= cap_old - 1e-6]
    sat.sort(key=lambda o: o.question_id)
    sat = sat[: args.n_targets]

    ckpt = (RESULTS_DIR / f"pilot_n20_ckpt{args.tag}.jsonl" if args.checkpoint == "auto"
            else (Path(args.checkpoint) if args.checkpoint else None))
    done: dict[str, dict] = {}
    if ckpt is not None and ckpt.exists():
        for line in ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done[r["question_id"]] = r
            except Exception:
                continue

    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=args.n_samples, temperature=1.0, seed=0)
    cap_new = math.log(args.n_samples)
    print(f"[pilot] {len(sat)} saturated targets; N={args.n_samples} -> cap {cap_new:.4f} "
          f"(was {cap_old:.4f}); {len(done)} already done", flush=True)

    records = list(done.values())
    for o in sat:
        if o.question_id in done:
            continue
        before = semantic_entropy(o.question, pair.lm, pair.nli, gen).entropy_nats
        after = semantic_entropy(o.best_query, pair.lm, pair.nli, gen).entropy_nats
        rec = {
            "question_id": o.question_id,
            "entropy_before_old": o.entropy_before, "entropy_after_old": o.entropy_after,
            "entropy_before_new": before, "entropy_after_new": after,
            "saturated_new": bool(after >= cap_new - 1e-6),
        }
        records.append(rec)
        if ckpt is not None:
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            with ckpt.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=float) + "\n")
                f.flush()
        print(f"  {o.question_id}: N=10 {o.entropy_before:.3f}->{o.entropy_after:.3f} (AT CAP) | "
              f"N={args.n_samples} {before:.3f}->{after:.3f} "
              f"{'STILL AT CAP' if rec['saturated_new'] else 'freed'}", flush=True)

    s = summarize(records, args.n_samples)
    L = [f"# N={args.n_samples} ceiling pilot (critique_log 23)", "",
         f"Targets that saturate at N=10 (cap {cap_old:.4f}), re-scored at N={args.n_samples} "
         f"(cap {s.get('cap_new', float('nan')):.4f}), same seed.", ""]
    if s["n"]:
        L += [f"- n = {s['n']}",
              f"- **still saturated at the new cap: {s['saturated_at_new_cap']}/{s['n']} = "
              f"{s['saturation_rate_new']:.0%}**",
              f"- baselines already at the new cap: {s['baselines_at_new_cap']}/{s['n']}",
              f"- mean attack move: {s['mean_move_old']:.3f} nats at N=10 -> "
              f"{s['mean_move_new']:.3f} at N={args.n_samples}",
              f"- mean headroom at the new cap: {s['mean_headroom_new']:.3f} nats", "",
              "READING: a LOW residual saturation rate means raising N buys back both "
              "effect-size identifiability and the exceedance test's power, and the full "
              "re-run is justified. A HIGH residual rate means the attack simply drives the "
              "model to N distinct answers at any N, the ceiling is not an artifact of the "
              "sample budget, and false-alarm effect sizes in nats are not identifiable at "
              "feasible N — in which case report censoring-robust statistics only."]
    else:
        L.append("- no records")
    out = RESULTS_DIR / "pilot_n20_ceiling.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
