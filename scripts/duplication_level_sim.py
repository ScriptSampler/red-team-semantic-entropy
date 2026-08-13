"""H0 level of the exceedance test when the two arms DUPLICATE at different rates. CPU only.

THE SECOND EXCHANGEABILITY THREAT, and it is not the one the critic named. `proposer.propose`
decodes GREEDILY: diversity comes only from randomising the instruction (10 verbs x 8 styles
x 5 templates), so for a FIXED parent the reachable candidate set is small and repeats.
The two arms then duplicate at very different rates, because they have different numbers of
parents:

  * the attack draws its A ~ 181 candidates from up to 3 fresh parents per round over 20
    rounds, so it samples many small reachable sets. Measured on the one ablation target on
    disk (results/null_objective_ablation_ckpt_def.jsonl): 73 DISTINCT strings from 181 calls.
  * every benign draw in `null_control._benign_moves_arms` is a rewrite of the SAME original
    question, so all m draws come from one reachable set. Same target: 6 feasible survivors.

`exceedance_test` assumes the A attack candidates and the m benign draws are exchangeable
draws from one F. Duplication does not by itself break that — a duplicated value is a tie and
the randomised rule prices ties — but ASYMMETRIC duplication does, and its sign is not
obvious: heavier benign duplication clusters the benign draws (over-dispersing K, which
widens the true null relative to the assumed BetaBinomial), while heavier attack duplication
inflates b (which SHRINKS the tie credit 1/(b+1), the documented anti-conservative
direction). Both act at once.

This project's standing rule is that every tie/censoring intuition here has been wrong until
simulated (critique_log 26). So this simulates it rather than arguing it: build both arms
under a TRUE null — one shared F per target, values iid across DISTINCT candidates, then
replicated to the arm's call count — and measure the rejection rate at nominal 0.05.

    python scripts/duplication_level_sim.py --trials 400
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import exceedance_counts_randomized, exceedance_test   # noqa: E402


def _multiplicities(total: int, n_distinct: int, rng) -> np.ndarray:
    """Split `total` draws over `n_distinct` reachable strings, uniformly at random."""
    n_distinct = max(1, min(int(n_distinct), int(total)))
    # every distinct string appears at least once, the rest fall where they may
    counts = np.ones(n_distinct, dtype=int)
    if total > n_distinct:
        extra = rng.integers(0, n_distinct, size=total - n_distinct)
        counts += np.bincount(extra, minlength=n_distinct)
    return counts


def _arm_values(total: int, n_distinct: int, q_ceiling: float, cap: float, rng):
    """Values for one arm: iid F per DISTINCT candidate, replicated to `total` calls.

    F = an atom of mass `q_ceiling` at the log(N) cap plus a continuous part below it, which
    is the shape the real score has (results/ceiling_saturation_finding.md)."""
    counts = _multiplicities(total, n_distinct, rng)
    k = len(counts)
    at_cap = rng.random(k) < q_ceiling
    vals = np.where(at_cap, cap, rng.uniform(0.0, cap, size=k))
    return np.repeat(vals, counts)


def simulate_level(*, n_targets=80, A=181, m=50, uniq_a=181, uniq_b=50, q_ceiling=0.05,
                   trials=400, alpha=0.05, cap=float(np.log(10)), seed=0) -> dict:
    """H0 rejection rate of the deployed test with the two arms duplicating as specified.

    `uniq_a`/`uniq_b` are the DISTINCT reachable strings behind each arm's A / m calls;
    setting both equal to the call count is the no-duplication reference. H0 is true by
    construction: both arms draw from the same F on every target."""
    rng = np.random.default_rng(seed)
    rejects = 0
    kbars, bbars = [], []
    for _ in range(int(trials)):
        amax, blists, bmul = [], [], []
        for _ in range(int(n_targets)):
            av = _arm_values(A, uniq_a, q_ceiling, cap, rng)
            bv = _arm_values(m, uniq_b, q_ceiling, cap, rng)
            mx = float(av.max())
            amax.append(mx)
            bmul.append(int(np.isclose(av, mx).sum()))     # b, counting replicates as the optimiser does
            blists.append(list(map(float, bv)))
        counts = exceedance_counts_randomized(amax, blists, bmul, n_attack_candidates=A,
                                              seed=int(rng.integers(0, 2**31 - 1)))
        r = exceedance_test(counts, A)
        rejects += int(r["p_value"] <= alpha)
        kbars.append(r["observed"] / max(1, r["n_targets"]))
        bbars.append(float(np.mean(bmul)))
    return {
        "uniq_a": uniq_a, "uniq_b": uniq_b, "q_ceiling": q_ceiling,
        "level": rejects / trials,
        "mean_Kbar": float(np.mean(kbars)),
        "expected_Kbar": m / (A + 1),
        "Kbar_ratio": float(np.mean(kbars)) / (m / (A + 1)),
        "mean_b": float(np.mean(bbars)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--n_targets", type=int, default=80)
    ap.add_argument("--A", type=int, default=181)
    ap.add_argument("--m", type=int, default=50)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    # (uniq_a, uniq_b, q): the reference, then the measured asymmetry, then its two halves
    # separated so the sign of each mechanism is visible on its own.
    cells = [
        (args.A, args.m, 0.05, "reference: no duplication in either arm"),
        (args.A, args.m, 0.20, "reference, heavier ceiling atom"),
        (73, args.m, 0.05, "attack duplicates only (73/181 distinct, measured)"),
        (args.A, 6, 0.05, "benign duplicates only (6 distinct, measured)"),
        (73, 6, 0.05, "BOTH, as measured on the one ablation target"),
        (73, 6, 0.20, "BOTH, heavier ceiling atom"),
        (73, 20, 0.05, "BOTH, a milder benign collapse"),
    ]
    print(f"H0 level at alpha={args.alpha}, n_targets={args.n_targets}, A={args.A}, "
          f"m={args.m}, {args.trials} trials")
    print(f"{'uniq_a':>7}{'uniq_b':>8}{'q':>7}{'level':>8}{'Kbar':>8}{'/exp':>7}{'mean b':>8}"
          f"   note")
    for ua, ub, q, note in cells:
        r = simulate_level(n_targets=args.n_targets, A=args.A, m=args.m, uniq_a=ua, uniq_b=ub,
                           q_ceiling=q, trials=args.trials, alpha=args.alpha)
        flag = "  <-- ANTI-CONSERVATIVE" if r["level"] > 2 * args.alpha else ""
        print(f"{ua:>7}{ub:>8}{q:>7.2f}{r['level']:>8.3f}{r['mean_Kbar']:>8.3f}"
              f"{r['Kbar_ratio']:>7.2f}{r['mean_b']:>8.1f}   {note}{flag}")
    print(f"\nexpected Kbar under the deployed null = m/(A+1) = {args.m/(args.A+1):.4f}; "
          f"the '/exp' column is the entry-23 gate ratio, band [0.5, 2.0].")
    return 0


if __name__ == "__main__":
    sys.exit(main())
