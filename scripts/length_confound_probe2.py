"""Follow-ups to scripts/length_confound_probe.py.

Three questions the first probe raised but did not settle:

  G. Does semantic entropy actually BEAT a trivial mean-generation-length baseline?
     Probe 1 found length alone scores AUROC 0.631 against SE's 0.694. That gap needs
     a PAIRED interval (same questions, resampled jointly) before anything is said
     about it, and a combined detector to see whether SE is even the better of the two
     signals it is implicitly mixing.

  H. Does the FALSE-ALARM ATTACK work by lengthening the generations? The attack drives
     entropy up on questions the model answers correctly. If the winning paraphrase also
     makes the model produce LONGER answers, then part of the measured entropy move is
     the same length effect rather than a semantic one. This is the version of the
     length question that touches the attack claims rather than the clean ones.

  I. What does the attack cell actually store -- can H be answered from cache at all?

CPU only; reads the same cache.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from pathlib import Path

import numpy as np

from length_confound_probe import (auroc, index_by, read_jsonl, spearman,
                                   stratum_ids, wilson_ci)


def paired_boot_auroc_delta(s_a, s_b, y, *, seed=0, n_boot=4000, alpha=0.05):
    """Bootstrap the DIFFERENCE auroc(a) - auroc(b) resampling questions jointly, so
    the two detectors always see the same resampled pool."""
    rng = np.random.default_rng(seed)
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yy = y[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        vals.append(auroc(s_a[idx], yy) - auroc(s_b[idx], yy))
    v = np.sort(np.array(vals))
    return (float(v.mean()), float(np.quantile(v, alpha / 2)),
            float(np.quantile(v, 1 - alpha / 2)))


def zscore(x):
    return (x - x.mean()) / (x.std() or 1.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="~/.cache/se-research/samples")
    ap.add_argument("--pool", default="wk4_full_2000q")
    ap.add_argument("--fa_tag", default="wk9_defb")
    ap.add_argument("--n_boot", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    L: list[str] = []

    def say(s=""):
        print(s, flush=True)
        L.append(s)

    root = Path(os.path.expanduser(args.cache))
    smp = index_by(read_jsonl(root / args.pool / "samples.jsonl"))
    ent = index_by(read_jsonl(root / args.pool / "entropy.jsonl"))
    rel = index_by(read_jsonl(root / args.pool / "relabeled.jsonl"))
    qids = [q for q in smp if q in ent and q in rel]

    y = np.array([0 if bool(rel[q]["greedy_correct"]) else 1 for q in qids])
    hh = np.array([ent[q]["entropy_nats"] for q in qids], float)
    ml = np.array([statistics.mean(len(s.split()) for s in smp[q]["samples"])
                   for q in qids], float)

    # =======================================================================
    say("=" * 78)
    say("G. DOES SEMANTIC ENTROPY BEAT A MEAN-LENGTH BASELINE?")
    say("=" * 78)
    say("  A paper-grade detector claim needs to clear the cheapest baseline that")
    say("  shares its inputs. Mean generation length costs nothing: no NLI model, no")
    say("  clustering, no second forward pass.")
    say()

    for lbl, sel in (("full labelled pool", np.ones(len(qids), bool)),):
        d, lo, hi = paired_boot_auroc_delta(hh[sel], ml[sel], y[sel],
                                            seed=args.seed, n_boot=args.n_boot)
        say(f"  {lbl} (n={int(sel.sum())}):")
        say(f"    SE AUROC              {auroc(hh[sel], y[sel]):.4f}")
        say(f"    mean-length AUROC     {auroc(ml[sel], y[sel]):.4f}")
        say(f"    PAIRED delta SE-length {d:+.4f} [{lo:+.4f}, {hi:+.4f}]"
            f"   {'SIGNIFICANT' if lo > 0 else 'NOT significant'}")
    say()

    right = stratum_ids("right", 0, rel)[:200]
    wrong = stratum_ids("wrong", 0, rel)[:200]
    fair = [q for q in right + wrong if q in ent and q in smp]
    fidx = np.array([qids.index(q) for q in fair])
    d, lo, hi = paired_boot_auroc_delta(hh[fidx], ml[fidx], y[fidx],
                                        seed=args.seed, n_boot=args.n_boot)
    say(f"  FAIR POOL (n={len(fair)}) -- the pool the headline 0.704 is quoted on:")
    say(f"    SE AUROC              {auroc(hh[fidx], y[fidx]):.4f}")
    say(f"    mean-length AUROC     {auroc(ml[fidx], y[fidx]):.4f}")
    say(f"    PAIRED delta SE-length {d:+.4f} [{lo:+.4f}, {hi:+.4f}]"
        f"   {'SIGNIFICANT' if lo > 0 else 'NOT significant'}")
    say()

    say("  Combined detector (equal-weight z-scores), to see whether the two signals")
    say("  are redundant or complementary:")
    for lbl, idx in (("full pool", np.arange(len(qids))), ("fair pool", fidx)):
        comb = zscore(hh[idx]) + zscore(ml[idx])
        say(f"    {lbl:<10}: SE {auroc(hh[idx], y[idx]):.4f}   length "
            f"{auroc(ml[idx], y[idx]):.4f}   SE+length {auroc(comb, y[idx]):.4f}")
    say()
    say(f"  Spearman corr(SE, mean length) = {spearman(hh, ml):+.4f}  "
        f"-- how much the two overlap as signals")
    say()

    # =======================================================================
    say("=" * 78)
    say("H/I. THE ATTACK CELL: is the entropy move accompanied by a LENGTH move?")
    say("=" * 78)
    fa_p = root / "attacks" / args.fa_tag / "triviaqa_se_false_alarm.jsonl"
    if not fa_p.exists():
        say(f"  no attack cell at {fa_p}")
    else:
        rows = read_jsonl(fa_p)
        say(f"  {fa_p.name}: n={len(rows)}")
        say(f"  stored fields: {sorted(rows[0].keys())}")
        say()
        # what sample-bearing fields exist?
        sample_fields = [k for k, v in rows[0].items()
                         if isinstance(v, list) and v and isinstance(v[0], str)]
        say(f"  list-of-string fields (candidate sample arrays): {sample_fields}")
        say()
        if not sample_fields:
            say("  -> The attack cell stores SCORES, not the attacked generations.")
            say("     H CANNOT be answered from cache. Deciding whether the false-alarm")
            say("     entropy move is partly a length move requires re-generating the 10")
            say("     samples under each winning q' -- a GPU job. Cost: 80 targets x ~6.1 s")
            say(f"     = ~{80*6.1/60:.0f} min of generation, plus the same for the hide cell.")
            say("     Under 20 GPU-minutes total. This is the single highest-value")
            say("     measurement the length question implies, and it is cheap.")
        else:
            for f in sample_fields:
                lens_b, lens_a = [], []
                for r in rows:
                    if f in r:
                        lens_a.append(statistics.mean(len(s.split()) for s in r[f]))
                say(f"  field {f}: mean words {statistics.mean(lens_a):.2f}")
        say()
        # what we CAN say from cache: benign length vs benign entropy on these 80
        fa_ids = [r["question_id"] for r in rows if r["question_id"] in smp]
        bl = np.array([statistics.mean(len(s.split()) for s in smp[q]["samples"])
                       for q in fa_ids], float)
        be = np.array([ent[q]["entropy_nats"] for q in fa_ids], float)
        moves = {r["question_id"]: r["entropy_after"] - r["entropy_before"]
                 for r in rows if "entropy_after" in r}
        mv = np.array([moves.get(q, float("nan")) for q in fa_ids], float)
        ok = ~np.isnan(mv)
        say("  What the cache DOES license on the 80 FA targets:")
        say(f"    benign mean length {bl.mean():.2f} words   benign mean H {be.mean():.3f}")
        say(f"    Spearman corr(benign length, benign H) = {spearman(bl, be):+.4f}")
        if ok.sum() > 2:
            say(f"    Spearman corr(benign length, attack entropy MOVE) = "
                f"{spearman(bl[ok], mv[ok]):+.4f}   (n={int(ok.sum())})")
            say("      -- a strong negative would mean the attack mostly wins on targets")
            say("         whose benign generations were SHORT, i.e. had room to lengthen.")
    say()

    if args.out:
        Path(args.out).write_text("\n".join(L) + "\n")
        print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
