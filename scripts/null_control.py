"""Null / noise-floor control for the attack (external review B7, finding 13).

The confirmatory SE headline is BLOCKED until attack success is reported NET OF a
noise floor. Seeded SE is reproducible but each candidate's entropy is a finite
N=10 Monte-Carlo estimate, so the beam search's max over ~180 candidates is
upward-biased even without adversarial signal. This script quantifies that floor:

For each attacked target it draws K RANDOM NLI-passing paraphrases (the proposer +
feasibility gate, but NO optimization) and re-scores the SAME question under several
seeds, giving three bands of intended-direction entropy move:

  seed-noise floor    same question, different seed (pure N=10 estimator noise)
  benign floor        K unoptimised feasible paraphrases (what rephrasing gets free)
  attack              the optimised best_query

It places the attack as a PERCENTILE within the FULL benign distribution (NOT
max-vs-max: the attack searched ~180 candidates and the benign floor only K, so a
max-vs-max delta is biased toward the attack — critic, critique_log entry 13). The
headline "success" is attack > benign 90th percentile; the strict "attack > benign
max" is reported alongside for comparison only. A real targeted attack needs
seed < benign < attack with the net-move CI above 0; if benign already clears the
seed floor, that is evidence for the "SE fragile to any paraphrase" reframe (b),
though confounded by the shared NLI until the independent-clusterer arm runs.

GPU; ~(K + n_seeds) detector evals/target (<< the ~180 the attack uses).

    # in Ubuntu-24.04:  export HF_HOME=/home/abhi/.cache/huggingface
    ./.venv-wsl/bin/python scripts/null_control.py --tag _fair --K 8 --n_seeds 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import GenConfig, RESULTS_DIR
from se.sampling import DEFAULT_SAMPLES_DIR
from se.attacks.harness import load_pair, read_outcomes, _stable_seed
from se.attacks import proposer, feasibility
from se.se_pipeline import semantic_entropy
from se.stats import rate_ci, bootstrap_ci

CELLS = [("false_alarm", "se"), ("hide", "se")]


def _move(attack: str, before: float, after: float) -> float:
    return (before - after) if attack == "hide" else (after - before)


def _percentile_below(value: float, dist) -> float:
    """Fraction of dist strictly below value = value's percentile within dist."""
    if not dist:
        return float("nan")
    return sum(1 for d in dist if d < value) / len(dist)


def summarize_bands(attack_moves, benign_lists, seed_lists) -> dict:
    """Pure, hermetic aggregation for the null control (critic DoD, critique_log 13).

    Fixes the max-of-180 (attack) vs max-of-8 (benign) bias of the first version by
    placing the attack move as a PERCENTILE within the FULL benign-move distribution,
    and adds a same-question seed-noise floor as a second band. The three bands should
    order seed < benign < attack iff the attack is real signal beyond estimator noise.

      attack_moves[i]   scalar: optimised best_query's intended-direction move
      benign_lists[i]   list:   moves of K benign (unoptimised) feasible paraphrases
      seed_lists[i]     list:   moves of the SAME question re-scored under n_seeds seeds
    """
    n = len(attack_moves)
    all_benign = [b for lst in benign_lists for b in lst]
    all_seed = [s for lst in seed_lists for s in lst]

    beats_bmax, beats_bp90, pctiles, net_vs_bmean, benign_over_seed = [], [], [], [], []
    for a, benign, seed in zip(attack_moves, benign_lists, seed_lists):
        if benign:
            beats_bmax.append(a > max(benign))                      # strict, budget-biased
            beats_bp90.append(a > float(np.percentile(benign, 90)))  # budget-robust
            pctiles.append(_percentile_below(a, benign))
            net_vs_bmean.append(a - float(np.mean(benign)))
        if benign and seed:
            benign_over_seed.append(float(np.mean(benign)) > max(seed))

    return {
        "n": n,
        "mean_seed_move": float(np.mean(all_seed)) if all_seed else float("nan"),
        "mean_benign_move": float(np.mean(all_benign)) if all_benign else float("nan"),
        "mean_attack_move": float(np.mean(attack_moves)) if attack_moves else float("nan"),
        "beats_benign_p90_ci": rate_ci(beats_bp90) if beats_bp90 else None,   # headline
        "beats_benign_max_ci": rate_ci(beats_bmax) if beats_bmax else None,   # comparison
        "mean_attack_percentile": float(np.mean(pctiles)) if pctiles else float("nan"),
        "net_vs_benign_mean_ci": bootstrap_ci(net_vs_bmean, np.mean) if net_vs_bmean else None,
        "benign_over_seed_ci": rate_ci(benign_over_seed) if benign_over_seed else None,  # reframe (b)
    }


def _benign_moves(question: str, before: float, attack: str, pair, gen,
                  K: int, seed: int) -> list[float]:
    """Intended-direction moves for K benign (unoptimized) feasible paraphrases."""
    proposer.seed_proposer(seed)
    moves: list[float] = []
    tries = 0
    while len(moves) < K and tries < K * 5:
        tries += 1
        cand = proposer.propose(question, pair.lm)
        if not feasibility.check(cand, question, pair.nli).feasible:
            continue
        ent = semantic_entropy(cand, pair.lm, pair.nli, gen).entropy_nats
        moves.append(_move(attack, before, ent))
    return moves


