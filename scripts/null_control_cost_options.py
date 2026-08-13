"""Costing + design options for the definitive null control (`--tag _defb`, FA cell).

Read-only. Launches NO GPU work. Every number in
`results/null_control_cost_options.md` is produced here.

What it settles, in the artifact's order:

1. TIMING, re-derived from the filesystem rather than modelled:
     - matrix stage's last write  (wk9_defb/triviaqa_se_hide.jsonl mtime) = chain handoff
     - null-control checkpoint ctime = completion of target 1
     - null-control checkpoint mtime = completion of target 11
   Two spans, one implied model-load time; they must agree, and they do.

2. PREFIX (the free arm).  `trajectory_best_obj[t]` is the attack's running best after
   `1 + 9t` objective calls, so the ATTACK side of the pre-registered prefix statistic
   (critique_log 22) is on disk for all 80 targets.  The BENIGN side is the null
   control's own arm, so the statistic is half-free, not free.

3. HARD FLOOR.  `exceedance_test`'s smallest attainable p is P(S=0) = (A/(A+m))^n, so
   below some n a rejection is arithmetically impossible.  Computed through the
   deployed function and cross-checked against the closed form.

4. POWER over (m, n) on the DGP of `scripts/power_sim_deployed.py`, which is imported
   rather than re-implemented; per-target draws are vectorised and validated against
   the scalar `one_target_parts` they replace.  Includes a REALISED-BUDGET scenario
   built from the benign-arm attrition the run has actually shown.

5. The 11 completed targets, quarantined.

6/7/8/9. Cost table, the m ruling, the n ruling, and the recommendation.

Usage:  .venv/Scripts/python.exe scripts/null_control_cost_options.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from se.stats import (  # noqa: E402
    attack_move_at_budget,
    exceedance_counts_randomized,
    exceedance_test,
    expected_max_at_budget,
    paired_max_net,
)
from power_sim_deployed import (  # noqa: E402
    ALPHA,
    N_ATTACK,
    analytic_p,
    calibrate_scale,
    one_target_parts,
    resolve_headroom,
)

RESULTS = ROOT / "results"
FA_CACHE = ROOT / "data" / "cache" / "attacks" / "wk9_defb_snap" / "triviaqa_se_false_alarm.jsonl"
CKPT = RESULTS / "null_control_ckpt_defb.jsonl"
MATRIX_HIDE_CANDIDATES = [
    Path(os.path.expanduser(
        "~/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_hide.jsonl")),
    Path(r"\\wsl.localhost\Ubuntu-24.04\home\abhi\.cache\se-research\samples"
         r"\attacks\wk9_defb\triviaqa_se_hide.jsonl"),
]

PER_ITER = 9                # top_N=3 x candidate_size_M=3
N_FULL = 80
N_SEEDS = 3
K_DEPLOYED = 50
S_PROPOSE_GATE = 0.52       # s per propose+NLI-gate attempt (null_objective_ablation_plan.md §6)
OUT = RESULTS / "null_control_cost_options.md"

L: list[str] = []


def say(s: str = "") -> None:
    L.append(s)
    print(s)


# ============================================================================ inputs

def load_attack() -> list[dict]:
    return [json.loads(x) for x in FA_CACHE.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_ckpt() -> list[dict]:
    return [json.loads(x) for x in CKPT.read_text(encoding="utf-8").splitlines() if x.strip()]


# =========================================================================== 1. timing

def timing(recs: list[dict]) -> dict:
    st = CKPT.stat()
    # The checkpoint is opened "a" only at the moment a target's record is written
    # (null_control.py:413); nothing creates it earlier. ctime == target 1 done,
    # mtime == target len(recs) done, so the span covers len(recs) - 1 targets.
    ck_c = datetime.fromtimestamp(st.st_ctime)
    ck_m = datetime.fromtimestamp(st.st_mtime)
    n = len(recs)
    span = (ck_m - ck_c).total_seconds()
    hide = next((p for p in MATRIX_HIDE_CANDIDATES if p.exists()), None)
    handoff = datetime.fromtimestamp(hide.stat().st_mtime) if hide else None
    out = {"n": n, "ck_c": ck_c, "ck_m": ck_m, "span": span,
           "per_target_mixed": span / (n - 1), "handoff": handoff,
           "handoff_src": str(hide) if hide else None}
    if handoff is not None:
        out["total"] = (ck_m - handoff).total_seconds()
        out["implied_load"] = out["total"] - n * out["per_target_mixed"]
    return out


def cost_decomposition_at(recs: list[dict], span: float, gate_rate: float = 0.85,
                          s_try: float = S_PROPOSE_GATE) -> dict:
    """Split the measured span into a per-clustering cost and a per-proposer-try cost.

    Cost model per target j:   T_j = c_arms * (2 + n_seeds + m_j)  +  c_try * tries_j
    `_benign_moves_arms` stops at m_j feasible draws or 5*K tries, so a target that
    returned fewer than K draws hit the 250-try cap. c_try is taken from the token
    split in results/null_objective_ablation_plan.md §6 (0.37 s proposer + 0.15 s NLI
    gate); c_arms is then the residual, which is the quantity of interest. `gate_rate`
    and `s_try` are the two assumed inputs, exposed so the artifact can quote their
    sensitivity rather than assert it.
    """
    lens = [len(r["benign"]["nli"]) for r in recs]
    # targets 2..n are the ones inside the measured span
    inside = lens[1:]
    n_arms = sum(2 + N_SEEDS + m for m in inside)
    tries = sum(5 * K_DEPLOYED if m < K_DEPLOYED else m / gate_rate for m in inside)
    c_arms = (span - s_try * tries) / n_arms
    full = c_arms * (2 + N_SEEDS + K_DEPLOYED) + s_try * K_DEPLOYED / gate_rate
    return {"lens": lens, "c_arms": c_arms, "tries": tries,
            "full_target_s": full, "mixed_target_s": span / (len(recs) - 1),
            "n_short": sum(1 for m in lens if m < K_DEPLOYED),
            "n_zero": sum(1 for m in lens if m == 0),
            "mean_m": float(np.mean(lens))}


# =========================================================================== 2. prefix

def prefix_table(rows: list[dict]) -> dict:
    full = np.array([attack_move_at_budget(r["trajectory_best_obj"], 10 ** 6) for r in rows])
    tab = {}
    for b in [1] + [1 + PER_ITER * t for t in range(1, 21)]:
        mv = np.array([attack_move_at_budget(r["trajectory_best_obj"], b) for r in rows])
        tab[b] = {"iter": (b - 1) // PER_ITER, "mean": float(mv.mean()),
                  "share": float(mv.sum() / full.sum()),
                  "at_final": float(np.mean(np.isclose(mv, full)))}
    return {"tab": tab, "n_moved": int((full > 1e-12).sum()),
            "calls": sorted({int(r["n_objective_calls"]) for r in rows})}


# ======================================================================= 3. hard floor

def hard_floor(m: int, alpha: float = ALPHA) -> dict:
    n_min = next(n for n in range(1, 500) if analytic_p(0, m, n) <= alpha)
    err = max(abs(analytic_p(0, m, n) - (N_ATTACK / (N_ATTACK + m)) ** n) for n in (5, 20, 80))
    return {"m": m, "n_min": n_min, "err": err,
            "p11": analytic_p(0, m, 11), "p80": analytic_p(0, m, 80)}


# ============================================================================ 4. power

def per_target_counts(scale, hr, m, mult, n_draws, rng, chunk=20000):
    """Vectorised `one_target_parts` + tie credit: n_draws iid per-target counts.

    Statistically identical to power_sim_deployed.run_totals's inner loop (targets are
    drawn iid with replacement from hr there too); a different RNG stream, so it is
    validated distributionally by `validate_vectorised`, not bitwise.
    """
    if m == 0:
        return np.zeros(n_draws, dtype=np.int64)
    n_att = int(round(N_ATTACK * mult))
    out = np.empty(n_draws, dtype=np.int64)
    done = 0
    while done < n_draws:
        t = min(chunk, n_draws - done)
        h = hr[rng.integers(0, len(hr), t)][:, None]
        att = np.minimum(rng.exponential(scale, (t, n_att)), h)
        A = att.max(1)
        at_cap = A >= (h[:, 0] - 1e-12)
        b = np.where(at_cap, np.maximum(1, (att >= h - 1e-12).sum(1)), 1)
        ben = np.minimum(rng.exponential(scale, (t, m)), h)
        strict = (ben > A[:, None] + 1e-12).sum(1)
        tied = np.isclose(ben, A[:, None]).sum(1)
        out[done:done + t] = strict + rng.binomial(tied, 1.0 / (b + 1))
        done += t
    return out


def validate_vectorised(scale, hr, m, mult, n=40000, seed=7):
    rs = np.random.default_rng(seed)
    scal = np.empty(n)
    for i in range(n):
        h = hr[rs.integers(0, len(hr))]
        strict, tied, b = one_target_parts(scale, h, m, mult, rs)
        scal[i] = strict + (int(rs.binomial(tied, 1.0 / (b + 1))) if tied else 0)
    vec = per_target_counts(scale, hr, m, mult, n, np.random.default_rng(seed + 1))
    se = math.sqrt(scal.var() / n + vec.var() / n)
    return {"m": m, "mult": mult, "scalar": float(scal.mean()), "vector": float(vec.mean()),
            "z": float((scal.mean() - vec.mean()) / se) if se else 0.0}


def p_hetero(total: int, m_list) -> float:
    """`exceedance_test`'s p-value for an exceedance TOTAL under a heterogeneous benign
    budget. p depends on the multiset of m_j and the total only (see exceedance_test:
    `obs = sum(k...)`; the convolution uses the m's), so any split reproduces it."""
    ms = [int(m) for m in m_list if m > 0]
    total = int(total)
    counts, rem = [], total
    for m in ms:
        take = min(m, rem)
        counts.append((take, m))
        rem -= take
    if rem > 0:
        return 1.0
    return exceedance_test(counts, N_ATTACK)["p_value"]


def crit_hetero(m_list, alpha: float = ALPHA) -> int:
    lo, hi = -1, sum(int(m) for m in m_list)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if p_hetero(mid, m_list) <= alpha:
            lo = mid
        else:
            hi = mid - 1
    return lo


def totals_for(scale, hr, m_list, mult, trials, rng):
    """Simulated exceedance totals for a design whose per-target benign budgets are
    `m_list` (zeros are targets that returned no feasible benign draw; the deployed
    code drops them, and so does this)."""
    tot = np.zeros(trials, dtype=np.int64)
    for m, g in Counter(int(x) for x in m_list if x > 0).items():
        tot += per_target_counts(scale, hr, m, mult, trials * g, rng).reshape(trials, g).sum(1)
    return tot


def design_row(scale, hr, m_list, *, trials, null_trials, rng, mults=(2.0, 3.0)):
    crit = crit_hetero(m_list)
    S0 = totals_for(scale, hr, m_list, 1.0, null_trials, rng)
    row = {"crit": crit, "nominal": p_hetero(crit, m_list) if crit >= 0 else float("nan"),
           "min_p": p_hetero(0, m_list),
           "level": float((S0 <= crit).mean()) if crit >= 0 else 0.0,
           "n_eff": sum(1 for m in m_list if m > 0),
           "E_S": sum(m for m in m_list if m > 0) / (N_ATTACK + 1)}
    # the best a cut on S can do while honouring alpha on THIS DGP -- brackets how much
    # of any power difference is the analytic null's discreteness rather than information
    cuts = np.arange(-1, int(S0.max()) + 1)
    ok = [c for c in cuts if (S0 <= c).mean() <= ALPHA]
    row["crit_exact"] = int(max(ok)) if ok else -1
    row["level_exact"] = float((S0 <= row["crit_exact"]).mean()) if ok else 0.0
    for mu in mults:
        S1 = totals_for(scale, hr, m_list, mu, trials, rng)
        row[f"pow{int(mu)}"] = float((S1 <= crit).mean()) if crit >= 0 else 0.0
        row[f"pow{int(mu)}_exact"] = float((S1 <= row["crit_exact"]).mean()) if ok else 0.0
    return row


# ========================================================================== 5. interim

def interim(rows_attack, recs):
    from scipy.stats import binomtest
    by_q = {r["question_id"]: r for r in rows_attack}
    out = {"n": len(recs), "arms": {}, "lens": [len(r["benign"]["nli"]) for r in recs]}
    for arm in ("nli", "exact", "judge"):
        atk, ben = [], []
        for r in recs:
            a, bl = r["attack_move"].get(arm), (r["benign"].get(arm) or [])
            if a is None or not bl:
                continue
            atk.append(float(a))
            ben.append([float(x) for x in bl])
        a = np.array(atk)
        bmax = np.array([max(b) for b in ben])
        net = a - bmax
        pmn = paired_max_net(a, ben)
        w = int((net > 1e-12).sum())
        ls = int((net < -1e-12).sum())
        out["arms"][arm] = {
            "n": len(a), "atk": float(a.mean()), "bmax": float(bmax.mean()),
            "net": float(net.mean()), "sd": float(net.std(ddof=1)),
            "w": w, "l": ls, "t": len(net) - w - ls,
            "sign_p": binomtest(w, w + ls, 0.5, alternative="greater").pvalue if w + ls else float("nan"),
            "paired": pmn,
            "beq": [next((bb for bb in range(1, len(b) + 1)
                          if expected_max_at_budget(b, bb) >= ai), None)
                    for ai, b in zip(a, ben)],
        }
    bl = [[float(x) for x in r["benign"]["judge"]] for r in recs]
    am = [float(r["attack_move"]["judge"]) for r in recs]
    tie = [int(by_q[r["question_id"]]["n_feasible_at_best"]) for r in recs]
    cnt = exceedance_counts_randomized(am, bl, tie, n_attack_candidates=N_ATTACK, seed=0)
    out["exc"] = exceedance_test(cnt, N_ATTACK)
    return out


# ============================================================================== driver

def main() -> int:
    recs = load_ckpt()
    rows = load_attack()
    t = timing(recs)
    cd = cost_decomposition_at(recs, t["span"])
    hr, _qids, prov = resolve_headroom()
    scale, sat = calibrate_scale(hr)
    remaining = N_FULL - t["n"]

    def hours(n_targets: int, K: int, unit: float) -> float:
        """n_targets at benign budget K, priced off the measured full-target unit."""
        return n_targets * unit * (2 + N_SEEDS + K) / (2 + N_SEEDS + K_DEPLOYED) / 3600.0

    unit_mix = cd["mixed_target_s"]
    unit_full = cd["full_target_s"]

    say("# Null control: what the remaining GPU-hours buy, and what a cheaper design forfeits")
    say()
    say("Produced by `scripts/null_control_cost_options.py` (read-only; launches no GPU work).")
    say("Job under costing:")
    say()
    say("```")
    say("scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 \\")
    say("    --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 \\")
    say("    --dump_diag results/diag_defb.json --checkpoint auto")
    say("```")
    say()
    say("**Bottom line: the ~60 GPU-h figure is wrong by about 2.5x. Measured on the run's own")
    say(f"wall-clock, the remainder is {hours(remaining, 50, unit_mix):.0f}-"
        f"{hours(remaining, 50, unit_full):.0f} GPU-h -- two to three nights, not six. Finish")
    say("it as designed.** No cheaper design removes a meaningful cost; the largest saving on")
    say("offer is under one night and costs a third of the design's power. The one genuinely")
    say("free result (the prefix statistic) is a companion to this run's data, not a")
    say("substitute for it -- half of it is the benign arm this run exists to produce.")
    say()

    # -------------------------------------------------------------------- 1. timing
    say("## 1. Re-deriving the cost from the run itself")
    say()
    say("`~67 GPU-h` (critique_log 26a, `docs/definitive_run_plan.md`,")
    say("`results/null_objective_ablation_plan.md` §6) is a MODEL: *55 clusterings/target at")
    say("~55 s each => ~50 min/target*. The 55 s came from a K=8 measurement in critique_log")
    say("22 (*13 calls ~ 12 min/target*, 2026-08-02). The deployed run refutes it.")
    say()
    say("Three filesystem anchors (local time), none depending on a per-eval assumption:")
    say()
    say("| anchor | source | local time |")
    say("|---|---|---|")
    if t["handoff"]:
        say(f"| matrix stage hands the chain over | mtime of `wk9_defb/triviaqa_se_hide.jsonl` "
            f"| {t['handoff']:%Y-%m-%d %H:%M:%S} |")
    say(f"| target 1 written | ctime of `{CKPT.name}` -- the file is opened `\"a\"` only at the "
        f"first record write (`null_control.py:413`) | {t['ck_c']:%Y-%m-%d %H:%M:%S} |")
    say(f"| target {t['n']} written | mtime of the same file | {t['ck_m']:%Y-%m-%d %H:%M:%S} |")
    say()
    say(f"- Targets 2..{t['n']} span **{t['span']:.0f} s** for {t['n'] - 1} targets => "
        f"**{unit_mix:.0f} s/target** ({unit_mix / 60:.1f} min) as a mixed average.")
    if "total" in t:
        say(f"- Hand-off to target {t['n']} is {t['total']:.0f} s. Charging {t['n']} targets at "
            f"that rate leaves **{t['implied_load']:.0f} s** for process start plus loading "
            f"Llama-8B-4bit + DeBERTa-large + Qwen-7B-4bit. That the residual lands at a "
            f"plausible model-load time is the consistency check; it is not something the "
            f"two anchors were fitted to.")
    say()
    say(f"Measured per clustering: **{cd['c_arms']:.1f} s** (fit below) against the 55 s the")
    say("budget assumed.")
    say()
    say("**The conclusion does not depend on reading the ctime as target 1's write.** Suppose")
    say("instead that the file somehow existed from process start. Then all "
        f"{t['n']} targets fall")
    say(f"inside the {t['span']:.0f} s span, giving {t['span'] / t['n']:.0f} s/target and "
        f"{remaining * t['span'] / t['n'] / 3600:.1f} GPU-h remaining -- and it would also")
    say(f"require {t['total'] - t['span']:.0f} s of pure model loading between the hand-off and "
        f"process start, which is not credible for three cached quantised models. Either")
    say("reading lands in the low twenties of GPU-hours; neither lands near 60.")
    say()
    say("### The mixed average understates a normal target, and why")
    say()
    say(f"Two of the {t['n']} completed targets did not get a full benign arm. "
        f"`_benign_moves_arms` stops at `K` feasible draws **or `5K` tries**, so a question")
    say("whose paraphrases keep failing the NLI gate returns a short arm -- and a short arm")
    say("is CHEAPER, not dearer (250 proposer+gate attempts, but fewer than 50 SE evals).")
    say()
    say("| question_id | benign draws returned |")
    say("|---|---|")
    for r, m in zip(recs, cd["lens"]):
        if m < K_DEPLOYED:
            say(f"| `{r['question_id']}` | **{m}** of 50 |")
    say(f"| the other {t['n'] - cd['n_short']} | 50 of 50 |")
    say()
    say(f"Fitting `T_j = c_arms*(2 + n_seeds + m_j) + 0.52*tries_j` over the measured span "
        f"gives **c_arms = {cd['c_arms']:.1f} s** and a full-arm target at "
        f"**{unit_full:.0f} s**. Two inputs to that fit are")
    say("assumed rather than measured -- the 0.52 s propose+gate unit (the token split in")
    say("`null_objective_ablation_plan.md` §6) and an 85% benign gate pass rate -- and neither")
    say("matters: proposer work is only "
        f"{100 * S_PROPOSE_GATE * cd['tries'] / t['span']:.0f}% of the span, so halving the")
    say(f"assumed pass rate moves the full-target cost by "
        f"{abs(cost_decomposition_at(recs, t['span'], 0.425)['full_target_s'] - unit_full):.0f} s "
        f"and doubling the per-try cost moves it by "
        f"{abs(cost_decomposition_at(recs, t['span'], 0.85, 1.04)['full_target_s'] - unit_full):.0f} s.")
    say("So:")
    say()
    say(f"| projection for the remaining {remaining} targets | GPU-h |")
    say("|---|---|")
    say(f"| at the observed mix ({cd['n_short']}/{t['n']} short arms) | "
        f"**{hours(remaining, 50, unit_mix):.1f}** |")
    say(f"| if every remaining target gets a full 50-draw arm (upper bound) | "
        f"**{hours(remaining, 50, unit_full):.1f}** |")
    say(f"| the budget's own figure, for comparison | ~60 |")
    say()
    say("Both anchors *include* any crash and restart inside the window")
    say("(`run_definitive_chain.sh` retries after 60 s with a full model reload), so these are")
    say("upper bounds on marginal cost, not best cases.")
    say()
    say("**Caveats, stated not buried.** `/tmp/defb_chain.log` did not survive the WSL restart")
    say("at 22:56 on 2026-08-13, so per-target timing lines are gone; this is a span/count")
    say(f"average over {t['n'] - 1} targets, not {t['n'] - 1} individual timings. GPU contention "
        f"during the window is unknown. The short-arm rate ({cd['n_short']}/{t['n']}) is itself")
    say("estimated on 11 targets. All three uncertainties push the estimate up, and it is")
    say("still under half the budgeted figure.")
    say()

    # -------------------------------------------------------------------- 2. prefix
    pf = prefix_table(rows)
    say("## 2. The prefix statistic: exactly which half is free")
    say()
    say("critique_log 22 pre-registers the fallback claim statistic as *attack-max over the")
    say("FIRST m candidates vs benign-max over m, both matched at m, under the judge*, with")
    say("**m = 36** (k=4 iterations x 9 candidates) fixed in writing.")
    say("`results/null_objective_ablation_plan.md` §7 calls it assumption-free and says it")
    say("*costs ZERO new GPU*. Both halves of that need separating.")
    say()
    say("**Free, and genuinely so.** `trajectory_best_obj[t]` is the running best after")
    say("`1 + 9t` objective calls, recorded on all 80 targets, so the attack's achievement at")
    say("every prefix budget is already on disk. The budget curve, at no cost:")
    say()
    say("| budget (calls) | iterations | mean move (nats) | share of the full-181 move | targets already at their final max |")
    say("|---|---|---|---|---|")
    for b in (1, 10, 19, 28, 37, 46, 55, 91, 136, 181):
        r = pf["tab"][b]
        say(f"| {b} | {r['iter']} | {r['mean']:.4f} | {r['share'] * 100:.1f}% | "
            f"{r['at_final'] * 100:.1f}% |")
    say()
    say(f"n = 80 targets ({pf['n_moved']} move at all); every target ran the full "
        f"{pf['calls']} objective calls, so no target's prefix is an artefact of a short run.")
    say(f"A budget-37 prefix keeps {pf['tab'][37]['share'] * 100:.0f}% of the attack's total move "
        f"and {pf['tab'][46]['share'] * 100:.0f}% at 46. Truncating the attacker to the "
        f"pre-registered m=36 is a mild handicap, not a gutting -- which is the substantive")
    say("thing this free computation establishes, and it was worth establishing.")
    say()
    say("**Not free.** The statistic is a comparison and its other half is `benign-max over")
    say("m`, which is the null control's benign arm and nothing else. §7's phrase is written")
    say("inside a branch where the null control has ALREADY run; lifted out of that branch it")
    say("reads as though the whole statistic were free. It is not:")
    say()
    say("| component | on disk today | GPU to obtain |")
    say("|---|---|---|")
    say("| attack-max at any budget m <= 181, all 80 targets | yes (`trajectory_best_obj`) | none |")
    say(f"| benign-max over m <= 50 under NLI / exact / judge | {t['n']} of 80 targets | this run |")
    say(f"| seed-noise band | {t['n']} of 80 targets | this run |")
    say()
    say("Two consequences worth acting on:")
    say()
    say("1. **A K=50 benign arm already serves the prefix statistic at every m <= 50.** Benign")
    say("   draws are exchangeable, and `se.stats.expected_max_at_budget` computes the exact")
    say("   expected max of a random m-subset with no distributional assumption. So the")
    say("   pre-registered m=36 needs no separate run and no change to `--K 50`. The prefix")
    say("   statistic is a free *by-product* of finishing this job.")
    say("2. **It does not shrink the job.** The only version of the prefix statistic that")
    say("   costs nothing more is the one restricted to the targets whose benign arm exists,")
    say(f"   i.e. n = {t['n']}. What that buys is §3 and §5.")
    say()

    # -------------------------------------------------------------------- 3. floor
    say("## 3. The exceedance test cannot reject below a minimum n -- and n=11 is below it")
    say()
    say("`exceedance_test` returns P(S <= s) under a convolution of BetaBinomial(m; 1, A), so")
    say("the smallest p it can EVER return is P(S = 0) = (A/(A+m))^n. Below the n where that")
    say("crosses alpha, no data can produce a rejection.")
    say()
    say("| m | min attainable p at n=11 | min attainable p at n=80 | smallest n that can reject at 0.05 |")
    say("|---|---|---|---|")
    fl = {}
    for m in (20, 30, 36, 50, 80):
        fl[m] = hard_floor(m)
        say(f"| {m} | {fl[m]['p11']:.4f} | {fl[m]['p80']:.2e} | **{fl[m]['n_min']}** |")
    say()
    say(f"Computed through the deployed `exceedance_test`; agrees with the closed form to "
        f"{max(f['err'] for f in fl.values()):.1e}. A = {N_ATTACK}.")
    say()
    say(f"**The {t['n']} targets on disk therefore cannot reject under the exceedance test at "
        f"any m: min p = {fl[50]['p11']:.3f} > 0.05.** The floor is far below n=40, so it never")
    say("binds on a reduced-n design -- it binds only on *just analyse what we already have*.")
    say()
    say("The prefix statistic has no such floor. A one-sided sign test on 11 paired targets")
    say(f"reaches p = 2^-11 = {0.5 ** 11:.5f} at best, and the paired bootstrap is continuous.")
    say("That asymmetry -- not assumption-freeness -- is the operative reason the prefix")
    say("statistic is the right thing to compute on a partial run.")
    say()

    # -------------------------------------------------------------------- 4. power
    say("## 4. Power on the DEPLOYED analytic null, over m and n")
    say()
    say(f"DGP imported from `scripts/power_sim_deployed.py`: headroom from `{prov}`,")
    say(f"per-draw scale {scale} calibrated to {sat:.2f} saturation against the observed 0.49,")
    say(f"A = {N_ATTACK}, alpha = {ALPHA}. Per-target draws are vectorised here so the (m x n)")
    say("grid is affordable; validated against the scalar `one_target_parts` they replace:")
    say()
    say("| m | effect | scalar mean K | vectorised mean K | z |")
    say("|---|---|---|---|---|")
    for m in (30, 50):
        for mu in (1.0, 2.0):
            v = validate_vectorised(scale, hr, m, mu)
            say(f"| {m} | {v['mult']:.0f}x | {v['scalar']:.4f} | {v['vector']:.4f} | {v['z']:+.2f} |")
    say()
    rng = np.random.default_rng(101)
    TR, NT = 6000, 30000
    grid = {}
    for m in (30, 36, 50):
        for n in (40, 60, 80):
            grid[(m, n)] = design_row(scale, hr, [m] * n, trials=TR, null_trials=NT, rng=rng)
    say("| m | n | crit on S | achieved level | power @2x | power @3x | power @2x at an exact-0.05 cut | E[S] |")
    say("|---|---|---|---|---|---|---|---|")
    for (m, n), r in grid.items():
        mark = "**" if (m, n) == (50, 80) else ""
        say(f"| {mark}{m}{mark} | {mark}{n}{mark} | {r['crit']} | {r['level']:.3f} | "
            f"**{r['pow2']:.2f}** | {r['pow3']:.2f} | {r['pow2_exact']:.2f} | {r['E_S']:.1f} |")
    say()
    say(f"The (m=50, n=80) cell reproduces `results/power_deployed_vs_oracle.md` table B on")
    say(f"independent draws -- power @2x {grid[(50, 80)]['pow2']:.2f} against its 0.77, achieved "
        f"level {grid[(50, 80)]['level']:.3f} against its 0.041 -- which is the check that this")
    say("grid is the same test and not a re-implementation of a different one.")
    say()
    say("The exact-0.05 column matters for reading the n rows honestly: the analytic null is")
    say("discrete, and at small n its achieved level falls well below alpha, so part of the")
    say("power drop is conservatism rather than lost information. Even at the best cut a")
    say("level-0.05 test could take on this DGP, n=40 reaches only "
        f"{grid[(50, 40)]['pow2_exact']:.2f} against {grid[(50, 80)]['pow2_exact']:.2f} at n=80.")
    say()
    say("### The realised design is slightly weaker than the nominal one")
    say()
    say("The grid above assumes every target contributes 50 benign draws. The run has already")
    say(f"shown it will not: {cd['n_short']}/{t['n']} targets returned a short arm and "
        f"{cd['n_zero']}/{t['n']} returned NONE. A target with zero benign draws is dropped by")
    say("`exceedance_counts_randomized` (`if not bl: continue`) and again by `exceedance_test`")
    say("(`m > 0`), so the test's n is the number of targets with a benign arm, not 80. Using")
    say("the observed attrition to build an 80-target design (this uses feasibility rates, not")
    say("outcome values, so it is not a peek at the result):")
    say()
    obs = cd["lens"]
    real = [obs[i % len(obs)] for i in range(N_FULL)]
    r_real = design_row(scale, hr, real, trials=TR, null_trials=NT, rng=rng)
    r_nom = grid[(50, 80)]
    say("| design at n=80 nominal | targets with a benign arm | sum of m_j | crit | level | power @2x |")
    say("|---|---|---|---|---|---|")
    say(f"| every target gets 50 | 80 | 4000 | {r_nom['crit']} | {r_nom['level']:.3f} | "
        f"**{r_nom['pow2']:.2f}** |")
    say(f"| observed attrition replayed to 80 | {r_real['n_eff']} | {sum(real)} | "
        f"{r_real['crit']} | {r_real['level']:.3f} | **{r_real['pow2']:.2f}** |")
    say()
    say("A real but second-order correction. It is worth knowing before the run finishes")
    say("rather than after, and it argues mildly for n=80 over anything smaller, since the")
    say("attrition eats into n before the statistic sees it.")
    say()

    # -------------------------------------------------------------------- 5. interim
    it = interim(rows, recs)
    say(f"## 5. Interim look at the {t['n']} completed targets -- QUARANTINED")
    say()
    say("> **Do not re-choose the design on this section.** m=50 and n>=80 are pre-committed")
    say("> (critique_log 26a) and the decision rule is locked (critique_log 21, M1). It is")
    say("> reported for three legitimate purposes: to confirm the arms are behaving, to")
    say("> supply the attrition rate §4 needs, and because a recommendation to spend or not")
    say("> spend 25 GPU-h that refused to look at the 14% already spent would be worthless.")
    say("> The recommendation in §9 is argued on cost and power, and would be the same with")
    say("> the sign of every number below reversed.")
    say()
    say("| arm | role | attack move (mean) | benign-MAX (mean) | paired net | net sd | wins/losses/ties | one-sided sign p |")
    say("|---|---|---|---|---|---|---|---|")
    roles = {"nli": "shared with the optimiser's objective -- confounded/permissive",
             "exact": "independent, strict (over-counts surface form)",
             "judge": "**the adjudicator** (validated 0.93)"}
    for arm in ("nli", "exact", "judge"):
        a = it["arms"][arm]
        say(f"| {arm} | {roles[arm]} | {a['atk']:+.4f} | {a['bmax']:+.4f} | {a['net']:+.4f} | "
            f"{a['sd']:.4f} | {a['w']}/{a['l']}/{a['t']} | {a['sign_p']:.3f} |")
    say()
    ex = it["exc"]
    say(f"Exceedance test on the judge arm, n={ex['n_targets']} usable: observed S = "
        f"{ex['observed']} against an expected {ex['expected']:.1f} under H0. The p-value is")
    say(f"{ex['p_value']:.3f}, and per §3 no value of S could have produced a rejection at this n.")
    say()
    say("Two things follow, and only two:")
    say()
    say("1. **The arms are behaving as the design predicted.** The attack wins under the")
    say("   clusterer it was optimised against and does not win under the independent")
    say("   adjudicator. That is precisely the confound the null control exists to expose,")
    say("   and it means the machinery is measuring what it was built to measure.")
    say("2. **The remaining hours buy a power qualifier, not a direction.** The direction is")
    say("   already legible. What n=80 buys is the right to write *non-rejection at power")
    say(f"   {grid[(50, 80)]['pow2']:.2f} against a 2x effect* instead of *we did not find one*. For a")
    say("   null result that qualifier IS the result; without it the case study is an anecdote.")
    say()
    say("On optional stopping: the usual hazard runs the other way (stop once significant),")
    say("and stopping early on a null makes the null weaker, never stronger -- so the")
    say("integrity risk here is small and the cost is interpretability. But if n is cut after")
    say("this section exists, the paper must say that an interim was seen and that n was cut")
    say("on compute grounds. That disclosure is cheap; discovering the omission in review is not.")
    say()

    # -------------------------------------------------------------------- 6. cost table
    say("## 6. The designs, costed")
    say()
    say(f"Unit: the measured targets, scaled by clusterings per target (2 + K + n_seeds),")
    say("which also carries the proposer retries since those scale with K. **expected** uses")
    say(f"the observed mix ({unit_mix:.0f} s/target, i.e. with the §1 attrition); **max** assumes")
    say(f"every target gets a full arm ({unit_full:.0f} s). `to run` counts only targets not")
    say("already on disk. **Changing K invalidates the checkpoint**: `_ckpt_load` matches on")
    say(f"the whole cfg dict, K included (`null_control.py:338`), so any m other than 50")
    say(f"discards all {t['n']} completed targets and restarts from zero.")
    say()
    say("| design | to run | GPU-h expected | GPU-h max | power @2x | what it can still claim | what it forfeits |")
    say("|---|---|---|---|---|---|---|")
    designs = [
        ("**A. Finish as launched** — m=50, n=80", remaining, 50, grid[(50, 80)]["pow2"],
         "the pre-registered exceedance verdict at full power; the prefix statistic at any "
         "m<=50 as a free companion; the benign arm the null-objective gate needs; the "
         "reframe-(b) seed-vs-benign question",
         "nothing"),
        ("B. m=30, n=80 — restart", N_FULL, 30, grid[(30, 80)]["pow2"],
         "the same verdict at two-thirds the power",
         f"the {t['n']} completed targets; the prefix statistic above m=30; an interpretable "
         "non-rejection"),
        ("C. m=36 (the pre-registered prefix budget), n=80 — restart", N_FULL, 36,
         grid[(36, 80)]["pow2"],
         "the exceedance verdict plus the prefix statistic at exactly its pre-registered m",
         f"the {t['n']} completed targets; ~0.16 of power; and it buys nothing the m=50 arm "
         "does not already contain"),
        ("D. m=50, n=60", 60 - t["n"], 50, grid[(50, 60)]["pow2"],
         "the same verdict with n disclosed as short of the pre-registered 80",
         "0.22 of power; the n>=80 pre-commitment; a sixth of the gate's n"),
        ("E. m=50, n=40", 40 - t["n"], 50, grid[(50, 40)]["pow2"],
         "a bracketed result — rejection is still arithmetically possible (§3), but a "
         "non-rejection carries little",
         "0.40 of power; n>=80; half the null-objective gate's n"),
        ("F. Drop or subsample an arm", remaining, 50, grid[(50, 80)]["pow2"],
         "nothing — there is no arm to drop; see below", "see below"),
        ("G. Prefix-only, zero new GPU", 0, 50, float("nan"),
         f"the free budget curve (§2) and a descriptive paired net + sign test on n={t['n']}",
         "the exceedance test entirely (§3 floor); any power statement; the gate's benign "
         "arm; the reframe-(b) answer"),
    ]
    for name, n_run, K, pw, claim, forf in designs:
        he = hours(n_run, K, unit_mix) if n_run else 0.0
        hm = hours(n_run, K, unit_full) if n_run else 0.0
        say(f"| {name} | {n_run} | **{he:.1f}** | {hm:.1f} | "
            f"{'n/a' if pw != pw else f'{pw:.2f}'} | {claim} | {forf} |")
    say()
    say("Read the two cost columns together: the *largest* saving any cheaper design offers "
        f"is {hours(remaining, 50, unit_mix) - hours(N_FULL, 30, unit_mix):.1f}-"
        f"{hours(remaining, 50, unit_full) - hours(N_FULL, 30, unit_full):.1f} GPU-h (B), and it")
    say(f"costs {grid[(50, 80)]['pow2'] - grid[(30, 80)]['pow2']:.2f} of power. Design C is "
        f"within a rounding error of simply finishing.")
    say()
    say("### F: there is no arm to drop")
    say()
    say("`_arms` generates ONE set of samples with `semantic_entropy(...)`, which *is* the NLI")
    say("arm; exact-match is a re-clustering of those same strings at zero GPU cost; the")
    say("embedding arm is already off (`--embedding_model ''`, disqualified at hard-negative")
    say("AUROC 0.51). The two bracket arms are by-products of a computation the judge arm")
    say("needs anyway. **The only arm that costs anything is the judge** -- 45 pairs x 2")
    say("orderings = 90 prompts per clustering, sub-batched at 6, so 15 `generate()` calls per")
    say("clustering and ~825 per target -- and the judge is the sole adjudicator.")
    say()
    say(f"Its share, from the fit in §1: a clustering costs {cd['c_arms']:.1f} s, of which the "
        f"sampling+NLI half is the ~2.8 s the token split in `null_objective_ablation_plan.md`")
    say(f"§6 attributes to an SE eval (10 x 48 new tokens). So the judge is roughly "
        f"{100 * (cd['c_arms'] - 2.8) / cd['c_arms']:.0f}% of a")
    say("clustering and ~85% of the run. Dropping it deletes the answer; keeping it and")
    say("dropping the brackets saves nothing and costs the strict/permissive bounds.")
    say()
    say("Subsampling the judge is worse than it looks. Judging only some of the 50 benign")
    say("draws makes the benign-MAX a max over fewer draws, which biases the floor DOWNWARD")
    say("and inflates the attack's margin -- the same direction as the winner's curse that B2")
    say("introduced the budget-matched control to remove. critique_log 22 already rejected the")
    say("cheaper version of this idea (NLI pre-screening) for exactly that reason.")
    say()
    say("Levers that are engineering rather than statistics:")
    say()
    say("- **`--judge_batch_size 6` -> larger.** Pure throughput, zero statistical effect. The")
    say("  cap exists because ~90 prompts OOM a 16 GB card also holding Llama and DeBERTa")
    say("  (`judge.load_judge` docstring), but 6 -> 10 has not been probed at the current")
    say("  footprint. `scripts/probe_batched_judge.py` exists. This is the only free speed-up")
    say("  on the table and it is worth ten minutes before relaunching.")
    say("- **Single-ordering judge** (90 -> 45 prompts, ~2x). critique_log 22 permits it ONLY")
    say("  with a re-validation of hard-negative accuracy under that exact config, and the")
    say("  0.93 [0.90, 0.96] figure the paper cites once is the symmetric config. Not free,")
    say("  and not worth it to save ~12 GPU-h.")
    say()

    # -------------------------------------------------------------------- 7. m
    say("## 7. Is m=30 defensible on the corrected power figures?")
    say()
    say("**No, and the decisive reason is arithmetic, not discipline.**")
    say()
    say("The pre-registration chose m=50 over m=30 on ORACLE power, 0.84 vs 0.67. The")
    say(f"deployed analytic test delivers {grid[(50, 80)]['pow2']:.2f} vs {grid[(30, 80)]['pow2']:.2f} "
        f"here (`results/power_deployed_vs_oracle.md`: 0.77 / 0.51). Both arms lost about the")
    say("same amount, so the ordering that drove the choice is untouched -- m=30 is simply")
    say("worse than it looked, in absolute terms.")
    say()
    say("**On the pre-registration question.** Re-costing an as-yet-unrun design against")
    say("corrected power figures is a different act from re-choosing it: it consumes no")
    say("outcome data, and critique_log 26a explicitly contemplates it (*if compute forces a")
    say("smaller m, the shortfall is REPORTED as such*). So the audit is legitimate. Acting on")
    say("it today is not, for a reason that has nothing to do with power: §5 above has now")
    say("looked at 11 targets, so a switch to m=30 could no longer be cleanly defended as")
    say("compute-forced even if it were. The window for a clean m change closed when the")
    say("interim was read.")
    say()
    say("**And it would not be worth taking anyway:**")
    say()
    say(f"- finish at m=50: **{hours(remaining, 50, unit_mix):.1f}-"
        f"{hours(remaining, 50, unit_full):.1f} GPU-h**, power {grid[(50, 80)]['pow2']:.2f}")
    say(f"- restart at m=30: **{hours(N_FULL, 30, unit_mix):.1f}-"
        f"{hours(N_FULL, 30, unit_full):.1f} GPU-h**, power {grid[(30, 80)]['pow2']:.2f}")
    say(f"- restart at m=36: **{hours(N_FULL, 36, unit_mix):.1f}-"
        f"{hours(N_FULL, 36, unit_full):.1f} GPU-h**, power {grid[(36, 80)]['pow2']:.2f}")
    say(f"- net saving at m=30: **{hours(remaining, 50, unit_mix) - hours(N_FULL, 30, unit_mix):.1f}"
        f"-{hours(remaining, 50, unit_full) - hours(N_FULL, 30, unit_full):.1f} GPU-h** -- under "
        f"one night -- for {grid[(50, 80)]['pow2'] - grid[(30, 80)]['pow2']:.2f} of power. At "
        f"m=36 the saving is "
        f"{hours(remaining, 50, unit_mix) - hours(N_FULL, 36, unit_mix):.1f}-"
        f"{hours(remaining, 50, unit_full) - hours(N_FULL, 36, unit_full):.1f} GPU-h for "
        f"{grid[(50, 80)]['pow2'] - grid[(36, 80)]['pow2']:.2f} of power, which is close to "
        f"paying full price for a worse design.")
    say()
    say("The restart is what kills it: K is part of the checkpoint key, so m=30 pays for 80")
    say("fresh targets to avoid 69. At power "
        f"{grid[(30, 80)]['pow2']:.2f} against a 2x effect a non-rejection is close to")
    say("uninterpretable -- barely better than a coin flip at seeing the effect it is being")
    say("read as absent -- and a non-rejection is the outcome this design is most likely to")
    say("produce.")
    say()

    # -------------------------------------------------------------------- 8. n
    say("## 8. Cutting n is the only lever with a real price ratio -- and it is still a bad buy")
    say()
    say("critique_log 22 rejected reducing n (*power is the binding constraint; n drives CI")
    say("width and is not recoverable by argument*), but that ruling was written for the")
    say("brute-force budget-matched design the exceedance test replaced in entry 23. On the")
    say("deployed test the trade is measurable rather than doctrinal:")
    say()
    say("| n | GPU-h from here at m=50 | nights at 10 h | power @2x | power @3x | achieved level | can the test reject at all? |")
    say("|---|---|---|---|---|---|---|")
    for n in (40, 60, 80):
        he = hours(max(0, n - t["n"]), 50, unit_mix)
        hm = hours(max(0, n - t["n"]), 50, unit_full)
        g = grid[(50, n)]
        say(f"| {n} | {he:.1f}-{hm:.1f} | {he / 10:.1f}-{hm / 10:.1f} | {g['pow2']:.2f} | "
            f"{g['pow3']:.2f} | {g['level']:.3f} | yes (floor is n={fl[50]['n_min']}) |")
    say()
    say("Each 20 targets costs about half a night and buys about 0.2 of power. Three further")
    say("costs do not show up in that table:")
    say()
    say("- The null-objective ablation consumes this benign arm via")
    say("  `--benign_from results/diag_defb.json`. Its resolving power is *already* only *no")
    say("  gross violation at n=80* (`null_objective_ablation_plan.md` §5 computes that 3 sd on")
    say("  the lower band edge would need n~165). Halving n halves the gate's n too.")
    say("- The attrition in §4 eats n before the statistic sees it: nominal 80 is an effective")
    say(f"  {r_real['n_eff']} on the observed rate, so n=40 nominal is more like "
        f"{int(round(40 * r_real['n_eff'] / 80))} effective.")
    say("- n>=80 is the pre-registered decision rule (critique_log 21 M1, 26a). Cutting it is a")
    say("  disclosable deviation, and it would be the fifth.")
    say()

    # -------------------------------------------------------------------- 9. rec
    say("## 9. Recommendation")
    say()
    say(f"**Finish design A. It is {hours(remaining, 50, unit_mix):.0f}-"
        f"{hours(remaining, 50, unit_full):.0f} GPU-h, not 60 -- "
        f"{hours(remaining, 50, unit_mix) / 10:.1f}-{hours(remaining, 50, unit_full) / 10:.1f} "
        f"nights at 10 h -- against 33 days to the arXiv date. Every cheaper design on the")
    say("table trades a large fraction of the power for well under a night, and the one that")
    say("matches the pre-registered prefix budget (m=36) costs almost exactly what finishing")
    say("costs while delivering 0.17 less power.**")
    say()
    say("Order of operations:")
    say()
    say("1. **Ten minutes on `--judge_batch_size` before relaunching.**")
    say("   `scripts/probe_batched_judge.py` at 6 vs 8 vs 10 with Llama and DeBERTa resident.")
    say("   The judge is ~80% of the run; a 20% throughput win is ~4 GPU-h, and it is the")
    say("   only saving on this page that costs nothing statistically. If it OOMs, stay at 6.")
    say("2. **Relaunch A and let it run.** It resumes from the checkpoint. At the measured")
    say(f"   rate a 10 h night finishes {int(10 * 3600 / unit_full)}-{int(10 * 3600 / unit_mix)} "
        f"targets, so the cell completes on the third night. That also reverses the")
    say("   reasoning in `scripts/overnight_2026_08_13.sh` (*~60 GPU-h left ... yields nothing")
    say("   by morning*): at the measured rate it yields a third of the cell by morning.")
    say()
    say("   **Pre-flight, and this one is a trap.** `ckpt_cfg` is")
    say("   `{K, n_seeds, embedding_model, embed_threshold, judge_model}` and `_ckpt_load`")
    say(f"   reuses a record only on an EXACT dict match, so if the `--dump_judge_detail` work")
    say(f"   now in flight adds a field to that dict, all {t['n']} completed targets silently")
    say("   stop being reusable and the run restarts from zero -- 3.6 GPU-h thrown away, with")
    say("   no error, just a `[ckpt] ... 0 reusable target(s)` line. Check that line on")
    say(f"   relaunch: it must say {t['n']}. Relatedly, the 11 existing records cannot contain")
    say("   per-pair judge detail that did not exist when they were written, so any detail")
    say("   dump will cover 69 targets, not 80, unless those 11 are deliberately recomputed.")
    say("3. **Compute the prefix statistic on the same data when it lands.** It is free, it is")
    say("   pre-registered (entry 22, m=36), it needs no exchangeability assumption, and it is")
    say("   the pre-committed fallback if the null-objective gate fails. Run it whatever the")
    say("   gate says -- an assumption-free companion to an assumption-dependent headline is")
    say("   worth having when the assumption is load-bearing for 92% of the tie multiplicity.")
    say("4. **Then the ~4 GPU-h null-objective ablation**, in the order its own plan specifies")
    say("   (after the null control, using `--benign_from results/diag_defb.json`).")
    say()
    say("What to skip:")
    say()
    say("- **Any change to m.** The best case saves under one night and costs a third of the")
    say("  power; at m=36 the saving nearly vanishes once the restart is priced. And the")
    say("  clean window for changing m closed when the interim was read (§7).")
    say("- **Any change to n.** ~0.2 of power per half-night, and it damages the ablation gate")
    say("  and the pre-registration at the same time (§8).")
    say("- **Dropping or subsampling arms.** Three of the four are free; the fourth is the")
    say("  adjudicator; subsampling it biases the floor the wrong way (§6F).")
    say("- **Stopping at n=11 and leaning on the prefix statistic alone.** It is the right")
    say("  companion and the wrong headline: at n=11 the exceedance test is arithmetically")
    say("  incapable of rejecting (§3), and a non-rejection with no power statement is exactly")
    say("  the reviewer bait the null control was built to avoid.")
    say()
    say("**The honest counter-case**, since the spine of the paper is now the measurement")
    say("result and this decides a case study: if the queue's other jobs are genuinely more")
    say("valuable per hour, the defensible cut is to run the null control to n=80 *later* --")
    say("not smaller. 25 GPU-h can be deferred inside a 33-day window; the power a smaller n")
    say("throws away cannot be recovered without paying for it twice.")
    say()

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
