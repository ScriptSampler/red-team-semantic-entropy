"""Direct measurement of the winner's curse: re-score the SELECTED attack on FRESH samples.

The whole B2 problem is that the attack reports the MAXIMUM over ~181 noisy entropy
estimates, so the reported move is inflated by selection-on-noise. The classical diagnostic
for exactly this is to re-evaluate the selected item on independent data: if the advantage
was noise, it regresses toward the mean; if it is real, it persists.

This does that, cheaply and without any judge or benign floor. For every completed target we
re-score BOTH the original question and the attack's chosen paraphrase at the SAME N but a
DIFFERENT sampling seed, and compare the fresh move to the selection-time move. The shrinkage
    retention = mean(fresh move) / mean(selection move)
is a direct estimate of how much of the reported effect survives the winner's curse. It does
not replace the benign-floor control (which answers a different question: whether random
paraphrasing achieves the same) but it bounds the selection-on-noise component on its own.

BOTH headline numbers carry an interval computed HERE, from code (see `retention_ci`):
the shrinkage (a difference of means) and the retention (a RATIO of means, which needs a
paired bootstrap plus explicit denominator diagnostics — a ratio is not a mean and a naive
percentile bootstrap of one can be badly behaved).

Verified prerequisite: seeded draws at different seeds are genuinely different samples
(checked explicitly — a 20-sample draw is not a prefix-superset of a 10-sample draw).

    ./.venv-wsl/bin/python scripts/winners_curse_reeval.py --tag _def --cell se_false_alarm

Rebuild the report from an existing checkpoint with no GPU and no model load:

    .venv/Scripts/python.exe scripts/winners_curse_reeval.py --report_only --tag _def
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np                                    # noqa: E402

from se.config import GenConfig, RESULTS_DIR          # noqa: E402
from se.sampling import DEFAULT_SAMPLES_DIR           # noqa: E402

RETENTION_N_BOOT = 10_000
RETENTION_SEED = 0


def retention_point(sel, fresh) -> float:
    """retention = mean(fresh move) / mean(selection move). NaN if the denominator is 0."""
    s = np.asarray(sel, dtype=float)
    f = np.asarray(fresh, dtype=float)
    if s.size == 0:
        return float("nan")
    ms = float(s.mean())
    return float(f.mean() / ms) if ms != 0.0 else float("nan")


def retention_replicates(sel, fresh, *, n_boot: int = RETENTION_N_BOOT,
                         seed: int = RETENTION_SEED):
    """Paired bootstrap replicates of the retention ratio.

    Returns (ratios, numerator_means, denominator_means), one entry per replicate.

    WHY THE RESAMPLE MUST BE PAIRED (this is the whole correctness argument).
    `sel[i]` and `fresh[i]` are the SAME TARGET measured twice — once on the sample the
    attack selected on, once on an independent sample. They are strongly dependent
    (r = +0.46 on the real data): a target whose paraphrase genuinely moves entropy moves
    it in both measurements. So the sampling unit is the TARGET, and a bootstrap replicate
    must draw ONE index vector and apply it to BOTH arrays — `s[idx]` and `f[idx]`, never
    two independent index vectors.

    Resampling the two arms independently would destroy exactly the dependence that makes
    the ratio well determined and would inflate the interval: on the real checkpoint the
    unpaired interval is [0.229, 0.708] against the paired [0.249, 0.650], ~19% wider for
    no reason but a modelling error. In the limit it is starker — if every target satisfied
    fresh = 0.5 * sel exactly, retention is 0.5 with NO uncertainty at all, and only the
    paired resample recovers that (every replicate returns exactly 0.5); the unpaired one
    invents a wide interval out of the between-target spread. `tests/test_winners_curse.py`
    pins that property.

    The per-replicate means are returned alongside because retention is a RATIO OF MEANS,
    not a mean: its bootstrap distribution misbehaves when the denominator can approach
    zero, and the caller needs to see whether that happened before quoting a percentile
    interval.
    """
    s = np.asarray(sel, dtype=float)
    f = np.asarray(fresh, dtype=float)
    n = s.size
    if n == 0:
        return np.empty(0), np.empty(0), np.empty(0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(int(n_boot), n))     # ONE index per replicate, shared
    den = s[idx].mean(axis=1)
    num = f[idx].mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(den != 0.0, num / den, np.nan)
    return r, num, den


def _fieller_interval(sel, fresh, alpha: float = 0.05):
    """Fieller's theorem interval for a ratio of means, plus its instability diagnostic g.

    g = t^2 * Var(mean_sel) / mean_sel^2 is the squared inverse t-statistic of the
    DENOMINATOR. g >= 1 means the denominator is not distinguishable from zero at level
    alpha, and then the ratio's confidence SET is genuinely unbounded (an exclusive region
    or the whole line) — no percentile bootstrap can rescue that, it can only hide it.
    Returns (lo, hi, g); (nan, nan, g) when the set is unbounded or undefined.
    """
    from scipy.stats import t as _t
    s = np.asarray(sel, dtype=float)
    f = np.asarray(fresh, dtype=float)
    n = s.size
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    ms, mf = float(s.mean()), float(f.mean())
    vs = float(s.var(ddof=1)) / n            # variance OF THE MEAN
    vf = float(f.var(ddof=1)) / n
    cov = float(np.cov(f, s, ddof=1)[0, 1]) / n
    tc = float(_t.ppf(1 - alpha / 2, n - 1))
    g = (tc ** 2 * vs / ms ** 2) if ms != 0.0 else float("inf")
    a = ms ** 2 - tc ** 2 * vs
    b = -2.0 * (mf * ms - tc ** 2 * cov)
    c = mf ** 2 - tc ** 2 * vf
    disc = b ** 2 - 4 * a * c
    if a <= 0 or disc <= 0:                  # unbounded / empty set
        return float("nan"), float("nan"), g
    root = disc ** 0.5
    lo, hi = sorted(((-b - root) / (2 * a), (-b + root) / (2 * a)))
    return float(lo), float(hi), float(g)


def retention_ci(sel, fresh, *, n_boot: int = RETENTION_N_BOOT, alpha: float = 0.05,
                 seed: int = RETENTION_SEED) -> dict:
    """Paired percentile-bootstrap CI for retention, WITH the diagnostics that say whether
    a percentile interval on this ratio is trustworthy.

    Three intervals are computed and all three are reported, because a ratio of means is
    not a mean and the honest thing is to show that the answer does not hinge on the
    estimator:
      percentile  — paired percentile bootstrap of mean(fresh)/mean(sel). Primary.
      log-ratio   — paired bootstrap of log(mean fresh) - log(mean sel), exponentiated.
                    Defined only when both means are > 0; the log scale tames the right
                    tail that a small denominator produces.
      Fieller     — the classical exact interval for a ratio of normal means. It is the
                    one method that reports an UNBOUNDED set when the denominator is not
                    significantly non-zero, instead of silently producing a finite one.

    `stable` is False when the ratio bootstrap cannot be trusted: mean(sel) == 0, or
    Fieller's g >= 1, or any material mass of bootstrap replicates has a denominator that
    touches or crosses zero. When `stable` is False the caller must NOT quote the
    percentile interval as the answer.
    """
    s = np.asarray(sel, dtype=float)
    f = np.asarray(fresh, dtype=float)
    n = s.size
    out: dict = {"n": int(n), "n_boot": int(n_boot), "alpha": float(alpha), "seed": int(seed)}
    if n == 0:
        out.update(point=float("nan"), lo=float("nan"), hi=float("nan"),
                   stable=False, warning="no records")
        return out

    ms, mf = float(s.mean()), float(f.mean())
    out["mean_selection"], out["mean_fresh"] = ms, mf
    out["point"] = retention_point(s, f)

    reps, num, den = retention_replicates(s, f, n_boot=n_boot, seed=seed)
    # A denominator "near zero" is measured relative to the observed denominator, not
    # against an absolute epsilon: what breaks the ratio is the mean shrinking toward zero
    # under resampling, and the scale of "small" is set by the estimate itself.
    near_zero = (~np.isfinite(den)) | (np.abs(den) <= 0.1 * abs(ms)) | (np.sign(den) != np.sign(ms))
    out["denom_near_zero_frac"] = float(np.mean(near_zero)) if den.size else float("nan")

    finite = reps[np.isfinite(reps)]
    if finite.size:
        out["lo"] = float(np.quantile(finite, alpha / 2))
        out["hi"] = float(np.quantile(finite, 1 - alpha / 2))
    else:
        out["lo"] = out["hi"] = float("nan")

    if ms > 0 and mf > 0:
        ok = (den > 0) & (num > 0)           # same paired replicates, log scale
        if ok.any():
            lr = np.log(num[ok]) - np.log(den[ok])
            out["log_lo"] = float(np.exp(np.quantile(lr, alpha / 2)))
            out["log_hi"] = float(np.exp(np.quantile(lr, 1 - alpha / 2)))
            out["log_defined_frac"] = float(ok.mean())
    flo, fhi, g = _fieller_interval(s, f, alpha=alpha)
    out["fieller_lo"], out["fieller_hi"], out["fieller_g"] = flo, fhi, g

    reasons = []
    if ms == 0.0:
        reasons.append("mean selection move is exactly 0 — retention is undefined")
    if np.isfinite(g) and g >= 1.0:
        reasons.append(f"Fieller g = {g:.2f} >= 1: the denominator is not significantly "
                       f"different from zero, so the confidence set for the ratio is "
                       f"UNBOUNDED and the percentile interval understates it")
    elif not np.isfinite(g):
        reasons.append("Fieller g is undefined (degenerate denominator)")
    if out["denom_near_zero_frac"] > 1e-3:
        reasons.append(f"{out['denom_near_zero_frac']:.1%} of bootstrap replicates have a "
                       f"denominator at/through zero, so the ratio's bootstrap distribution "
                       f"is heavy-tailed")
    out["stable"] = not reasons
    out["warning"] = "; ".join(reasons)
    return out


def retention_ci_mc_spread(sel, fresh, *, n_seeds: int = 12, n_boot: int = RETENTION_N_BOOT):
    """How much of the reported interval is Monte-Carlo noise from the bootstrap RNG itself.

    A bootstrap interval is quoted from a fixed seed, which makes it REPRODUCIBLE but not
    DETERMINED: the tail quantiles wobble across seeds. Report that wobble so nobody reads
    a digit the resampling does not support. Returns (lo_min, lo_max, hi_min, hi_max).
    """
    los, his = [], []
    for s in range(int(n_seeds)):
        r = retention_ci(sel, fresh, n_boot=n_boot, seed=s)
        if np.isfinite(r.get("lo", float("nan"))):
            los.append(r["lo"])
            his.append(r["hi"])
    if not los:
        return (float("nan"),) * 4
    return min(los), max(los), min(his), max(his)


def summarize(records: list[dict]) -> dict:
    if not records:
        return {"n": 0}
    sel = [r["move_selection"] for r in records]
    fresh = [r["move_fresh"] for r in records]
    pos = sum(1 for m in fresh if m > 0)
    out = {
        "n": len(records),
        "mean_selection": st.mean(sel),
        "mean_fresh": st.mean(fresh),
        "median_selection": st.median(sel),
        "median_fresh": st.median(fresh),
        "retention": (st.mean(fresh) / st.mean(sel)) if st.mean(sel) else float("nan"),
        "kept_positive": pos,
        "kept_positive_rate": pos / len(records),
    }
    out["retention_ci"] = retention_ci(sel, fresh)
    try:
        from se.stats import bootstrap_ci
        d = [f - s for f, s in zip(fresh, sel)]
        ci = bootstrap_ci(d, np.mean)
        out["shrinkage_ci"] = (ci.point, ci.lo, ci.hi)
        out["corr"] = float(np.corrcoef(sel, fresh)[0, 1]) if len(sel) > 2 else float("nan")
    except Exception:
        pass
    return out


def build_report(records: list[dict], cell: str, fresh_seed) -> str:
    """The report text, as a pure function of the records — so it can be rebuilt from a
    checkpoint with `--report_only` and no GPU. Every number here comes from code; nothing
    in this file should ever be hand-edited."""
    s = summarize(records)
    seed_txt = fresh_seed if fresh_seed is not None else "unrecorded"
    L = [f"# Winner's-curse re-evaluation — {cell} (fresh seed {seed_txt})", "",
         "The attack reports the MAXIMUM over ~181 noisy entropy estimates, so its move is "
         "inflated by selection-on-noise. Here the SELECTED paraphrase is re-scored on an "
         "INDEPENDENT sample (same N, different seed). Regression toward the mean measures "
         "the selection component directly; it does not answer whether benign paraphrasing "
         "achieves the same (that is the benign-floor control's job).", ""]
    if s["n"]:
        L += [f"- n = {s['n']}",
              f"- mean move at selection: **{s['mean_selection']:+.3f}** nats -> "
              f"on fresh samples: **{s['mean_fresh']:+.3f}** nats",
              f"- **retention = {s['retention']:.1%}** of the selection-time effect",
              f"- median: {s['median_selection']:+.3f} -> {s['median_fresh']:+.3f}",
              f"- targets keeping a positive move: {s['kept_positive']}/{s['n']} "
              f"({s['kept_positive_rate']:.0%})"]
        if "shrinkage_ci" in s:
            p, lo, hi = s["shrinkage_ci"]
            L.append(f"- shrinkage (fresh - selection): {p:+.3f} [{lo:+.3f}, {hi:+.3f}] nats "
                     f"(a CI excluding 0 means the selection effect is provably inflated)")
        if "corr" in s:
            L.append(f"- corr(selection move, fresh move) = {s['corr']:+.3f}")

        rc = s.get("retention_ci") or {}
        if rc.get("n"):
            L += ["", "## Retention interval (ratio of means — read the estimator note)", "",
                  f"- **retention = {rc['point']:.1%}, paired percentile bootstrap 95% CI "
                  f"[{rc['lo']:.1%}, {rc['hi']:.1%}]** "
                  f"({rc['n_boot']:,} replicates, seed {rc['seed']})"]
            if "log_lo" in rc:
                L.append(f"- log-ratio bootstrap (same paired replicates): "
                         f"[{rc['log_lo']:.1%}, {rc['log_hi']:.1%}]")
            flo = rc.get("fieller_lo")
            if flo is not None and np.isfinite(flo):
                L.append(f"- Fieller's theorem interval: "
                         f"[{rc['fieller_lo']:.1%}, {rc['fieller_hi']:.1%}]")
            else:
                L.append("- Fieller's theorem interval: **UNBOUNDED** — the denominator is "
                         "not significantly different from zero at this level")
            L += [f"- denominator stability: Fieller g = {rc['fieller_g']:.3f} "
                  f"(g >= 1 would make the confidence set unbounded); "
                  f"{rc['denom_near_zero_frac']:.2%} of bootstrap replicates have a "
                  f"denominator at or through zero"]
            lo_lo, lo_hi, hi_lo, hi_hi = retention_ci_mc_spread(
                [r["move_selection"] for r in records], [r["move_fresh"] for r in records])
            if np.isfinite(lo_lo):
                L.append(f"- Monte-Carlo wobble of the endpoints across 12 bootstrap seeds: "
                         f"lower {lo_lo:.1%}–{lo_hi:.1%}, upper {hi_lo:.1%}–{hi_hi:.1%}. Only "
                         f"the whole-percent interval **[{rc['lo']:.0%}, {rc['hi']:.0%}]** is "
                         f"supported by the resampling; the tenths are RNG noise, not data.")
            if rc.get("stable"):
                # Don't ASSERT that the estimators agree — measure it and print the number.
                ends = [(rc["lo"], rc["hi"])]
                if "log_lo" in rc:
                    ends.append((rc["log_lo"], rc["log_hi"]))
                if flo is not None and np.isfinite(flo):
                    ends.append((rc["fieller_lo"], rc["fieller_hi"]))
                spread = max(max(e[k] for e in ends) - min(e[k] for e in ends)
                             for k in (0, 1))
                L += ["", f"The {len(ends)} estimators agree to within {spread:.1%} on the "
                      "worst endpoint, the denominator (mean selection-time move) is bounded "
                      "well away from zero, and no bootstrap replicate approaches a zero "
                      "denominator — so the percentile interval is the one to quote. "
                      "Resampling is PAIRED over targets: each target's selection-time and "
                      "fresh moves are the same target measured twice and must move together."]
            else:
                L += ["", f"⚠ **THE RATIO BOOTSTRAP IS NOT TRUSTWORTHY HERE**: {rc['warning']}. "
                      "Do not quote the percentile interval as the answer; report the Fieller "
                      "set (which is honest about being unbounded) and the shrinkage CI, which "
                      "is a difference of means and is unaffected by a small denominator."]
        L += ["", "READING: retention near 1.0 means the selected paraphrase's advantage is a "
              "property of the paraphrase, not of the sample it was selected on. Retention "
              "near 0 means the reported effect was largely selection-on-noise — which the "
              "benign floor would then also show.", "",
              "Note the asymmetry in what these two intervals establish. THAT there is "
              "inflation is settled by the shrinkage CI (a difference of means) and its "
              "relation to zero. HOW MUCH survives is the retention interval above, and it "
              "is wide. Quote retention with its interval, never bare.", "",
              f"Generated by `scripts/winners_curse_reeval.py` from "
              f"`results/winners_curse_ckpt_{cell}*.jsonl`. Do not hand-edit."]
    return "\n".join(L) + "\n"


def load_checkpoint(ck: Path | None) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if ck is None or not ck.exists():
        return done
    for line in ck.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            done[r["question_id"]] = r
        except Exception:
            continue
    return done


def seed_provenance(done: dict[str, dict], fresh_seed: int) -> tuple[str | None, str, object]:
    """Guard against the checkpoint/seed collision. Returns (error, warning, headline_seed).

    THE DEFECT THIS CLOSES. The checkpoint path is
    `winners_curse_ckpt_{cell}{tag}.jsonl` — `--fresh_seed` is NOT in the filename, but it IS
    in the report headline. So re-running at a different seed found every `question_id`
    already present, skipped ALL re-scoring, and re-published the OLD seed's numbers under
    the NEW seed's headline: a different-looking result that is byte-identical evidence.

    Records now carry `fresh_seed`, so a genuine mismatch is a hard error. Records written
    before stamping carry none; those are not rejected (that would strand the committed
    n=60 checkpoint) but the headline says out loud that the seed is ASSERTED by the flag
    rather than read from the data, which is the honest label for what is known.
    """
    known = {r.get("fresh_seed") for r in done.values()} - {None}
    n_unstamped = sum(1 for r in done.values() if r.get("fresh_seed") is None)
    if known and known != {fresh_seed}:
        return (f"checkpoint holds records from fresh seed(s) {sorted(known)} but "
                f"--fresh_seed is {fresh_seed}. The checkpoint path does not encode the "
                f"seed, so continuing would mix seeds and label the result with the wrong "
                f"one. Pass an explicit --checkpoint for this seed.", "", fresh_seed)
    if not n_unstamped:
        return None, "", fresh_seed
    warn = (f"{n_unstamped} checkpoint records predate seed stamping; the headline seed is "
            f"asserted by --fresh_seed ({fresh_seed}), not read from the data.")
    headline = (f"{fresh_seed} — asserted by --fresh_seed; {n_unstamped} of {len(done)} "
                f"checkpoint records predate seed stamping")
    return None, warn, headline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="_def")
    ap.add_argument("--cell", default="se_false_alarm")
    ap.add_argument("--fresh_seed", type=int, default=1, help="a DIFFERENT seed from the run's 0")
    ap.add_argument("--n_targets", type=int, default=0, help="0 = all")
    ap.add_argument("--checkpoint", default="auto")
    ap.add_argument("--report_only", action="store_true",
                    help="rebuild the report from the existing checkpoint; no GPU, no model "
                         "load, no new scoring")
    args = ap.parse_args()

    ck = (RESULTS_DIR / f"winners_curse_ckpt_{args.cell}{args.tag}.jsonl"
          if args.checkpoint == "auto" else (Path(args.checkpoint) if args.checkpoint else None))
    done = load_checkpoint(ck)

    err, warn, seed_txt = seed_provenance(done, args.fresh_seed)
    if err:
        print(f"[wc] ERROR: {ck}: {err}", file=sys.stderr, flush=True)
        return 2
    if warn:
        print(f"[wc] WARNING: {warn}", flush=True)

    if args.report_only:
        records = list(done.values())
        if not records:
            print(f"[wc] ERROR: --report_only but no records in {ck}", file=sys.stderr)
            return 1
        print(f"[wc] report-only: {len(records)} records from {ck}", flush=True)
    else:
        from se.attacks.harness import load_pair, read_outcomes
        from se.se_pipeline import semantic_entropy

        campaign = DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}"
        outs = read_outcomes(campaign / f"triviaqa_{args.cell}.jsonl")
        outs.sort(key=lambda o: o.question_id)
        if args.n_targets:
            outs = outs[: args.n_targets]

        pair = load_pair()
        gen = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=args.fresh_seed)
        print(f"[wc] {len(outs)} targets in {args.cell}; fresh seed {args.fresh_seed}; "
              f"{len(done)} already done", flush=True)

        records = list(done.values())
        for o in outs:
            if o.question_id in done:
                continue
            if o.best_query == o.question:      # optimiser found nothing; no selection to re-test
                continue
            before = semantic_entropy(o.question, pair.lm, pair.nli, gen).entropy_nats
            after = semantic_entropy(o.best_query, pair.lm, pair.nli, gen).entropy_nats
            sign = -1.0 if o.attack == "hide" else 1.0
            rec = {
                "question_id": o.question_id, "attack": o.attack,
                "fresh_seed": args.fresh_seed,
                "before_selection": o.entropy_before, "after_selection": o.entropy_after,
                "move_selection": sign * (o.entropy_after - o.entropy_before),
                "before_fresh": before, "after_fresh": after,
                "move_fresh": sign * (after - before),
            }
            records.append(rec)
            if ck is not None:
                ck.parent.mkdir(parents=True, exist_ok=True)
                with ck.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, default=float) + "\n")
                    f.flush()
            print(f"  {o.question_id}: selection {rec['move_selection']:+.3f} -> "
                  f"fresh {rec['move_fresh']:+.3f}", flush=True)

    out = RESULTS_DIR / f"winners_curse_{args.cell}.md"
    # newline="\n" explicitly: this report is normally regenerated from WSL but --report_only
    # runs from the Windows venv, and default newline translation would rewrite every line of
    # a committed artifact as a phantom diff.
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(build_report(records, args.cell, seed_txt))
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
