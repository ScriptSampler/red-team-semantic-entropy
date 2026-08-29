"""Definitive null-control analysis for the `_defb` campaign (80/80 targets, 2026-08-29).

Reads ONLY (never writes) the completed run artefacts:

  results/null_control_ckpt_defb.jsonl            80 per-target records (the measurement)
  results/diag_defb.json                          the --dump_diag dump of the same records
  data/cache/attacks/wk9_defb_snap/               the campaign outcomes (best_query,
      triviaqa_se_false_alarm.jsonl               n_feasible_at_best, n_objective_calls)

and writes results/null_control_report_defb.md.

The snapshot copy of the campaign file is used rather than the live WSL directory so that
this script runs Windows-side with no WSL dependency; its sha256 is printed in the report
and was verified equal to the live
`/home/abhi/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl`
(md5 24ffbc159468924cc922449a688aa4bc, mtime 2026-08-12 07:02, untouched since the
2026-08-13 snapshot). That discharges owed item 1 of
results/PREREG_noop_convention_2026_08_28.md.

FULLY DETERMINISTIC: every seed is fixed and no timestamp, path-dependent value or
dict-iteration-order-dependent value reaches the output. Running it twice produces a
byte-identical report.

    .venv/Scripts/python.exe scripts/null_control_defb_report.py
"""
from __future__ import annotations

import hashlib
import json
from math import comb
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from se.stats import (bootstrap_ci, rate_ci, exceedance_counts,  # noqa: E402
                      exceedance_counts_randomized, exceedance_test,
                      exceedance_test_over_seeds, exceedance_test_over_tie_scales)

CKPT = ROOT / "results" / "null_control_ckpt_defb.jsonl"
DIAG = ROOT / "results" / "diag_defb.json"
OUTCOMES = ROOT / "data" / "cache" / "attacks" / "wk9_defb_snap" / "triviaqa_se_false_alarm.jsonl"
REPORT = ROOT / "results" / "null_control_report_defb.md"

ARMS = ["nli", "exact", "judge"]
ARM_LABEL = {
    "nli": "NLI (the detector's own clusterer — shared, permissive bound)",
    "exact": "exact-match (independent, strict — over-splits on surface form)",
    "judge": "LLM judge Qwen2.5-7B-Instruct (independent — the PRE-REGISTERED adjudicator)",
}

N_BOOT = 20000
BOOT_SEED = 20260828        # the seed the 2026-08-28 pre-registration used
N_TIE_SEEDS = 101           # tie-break realisations for the randomised exceedance test
TOL = 1e-12


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fmt(x: float, nd: int = 4) -> str:
    """Sign-forced fixed format that never prints '-0.0000'."""
    s = f"{x:+.{nd}f}"
    if set(s[1:]) <= {"0", "."}:
        s = "+" + s[1:]
    return s


def ci_str(ci) -> str:
    return f"{fmt(ci.point)} [{fmt(ci.lo)}, {fmt(ci.hi)}]"


def exp_max_of_subset(values, m: int) -> float:
    """Exact E[max of a uniformly random size-m subset (no replacement)] of `values`."""
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    if m >= n:
        return float(v[-1])
    total = comb(n, m)
    e, prev = 0.0, 0.0
    for u in np.unique(v):
        c = int((v <= u + TOL).sum())
        p_le = comb(c, m) / total if c >= m else 0.0
        e += float(u) * (p_le - prev)
        prev = p_le
    return e


# --------------------------------------------------------------------------- load
raw = CKPT.read_bytes()
lines = raw.decode("utf-8").split("\n")
torn = []
records = []
for i, ln in enumerate(lines):
    if not ln.strip():
        continue
    try:
        records.append(json.loads(ln))
    except Exception:
        torn.append(i + 1)

outcomes = {}
for ln in OUTCOMES.read_text(encoding="utf-8").splitlines():
    if ln.strip():
        o = json.loads(ln)
        outcomes[o["question_id"]] = o

ids = [r["question_id"] for r in records]
cfgs = sorted({json.dumps(r["cfg"], sort_keys=True) for r in records})

# diag vs checkpoint: identical content?
diag = json.loads(DIAG.read_text(encoding="utf-8"))
canon = lambda rs: [json.dumps(r, sort_keys=True) for r in rs]  # noqa: E731
diag_identical = canon(diag) == canon(records)
diag_ids_same_order = [r["question_id"] for r in diag] == ids
diag_keys = sorted({k for r in diag for k in r})
ckpt_keys = sorted({k for r in records for k in r})

# --------------------------------------------------------------------------- structure
noop_ids = [q for q in ids if outcomes[q]["best_query"] == outcomes[q]["question"]]
noop = set(noop_ids)
# cross-checks on the no-op definition
noop_alt_improved = {q for q in ids if not outcomes[q]["improved"]}
noop_alt_nfb = {q for q in ids if (outcomes[q].get("n_feasible_at_best") or 0) == 0}

empty_ids = [q for q, r in zip(ids, records) if not r["benign"]["nli"]]
partial = [(q, len(r["benign"]["nli"])) for q, r in zip(ids, records)
           if 0 < len(r["benign"]["nli"]) < 50]
full_n = sum(1 for r in records if len(r["benign"]["nli"]) == 50)
K_DECLARED = json.loads(cfgs[0])["K"]

# arm-length agreement (empty/partial sets identical across arms?)
arm_len_agree = all(
    [len(r["benign"][a]) for r in records] == [len(r["benign"]["nli"]) for r in records]
    for a in ARMS)
