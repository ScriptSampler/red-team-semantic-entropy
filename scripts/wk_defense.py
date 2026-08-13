"""Defense evaluation: does input-paraphrase-averaging blunt the attacks?

WHAT CHANGED AND WHY (2026-08-13). The original version of this script compared
two arms:

    vanilla effect  = | SE(Q') - SE(Q) |               (cached, selection-time)
    defended effect = | defended(Q') - defended(Q) |   (fresh, unseeded, d-averaged)

and reported `1 - defended/vanilla` as "the defense works". That comparison is
CONFOUNDED and could not have produced a falsifiable result, because the two
arms differ in two ways at once:

  (a) the defense averages over d paraphrases          <- what we want to measure
  (b) the defended arm re-samples on a fresh seed      <- pure regression to the mean

Q' was chosen as the argmax over ~181 noisy entropy estimates, so (b) alone
shrinks the effect substantially. This project has MEASURED that shrinkage
directly: results/winners_curse_se_false_alarm.md finds retention of only
45.2% (95% CI [25%, 65%]) when the SELECTED paraphrase is re-scored at the same
N=10 on a different seed -- i.e. roughly 55% of the effect evaporates from
re-sampling with NO defense of any kind. The old two-arm design would have
booked that entire 55% as a defense success.

So a third arm is now run: the d=1 fresh-redraw CONTROL, which pays exactly the
re-sampling cost of the defended arm and none of the averaging.

    A. cached    | SE(Q') - SE(Q) |                    selection-time (seeded)
    B. control   | SE_fresh(Q') - SE_fresh(Q) |        d=1, unseeded  <- BASELINE
    C. defended  | defended(Q') - defended(Q) |        d=K, unseeded

  B vs A  isolates the winner's curse (already known; a cross-check).
  C vs B  isolates THE DEFENSE. This is the only comparison that can falsify
          the defense claim, because both arms re-sample identically and differ
          only in whether the score is averaged over paraphrases.

The prediction under test is stated in the report header and must be able to
fail: see FALSIFIABLE_CLAIM below.

Requires GPU. Print the cost first, then schedule it:
    python scripts/wk_defense.py --estimate-only
    python scripts/wk_defense.py --tag _defb
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR, GenConfig
from se.nli import NLI
from se import model as M
from se.config import ModelConfig
from se.sampling import DEFAULT_SAMPLES_DIR
from se.defense import defended_entropy
from se.se_pipeline import semantic_entropy
from se.attacks.harness import read_outcomes


ATTACKS = ("hide", "false_alarm")

FALSIFIABLE_CLAIM = (
    "PREDICTION UNDER TEST: averaging the detector score over d NLI-equivalent "
    "paraphrases of whatever input it receives reduces the attack's surviving "
    "entropy move by MORE than re-sampling alone does. Operationally: the "
    "per-question paired reduction of arm C against arm B is > 0, with a 95% CI "
    "excluding 0. If the CI covers 0, the defense adds nothing beyond forcing "
    "the attacker to re-pay for selection noise, and the claim is FALSE."
)

# ---- measured per-call costs (this repo, RX 9070 XT, Llama-3.1-8B nf4) -------
# SE sampling, N=10 @ 48 new tokens, batched via num_return_sequences:
#   12.4 s/Q for greedy + 10 samples (results/run_all.log, n=1907)
#   1.49 s/Q for the greedy answer alone (results/pipeline_check.md)
#   -> 10-sample draw ~ 10.9 s
# NLI clustering of 10 samples (C(10,2)=45 pairs): 1.84 s/Q
#   (results/wk3_fri_entropy.md, "clustered 50 questions in 92.2s")
SEC_PER_SE_EVAL = 10.9 + 1.84       # one semantic_entropy() call
SEC_PER_PROPOSE = 1.49 * (64 / 48)  # one greedy 64-token paraphrase
SEC_PER_GATE = 0.15                 # one unbatched bidirectional NLI check
SEC_MODEL_LOAD = 180.0
# Empirical bidirectional-NLI equivalence pass rate on proposer output, from the
# definitive campaigns' own gate counters (n_feasibility_passed/n_feasibility_checks):
#   wk9_defb hide 0.692, wk9_defb false_alarm 0.650, wk9_def hide 0.641.
# feasibility.check also applies no-op and length filters that the defense does
# not, so this is a LOWER bound on the defense's keep rate.
GATE_PASS_RATE = 0.67


def sec_per_defended_call(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    n_variants = 1.0 + k * gate_rate
    return k * SEC_PER_PROPOSE + k * SEC_PER_GATE + n_variants * SEC_PER_SE_EVAL


def sec_per_outcome(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    # two sides (Q and Q') x (one defended call + one d=1 control SE call)
    return 2 * sec_per_defended_call(k, gate_rate) + 2 * SEC_PER_SE_EVAL


@dataclass
class DefenseRecord:
    attack: str
    question_id: str
    cached_before: float
    cached_after: float
    fresh_before: float
    fresh_after: float
    defended_before: float
    defended_after: float
    d_before: int          # effective paraphrase count actually averaged, Q side
    d_after: int           # ... Q' side
    rejected_gate_before: int = 0
    rejected_gate_after: int = 0

    @property
    def effect_cached(self) -> float:
        return abs(self.cached_after - self.cached_before)

    @property
    def effect_control(self) -> float:
        return abs(self.fresh_after - self.fresh_before)

    @property
    def effect_defended(self) -> float:
        return abs(self.defended_after - self.defended_before)


def _ckpt_load(path: Path) -> dict[str, DefenseRecord]:
    out: dict[str, DefenseRecord] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            out[f"{rec['attack']}::{rec['question_id']}"] = DefenseRecord(**rec)
        except Exception:
            continue
    return out


def _paired_reduction(num: list[float], den: list[float]) -> list[float]:
    """Per-question 1 - num/den, skipping questions with a ~zero denominator."""
    return [1.0 - n / d for n, d in zip(num, den) if d > 1e-9]


def _ratio_reduction_ci(num: list[float], den: list[float], n_boot: int = 10000,
                        seed: int = 0) -> tuple[float, float, float, float]:
    """Paired percentile bootstrap on 1 - mean(num)/mean(den).

    Paired over questions: each question contributes its (num, den) jointly,
    because they are the same target measured under two arms. Returns
    (point, lo, hi, denominator_z) where denominator_z is the mean denominator
    in units of its own standard error -- if it is small the ratio is badly
    conditioned and the interval must not be quoted (see the estimator note in
    results/winners_curse_se_false_alarm.md).
    """
    a, b = np.asarray(num, dtype=float), np.asarray(den, dtype=float)
    n = len(a)
    if n < 2 or b.mean() <= 1e-9:
        return float("nan"), float("nan"), float("nan"), 0.0
    point = 1.0 - a.mean() / b.mean()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    reps = 1.0 - a[idx].mean(axis=1) / b[idx].mean(axis=1)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    se = b.std(ddof=1) / np.sqrt(n)
    return float(point), float(lo), float(hi), float(b.mean() / se) if se > 0 else 0.0


def estimate(args, counts: dict[str, int]) -> list[str]:
    """Cost table. No GPU, no model load."""
    lines = ["## Cost estimate (no GPU used to produce this table)", ""]
    per_def = sec_per_defended_call(args.k)
    per_out = sec_per_outcome(args.k)
    lines.append(f"assumed gate pass rate {GATE_PASS_RATE:.2f} -> effective d = "
                 f"{1 + args.k * GATE_PASS_RATE:.1f} variants per defended call")
    lines.append(f"one semantic_entropy() call        {SEC_PER_SE_EVAL:5.1f} s")
    lines.append(f"one defended_entropy(k={args.k}) call   {per_def:5.1f} s")
    lines.append(f"one outcome (3 arms, both sides)   {per_out:5.1f} s")
    lines.append("")
    total = 0.0
    for attack, n in counts.items():
        t = n * per_out
        total += t
        lines.append(f"  {attack:<12} {n:3d} outcomes  {t/3600:5.2f} GPU-h")
    total += SEC_MODEL_LOAD
    lines.append(f"  {'TOTAL':<12} {sum(counts.values()):3d} outcomes  "
                 f"{total/3600:5.2f} GPU-h  (+{SEC_MODEL_LOAD/60:.0f} min model load)")
    lines.append("")
    lines.append("VRAM: Llama-3.1-8B nf4 ~5.5 GB (results/run_all.log) + "
                 "DeBERTa-large-MNLI fp32 ~1.6 GB ~= 7 GB, co-resident.")
    lines.append("")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="_defb",
                    help="campaign directory suffix under samples/attacks/wk9<tag>. "
                         "'' selects the SUPERSEDED pre-B1 n=15 wk9 campaign.")
    ap.add_argument("--campaign-dir", default="",
                    help="explicit campaign directory, overrides --tag")
    ap.add_argument("--attacks", default=",".join(ATTACKS))
    ap.add_argument("--filter", default="entropy_and_feasible",
                    choices=["entropy_and_feasible", "success", "improved"],
                    help="which outcomes are attack targets worth defending against")
    ap.add_argument("--k", type=int, default=4, help="paraphrases per input (d)")
    ap.add_argument("--aggregate", default="median", choices=["median", "mean", "min"])
    ap.add_argument("--max-per-attack", type=int, default=40)
    ap.add_argument("--checkpoint", default="auto")
    ap.add_argument("--out", default="")
    ap.add_argument("--estimate-only", action="store_true",
                    help="print the GPU cost table and exit without loading a model")
    args = ap.parse_args()

    campaign_dir = (Path(args.campaign_dir) if args.campaign_dir
                    else DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}")
    attacks = [a.strip() for a in args.attacks.split(",") if a.strip()]
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"defense_eval{args.tag}.md"
    ckpt_path = (RESULTS_DIR / f"defense_ckpt{args.tag}.jsonl"
                 if args.checkpoint == "auto" else Path(args.checkpoint))

    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    log("# Defense: input-paraphrase-averaged SE vs the attacks")
    log("")
    log(f"campaign: `{campaign_dir}`  filter: `{args.filter}`  "
        f"d={args.k}  aggregate={args.aggregate}  cap={args.max_per_attack}/attack")
    log("")
    log("Three arms, because the two-arm version of this experiment was confounded")
    log("by the winner's curse (see the module docstring and")
    log("results/winners_curse_se_false_alarm.md):")
    log("")
    log("  A cached    selection-time |SE(Q')-SE(Q)|, seeded")
    log("  B control   d=1 fresh unseeded redraw of the same two inputs")
    log("  C defended  d=K fresh unseeded paraphrase-averaged score")
    log("")
    log("**C vs B is the defense.** A vs B is the winner's curse, reported as a")
    log("cross-check against the independently measured 45.2% retention.")
    log("")
    log(FALSIFIABLE_CLAIM)
    log("")

    # ---- select targets --------------------------------------------------
    targets: dict[str, list] = {}
    for attack in attacks:
        camp = campaign_dir / f"triviaqa_se_{attack}.jsonl"
        if not camp.exists():
            log(f"- {attack}: no campaign file at `{camp}`, skipped")
            continue
        allo = read_outcomes(camp)
        sel = [o for o in allo if getattr(o, args.filter)][: args.max_per_attack]
        if not sel and allo:
            n_imp = sum(o.improved for o in allo)
            log(f"- {attack}: 0 of {len(allo)} outcomes pass `{args.filter}` "
                f"({n_imp} pass `improved`). Records written before the B2 schema "
                f"have entropy_and_feasible=False by default -- pass "
                f"`--filter improved` explicitly if that is really the intent.")
            continue
        targets[attack] = sel
        log(f"- {attack}: {len(sel)} targets of {len(allo)} outcomes")
    log("")

    counts = {a: len(v) for a, v in targets.items()}
    for line in estimate(args, counts):
        log(line)

    if args.estimate_only:
        print("(--estimate-only: no model loaded, nothing run)", file=sys.stderr)
        return 0
    if not targets:
        out_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        log("No targets; nothing to run.")
        return 1

    # ---- run -------------------------------------------------------------
    done = _ckpt_load(ckpt_path)
    print(f"checkpoint {ckpt_path}: {len(done)} records already complete", flush=True)

    todo = [(a, o) for a, outs in targets.items() for o in outs
            if f"{a}::{o.question_id}" not in done]

    # Only pay for the model when there is something left to run. A completed
    # checkpoint can therefore be re-analysed (or the report re-rendered after an
    # analysis change) on a machine with no GPU at all, while the chain has it.
    lm = nli = None
    if todo:
        lm = M.load_llama(ModelConfig())
        nli = NLI()
    else:
        print("checkpoint complete: re-rendering the report, no model loaded",
              flush=True)

    # Both fresh arms force seed=None so the control and the defended arm
    # re-sample on exactly the SAME footing.
    fresh = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=None)

    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    n_new = 0
    with ckpt_path.open("a", encoding="utf-8") as fh:
        for attack, outcomes in targets.items():
            for i, o in enumerate(outcomes):
                key = f"{attack}::{o.question_id}"
                if key in done:
                    continue
                d_q = defended_entropy(o.question, lm, nli, k_paraphrases=args.k,
                                       aggregate=args.aggregate, gen_cfg=fresh)
                d_adv = defended_entropy(o.best_query, lm, nli, k_paraphrases=args.k,
                                         aggregate=args.aggregate, gen_cfg=fresh)
                rec = DefenseRecord(
                    attack=attack,
                    question_id=o.question_id,
                    # Cached: both sides from the run that produced the attack, so
                    # the selection-time effect has no fresh-vs-cached mismatch.
                    cached_before=o.entropy_before,
                    cached_after=o.entropy_after,
                    # Control: d=1, unseeded, same generation config as the
                    # defended arm's per-variant draws.
                    fresh_before=semantic_entropy(o.question, lm, nli, fresh).entropy_nats,
                    fresh_after=semantic_entropy(o.best_query, lm, nli, fresh).entropy_nats,
                    defended_before=d_q.defended_entropy,
                    defended_after=d_adv.defended_entropy,
                    d_before=d_q.effective_d,
                    d_after=d_adv.effective_d,
                    rejected_gate_before=d_q.n_rejected_gate,
                    rejected_gate_after=d_adv.n_rejected_gate,
                )
                fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
                fh.flush()
                done[key] = rec
                n_new += 1
                if n_new % 5 == 0:
                    el = time.perf_counter() - t0
                    print(f"  {attack} {i+1}/{len(outcomes)} | {n_new} new in "
                          f"{el/60:.1f} min ({el/n_new:.0f}s/target)", flush=True)

    # ---- analyse ---------------------------------------------------------
    for attack, outcomes in targets.items():
        recs = [done[f"{attack}::{o.question_id}"] for o in outcomes
                if f"{attack}::{o.question_id}" in done]
        if not recs:
            continue
        log(f"## {attack}: n = {len(recs)}")
        log("")

        a = [r.effect_cached for r in recs]
        b = [r.effect_control for r in recs]
        c = [r.effect_defended for r in recs]
        # ASCII only: this report is printed to a Windows cp1252 console as well
        # as written to a UTF-8 file.
        log("| arm | mean abs. move (nats) | median |")
        log("|---|---|---|")
        log(f"| A cached (selection-time) | {statistics.mean(a):.3f} | {statistics.median(a):.3f} |")
        log(f"| B control (d=1 fresh) | {statistics.mean(b):.3f} | {statistics.median(b):.3f} |")
        log(f"| C defended (d={args.k}) | {statistics.mean(c):.3f} | {statistics.median(c):.3f} |")
        log("")

        # Did the defense actually average anything?
        eff = [r.d_before for r in recs] + [r.d_after for r in recs]
        degen = sum(1 for e in eff if e == 0)
        log(f"effective d actually averaged: mean {statistics.mean(eff):.2f} of "
            f"{args.k} requested; {degen}/{len(eff)} calls degenerated to a single "
            f"variant (the equivalence gate rejected every paraphrase).")
        if degen > 0.25 * len(eff):
            log("")
            log("> **WARNING.** More than a quarter of the defended scores averaged")
            log("> nothing at all. For those the C arm IS the B arm, and the C-vs-B")
            log("> comparison is diluted toward 0 by construction. Report the")
            log("> non-degenerate subset separately before drawing any conclusion.")
        log("")

        # C vs B: THE DEFENSE.
        pt, lo, hi, dz = _ratio_reduction_ci(c, b)
        paired = _paired_reduction(c, b)
        log(f"**C vs B (the defense):** reduction {pt*100:.1f}% "
            f"[{lo*100:.1f}%, {hi*100:.1f}%] (paired percentile bootstrap, "
            f"10,000 reps, seed 0; denominator {dz:.1f} SE from zero)")
        if paired:
            log(f"per-question paired reduction: median {statistics.median(paired)*100:.1f}%, "
                f"mean {statistics.mean(paired)*100:.1f}% (n={len(paired)})")
        if not (lo > 0):
            log("")
            log("> **The prediction FAILED for this cell.** The interval covers 0:")
            log("> averaging over paraphrases did not reduce the surviving effect")
            log("> beyond what re-sampling alone achieves.")
        log("")

        # B vs A: the winner's curse, as a cross-check on a known quantity.
        pt2, lo2, hi2, _ = _ratio_reduction_ci(b, a)
        log(f"B vs A (winner's curse cross-check, NOT a defense result): "
            f"reduction {pt2*100:.1f}% [{lo2*100:.1f}%, {hi2*100:.1f}%]. "
            f"Independently measured at 55% (retention 45.2%, CI [25%, 65%]) in "
            f"results/winners_curse_se_false_alarm.md; a large disagreement here "
            f"means one of the two measurements is wrong.")
        log("")

        pt3, lo3, hi3, _ = _ratio_reduction_ci(c, a)
        log(f"C vs A (total apparent reduction): {pt3*100:.1f}% "
            f"[{lo3*100:.1f}%, {hi3*100:.1f}%]. **Do not quote this as the defense's "
            f"effect** -- it compounds the defense with the winner's curse, which is "
            f"what the superseded two-arm version of this script reported.")
        log("")

    log("## Scope")
    log("")
    log("This measures the defense against paraphrases the attacker found WITHOUT")
    log("knowing a defense was deployed. It is therefore an upper bound on the")
    log("defense's value: an adaptive attacker optimising against")
    log("`defended_entropy` directly is a strictly harder case and is not run here.")
    log("")
    log("No AUROC is reported. The defended detector's AUROC needs both classes in")
    log("one pool (hide targets are all incorrect-answer questions, false-alarm")
    log("targets all correct-answer ones), which is the fair-pool construction owned")
    log("by scripts/recompute_fair.py. An earlier docstring here promised that")
    log("number; it was never computed.")

    out_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
