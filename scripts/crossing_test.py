"""Operating-point CROSSING test on the definitive false-alarm cell (critique_log 32).

STATUS — READ THIS BEFORE READING ANY NUMBER BELOW.
  This is a DISCLOSED, OUTCOME-TRIGGERED SECONDARY DIAGNOSTIC. The trigger is named and
  is not hidden: 42/80 = 52.5% of `_defb` false-alarm targets finish exactly at the
  log(10) = 2.3026 ceiling, so an effect size measured in nats is right-censored. This
  script exists to ask a question a ceiling cannot censor. It is NOT the claim statistic.
  The primary remains the randomised-tie exceedance test (critique_log 26a,
  `se.stats.exceedance_test_over_seeds`). Nothing printed here is a verdict on the attack.

WHY A CROSSING TEST. `se.stats.flip_test_conditional` counts, per target, how many
candidates land on the far side of a fixed detector operating point tau, and tests the
attack arm against the benign arm with an EXACT stratified hypergeometric null that
conditions on the 2x2 margins. Crossing is binary, so — in principle — the log(N) cap
cannot censor it: past tau is past tau, however far past.

THE OPERATING POINT, pre-registered in docs/critique_log.md entry 32 BEFORE the
null-control data existed: tau = the fair-pool clean-score threshold at 10% FPR on correct
answers, i.e. the point at which a deployed detector flags one correct answer in ten. A
"crossing" is a paraphrase pushing a correct answer's score to/over tau — operationally,
what a false alarm IS. The fair pool is the 200 score-independently drawn correct-answer
items (`se.attacks.select`), scored from the Week-4 span-oracle cache.

THREE THINGS THE PRE-REGISTRATION GOT WRONG, all reported by this script rather than
quietly patched. They are measurement facts, not opinions, and each is printed at run time:

  (1) tau is NOT independent of the attacked targets. Entry 32 says "Fixing it on the FAIR
      pool keeps the threshold independent of the attacked targets." It does not: the 80
      attacked false-alarm targets are literally the FIRST 80 of the same 200-item shuffled
      fair-pool draw (`_stratum_ids` is a pure function of (want, seed)), so 40% of the
      sample defining tau is the attacked set itself. We therefore also compute tau on the
      120 fair-pool items that were NOT attacked and report both.

  (2) "10% FPR" is not an attainable operating point on this detector. Semantic entropy at
      N=10 takes ~28 distinct values on the fair pool, with large atoms; the achievable
      false-positive rates jump from 9.5% (at the ceiling) straight to 21.5%. The quantile
      rule that `se.stats.operating_point` implements is only exact for a continuous score.
      So the REALISED FPR of tau is always printed next to tau. Do not quote "10% FPR".

  (3) At 10% FPR the operating point coincides with the CEILING, which destroys the very
      censoring-immunity that motivated this test. The smallest threshold whose realised FPR
      is <= 0.10 is 2.3026 = log(10) itself. With a strict `>` crossing rule nothing can
      cross it (it is the maximum attainable score) and with a `>=` rule "crossed" is
      identical to "saturated" — the crossing statistic collapses back into the saturation
      statistic it was built to escape. Censoring-immunity holds only when tau is strictly
      INTERIOR to the attainable range. The quantile-rule tau (2.1640) is interior; the
      FPR<=0.10 tau is not. Both are computed; the interior one is the only usable one.

WHAT `feasible_objs` ACTUALLY IS — and why the attack arm is NOT exchangeable with a
benign arm. This is the most important caveat in the file. In `se.attacks.optimizer`, a
candidate is recorded in `feasible_objs` only if it (a) scored >= the RUNNING BEST and then
(b) passed the equivalence gate. It is a running-record subset, not the attack's candidate
sample: measured on `_defb`, zero of 3058 recorded candidates fall below their target's own
clean score. `flip_test_conditional`'s null assumes the attack candidates and the benign
draws are exchangeable draws from one distribution; a monotone record filter on one arm
breaks that, upward, even if the optimiser carries no signal at all. Read any crossing
p-value computed from this arm as an UPPER BOUND on the evidence, and see the printed
caveat. Fixing it properly needs the optimiser to log all candidate objectives, not only
the record-setting feasible ones.

BENIGN ARM. `flip_test_conditional` needs per-target benign crossing counts. The attack
campaign JSONL does not carry benign draws, so they must come from the null control
(`scripts/null_control.py`, which writes per-target benign MOVE lists plus a fresh
`baseline`). That run had not started when this script was written; pass `--benign
<null_control_ckpt.jsonl>` once it has. Without it the test is NOT EVALUABLE and the script
says so — it does not substitute a fabricated benign arm.

Run (Windows):  .venv\\Scripts\\python.exe scripts\\crossing_test.py
Run (WSL):      ./.venv-wsl/bin/python scripts/crossing_test.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.attacks.select import RELABELED, _stratum_ids, load_labels   # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR                          # noqa: E402
from se.stats import ceiling_saturation, flip_test_conditional, operating_point  # noqa: E402

CAP_N = 10                       # GenConfig.n_samples; the ceiling is log(CAP_N)
CAP = math.log(CAP_N)
FAIR_N = 200                     # fair-pool size per stratum (scripts/fair_pool_check.py)
FAIR_SEED = 0

# How the 11/80 targets with an EMPTY `feasible_objs` are treated. Both are reported.
#   'drop'  — the target contributes no 2x2 table. This is what flip_test_conditional does
#             on its own (rows with attack_n == 0 are dropped). It is also a SELECTIVE drop:
#             all 11 are outright attack failures (delta == 0, success == False, the
#             optimiser never got a feasible candidate past the gate), so dropping them
#             discards the attack's worst targets and biases the result toward the attack.
#   'original' — the target enters with its single trivially-feasible candidate, the
#             ORIGINAL query (feasible by definition, objective == entropy_before). This is
#             the conservative reading and is reported as a sensitivity.
EMPTY_POLICY = ("drop", "original")


class InputMissing(RuntimeError):
    """A required input is absent. Raised — never swallowed into a default."""


# --------------------------------------------------------------------------- inputs

def default_attack_path(tag: str = "_defb") -> Path:
    return DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{tag}" / "triviaqa_se_false_alarm.jsonl"


def load_attack_rows(path: Path) -> list[dict]:
    """Per-target attack records. Fails loudly on a missing/empty file or a wrong cell.

    The `hide` cell is REFUSED rather than handled: there the optimiser maximises
    -entropy, so `feasible_objs` are negated entropies and comparing them to an entropy
    threshold silently inverts the test. The pre-registered tau is also defined for false
    alarms specifically ("a paraphrase pushing a correct answer's score above tau").
    """
    path = Path(path)
    if not path.exists():
        raise InputMissing(
            f"attack campaign JSONL not found: {path}\n"
            f"  Under WSL the definitive cell is\n"
            f"  /home/abhi/.cache/se-research/samples/attacks/wk9_defb/"
            f"triviaqa_se_false_alarm.jsonl\n"
            f"  Pass --path explicitly if you are running against a Windows-visible copy.")
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not rows:
        raise InputMissing(f"attack campaign JSONL is empty: {path}")
    attacks = {r.get("attack") for r in rows}
    if attacks != {"false_alarm"}:
        raise InputMissing(
            f"{path} holds attack cell(s) {sorted(attacks)}; this script is false_alarm only. "
            f"For 'hide' the objective is -entropy, so feasible_objs are NEGATED and the "
            f"crossing direction reverses; that needs its own pre-registered operating point.")
    required = ("question_id", "entropy_before", "entropy_after", "feasible_objs")
    missing = sorted({k for k in required for r in rows if k not in r})
    if missing:
        raise InputMissing(
            f"{path}: records lack {missing}. This needs the INSTRUMENTED optimiser "
            f"(tag _defb); an older uninstrumented run cannot support this test.")
    return rows


def n_candidates_below_clean(rows) -> int:
    """How many recorded attack candidates score BELOW their own target's clean score.

    The exchangeability diagnostic. `se.attacks.optimizer` only records a candidate whose
    objective was >= the running best, and the running best starts at the clean score — so
    under the record filter this count is structurally 0, and a 0 here is the evidence that
    the attack arm is a censored upper tail rather than a candidate sample.
    """
    return sum(1 for r in rows for o in (r.get("feasible_objs") or [])
               if float(o) < float(r["entropy_before"]) - 1e-12)


def fair_pool_clean_scores(labels_path: Path = RELABELED, *, n: int = FAIR_N,
                           seed: int = FAIR_SEED, want: str = "right"):
    """(ids, clean SE scores in nats) for the fair pool's `want` stratum.

    Uses `se.attacks.select._stratum_ids`, the SAME pure function `select_stratified` (and
    therefore `campaign_pool`) uses, so the pool defining tau cannot drift from the pool the
    campaign drew its targets from. Scores are `entropy_nats` from the Week-4 span-oracle
    relabel cache — verified identical to the campaign's own `entropy_before` on all 80
    attacked targets, so tau and the attack candidates live on one scale.
    """
    labels_path = Path(labels_path)
    if not labels_path.exists():
        raise InputMissing(
            f"fair-pool clean scores not found: {labels_path}\n"
            f"  This file (question_id, entropy_nats, greedy_correct) is what defines the "
            f"pre-registered operating point. Without it, pass --tau explicitly; do NOT let "
            f"the script invent a substitute threshold.")
    labels = load_labels(labels_path)
    ids = _stratum_ids(want, seed, labels)[:n]
    if len(ids) < n:
        raise InputMissing(
            f"{labels_path}: only {len(ids)} '{want}' items, need {n} for the fair pool.")
    return ids, np.array([float(labels[q]["entropy_nats"]) for q in ids])


# ------------------------------------------------------------------- operating point

def realised_fpr(scores, tau: float, compare: str = "ge") -> float:
    """Fraction of CORRECT answers the detector would actually flag at tau.

    The deployed convention in `se.stats.flips_at_threshold` is `score >= threshold` fires,
    so 'ge' is the default. This is the number to quote — never the nominal target, which a
    discrete score generally cannot hit.
    """
    s = np.asarray(scores, dtype=float)
    return float((s >= tau).mean() if compare == "ge" else (s > tau).mean())


def attainable_grid(scores, compare: str = "ge") -> list[tuple[float, float]]:
    """Every threshold the score can actually take, with its realised FPR. Ascending.

    Printing this is the whole defence against quoting an operating point that does not
    exist: at N=10 the FPR does not vary continuously, it steps.
    """
    return [(float(v), realised_fpr(scores, float(v), compare))
            for v in sorted(set(float(x) for x in np.asarray(scores, dtype=float)))]


def smallest_threshold_at_most_fpr(scores, target_fpr: float, compare: str = "ge"):
    """Smallest ATTAINABLE threshold whose realised FPR is <= target. None if none is.

    This is the honest reading of "an operating point at 10% FPR" for a discrete score,
    and it is exactly the reading that lands on the ceiling here — which is the finding.
    """
    for thr, fpr in attainable_grid(scores, compare):
        if fpr <= target_fpr:
            return thr
    return None


def compute_tau(scores, target_fpr: float = 0.10, compare: str = "ge") -> dict:
    """The pre-registered tau plus everything needed to read it honestly."""
    s = np.asarray(scores, dtype=float)
    tau = float(operating_point([0] * len(s), s, target_fpr=target_fpr))
    strict = smallest_threshold_at_most_fpr(s, target_fpr, compare)
    return {
        "tau": tau,
        "target_fpr": float(target_fpr),
        "realised_fpr": realised_fpr(s, tau, compare),
        "n_scores": int(len(s)),
        "n_distinct": int(len(set(s.tolist()))),
        "tau_at_most_target_fpr": strict,
        "realised_fpr_at_most": (realised_fpr(s, strict, compare) if strict is not None
                                 else float("nan")),
        "tau_is_interior": bool(tau < CAP - 1e-9),
        "at_most_is_ceiling": (strict is not None and strict >= CAP - 1e-9),
    }


# ------------------------------------------------------------------ crossing counts

def crossing_counts(rows, tau: float, *, compare: str = "ge",
                    empty_policy: str = "drop") -> list[dict]:
    """Per target: how many attack candidates crossed tau, and how many there were.

    `feasible_objs` is the per-candidate objective from the instrumented optimiser; for the
    false-alarm cell the objective IS the entropy in nats (`se.attacks.objectives`: hide
    passes -entropy, false_alarm passes +entropy), so it is directly comparable to tau.

    See the module docstring: this arm is a RUNNING-RECORD subset, not a candidate sample.
    """
    if empty_policy not in EMPTY_POLICY:
        raise ValueError(f"empty_policy must be one of {EMPTY_POLICY}")
    out = []
    for r in rows:
        objs = [float(x) for x in (r.get("feasible_objs") or [])]
        was_empty = not objs
        if was_empty and empty_policy == "original":
            objs = [float(r["entropy_before"])]          # the trivially-feasible candidate
        crossed = sum(1 for o in objs if (o >= tau if compare == "ge" else o > tau))
        out.append({
            "question_id": r.get("question_id"),
            "attack_crossed": int(crossed),
            "attack_n": int(len(objs)),
            "empty_feasible_objs": bool(was_empty),
            "entropy_before": float(r["entropy_before"]),
            "entropy_after": float(r["entropy_after"]),
            "clean_already_flagged": bool(
                float(r["entropy_before"]) >= tau if compare == "ge"
                else float(r["entropy_before"]) > tau),
            "n_feasible_at_best": int(r.get("n_feasible_at_best") or 0),
            "n_objective_calls": int(r.get("n_objective_calls") or 0),
            "success": bool(r.get("success")),
            "status_held": bool(r.get("status_held")),
        })
    return out


def load_benign_crossings(path, tau: float, *, compare: str = "ge",
                          arm: str = "nli") -> dict[str, tuple[int, int]]:
    """{question_id: (benign_crossed, benign_n)} from a null-control checkpoint JSONL.

    `scripts/null_control.py` stores per-target `baseline[arm]` (a FRESH re-evaluation of
    the original question) and `benign[arm]`, a list of intended-direction MOVES of K
    unoptimised feasible paraphrases. For false_alarm, move = after - before, so the
    paraphrase's absolute score is `baseline + move` — an N=10 entropy on the same scale as
    tau and as the attack candidates.
    """
    path = Path(path)
    if not path.exists():
        raise InputMissing(
            f"benign arm not found: {path}\n"
            f"  It is produced by scripts/null_control.py (--checkpoint auto writes "
            f"results/null_control_ckpt<tag>.jsonl). Until that run exists the crossing "
            f"test has only one arm and is NOT evaluable.")
    out: dict[str, tuple[int, int]] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        if rec.get("attack") != "false_alarm":
            continue
        base = (rec.get("baseline") or {}).get(arm)
        moves = (rec.get("benign") or {}).get(arm) or []
        if base is None or not moves:
            continue
        vals = [float(base) + float(m) for m in moves]
        k = sum(1 for v in vals if (v >= tau if compare == "ge" else v > tau))
        out[rec["question_id"]] = (int(k), int(len(vals)))
    if not out:
        raise InputMissing(
            f"{path} has no usable false_alarm benign records under arm '{arm}'.")
    return out


def assemble_arms(per_target, benign: dict[str, tuple[int, int]] | None):
    """Four parallel lists in flip_test_conditional's argument order."""
    ac, an, bc, bn = [], [], [], []
    for t in per_target:
        k, m = (benign or {}).get(t["question_id"], (0, 0))
        ac.append(t["attack_crossed"]); an.append(t["attack_n"])
        bc.append(k); bn.append(m)
    return ac, an, bc, bn


