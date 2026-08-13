"""Defense evaluation: does input-paraphrase-averaging blunt the attacks?

THE ESTIMAND. `src/se/defense.py` scores an input by aggregating semantic
entropy over the input plus K NLI-equivalent paraphrases of it. The question
this script must answer is whether THE PARAPHRASING buys robustness. That is
not the same question as whether the defended NUMBER is smaller, and the gap
between those two questions has now eaten two versions of this experiment.

ROUND 0 (confounded). Two arms:

    vanilla effect  = | SE(Q') - SE(Q) |               (cached, selection-time)
    defended effect = | defended(Q') - defended(Q) |   (fresh, unseeded, d-averaged)

reported as `1 - defended/vanilla`. Q' was chosen as the argmax over ~181 noisy
entropy estimates, so a fresh re-draw alone regresses it toward the mean. This
project has MEASURED that: results/winners_curse_se_false_alarm.md finds only
45.2% (95% CI [25%, 65%]) of the selection-time move survives a re-score at the
same N on a different seed, with NO defense of any kind. Round 0 would have
booked that ~55% as a defense success.

ROUND 1 (still confounded, one level down). A d=1 fresh-redraw control (arm B)
was added, and the header claimed B "pays exactly the re-sampling cost of the
defended arm" and that B and C "differ only in whether the score is averaged
over paraphrases". Both claims were false by this file's own cost model: arm C
buys ~3.7 SE evaluations per side and arm B bought one. The outcome statistic is
abs(after - before), and for X = effect + noise, E|X| is STRICTLY INCREASING in
the noise of X. So the arm that averages more evaluations posts a smaller
number with no defense effect whatsoever.

Quantified on this project's own data (`--null-sim`, reproducible with no GPU).
The 60 paired baselines in results/winners_curse_ckpt_se_false_alarm_def.jsonl
give a per-estimate sigma of 0.34 nats. Simulating the STRICT NULL -- every
paraphrase carries exactly the true entropy of its input, true effects set to
the empirical fresh moves, median aggregate:

    arm B  (m=1)          E|.| = 0.6575   (closed form, no Monte-Carlo error)
    arm C  (median of 3)  E|.| = 0.5834   -> apparent "defense" 11.3%
    arm C  (median of 4)  E|.| = 0.5599   -> apparent "defense" 14.8%

The audit that raised this reported 0.6595 / 0.5829 / 0.5598 and 11.6% / 15.1%.
The m>1 rows agree to the fourth decimal; the m=1 row differs by 0.002, which
is the audit's Monte-Carlo error on a baseline that has a closed form (its
value corresponds to sigma = 0.3427 against the checkpoint's 0.3395). The
finding reproduces; `tests/test_wk_defense.py` pins it against the real file.

Double-digit "defense" from variance reduction alone. Note that
`src/se/defense.py:168-171` states this mechanism outright as the defense's own
premise -- "averaging SE over paraphrases cancels independent sampling noise".
That is the ALTERNATIVE HYPOTHESIS, not the claim: plain repetition cancels
independent sampling noise too, and it needs no paraphraser, no equivalence
gate and no semantic argument.

ROUND 2 (this version). Four arms. The new one is B', the NOISE-MATCHED
control: the aggregate of m INDEPENDENT RE-DRAWS OF THE IDENTICAL INPUT, same
aggregation rule and the same m as the defended call actually used on that
target and that side.

    A. cached    | SE(Q') - SE(Q) |                          selection-time, seeded
    B. control   | SE_1(Q') - SE_1(Q) |                       one fresh draw per side
    B'. noise    | agg_m(SE(Q')) - agg_m(SE(Q)) |             m fresh draws, SAME input
    C. defended  | defended_m(Q') - defended_m(Q) |           m fresh draws, PARAPHRASES

  C vs B'  THE DEFENSE. Both arms aggregate the same number of independent SE
           evaluations of a semantically equivalent input set, with the same
           rule. They differ in one thing: whether the extra evaluations are of
           PARAPHRASES of the input or of the input itself. Any difference is
           attributable to paraphrase dilution, because noise-averaging is held
           fixed. This is what C vs B cannot license.
  B' vs B  THE ARTEFACT, measured rather than assumed: how much apparent
           reduction pure noise-averaging delivers on this data. Under the
           strict null this is exactly what C vs B would have reported.
  B  vs A  the winner's curse, as a cross-check on a known quantity.
  C  vs B  the ROUND-1 comparison, still printed, labelled confounded. It is
           approximately (artefact) compounded with (defense) and must not be
           quoted alone.

WHAT CAN STILL GO WRONG, stated so it cannot be quietly rediscovered:
  - If the equivalence gate rejects every paraphrase, C degenerates to vanilla
    SE, m = 1, and B' degenerates with it -- so C vs B' correctly reports zero
    rather than a spurious reduction. The degenerate fraction is reported.
  - B' shares its first draw with arm C's own original-input variant, and arm B
    IS that shared draw. This is common random numbers on a paired contrast: it
    leaves every arm's marginal distribution exactly as specified, makes the
    strict null EXACT (under it C and B' are identically distributed), tightens
    the paired interval, and saves 2 SE evaluations per outcome.
  - The defense is measured against paraphrases the attacker found WITHOUT
    knowing a defense was deployed. Upper bound; see "Scope" in the report.

Requires GPU. Print the cost first, then schedule it. The cost table reads the
CURRENT campaign and prints the n it used -- no GPU-hour figure is quoted
anywhere in this docstring, deliberately, because the cells grow:

    python scripts/wk_defense.py --estimate-only
    python scripts/wk_defense.py --null-sim --estimate-only      # no GPU, no model
    python scripts/wk_defense.py --synthetic --out /tmp/x.md     # no GPU, no model
    python scripts/wk_defense.py --tag _defb
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR, GenConfig, ModelConfig
from se.defense import AGGREGATES, aggregate_entropy, defended_entropy
from se.se_pipeline import semantic_entropy
from se.stats import bootstrap_ci


ATTACKS = ("hide", "false_alarm")

# Checkpoint schema. Round-1 records (fresh_before/fresh_after scalars, no
# redraws) cannot be re-analysed under the round-2 design -- arm B' needs the
# individual draws -- so a version mismatch is a hard error, not a silent skip.
SCHEMA_VERSION = 2

N_BOOT = 10_000
BOOT_SEED = 0

FALSIFIABLE_CLAIM = (
    "PREDICTION UNDER TEST (arm C against arm B'): averaging the detector score "
    "over d NLI-equivalent PARAPHRASES of its input reduces the attack's "
    "surviving entropy move by more than aggregating THE SAME NUMBER of "
    "independent re-draws of the IDENTICAL input does. ESTIMAND: the mean over "
    "targets of the paired difference delta_i = |B'_i| - |C_i| in nats, where "
    "|B'_i| and |C_i| are that target's absolute entropy moves under the two "
    "arms. Both arms aggregate the same number of independent SE evaluations "
    "with the same rule, so neither is handed a smaller E|.| by carrying less "
    "noise than the other. REJECTION REGION: the claim is FALSE unless the 95% "
    "CI for mean(delta) lies entirely above 0. A CI covering 0 means "
    "paraphrasing adds nothing to plain noise-averaging, and the defense is a "
    "variance reduction with a semantic story attached."
)

# ---- measured per-call costs (this repo, RX 9070 XT, Llama-3.1-8B nf4) -------
# SE sampling, N=10 @ 48 new tokens, batched via num_return_sequences:
#   12.4 s/Q for greedy + 10 samples (results/run_all.log, n=1907)
#   1.49 s/Q for the greedy answer alone (results/pipeline_check.md)
#   -> 10-sample draw ~ 10.9 s
# NLI clustering of 10 samples (C(10,2)=45 pairs): 1.84 s/Q
#   (results/wk3_fri_entropy.md, "clustered 50 questions in 92.2s")
SEC_PER_SE_EVAL = 10.9 + 1.84       # one semantic_entropy() call
SEC_PER_PROPOSE = 1.49 * (64 / 48)  # one greedy 64-token paraphrase
SEC_PER_GATE = 0.15                 # one unbatched bidirectional NLI check
SEC_MODEL_LOAD = 180.0
# Empirical bidirectional-NLI equivalence pass rate on proposer output, from the
# definitive campaigns' own gate counters (n_feasibility_passed/n_feasibility_checks):
#   wk9_defb hide 0.692, wk9_defb false_alarm 0.650, wk9_def hide 0.641.
# feasibility.check also applies no-op and length filters that the defense does
# not, so this is a LOWER bound on the defense's keep rate.
GATE_PASS_RATE = 0.67


def variants_per_call(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Expected aggregate size m: the input itself plus the paraphrases that
    survive the equivalence gate. Arm B' is sized to match this exactly, per
    target and per side, using the count the defended call actually produced."""
    return 1.0 + k * gate_rate