def _seed_noise_moves(question: str, before: float, attack: str, pair,
                      base_gen, n_seeds: int) -> list[float]:
    """Intended-direction 'moves' of the SAME question re-scored under n_seeds seeds
    — pure N=10 estimator noise with NO paraphrase, the floor below the benign floor.
    (seed 0 reproduces `before`, so its move is ~0; other seeds expose the wobble.)"""
    moves = []
    for s in range(n_seeds):
        g = GenConfig(max_new_tokens=base_gen.max_new_tokens,
                      temperature=base_gen.temperature, top_p=base_gen.top_p,
                      n_samples=base_gen.n_samples, seed=s)
        ent = semantic_entropy(question, pair.lm, pair.nli, g).entropy_nats
        moves.append(_move(attack, before, ent))
    return moves


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_fair")
    ap.add_argument("--K", type=int, default=8, help="benign paraphrases per target")
    ap.add_argument("--n_seeds", type=int, default=3, help="seeds for the original noise band")
    ap.add_argument("--max_targets", type=int, default=0, help="0 = all completed targets")
    args = ap.parse_args()

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    pair = load_pair()
    print(f"[load] pair ready; dir={campaign_dir}", flush=True)

    def _ci(c):
        return "n/a" if c is None else f"{c.point:+.3f} [{c.lo:+.3f}, {c.hi:+.3f}]"
    def _pc(c):
        return "n/a" if c is None else f"{c.point:.0%} [{c.lo:.0%}, {c.hi:.0%}]"

    L: list[str] = ["# Null / noise-floor control (three-band: seed < benign < attack)", ""]
    L.append(f"K={args.K} benign feasible paraphrases + {args.n_seeds} same-question seeds "
             f"per target, on the fair pool ({campaign_dir.name}). The attack is placed as "
             f"a PERCENTILE within the FULL benign-move distribution (not max-vs-max, which "
             f"is biased toward the attack by its larger candidate budget). Headline success "
             f"= attack move exceeds the benign 90th percentile. See docs/critique_log.md 13.")
    L.append("")

    for attack, detector in CELLS:
        f = campaign_dir / f"triviaqa_{detector}_{attack}.jsonl"
        if not f.exists():
            L.append(f"## {detector}_{attack}: no outcomes yet"); L.append(""); continue
        outcomes = read_outcomes(f)
        if args.max_targets:
            outcomes = outcomes[: args.max_targets]

        attack_moves, benign_lists, seed_lists = [], [], []
        for o in outcomes:
            benign = _benign_moves(o.question, o.entropy_before, o.attack, pair, gen,
                                   args.K, seed=_stable_seed("null:" + o.question_id))
            seed = _seed_noise_moves(o.question, o.entropy_before, o.attack, pair, gen,
                                     args.n_seeds)
            atk = _move(o.attack, o.entropy_before, o.entropy_after)
            attack_moves.append(atk); benign_lists.append(benign); seed_lists.append(seed)
            pct = _percentile_below(atk, benign)
            print(f"  {o.question_id}: attack {atk:+.3f} | benign(mean {np.mean(benign):+.3f}, "
                  f"max {max(benign):+.3f}) | attack pctile {pct:.0%}", flush=True)

        agg = summarize_bands(attack_moves, benign_lists, seed_lists)
        L.append(f"## {detector.upper()} / {attack}  (n={agg['n']})")
        L.append("")
        L.append("Three bands (mean intended move, nats) — expect seed < benign < attack:")
        L.append(f"- seed-noise floor (same question):   {agg['mean_seed_move']:+.3f}")
        L.append(f"- benign-paraphrase floor:            {agg['mean_benign_move']:+.3f}")
        L.append(f"- optimised attack:                   {agg['mean_attack_move']:+.3f}")
        L.append("")
        L.append(f"- attack vs benign, headline (beats benign p90):  {_pc(agg['beats_benign_p90_ci'])}")
        L.append(f"- attack vs benign, strict (beats benign max):    {_pc(agg['beats_benign_max_ci'])} "
                 f"(budget-biased toward the attack; report for comparison only)")
        L.append(f"- mean attack percentile within benign dist:      {agg['mean_attack_percentile']:.0%}")
        L.append(f"- net move (attack - mean benign):                {_ci(agg['net_vs_benign_mean_ci'])} nats")
        L.append(f"- benign clears the seed floor (reframe (b)):      {_pc(agg['benign_over_seed_ci'])}")
        L.append("")
        L.append("Reading: (a) targeted-attack claim needs 'beats benign p90' and the net-move "
                 "CI well above 0. (b) 'SE fragile to any paraphrase' needs 'benign clears the "
                 "seed floor' high — but that is confounded by the shared NLI until the "
                 "independent-clusterer arm runs (finding 14).")
        L.append("")

    out = RESULTS_DIR / "null_control_report.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
