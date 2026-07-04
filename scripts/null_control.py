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
from se.entropy import cluster_and_score_exact, cluster_and_score_embedding
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


def _reseed(gen, seed: int):
    return GenConfig(max_new_tokens=gen.max_new_tokens, temperature=gen.temperature,
                     top_p=gen.top_p, n_samples=gen.n_samples, seed=seed)


def _arms(question, pair, gen, embed_fn, threshold, seed: int | None = None):
    """(NLI, exact-match, embedding) entropy from the SAME seeded samples — up to three
    clusterings of ONE model output (finding-14 2x2/3-arm). embedding is None if no
    embed_fn (embedding requires the encoder model)."""
    g = gen if seed is None else _reseed(gen, seed)
    res = semantic_entropy(question, pair.lm, pair.nli, g)
    nli = res.entropy_nats
    exact = cluster_and_score_exact(res.samples).entropy_nats
    emb = (cluster_and_score_embedding(res.samples, embed_fn, threshold).entropy_nats
           if embed_fn is not None else None)
    return nli, exact, emb


def _moves(before, after, attack):
    """(nli, exact, embed) intended-direction moves; embed move is None if not scored."""
    n = _move(attack, before[0], after[0])
    x = _move(attack, before[1], after[1])
    e = _move(attack, before[2], after[2]) if before[2] is not None and after[2] is not None else None
    return n, x, e


def _benign_moves_arms(question, before, attack, pair, gen, K, seed, embed_fn, threshold):
    """K benign feasible paraphrases -> (nli, exact, embed) move lists from the same
    generations. embed list is empty if no embed_fn."""
    proposer.seed_proposer(seed)
    nm, xm, em, tries = [], [], [], 0
    while len(nm) < K and tries < K * 5:
        tries += 1
        cand = proposer.propose(question, pair.lm)
        if not feasibility.check(cand, question, pair.nli).feasible:
            continue
        n, x, e = _moves(before, _arms(cand, pair, gen, embed_fn, threshold), attack)
        nm.append(n); xm.append(x)
        if e is not None:
            em.append(e)
    return nm, xm, em


