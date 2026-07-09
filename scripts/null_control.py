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
from se.entropy import cluster_and_score_exact, cluster_and_score_embedding, cluster_and_score_judge
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


def _per_target_nets(attack_moves, benign_lists):
    """Per-target net = attack move - mean benign move (paired within a target)."""
    return [a - float(np.mean(b)) for a, b in zip(attack_moves, benign_lists) if b]


def survival_ratio(nli_nets, embed_nets, *, n_boot: int = 3000, seed: int = 0):
    """embedding_net / NLI_net with a paired bootstrap CI over targets (critic entry 15):
    the fraction of the confounded NLI-measured effect that survives under the independent
    encoder. ~1 -> attack is real (reframe a); ~0 -> attack was largely an NLI-clusterer
    artifact. Returns a se.stats.CI or None."""
    from se.stats import CI
    if not nli_nets or not embed_nets:
        return None
    m = min(len(nli_nets), len(embed_nets))
    a = np.asarray(nli_nets[:m], float)
    b = np.asarray(embed_nets[:m], float)

    def _ratio(idx):
        na = a[idx].mean()
        return (b[idx].mean() / na) if abs(na) > 1e-9 else float("nan")

    point = _ratio(np.arange(m))
    rng = np.random.default_rng(seed)
    vals = [r for _ in range(n_boot)
            if (r := _ratio(rng.integers(0, m, m))) == r]  # drop nan (near-zero NLI net)
    if not vals:
        return CI(point, float("nan"), float("nan"))
    return CI(point, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)))


def _reseed(gen, seed: int):
    return GenConfig(max_new_tokens=gen.max_new_tokens, temperature=gen.temperature,
                     top_p=gen.top_p, n_samples=gen.n_samples, seed=seed)


def _arms(question, pair, gen, embed_fn, threshold, judge_fn=None, seed: int | None = None):
    """(NLI, exact-match, embedding, judge) entropy from the SAME seeded samples — up to
    four clusterings of ONE model output (finding-14). embedding/judge are None if their
    oracle is not supplied. The judge arm is O(n^2) LLM calls, so it is opt-in."""
    g = gen if seed is None else _reseed(gen, seed)
    res = semantic_entropy(question, pair.lm, pair.nli, g)
    nli = res.entropy_nats
    exact = cluster_and_score_exact(res.samples).entropy_nats
    emb = (cluster_and_score_embedding(res.samples, embed_fn, threshold).entropy_nats
           if embed_fn is not None else None)
    jud = (cluster_and_score_judge(res.samples, judge_fn).entropy_nats
           if judge_fn is not None else None)
    return nli, exact, emb, jud


def _moves(before, after, attack):
    """(nli, exact, embed, judge) intended-direction moves; embed/judge None if not scored."""
    def _m(i):
        return _move(attack, before[i], after[i]) if before[i] is not None and after[i] is not None else None
    return _move(attack, before[0], after[0]), _m(1), _m(2), _m(3)


def _benign_moves_arms(question, before, attack, pair, gen, K, seed, embed_fn, threshold, judge_fn=None):
    """K benign feasible paraphrases -> (nli, exact, embed, judge) move lists from the same
    generations. embed/judge lists are empty if their oracle is absent."""
    proposer.seed_proposer(seed)
    nm, xm, em, jm, tries = [], [], [], [], 0
    while len(nm) < K and tries < K * 5:
        tries += 1
        cand = proposer.propose(question, pair.lm)
        if not feasibility.check(cand, question, pair.nli).feasible:
            continue
        n, x, e, j = _moves(before, _arms(cand, pair, gen, embed_fn, threshold, judge_fn), attack)
        nm.append(n); xm.append(x)
        if e is not None:
            em.append(e)
        if j is not None:
            jm.append(j)
    return nm, xm, em, jm