embed_all_empty = all(not r["benign"]["embed"] for r in records) and \
    all(r["attack_move"]["embed"] is None for r in records)

budgets = [outcomes[q]["n_objective_calls"] for q in ids]
N_ATTACK = int(np.median([b for b in budgets if b] or [180]))
tie_b = [max(1, int(outcomes[q].get("n_feasible_at_best") or 1)) for q in ids]

# --------------------------------------------------------------------------- statistics
def paired_rows(arm):
    """[(qid, attack_move, benign_max)] over targets with a non-empty benign arm."""
    return [(r["question_id"], float(r["attack_move"][arm]), max(r["benign"][arm]))
            for r in records if r["benign"][arm]]


def conventions(arm):
    rows = paired_rows(arm)
    out = {}
    out["a"] = ([a - b for _, a, b in rows], "as-is")
    out["b"] = ([0.0 if q in noop else a - b for q, a, b in rows],
                "no-op PAIRS neutralised to 0")
    out["b'"] = ([a - max(0.0, b) if q in noop else a - b for q, a, b in rows],
                 "benign may decline ON NO-OP TARGETS ONLY")
    out["c"] = ([a - b for q, a, b in rows if q not in noop], "no-op targets excluded")
    out["d"] = ([a - max(0.0, b) for _, a, b in rows],
                "benign may decline on EVERY target (LOCKED)")
    return rows, out


results = {}
for arm in ARMS:
    rows, convs = conventions(arm)
    am = [float(r["attack_move"][arm]) for r in records]
    bl = [r["benign"][arm] for r in records]

    conv_stats = {}
    for k, (diffs, label) in convs.items():
        ci = bootstrap_ci(diffs, np.mean, n_boot=N_BOOT, seed=BOOT_SEED)
        conv_stats[k] = {"label": label, "n": len(diffs), "ci": ci}

    sign_d = rate_ci([a > max(0.0, b) for _, a, b in rows],
                     n_boot=N_BOOT, seed=BOOT_SEED)
    # is the headline interval a property of the data or of one bootstrap seed?
    d_diffs = convs["d"][0]
    alt = [bootstrap_ci(d_diffs, np.mean, n_boot=N_BOOT, seed=s) for s in (0, 1, 42, 999999)]
    alt_lo = min([c.lo for c in alt] + [conv_stats["d"]["ci"].lo])
    alt_hi = max([c.hi for c in alt] + [conv_stats["d"]["ci"].hi])
    from scipy import stats as _ss
    _t = float(_ss.ttest_1samp(np.asarray(d_diffs), 0.0).pvalue)
    _w = float(_ss.wilcoxon(np.asarray(d_diffs)).pvalue)

    rnd0 = exceedance_test(
        exceedance_counts_randomized(am, bl, tie_b, n_attack_candidates=N_ATTACK, seed=0),
        N_ATTACK)
    over = exceedance_test_over_seeds(am, bl, tie_b, N_ATTACK, n_seeds=N_TIE_SEEDS)
    strict = exceedance_test(exceedance_counts(am, bl, ties="strict"), N_ATTACK)
    cons = exceedance_test(exceedance_counts(am, bl, ties="conservative"), N_ATTACK)
    scales = exceedance_test_over_tie_scales(am, bl, tie_b, N_ATTACK, n_seeds=25)

    # short-arm (m < K) bias, estimated from the 71 full arms by exact subset expectation
    fulls = [r["benign"][arm] for r in records if len(r["benign"][arm]) == 50]
    short_bias_asis = 0.0
    short_bias_d = 0.0
    short_detail = []
    for q, m in partial:
        rec = next(r for r in records if r["question_id"] == q)
        shortfall = float(np.mean([max(f) - exp_max_of_subset(f, m) for f in fulls]))
        bm = max(rec["benign"][arm])
        short_bias_asis += shortfall
        short_bias_d += max(0.0, bm + shortfall) - max(0.0, bm)
        short_detail.append((q, m, shortfall, bm))
    n_pair = len(rows)

    results[arm] = {
        "rows": rows, "conv": conv_stats, "sign_d": sign_d,
        "n_noop_pos_bmax": sum(1 for q, _, b in rows if q in noop and b > 0),
        "alt_lo": alt_lo, "alt_hi": alt_hi, "t_p": _t, "w_p": _w,
        "median_d": float(np.median(d_diffs)),
        "frac_neg_d": float(np.mean([x < 0 for x in d_diffs])),
        "rnd0": rnd0, "over": over, "strict": strict, "cons": cons, "scales": scales,
        "neg_bmax": sum(1 for _, _, b in rows if b < 0),
        "attack_min": min(am), "attack_neg": sum(1 for a in am if a < 0),
        "attack_zero": sum(1 for a in am if abs(a) < TOL),
        "noop_contrib": sum(a - b for q, a, b in rows if q in noop),
        "n_noop_paired": sum(1 for q, _, _ in rows if q in noop),
        "short_bias_asis": short_bias_asis / n_pair,
        "short_bias_d": short_bias_d / n_pair,
        "short_detail": short_detail,
        "median_distinct": float(np.median([len(set(np.round(b, 12))) for b in fulls])),
        "frac_at_max": float(np.mean([sum(1 for x in b if abs(x - max(b)) < TOL) / len(b)
                                      for b in fulls])),
        "seed_mean": float(np.mean([x for r in records for x in r["seed"][arm]])),
        "seed_n": sum(len(r["seed"][arm]) for r in records),
        # clustered by target: resample targets, not individual seed draws
        "seed_ci": bootstrap_ci([float(np.mean(r["seed"][arm])) for r in records],
                                np.mean, n_boot=N_BOOT, seed=BOOT_SEED),
    }