def _seed_moves_arms(question, before, attack, pair, gen, n_seeds, embed_fn, threshold):
    """Same question re-scored under n_seeds seeds -> (nli, exact, embed) move lists."""
    nm, xm, em = [], [], []
    for s in range(n_seeds):
        n, x, e = _moves(before, _arms(question, pair, gen, embed_fn, threshold, seed=s), attack)
        nm.append(n); xm.append(x)
        if e is not None:
            em.append(e)
    return nm, xm, em


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_fair")
    ap.add_argument("--K", type=int, default=8, help="benign paraphrases per target")
    ap.add_argument("--n_seeds", type=int, default=3, help="seeds for the original noise band")
    ap.add_argument("--max_targets", type=int, default=0, help="0 = all completed targets")
    ap.add_argument("--embedding_model", default="",
                    help="e.g. intfloat/e5-base-unsupervised to add the embedding arm (finding 14)")
    ap.add_argument("--embed_threshold", type=float, default=0.82,
                    help="cosine threshold for the embedding clusterer (calibrate; default 0.82)")
    args = ap.parse_args()

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    pair = load_pair()
    print(f"[load] pair ready; dir={campaign_dir}", flush=True)

    embed_fn = None
    if args.embedding_model:
        from se.embedding import load_embedder
        prefix = "" if "gtr" in args.embedding_model else "query: "
        embed_fn = load_embedder(args.embedding_model, prefix=prefix)
        print(f"[embed] {args.embedding_model} loaded (threshold {args.embed_threshold})", flush=True)

    def _ci(c):
        return "n/a" if c is None else f"{c.point:+.3f} [{c.lo:+.3f}, {c.hi:+.3f}]"
    def _pc(c):
        return "n/a" if c is None else f"{c.point:.0%} [{c.lo:.0%}, {c.hi:.0%}]"

    L: list[str] = ["# Null / noise-floor control (three-band: seed < benign < attack)", ""]
    n_total = sum(len(read_outcomes(campaign_dir / f"triviaqa_{d}_{a}.jsonl"))
                  for a, d in CELLS if (campaign_dir / f"triviaqa_{d}_{a}.jsonl").exists())
    if n_total < 80:
        L.append(f"> ⚠ MACHINERY-VALIDATION ONLY (n={n_total} < 80). These numbers are NOT a "
                 f"result — they confirm the pipeline runs and reports correctly on real "
                 f"generations. A confirmatory claim needs n>=80/stratum (critique_log 13). "
                 f"The exact-match arm is the STRICT bound (over-counts surface-form change); "
                 f"reframe (b) is adjudicated only under an embedding-cosine clusterer, not "
                 f"yet added. Do NOT lift these numbers into the paper.")
        L.append("")
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

        # Collect the three bands under up to THREE clusterers (finding-14 arms) from the
        # same generations: NLI (shared/confounded), exact-match (independent, strict),
        # embedding-cosine (independent, semantic — the reframe-(b) adjudicator).
        atk = {"nli": [], "exact": [], "embed": []}
        ben = {"nli": [], "exact": [], "embed": []}
        sd = {"nli": [], "exact": [], "embed": []}
        for o in outcomes:
            before = _arms(o.question, pair, gen, embed_fn, args.embed_threshold)
            after = _arms(o.best_query, pair, gen, embed_fn, args.embed_threshold)
            an, ax, ae = _moves(before, after, o.attack)
            atk["nli"].append(an); atk["exact"].append(ax)
            if ae is not None:
                atk["embed"].append(ae)
            s = _stable_seed("null:" + o.question_id)
            bnl, bxl, bel = _benign_moves_arms(o.question, before, o.attack, pair, gen,
                                               args.K, s, embed_fn, args.embed_threshold)
            snl, sxl, sel = _seed_moves_arms(o.question, before, o.attack, pair, gen,
                                             args.n_seeds, embed_fn, args.embed_threshold)
            ben["nli"].append(bnl); ben["exact"].append(bxl); sd["nli"].append(snl); sd["exact"].append(sxl)
            if embed_fn is not None:
                ben["embed"].append(bel); sd["embed"].append(sel)
            print(f"  {o.question_id}: attack nli {an:+.3f} / exact {ax:+.3f}"
                  + (f" / embed {ae:+.3f}" if ae is not None else "")
                  + f" | benign nli-mean {np.mean(bnl):+.3f}", flush=True)

        arms = [("shared NLI clusterer (the detector's own — confounded/permissive bound)",
                 atk["nli"], ben["nli"], sd["nli"]),
                ("independent exact-match clusterer (strict bound — over-counts surface form)",
                 atk["exact"], ben["exact"], sd["exact"])]
        if embed_fn is not None:
            arms.append((f"independent embedding-cosine clusterer "
                         f"({args.embedding_model} @ {args.embed_threshold}) — reframe-(b) ADJUDICATOR",
                         atk["embed"], ben["embed"], sd["embed"]))
        L.append(f"## {detector.upper()} / {attack}  (n={len(outcomes)})")
        L.append("")
        for arm_name, am, bl, sl in arms:
            agg = summarize_bands(am, bl, sl)
            L.append(f"### {arm_name}")
            L.append("Three bands (mean intended move, nats) — expect seed < benign < attack:")
            L.append(f"- seed-noise floor: {agg['mean_seed_move']:+.3f} · "
                     f"benign floor: {agg['mean_benign_move']:+.3f} · "
                     f"attack: {agg['mean_attack_move']:+.3f}")
            L.append(f"- attack beats benign p90 (headline): {_pc(agg['beats_benign_p90_ci'])} · "
                     f"beats benign max (budget-biased): {_pc(agg['beats_benign_max_ci'])}")
            L.append(f"- mean attack percentile in benign: {agg['mean_attack_percentile']:.0%} · "
                     f"net (attack - mean benign): {_ci(agg['net_vs_benign_mean_ci'])} nats")
            L.append(f"- benign clears seed floor (reframe b): {_pc(agg['benign_over_seed_ci'])}")
            L.append("")
        L.append("Reading the 2x2 (finding 14): a targeted attack needs 'beats benign p90' + "
                 "net CI > 0. Reframe (b) 'SE fragile to any paraphrase' needs the benign floor "
                 "to clear the seed floor UNDER THE INDEPENDENT CLUSTERER — if it only clears it "
                 "under the shared NLI, the 'fragility' was the NLI talking to itself, not a "
                 "property of the model's answer distribution.")
        L.append("")

    out = RESULTS_DIR / "null_control_report.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
