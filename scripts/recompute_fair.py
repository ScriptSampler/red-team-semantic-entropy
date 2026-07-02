"""Turnkey corrected (B1/B2) fair-pool attack-matrix recompute.

Loads the model once and runs the four TriviaQA cells (SE/SRE x hide/false_alarm)
on the DETECTOR-INDEPENDENT fair pool (campaign_pool, shared seed) with the B2
answer-invariance success metric. Resumable (skips done qids). Then writes the
review-compliant report: per-cell CIs + attrition + answer-flip (report.py),
plus the matrix operating-point FPR sweep and the answer-flip direction split.

    # in Ubuntu-24.04:  export HF_HOME=/home/abhi/.cache/huggingface
    ./.venv-wsl/bin/python scripts/recompute_fair.py --n 40 --tag _fair
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import load_pair, run_attack_batch, read_outcomes
from se.attacks.select import campaign_pool
from se.attacks import report as R

# SE cells first (the headline + a complete SE operating point) so a time-limited
# run still yields the primary result; SRE is best-effort after.
CELLS = [("false_alarm", "se"), ("hide", "se"),
         ("false_alarm", "sre"), ("hide", "sre")]


def write_report(outcomes_by_cell: dict, out_md: Path, n: int, seed: int) -> None:
    L: list[str] = []
    def log(s: str = "") -> None:
        L.append(s)

    log("# Fair-pool recompute — B1 shared pool + B2 answer-invariance metric")
    log("")
    log(f"Detector-independent pool via `campaign_pool` (seed={seed}, n={n}/stratum), "
        "success = entropy moved AND feasible AND hallucination status held under Q'. "
        "All rates carry bootstrap 95% CIs. This supersedes the pre-B1/B2 wk9 matrix.")
    log("")

    # Per-cell summaries.
    log("## Per-cell summaries")
    log("")
    for attack, detector in CELLS:
        key = f"{detector}_{attack}"
        outs = outcomes_by_cell.get(key)
        if not outs_present(outs):
            log(f"### {key}: (no outcomes)")
            log("")
            continue
        s = R.summarize_cell(outs)
        for line in R.render_cell_md(s):
            log(line)
        log("")

    # Matrix-level operating point (needs both classes; per detector).
    log("## Operating-point flips (clean-data threshold sweep)")
    log("")
    log("Hide=positives (model wrong), false-alarm=negatives (model right); clean="
        "entropy_before, attacked=entropy_after. Headline FPR 0.10; 0.05 is noisy at "
        "small n (few negatives set the threshold).")
    log("")
    for detector in ("se", "sre"):
        hide = outcomes_by_cell.get(f"{detector}_hide") or []
        fa = outcomes_by_cell.get(f"{detector}_false_alarm") or []
        if not hide or not fa:
            log(f"### {detector.upper()}: operating point needs both cells (missing one).")
            log("")
            continue
        log(f"### {detector.upper()}")
        log("| target FPR | thr | hide flip (flagged→unflagged) | fa flip (unflagged→flagged) | n_neg |")
        log("| --- | --- | --- | --- | --- |")
        for row in R.matrix_operating_point_sweep(hide, fa):
            log(f"| {row['target_fpr']:.2f} | {row['threshold']:.3f} | "
                f"{row['hide_flagged_to_unflagged']}/{row['n_hide']} "
                f"({row['hide_flip_rate']:.0%}) | "
                f"{row['fa_unflagged_to_flagged']}/{row['n_false_alarm']} "
                f"({row['fa_flip_rate']:.0%}) | {row['n_negatives_for_threshold']} |")
        # Answer-flip direction split (B2 nit 1 / B5).
        b = R.matrix_answer_flip_breakdown(hide, fa)
        log("")
        log(f"answer-flip (NLI-fidelity suspects): hide→correct {b['hide_became_correct']}"
            f"/{b['hide_ef_n']}, false_alarm→wrong {b['fa_became_wrong']}/{b['fa_ef_n']}.")
        log("")

    out_md.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out_md}", flush=True)


def outs_present(outs) -> bool:
    return bool(outs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--tag", default="_fair")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_iteration", type=int, default=20)
    ap.add_argument("--only", default="",
                    help="restrict to cells, e.g. se_hide,se_false_alarm")
    ap.add_argument("--report_only", action="store_true",
                    help="skip attacks; just (re)build the report from existing JSONLs")
    args = ap.parse_args()

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    outcomes_by_cell: dict = {}
    pair = None
    for attack, detector in CELLS:
        key = f"{detector}_{attack}"
        out = campaign_dir / f"triviaqa_{detector}_{attack}.jsonl"
        if only and key not in only:
            if out.exists():
                outcomes_by_cell[key] = read_outcomes(out)
            continue
        if args.report_only:
            outcomes_by_cell[key] = read_outcomes(out) if out.exists() else []
            continue
        if pair is None:
            t0 = time.perf_counter()
            pair = load_pair()
            print(f"[load] model+NLI in {time.perf_counter()-t0:.0f}s", flush=True)
        want = "wrong" if attack == "hide" else "right"
        examples = campaign_pool("triviaqa", want, args.n, seed=args.seed)
        sre_kwargs = (dict(n_reform=3, k_samples=8, temperature=0.8)
                      if detector == "sre" else None)
        print(f"[cell {key}] n={len(examples)} -> {out.name}", flush=True)
        t0 = time.perf_counter()
        run_attack_batch(
            examples, attack, pair, out, detector=detector, gen_cfg=gen,
            sre_kwargs=sre_kwargs, max_iteration=args.max_iteration,
            candidate_size_M=3, top_N=3, min_delta_nats=0.25, progress_every=5,
        )
        outcomes_by_cell[key] = read_outcomes(out)
        print(f"[cell {key}] done in {time.perf_counter()-t0:.0f}s "
              f"({sum(o.success for o in outcomes_by_cell[key])}/"
              f"{len(outcomes_by_cell[key])} gated success)", flush=True)

    write_report(outcomes_by_cell, RESULTS_DIR / "fair_recompute_report.md",
                 args.n, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