# ------------- the pre-registration's own table, recomputed on its 68-target view -------
PREREG_TABLE = {  # as printed in results/PREREG_noop_convention_2026_08_28.md section 0
    ("a", "nli"): 0.1926, ("a", "exact"): 0.0176, ("a", "judge"): -0.1515,
    ("b", "nli"): 0.1200, ("b", "exact"): -0.0072, ("b", "judge"): -0.1675,
    ("c", "nli"): 0.1432, ("c", "exact"): -0.0086, ("c", "judge"): -0.1998,
    ("d", "nli"): 0.1061, ("d", "exact"): -0.0169, ("d", "judge"): -0.2042,
}
first68 = records[:68]
noop68 = {q for q in ids[:68] if q in noop}
repro = {}
for arm in ARMS:
    rows68 = [(r["question_id"], float(r["attack_move"][arm]), max(r["benign"][arm]))
              for r in first68 if r["benign"][arm]]
    c68 = {
        "a": [a - b for _, a, b in rows68],
        "b": [0.0 if q in noop68 else a - b for q, a, b in rows68],
        "b'": [a - max(0.0, b) if q in noop68 else a - b for q, a, b in rows68],
        "c": [a - b for q, a, b in rows68 if q not in noop68],
        "d": [a - max(0.0, b) for _, a, b in rows68],
    }
    repro[arm] = {k: (float(np.mean(v)), len(v)) for k, v in c68.items()}
    repro[arm]["_noop_contrib"] = sum(a - b for q, a, b in rows68 if q in noop68)
    repro[arm]["_n_noop"] = sum(1 for q, _, _ in rows68 if q in noop68)
n_paired68 = repro["nli"]["a"][1]
matches = {k: [abs(repro[a][k][0] - PREREG_TABLE[(k, a)]) <= 5e-5 for a in ARMS]
           for k in ["a", "b", "c", "d"]}

# ------------------------------------------------------------------ report assembly
L: list[str] = []
A = L.append

A("# Null control, definitive: does the attack beat a budget-matched benign search?")
A("")
A("**Campaign `_defb`, SE detector, false-alarm cell, 80/80 targets complete (run finished")
A("2026-08-29 03:57). Analysis by `scripts/null_control_defb_report.py`; regenerable and")
A("byte-identical on re-run.**")
A("")
A("Convention for the paired net is the one locked in")
A("`results/PREREG_noop_convention_2026_08_28.md` **before** the final 12 targets landed:")
A("convention (d), the benign arm may decline. All four conventions are reported below")
A("because that pre-registration requires it.")
A("")

# ---- headline
A("## 0. The answer in one paragraph")
A("")
d_nli = results["nli"]["conv"]["d"]["ci"]
d_ex = results["exact"]["conv"]["d"]["ci"]
d_ju = results["judge"]["conv"]["d"]["ci"]
ov_nli = results["nli"]["over"]
A(f"**No.** On the pre-committed claim statistic — the randomised-tie exceedance test, whose")
A(f"null prices the attack's {N_ATTACK}-candidate search budget into the comparison — the attack")
A(f"produces *more* benign exceedances than the null expects in every arm, so the one-sided")
A(f"p-value P(S <= s_obs) is far from significance: median p = {ov_nli['p_median']:.4f} (NLI),")
A(f"{results['exact']['over']['p_median']:.4f} (exact), {results['judge']['over']['p_median']:.4f}")
A(f"(judge) over {N_TIE_SEEDS} tie-break realisations, against a 0.05 threshold; in no arm and")
A(f"under no realisation does the test reject. On the supplementary paired net under the locked")
A(f"convention (d), the attack's advantage over a budget-matched benign search is")
A(f"{ci_str(d_nli)} nats in the detector's own NLI arm — positive but measured with the")
A(f"clusterer the attack was optimised against — {ci_str(d_ex)} nats under exact match, and")
A(f"**{ci_str(d_ju)} nats under the pre-registered independent LLM-judge adjudicator, an")
A(f"interval lying entirely below zero.** The sign is negative: under the adjudicator the")
A(f"optimised attack moves semantic entropy *less* than the best of {K_DECLARED} random feasible")
A(f"paraphrases drawn at matched budget, by about {abs(d_ju.point):.2f} nats per target. The")
A(f"campaign has 80 targets, but the paired net and the exceedance test both run on")
A(f"n = {results['judge']['conv']['d']['n']} and convention (c) on")
A(f"n = {results['judge']['conv']['c']['n']}; those denominators are itemised in section 4 and")
A(f"a reader must not read any of them as 80. The paper's claim of no attack effect is")
A(f"supported, and strengthened: the effect is not merely absent under the independent")
A(f"adjudicator, it is reversed.")
A("")

# ---- provenance
A("## 1. Provenance and integrity of the inputs")
A("")
A("| file | bytes | sha256 (first 16) | content |")
A("|---|---|---|---|")
for p, desc in [(CKPT, f"{len(records)} JSONL records, {len(set(ids))} unique question_ids"),
                (DIAG, f"{len(diag)} records (`--dump_diag`)"),
                (OUTCOMES, f"{len(outcomes)} campaign outcomes")]:
    A(f"| `{p.relative_to(ROOT).as_posix()}` | {p.stat().st_size:,} | "
      f"`{sha256(p)[:16]}` | {desc} |")
A("")
A(f"- Checkpoint: **{len(records)} records parsed, {len(set(ids))} unique question_ids, "
  f"{len(torn)} torn lines**, file ends with a newline. Every record carries the same cfg.")
