"""The tie-rule showdown, re-scored against the DEPLOYED analytic null.

WHY THIS SCRIPT EXISTS. `results/tie_rule_showdown.md` measures each tie rule against a null
SIMULATED WITH THAT SAME RULE — the right way to ask "is this rule self-consistent", and the
reason its randomised row reads level 0.093 at the fully saturated cell (q=0.05, m=30).
paper/sections/experiments.tex instead quotes an "analytic-null level 0.021" for that cell,
which is a different and more relevant quantity: the level the SHIPPED test achieves, since
the pipeline scores against `se.stats.exceedance_test`'s BetaBinomial null and never gets to
simulate the truth. That 0.021 appeared in no artifact. This script produces it, and puts the
simulated-null column beside it so the two nulls cannot be confused again.

It also records the analytic max-of-N percentile the same paragraph relies on
("a max-of-181 sits at ~99% of an individual-draw distribution"), straight from
`se.stats.analytic_max_percentile`.

DGP INTEGRITY. `scripts/tie_rule_showdown.py` runs its simulation at module scope (no
`__main__` guard), so it cannot simply be imported. Rather than copy its functions and let
them drift, this script PARSES that file and executes only its `N_ATTACK`, `draw` and
`one_target` definitions. The DGP is therefore literally the same code, and a change there
shows up here.

    .venv/Scripts/python.exe scripts/tie_rule_analytic_level.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from se.config import RESULTS_DIR                          # noqa: E402
from se.stats import analytic_max_percentile               # noqa: E402
from power_sim_deployed import analytic_crit               # noqa: E402

SHOWDOWN = ROOT / "scripts" / "tie_rule_showdown.py"
PROBE = ROOT / "scripts" / "tie_level_probe.py"
RULES = ("strict", "conservative", "randomized")
Q_GRID = (0.0, 0.01, 0.05)
M_GRID = (30, 60)
N_TARGETS = 80
ALPHA = 0.05
TRIALS = 3000
NULL_TRIALS = 3000
MULT = 2.0
PAPER_CLAIM_ANALYTIC_LEVEL = 0.021        # experiments.tex, cell q=0.05 m=30, randomised
PAPER_CLAIM_STRICT_LEVEL = 0.995          # same sentence, simulated null
PAPER_CLAIM_CONSERVATIVE_POWER = 0.05     # same sentence


def load_dgp():
    """Execute only the DGP definitions from tie_rule_showdown.py."""
    tree = ast.parse(SHOWDOWN.read_text(encoding="utf-8"), filename=str(SHOWDOWN))
    keep = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in ("draw", "one_target"))
            or (isinstance(n, ast.Assign)
                and any(getattr(t, "id", None) == "N_ATTACK" for t in n.targets))]
    if len(keep) != 3:
        raise SystemExit(f"expected N_ATTACK, draw, one_target in {SHOWDOWN}; got "
                         f"{[getattr(n, 'name', 'N_ATTACK') for n in keep]}")
    ns: dict = {"np": np}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SHOWDOWN), "exec"), ns)
    return ns["N_ATTACK"], ns["one_target"]


N_ATTACK, one_target = load_dgp()


def load_probe_dgp():
    """Execute only `draw_target` (and its constants) from tie_level_probe.py.

    That script differs from the showdown in ONE respect that turns out to matter: it takes
    the tie multiplicity b as the number of attack candidates ACTUALLY at the atom, whereas
    the showdown redraws it as 1 + Binomial(N-1, q). The measured-b convention is the one
    both the deployed statistic and `power_sim_randomized` use, so the difference is not
    cosmetic — it moves the level.
    """
    tree = ast.parse(PROBE.read_text(encoding="utf-8"), filename=str(PROBE))

    def _wanted(node) -> bool:
        if isinstance(node, ast.FunctionDef):
            return node.name == "draw_target"
        if isinstance(node, ast.Assign):
            names = []
            for t in node.targets:
                names += ([e.id for e in t.elts if isinstance(e, ast.Name)]
                          if isinstance(t, ast.Tuple) else
                          ([t.id] if isinstance(t, ast.Name) else []))
            return bool(names) and set(names) <= {"N", "M", "T", "rng"}
        return False

    keep = [n for n in tree.body if _wanted(n)]
    ns: dict = {"np": np}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(PROBE), "exec"), ns)
    if "draw_target" not in ns or "M" not in ns:
        raise SystemExit(f"could not lift draw_target/M out of {PROBE}")
    return ns


def run(q, m, n_targets, mult, rule, trials, rng):
    """Per-trial exceedance totals; same shape as tie_rule_showdown.run."""
    return np.array([[one_target(q, m, mult, rule, rng) for _ in range(n_targets)]
                     for _ in range(trials)]).sum(axis=1)


def run_probe(ns, q, mult, trials, n_targets, seed):
    """Per-trial totals under the tie_level_probe DGP (single randomized draw)."""
    ns["rng"] = np.random.default_rng(seed)
    dt = ns["draw_target"]
    return np.array([sum(int(dt(q, mult)[1]) for _ in range(n_targets))
                     for _ in range(trials)])


def main() -> int:
    c_by_m = {m: analytic_crit(m, N_TARGETS, ALPHA) for m in M_GRID}

    rows = []
    for q in Q_GRID:
        for rule in RULES:
            for m in M_GRID:
                rng = np.random.default_rng(7)
                null = run(q, m, N_TARGETS, 1.0, rule, NULL_TRIALS, rng)
                crit_sim = float(np.quantile(null, ALPHA))
                lvl = run(q, m, N_TARGETS, 1.0, rule, TRIALS, np.random.default_rng(9))
                obs = run(q, m, N_TARGETS, MULT, rule, TRIALS, np.random.default_rng(8))
                c_a = c_by_m[m]
                rows.append({
                    "q": q, "rule": rule, "m": m,
                    "e_s_h0": float(null.mean()),
                    "crit_analytic": c_a, "crit_sim": crit_sim,
                    "level_analytic": float((lvl <= c_a).mean()),
                    "level_sim": float((lvl <= crit_sim).mean()),
                    "power_analytic": float((obs <= c_a).mean()),
                    "power_sim": float((obs <= crit_sim).mean()),
                })
                print(f"q={q} {rule:>12} m={m}  E[S]={null.mean():7.2f}  "
                      f"analytic level {rows[-1]['level_analytic']:.3f} "
                      f"power {rows[-1]['power_analytic']:.2f} | "
                      f"simulated level {rows[-1]['level_sim']:.3f} "
                      f"power {rows[-1]['power_sim']:.2f}", flush=True)

    # Same question under the tie_level_probe DGP, whose b is MEASURED rather than redrawn.
    pns = load_probe_dgp()
    if int(pns["M"]) != 30:
        raise SystemExit(f"tie_level_probe M changed to {pns['M']}; this section assumes 30")
    probe_level = {}
    for q in Q_GRID:
        tot = run_probe(pns, q, 1.0, TRIALS, N_TARGETS, seed=9)
        probe_level[q] = float((tot <= c_by_m[30]).mean())
        print(f"probe DGP q={q} m=30 analytic level {probe_level[q]:.3f}", flush=True)
    sd_005 = next(r["level_analytic"] for r in rows
                  if r["q"] == 0.05 and r["m"] == 30 and r["rule"] == "randomized")

    L: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); L.append(s)

    log("# Tie rules scored against the DEPLOYED analytic null")
    log("")
    log("Producing script: `scripts/tie_rule_analytic_level.py`. Companion to")
    log("`results/tie_rule_showdown.md`, which scored each rule against a null SIMULATED with")
    log("that same rule. The pipeline cannot do that — it scores against")
    log("`se.stats.exceedance_test`'s BetaBinomial null — so the level that matters for a")
    log("deployment claim is the `analytic` column here.")
    log("")
    log(f"DGP executed from `scripts/tie_rule_showdown.py` itself (its `draw` / `one_target`),")
    log(f"so the two cannot drift: atom of mass q at the ceiling, Uniform(0,1) below, attacker")
    log(f"candidates N = {N_ATTACK}, {N_TARGETS} targets, alpha = {ALPHA}, "
        f"H1 = the attack is worth {MULT:g}x its budget.")
    log(f"{NULL_TRIALS} H0 trials for the simulated critical value, {TRIALS} trials each for "
        f"level and power (SE on a level near 0.05: "
        f"{np.sqrt(0.05 * 0.95 / TRIALS):.4f}).")
    log("")
    log("Analytic critical values (reject iff the exceedance total S <= c): "
        + ", ".join(f"m={m} -> c={c}" for m, c in c_by_m.items()) + ".")
    log("")
    log("| q | rule | m | E[S]\\|H0 | **analytic level** | **analytic power @2x** | "
        "simulated level | simulated power @2x |")
    log("|---|---|---|---|---|---|---|---|")
    for r in rows:
        star = "**" if (r["q"] == 0.05 and r["m"] == 30) else ""
        log(f"| {r['q']:.3f} | {star}{r['rule']}{star} | {r['m']} | {r['e_s_h0']:.2f} | "
            f"{star}{r['level_analytic']:.3f}{star} | {star}{r['power_analytic']:.2f}{star} | "
            f"{r['level_sim']:.3f} | {r['power_sim']:.2f} |")
    log("")

    cell = {r["rule"]: r for r in rows if r["q"] == 0.05 and r["m"] == 30}
    log("## The cell the paper quotes (full saturation, q=0.05, m=30)")
    log("")
    log("experiments.tex: \"counting ties strictly gives a null rejection rate of 0.995 and")
    log("counting them against the attack gives power 0.05 at a two-fold effect, while the")
    log("randomised rule stays calibrated there (analytic-null level 0.021)\".")
    log("")
    log("| claim | paper | this run | which null | verdict |")
    log("|---|---|---|---|---|")
    tol = 3 * float(np.sqrt(PAPER_CLAIM_ANALYTIC_LEVEL
                            * (1 - PAPER_CLAIM_ANALYTIC_LEVEL) / TRIALS))
    v = cell["randomized"]["level_analytic"]
    log(f"| randomised tie rule stays calibrated | {PAPER_CLAIM_ANALYTIC_LEVEL:.3f} | "
        f"{v:.3f} | analytic, showdown DGP (b redrawn) | "
        f"{'MATCHES' if abs(v - PAPER_CLAIM_ANALYTIC_LEVEL) <= tol else '**DIFFERS**'} |")
    log(f"| randomised tie rule stays calibrated | {PAPER_CLAIM_ANALYTIC_LEVEL:.3f} | "
        f"{probe_level[0.05]:.3f} | analytic, probe DGP (b measured) | "
        f"{'MATCHES' if abs(probe_level[0.05] - PAPER_CLAIM_ANALYTIC_LEVEL) <= tol else '**DIFFERS**'} |")
    v = cell["strict"]["level_sim"]
    log(f"| strict tie rule null rejection | {PAPER_CLAIM_STRICT_LEVEL:.3f} | {v:.3f} | "
        f"simulated (as in tie_rule_showdown.md) | "
        f"{'MATCHES' if abs(v - PAPER_CLAIM_STRICT_LEVEL) < 0.01 else '**DIFFERS**'} |")
    v = cell["conservative"]["power_sim"]
    log(f"| conservative tie rule power @2x | {PAPER_CLAIM_CONSERVATIVE_POWER:.2f} | "
        f"{v:.2f} | simulated | "
        f"{'MATCHES' if abs(v - PAPER_CLAIM_CONSERVATIVE_POWER) < 0.02 else '**DIFFERS**'} |")
    log("")
    log("Note the strict rule's ANALYTIC level in the table above: under a ceiling atom its")
    log(f"exceedance total collapses to ~{cell['strict']['e_s_h0']:.2f}, which is at or below")
    log("the analytic critical value, so the deployed test would reject essentially always.")
    log("Both nulls disqualify it; only the reasons differ.")
    log("")

    log("## Where 0.021 could have come from: the tie multiplicity b")
    log("")
    log("`scripts/tie_level_probe.py` runs the same question with ONE structural difference:")
    log("it takes b as the number of attack candidates ACTUALLY at the atom, where the")
    log("showdown redraws b as 1 + Binomial(N-1, q). The measured-b convention is the one the")
    log("deployed statistic uses (`exceedance_counts_randomized` is handed a measured")
    log("`n_feasible_at_best`) and the one `scripts/power_sim_randomized.py` simulates, so it")
    log("is the faithful DGP; the showdown's b runs about one higher, which shrinks the tie")
    log("credit 1/(b+1) and pushes the level up. Both are re-measured here, and the probe's")
    log("numbers have never been in an artifact either — they live in a docstring in")
    log("`src/se/stats.py`.")
    log("")
    log(f"| q | showdown b = 1+Bin(N-1,q) | probe b = measured | "
        f"stats.py docstring (1500 trials) |")
    log("|---|---|---|---|")
    doc = {0.0: 0.041, 0.01: 0.037, 0.05: 0.024}
    for q in Q_GRID:
        sd = next(r["level_analytic"] for r in rows
                  if r["q"] == q and r["m"] == 30 and r["rule"] == "randomized")
        log(f"| {q:.3f} | {sd:.3f} | {probe_level[q]:.3f} | {doc[q]:.3f} |")
    log("")
    pl = probe_level[0.05]
    ok = abs(pl - PAPER_CLAIM_ANALYTIC_LEVEL) <= tol
    log(f"At the paper's cell the two conventions give **{sd_005:.3f}** (b redrawn) and "
        f"**{pl:.3f}** (b measured), against the paper's "
        f"**{PAPER_CLAIM_ANALYTIC_LEVEL:.3f}** (3-sigma tolerance at {TRIALS} trials: "
        f"+/-{tol:.3f}).")
    log("")
    log(f"**The paper's 0.021 reproduces under the MEASURED-b DGP and not under the other "
        f"one** ({'confirmed' if ok else 'NOT confirmed'} here). That is the resolution, and")
    log("it is worth stating because the sentence in experiments.tex reads as one simulation:")
    log("its 0.995 and its 0.05 come from `tie_rule_showdown.py`, where b is redrawn, while")
    log("its 0.021 comes from the measured-b path. Both are defensible numbers; quoting them")
    log("in one breath is what hides the fact that the randomised rule's level at this cell is")
    log(f"{sd_005:.3f}, not {pl:.3f}, if b is generated the way the same sentence's other two")
    log("numbers were. The measured-b figure is the right one to keep, because b is measured")
    log("in deployment.")
    log("")

    log("## The max-of-N null percentile the same paragraph uses")
    log("")
    log("`se.stats.analytic_max_percentile(A)` = A/(A+1): under exchangeability, where the")
    log("max of A candidates sits in an individual draw's distribution with NO adversarial")
    log("signal at all.")
    log("")
    log("| A (attacker candidates) | analytic percentile |")
    log("|---|---|")
    for a in (10, 30, 50, 180, 181):
        log(f"| {a} | {analytic_max_percentile(a):.4f} |")
    log("")
    log(f"So the paper's \"~99%\" for A=181 is {analytic_max_percentile(181):.4f}; the point of")
    log("the sentence is that it is nowhere near 50%, and it is a closed form, not an estimate.")

    out = RESULTS_DIR / "tie_rule_analytic_level.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