def _seed_moves_arms(question, before, attack, pair, gen, n_seeds, embed_fn, threshold, judge_fn=None):
    """Same question re-scored under n_seeds seeds -> (nli, exact, embed) move lists.

    Seeds start at 1, NOT 0: `before` is generated at the baseline gen.seed=0, so a seed-0
    draw here reproduces `before` exactly (torch.manual_seed(0) resets the RNG identically)
    and injects a structural 0.0 move into every target's seed band — deflating the noise
    floor and biasing the seed<benign ordering + benign_over_seed reframe check toward the
    attack. Excluding seed 0 keeps the seed band an honest estimate of estimator noise."""
    nm, xm, em, jm = [], [], [], []
    for s in range(1, n_seeds + 1):
        n, x, e, j = _moves(before, _arms(question, pair, gen, embed_fn, threshold, judge_fn, seed=s), attack)
        nm.append(n); xm.append(x)
        if e is not None:
            em.append(e)
        if j is not None:
            jm.append(j)
    return nm, xm, em, jm


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
    ap.add_argument("--judge_model", default="",
                    help="e.g. Qwen/Qwen2.5-7B-Instruct to add the LLM-judge arm (finding 14, O(n^2))")
    args = ap.parse_args()

    campaign_dir = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
    gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=0)
    pair = load_pair()
    print(f"[load] pair ready; dir={campaign_dir}", flush=True)

    embed_fn = None
    if args.embedding_model:
        import math as _math
        if not _math.isfinite(args.embed_threshold):
            raise SystemExit(f"--embed_threshold must be finite, got {args.embed_threshold}. "
                             f"A nan/inf cut (e.g. from a below-chance calibration) would make "
                             f"the embedding clusterer degenerate to all-singletons.")
        from se.embedding import load_embedder
        prefix = "" if "gtr" in args.embedding_model else "query: "
        embed_fn = load_embedder(args.embedding_model, prefix=prefix)
        print(f"[embed] {args.embedding_model} loaded (threshold {args.embed_threshold})", flush=True)

    judge_fn = None
    if args.judge_model:
        from se.judge import load_judge
        judge_fn = load_judge(args.judge_model)
        print(f"[judge] {args.judge_model} loaded (O(n^2) LLM calls per candidate)", flush=True)

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
                 f"NLI is the confounded/permissive bound; exact-match the strict bound "
                 f"(over-counts surface-form change); the embedding arm ADJUDICATES but MUST be "
                 f"threshold-calibrated first — an uncalibrated cosine cut saturates it "
                 f"(scripts/calibrate_embed_threshold.py). Do NOT lift these numbers into the paper.")
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
        atk = {"nli": [], "exact": [], "embed": [], "judge": []}
        ben = {"nli": [], "exact": [], "embed": [], "judge": []}
        sd = {"nli": [], "exact": [], "embed": [], "judge": []}
        for o in outcomes:
            before = _arms(o.question, pair, gen, embed_fn, args.embed_threshold, judge_fn)
            after = _arms(o.best_query, pair, gen, embed_fn, args.embed_threshold, judge_fn)
            an, ax, ae, aj = _moves(before, after, o.attack)
            atk["nli"].append(an); atk["exact"].append(ax)
            if ae is not None: atk["embed"].append(ae)
            if aj is not None: atk["judge"].append(aj)
            s = _stable_seed("null:" + o.question_id)
            bnl, bxl, bel, bjl = _benign_moves_arms(o.question, before, o.attack, pair, gen,
                                                    args.K, s, embed_fn, args.embed_threshold, judge_fn)
            snl, sxl, sel, sjl = _seed_moves_arms(o.question, before, o.attack, pair, gen,
                                                  args.n_seeds, embed_fn, args.embed_threshold, judge_fn)
            ben["nli"].append(bnl); ben["exact"].append(bxl); sd["nli"].append(snl); sd["exact"].append(sxl)
            if embed_fn is not None:
                ben["embed"].append(bel); sd["embed"].append(sel)
            if judge_fn is not None:
                ben["judge"].append(bjl); sd["judge"].append(sjl)
            print(f"  {o.question_id}: attack nli {an:+.3f} / exact {ax:+.3f}"
                  + (f" / embed {ae:+.3f}" if ae is not None else "")
                  + (f" / judge {aj:+.3f}" if aj is not None else "")
                  + f" | benign nli-mean {np.mean(bnl):+.3f}", flush=True)

        arms = [("shared NLI clusterer (the detector's own — confounded/permissive bound)",
                 atk["nli"], ben["nli"], sd["nli"]),
                ("independent exact-match clusterer (strict bound — over-counts surface form)",
                 atk["exact"], ben["exact"], sd["exact"])]
        if embed_fn is not None:
            arms.append((f"independent embedding-cosine clusterer "
                         f"({args.embedding_model} @ {args.embed_threshold}) — reframe-(b) ADJUDICATOR",
                         atk["embed"], ben["embed"], sd["embed"]))
        if judge_fn is not None:
            arms.append((f"independent LLM-judge clusterer ({args.judge_model}) — finding-14 ADJUDICATOR "
                         f"(hard-neg-validated; positive-recognition ~0.7 -> slightly over-splits)",
                         atk["judge"], ben["judge"], sd["judge"]))
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
        for arm_key, arm_label, present in [("embed", "embedding", embed_fn is not None),
                                            ("judge", "LLM-judge", judge_fn is not None)]:
            if not present:
                continue
            sr = survival_ratio(_per_target_nets(atk["nli"], ben["nli"]),
                                _per_target_nets(atk[arm_key], ben[arm_key]))
            if sr is not None:
                L.append(f"### Survival ratio ({arm_label}_net / NLI_net) — SUPPLEMENTARY (not headline)")
                L.append(f"- {arm_label}_net / NLI_net = {sr.point:+.2f} [{sr.lo:+.2f}, {sr.hi:+.2f}]. "
                         f"CAVEAT: a ratio of two nets is inflated when the {arm_label} benign floor is "
                         f"low; read the PERCENTILE comparison above as the headline, not this ratio.")
                L.append("- Net is per-target: mean_i(attack_i - mean(benign_i)), which differs from "
                         "(pooled mean attack - pooled mean benign) when per-target benign counts vary.")
                L.append("")
        L.append("Reading the arms (finding 14): NLI is the confounded/permissive bound; exact-match "
                 "the strict/saturated bound; a VALIDATED LLM-judge (if present) is the ADJUDICATOR. "
                 "HEADLINE INDICATOR = the attack's PERCENTILE within the benign distribution under "
                 "each clusterer (beats-benign-p90 + mean-percentile): it is null-controlled AND "
                 "scale-free, so it is robust to a clusterer's benign-floor LEVEL. The net-ratio "
                 "below is a SUPPLEMENTARY view only — it is inflated when a clusterer's benign floor "
                 "is low (e.g. the judge's -0.19), so do NOT read it as the headline. The raw "
                 "attack-move is NOT null-controlled (winner's-curse biased). Claim reframe (a) IFF "
                 "the ADJUDICATOR's net CI > 0 at n>=80 (critique_log 15); the NLI-arm alone is "
                 "necessary but NOT sufficient (it cannot separate a real answer-distribution change "
                 "from the NLI clusterer partitioning the same answers differently).")
        L.append("")

    out = RESULTS_DIR / "null_control_report.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