A(f"- Single cfg across all 80 records: `{cfgs[0]}` "
  f"({'1 distinct cfg' if len(cfgs) == 1 else str(len(cfgs)) + ' DISTINCT CFGS — INVESTIGATE'}).")
A(f"- All records are `detector=se`, `attack=false_alarm`: "
  f"{sorted({r['detector'] for r in records})} / {sorted({r['attack'] for r in records})}.")
A("- Campaign outcomes are read from the in-repo snapshot `wk9_defb_snap` (2026-08-13). Its")
A("  md5 was verified equal to the live WSL campaign file")
A("  `/home/abhi/.cache/se-research/samples/attacks/wk9_defb/triviaqa_se_false_alarm.jsonl`")
A("  (`24ffbc159468924cc922449a688aa4bc`, mtime 2026-08-12 07:02), so `recompute_fair.py` has")
A("  **not** touched the false-alarm cell since the snapshot. This discharges owed item 1 of")
A("  the pre-registration. (The neighbouring `triviaqa_se_hide.jsonl` *has* changed; it is not")
A("  used here.)")
A("")

# ---- exceedance
A("## 2. The exceedance test — the pre-committed claim statistic")
A("")
A("`docs/critique_log.md:1023` pre-commits the decision rule to the **randomised-tie**")
A("exceedance test (`se.stats.exceedance_test` fed by `exceedance_counts_randomized`).")
A("Under H0 the attack's N candidates and a target's m benign draws are exchangeable draws")
A("from one distribution, so the number of benign draws reaching the attack's max is")
A("`K_j ~ BetaBinomial(m_j; a=1, b=N)` with `E[K_j] = m_j/(N+1)`; the null of `S = sum_j K_j`")
A("is obtained by exact convolution and the one-sided p-value is `P(S <= s_obs)`. **Fewer")
A("exceedances than expected is evidence for the attack**, so a small p rejects H0 in the")
A("attack's favour.")
A("")
A(f"- `N = {N_ATTACK}` attack candidates per target: `n_objective_calls` is **exactly "
  f"{min(budgets)} on all 80 targets** (min = max = median), so the heterogeneous-N caveat in")
A("  `exceedance_counts_randomized`'s docstring does not bite here.")
A(f"- Tie multiplicity `b_j = n_feasible_at_best` (clamped to >= 1): min {min(tie_b)}, "
  f"max {max(tie_b)}. At the measured b, max b <= N, so **no target was clamped** in the")
A("  headline row and the p-values are not degraded toward the disqualified strict rule.")
A("  (The `b x 2` sensitivity row below does clamp; its count is shown there.)")
A("")
A(f"| arm | n_targets | observed S | expected E[S] | p (seed 0) | p median over {N_TIE_SEEDS} seeds | p range | frac p<=0.05 | n_eff |")
A("|---|---|---|---|---|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| {arm} | {r['rnd0']['n_targets']} | {r['rnd0']['observed']} | "
      f"{r['rnd0']['expected']:.2f} | {r['rnd0']['p_value']:.4f} | "
      f"**{r['over']['p_median']:.4f}** | [{r['over']['p_lo']:.4f}, {r['over']['p_hi']:.4f}] | "
      f"{r['over']['frac_below_05']:.3f} | {r['rnd0']['n_eff']:.1f} |")
A("")
A("**What this licenses.** Nothing in the attack's favour, in any arm. The observed")
A("exceedance total is *above* its null expectation everywhere (NLI "
  f"{results['nli']['rnd0']['observed']} vs {results['nli']['rnd0']['expected']:.1f}; exact "
  f"{results['exact']['rnd0']['observed']} vs {results['exact']['rnd0']['expected']:.1f}; judge "
  f"{results['judge']['rnd0']['observed']} vs {results['judge']['rnd0']['expected']:.1f}), which")
A("is the direction *against* the attack, and no tie-break realisation out of "
  f"{N_TIE_SEEDS} produced p <= 0.05 in any arm. The paper may state that the pre-committed")
A("test does not reject the null that the optimiser's guidance carries no signal. It may not")
A("state a positive attack effect on this statistic, and it does not need to.")
A("")
A("`n_eff` reads as *\"the beam search is worth this many random paraphrases\"*: in the NLI arm")
A(f"the {N_ATTACK}-candidate optimiser is worth about {results['nli']['rnd0']['n_eff']:.0f} random")
A(f"draws, i.e. **less than its own budget**; under the judge it is worth about")
A(f"{results['judge']['rnd0']['n_eff']:.0f}. The estimator is method-of-moments and upward-biased")
A("when the mean count is small, so treat it as indicative only.")
A("")
A("**Disagreement between tie rules, disclosed as `critique_log` 26 requires.** The two")
A("disqualified fixed tie rules are reported as diagnostics only:")
A("")
A("| arm | strict (b > a): p, obs | conservative (b >= a): p, obs | randomised (pre-committed) |")
A("|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| {arm} | {r['strict']['p_value']:.4f}, {r['strict']['observed']} | "
      f"{r['cons']['p_value']:.4f}, {r['cons']['observed']} | "
      f"{r['over']['p_median']:.4f}, {r['rnd0']['observed']} |")
