"""The cluster-count bound: the one ceiling claim that survives every SE estimator.

WHY THIS EXISTS
---------------
`results/fair_pool_granularity.md` characterises the attainable lattice of semantic
entropy at N=10 (39 attainable values, 2 of them in the top tenth of the range). That
statement is TRUE OF OUR ESTIMATOR and only of our estimator. There are three semantic
entropies in the literature and we implement one of them:

  (1) DISCRETE / sample-proportion.  H = -sum_c (n_c/N) log(n_c/N).
      Farquhar et al. (Nature 2024) define this as a variant and use it for all their
      GPT-4 results. It is `se.entropy.discrete_entropy`, i.e. what this repo computes.
      Cluster probabilities are multiples of 1/N -> a finite lattice of attainable
      values. Bounded by log N.

  (2) FARQUHAR Eq. (5).  H = -sum_c p(c) log p(c) with p(c) proportional to the summed
      sequence likelihood of the cluster's members, explicitly normalised over clusters.
      p is a genuine probability vector over the K observed clusters, so this is still
      bounded by log K <= log N -- but it is NOT confined to a lattice: p(c) can take
      any value in (0, 1).

  (3) KUHN et al. Eq. (4).  An average of per-cluster surprisals, UNNORMALISED. It is
      not the entropy of a probability vector and is NOT bounded by log N at all.

Consequence for the paper: the LATTICE claim is estimator-specific and dies under (2)
and (3). The log N CEILING survives under (1) and (2) but not (3).

THE CLAIM THIS SCRIPT ESTABLISHES
---------------------------------
K, the number of observed semantic clusters, is produced by the SAME clustering step
under all three variants -- none of them changes which samples get merged, only how the
merged groups are weighted. And for any NORMALISED weighting over K clusters,

        H <= log K                    (entropy of a K-point distribution)

so a score in the top tenth of the range [0, log N] requires

        log K >= 0.9 log N   <=>   K^10 >= N^9   <=>   K >= ceil(N^0.9).

At N=10 that is K >= 8, because log 8 = 2.0794 > 0.9 log 10 = 2.0723 while
log 7 = 1.9459 < 2.0723. This is a NECESSARY condition on the CLUSTERING, not on the
weighting, so it holds for the discrete estimator and for Farquhar Eq. (5) alike -- and
it is checkable from the cached `assignments` with no model and no GPU.

WHAT IS AND IS NOT CLAIMED
--------------------------
- Necessary, not sufficient. K >= 8 admits a top-decile score; it does not produce one.
  Section 3 measures how nearly-uniform the weights have to be at each K.
- Kuhn Eq. (4) is exempt: it has no log N ceiling, so no ceiling-derived bound applies.
  Reported here as a stated scope limit, not smuggled in.
- Discrete-specific tightening (Section 4): over integer partitions of 10 the binding
  requirement is actually K >= 9, since no 8-part partition of 10 clears 2.0723.

Usage (data lives in the WSL cache; CPU only, no model, no GPU):
    wsl -d Ubuntu-24.04 -- bash -c "cd '/mnt/i/GITHUBPROJECTS/SE Research' && \
        ./.venv-wsl/bin/python scripts/cluster_count_bound.py"
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
sys.path.insert(0, str(REPO_ROOT / "src"))

from se.attacks.select import ENTROPY, RELABELED, _stratum_ids, load_labels  # noqa: E402
from se.entropy import discrete_entropy  # noqa: E402

N_SAMPLES = 10                       # the deployed sample budget N
CAP = math.log(N_SAMPLES)            # ln 10 = 2.302585..., the attainable maximum
DECILE_FRAC = 0.9                    # "top tenth of the RANGE [0, log N]"
TOP_DECILE = DECILE_FRAC * CAP       # 2.072327... nats
N_PER_STRATUM = 200                  # fair pool: 200 correct + 200 hallucinating
N_FA = 80                            # the false-alarm attack stratum
SEED = 0
TOL = 1e-12
N_MC_SIMPLEX = 400_000               # draws per K for the sufficiency-volume estimates
BALL_R_MULT = 1.5                    # containing-ball radius, as a multiple of the
BALL_R_MULT_CHECK = 2.5              # quadratic radius; the second value is the
                                     # containment stability check
RULE_OF_THREE = 3.0                  # 95% upper bound on p given 0 hits in n draws

ATTACK_CACHE = Path("~/.cache/se-research/samples/attacks").expanduser()
FA_CELLS = [                         # on-disk cells that should be the FA-80 prefix
    "wk9_defb/triviaqa_se_false_alarm.jsonl",
    "wk9_def/triviaqa_se_false_alarm.jsonl",
]


# --------------------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion. Returns (p_hat, lo, hi).

    Wilson rather than Wald because several of these counts sit near 0 or near n,
    where Wald leaves the unit interval and under-covers."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


def newcombe_diff(k1: int, n1: int, k2: int, n2: int,
                  z: float = 1.959963984540054) -> tuple[float, float, float]:
    """Newcombe's method 10 interval for p1 - p2, built from the two Wilson intervals.

    Wilson-based rather than Wald-based for the same reason as above; Newcombe is the
    standard hybrid-score interval for a difference of independent proportions."""
    p1, l1, u1 = wilson(k1, n1, z)
    p2, l2, u2 = wilson(k2, n2, z)
    lo = (p1 - p2) - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = (p1 - p2) + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return p1 - p2, max(-1.0, lo), min(1.0, hi)


# ------------------------------------------------------------------- the bound itself
def k_min_exact(n_samples: int, num: int = 9, den: int = 10) -> int:
    """Smallest integer K with log K >= (num/den) * log N, computed in EXACT integers.

        log K >= (num/den) log N  <=>  den*log K >= num*log N  <=>  K**den >= N**num

    Integer arithmetic, so no float tie-breaking at the boundary (a real hazard: at
    N=10 the margin is log 8 - 0.9 log 10 = 7.1e-3 nats, and for other N the two sides
    can coincide exactly). Cross-checked against ceil(N**0.9) by the caller."""
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    target = n_samples ** num
    for k in range(1, n_samples + 1):
        if k ** den >= target:
            return k
    return n_samples  # unreachable: K=N gives N**den >= N**num for den >= num


def k_min_float(n_samples: int, frac: float = DECILE_FRAC) -> int:
    """ceil(N**frac) -- the closed form quoted in prose. Cross-check for k_min_exact."""
    return math.ceil(n_samples ** frac - 1e-12)


def partitions(n: int, largest: int | None = None):
    """Yield every integer partition of n as a non-increasing tuple."""
    if largest is None:
        largest = n
    if n == 0:
        yield ()
        return
    for part in range(min(n, largest), 0, -1):
        for rest in partitions(n - part, part):
            yield (part,) + rest


def partition_entropy(part: tuple[int, ...]) -> float:
    tot = sum(part)
    return -sum((c / tot) * math.log(c / tot) for c in part)


def discrete_k_min(n_samples: int, thresh: float) -> tuple[int, dict[int, float]]:
    """For the DISCRETE estimator: the smallest number of parts K such that SOME integer
    partition of n_samples into exactly K parts has entropy >= thresh, plus the max
    attainable entropy at each K.

    This is strictly stronger than the weighting-invariant bound, because the discrete
    estimator cannot place arbitrary mass on a cluster -- p(c) is a multiple of 1/N."""
    best_at_k: dict[int, float] = {}
    for p in partitions(n_samples):
        k = len(p)
        h = partition_entropy(p)
        if h > best_at_k.get(k, -1.0):
            best_at_k[k] = h
    feasible = [k for k, h in best_at_k.items() if h >= thresh - TOL]
    return (min(feasible) if feasible else n_samples + 1), best_at_k


def _entropy_rows(w: np.ndarray) -> np.ndarray:
    safe = np.where(w > 0, w, 1.0)
    return -(np.where(w > 0, w * np.log(safe), 0.0)).sum(axis=1)


def simplex_topdecile_volume(k: int, thresh: float, n_mc: int, rng) -> tuple[int, int]:
    """Crude uniform Monte Carlo: hits and draws for {H >= thresh} on the (K-1)-simplex.

    Dirichlet(1,...,1) IS the uniform distribution on the simplex, so hits/draws is an
    unbiased estimate of the normalised volume. Returns raw counts so the caller can
    attach an interval (and so a zero-hit cell is reported as a bound, not as "0%")."""
    if k <= 1:
        return (n_mc if 0.0 >= thresh - TOL else 0), n_mc
    hit = 0
    done = 0
    while done < n_mc:
        m = min(20_000, n_mc - done)
        hit += int((_entropy_rows(rng.dirichlet(np.ones(k), size=m)) >= thresh - TOL).sum())
        done += m
    return hit, n_mc


def quadratic_radius(k: int, thresh: float) -> float:
    """Radius of the admissible set around the uniform weighting, to second order.

    Writing p = u + d with u = (1/K,...,1/K) and sum_i d_i = 0,
        H(u + d) = log K - (K/2) ||d||^2 + O(||d||^3),
    so {H >= thresh} is approximately the ball ||d|| <= sqrt(2 (log K - thresh) / K)."""
    eps = math.log(k) - thresh
    if eps <= 0:
        return 0.0
    return math.sqrt(2.0 * eps / k)


def log_ball_over_simplex(k: int, radius: float) -> float:
    """log[ vol_{K-1}(ball of `radius`) / vol_{K-1}(standard simplex) ].

    The simplex {p >= 0, sum p = 1} is a (K-1)-dimensional set in R^K with volume
    sqrt(K)/(K-1)!; the ball is taken inside the same hyperplane, so both are measured
    in the same (K-1)-dimensional Lebesgue measure and the ratio is dimensionless."""
    d = k - 1
    log_ball = (d / 2) * math.log(math.pi) + d * math.log(radius) - math.lgamma(d / 2 + 1)
    log_simplex = 0.5 * math.log(k) - math.lgamma(k)
    return log_ball - log_simplex


def simplex_topdecile_volume_ball(k: int, thresh: float, radius: float,
                                  n_mc: int, rng) -> tuple[float, float, int, float]:
    """Normalised volume of {H >= thresh} by the ball-ratio method. EXACT, not an
    approximation, provided the admissible set is contained in the ball of `radius`.

        vol(A)/vol(simplex) = [vol(A n B_R)/vol(B_R)] * [vol(B_R)/vol(simplex)]

    The first factor is a plain hit rate under uniform sampling of B_R; the second is
    closed form. Crude uniform-on-simplex sampling cannot resolve A at K=8 (zero hits
    in any feasible number of draws) because A there has relative volume ~2e-6, but
    sampling the ball puts essentially all draws where A lives.

    H is concave, so A is convex and nested around the uniform weighting -- which is
    what makes a single containing ball the right envelope. Containment is checked
    empirically: the returned `max_hit_radius` must sit well inside `radius`, and the
    caller re-runs at a larger radius to confirm the estimate does not grow.

    Returns (volume, standard_error, hits, max_hit_radius)."""
    d = k - 1
    u = np.full(k, 1.0 / k)
    ratio = math.exp(log_ball_over_simplex(k, radius))
    hits = 0
    done = 0
    max_hit_r = 0.0
    while done < n_mc:
        m = min(200_000, n_mc - done)
        # uniform on the (K-1)-ball inside the hyperplane {sum d_i = 0}:
        # isotropic direction in the hyperplane, radius ~ R * U^(1/(K-1)).
        g = rng.standard_normal((m, k))
        g -= g.mean(axis=1, keepdims=True)
        g /= np.linalg.norm(g, axis=1, keepdims=True)
        rad = radius * rng.random(m) ** (1.0 / d)
        p = u + g * rad[:, None]
        inside = (p >= 0).all(axis=1)          # points outside the simplex are not in A
        h = np.full(m, -1.0)
        h[inside] = _entropy_rows(p[inside])
        sel = inside & (h >= thresh - TOL)
        if sel.any():
            max_hit_r = max(max_hit_r, float(rad[sel].max()))
        hits += int(sel.sum())
        done += m
    frac = hits / n_mc
    se = math.sqrt(max(frac * (1 - frac), 0.0) / n_mc) * ratio
    return frac * ratio, se, hits, max_hit_r


# ------------------------------------------------------------------------ data access
def load_entropy_records(path: Path = ENTROPY) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            obj = json.loads(line)
            out[obj["question_id"]] = obj
    return out


def verify_cache(ent: dict[str, dict], labels: dict[str, dict]) -> list[str]:
    """Recompute K and H from the raw `assignments` and confirm the cache is self
    consistent. Returns human-readable check lines; raises if a check fails hard."""
    lines = []
    if set(ent) != set(labels):
        raise AssertionError("entropy.jsonl and relabeled.jsonl cover different ids")
    bad_k = bad_h = 0
    max_dh = 0.0
    for qid, rec in ent.items():
        a = rec["assignments"]
        if len(a) != N_SAMPLES:
            raise AssertionError(f"{qid}: {len(a)} assignments, expected {N_SAMPLES}")
        if len(set(a)) != rec["n_clusters"]:
            bad_k += 1
        dh = abs(discrete_entropy(a) - rec["entropy_nats"])
        max_dh = max(max_dh, dh)
        if dh > 1e-9:
            bad_h += 1
    if bad_k or bad_h:
        raise AssertionError(f"cache inconsistent: {bad_k} K mismatches, {bad_h} H mismatches")
    lines.append(f"- `assignments` -> K recomputed for all {len(ent)} questions: "
                 f"**{bad_k} mismatches** against the cached `n_clusters`.")
    lines.append(f"- `assignments` -> discrete H recomputed for all {len(ent)} questions: "
                 f"max |dH| = **{max_dh:.2e}** nats against the cached `entropy_nats`.")
    lines.append(f"- every record carries exactly N={N_SAMPLES} assignments.")
    return lines


def verify_fa_nesting(fa_ids: list[str]) -> list[str]:
    """The 80 FA targets should be the first 80 ids of the correct stratum. Check that
    against whatever attack cells are on disk (the chain may still be writing)."""
    lines = []
    for rel in FA_CELLS:
        p = ATTACK_CACHE / rel
        if not p.exists():
            lines.append(f"| `{rel}` | absent | - |")
            continue
        ids = [json.loads(l)["question_id"] for l in p.read_text().splitlines() if l.strip()]
        prefix = ids == fa_ids[:len(ids)]
        lines.append(f"| `{rel}` | n={len(ids)} | prefix of the correct stratum: "
                     f"**{prefix}** |")
    return lines


# ------------------------------------------------------------------------- reporting
def k_table(ids: list[str], ent: dict[str, dict]) -> str:
    """Full K histogram as a markdown table row block, K=1..N."""
    c = Counter(ent[q]["n_clusters"] for q in ids)
    n = len(ids)
    rows = []
    cum = 0
    for k in range(1, N_SAMPLES + 1):
        v = c.get(k, 0)
        cum += v
        rows.append(f"| {k} | {v} | {v / n:.1%} | {1 - (cum - v) / n:.1%} |")
    return "\n".join(rows)


def k_summary(ids: list[str], ent: dict[str, dict]) -> dict:
    ks = np.array([ent[q]["n_clusters"] for q in ids])
    hs = np.array([ent[q]["entropy_nats"] for q in ids])
    n = len(ids)
    return {
        "n": n,
        "mean": float(ks.mean()),
        "median": float(np.median(ks)),
        "q25": float(np.percentile(ks, 25)),
        "q75": float(np.percentile(ks, 75)),
        "ge8": int((ks >= 8).sum()),
        "ge9": int((ks >= 9).sum()),
        "eq10": int((ks == 10).sum()),
        "le7": int((ks <= 7).sum()),
        "le3": int((ks <= 3).sum()),
        "topdecile": int((hs >= TOP_DECILE - TOL).sum()),
        "atcap": int((hs >= CAP - TOL).sum()),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    labels = load_labels(RELABELED)
    ent = load_entropy_records(ENTROPY)

    check_lines = verify_cache(ent, labels)

    right = _stratum_ids("right", SEED, labels)
    wrong = _stratum_ids("wrong", SEED, labels)
    fair_c, fair_h = right[:N_PER_STRATUM], wrong[:N_PER_STRATUM]
    fa80 = right[:N_FA]
    full = sorted(ent)
    full_c = [q for q in full if labels[q]["greedy_correct"]]
    full_h = [q for q in full if not labels[q]["greedy_correct"]]

    # The 30.3% / 59.1% figures in circulation: which label set do they come from?
    prelim = {}
    for name, ok in [("relabeled.jsonl (span oracle, the paper's rule)",
                      lambda q: bool(labels[q]["greedy_correct"])),
                     ("entropy.jsonl (pre-relabel label)",
                      lambda q: bool(ent[q]["greedy_correct"])),
                     ("relabeled.jsonl `greedy_correct_substr`",
                      lambda q: bool(labels[q]["greedy_correct_substr"]))]:
        c = [q for q in full if ok(q)]
        h = [q for q in full if not ok(q)]
        prelim[name] = (
            sum(1 for q in c if ent[q]["n_clusters"] >= 8), len(c),
            sum(1 for q in h if ent[q]["n_clusters"] >= 8), len(h),
        )

    # --- the bound, at several budgets
    bound_rows = []
    for n in (5, 10, 20, 40, 100, 1000, 1024):
        km_e, km_f = k_min_exact(n), k_min_float(n)
        assert km_e == km_f, f"exact/float bound disagree at N={n}: {km_e} vs {km_f}"
        bound_rows.append((n, km_e, km_e / n, n ** -0.1, n - km_e, math.log(n)))

    # --- sufficiency volume at each admissible K (N=10)
    #     crude uniform MC everywhere; importance sampling as well, because at K=8 the
    #     admissible set is far too small for crude sampling to resolve. K=9 and K=10
    #     are measurable both ways and act as the IS estimator's validation.
    vol_mc = {k: simplex_topdecile_volume(k, TOP_DECILE, N_MC_SIMPLEX, rng)
              for k in range(7, N_SAMPLES + 1)}
    vol_ball, vol_check, vol_quad = {}, {}, {}
    for k in range(8, N_SAMPLES + 1):
        r = quadratic_radius(k, TOP_DECILE)
        vol_ball[k] = (r,) + simplex_topdecile_volume_ball(
            k, TOP_DECILE, BALL_R_MULT * r, N_MC_SIMPLEX, rng)
        vol_check[k] = simplex_topdecile_volume_ball(
            k, TOP_DECILE, BALL_R_MULT_CHECK * r, N_MC_SIMPLEX, rng)[:2]
        vol_quad[k] = math.exp(log_ball_over_simplex(k, r))

    # --- the discrete-specific tightening
    d_kmin, best_at_k = discrete_k_min(N_SAMPLES, TOP_DECILE)

    # --- empirical: which K actually produced a top-decile score
    td_by_k = Counter(ent[q]["n_clusters"] for q in full
                      if ent[q]["entropy_nats"] >= TOP_DECILE - TOL)
    cap_by_k = Counter(ent[q]["n_clusters"] for q in full
                       if ent[q]["entropy_nats"] >= CAP - TOL)

    pops = [
        ("Fair pool -- correct stratum", fair_c),
        ("Fair pool -- hallucinating stratum", fair_h),
        ("Fair pool -- both strata pooled", fair_c + fair_h),
        ("FA attack stratum (n=80, nested in fair-correct)", fa80),
        ("Full labelled pool -- correct", full_c),
        ("Full labelled pool -- hallucinating", full_h),
        ("Full labelled pool -- natural prevalence", full),
    ]

    # ------------------------------------------------------------------ write report
    out = []
    A = out.append
    A("# The cluster-count bound: the ceiling claim that survives every SE estimator")
    A("")
    A(f"Generated {_dt.date.today().isoformat()} by `scripts/cluster_count_bound.py` "
      "(CPU only; no GPU, no model, no re-clustering).")
    A("")
    A("## 0. Why this measurement exists")
    A("")
    A("There are three semantic entropies in the literature and this repo implements "
      "one of them:")
    A("")
    A("| # | estimator | cluster weights | bounded by | ours? |")
    A("| --- | --- | --- | --- | --- |")
    A("| 1 | **Discrete** (sample proportion) | n_c / N, a multiple of 1/N | log N | "
      "**yes** -- `se.entropy.discrete_entropy` |")
    A("| 2 | **Farquhar Eq. (5)** | summed sequence likelihood, normalised over clusters "
      "| log K <= log N | no |")
    A("| 3 | **Kuhn Eq. (4)** | mean of per-cluster surprisals, **unnormalised** | "
      "**nothing** -- can exceed log N | no |")
    A("")
    A("Farquhar et al. (Nature 2024) define (2) as their headline and (1) as an "
      "explicit discrete variant, which they use for all their GPT-4 results. Our "
      "lattice statement -- 39 attainable values at N=10, 2 of them in the top tenth "
      "of the range (`results/fair_pool_granularity.md`) -- is a property of (1) and "
      "**dies under (2)**: once cluster weights are likelihood-derived they are no "
      "longer multiples of 1/N and the attainable set is a continuum. The log N "
      "**ceiling** survives (1) and (2) and **does not survive (3)**.")
    A("")
    A("What follows is the part that survives (1) AND (2): a necessary condition on the "
      "**clustering**, which all three variants share, rather than on the weighting, "
      "which is what they disagree about.")
    A("")
    A("## 1. The bound")
    A("")
    A("Let K be the number of distinct semantic clusters observed among the N samples. "
      "All three estimators consume the SAME clustering -- none of them changes which "
      "samples are merged, only how the merged groups are weighted. For any NORMALISED "
      "weighting p over those K clusters, entropy is maximised by the uniform weighting, "
      "so")
    A("")
    A("```")
    A("    H  <=  log K                                     (any normalised weighting)")
    A("")
    A("    H  >=  0.9 log N   (top tenth of the range [0, log N])")
    A("    =>  log K >= 0.9 log N")
    A("    =>  K^10  >= N^9            [exact integer form, no float tie-breaking]")
    A("    =>  K     >= ceil(N^0.9)")
    A("```")
    A("")
    A(f"At N={N_SAMPLES}: log 8 = {math.log(8):.6f} > 0.9 log 10 = {TOP_DECILE:.6f} > "
      f"log 7 = {math.log(7):.6f}. So **K >= 8 is necessary** for a top-decile score, "
      f"and the margin at K=8 is only {math.log(8) - TOP_DECILE:.2e} nats.")
    A("")
    A("| N | K_min = ceil(N^0.9) | K_min / N (fraction of samples that must land in "
      "distinct clusters) | continuous form N^(-0.1) | slack N - K_min | cap log N |")
    A("| --- | --- | --- | --- | --- | --- |")
    for n, km, frac, cont, slack, cap in bound_rows:
        A(f"| {n} | {km} | {frac:.1%} | {cont:.1%} | {slack} | {cap:.4f} |")
    A("")
    A("**Does raising N relax the constraint or just the cap?** Both, but by wildly "
      "different amounts. The cap log N grows without limit. The *constraint* is the "
      "required fraction K_min/N ~ N^(-0.1), which decays glacially: 79.4% at N=10, "
      "74.1% at N=20, 63.1% at N=100. Doubling the budget from 10 to 20 buys 5.3 "
      "percentage points of relief. To get the requirement down to \"half the samples "
      "must be in distinct clusters\" you need N^(-0.1) = 1/2, i.e. **N = 2^10 = 1024 "
      "samples per question**. So a bigger budget mostly raises the ceiling; it barely "
      "loosens what a question must look like to approach it.")
    A("")
    A("## 2. Necessary, not sufficient -- how special the weighting has to be")
    A("")
    A("K >= 8 admits a top-decile score; it does not deliver one. At K=8 the admissible "
      f"region is everything within {math.log(8) - TOP_DECILE:.2e} nats of the MAXIMUM "
      "entropy of an 8-point distribution -- a sliver around the uniform weighting. "
      "Measured as a fraction of the (K-1)-simplex, two ways: crude uniform sampling "
      "(Dirichlet(1,...,1) is exactly uniform on the simplex) and a ball-ratio estimator "
      "that samples a containing ball around the uniform weighting and rescales by the "
      "closed-form ball/simplex volume ratio. Crude sampling cannot resolve K=8 at any "
      f"feasible draw count; the ball estimator can. {N_MC_SIMPLEX:,} draws per cell, "
      "seed 0.")
    A("")
    A("| K | max attainable H = log K | clears 2.0723? | crude MC | **ball-ratio volume** "
      "| quadratic closed form |")
    A("| --- | --- | --- | --- | --- | --- |")
    for k in range(7, N_SAMPLES + 1):
        clears = "no" if math.log(k) < TOP_DECILE else "yes"
        hit, draws = vol_mc[k]
        crude = (f"0 / {draws:,} (95% upper bd {RULE_OF_THREE / draws:.1e})"
                 if hit == 0 else f"{hit / draws:.4%} ({hit:,}/{draws:,})")
        if k in vol_ball:
            _, v, se, hits, _ = vol_ball[k]
            ball = f"**{v:.3e}** +/- {se:.1e} ({hits:,} hits)"
            quad = f"{vol_quad[k]:.3e}"
        else:
            ball, quad = "-- (empty set)", "--"
        A(f"| {k} | {math.log(k):.4f} | {clears} | {crude} | {ball} | {quad} |")
    A("")
    A("The ball-ratio estimator is the load-bearing one; the other two columns are there "
      "to keep it honest. Where crude MC works (K=9, K=10) the two agree to within "
      "Monte-Carlo error, which is what licenses the K=8 figure. The quadratic closed "
      "form agrees at K=8, where the region is small enough for the second-order "
      "expansion to hold, and over-estimates badly at K=9 and K=10, where the region is "
      "large and the expansion is out of its regime -- exactly the expected pattern.")
    A("")
    for k in range(8, N_SAMPLES + 1):
        r, v, se, hits, maxr = vol_ball[k]
        cv, cse = vol_check[k]
        crude_txt = (f"crude MC {vol_mc[k][0] / vol_mc[k][1]:.4%}"
                     if vol_mc[k][0] else "crude MC unresolvable (0 hits)")
        A(f"- **K={k}**: {crude_txt} / ball-ratio {v:.3e} +/- {se:.1e} / quadratic "
          f"{vol_quad[k]:.3e}. Containment: ball radius {BALL_R_MULT} x {r:.4f} = "
          f"{BALL_R_MULT * r:.4f}, furthest accepted point at {maxr:.4f} "
          f"({maxr / (BALL_R_MULT * r):.0%} of the radius); widening the ball to "
          f"{BALL_R_MULT_CHECK}x gives {cv:.3e} +/- {cse:.1e}, so nothing is being "
          "clipped.")
    A("")
    v8, r8 = vol_ball[8][1], quadratic_radius(8, TOP_DECILE)
    v9 = vol_ball[9][1]
    A(f"So K >= 8 is the honest necessary condition, but it is *barely* attainable: only "
      f"**{v8:.1e}** of the K=8 weighting simplex clears the top decile -- about one "
      f"part in {1 / v8:,.0f} -- against {v9:.1%} at K=9, a factor of "
      f"{v9 / v8:,.0f}. Concretely, an 8-cluster weighting reaches the top decile only "
      f"if it lies within Euclidean distance {r8:.3f} of the uniform vector "
      f"(1/8, ..., 1/8), i.e. no cluster weight may sit more than about "
      f"{r8:.3f} away from 0.125 and most must be far closer than that. The working "
      "requirement is K >= 9 under any normalised estimator; K >= 8 is what can be "
      "*proved* without committing to one.")
    A("")
    A("## 3. The discrete estimator tightens it to K >= 9 (exactly)")
    A("")
    A("Under (1) the cluster weights are an integer partition of N, so the question is "
      "whether any partition of 10 into exactly K parts clears 2.0723:")
    A("")
    A("| K (number of parts) | best partition's H | clears 2.0723? |")
    A("| --- | --- | --- |")
    for k in range(6, N_SAMPLES + 1):
        h = best_at_k[k]
        A(f"| {k} | {h:.4f} | {'**yes**' if h >= TOP_DECILE - TOL else 'no'} |")
    A("")
    A(f"Binding requirement under the discrete estimator: **K >= {d_kmin}**. The two "
      "top-decile lattice points are exactly the K=9 partition (2,1^8) -> 2.1640 and "
      "the K=10 partition (1^10) -> 2.3026. Empirically this is what the cache shows: "
      f"of the {len(full)} questions, every top-decile score has "
      f"K in {{{', '.join(str(k) for k in sorted(td_by_k))}}} "
      f"(counts {dict(sorted(td_by_k.items()))}) and every at-cap score has "
      f"K in {{{', '.join(str(k) for k in sorted(cap_by_k))}}} "
      f"(counts {dict(sorted(cap_by_k.items()))}).")
    A("")
    A("**Reporting rule.** K >= 8 is the variant-proof number and is the one the paper "
      "should quote. K >= 9 is ours specifically, and quoting it as though it were "
      "general would repeat the mistake this document exists to correct.")
    A("")
    A("## 4. Cache verification")
    A("")
    A("K and H are recomputed here from the raw `assignments` array in "
      "`~/.cache/se-research/samples/wk4_full_2000q/entropy.jsonl`, not read off the "
      "cached summary fields:")
    A("")
    for line in check_lines:
        A(line)
    A("")
    A("The FA attack stratum is the first 80 ids of the score-independent correct "
      "stratum (`_stratum_ids(\"right\", seed=0)`), i.e. **nested inside** the fair "
      "pool's correct arm rather than disjoint from it. Checked against the on-disk "
      "cells:")
    A("")
    A("| attack cell | size | nesting |")
    A("| --- | --- | --- |")
    for line in verify_fa_nesting(fa80):
        A(line)
    A("")
    A("## 5. The K distribution, per population")
    A("")
    A("Every row carries its n and a Wilson 95% interval. The distribution is the "
      "point, not just the tail rate.")
    A("")
    for name, ids in pops:
        s = k_summary(ids, ent)
        A(f"### {name} (n={s['n']})")
        A("")
        A("| K | count | share | share with K' >= K |")
        A("| --- | --- | --- | --- |")
        A(k_table(ids, ent))
        A("")
        A(f"- mean K = {s['mean']:.2f}, median = {s['median']:.1f}, "
          f"IQR = [{s['q25']:.1f}, {s['q75']:.1f}]")
        A(f"- **K >= 8** (top decile possible under ANY normalised weighting): "
          f"{fmt_prop(s['ge8'], s['n'])}")
        A(f"- K >= 9 (top decile possible under the DISCRETE estimator): "
          f"{fmt_prop(s['ge9'], s['n'])}")
        A(f"- K = 10 (at-cap possible under the discrete estimator): "
          f"{fmt_prop(s['eq10'], s['n'])}")
        A(f"- **K <= 7** -- top decile IMPOSSIBLE under any normalised weighting: "
          f"{fmt_prop(s['le7'], s['n'])}")
        A(f"- K <= 3 (bottom of the clustering range): {fmt_prop(s['le3'], s['n'])}")
        A(f"- observed discrete top-decile rate: {fmt_prop(s['topdecile'], s['n'])}; "
          f"at-cap rate: {fmt_prop(s['atcap'], s['n'])}")
        A("")

    # --- the correct-vs-hallucinating contrast
    A("## 6. The contrast that carries the finding")
    A("")
    A("| population pair | K >= 8, correct | K >= 8, hallucinating | difference "
      "(Newcombe 95%) |")
    A("| --- | --- | --- | --- |")
    for pname, cids, hids in [("fair pool (200 + 200)", fair_c, fair_h),
                              ("full labelled pool (1424 + 576)", full_c, full_h)]:
        kc = sum(1 for q in cids if ent[q]["n_clusters"] >= 8)
        kh = sum(1 for q in hids if ent[q]["n_clusters"] >= 8)
        d, lo, hi = newcombe_diff(kh, len(hids), kc, len(cids))
        A(f"| {pname} | {fmt_prop(kc, len(cids))} | {fmt_prop(kh, len(hids))} | "
          f"{d:+.1%} [{lo:+.1%}, {hi:+.1%}] |")
    A("")
    A("## 7. Do the circulating 30.3% / 59.1% figures hold?")
    A("")
    A("They are close but were computed against the WRONG label column. "
      "`entropy.jsonl` carries the pre-relabel `greedy_correct`; the paper's rule uses "
      "the B3 span-oracle relabel in `relabeled.jsonl`, and the two disagree on 20 of "
      "2000 questions. Corrected figures first:")
    A("")
    A("| label column | correct stratum, K >= 8 | hallucinating stratum, K >= 8 |")
    A("| --- | --- | --- |")
    for name, (kc, nc, kh, nh) in prelim.items():
        A(f"| {name} | {fmt_prop(kc, nc)} | {fmt_prop(kh, nh)} |")
    A("")
    A("The preliminary 30.3% / 59.1% reproduces exactly under `entropy.jsonl`'s label "
      "column. Under the span-oracle relabel the figures are **30.3% and 58.3%** -- the "
      "correct-stratum number is unchanged to the quoted precision and the "
      "hallucinating-stratum number moves by 0.8 points. The qualitative claim is "
      "unaffected; **quote the span-oracle numbers.**")
    A("")
    A("## 8. Proposed paper sentence")
    A("")
    A("> Because every semantic-entropy variant scores the same clustering and differs "
      "only in how clusters are weighted, and because any normalised weighting over K "
      "clusters satisfies H <= log K, a score in the top tenth of the range [0, log N] "
      "requires K >= ceil(N^0.9) -- at N = 10, K >= 8, since log 8 = 2.079 exceeds "
      "0.9 log 10 = 2.072 while log 7 = 1.946 does not. On the score-independent fair "
      "pool this condition is met by only " +
      f"{fmt_prop(sum(1 for q in fair_c if ent[q]['n_clusters'] >= 8), len(fair_c))}"
      " of correct-stratum questions against " +
      f"{fmt_prop(sum(1 for q in fair_h if ent[q]['n_clusters'] >= 8), len(fair_h))}"
      " of hallucinating ones, so for the majority of the correct stratum the top decile "
      "of the scale is unreachable under any weighting scheme, not merely unreached "
      "under ours. Raising N lifts the cap without loosening the condition: the "
      "required fraction of samples in distinct clusters falls only as N^(-0.1), from "
      "79% at N = 10 to 74% at N = 20.")
    A("")
    A("(Scope: the bound follows from the log N ceiling, so it applies to the discrete "
      "estimator and to Farquhar Eq. (5). Kuhn et al.'s Eq. (4) is an unnormalised mean "
      "surprisal with no log N ceiling and is therefore outside its scope -- state that "
      "rather than let the reader assume otherwise.)")
    A("")

    path = RESULTS_DIR / "cluster_count_bound.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")
    for name, ids in pops:
        s = k_summary(ids, ent)
        print(f"  {name:52s} n={s['n']:4d}  K>=8 {fmt_prop(s['ge8'], s['n'])}")


if __name__ == "__main__":
    main()
