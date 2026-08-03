"""Direct measurement of the winner's curse: re-score the SELECTED attack on FRESH samples.

The whole B2 problem is that the attack reports the MAXIMUM over ~181 noisy entropy
estimates, so the reported move is inflated by selection-on-noise. The classical diagnostic
for exactly this is to re-evaluate the selected item on independent data: if the advantage
was noise, it regresses toward the mean; if it is real, it persists.

This does that, cheaply and without any judge or benign floor. For every completed target we
re-score BOTH the original question and the attack's chosen paraphrase at the SAME N but a
DIFFERENT sampling seed, and compare the fresh move to the selection-time move. The shrinkage
    retention = mean(fresh move) / mean(selection move)
is a direct estimate of how much of the reported effect survives the winner's curse. It does
not replace the benign-floor control (which answers a different question: whether random
paraphrasing achieves the same) but it bounds the selection-on-noise component on its own.

Verified prerequisite: seeded draws at different seeds are genuinely different samples
(checked explicitly — a 20-sample draw is not a prefix-superset of a 10-sample draw).

    ./.venv-wsl/bin/python scripts/winners_curse_reeval.py --tag _def --cell se_false_alarm
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR          # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR           # noqa: E402


def summarize(records: list[dict]) -> dict:
    if not records:
        return {"n": 0}
    sel = [r["move_selection"] for r in records]
    fresh = [r["move_fresh"] for r in records]
    pos = sum(1 for m in fresh if m > 0)
    out = {
        "n": len(records),
        "mean_selection": st.mean(sel),
        "mean_fresh": st.mean(fresh),
        "median_selection": st.median(sel),
        "median_fresh": st.median(fresh),
        "retention": (st.mean(fresh) / st.mean(sel)) if st.mean(sel) else float("nan"),
        "kept_positive": pos,
        "kept_positive_rate": pos / len(records),
    }
    try:
        import numpy as np
        from se.stats import bootstrap_ci
        d = [f - s for f, s in zip(fresh, sel)]
        ci = bootstrap_ci(d, np.mean)
        out["shrinkage_ci"] = (ci.point, ci.lo, ci.hi)
        out["corr"] = float(np.corrcoef(sel, fresh)[0, 1]) if len(sel) > 2 else float("nan")
    except Exception:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_def")
    ap.add_argument("--cell", default="se_false_alarm")
    ap.add_argument("--fresh_seed", type=int, default=1, help="a DIFFERENT seed from the run's 0")
    ap.add_argument("--n_targets", type=int, default=0, help="0 = all")
    ap.add_argument("--checkpoint", default="auto")
    args = ap.parse_args()

    from se.attacks.harness import load_pair, read_outcomes
    from se.se_pipeline import semantic_entropy

    campaign = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    outs = read_outcomes(campaign / f"triviaqa_{args.cell}.jsonl")
    outs.sort(key=lambda o: o.question_id)
    if args.n_targets:
        outs = outs[: args.n_targets]

    ck = (RESULTS_DIR / f"winners_curse_ckpt_{args.cell}{args.tag}.jsonl"
          if args.checkpoint == "auto" else (Path(args.checkpoint) if args.checkpoint else None))
    done: dict[str, dict] = {}
    if ck is not None and ck.exists():
        for line in ck.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done[r["question_id"]] = r
            except Exception:
                continue

    pair = load_pair()
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=args.fresh_seed)
    print(f"[wc] {len(outs)} targets in {args.cell}; fresh seed {args.fresh_seed}; "
          f"{len(done)} already done", flush=True)

    records = list(done.values())
    for o in outs:
        if o.question_id in done:
            continue
        if o.best_query == o.question:          # optimiser found nothing; no selection to re-test
            continue
        before = semantic_entropy(o.question, pair.lm, pair.nli, gen).entropy_nats
        after = semantic_entropy(o.best_query, pair.lm, pair.nli, gen).entropy_nats
        sign = -1.0 if o.attack == "hide" else 1.0
        rec = {
            "question_id": o.question_id, "attack": o.attack,
            "before_selection": o.entropy_before, "after_selection": o.entropy_after,
            "move_selection": sign * (o.entropy_after - o.entropy_before),
            "before_fresh": before, "after_fresh": after,
            "move_fresh": sign * (after - before),
        }
        records.append(rec)
        if ck is not None:
            ck.parent.mkdir(parents=True, exist_ok=True)
            with ck.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=float) + "\n")
                f.flush()
        print(f"  {o.question_id}: selection {rec['move_selection']:+.3f} -> "
              f"fresh {rec['move_fresh']:+.3f}", flush=True)

    s = summarize(records)
    L = [f"# Winner's-curse re-evaluation — {args.cell} (fresh seed {args.fresh_seed})", "",
         "The attack reports the MAXIMUM over ~181 noisy entropy estimates, so its move is "
         "inflated by selection-on-noise. Here the SELECTED paraphrase is re-scored on an "
         "INDEPENDENT sample (same N, different seed). Regression toward the mean measures "
         "the selection component directly; it does not answer whether benign paraphrasing "
         "achieves the same (that is the benign-floor control's job).", ""]
    if s["n"]:
        L += [f"- n = {s['n']}",
              f"- mean move at selection: **{s['mean_selection']:+.3f}** nats -> "
              f"on fresh samples: **{s['mean_fresh']:+.3f}** nats",
              f"- **retention = {s['retention']:.0%}** of the selection-time effect",
              f"- median: {s['median_selection']:+.3f} -> {s['median_fresh']:+.3f}",
              f"- targets keeping a positive move: {s['kept_positive']}/{s['n']} "
              f"({s['kept_positive_rate']:.0%})"]
        if "shrinkage_ci" in s:
            p, lo, hi = s["shrinkage_ci"]
            L.append(f"- shrinkage (fresh - selection): {p:+.3f} [{lo:+.3f}, {hi:+.3f}] nats "
                     f"(a CI excluding 0 means the selection effect is provably inflated)")
        if "corr" in s:
            L.append(f"- corr(selection move, fresh move) = {s['corr']:+.3f}")
        L += ["", "READING: retention near 1.0 means the selected paraphrase's advantage is a "
              "property of the paraphrase, not of the sample it was selected on. Retention "
              "near 0 means the reported effect was largely selection-on-noise — which the "
              "benign floor would then also show."]
    out = RESULTS_DIR / f"winners_curse_{args.cell}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