A("")
A(f"The strict rule 'rejects' in the NLI arm (p = {results['nli']['strict']['p_value']:.4f}) and")
A("that is an artifact, not a finding: it is disqualified at H0 level 0.995 precisely because")
A("the score has an atom at the log(N) ceiling, and the benign arms here are extremely lumpy")
A(f"(median {results['nli']['median_distinct']:.0f} distinct values among 50 NLI draws, with")
A(f"{results['nli']['frac_at_max']:.1%} of draws sitting exactly at that target's maximum).")
A("Counting only strict exceedances discards those ties and manufactures evidence. The")
A("conservative rule is disqualified in the opposite direction (power 0.05). Neither may be")
A("quoted as a result; the disagreement is exactly the ceiling-saturation signature the")
A("project already documented, not the attack outperforming chance.")
A("")
A("**Robustness to an error in the measured tie multiplicity b** "
  "(`exceedance_test_over_tie_scales`; scaling b up shrinks p, so this is the one-sided check")
A("that matters):")
A("")
A("| arm | " + " | ".join(f"b x {row['scale']:g}" for row in results['nli']['scales']['scales']) + " |")
A("|---|" + "---|" * len(results['nli']['scales']['scales']))
for arm in ARMS:
    A(f"| {arm} | " + " | ".join(f"{row['p_median']:.4f}"
                                 for row in results[arm]['scales']['scales']) + " |")
A("| targets clamped to b=N | " + " | ".join(str(row['n_tie_clamped'])
                                            for row in results['nli']['scales']['scales']) + " |")
A("")
A("No scale in the plausible range brings any arm near 0.05, so the non-rejection is a")
A("property of the data and not of the optimiser's bookkeeping. The `b x 2` column clamps "
  f"{results['nli']['scales']['scales'][-1]['n_tie_clamped']} targets to b = N, which raises")
A("its p-value relative to an unclamped doubling; even so it stops at "
  f"{results['nli']['scales']['scales'][-1]['p_median']:.4f} in the NLI arm, and the doubling")
A("itself is already an implausible bookkeeping error given that b is read straight off the")
A("instrumented optimiser.")
A("")
A("**One assumption is violated and the violation is in the attack's favour.** The")
A("exchangeability premise requires the attack's reported value to be a draw from the same")
A("feasible-paraphrase distribution as the benign draws. On the no-op targets it is not: the")
A("optimiser returned the original question, so `attack_move` is a structural 0, while")
A("`feasibility.check(..., require_different=True)` rejects the no-op as its *first* test, so")
A("the benign arm can never produce it. Those targets donate free zero-exceedances in the NLI")
A("arm, pushing S down, i.e. **anti-conservatively, toward rejecting H0 in the attack's")
A("favour**. Since the test does not reject even with that help, the violation changes no")
A("conclusion here. It is unresolved and would matter at a borderline result.")
A("")

# ---- paired net
A("## 3. The paired net, supplementary — all four conventions plus the audit's variant")
A("")
A("The paired net is `attack_move_j - benign_max_j` averaged over targets, with a paired")
A(f"bootstrap 95% interval ({N_BOOT:,} resamples of targets, seed {BOOT_SEED}). It is")
A("**supplementary**; the claim statistic is section 2.")
A("")
A("Conventions, stated precisely because two of them are easy to conflate:")
A("")
A("- **(a) as-is** — `attack_move - benign_max`, no adjustment.")
A("- **(b) no-op pairs neutralised** — the paired difference is set to 0 on every no-op")
A("  target; n preserved.")
A("- **(b')** the variant in `results/benign_arm_audit.md` §6 — `benign_max -> max(0, benign_max)`")
A("  **on no-op targets only**; n preserved. (b) and (b') coincide on a target only when its")
A("  benign max is <= 0; the number of no-op targets in the paired net whose benign max is")
A("  **positive**, and which therefore separate the two, is " +
  ", ".join(f"{results[a]['n_noop_pos_bmax']} ({a})" for a in ARMS) + ".")
A("- **(c) no-op targets excluded** — dropped from the average; n falls.")
A("- **(d) benign may decline (LOCKED)** — `attack_move - max(0, benign_max)` on **every**")
A("  target; n preserved.")
A("")
A("### Headline — convention (d)")
A("")
A("| arm | paired net (nats) | n | sign rate: `attack_move > max(0, benign_max)` |")
A("|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| **{arm}** — {ARM_LABEL[arm]} | **{ci_str(r['conv']['d']['ci'])}** | "
      f"{r['conv']['d']['n']} | {ci_str(r['sign_d'])} |")
A("")
A("The headline interval is a property of the data, not of one bootstrap seed. Re-running the")
A("bootstrap at seeds 0, 1, 42 and 999999 as well as the pre-registered 20260828, and adding")
A("two distribution-based tests that use no resampling at all:")
A("")
A("| arm | envelope of the 5 bootstrap intervals | median paired diff | share of targets with a negative diff | one-sample t | Wilcoxon signed-rank |")
A("|---|---|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| {arm} | [{fmt(r['alt_lo'])}, {fmt(r['alt_hi'])}] | {fmt(r['median_d'])} | "
      f"{r['frac_neg_d']:.1%} | p = {r['t_p']:.4g} | p = {r['w_p']:.4g} |")