def sec_per_defended_call(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Arm C, one side: k paraphrase generations, k gate checks, m SE evals."""
    return (k * SEC_PER_PROPOSE + k * SEC_PER_GATE
            + variants_per_call(k, gate_rate) * SEC_PER_SE_EVAL)


def sec_per_noise_control(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Arm B', one side. Only m-1 EXTRA evaluations: the m-th is arm C's own
    original-input variant, reused. Arm B is that same shared draw and is free."""
    return (variants_per_call(k, gate_rate) - 1.0) * SEC_PER_SE_EVAL


def sec_per_outcome(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Both sides (Q and Q') of all four arms. A is cached and costs nothing."""
    return 2 * (sec_per_defended_call(k, gate_rate) + sec_per_noise_control(k, gate_rate))


def sec_per_outcome_round0(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Historical: the confounded two-arm version (A cached, C defended)."""
    return 2 * sec_per_defended_call(k, gate_rate)


def sec_per_outcome_round1(k: int, gate_rate: float = GATE_PASS_RATE) -> float:
    """Historical: three arms, with the un-matched d=1 control."""
    return 2 * sec_per_defended_call(k, gate_rate) + 2 * SEC_PER_SE_EVAL


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------

@dataclass
class DefenseRecord:
    """One target, all four arms, both sides.

    `redraws_*` holds the m independent identical-input SE evaluations, with
    element 0 being the score arm C's aggregate used for the original input.
    Arm B is redraws[0]; arm B' is the aggregate of the whole list. Storing the
    draws rather than the two summaries means the aggregation rule can be
    changed in analysis without re-running the GPU (and means a schema mismatch
    is detectable, which round-1 records are not).
    """
    attack: str
    question_id: str
    aggregate: str
    k_requested: int
    cached_before: float
    cached_after: float
    redraws_before: list[float]
    redraws_after: list[float]
    defended_before: float
    defended_after: float
    d_before: int          # paraphrases that actually entered arm C's aggregate, Q side
    d_after: int           # ... Q' side
    rejected_gate_before: int = 0
    rejected_gate_after: int = 0
    schema: int = SCHEMA_VERSION

    # -- arm scores ---------------------------------------------------------
    @property
    def sign(self) -> float:
        """The attack's intended direction: Hide drives entropy DOWN."""
        return -1.0 if self.attack == "hide" else 1.0

    @property
    def m_before(self) -> int:
        return len(self.redraws_before)

    @property
    def m_after(self) -> int:
        return len(self.redraws_after)

    @property
    def fresh_before(self) -> float:
        return float(self.redraws_before[0])

    @property
    def fresh_after(self) -> float:
        return float(self.redraws_after[0])

    @property
    def noise_before(self) -> float:
        return aggregate_entropy(self.redraws_before, self.aggregate)

    @property
    def noise_after(self) -> float:
        return aggregate_entropy(self.redraws_after, self.aggregate)

    # -- outcome statistics -------------------------------------------------
    @property
    def effect_cached(self) -> float:
        return abs(self.cached_after - self.cached_before)

    @property
    def effect_control(self) -> float:
        return abs(self.fresh_after - self.fresh_before)

    @property
    def effect_noise(self) -> float:
        return abs(self.noise_after - self.noise_before)

    @property
    def effect_defended(self) -> float:
        return abs(self.defended_after - self.defended_before)

    # -- SIGNED moves, for the winner's-curse cross-check only ---------------
    # winners_curse_reeval.py's retention is a ratio of SIGNED means; comparing
    # an absolute-move ratio against it is a category error (see cross_check()).
    @property
    def move_cached(self) -> float:
        return self.sign * (self.cached_after - self.cached_before)

    @property
    def move_control(self) -> float:
        return self.sign * (self.fresh_after - self.fresh_before)


class CheckpointMismatch(RuntimeError):
    """The checkpoint on disk was written under settings that make it unusable
    for the requested analysis. Loud, because the round-1 failure mode was
    exactly a silent `except: continue` over records that no longer meant what
    the reader thought."""


def _ckpt_load(path: Path, *, aggregate: str | None = None,
               k: int | None = None) -> dict[str, DefenseRecord]:
    """Read the checkpoint, refusing to mix incompatible records.

    Round-1 and earlier records carry no `schema` field and no `redraws_*`, so
    arm B' cannot be reconstructed from them: they are rejected by name rather
    than skipped. A checkpoint written at a different --aggregate or --k is
    also rejected -- both are baked into `defended_*`, so continuing would
    average two different experiments into one table.
    """
    out: dict[str, DefenseRecord] = {}
    if not path.exists():
        return out
    bad: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except Exception:
            bad.append(f"line {i}: not JSON")
            continue
        if int(raw.get("schema", 1)) != SCHEMA_VERSION:
            bad.append(f"line {i}: schema {raw.get('schema', 1)} "
                       f"(this script writes and reads {SCHEMA_VERSION})")
            continue
        try:
            rec = DefenseRecord(**raw)
        except Exception as exc:
            bad.append(f"line {i}: {type(exc).__name__}: {exc}")
            continue
        if not rec.redraws_before or not rec.redraws_after:
            bad.append(f"line {i}: empty redraws, arm B' is not reconstructible")
            continue
        out[f"{rec.attack}::{rec.question_id}"] = rec
    if bad:
        raise CheckpointMismatch(
            f"{path}: {len(bad)} unusable record(s); the first few are:\n  "
            + "\n  ".join(bad[:5])
            + "\nDelete the checkpoint or pass --checkpoint <new path>. Records "
              "written before schema 2 lack the per-draw scores arm B' needs.")
    if aggregate is not None:
        aggs = {r.aggregate for r in out.values()}
        if aggs - {aggregate}:
            raise CheckpointMismatch(
                f"{path}: holds records aggregated with {sorted(aggs)} but "
                f"--aggregate is {aggregate!r}. The aggregation rule is baked "
                f"into defended_before/after; continuing would mix experiments.")
    if k is not None:
        ks = {r.k_requested for r in out.values()}
        if ks - {k}:
            raise CheckpointMismatch(
                f"{path}: holds records at k={sorted(ks)} but --k is {k}. "
                f"Pass an explicit --checkpoint for this k.")
    return out


# ---------------------------------------------------------------------------
# estimators
# ---------------------------------------------------------------------------

@dataclass
class PairedReduction:
    """Per-question 1 - num/den, WITH the accounting for what was dropped.

    The drop is on the DENOMINATOR, which is the control arm's effect -- so the
    dropped targets are exactly those where the control already left nothing to
    reduce. Conditioning on that is a selection effect ON THE OUTCOME: it
    removes the targets least able to show a reduction and inflates the mean of
    what remains. Which is why nothing headline is computed from this. It is
    reported descriptively, with `n_dropped` and the mean numerator among the
    dropped targets, so the reader can see whether the drop was benign (both
    arms ~0) or not (numerator large, denominator ~0 -> reduction hugely
    negative, and silently deleted).
    """
    values: list[float]
    n_total: int
    n_dropped: int
    dropped_num_mean: float

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def median(self) -> float:
        return statistics.median(self.values) if self.values else float("nan")

    @property
    def mean(self) -> float:
        return statistics.mean(self.values) if self.values else float("nan")


def _paired_reduction(num, den, eps: float = 1e-9) -> PairedReduction:
    """Per-question 1 - num/den. See PairedReduction for why the drops matter."""
    vals: list[float] = []
    dropped_nums: list[float] = []
    for n_i, d_i in zip(num, den):
        if d_i > eps:
            vals.append(1.0 - n_i / d_i)
        else:
            dropped_nums.append(float(n_i))
    return PairedReduction(
        values=vals,
        n_total=len(vals) + len(dropped_nums),
        n_dropped=len(dropped_nums),
        dropped_num_mean=(statistics.mean(dropped_nums) if dropped_nums else float("nan")),
    )


def _ratio_reduction_ci(num, den, n_boot: int = N_BOOT,
                        seed: int = BOOT_SEED) -> tuple[float, float, float, float]:
    """Paired percentile bootstrap on 1 - mean(num)/mean(den).

    Paired over questions: each question contributes its (num, den) jointly,
    because they are the same target measured under two arms. Returns
    (point, lo, hi, denominator_z) where denominator_z is the mean denominator
    in units of its own standard error -- if it is small the ratio is badly
    conditioned and the interval must not be quoted (see the estimator note in
    results/winners_curse_se_false_alarm.md). A denominator with zero spread is
    perfectly conditioned, not badly conditioned, and reports z = inf.

    This is a SECONDARY statistic here. The headline is the paired difference
    (`_paired_diff_ci`), which is a mean and needs no denominator at all.
    """
    a, b = np.asarray(num, dtype=float), np.asarray(den, dtype=float)
    n = a.size
    if n < 2 or not np.isfinite(a).all() or not np.isfinite(b).all() or b.mean() <= 1e-9:
        return float("nan"), float("nan"), float("nan"), 0.0
    point = 1.0 - a.mean() / b.mean()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    with np.errstate(divide="ignore", invalid="ignore"):
        reps = 1.0 - a[idx].mean(axis=1) / b[idx].mean(axis=1)
    finite = reps[np.isfinite(reps)]
    if finite.size == 0:
        return float(point), float("nan"), float("nan"), 0.0
    lo, hi = np.percentile(finite, [2.5, 97.5])
    se = b.std(ddof=1) / np.sqrt(n)
    z = float(b.mean() / se) if se > 0 else float("inf")
    return float(point), float(lo), float(hi), z


def _paired_diff_ci(num, den, n_boot: int = N_BOOT,
                    seed: int = BOOT_SEED) -> tuple[float, float, float]:
    """Bootstrap CI for mean(den - num), the PRIMARY estimand, in nats.

    The unit of resampling is the target, and the statistic is a mean of the
    per-target paired differences -- so an i.i.d. resample of the difference
    vector IS the paired bootstrap. No denominator, so no conditioning problem,
    no dropped targets, and a sign that means what the claim says it means:
    positive = the defended arm moved less than the control arm.
    """
    d = np.asarray(den, dtype=float) - np.asarray(num, dtype=float)
    if d.size < 2 or not np.isfinite(d).all():
        return float("nan"), float("nan"), float("nan")
    ci = bootstrap_ci(d, np.mean, n_boot=n_boot, seed=seed)
    return float(ci.point), float(ci.lo), float(ci.hi)


@dataclass
class ArmComparison:
    """`num` is the arm under test, `den` the control it must beat."""
    label: str
    n: int
    mean_num: float
    mean_den: float
    diff: float                 # mean(den - num), nats -- PRIMARY
    diff_lo: float
    diff_hi: float
    ratio: float                # 1 - mean(num)/mean(den) -- secondary
    ratio_lo: float
    ratio_hi: float
    denom_z: float
    per_q: PairedReduction      # descriptive only

    @property
    def computable(self) -> bool:
        return self.n >= 2 and math.isfinite(self.diff_lo) and math.isfinite(self.diff_hi)

    @property
    def verdict(self) -> str:
        """SURVIVES / FAILED / NOT COMPUTABLE. A NaN interval is NOT a failure:
        it is an absence of evidence, and printing 'the prediction FAILED' on
        one (the round-1 behaviour, since NaN > 0 is False) manufactures a
        result out of missing data."""
        if not self.computable:
            return "NOT COMPUTABLE"
        return "SURVIVES" if self.diff_lo > 0 else "FAILED"


def compare_arms(num, den, label: str, *, n_boot: int = N_BOOT,
                 seed: int = BOOT_SEED) -> ArmComparison:
    num = [float(x) for x in num]
    den = [float(x) for x in den]
    d_pt, d_lo, d_hi = _paired_diff_ci(num, den, n_boot=n_boot, seed=seed)
    r_pt, r_lo, r_hi, dz = _ratio_reduction_ci(num, den, n_boot=n_boot, seed=seed)
    return ArmComparison(
        label=label,
        n=len(num),
        mean_num=statistics.mean(num) if num else float("nan"),
        mean_den=statistics.mean(den) if den else float("nan"),
        diff=d_pt, diff_lo=d_lo, diff_hi=d_hi,
        ratio=r_pt, ratio_lo=r_lo, ratio_hi=r_hi,
        denom_z=dz,
        per_q=_paired_reduction(num, den),
    )


def format_comparison(c: ArmComparison, *, indent: str = "") -> list[str]:
    L = [f"{indent}- paired difference mean(|{c.label.split(' vs ')[1]}|) - "
         f"mean(|{c.label.split(' vs ')[0]}|) = {c.diff:+.4f} nats "
         f"[{c.diff_lo:+.4f}, {c.diff_hi:+.4f}]  <- the estimand",
         f"{indent}- ratio of means: reduction {c.ratio*100:.1f}% "
         f"[{c.ratio_lo*100:.1f}%, {c.ratio_hi*100:.1f}%] "
         f"(denominator {c.denom_z:.1f} SE from zero)"]
    pq = c.per_q
    if pq.n:
        L.append(f"{indent}- per-question reduction (descriptive, see note): "
                 f"median {pq.median*100:.1f}%, mean {pq.mean*100:.1f}% "
                 f"(n={pq.n} of {pq.n_total})")
    else:
        L.append(f"{indent}- per-question reduction: undefined for all "
                 f"{pq.n_total} targets (every control effect ~ 0)")
    if pq.n_dropped:
        L.append(f"{indent}  DROPPED {pq.n_dropped}/{pq.n_total} targets with a ~zero "
                 f"control effect; their mean numerator is {pq.dropped_num_mean:.4f} "
                 f"nats. This drop is a selection effect ON THE OUTCOME (it removes "
                 f"the targets where re-sampling already killed the effect), which is "
                 f"why the headline is the paired difference above and not this.")
    return L


# ---------------------------------------------------------------------------
# the winner's-curse cross-check reference, computed live
# ---------------------------------------------------------------------------

@dataclass
class WinnersCurseReference:
    """Read from the winner's-curse checkpoint at run time. NOTHING here is a
    hardcoded constant: the round-1 version compared its own ABSOLUTE-move ratio
    against the published 45.2%, which is a ratio of SIGNED means, so the check
    was guaranteed to read as a contradiction on a CORRECT run."""
    path: Path
    n: int
    signed_retention: float
    absolute_retention: float
    n_sign_flips: int
    sigma: float
    effects: list[float] = field(default_factory=list)


def wc_checkpoint_path(attack: str, tag: str = "_def") -> Path:
    return RESULTS_DIR / f"winners_curse_ckpt_se_{attack}{tag}.jsonl"


def load_wc_reference(path: Path) -> WinnersCurseReference | None:
    """Recompute both functionals from the checkpoint winners_curse_reeval wrote."""
    if not path.exists():
        return None
    recs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    if not recs:
        return None
    sel = np.array([r["move_selection"] for r in recs], dtype=float)
    fresh = np.array([r["move_fresh"] for r in recs], dtype=float)
    return WinnersCurseReference(
        path=path,
        n=len(recs),
        signed_retention=float(fresh.mean() / sel.mean()) if sel.mean() else float("nan"),
        absolute_retention=(float(np.abs(fresh).mean() / np.abs(sel).mean())
                            if np.abs(sel).mean() else float("nan")),
        n_sign_flips=int((fresh < 0).sum()),
        sigma=per_estimate_sigma(recs),
        effects=[float(x) for x in fresh],
    )


def per_estimate_sigma(wc_records) -> float:
    """Per-estimate SE noise sigma, in nats, from paired independent re-scores.

    Uses the BEFORE side only. `before_selection` and `before_fresh` are two
    independent estimates of the same quantity, SE(Q), neither of them selected
    -- so their difference has variance 2*sigma^2. The AFTER side is not usable
    for this: `after_selection` is the argmax over ~181 draws, so its deviation
    from a fresh re-score is selection bias plus noise, not noise.
    """
    d = np.array([r["before_fresh"] - r["before_selection"] for r in wc_records],
                 dtype=float)
    if d.size < 2:
        return float("nan")
    return float(d.std(ddof=1) / math.sqrt(2.0))


# ---------------------------------------------------------------------------
# strict-null calibration: how much "defense" does noise-averaging alone buy?
# ---------------------------------------------------------------------------

def _agg_axis(z: np.ndarray, aggregate: str) -> np.ndarray:
    if aggregate == "median":
        return np.median(z, axis=-1)
    if aggregate == "mean":
        return z.mean(axis=-1)
    if aggregate == "min":
        return z.min(axis=-1)
    raise ValueError(f"unknown aggregate: {aggregate}")


def expected_abs_normal(mu, sigma: float) -> float:
    """E|X| for X ~ N(mu, sigma^2), averaged over the vector mu. Closed form, so
    the m=1 arm of the null simulation carries no Monte-Carlo error at all."""
    mu = np.asarray(mu, dtype=float)
    if sigma <= 0:
        return float(np.abs(mu).mean())
    t = mu / (sigma * math.sqrt(2.0))
    erf = np.vectorize(math.erf)(t)
    return float((sigma * math.sqrt(2.0 / math.pi) * np.exp(-(mu ** 2) / (2 * sigma ** 2))
                  + mu * erf).mean())


def null_expected_abs_move(effects, sigma: float, m: int, aggregate: str = "median",
                           n_reps: int = 20_000, seed: int = BOOT_SEED,
                           block: int = 2_000) -> float:
    """E|agg_m(after) - agg_m(before)| under the STRICT NULL.

    Strict null: every paraphrase carries exactly the true entropy of its input,
    so aggregating over m paraphrases is distributionally identical to
    aggregating over m re-draws of the input. The only thing m changes is how
    much estimation noise survives. `effects` are the true per-target moves,
    taken from the empirical fresh moves; each side of each target gets its own
    independent aggregate of m N(0, sigma^2) draws.

    m = 1 is exact (closed form). m > 1 is Monte Carlo, blocked to bound memory.
    """
    e = np.asarray(effects, dtype=float)
    if e.size == 0 or not math.isfinite(sigma):
        return float("nan")
    if m <= 1:
        return expected_abs_normal(e, sigma * math.sqrt(2.0))
    rng = np.random.default_rng(seed)
    total, done = 0.0, 0
    while done < n_reps:
        r = min(block, n_reps - done)
        za = _agg_axis(rng.standard_normal((r, e.size, m)), aggregate) * sigma
        zb = _agg_axis(rng.standard_normal((r, e.size, m)), aggregate) * sigma
        total += float(np.abs(e[None, :] + za - zb).sum())
        done += r
    return total / (done * e.size)


def null_calibration(effects, sigma: float, ms=(1, 2, 3, 4, 5),
                     aggregate: str = "median", n_reps: int = 20_000,
                     seed: int = BOOT_SEED) -> dict[int, dict[str, float]]:
    """{m: {'e_abs': E|.|, 'apparent_reduction': 1 - E_m/E_1}} under the strict null."""
    base = null_expected_abs_move(effects, sigma, 1, aggregate, n_reps, seed)
    out: dict[int, dict[str, float]] = {}
    for m in ms:
        v = null_expected_abs_move(effects, sigma, int(m), aggregate, n_reps, seed + m)
        out[int(m)] = {
            "e_abs": v,
            "apparent_reduction": (1.0 - v / base) if base else float("nan"),
        }
    return out


def null_sim_lines(ref: WinnersCurseReference, aggregate: str, k: int,
                   n_reps: int = 20_000) -> list[str]:
    ms = sorted({1, 2, 3, 4, max(2, int(round(variants_per_call(k))))})
    cal = null_calibration(ref.effects, ref.sigma, ms=ms, aggregate=aggregate,
                           n_reps=n_reps)
    L = ["### Strict-null calibration (no GPU; this is why arm B' exists)", "",
         f"Per-estimate sigma = {ref.sigma:.3f} nats, from the {ref.n} paired "
         f"independent re-scores in `{ref.path.name}` "
         f"(sd of before_fresh - before_selection, / sqrt 2).",
         f"True per-target effects = that checkpoint's empirical fresh moves. "
         f"Aggregate = {aggregate}. Under the STRICT NULL a paraphrase carries "
         f"exactly the true entropy of its input, so the defense does NOTHING and "
         f"any reduction below is pure variance reduction:", "",
         "| m evaluations aggregated | E abs. move (nats) | apparent 'defense' vs m=1 |",
         "|---|---|---|"]
    for m in ms:
        c = cal[m]
        red = "--" if m == 1 else f"{c['apparent_reduction']*100:.1f}%"
        L.append(f"| {m} | {c['e_abs']:.4f} | {red} |")
    L += ["",
          f"A C-vs-B comparison (m={int(round(variants_per_call(k)))} against m=1) "
          f"would therefore report a double-digit 'defense' with no defense present. "
          f"Arm B' removes this by aggregating the same m; the MEASURED size of the "
          f"artefact on the real run is the B' vs B row in each cell below, and it "
          f"should land near this table.", ""]
    return L


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------

def cross_check_lines(recs: list[DefenseRecord], ref: WinnersCurseReference | None,
                      attack: str, *, unavailable_reason: str | None = None) -> list[str]:
    """A vs B against the independently measured winner's curse -- using the
    SAME FUNCTIONAL the reference is defined with.

    THE ROUND-1 BUG. The reference retention (45.2%) is a ratio of SIGNED means:
    winners_curse_reeval computes move = sign * (after - before) and divides
    mean(fresh) by mean(selection). The round-1 cross-check printed
    1 - mean|B|/mean|A|, an ABSOLUTE-move ratio. On that same checkpoint the two
    functionals are 45.2% and 71.2% -- because 16 of 60 targets flip sign on a
    fresh draw and the absolute value folds those back into the numerator. So
    the reference sat outside the range the script could print, and a CORRECT
    run would have read as a contradiction.

    Which functional is right for a cross-check is not a matter of taste. The
    signed ratio is a ratio of MEANS and is therefore invariant to how much
    estimation noise each measurement carries. E|X| is not: it is strictly
    increasing in the noise of X. The two measurements do NOT share a noise
    regime (see the seeding note below), so only the signed functional is
    comparable across them. That is the same fact that forces arm B' to exist.
    """
    L = ["**A vs B: winner's-curse cross-check (NOT a defense result).**", ""]
    signed_sel = [r.move_cached for r in recs]
    signed_fresh = [r.move_control for r in recs]
    ms = statistics.mean(signed_sel)
    here_signed = (statistics.mean(signed_fresh) / ms) if ms else float("nan")
    abs_sel = [r.effect_cached for r in recs]
    abs_fresh = [r.effect_control for r in recs]
    ma = statistics.mean(abs_sel)
    here_abs = (statistics.mean(abs_fresh) / ma) if ma else float("nan")
    n_flip = sum(1 for m in signed_fresh if m < 0)

    L.append(f"- this run, SIGNED retention mean(fresh move)/mean(selection move) = "
             f"{here_signed*100:.1f}%  ({n_flip}/{len(recs)} targets flip sign on the "
             f"fresh draw)")
    L.append(f"- this run, ABSOLUTE retention mean|B|/mean|A| = {here_abs*100:.1f}% "
             f"(NOT the comparable functional -- see below; every reference "
             f"number in this section is recomputed from the checkpoint at run "
             f"time, none is a literal in this file)")
    if ref is None:
        p = wc_checkpoint_path(attack)
        why = unavailable_reason or (
            f"no winner's-curse checkpoint for this cell at `{p.name}`"
            if not p.exists()
            else f"`{p.name}` exists but was not supplied as a reference here")
        L += [f"- reference: **unavailable** -- {why}. The cross-check is SKIPPED "
              "rather than compared against another cell's number.", ""]
        return L
    L.append(f"- reference, recomputed live from `{ref.path.name}` (n={ref.n}, "
             f"{ref.n_sign_flips} sign flips): SIGNED retention "
             f"{ref.signed_retention*100:.1f}%, ABSOLUTE retention "
             f"{ref.absolute_retention*100:.1f}%")
    L += ["",
          "Compare SIGNED against SIGNED. The signed retention is a ratio of means "
          "and is invariant to how noisy each measurement is; the absolute one is "
          "not, because E|X| is strictly increasing in the noise of X. The two "
          "measurements do not share a noise regime.",
          "",
          "SEEDING. winners_curse_reeval draws at a FIXED --fresh_seed 1; arm B here "
          "is unseeded. For the SIGNED functional this does not matter: seed 1 was "
          "chosen a priori and is independent of the seed-0 draw the attack selected "
          "on, so the fresh move is an unbiased draw from the post-selection "
          "distribution either way -- the seed fixes WHICH independent draw is taken, "
          "not its distribution. Two second-order differences remain and are the "
          "reason this is a cross-check and not an equality test: (i) a fixed seed "
          "resets the RNG identically before the Q and the Q' call, so the two sides "
          "of a target are not independent there and are here, which changes "
          "Var(move) but not E(move); (ii) an ABSOLUTE functional is sensitive to "
          "exactly that variance, which is the second reason not to cross-check with "
          "it. POPULATIONS also differ: the reference is the `_def` campaign's "
          f"{ref.n} sorted targets, this cell is the run's filtered and capped "
          "targets. Read a large disagreement as a flag to investigate, never as a "
          "refutation of either measurement.", ""]
    return L


def analyse_cell(recs: list[DefenseRecord], attack: str, *, k: int, aggregate: str,
                 wc_ref: WinnersCurseReference | None = None,
                 wc_unavailable_reason: str | None = None,
                 n_boot: int = N_BOOT) -> tuple[list[str], dict[str, ArmComparison]]:
    """Everything the report says about one attack cell. Pure: no GPU, no I/O."""
    L = [f"## {attack}: n = {len(recs)}", ""]
    a = [r.effect_cached for r in recs]
    b = [r.effect_control for r in recs]
    bp = [r.effect_noise for r in recs]
    c = [r.effect_defended for r in recs]

    # ASCII only: this report is printed to a Windows cp1252 console as well as
    # written to a UTF-8 file.
    L += ["| arm | what it aggregates | mean abs. move (nats) | median |",
          "|---|---|---|---|",
          f"| A cached | selection-time, seeded | {statistics.mean(a):.3f} | "
          f"{statistics.median(a):.3f} |",
          f"| B control | 1 fresh draw | {statistics.mean(b):.3f} | "
          f"{statistics.median(b):.3f} |",
          f"| B' noise | m fresh draws, IDENTICAL input | {statistics.mean(bp):.3f} | "
          f"{statistics.median(bp):.3f} |",
          f"| C defended | m fresh draws, PARAPHRASES | {statistics.mean(c):.3f} | "
          f"{statistics.median(c):.3f} |", ""]

    m_all = [r.m_before for r in recs] + [r.m_after for r in recs]
    eff_d = [r.d_before for r in recs] + [r.d_after for r in recs]
    degen = sum(1 for e in eff_d if e == 0)
    L.append(f"aggregate size m actually used: mean {statistics.mean(m_all):.2f} "
             f"(= 1 + {statistics.mean(eff_d):.2f} paraphrases of {k} requested). "
             f"Arm B' used the SAME m on the same target and side, by construction. "
             f"{degen}/{len(eff_d)} calls degenerated to a single variant (the "
             f"equivalence gate rejected every paraphrase).")
    if degen > 0.25 * len(eff_d):
        L += ["",
              "> **WARNING.** More than a quarter of the defended scores averaged",
              "> nothing at all. For those C IS B' IS B, and every comparison below",
              "> is diluted toward 0 by construction. Report the non-degenerate",
              "> subset separately before drawing any conclusion."]
    L.append("")

    cmps = {
        "C vs B'": compare_arms(c, bp, "C vs B'", n_boot=n_boot),
        "B' vs B": compare_arms(bp, b, "B' vs B", n_boot=n_boot),
        "C vs B": compare_arms(c, b, "C vs B", n_boot=n_boot),
        "C vs A": compare_arms(c, a, "C vs A", n_boot=n_boot),
    }

    # --- THE DEFENSE ------------------------------------------------------
    prim = cmps["C vs B'"]
    L += ["### C vs B': THE DEFENSE (the only comparison that isolates paraphrasing)",
          ""]
    L += format_comparison(prim)
    L.append("")
    if prim.verdict == "NOT COMPUTABLE":
        L += ["> **NOT COMPUTABLE for this cell.** Fewer than 2 usable targets, or a",
              "> non-finite arm. This is an ABSENCE of evidence and must not be read",
              "> as a rejection: the prediction was not tested here.", ""]
    elif prim.verdict == "FAILED":
        L += ["> **The prediction FAILED for this cell.** The 95% interval for the",
              "> paired difference covers 0 (or lies below it): averaging over",
              "> PARAPHRASES did not reduce the surviving effect beyond what averaging",
              "> the same number of re-draws of the identical input already achieves.",
              "> The defense is a variance reduction, and a paraphraser is not needed",
              "> to buy one.", ""]
    else:
        L += ["> **The prediction SURVIVES for this cell.** The interval excludes 0 on",
              "> the positive side with noise-averaging held equal, so the reduction is",
              "> attributable to paraphrase dilution and not to aggregating more",
              "> evaluations.", ""]

    # --- the artefact -----------------------------------------------------
    art = cmps["B' vs B"]
    L += ["### B' vs B: the noise-averaging artefact, MEASURED", "",
          "Two arms with no defense in either: one fresh draw against m fresh draws "
          "of the SAME input. Any reduction here is pure variance reduction. Under "
          "the strict null this is exactly the number a C-vs-B comparison reports.",
          ""]
    L += format_comparison(art)
    L.append("")

    # --- the round-1 comparison, kept and labelled ------------------------
    conf = cmps["C vs B"]
    L += ["### C vs B: the ROUND-1 comparison (CONFOUNDED -- do not quote)", ""]
    L += format_comparison(conf)
    L += ["",
          "This is the artefact above compounded with whatever the defense does. "
          "It is printed only so the size of the round-1 error is visible.", ""]

    # --- cross-check ------------------------------------------------------
    L += cross_check_lines(recs, wc_ref, attack,
                           unavailable_reason=wc_unavailable_reason)

    tot = cmps["C vs A"]
    L += [f"**C vs A (total apparent reduction): {tot.ratio*100:.1f}% "
          f"[{tot.ratio_lo*100:.1f}%, {tot.ratio_hi*100:.1f}%].** Do not quote this "
          f"as the defense's effect -- it compounds the defense with the winner's "
          f"curse AND the noise-averaging artefact, which is what the round-0 "
          f"two-arm version of this script reported.", ""]
    return L, cmps


# ---------------------------------------------------------------------------
# synthetic verification (no GPU, no model, no campaign)
# ---------------------------------------------------------------------------

def matched_redraws(text: str, res, score) -> list[float]:
    """Arm B' for one side: m identical-input SE draws, where m is the aggregate
    size arm C ACTUALLY used on this target and side (`res.n_variants`), not the
    requested k and not its expectation.

    Draw 0 is arm C's own original-input variant score, reused rather than
    redrawn -- common random numbers on a paired contrast. It leaves every arm's
    marginal distribution exactly as specified, makes the strict null exact
    (under it C and B' are identically distributed), tightens the paired
    interval, and saves one SE evaluation per side. Arm B is this same draw 0.

    `score(text) -> float` is the fresh single-input scorer, injected so this is
    testable without a GPU.
    """
    out = [float(res.per_variant_entropy[0])]
    for _ in range(int(res.n_variants) - 1):
        out.append(float(score(text)))
    return out


def make_synthetic_records(n: int = 24, *, attack: str = "false_alarm",
                           r_cb: float = 0.50, r_bb: float = 0.40,
                           r_ba: float = 0.70, aggregate: str = "median",
                           k: int = 4, seed: int = 0) -> list[DefenseRecord]:
    """Records with EXACTLY known planted reductions, for end-to-end estimator
    verification with no GPU.

    Per target the cached effect is a_i and the arms are nested multiplicatively:

        |B_i|  = (1 - r_ba) * a_i          -> B  vs A  reduction = r_ba
        |B'_i| = (1 - r_bb) * |B_i|        -> B' vs B  reduction = r_bb
        |C_i|  = (1 - r_cb) * |B'_i|       -> C  vs B' reduction = r_cb

    Because the ratio is planted PER TARGET, every estimator must recover it
    exactly: the ratio of means, the per-question reduction, and (for B' vs B)
    the aggregation path, since the m=3 redraw list [B, B', B'] has median B'
    for either ordering while its first element is B. Signed moves carry the
    attack's own sign, so the winner's-curse cross-check is exercised too.
    """
    rng = np.random.default_rng(seed)
    sign = -1.0 if attack == "hide" else 1.0
    recs: list[DefenseRecord] = []
    for i in range(n):
        a = float(0.4 + 1.2 * rng.random())          # cached effect, nats
        v_b = (1.0 - r_ba) * a
        v_bp = (1.0 - r_bb) * v_b
        v_c = (1.0 - r_cb) * v_bp
        recs.append(DefenseRecord(
            attack=attack,
            question_id=f"syn_{i:04d}",
            aggregate=aggregate,
            k_requested=k,
            cached_before=0.0,
            cached_after=sign * a,
            redraws_before=[0.0, 0.0, 0.0],
            redraws_after=[sign * v_b, sign * v_bp, sign * v_bp],
            defended_before=0.0,
            defended_after=sign * v_c,
            d_before=2,
            d_after=2,
        ))
    return recs


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------

def estimate(k: int, counts: dict[str, int], *, campaign: str, filt: str,
             cap: int) -> list[str]:
    """Cost table. No GPU, no model load.

    Every figure is derived from the CURRENT campaign's cell sizes and prints
    the n it used, on the same line as the hours. The round-0/1 rows exist so a
    cost delta can never again be quoted from a commit message: the arithmetic
    is in the output.
    """
    n_total = sum(counts.values())
    per_def = sec_per_defended_call(k)
    per_noise = sec_per_noise_control(k)
    per_out = sec_per_outcome(k)
    m = variants_per_call(k)
    total = n_total * per_out + SEC_MODEL_LOAD

    lines = ["## Cost estimate (no GPU used to produce this table)", "",
             f"HEADLINE: **{total/3600:.2f} GPU-h at n = {n_total} outcomes** "
             f"({', '.join(f'{a} {c}' for a, c in counts.items()) or 'no cells'}), "
             f"k={k}, gate {GATE_PASS_RATE:.2f}, cap {cap}/attack, filter `{filt}`, "
             f"campaign `{campaign}`.",
             "This number is a function of the cell sizes READ ABOVE at run time. "
             "Quote it only together with the n; the cells grow.", ""]
    lines += [f"assumed gate pass rate {GATE_PASS_RATE:.2f} -> m = {m:.2f} "
              f"evaluations per aggregate",
              f"one semantic_entropy() call              {SEC_PER_SE_EVAL:6.1f} s",
              f"arm C, one side (k proposals+gates, m SE) {per_def:6.1f} s",
              f"arm B', one side (m-1 extra SE)          {per_noise:6.1f} s",
              f"arms A and B, one side                     {0.0:6.1f} s  "
              f"(A is cached; B is B' draw 0, already paid for)",
              f"ONE OUTCOME, both sides, all four arms   {per_out:6.1f} s", ""]
    lines += ["cost history, same k and gate rate, so the deltas are checkable:",
              f"  round 0  2 arms (A, C)          {sec_per_outcome_round0(k):6.1f} s/outcome",
              f"  round 1  3 arms (+ unmatched B) {sec_per_outcome_round1(k):6.1f} s/outcome  "
              f"({sec_per_outcome_round1(k)/sec_per_outcome_round0(k)-1:+.0%} vs round 0)",
              f"  round 2  4 arms (+ matched B')  {per_out:6.1f} s/outcome  "
              f"({per_out/sec_per_outcome_round1(k)-1:+.0%} vs round 1, "
              f"{per_out/sec_per_outcome_round0(k)-1:+.0%} vs round 0)", ""]
    for attack, n in counts.items():
        lines.append(f"  {attack:<12} {n:3d} outcomes  {n*per_out/3600:5.2f} GPU-h")
    lines.append(f"  {'TOTAL':<12} {n_total:3d} outcomes  {total/3600:5.2f} GPU-h  "
                 f"(+{SEC_MODEL_LOAD/60:.0f} min model load)")
    lines += ["", "sensitivity to k (same n):"]
    for kk in (1, 2, 3, 4, 6):
        t = (n_total * sec_per_outcome(kk) + SEC_MODEL_LOAD) / 3600
        lines.append(f"  k={kk}  m={variants_per_call(kk):.2f}  "
                     f"{sec_per_outcome(kk):6.1f} s/outcome  {t:5.2f} GPU-h")
    lines += ["",
              "VRAM: Llama-3.1-8B nf4 ~5.5 GB (results/run_all.log) + "
              "DeBERTa-large-MNLI fp32 ~1.6 GB ~= 7 GB, co-resident.", ""]
    return lines


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="_defb",
                    help="campaign directory suffix under samples/attacks/wk9<tag>. "
                         "'' selects the SUPERSEDED pre-B1 n=15 wk9 campaign.")
    ap.add_argument("--campaign-dir", default="",
                    help="explicit campaign directory, overrides --tag")
    ap.add_argument("--attacks", default=",".join(ATTACKS))
    ap.add_argument("--filter", default="entropy_and_feasible",
                    choices=["entropy_and_feasible", "success", "improved"],
                    help="which outcomes are attack targets worth defending against")
    ap.add_argument("--k", type=int, default=4, help="paraphrases per input (d)")
    ap.add_argument("--aggregate", default="median", choices=list(AGGREGATES))
    ap.add_argument("--max-per-attack", type=int, default=40)
    ap.add_argument("--checkpoint", default="auto")
    ap.add_argument("--out", default="")
    ap.add_argument("--wc-tag", default="_def",
                    help="tag of the winner's-curse checkpoint used as the "
                         "cross-check reference and the null-simulation input")
    ap.add_argument("--estimate-only", action="store_true",
                    help="print the GPU cost table and exit without loading a model")
    ap.add_argument("--null-sim", action="store_true",
                    help="print the strict-null calibration table (CPU only): how "
                         "much apparent 'defense' pure noise-averaging buys")
    ap.add_argument("--null-sim-reps", type=int, default=20_000)
    ap.add_argument("--synthetic", action="store_true",
                    help="run the analysis on a synthetic checkpoint with planted "
                         "reductions; no GPU, no model, no campaign needed")
    ap.add_argument("--synthetic-plant", default="0.50,0.40,0.70",
                    help="planted reductions 'C-vs-B\\',B\\'-vs-B,B-vs-A'")
    ap.add_argument("--synthetic-n", type=int, default=24)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    out_path = Path(args.out) if args.out else RESULTS_DIR / f"defense_eval{args.tag}.md"
    ckpt_path = (RESULTS_DIR / f"defense_ckpt{args.tag}.jsonl"
                 if args.checkpoint == "auto" else Path(args.checkpoint))

    report: list[str] = []

    def log(s: str = "") -> None:
        print(s, flush=True)
        report.append(s)

    def flush_report() -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    log("# Defense: input-paraphrase-averaged SE vs the attacks")
    log("")

    # ---- synthetic mode: estimator verification, no GPU ------------------
    if args.synthetic:
        try:
            r_cb, r_bb, r_ba = (float(x) for x in args.synthetic_plant.split(","))
        except Exception:
            print(f"--synthetic-plant must be three comma-separated reductions, "
                  f"got {args.synthetic_plant!r}", file=sys.stderr)
            return 2
        log(f"SYNTHETIC MODE. No GPU, no model, no campaign. n={args.synthetic_n} "
            f"targets with per-target reductions planted EXACTLY at "
            f"C-vs-B' {r_cb:.0%}, B'-vs-B {r_bb:.0%}, B-vs-A {r_ba:.0%}. Every "
            f"estimator below must recover those numbers; this is the end-to-end "
            f"check that the analysis path reports what it claims to.")
        log("")
        recs = make_synthetic_records(args.synthetic_n, r_cb=r_cb, r_bb=r_bb,
                                      r_ba=r_ba, aggregate=args.aggregate, k=args.k)
        lines, _ = analyse_cell(
            recs, recs[0].attack, k=args.k, aggregate=args.aggregate, wc_ref=None,
            wc_unavailable_reason="these are SYNTHETIC records and must not be "
                                  "cross-checked against a real measurement")
        for line in lines:
            log(line)
        flush_report()
        print(f"\nWritten to {out_path}", file=sys.stderr)
        return 0

    from se.sampling import DEFAULT_SAMPLES_DIR
    from se.attacks.harness import read_outcomes

    campaign_dir = (Path(args.campaign_dir) if args.campaign_dir
                    else DEFAULT_SAMPLES_DIR / "attacks" / f"wk9{args.tag}")
    attacks = [a.strip() for a in args.attacks.split(",") if a.strip()]

    log(f"campaign: `{campaign_dir}`  filter: `{args.filter}`  "
        f"d={args.k}  aggregate={args.aggregate}  cap={args.max_per_attack}/attack")
    log("")
    log("Four arms. The two-arm version was confounded by the winner's curse; the")
    log("three-arm version was confounded by noise-averaging, because E|X| is")
    log("strictly increasing in the noise of X and the d=1 control carried more of")
    log("it than the defended arm. See the module docstring.")
    log("")
    log("  A  cached    selection-time |SE(Q')-SE(Q)|, seeded")
    log("  B  control   one fresh unseeded draw per side")
    log("  B' noise     m fresh unseeded draws of the IDENTICAL input, same aggregate")
    log("  C  defended  m fresh unseeded draws over the input plus its paraphrases")
    log("")
    log("**C vs B' is the defense**: same m, same aggregation rule, same generation")
    log("config; the only difference is paraphrasing. **B' vs B is the artefact**")
    log("that C vs B would have booked as a defense. A vs B is the winner's curse.")
    log("")
    log(FALSIFIABLE_CLAIM)
    log("")

    # ---- winner's-curse reference + strict-null calibration --------------
    wc_refs = {a: load_wc_reference(wc_checkpoint_path(a, args.wc_tag)) for a in attacks}
    if args.null_sim:
        ref = next((r for r in wc_refs.values() if r is not None), None)
        if ref is None:
            log(f"(--null-sim requested but no winner's-curse checkpoint found under "
                f"`{RESULTS_DIR}` for {attacks} at tag `{args.wc_tag}`; skipped)")
            log("")
        else:
            for line in null_sim_lines(ref, args.aggregate, args.k, args.null_sim_reps):
                log(line)

    # ---- select targets --------------------------------------------------
    targets: dict[str, list] = {}
    for attack in attacks:
        camp = campaign_dir / f"triviaqa_se_{attack}.jsonl"
        if not camp.exists():
            log(f"- {attack}: no campaign file at `{camp}`, skipped")
            continue
        allo = read_outcomes(camp)
        sel = [o for o in allo if getattr(o, args.filter)][: args.max_per_attack]
        if not sel and allo:
            n_imp = sum(o.improved for o in allo)
            log(f"- {attack}: 0 of {len(allo)} outcomes pass `{args.filter}` "
                f"({n_imp} pass `improved`). Records written before the B2 schema "
                f"have entropy_and_feasible=False by default -- pass "
                f"`--filter improved` explicitly if that is really the intent.")
            continue
        targets[attack] = sel
        log(f"- {attack}: {len(sel)} targets of {len(allo)} outcomes")
    log("")

    counts = {a: len(v) for a, v in targets.items()}
    for line in estimate(args.k, counts, campaign=str(campaign_dir),
                         filt=args.filter, cap=args.max_per_attack):
        log(line)

    if args.estimate_only:
        print("(--estimate-only: no model loaded, nothing run)", file=sys.stderr)
        return 0
    if not targets:
        log("No targets; nothing to run.")
        flush_report()          # flush AFTER the last line, or it is not in the file
        return 1

    # ---- run -------------------------------------------------------------
    try:
        done = _ckpt_load(ckpt_path, aggregate=args.aggregate, k=args.k)
    except CheckpointMismatch as exc:
        print(f"[defense] ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"checkpoint {ckpt_path}: {len(done)} records already complete", flush=True)

    todo = [(a, o) for a, outs in targets.items() for o in outs
            if f"{a}::{o.question_id}" not in done]

    # Only pay for the model when there is something left to run. A completed
    # checkpoint can therefore be re-analysed (or the report re-rendered after an
    # analysis change) on a machine with no GPU at all, while the chain has it.
    lm = nli = None
    if todo:
        from se.nli import NLI
        from se import model as M
        lm = M.load_llama(ModelConfig())
        nli = NLI()
    else:
        print("checkpoint complete: re-rendering the report, no model loaded",
              flush=True)

    # Every fresh arm forces seed=None so B, B' and C re-sample on exactly the
    # same footing. defended_entropy does the same internally.
    fresh = GenConfig(max_new_tokens=48, n_samples=10, temperature=1.0, seed=None)

    def score_fresh(text: str) -> float:
        return semantic_entropy(text, lm, nli, fresh).entropy_nats

    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    n_new = 0
    with ckpt_path.open("a", encoding="utf-8") as fh:
        for attack, outcomes in targets.items():
            for i, o in enumerate(outcomes):
                key = f"{attack}::{o.question_id}"
                if key in done:
                    continue
                d_q = defended_entropy(o.question, lm, nli, k_paraphrases=args.k,
                                       aggregate=args.aggregate, gen_cfg=fresh)
                rd_q = matched_redraws(o.question, d_q, score_fresh)
                d_adv = defended_entropy(o.best_query, lm, nli, k_paraphrases=args.k,
                                         aggregate=args.aggregate, gen_cfg=fresh)
                rd_adv = matched_redraws(o.best_query, d_adv, score_fresh)
                rec = DefenseRecord(
                    attack=attack,
                    question_id=o.question_id,
                    aggregate=args.aggregate,
                    k_requested=args.k,
                    # Cached: both sides from the run that produced the attack, so
                    # the selection-time effect has no fresh-vs-cached mismatch.
                    cached_before=o.entropy_before,
                    cached_after=o.entropy_after,
                    redraws_before=rd_q,
                    redraws_after=rd_adv,
                    defended_before=d_q.defended_entropy,
                    defended_after=d_adv.defended_entropy,
                    d_before=d_q.effective_d,
                    d_after=d_adv.effective_d,
                    rejected_gate_before=d_q.n_rejected_gate,
                    rejected_gate_after=d_adv.n_rejected_gate,
                )
                fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
                fh.flush()
                done[key] = rec
                n_new += 1
                if n_new % 5 == 0:
                    el = time.perf_counter() - t0
                    print(f"  {attack} {i+1}/{len(outcomes)} | {n_new} new in "
                          f"{el/60:.1f} min ({el/n_new:.0f}s/target)", flush=True)

    # ---- analyse ---------------------------------------------------------
    for attack, outcomes in targets.items():
        recs = [done[f"{attack}::{o.question_id}"] for o in outcomes
                if f"{attack}::{o.question_id}" in done]
        if not recs:
            continue
        lines, _ = analyse_cell(recs, attack, k=args.k, aggregate=args.aggregate,
                                wc_ref=wc_refs.get(attack))
        for line in lines:
            log(line)

    log("## Scope")
    log("")
    log("This measures the defense against paraphrases the attacker found WITHOUT")
    log("knowing a defense was deployed. It is therefore an upper bound on the")
    log("defense's value: an adaptive attacker optimising against")
    log("`defended_entropy` directly is a strictly harder case and is not run here.")
    log("")
    log("C vs B' licenses a statement about PARAPHRASING and nothing else. If the")
    log("interest is 'should a deployed detector average several evaluations', that")
    log("is the B' vs B row, it needs no paraphraser, and it is cheaper.")
    log("")
    log("No AUROC is reported. The defended detector's AUROC needs both classes in")
    log("one pool (hide targets are all incorrect-answer questions, false-alarm")
    log("targets all correct-answer ones), which is the fair-pool construction owned")
    log("by scripts/recompute_fair.py. An earlier docstring here promised that")
    log("number; it was never computed.")

    flush_report()
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