# ------------------------------------------------------------------------- reporting

def _banner(lines: list[str]) -> None:
    w = max(len(x) for x in lines) + 2
    print("+" + "-" * w + "+")
    for x in lines:
        print("| " + x.ljust(w - 1) + "|")
    print("+" + "-" * w + "+")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", default="_defb",
                    help="campaign tag; the cell dir is attacks/wk9<tag> (default _defb)")
    ap.add_argument("--path", default="",
                    help="explicit attack JSONL (for Windows-visible copies)")
    ap.add_argument("--labels", default=str(RELABELED),
                    help="relabel cache holding the fair-pool clean scores")
    ap.add_argument("--benign", default="",
                    help="null-control checkpoint JSONL supplying the benign arm")
    ap.add_argument("--benign-arm", default="nli",
                    choices=["nli", "exact", "embed", "judge"],
                    help="which clusterer arm of the null control to read")
    ap.add_argument("--tau", type=float, default=None,
                    help="override the pre-registered operating point (diagnostic only)")
    ap.add_argument("--target-fpr", type=float, default=0.10,
                    help="pre-registered FPR on fair-pool correct answers (default 0.10)")
    ap.add_argument("--compare", default="ge", choices=["ge", "gt"],
                    help="detector fires at score >= tau ('ge', the repo convention) or > tau")
    ap.add_argument("--fair-n", type=int, default=FAIR_N)
    ap.add_argument("--json", default="", help="also write the full result as JSON here")
    args = ap.parse_args(argv)

    _banner([
        "DISCLOSED, OUTCOME-TRIGGERED SECONDARY DIAGNOSTIC — NOT THE CLAIM STATISTIC.",
        "Trigger (named, not hidden): 52.5% of _defb false-alarm targets finish at the",
        "log(10)=2.3026 ceiling, so a nats effect size is right-censored.",
        "The PRIMARY statistic remains the randomised-tie exceedance test",
        "(critique_log 26a, se.stats.exceedance_test_over_seeds).",
        "Nothing below is a verdict on the attack.",
    ])
    print()

    path = Path(args.path) if args.path else default_attack_path(args.tag)
    rows = load_attack_rows(path)
    print(f"attack cell   : {path}")
    print(f"targets       : {len(rows)}")
    sat = ceiling_saturation([r["entropy_after"] for r in rows], CAP_N)
    print(f"saturation    : {sat:.1%} of targets at the log({CAP_N}) ceiling "
          f"({round(sat * len(rows))}/{len(rows)}) — the trigger for this diagnostic")
    print()

    # ---- operating point -------------------------------------------------------
    print("== PRE-REGISTERED OPERATING POINT (docs/critique_log.md entry 32) ==")
    tau_info = None
    if args.tau is not None:
        tau = float(args.tau)
        print(f"tau           : {tau:.6f}  (OVERRIDDEN via --tau; not the pre-registration)")
    else:
        ids, scores = fair_pool_clean_scores(Path(args.labels), n=args.fair_n)
        tau_info = compute_tau(scores, args.target_fpr, args.compare)
        tau = tau_info["tau"]
        attacked = {r["question_id"] for r in rows}
        overlap = len(attacked & set(ids))
        by_id = dict(zip(ids, scores))
        held_ids = [q for q in ids if q not in attacked]
        held = np.array([by_id[q] for q in held_ids])
        tau_held = compute_tau(held, args.target_fpr, args.compare)

        print(f"definition    : fair-pool clean-score threshold at {args.target_fpr:.0%} FPR "
              f"on correct answers")
        print(f"fair pool     : {len(ids)} score-independent correct-answer items "
              f"({tau_info['n_distinct']} distinct scores)")
        print(f"tau           : {tau:.6f} nats")
        print(f"REALISED FPR  : {tau_info['realised_fpr']:.1%}  "
              f"<-- QUOTE THIS, NOT '{args.target_fpr:.0%}'")
        print()
        print("  [W1] tau is NOT independent of the attacked targets, contrary to entry 32.")
        print(f"       {overlap}/{len(attacked)} attacked targets are IN the {len(ids)}-item "
              f"pool that defines tau")
        print(f"       (they are its first {overlap} draws — same seed, same shuffle).")
        print(f"       tau on the {len(held_ids)} never-attacked fair-pool items: "
              f"{tau_held['tau']:.6f} (realised FPR {tau_held['realised_fpr']:.1%})")
        print()
        print("  [W2] a 10% FPR operating point is NOT ATTAINABLE — the score is discrete.")
        print("       attainable thresholds near the top of the fair pool:")
        for thr, fpr in attainable_grid(scores, args.compare)[-5:]:
            mark = "  <- tau" if abs(thr - tau) < 1e-9 else ""
            mark += "  (= log(10) ceiling)" if thr >= CAP - 1e-9 else ""
            print(f"         thr={thr:.6f}   realised FPR={fpr:6.1%}{mark}")
        print()
        strict = tau_info["tau_at_most_target_fpr"]
        print(f"  [W3] smallest threshold with realised FPR <= {args.target_fpr:.0%}: "
              f"{strict if strict is None else f'{strict:.6f}'} "
              f"(FPR {tau_info['realised_fpr_at_most']:.1%})")
        if tau_info["at_most_is_ceiling"]:
            print("       That threshold IS the log(10) ceiling, so at a true <=10% FPR the")
            print("       crossing test LOSES its censoring-immunity: with '>' nothing can")
            print("       cross the maximum attainable score, and with '>=' 'crossed' is")
            print("       identical to 'saturated'. Censoring-immunity needs tau strictly")
            print("       INTERIOR to the attainable range. The quantile-rule tau above is")
            print("       interior; this one is not. Proceeding with the interior tau.")
        print()

    # ---- attack arm ------------------------------------------------------------
    print("== ATTACK ARM ==")
    per_target = crossing_counts(rows, tau, compare=args.compare, empty_policy="drop")
    n_empty = sum(1 for t in per_target if t["empty_feasible_objs"])
    used = [t for t in per_target if t["attack_n"] > 0]
    tot_n = sum(t["attack_n"] for t in used)
    tot_c = sum(t["attack_crossed"] for t in used)
    op = ">=" if args.compare == "ge" else ">"
    print(f"crossing rule : candidate objective {op} tau  "
          f"(false_alarm objective == entropy, se.attacks.objectives)")
    print(f"targets with candidates : {len(used)}/{len(rows)}")
    print(f"attack candidates       : {tot_n}   crossed: {tot_c} "
          f"({tot_c / max(1, tot_n):.1%})")
    print(f"targets with >=1 crossing: {sum(1 for t in used if t['attack_crossed'] > 0)}"
          f"/{len(used)}")
    print(f"targets already flagged clean (entropy_before {op} tau): "
          f"{sum(1 for t in used if t['clean_already_flagged'])}")
    print()
    print(f"EMPTY feasible_objs     : {n_empty}/{len(rows)} targets")
    print("  treatment (primary)   : DROPPED. flip_test_conditional drops any row with")
    print("                          attack_n == 0, so these contribute no 2x2 table.")
    empt = [t for t in per_target if t["empty_feasible_objs"]]
    print(f"  what they are         : all {len(empt)} are outright attack failures — "
          f"success={sum(t['success'] for t in empt)}/{len(empt)}, "
          f"entropy_after == entropy_before in "
          f"{sum(1 for t in empt if abs(t['entropy_after'] - t['entropy_before']) < 1e-12)}"
          f"/{len(empt)}.")
    print("  so the drop is SELECTIVE and biases toward the attack; the 'original-query'")
    print("  sensitivity below re-enters them with their one trivially-feasible candidate.")
    alt = crossing_counts(rows, tau, compare=args.compare, empty_policy="original")
    alt_used = [t for t in alt if t["attack_n"] > 0]
    print(f"  sensitivity           : {len(alt_used)} targets, "
          f"{sum(t['attack_n'] for t in alt_used)} candidates, "
          f"{sum(t['attack_crossed'] for t in alt_used)} crossings")
    print()
    n_below = n_candidates_below_clean(rows)
    _banner([
        "CAVEAT ON THE ATTACK ARM — read before any p-value.",
        "feasible_objs is a RUNNING-RECORD subset: se.attacks.optimizer records a",
        "candidate only if it scored >= the running best AND passed the gate. Measured",
        f"here: {n_below} of {tot_n} recorded candidates fall below their target's own clean",
        "score. flip_test_conditional's null assumes the two arms are exchangeable; a",
        "monotone record filter on one arm breaks that upward even under H0. Treat any",
        "p-value from this arm as an UPPER BOUND on the evidence.",
    ])
    print()

    # ---- benign arm ------------------------------------------------------------
    print("== BENIGN ARM ==")
    benign = None
    if args.benign:
        benign = load_benign_crossings(args.benign, tau, compare=args.compare,
                                       arm=args.benign_arm)
        matched = sum(1 for t in used if t["question_id"] in benign)
        print(f"source        : {args.benign}  (arm '{args.benign_arm}')")
        print(f"matched       : {matched}/{len(used)} targets")
        print(f"benign draws  : {sum(m for _, m in benign.values())}   crossed: "
              f"{sum(k for k, _ in benign.values())}")
    else:
        print("NOT AVAILABLE — and NOT faked.")
        print("  The attack campaign JSONL carries no benign draws: the per-target benign")
        print("  arm comes from scripts/null_control.py, which writes baseline + per-target")
        print("  benign MOVE lists to results/null_control_ckpt<tag>.jsonl. That run has not")
        print("  produced output yet (the _defb chain is still in its recompute_fair phase),")
        print("  so the crossing test has one arm and is NOT EVALUABLE.")
        print("  TODO: re-run with --benign results/null_control_ckpt_defb.jsonl once the")
        print("  null control completes. This script already reads that format.")
    print()

    # ---- the test --------------------------------------------------------------
    print("== flip_test_conditional (exact stratified hypergeometric) ==")
    ac, an, bc, bn = assemble_arms(per_target, benign)
    res = flip_test_conditional(ac, an, bc, bn)
    for k, v in res.items():
        print(f"  {k:24s} {v}")
    if not res.get("n_targets"):
        print()
        print("  n_targets == 0: every row was dropped because one arm has size 0. With no")
        print("  benign draws that is the CORRECT and expected outcome, not a bug — the")
        print("  conditional null is defined on 2x2 tables and there is no second column.")
        print("  The attack-arm counts printed above are DESCRIPTIVE ONLY. No p-value has")
        print("  been computed and none should be quoted.")
    print()
    _banner([
        "Reminder: secondary diagnostic. The claim statistic is the randomised-tie",
        "exceedance test. Do not present the above as a verdict on the attack.",
    ])

    if args.json:
        payload = {
            "status": "disclosed outcome-triggered secondary diagnostic; "
                      "primary = randomised-tie exceedance test",
            "attack_path": str(path), "tag": args.tag, "compare": args.compare,
            "tau": tau, "tau_info": tau_info, "saturation": sat,
            "n_targets_total": len(rows), "n_empty_feasible_objs": n_empty,
            "attack_candidates": tot_n, "attack_crossings": tot_c,
            "benign_available": benign is not None,
            "flip_test_conditional": res,
            "per_target": per_target,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2, default=float),
                                   encoding="utf-8")
        print(f"\nJSON written to {args.json}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InputMissing as exc:
        print(f"\nINPUT MISSING — refusing to proceed:\n  {exc}", file=sys.stderr)
        raise SystemExit(2)