A("")
A("The judge interval excludes zero under every seed and both non-bootstrap tests agree")
A(f"(t p = {results['judge']['t_p']:.4g}, Wilcoxon p = {results['judge']['w_p']:.4g}). The exact")
A("arm is the one place the two families disagree — its bootstrap and t intervals cover zero")
A(f"while the signed-rank test does not (p = {results['exact']['w_p']:.4g}) — because that arm's")
A("differences are a spike at 0 with a long negative tail, so a rank test sees the asymmetry")
A("that a mean does not. The exact arm is reported as covering zero, which is the conservative")
A("reading and the one consistent with the pre-registered statistic.")
A("")
A("### Sensitivity — the table the pre-registration requires")
A("")
A("| convention | n (nli/exact/judge) | NLI | exact | judge (adjudicator) |")
A("|---|---|---|---|---|")
for k in ["a", "b", "b'", "c", "d"]:
    ns = "/".join(str(results[a]["conv"][k]["n"]) for a in ARMS)
    label = results["nli"]["conv"][k]["label"]
    star = "**" if k == "d" else ""
    A(f"| {star}({k}) {label}{star} | {ns} | {ci_str(results['nli']['conv'][k]['ci'])} | "
      f"{ci_str(results['exact']['conv'][k]['ci'])} | "
      f"{star}{ci_str(results['judge']['conv'][k]['ci'])}{star} |")
A("")
A("The convention decides whether the adjudicator's interval covers zero: under (a) it")
A("includes zero, under (b), (b'), (c) and (d) it lies entirely below it. It never supports a")
A("positive attack effect under the adjudicator. The locked convention (d) is the one **least**")
A("favourable to the attack in all three arms, which is the direction that makes a post-hoc")
A("choice non-self-serving.")
A("")
A("### Why the correction exists")
A("")
A("| arm | attack_move min | n targets with attack_move < 0 | n with benign_max < 0 | no-op targets in the paired net | their as-is contribution (nats, total) |")
A("|---|---|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| {arm} | {fmt(r['attack_min'])} | {r['attack_neg']} | {r['neg_bmax']} | "
      f"{r['n_noop_paired']} | {fmt(r['noop_contrib'], 3)} |")
A("")
A("**A qualification the pre-registration does not make, and that a referee will find.** The")
A("statement \"`attack_move` is bounded below by zero because the optimiser can decline\" is")
A(f"true **only in the NLI arm** (minimum exactly {fmt(results['nli']['attack_min'])} over all 80")
A(f"targets). The optimiser searches in NLI space; the exact and judge arms are independent")
A("re-scorings of the query it chose, and there `attack_move` is negative on")
A(f"{results['exact']['attack_neg']} and {results['judge']['attack_neg']} targets respectively")
A(f"(minima {fmt(results['exact']['attack_min'])} and {fmt(results['judge']['attack_min'])}). The")
A("action-set argument for convention (d) still holds in every arm — the attack's action set")
A("contains the no-op, which scores exactly 0 in *all* arms because `best_query == question`")
A("makes `before == after`, and the benign arm's action set does not — but (d) gives the benign")
A("arm a *per-arm* decline decision while the attack's decline decision is taken on NLI alone.")
A("In the exact and judge arms (d) is therefore mildly generous to the null, which is the")
A("conservative direction for an attack claim and the anti-conservative direction for the")
A("negative judge result reported here. Convention (c), which touches neither arm's action")
A(f"set, gives the judge net {ci_str(results['judge']['conv']['c']['ci'])}; the negative sign")
A("does not depend on (d).")
A("")

# ---- denominators
A("## 4. The denominators, which are four different numbers")
A("")
A("| quantity | n | what it is |")
A("|---|---|---|")
A(f"| targets attacked in the cell | 80 | the campaign; `n >= 80` pre-registration met **here only** |")
A(f"| exceedance test | {results['nli']['rnd0']['n_targets']} | targets with `m_j > 0`; the 3 empty benign arms contribute nothing and are silently dropped by `exceedance_counts_randomized` |")
A(f"| paired net, (a)/(b)/(b')/(d) | {results['nli']['conv']['a']['n']} | targets with a non-empty benign arm |")
A(f"| paired net, (c) | {results['nli']['conv']['c']['n']} | the above minus the {results['nli']['n_noop_paired']} no-op targets that have a benign arm |")
A(f"| benign arm at the full declared budget K={K_DECLARED} | {full_n} | the rest are short |")
A("")
A(f"**Empty benign arm — {len(empty_ids)} targets: "
  f"{', '.join('`' + q + '`' for q in empty_ids)}.** The feasibility gate rejected all")
A(f"`K*5 = {K_DECLARED * 5}` attempts (`scripts/null_control.py:174`), so these targets have no")
A("benign maximum and no paired net. All three are also no-op targets — the optimiser found")
A("no feasible paraphrase either (`n_feasible_at_best == 0`; verified: "
  f"{set(empty_ids) <= noop and set(empty_ids) <= noop_alt_nfb}) — which is joint evidence")
A("that no feasible paraphrase of those questions exists, not that the sampler was unlucky.")
A("They are excluded, not absorbed.")
A("")
A(f"**Partial benign arm — {len(partial)} targets** with 1 <= m < {K_DECLARED}: " +
  ", ".join(f"`{q}` (m={m})" for q, m in partial) + ".")
A("Because the attempt cap is `K*5`, a shortfall means a gate pass rate below 20% and is")
A("informative about the question rather than random. Estimated inflation of the paired net,")
A("obtained by taking each of the 71 full arms and computing the exact expected maximum of a")
A("uniformly random size-m subset:")
A("")
A("| arm | bias, as-is (a) | bias, locked (d) | median distinct values in a 50-draw arm | share of draws at the arm's max |")
A("|---|---|---|---|---|")
for arm in ARMS:
    r = results[arm]
    A(f"| {arm} | {fmt(r['short_bias_asis'])} | {fmt(r['short_bias_d'])} | "
      f"{r['median_distinct']:.0f} | {r['frac_at_max']:.1%} |")
A("")
A("The bias is small because the benign score distributions are lumpy: with a median of only")
A(f"{results['nli']['median_distinct']:.0f} distinct values among 50 NLI draws and "
  f"{results['nli']['frac_at_max']:.0%} of draws already at the maximum, a maximum over 26 draws")
A("almost always equals the maximum over 50. Under the locked convention (d) the bias is")
A("smaller still, because the one severely short arm (`qb_6105`, m=1) has a negative benign")
A("maximum that the `max(0, .)` truncation removes. This is a **disclosure, not a correction**:")
_hw_a = (results['nli']['conv']['a']['ci'].hi - results['nli']['conv']['a']['ci'].lo) / 2
_hw_d = (results['nli']['conv']['d']['ci'].hi - results['nli']['conv']['d']['ci'].lo) / 2
A(f"the as-is bias is {results['nli']['short_bias_asis'] / _hw_a:.0%} of convention (a)'s NLI")
A(f"CI half-width, and the locked-convention bias is {results['nli']['short_bias_d'] / _hw_d:.0%}")
A("of (d)'s. For the exceedance test a short arm costs power, not calibration, because the")
A("null carries each target's own `m_j`.")
A("")
A("**The pre-registered `n >= 80` is met by the campaign and by nothing else here.** Every")
A("benign-referenced statistic runs on 77 or fewer targets. This belongs in Methods, not only")
A("in Limitations.")
A("")
A(f"**The `embed` arm does not exist in this campaign.** The run was launched with")
A(f"`embedding_model=\"\"`, so `attack_move.embed` is null and `benign.embed` is length 0 on all")
A(f"80 records (verified: {embed_all_empty}). It must never be reported as a null result — there")
A("is no measurement, not a measurement of no effect.")
A("")
A("The no-op set is identified three independent ways that agree exactly on the same "
  f"{len(noop_ids)} targets: `best_query == question`, `improved == False`, and")
A(f"`n_feasible_at_best == 0` "
  f"({'all three agree' if noop == noop_alt_improved == noop_alt_nfb else 'THEY DISAGREE — INVESTIGATE'}).")
A("")

# ---- diag
A("## 5. What `results/diag_defb.json` contains")
A("")
A("**Nothing the checkpoint does not.** It is the `--dump_diag` dump of the identical")
A("in-memory records: `scripts/null_control.py:429-430` appends the same `rec` object to a")
A("list that `:544` serialises with `json.dumps(..., indent=2)`. Verified by canonicalising")
A("both to sorted-key JSON:")
A("")
A(f"- record count: {len(diag)} vs {len(records)}; same question_ids in the same order: {diag_ids_same_order}")
A(f"- every record byte-identical after canonicalisation: **{diag_identical}**")
A(f"- key sets identical: {diag_keys == ckpt_keys} — `{', '.join(ckpt_keys)}`")
A("")
A(f"The 350 KB versus the checkpoint's 237 KB is entirely `indent=2` whitespace. So it holds")
A("no extra measurement, and the analysis above would be unchanged if it were deleted. What")
A("*both* files carry, per target, is: the `baseline` entropy in each arm; the `attack_move`;")
A(f"the full `benign` list of up to {K_DECLARED} move values per arm; and a `seed` band of 3")
A("re-scorings of the *same* question under seeds 1-3, which is the pure N=10 estimator-noise")
A(f"floor and is not otherwise reported. Its mean move, bootstrapped over targets rather than")
A(f"over the {results['nli']['seed_n']} individual draws because the three draws within a target")
A("are not independent, is")
A(", ".join(f"{ci_str(results[a]['seed_ci'])} ({a})" for a in ARMS) + ".")
A("Every one of those intervals covers zero, so pure N=10 estimator noise has no direction")
A("and the benign band and the attack are both read against a floor of 0. That is the")
A("reassurance the seed band exists to provide, and it holds.")
A("")

# ---- prereg corrections
A("## 6. What does not reproduce in the pre-registration")
A("")
A("The pre-registration's disclosure table (its section 0) was computed on the 68 targets then")
A("visible. Recomputing the same four conventions on the first 68 checkpoint rows — the same")
A("rows, in the same order, since the checkpoint is appended in completion order — gives:")
A("")
A("| convention | n | NLI: recomputed / pre-reg | exact: recomputed / pre-reg | judge: recomputed / pre-reg | largest discrepancy |")
A("|---|---|---|---|---|---|")
for k in ["a", "b", "b'", "c", "d"]:
    if k == "b'":
        cells = " | ".join(f"{fmt(repro[a][k][0])} / n/a" for a in ARMS)
        A(f"| (b') audit variant | {repro['nli'][k][1]} | {cells} | not in the pre-reg |")
        continue
    cells = " | ".join(f"{fmt(repro[a][k][0])} / {fmt(PREREG_TABLE[(k, a)])}" for a in ARMS)
    worst = max(abs(repro[a][k][0] - PREREG_TABLE[(k, a)]) for a in ARMS)
    ok = "reproduces" if all(matches[k]) else f"**{worst:.4f}**"
    A(f"| ({k}) | {repro['nli'][k][1]} | {cells} | {ok} |")
A("")
A("**Rows (a) and (d) reproduce to four decimals. Rows (b) and (c) do not.** The NLI and judge")
A("discrepancies (up to 0.0098 nats) are far too large to be rounding; one exact-arm cell")
A("differs only in the last printed digit and could be. The recomputed (b') and (c) figures")
A("match `results/benign_arm_audit.md` §6 exactly (+0.1256 / -0.0076 / -0.1868 and +0.1407 /")
A("-0.0085 / -0.1987), so the audit is right and the pre-registration mis-transcribed it. Two")
A("further slips travel with the same transcription:")
A("")
A(f"- \"Across the **11** no-op targets the contribution is +4.355 nats\" — +4.355 is the NLI-arm")
A(f"  total over the **{repro['nli']['_n_noop']}** no-op targets that had a benign arm at 68/80")
A(f"  (recomputed: {fmt(repro['nli']['_noop_contrib'])}). There were 10 no-op targets at 68/80,")
A(f"  not 11; there are {len(noop_ids)} at 80/80, of which {results['nli']['n_noop_paired']}")
A(f"  have a benign arm, contributing {fmt(results['nli']['noop_contrib'], 3)} nats.")
A(f"- \"(c) ... drops n from 65 to **57**\" — it dropped {n_paired68} to")
A(f"  **{repro['nli']['c'][1]}** at 68/80 ({repro['nli']['_n_noop']} exclusions, not 8), and")
A(f"  drops {results['nli']['conv']['a']['n']} to {results['nli']['conv']['c']['n']} here.")
A("")
A("None of this disturbs the locked decision: (a) and (d) are the rows the choice was argued")
A("from, they are correct, and the qualitative claim that the convention decides whether the")
A("judge interval covers zero survives recomputation. The corrected sensitivity table is")
A("section 3 above. The pre-registration's non-negotiable disclosure stands and is repeated")
A("here: **it was written with 68 of 80 targets visible and after their effect on every")
A("candidate convention had been computed. It was not blind.**")
A("")

# ---- verdict
A("## 7. Verdict")
A("")
A("**Does the attack beat a budget-matched benign search? No — and under the independent")
A("adjudicator it loses to one.** On the pre-committed statistic the exceedance test does not")
A("reject the null of no optimiser signal in any arm, at any of "
  f"{N_TIE_SEEDS} tie-break realisations, with the observed exceedance count *above* its null")
A("expectation everywhere; the attack's 181-candidate beam is worth about")
A(f"{results['nli']['rnd0']['n_eff']:.0f} random feasible paraphrases in the detector's own NLI")
A(f"arm and about {results['judge']['rnd0']['n_eff']:.0f} under the judge, in both cases less than")
A("the budget it spent. On the supplementary paired net under the pre-registered convention")
A(f"(d), the net is {ci_str(d_nli)} nats under the NLI clusterer the attack was optimised")
A(f"against, {ci_str(d_ex)} under exact match, and **{ci_str(d_ju)} under the pre-registered")
A("independent LLM judge — negative, with the whole 95% interval below zero**. Read with the")
A(f"sign in front of it: the optimised attack raises semantic entropy by about")
A(f"{abs(d_ju.point):.2f} nats *less* per target than simply taking the best of {K_DECLARED}")
A("random feasible paraphrases, once the benign arm is priced at the same budget and granted")
A("the same freedom to decline. The positive NLI")
A("figure is the confounded arm — the attack maximised that clusterer's own score, so it is an")
A("upper bound on the effect and not an independent measurement of it — and even there the")
A("effect does not survive the claim statistic. The paper's position that there is no attack")
A("effect is supported. A referee should read the negative judge net not as a defect in the")
A("measurement but as its result: with the search budget priced into the null, the")
A("adversarial optimiser under-performs random paraphrasing on the adjudicator that was")
A("chosen in advance to judge it.")
A("")
A("## 8. What was re-derived here, and what was taken on trust")
A("")
A("Re-derived from the artefacts by this script, not inherited from any prior document:")
A("checkpoint integrity and cardinality; the identity of `diag_defb.json` and the checkpoint;")
A("the empty and partial benign arms and their sizes; the no-op set under three definitions;")
A("`attack_move`'s per-arm minimum; the count of negative benign maxima; every exceedance")
A("p-value, its counts and its tie audit; every paired net and bootstrap interval under every")
A("convention at both 68 and 80 targets; the short-arm bias and the lumpiness statistics; and")
A("the four rows of the pre-registration's own table.")
A("")
A("Taken on trust, and each a place a referee could still dig:")
A("")
A("1. **That the recorded numbers are the numbers the GPU produced.** Nothing here re-runs the")
A("   detector; the entropies in the checkpoint are accepted as written. No GPU work was done.")
A("2. **The live-vs-snapshot check is an md5 comparison of the false-alarm outcomes file**, run")
A("   once, plus its unchanged mtime. The `hide` cell was not checked and is not used.")
A("3. **`n_feasible_at_best` is the optimiser's own bookkeeping.** The exceedance test's tie")
A("   credit depends on it and it is not independently verifiable from these artefacts; the")
A("   `b`-scaling row is the substitute, and it holds.")
A("4. **The judge clusterer's validity** (reported elsewhere at 0.93 symmetric agreement, with")
A("   positive-recognition ~0.7, so it slightly over-splits) is assumed, not re-measured. An")
A("   over-splitting judge adds noise to both arms, but the negative net is a difference")
A("   between arms measured on the same generations, so it is not obviously an artefact of it.")
A("5. **The exchangeability premise of the exceedance test** is assumed for the non-no-op")
A("   targets. `scripts/null_objective_ablation.py` is the measurement that bears on it and")
A("   was not re-run here.")
A("")
A("---")
A("")
A("Regenerate: `.venv/Scripts/python.exe scripts/null_control_defb_report.py` — deterministic,")
A("byte-identical on re-run.")

with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(L) + "\n")
print(f"wrote {REPORT} ({REPORT.stat().st_size} bytes)")
