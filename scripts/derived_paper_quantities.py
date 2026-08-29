"""Every DERIVED number the paper quotes that had no producing artifact.

WHY THIS SCRIPT EXISTS. A provenance sweep of paper/*.tex against results/ and docs/ found a
residue of numbers that are arithmetic on sourced inputs but appear, as printed, nowhere
outside the .tex: the censoring bias-bound chain in discussion.tex (2.6% of pairs -> 0.013,
against a 0.050 half-width, and the 2.9x counterfactual), and the headroom / step-size
figures in methods.tex (0.923 nats, 0.277 nats, 1/30). "Derivable" is not "reproducible":
nobody could check the arithmetic without redoing it, and the one place a factor of 1/2 was
doing real work -- the bias bound -- was nowhere written down. This computes each of them
from its inputs and states the derivation.

TWO GUARDS, AND THE SECOND ONE IS NEW (2026-08-19).

  INPUT GUARD. Every input carries the artifact it comes from and a literal that must still
  appear in that artifact. If an upstream number is revised and this script is not, it FAILS
  rather than quietly recomputing a stale chain.

  PAPER GUARD (new). Every "the paper says X" in this script used to be a hard-coded string
  in a dict called PAPER, checked against nothing. That is the same defect the script exists
  to close, one level up: the claim side was unverifiable. On 2026-08-19 the check was found
  green while asserting that experiments.tex says "roughly nine GPU-days" -- a phrase that
  file had not contained for five days. Every paper-side number is now a PaperClaim carrying
  the literal the .tex must still print, matched on whitespace-normalised text so that a
  reflow of the paragraph is not a failure but a rewording of the number is.

WHAT A FAILURE MEANS. Both guards collect rather than abort, so one stale literal cannot hide
the rest of the report; the run exits non-zero with every problem listed. A paper-side miss
can also be a RACE -- paper/ is edited concurrently -- so the report prints each .tex file's
size and digest at check time, and a miss should be re-checked against the file before it is
believed.

    .venv/Scripts/python.exe scripts/derived_paper_quantities.py
"""
from __future__ import annotations

import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from se.config import RESULTS_DIR                          # noqa: E402

PROBLEMS: list[str] = []
# Claim key -> the number of decimal places the comparison was made to, for every claim a
# derivation actually recomputed (as opposed to merely pinning its literal). Repopulated by
# every main(). The mutation tests read the dp so they can perturb by exactly one unit in the
# last place the check looks at -- a smaller nudge would pass and prove nothing.
EXERCISED: dict[str, int] = {}


def _norm(s: str) -> str:
    """Whitespace-normalised text. A LaTeX paragraph reflow moves a number across a line
    break without changing it; that must not read as a revision."""
    return " ".join(s.split())


def _read(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        PROBLEMS.append(f"missing source {rel}")
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Input:
    """A number lifted from an artifact, with the literal that must still be there."""
    name: str
    value: float
    literal: str
    source: str
    note: str = ""            # provenance tag, for the operational-figure checker

    def check(self) -> None:
        text = _read(self.source)
        if text and _norm(self.literal) not in _norm(text):
            PROBLEMS.append(
                f"INPUT '{self.name}': {self.source} no longer contains {self.literal!r}. "
                f"The upstream artifact changed; re-derive rather than trusting this script.")


@dataclass(frozen=True)
class PaperClaim:
    """A number the PAPER prints, with the literal paper/ must still contain.

    `present=False` inverts it: the literal must be ABSENT. That is how a retired number is
    held down -- the 1440-vs-1424 oracle mix-up below was fixed in the .tex, and the only way
    to keep it fixed is to fail if 1440 comes back."""
    name: str
    value: float
    literal: str
    source: str
    present: bool = True
    note: str = ""            # provenance tag, for the operational-figure checker

    def check(self) -> None:
        text = _read(self.source)
        if not text:
            return
        found = _norm(self.literal) in _norm(text)
        if found is not self.present:
            verb = "no longer contains" if self.present else "contains again"
            PROBLEMS.append(
                f"PAPER '{self.name}': {self.source} {verb} {self.literal!r}. "
                f"Either the paper was reworded (update this script) or the number moved "
                f"(re-derive). paper/ is edited concurrently -- re-check before believing it.")


# ======================================================================================
# INPUTS -- artifact-sourced
# ======================================================================================
INPUTS = [
    Input("mean clean entropy, correct answers, fair pool", 1.380,
          "| right | fair pool | 1.380", "results/fair_pool_report.md"),
    Input("mean clean entropy, wrong answers, fair pool", 1.843,
          "| wrong | fair pool | 1.843", "results/fair_pool_report.md"),
    Input("K=8 lattice point (next attainable value below the cap)", 2.0253,
          "2.0253", "results/cluster_count_bound.md"),
    Input("hallucinating answers at the ceiling, fair pool", 55 / 200,
          "55/200 = 27.5%", "results/achievable_fpr_grid.md"),
    Input("correct answers at the ceiling, fair pool", 19 / 200,
          "19/200 = 9.5%", "results/achievable_fpr_grid.md"),
    Input("clean fair-pool AUROC and CI", 0.704,
          "0.704 [0.653, 0.753]", "results/fair_pool_report.md"),
    # Repointed 2026-08-29. This INPUT is the K of the n=6 machinery-validation pass,
    # which is what methods.tex's 1/30 step is computed from. Its old source,
    # results/null_control_report.md, was regenerated by aa6fb9d for the DEFINITIVE
    # K=50 campaign, so the K=5 string legitimately vanished from it and this guard
    # went red -- correctly, because a source file had been swapped underneath an
    # anchor. The fact did not change; the file holding it did.
    Input("null-control benign draws per target (K)", 5,
          "K=5 benign", "results/null_control_3arm_judge_n6.md"),
    Input("greedy-correct count, SUBSTRING oracle", 1440,
          "old correct rate: 1440/2000", "results/relabel_report.md"),
    Input("greedy-correct count, SPAN oracle", 1424,
          "new correct rate: 1424/2000", "results/relabel_report.md"),

    # -- the repaired cost chain (2026-08-19) -------------------------------------------
    # The old input was Input(..., 228, "228 GPU-h", "docs/critique_log.md"): a MODELLED
    # figure sourced to a LOG ENTRY rather than to an artifact, and dead since the deployed
    # run measured its unit. The three inputs below are the live chain.
    Input("judge evaluations per target at K=180", 185,
          "185 evaluations/target", "results/operational_number_audit.md"),
    Input("measured seconds per clustering, deployed run", 24.0,
          "the measured 24.0 s/clustering from the deployed run",
          "results/operational_number_audit.md",
          note="MEASURED on the deployed run, same symmetric judge, `judge_batch_size` 6, "
               "N=10"),
    Input("retired entry-22 price of the judge arm, GPU-hours", 227.8,
          "| judge arm, K=180, n=80 | 227.8 GPU-h", "results/operational_number_audit.md",
          note="MODELLED from the 55 s unit of `docs/critique_log.md` 22 at K=180, n=80; superseded"),
    Input("re-priced judge arm, GPU-hours (cross-check)", 98.7,
          "**98.7 GPU-h — 4.1 GPU-days**", "results/operational_number_audit.md",
          note="MEASURED, re-derived from the 24.0 s/clustering unit above"),

    # -- the N=40 budget row, and the operating points on it ----------------------------
    Input("clean correct answers at the ln 40 cap, fair pool", 0,
          # Narrowed 2026-08-19 to the at-cap cell only. The rest of that row in
          # `post_overnight_claim_review.md` reads "**4/200 = 2.0% [0.8, 5.0]**", and
          # that interval is WITHDRAWN -- pinning it here would have this report quote a
          # retired number forward under the heading "artifact-sourced". The review file
          # itself is a timestamped record of what was believed at 03:55 and is left
          # alone deliberately: rewriting it would destroy the audit trail, and it is not
          # in the quotable set.
          "| N=40 measured | 0/200 = 0.0% [0.0, 1.9] |",
          "results/post_overnight_claim_review.md"),
    # The literal moved on 2026-08-19 when that row's interval was WITHDRAWN. It is
    # pinned on the withdrawal, not merely on the count, so that this guard fires if an
    # interval is put back beside the 2.0%.
    Input("clean correct answers above the cheapest firing threshold, N=40", 4,
          "| measured N=40 | 2.0% | **none -- withdrawn, see 2c** |",
          "results/replay_control.md"),
    Input("hallucinating answers caught at that threshold, N=40 (rate)", 6.0,
          "| 40 | 1% | 0.0% (flags nothing) | 0.0% | 2.0% **over budget** | 6.0% |",
          "results/n_scaling_grid.md"),
    Input("achieved false-alarm rate at a 5% budget, N=40 (rate)", 5.0,
          "| 40 | 5% | 5.0% | 11.0% | 5.0% | 11.0% |", "results/n_scaling_grid.md"),
    Input("count behind that achieved 5.0%", 10,
          "It is 10/200 on the fair pool's correct stratum; Wilson",
          "results/gate_paper_edits_2026_08_19.md"),

    # -- the replay floors and the variance decomposition -------------------------------
    Input("subset-averaged replay floor at N=10 (percent)", 11.974,
          "| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |",
          "results/replay_control.md"),
    Input("subset-averaged replay floor at N=20 (percent)", 3.134,
          "| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |",
          "results/replay_control.md"),

    # THE EXACT FLOORS, and why both these and the Monte-Carlo pair above are registered.
    # The two rows above are a 40,000-draw Monte Carlo over subsets. `p_at_cap()` in
    # `scripts/make_floor_budget_figure.py` computes the same quantities EXACTLY -- "all
    # singletons" is "the subset is an independent set of the verdict graph", so it is a
    # ratio of independent-set counts and there is nothing to sample -- and section 2c of
    # `results/replay_control.md` prints the exact values beside its own MC ones.
    #
    # THEY DISAGREE IN A PLACE THAT MATTERS. 11.974 - 3.134 = 8.840, which rounds to 8.8.
    # 11.9921 - 3.1291 = 8.8630, which rounds to 8.9, and 8.9 is what the paper prints.
    # The MC pair is fine for every other quantity here (the N=10 -> N=40 fall lands on
    # 10.0 either way), but on the 10 -> 20 leg it straddles the decimal the paper quotes.
    # Deriving that leg from the MC floors would make this script report the paper as
    # wrong -- which has already been attempted once, on the strength of two artifacts
    # agreeing while both were reading the same Monte-Carlo error.
    Input("exact replay floor at N=10 (percent)", 11.9921,
          "Exact: N=10 floor 11.9921%, N=20 floor 3.1291%",
          "results/replay_control.md",
          note="EXACT, by independent-set counting; not the 40k-draw MC row above"),
    Input("exact replay floor at N=20 (percent)", 3.1291,
          "Exact: N=10 floor 11.9921%, N=20 floor 3.1291%",
          "results/replay_control.md",
          note="EXACT, by independent-set counting; not the 40k-draw MC row above"),
    Input("exact 10 -> 20 paired floor leg (points)", -8.8630,
          "a 10 -> 20 paired leg of -8.8630",
          "results/replay_control.md",
          note="EXACT; the report's own MC rendering of this leg is -8.8 and is marked "
               "as MC in its differences table"),
    Input("N=10 question component, sd in rate points", 1.6346,
          "| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |",
          "results/replay_control.md"),
    Input("N=10 subset-draw component, sd in rate points", 1.6119,
          "| N=10 | 11.974% | 1.6346 | 1.6119 | 2.2957 | 2.2957 |",
          "results/replay_control.md"),
    Input("N=20 question component, sd in rate points", 0.7433,
          "| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |",
          "results/replay_control.md"),
    Input("N=20 subset-draw component, sd in rate points", 0.9826,
          "| N=20 | 3.134% | 0.7433 | 0.9826 | 1.2321 | 1.2321 |",
          "results/replay_control.md"),

    # -- the June/August generation drift ------------------------------------------------
    Input("mean answer length, June direct cache (chars)", 116.0,
          "116.0 chars direct vs 119.6 in the checkpoint, paired difference **+3.63 +/- 0.91**",
          "results/replay_control.md"),
    Input("mean answer length, August checkpoint (chars)", 119.6,
          "116.0 chars direct vs 119.6 in the checkpoint, paired difference **+3.63 +/- 0.91**",
          "results/replay_control.md"),
    Input("paired length difference (chars)", 3.63,
          "paired difference **+3.63 +/- 0.91**", "results/replay_control.md"),
    Input("paired length difference, standard error (chars)", 0.91,
          "paired difference **+3.63 +/- 0.91**", "results/replay_control.md"),
    Input("paired terminal-punctuation difference (fraction)", 0.0163,
          "0.738 vs 0.722, paired -0.0163 +/- 0.0071", "results/replay_control.md"),

    # -- goodness of fit ------------------------------------------------------------------
    Input("cluster-count chi-square, correct stratum, k=10", 7.39,
          "| correct, direct | 11 | 17 | 27 | 18 | 27 | 24 | 18 | 15 | 24 | 19 | 7.39 | 9 | 0.60 |",
          "results/replay_control.md"),
    Input("its degrees of freedom", 9,
          "| correct, direct | 11 | 17 | 27 | 18 | 27 | 24 | 18 | 15 | 24 | 19 | 7.39 | 9 | 0.60 |",
          "results/replay_control.md"),
    Input("exact Poisson-binomial P(X <= 19), producing implementation", 0.081,
          "P(X <= 19) = 0.081", "results/replay_control.md"),
    Input("the same p, independent reimplementation", 0.083,
          "| exact Poisson-binomial P(X ≤ 19) | **0.081** | **0.083** | yes |",
          "results/gate_paper_edits_2026_08_19.md"),
]

# ======================================================================================
# PAPER CLAIMS -- what paper/ prints today, each pinned to its literal
# ======================================================================================
DISC = "paper/sections/discussion.tex"
METH = "paper/sections/methods.tex"
EXPT = "paper/sections/experiments.tex"
LIMS = "paper/sections/limitations.tex"
MAIN = "paper/main.tex"
INTRO = "paper/sections/introduction.tex"
CONCL = "paper/sections/conclusion.tex"

CLAIMS = {c.name: c for c in [
    # -- methods.tex: headroom -----------------------------------------------------------
    PaperClaim("headroom_correct", 0.923, r"$0.923$ nats to the ceiling", METH),
    PaperClaim("headroom_next_lattice", 0.277,
               r"the next lattice point down, $2.025$, still leaves $0.277$ nats", METH),
    PaperClaim("arm_step", 1 / 30, r"moves in steps of roughly $1/30$", METH),

    # -- discussion.tex: the censoring bias bound -----------------------------------------
    PaperClaim("pinned_pair_fraction", 0.026,
               r"That is $0.275 \times 0.095 = 2.6\%$ of pairs,", DISC),
    PaperClaim("bias_bound", 0.013, r"bounding the downward bias at $0.013$", DISC),
    PaperClaim("ci_half_width", 0.050, r"a confidence half-width of $0.050$", DISC),
    PaperClaim("counterfactual_ratio", 2.9,
               r"$2.9\times$ as many pairs would be affected", DISC),

    # -- experiments.tex: the cost of the matched design ----------------------------------
    PaperClaim("gpu_hours_retired", 228, r"$228$ GPU-hours", EXPT,
               note="MODELLED from the 55 s unit of `docs/critique_log.md` 22 at K=180, n=80; superseded; the paper names it only to correct it"),
    PaperClaim("gpu_hours_repriced", 99, r"about $99$ GPU-hours", EXPT,
               note="MEASURED, re-derived from the 24.0 s/clustering unit"),
    PaperClaim("gpu_trigger_ratio", 2.3, r"$2.3\times$ too large", EXPT),
    # The phrase this script used to verify, and the reason the paper guard exists.
    PaperClaim("gpu_days_retired_phrase", 0, "roughly nine GPU-days", EXPT, present=False),

    # -- discussion.tex: the N=40 operating points ----------------------------------------
    PaperClaim("n40_atcap", 0.0, r"$0.0\%$ [$0.0$, $1.9$]", DISC),
    PaperClaim("n40_atcap_hi", 1.9, r"$0.0\%$ [$0.0$, $1.9$]", DISC),
    PaperClaim("n40_floor", 2.0, r"a measured $2.0\%$ at $N{=}40$", DISC),

    # THE N=40 FLOOR PRINTS NO INTERVAL, AND THAT IS THE FINDING, NOT AN OMISSION.
    # The reason is NON-IDENTIFICATION and it needs no model: once the ceiling atom
    # empties, "the floor" is the multiplicity of whichever rung this pool happened to
    # reach, and whether that rung is the top of the population's support cannot be
    # decided at n=200. If it is, 2.0% is an ordinary population proportion; if it is
    # not, the true floor is arbitrarily smaller. Two orders of magnitude apart, on a
    # hypothesis the sample cannot test -- so no interval prices it.
    #
    # THE COVERAGE FIGURES ARE BRANCH-CONDITIONAL. Do not quote either pair without its
    # population (`results/n40_floor_estimator_ruling.md` sec. 8.4, nominal 95%):
    #   calibrated Ewens (tau_top = 0.2726%): Wilson [0.78, 5.03] 53.67%, bootstrap 0.00%
    #   zero branch      (tau*     = 2.0%):   Wilson 95.06%,             bootstrap 100%
    # This comment used to give the first pair alone and conclude "the ESTIMAND breaks";
    # sec. 13 retracts that phrasing -- it is true only in the first branch, and the data
    # does not exclude the second (p=0.1175 for the fitted model against 0/200).
    # The interval the paper does print at N=40 is the at-cap mass above, whose
    # threshold (ln 40) is fixed a priori and is valid in BOTH branches.
    #
    # Four retired literals, held down at every site each one occupied, because this row
    # has already been "corrected" in one file at a time twice tonight. A bare "5.03" is
    # pinned as well as the bracketed forms: the whole concession used to turn on that one
    # digit, and it must not come back in any markup.
    PaperClaim("n40_floor_wilson_retired_disc", 5.03, r"[$0.78$, $5.03$]", DISC,
               present=False),
    PaperClaim("n40_floor_boot_retired_disc", 4.0, r"[$0.5$, $4.0$]", DISC, present=False),
    PaperClaim("n40_floor_503_retired_disc", 5.03, "5.03", DISC, present=False),
    PaperClaim("n40_floor_wilson_retired_main", 5.03, r"[$0.8$, $5.03$]", MAIN,
               present=False),
    PaperClaim("n40_floor_503_retired_main", 5.03, "5.03", MAIN, present=False),
    PaperClaim("n40_floor_wilson_retired_concl", 5.03, r"[$0.8$, $5.03$]", CONCL,
               present=False),
    PaperClaim("n40_floor_503_retired_concl", 5.03, "5.03", CONCL, present=False),
    PaperClaim("n40_floor_rounded_retired_intro", 5.0, r"[$0.8$, $5.0$]", INTRO,
               present=False),

    # The at-cap bound is now load-bearing in three more files than it was, because it is
    # what the concession rests on. Pin it where it is quoted.
    PaperClaim("n40_atcap_hi_main", 1.9, r"($0/200$, at most $1.9\%$)", MAIN),
    PaperClaim("n40_atcap_intro", 0.0, r"$0.0\%$ [$0.0$, $1.9$]", INTRO),
    PaperClaim("n40_atcap_concl", 0.0, r"$0.0\%$ [$0.0$, $1.9$]", CONCL),
    PaperClaim("n40_tpr", 6.0, r"$6.0\%$ [$3.5$, $10.2$]", DISC),
    PaperClaim("n40_tpr_lo", 3.5, r"$6.0\%$ [$3.5$, $10.2$]", DISC),
    PaperClaim("n40_tpr_hi", 10.2, r"$6.0\%$ [$3.5$, $10.2$]", DISC),
    PaperClaim("n40_achieved", 5.0, r"an achieved $5.0\%$ [$2.7$, $9.0$]", DISC),
    PaperClaim("n40_achieved_lo", 2.7, r"an achieved $5.0\%$ [$2.7$, $9.0$]", DISC),
    PaperClaim("n40_achieved_hi", 9.0, r"an achieved $5.0\%$ [$2.7$, $9.0$]", DISC),

    # -- discussion.tex: the fall across the budget ---------------------------------------
    PaperClaim("replay10_floor", 12.0,
               r"falls from a replayed $12.0\%$ [$8.9$, $15.3$] at $N{=}10$", DISC),
    PaperClaim("fall_points", 10.0, r"$10.0$ points [$7.2$, $12.9$]", DISC),

    # THE TWO LEGS, registered 2026-08-19. Until now the end-to-end fall was pinned here
    # and the two legs it decomposes into were not, so their only hold anywhere in the repo
    # was `figures/fig_floor_budget_stats.json` -- a file the paper is checked AGAINST but
    # which no test compares to the .tex. The 8.9 is the one to be careful with: it is
    # CORRECT, the exact leg is -8.8630, and the -8.8 that appears in
    # `results/replay_control.md` is Monte-Carlo error, now marked as such in that file's
    # own differences table. Do not "correct" the paper down to match it.
    PaperClaim("leg_10_20_points", 8.9, r"$8.9$ points [$6.8$, $11.1$]", DISC),
    PaperClaim("leg_20_40_points", 1.1, r"$1.1$ points [$-0.2$, $2.4$]", DISC),
    # ...and the MC renderings of that same leg, held down by ABSENCE, because "correct the
    # paper to match the artifact" is the specific move that has to be prevented here.
    PaperClaim("leg_10_20_mc_retired", 8.8, "8.8", DISC, present=False),
    PaperClaim("leg_10_20_mc_ci_retired", 11.0, r"[$6.8$, $11.0$]", DISC, present=False),
    # The retired replay family, held down as bare digits rather than as LaTeX. The whole
    # trio 11.9 / 3.0 / 2.0 and its fall of 9.9 [15.5, 5.0] came off an average over 200 whole
    # replicates and was replaced by the per-question mean; none of these five strings occurs
    # in discussion.tex today, and each is registered so that it cannot come back in ANY
    # markup. A guard written as `$9.9$ points` would have missed `9.9~points`.
    PaperClaim("fall_points_retired", 9.9, "9.9", DISC, present=False),
    PaperClaim("replay10_floor_retired", 11.9, "11.9", DISC, present=False),
    PaperClaim("replay20_floor_retired", 3.0, "3.0", DISC, present=False),
    PaperClaim("fall_ci_lo_retired", 15.5, "15.5", DISC, present=False),

    # -- discussion.tex: the variance decomposition ---------------------------------------
    PaperClaim("sd20_subset", 0.98,
               r"$0.98$ and $0.74$ points against a binomial $1.23$", DISC),
    PaperClaim("sd20_question", 0.74,
               r"$0.98$ and $0.74$ points against a binomial $1.23$", DISC),
    PaperClaim("sd20_binomial", 1.23,
               r"$0.98$ and $0.74$ points against a binomial $1.23$", DISC),
    PaperClaim("sd10_subset", 1.61, r"$1.61$ and $1.63$ against $2.30$", DISC),
    PaperClaim("sd10_question", 1.63, r"$1.61$ and $1.63$ against $2.30$", DISC),
    PaperClaim("sd10_binomial", 2.30, r"$1.61$ and $1.63$ against $2.30$", DISC),

    # -- discussion.tex: the June/August drift ---------------------------------------------
    PaperClaim("drift_chars", 3.6, r"about $3.6$ characters", DISC),
    PaperClaim("drift_z", 4.0, r"($z{=}+4.0$)", DISC),
    PaperClaim("drift_punct_points", 1.6, r"$1.6$ points less often", DISC),

    # -- discussion.tex: goodness of fit ----------------------------------------------------
    PaperClaim("poisson_binomial_p", 0.081, r"$p{=}0.081$", DISC),
    PaperClaim("chisq_p", 0.60, r"$p{=}0.60$", DISC),

    # -- limitations.tex: the oracle mix-up, now fixed and held down ------------------------
    PaperClaim("span_oracle_count", 1424, r"$1424$ greedy-correct questions", LIMS),
    PaperClaim("substring_oracle_count_absent", 1440, "1440", LIMS, present=False),
]}

CAP = math.log(10)
N_STRATUM = 200                 # fair pool: 200 correct + 200 hallucinating
N_TARGETS_NULL_CONTROL = 6      # the n=6 machinery pass
N_JUDGE_TARGETS = 80            # the matched design's n
AUROC_LO, AUROC_HI = 0.653, 0.753
PINNED_HALLUCINATING = 55
PINNED_CORRECT = 19
Z95 = 1.959963985


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval, in percent. Every count-based interval the paper prints on the
    fair pool's 200 is this function; the paper says so, and this is where it is checkable."""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z / d * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) * 100, (c + h) * 100


def chisq_sf(x: float, df: int) -> float:
    """Upper tail of chi-square. Kept dependency-free on purpose: this file is a checker and
    must not fail to run because an environment lost scipy."""
    from math import erfc, exp, lgamma, log, sqrt
    if x <= 0:
        return 1.0
    if df == 2:
        return exp(-x / 2)
    if df == 1:
        return erfc(sqrt(x / 2))
    # Regularised upper incomplete gamma Q(a, s) with a = df/2, s = x/2.
    a, s = df / 2.0, x / 2.0
    if s < a + 1.0:                                   # series for P, then Q = 1 - P
        term = 1.0 / a
        total = term
        n = a
        for _ in range(10000):
            n += 1.0
            term *= s / n
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        return 1.0 - total * exp(-s + a * log(s) - lgamma(a))
    b = s + 1.0 - a                                   # Lentz continued fraction for Q
    c_ = 1e300
    d_ = 1.0 / b
    h = d_
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d_ = an * d_ + b
        if abs(d_) < 1e-300:
            d_ = 1e-300
        c_ = b + an / c_
        if abs(c_) < 1e-300:
            c_ = 1e-300
        d_ = 1.0 / d_
        de = d_ * c_
        h *= de
        if abs(de - 1.0) < 1e-16:
            break
    return h * exp(-s + a * log(s) - lgamma(a))


def main(write: bool = True, quiet: bool = False) -> int:
    # A registered literal carries a U+2264 (`P(X <= 19)` is printed with the real glyph in
    # results/replay_control.md), and a Windows console defaults to cp1252, so the
    # documented regeneration command used to die with UnicodeEncodeError halfway down the
    # INPUTS table -- after the checks had run and before anything was written. The report
    # itself has always been written UTF-8 and the tests run quiet, so only the human path
    # was broken. Failing to PRINT a table is not a reason to fail to WRITE one.
    if not quiet:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):      # not a reconfigurable text stream
                pass
    PROBLEMS.clear()          # main() is called repeatedly by the tests; state must not carry
    EXERCISED.clear()
    for i in INPUTS:
        i.check()
    for c in CLAIMS.values():
        c.check()
    src = {i.name: i.value for i in INPUTS}

    L: list[str] = []

    def log(s: str = "") -> None:
        if not quiet:
            print(s, flush=True)
        L.append(s)

    exercised = EXERCISED

    def row(label: str, derivation: str, value: float, claim_key: str, dp: int = 3) -> bool:
        claimed = CLAIMS[claim_key].value
        exercised[claim_key] = dp
        ok = round(value, dp) == round(claimed, dp)
        log(f"| {label} | {derivation} | {value:.{dp + 1}f} | {claimed:.{dp}f} | "
            f"{'MATCHES' if ok else '**DIFFERS**'} |")
        if not ok:
            PROBLEMS.append(
                f"DERIVATION '{label}': computed {value:.{dp + 1}f}, paper prints "
                f"{claimed:.{dp}f} (claim '{claim_key}').")
        return ok

    log("# Derived quantities the paper quotes, with their arithmetic")
    log("")
    log("Producing script: `scripts/derived_paper_quantities.py`. These are numbers that are")
    log("arithmetic on artifact-sourced inputs but were printed only in the .tex, so no reader")
    log("(and no future run) could check them. Two guards run before any arithmetic: each")
    log("INPUT names the artifact it came from and a literal that must still be there, and")
    log("each PAPER claim names the literal `paper/` must still print. The second guard is new")
    log("on 2026-08-19 and is the one that was missing: this report previously verified that")
    log("`experiments.tex` says \"roughly nine GPU-days\" while that file had not said so for")
    log("five days, because the paper side was a hard-coded dict checked against nothing.")
    log("")
    log("Paper files are edited concurrently. A PAPER miss may be a race; the digests below")
    log("are taken at check time so a miss can be re-checked against the same bytes.")
    log("")
    log("| paper file | bytes | sha256[:12] |")
    log("|---|---|---|")
    for rel in sorted({c.source for c in CLAIMS.values()}):
        b = (ROOT / rel).read_bytes() if (ROOT / rel).exists() else b""
        log(f"| `{rel}` | {len(b)} | `{hashlib.sha256(b).hexdigest()[:12]}` |")
    log("")

    log("## Inputs, and where they come from")
    log("")
    log("| input | value | artifact | literal checked | provenance |")
    log("|---|---|---|---|---|")
    for i in INPUTS:
        log(f"| {i.name} | {i.value} | `{i.source}` | `{i.literal}` | {i.note or '-'} |")
    log("")
    log("## What the paper prints, and where")
    log("")
    log("| claim | value | file | literal | must be | provenance |")
    log("|---|---|---|---|---|---|")
    for c in CLAIMS.values():
        log(f"| {c.name} | {c.value} | `{c.source}` | `{c.literal}` | "
            f"{'present' if c.present else '**absent**'} | {c.note or '-'} |")
    log("")
    log(f"Ceiling: log(10) = {CAP:.6f} nats.")
    log("")

    # ==================================================================================
    log("## methods.tex — headroom to the ceiling")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    h_corr = CAP - src["mean clean entropy, correct answers, fair pool"]
    row("headroom from the correct-answer mean", "log(10) - 1.380", h_corr,
        "headroom_correct")
    h_next = CAP - src["K=8 lattice point (next attainable value below the cap)"]
    row("headroom at the next lattice point down", "log(10) - 2.0253", h_next,
        "headroom_next_lattice")
    h_wrong = CAP - src["mean clean entropy, wrong answers, fair pool"]
    log(f"| (not quoted) headroom from the wrong-answer mean | log(10) - 1.843 | "
        f"{h_wrong:.4f} | - | - |")
    log("")
    log("The second row is the one that carries an argument: the whole gap between the")
    log("correct-answer mean and the cap is 0.923 nats, but the score cannot occupy it")
    log("continuously — the last attainable step below the cap already leaves 0.277 nats, so")
    log("a move smaller than one lattice step is unrepresentable, not merely small.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the censoring bias bound")
    log("")
    log("AUROC is P(score of a hallucinating answer > score of a correct one) with ties at")
    log("1/2, taken over all cross-stratum pairs. min(., log N) is monotone, so censoring")
    log("cannot reorder a pair unless BOTH members are pinned at the cap; such a pair becomes")
    log("a tie and contributes exactly 1/2, whatever it contributed before. The true")
    log("contribution lies in [0, 1], so each affected pair can move the AUROC by at most 1/2 —")
    log("**that factor of 1/2 is the step the paper does not write down**, and it is what")
    log("turns a 2.6% pair fraction into a 0.013 bound rather than a 0.026 one.")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    n_pairs = N_STRATUM * N_STRATUM
    pinned_pairs = PINNED_HALLUCINATING * PINNED_CORRECT
    frac = pinned_pairs / n_pairs
    row("fraction of pairs with both members pinned",
        f"({PINNED_HALLUCINATING}/{N_STRATUM}) x ({PINNED_CORRECT}/{N_STRATUM}) = "
        f"{pinned_pairs}/{n_pairs}", frac, "pinned_pair_fraction")
    row("bound on the downward AUROC bias", "1/2 x 2.6% (a tie contributes 1/2; truth in [0,1])",
        0.5 * frac, "bias_bound")
    hw = (AUROC_HI - AUROC_LO) / 2
    row("half-width of the clean fair-pool AUROC CI",
        f"({AUROC_HI} - {AUROC_LO}) / 2", hw, "ci_half_width")
    cf = (PINNED_HALLUCINATING / N_STRATUM) ** 2
    row("counterfactual: both strata censored at the higher rate",
        f"0.275^2 / [0.275 x 0.095] = {cf:.4f} / {frac:.4f}", cf / frac,
        "counterfactual_ratio", dp=1)
    log("")
    log(f"So the bound is {0.5 * frac:.4f} against a half-width of {hw:.3f}: the censoring")
    log(f"bias is at most {0.5 * frac / hw:.0%} of the interval the AUROC is already reported")
    log("with, which is the point of the paragraph. Note the pair fraction is EXACT on this")
    log(f"pool ({pinned_pairs} of {n_pairs} pairs), not an approximation — the two strata are")
    log("fixed sets of 200, so the cross-product is a count.")
    log("")
    log("One wording caveat, recorded because the sweep raised it: `docs/critique_log.md` uses")
    log("2.9x for the ratio of the two CENSORING RATES' effect (27.5/9.5 = 2.89), while the")
    log("paper uses it for the ratio of AFFECTED PAIRS. The two coincide numerically here")
    log(f"(0.275^2 / (0.275 x 0.095) = 0.275/0.095 = {0.275 / 0.095:.2f}) because the")
    log("hallucinating rate cancels, so the sentence is correct — but it is correct by")
    log("coincidence of algebra, not because it is quoting the logged quantity.")
    log("")

    # ==================================================================================
    log("## methods.tex — resolution of the n=6 arm statistic")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    step = 1.0 / (N_TARGETS_NULL_CONTROL * src["null-control benign draws per target (K)"])
    row("step of the arm-level statistic",
        f"1 / (n={N_TARGETS_NULL_CONTROL} targets x K="
        f"{int(src['null-control benign draws per target (K)'])} benign draws)",
        step, "arm_step")
    log("")
    log("A per-target rank among K=5 benign draws moves in fifths; averaging over 6 targets")
    log("makes the arm statistic move in thirtieths. Any arm-to-arm gap smaller than that is")
    log("below the machinery pass's resolution and cannot be read as a difference.")
    log("")

    # ==================================================================================
    log("## experiments.tex — cost of the matched design (input repaired 2026-08-19)")
    log("")
    log("**The old registration was stale in both directions and green anyway.** It pinned")
    log("a MODELLED and long-superseded `228 GPU-h` to `docs/critique_log.md`, which still")
    log("contains that string, so the input")
    log("guard passed; and it verified the paper against the phrase \"roughly nine GPU-days\",")
    log("which `experiments.tex` had already stopped containing. A guard that reads only the")
    log("upstream side cannot see a paper that has moved on. Both sides are now pinned.")
    log("")
    log("The entry-22 figure is superseded and is named here only so it cannot come back")
    log("silently. Every operational figure below carries its tag and its anchor.")
    log("")
    log("| figure | provenance | value |")
    log("|---|---|---|")
    log("| entry-22 price of the judge arm (retired, superseded) | MODELLED from the 55 s "
        "unit of `docs/critique_log.md` 22, at K=180, n=80 | 227.8 GPU-h |")
    log("| clustering time on the deployed run | MEASURED, same symmetric judge, "
        "`judge_batch_size` 6, N=10, from `results/operational_number_audit.md` 2.4 | "
        "24.0 s/clustering |")
    log("| judge arm re-priced on that unit | MEASURED, re-derived from the 24.0 s figure "
        "above at K=180, n=80 | 98.7 GPU-h |")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    evals = src["judge evaluations per target at K=180"]
    unit = src["measured seconds per clustering, deployed run"]
    repriced = evals * unit * N_JUDGE_TARGETS / 3600.0
    row("re-priced cost of the judge arm", f"{evals:.0f} x {unit} x {N_JUDGE_TARGETS} / 3600",
        repriced, "gpu_hours_repriced", dp=0)
    ratio = CLAIMS["gpu_hours_retired"].value / repriced
    row("how much too large the recorded trigger was",
        f"{CLAIMS['gpu_hours_retired'].value:.0f} / {repriced:.1f}", ratio,
        "gpu_trigger_ratio", dp=1)
    log("")
    log(f"In days that is {repriced / 24.0:.2f}, against the "
        f"{src['retired entry-22 price of the judge arm, GPU-hours'] / 24.0:.1f} the retired")
    log("figure implied. The audit's own cross-check value is carried as an input and agrees:")
    log(f"{src['re-priced judge arm, GPU-hours (cross-check)']} against {repriced:.2f} computed here.")
    log("")
    log("**One thing that does not reproduce, and it is upstream of the paper.** Entry 22's")
    log("chain as quoted in `results/operational_number_audit.md` 2.4 is")
    log("`185 evaluations/target x 55 s = 171 min/target x 80 = 228 GPU-h` (MODELLED "
        "throughout, from that 55 s unit, and superseded). But 185 x 55 s is")
    log(f"{185 * 55 / 60:.1f} min, not 171, and 185 x 55 x 80 / 3600 is {185 * 55 * 80 / 3600:.1f},")
    log("not 227.8. The audit's own 227.8 back-solves to a unit of 55.4 s, not the 55 s the")
    log("same sentence prints. Nothing downstream moves — the ratio is 2.3x either way — but the")
    log("retired chain is not internally consistent, and a reader who checks it will find that")
    log("before they find anything else.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the N=40 operating points (registered 2026-08-19)")
    log("")
    log("Every interval the paper prints on a COUNT over the fair pool's 200 is a Wilson")
    log("interval, and the paper says so. None of them was checkable outside the .tex. The")
    log("counts are artifact-sourced; the intervals are arithmetic and are recomputed here.")
    log("")
    log("ONE ROW PRINTS NO INTERVAL. The N=40 floor is a point, `2.0%`, and that is the")
    log("ruling of `results/n40_floor_estimator_ruling.md`, not an omission: once the")
    log("ceiling atom empties, whether the top score this pool reached is the top of the")
    log("population's support is not determinable at n=200, so the estimand is NOT")
    log("IDENTIFIED -- it is 2.0% if the population can never produce 39 mutually")
    log("inequivalent answers out of 40, and can be arbitrarily smaller if it can. That")
    log("argument uses no population model. Coverage figures for the two candidates DO")
    log("use one and must be quoted with it: under the calibrated Ewens fit, 53.7%")
    log("(Wilson on 4/200) and 0.00% (question bootstrap) at nominal 95%; under the zero")
    log("branch, 95.06% and 100% (ruling sec. 8.4). The row below still prints")
    log("what Wilson WOULD give, so the withdrawal stays auditable, but nothing is")
    log("compared against the paper there -- the paper has no interval on that row to")
    log("compare to, and both candidates are pinned as retired literals above.")
    log("Population, once, for all four rows: the fair pool's 200-answer correct stratum for")
    log("false-alarm rates, its 200-answer hallucinating stratum for the true-positive rate.")
    log("")
    log("| quantity | count | Wilson 95% computed | paper | verdict |")
    log("|---|---|---|---|---|")

    def wrow(label: str, k: int, n: int, pt_key: str, lo_key: str, hi_key: str) -> None:
        lo, hi = wilson(k, n)
        pt = 100.0 * k / n
        for k_ in (pt_key, lo_key, hi_key):
            exercised[k_] = 1
        cl_pt, cl_lo, cl_hi = (CLAIMS[pt_key].value, CLAIMS[lo_key].value,
                               CLAIMS[hi_key].value)
        ok = (round(pt, 1) == round(cl_pt, 1) and round(lo, 1) == round(cl_lo, 1)
              and round(hi, 1) == round(cl_hi, 1))
        log(f"| {label} | {k}/{n} | {pt:.1f}% [{lo:.2f}, {hi:.2f}] | "
            f"{cl_pt:.1f}% [{cl_lo:.1f}, {cl_hi:.1f}] | "
            f"{'MATCHES' if ok else '**DIFFERS**'} |")
        if not ok:
            PROBLEMS.append(
                f"DERIVATION '{label}': Wilson on {k}/{n} gives "
                f"{pt:.1f}% [{lo:.2f}, {hi:.2f}], paper prints "
                f"{cl_pt:.1f}% [{cl_lo:.1f}, {cl_hi:.1f}].")

    def crow(label: str, k: int, n: int, pt_key: str) -> None:
        """A row the paper prints as a POINT with NO interval.

        The Wilson interval on the same count is still computed and printed here, because
        the number was withdrawn on evidence and a withdrawn number that vanishes from the
        record cannot be re-examined. It is NOT compared against the paper: there is
        nothing in the paper to compare it to, and `wrow` asserting a match is exactly how
        this script would drag the retired interval back in."""
        lo, hi = wilson(k, n)
        pt = 100.0 * k / n
        exercised[pt_key] = 1
        cl_pt = CLAIMS[pt_key].value
        ok = round(pt, 1) == round(cl_pt, 1)
        log(f"| {label} | {k}/{n} | {pt:.1f}%, no interval "
            f"(Wilson on this count would be [{lo:.2f}, {hi:.2f}] -- WITHDRAWN) | "
            f"{cl_pt:.1f}%, no interval | {'MATCHES' if ok else '**DIFFERS**'} |")
        if not ok:
            PROBLEMS.append(
                f"DERIVATION '{label}': {k}/{n} is {pt:.1f}%, paper prints "
                f"{cl_pt:.1f}%.")

    wrow("clean correct answers at the ln 40 cap", 0, N_STRATUM,
         "n40_atcap", "n40_atcap", "n40_atcap_hi")
    crow("cheapest firing threshold at N=40 (the floor)", 4, N_STRATUM, "n40_floor")
    tpr_count = int(round(src["hallucinating answers caught at that threshold, N=40 (rate)"]
                          * N_STRATUM / 100))
    wrow("hallucinating answers that threshold catches", tpr_count, N_STRATUM,
         "n40_tpr", "n40_tpr_lo", "n40_tpr_hi")
    wrow("achieved false-alarm rate at a 5% budget",
         int(src["count behind that achieved 5.0%"]), N_STRATUM,
         "n40_achieved", "n40_achieved_lo", "n40_achieved_hi")
    log("")
    log(f"The true-positive count is not printed as a count anywhere: `results/n_scaling_grid.md`")
    log(f"section 3 gives the rate 6.0%, and {tpr_count} is 6.0% of 200. The Wilson interval that")
    log("follows reproduces the paper's [3.5, 10.2] exactly, which is the check that the count")
    log("was read off the right denominator — the 200 HALLUCINATING answers, not the 200")
    log("correct ones. On the correct stratum the same rate would be a false-alarm rate, and")
    log("the paragraph would say the opposite of what it means.")
    log("")
    log("The 0.0% row is the one the concession now rests on: its threshold is ln 40, fixed")
    log("before any data, so its one-sided Wilson upper bound of 1.88% is the pre-registered")
    log("criterion read on the pre-registered quantity (at-cap mass), and it clears 5% with")
    log("three counts to spare. Do not read it as an operating point. It is a structural")
    log("zero — the never-fire")
    log("policy — and not an operating point; the cheapest alarm that exists at N=40 costs")
    log("2.0%. `results/replay_control.md` section 5 records that `n_scaling_grid.md` conflated")
    log("the two in its floor column, which is why both rows are registered here rather than")
    log("one.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the fall across the budget (registered 2026-08-19)")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    f10 = src["subset-averaged replay floor at N=10 (percent)"]
    row("the replayed N=10 floor, as the paper rounds it", f"{f10} to 1 dp", f10,
        "replay10_floor", dp=1)
    fall = f10 - 100.0 * 4 / N_STRATUM
    row("fall from the replayed N=10 floor to the measured N=40 floor",
        f"{f10} - 2.0 (4/200)", fall, "fall_points", dp=1)
    e10 = src["exact replay floor at N=10 (percent)"]
    e20 = src["exact replay floor at N=20 (percent)"]
    row("the N=10 -> N=20 leg, from the EXACT floors",
        f"{e10} - {e20} (exact, not the 40k-draw MC pair)", e10 - e20,
        "leg_10_20_points", dp=1)
    row("the N=20 -> N=40 leg", f"{e20} - 2.0 (4/200)", e20 - 2.0,
        "leg_20_40_points", dp=1)
    log("")
    log("**Why the leg above is derived from the exact floors and not from the two floor")
    log("inputs this script already had.** Those inputs are the report's 40,000-draw Monte")
    log("Carlo, 11.974 and 3.134. Their difference is 8.840, which rounds to **8.8**. The")
    log("exact floors differ by 8.8630, which rounds to **8.9**, and 8.9 is what the paper")
    log("prints. The end-to-end fall lands on 10.0 under either pair, which is why the")
    log("distinction never came up before; this leg straddles the decimal place the paper")
    log("quotes. THE PAPER IS RIGHT. `results/replay_control.md` prints -8.8 in its")
    log("differences table and marks it as Monte Carlo; correcting the paper down to match")
    log("it has been attempted once and was correctly refused. The exact leg is independently")
    log(f"recorded in that same file as {src['exact 10 -> 20 paired floor leg (points)']}, and")
    log("in `figures/fig_floor_budget_stats.json` as -8.86.")
    log("")
    log("The interval on that fall, [7.2, 12.9], is a PAIRED bootstrap over the 200 questions")
    log("and is not arithmetic on anything here — it is read from `results/replay_control.md`")
    log("section 2's step table and cannot be reconstructed from the two end intervals. It is")
    log("registered as a claim, not as a derivation, and this script does not verify it.")
    log("")
    log("**A retired value, recorded so it cannot return.** An earlier round quoted this fall")
    log("as **-9.9 points [-15.5, -5.0]** off floors of 11.9 / 3.0 / 2.0. Those point")
    log("estimates were averages over 200 whole replicates, whose Monte-Carlo error straddled")
    log("the first decimal; they were replaced by the mean of the 200 per-question")
    log("probabilities (`results/replay_control.md` section 2b, and")
    log("`results/post_overnight_claim_review.md` section 3.3), giving 12.0 / 3.1 / 2.0 and a")
    log("fall of 10.0 points on a much tighter paired interval. **9.9 is superseded.** The")
    log("paper is checked above for the ABSENCE of `$9.9$ points`.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the variance decomposition (registered 2026-08-19)")
    log("")
    log("The paper states an identity: for a floor that is a mean of independent indicators,")
    log("the subset-draw component and the question component sum in quadrature to exactly the")
    log("binomial standard error a Wilson interval on one replicate already reports. Both")
    log("components are artifact-sourced; the two things the paper asserts about them — that")
    log("they combine to the printed binomial figure, and that the binomial figure is the one")
    log("the floor implies — are arithmetic, and were printed only in the .tex.")
    log("")
    log("| budget | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    for tag, pbar, q, s, key, skey, qkey in (
            ("N=20", src["subset-averaged replay floor at N=20 (percent)"],
             src["N=20 question component, sd in rate points"],
             src["N=20 subset-draw component, sd in rate points"],
             "sd20_binomial", "sd20_subset", "sd20_question"),
            ("N=10", src["subset-averaged replay floor at N=10 (percent)"],
             src["N=10 question component, sd in rate points"],
             src["N=10 subset-draw component, sd in rate points"],
             "sd10_binomial", "sd10_subset", "sd10_question")):
        row(f"{tag}: subset-draw component, as the paper rounds it", f"{s} to 2 dp", s,
            skey, dp=2)
        row(f"{tag}: question component, as the paper rounds it", f"{q} to 2 dp", q,
            qkey, dp=2)
        row(f"{tag}: components in quadrature", f"sqrt({s}^2 + {q}^2)", math.hypot(s, q),
            key, dp=2)
        p = pbar / 100.0
        row(f"{tag}: binomial sd implied by the floor",
            f"100 x sqrt({pbar}% x (1-{pbar}%) / {N_STRATUM})",
            100.0 * math.sqrt(p * (1 - p) / N_STRATUM), key, dp=2)
    log("")
    log("Both budgets close to two decimals, which is the identity and not a coincidence: the")
    log("residual `results/replay_control.md` reports on the same rows is -1.1e-19 and 0.0e+00.")
    log("")
    log("**Status of the 0.99 the previous round carried.** The N=20 subset-draw component was")
    log("quoted as 0.99 points from a 500-replicate Monte-Carlo")
    log("(`results/gate_paper_edits_2026_08_19.md`). The exact value over 40000 subset draws")
    log("per question is 0.9826, which is what the paper now prints as 0.98. Same quantity,")
    log("better estimator; 0.99 is superseded and is not registered.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the June/August generation drift (registered 2026-08-19)")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    lj = src["mean answer length, June direct cache (chars)"]
    la = src["mean answer length, August checkpoint (chars)"]
    row("how much longer the August answers run", f"{la} - {lj}", la - lj, "drift_chars", dp=1)
    d = src["paired length difference (chars)"]
    se = src["paired length difference, standard error (chars)"]
    row("z on the paired length difference", f"{d} / {se}", d / se, "drift_z", dp=1)
    row("terminal-punctuation gap, in points",
        f"100 x {src['paired terminal-punctuation difference (fraction)']}",
        100 * src["paired terminal-punctuation difference (fraction)"],
        "drift_punct_points", dp=1)
    log("")
    log("The z is the load-bearing one: it is what turns \"the two caches differ a bit\" into")
    log("\"the two caches are measurably different runs\", which is the sentence that stops")
    log("either arm being called the odd one out. It appears in the paper as `$z{=}+4.0$` and")
    log("nowhere else as arithmetic; 3.63 / 0.91 = 3.99 rounds to it, but only just, and a")
    log("reader who recomputed it from the printed 116.0 and 119.6 would get 3.6 / 0.91 = 3.96")
    log("instead, because the paired difference is not the difference of the two means.")
    log("")

    # ==================================================================================
    log("## discussion.tex — the two goodness-of-fit p-values (registered 2026-08-19)")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    x2 = src["cluster-count chi-square, correct stratum, k=10"]
    df = int(src["its degrees of freedom"])
    row("upper-tail p of the cluster-count fit", f"chisq_sf({x2}, {df})", chisq_sf(x2, df),
        "chisq_p", dp=2)
    log("")
    log("The Poisson-binomial p is NOT a derivation this script can do: it is an exact DP over")
    log("200 per-question probabilities that live in the checkpoint, not in any artifact this")
    log("file reads. It is registered as a claim with a cross-check instead.")
    log("")
    log("| implementation | P(X <= 19) |")
    log("|---|---|")
    log(f"| `results/replay_control.md`, the producing run | "
        f"{src['exact Poisson-binomial P(X <= 19), producing implementation']} |")
    log(f"| `results/gate_paper_edits_2026_08_19.md`, independent reimplementation | "
        f"{src['the same p, independent reimplementation']} |")
    log(f"| what the paper prints | {CLAIMS['poisson_binomial_p'].value} |")
    log("")
    log("**Flag, not a failure: the paper prints three decimals that two implementations do")
    log("not agree on.** 0.081 and 0.083 differ in the last digit the paper shows. The")
    log("difference changes nothing — both are far from any threshold, and the sentence they")
    log("support says the count is not out of line — but `$p{=}0.081$` claims a precision the")
    log("evidence does not have. Two significant figures (`$p \\approx 0.08$`) is what the two")
    log("runs jointly support. This script does not edit the paper; it records the gap.")
    log("")

    # ==================================================================================
    log("## Resolved: the 1440 vs 1424 oracle mix-up")
    log("")
    log("This report previously carried an unresolved flag: `limitations.tex` described \"the")
    log("1440 greedy-correct questions of our 2000-question replication pass\" in the same")
    log("paragraph as the span-oracle AUROC, mixing the substring oracle's count with the span")
    log("oracle's result. **The paper has since been fixed** — `limitations.tex` now reads")
    log(f"\"{int(src['greedy-correct count, SPAN oracle'])} greedy-correct questions "
        "(alias-aware span oracle...)\" — and the fix is")
    log("held down by a claim above that requires `1440` to be ABSENT from that file. If it")
    log("returns, this script fails.")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    row("the count limitations.tex now prints", "results/relabel_report.md, span oracle",
        src["greedy-correct count, SPAN oracle"], "span_oracle_count", dp=0)
    log("")
    log("| oracle | greedy-correct of 2000 | rate |")
    log("|---|---|---|")
    for k, n in (("substring (retired)", int(src["greedy-correct count, SUBSTRING oracle"])),
                 ("span (operative)", int(src["greedy-correct count, SPAN oracle"]))):
        log(f"| {k} | {n} | {n / 2000:.1%} |")
    log("")

    # ==================================================================================
    log("## What is actually checked, and what is only pinned")
    log("")
    log("A registration is worth exactly as much as the check behind it, and these are not")
    log("all the same strength. A DERIVED claim is recomputed from artifact inputs and")
    log("compared; a PINNED claim is only held to still appear in the .tex, which catches a")
    log("silent edit but proves nothing about the number. Anything in the second table is a")
    log("number this script cannot check — usually a bootstrap endpoint — and it is listed")
    log("here rather than left to look guarded.")
    log("")
    log(f"Derived and compared: **{len(exercised)}** claims. Pinned only: "
        f"**{len(CLAIMS) - len(exercised)}**.")
    log("")
    log("| derived claim | value | compared to (decimal places) |")
    log("|---|---|---|")
    for name in sorted(exercised):
        log(f"| {name} | {CLAIMS[name].value} | {exercised[name]} |")
    log("")
    log("The decimal column is the honest limit of each check: a claim compared to 1 dp is")
    log("verified against the paper only as far as the paper prints it, and a drift smaller")
    log("than that would pass. `tests/test_derived_paper_quantities.py` mutates every row by")
    log("one unit in exactly this place and requires the run to go red, so none of these is a")
    log("comparison that cannot fail.")
    log("")
    log("| pinned-only claim | value | why it cannot be derived here |")
    log("|---|---|---|")
    why = {
        "n40_atcap": "structural zero; its interval is derived, the point is a count",
        "gpu_hours_retired": "a retired figure, held down so it cannot be quoted live",
        "gpu_days_retired_phrase": "absence check on the phrase this script used to verify",
        "fall_points_retired": "absence check on the superseded -9.9",
        "span_oracle_count": "an artifact count, not arithmetic",
        "substring_oracle_count_absent": "absence check on the retired oracle's count",
        "poisson_binomial_p": "exact DP over 200 per-question probabilities in the checkpoint",
        "sd20_subset": "an artifact component; the quadrature sum of it is derived",
        "sd20_question": "an artifact component; the quadrature sum of it is derived",
        "sd10_subset": "an artifact component; the quadrature sum of it is derived",
        "sd10_question": "an artifact component; the quadrature sum of it is derived",
    }
    for name, c in CLAIMS.items():
        if name in exercised:
            continue
        log(f"| {name} | {c.value} | {why.get(name, 'not derivable from the inputs here')} |")
    log("")

    # ==================================================================================
    log("## Guard results")
    log("")
    if PROBLEMS:
        log(f"**{len(PROBLEMS)} guard failure(s).** Each is either an artifact that moved")
        log("under a registration, or a paper that moved under one. Neither is safe to ignore,")
        log("and a paper-side miss should be re-checked against the digests above before it is")
        log("believed, because `paper/` is edited concurrently.")
        log("")
        for p in PROBLEMS:
            log(f"- {p}")
    else:
        log("All input literals and all paper literals verified. Every derivation above")
        log("matches the number the paper prints.")
    log("")

    if write:
        out = RESULTS_DIR / "derived_paper_quantities.md"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print(f"\n[report] wrote {out}", file=sys.stderr)
    if PROBLEMS:
        print(f"[guard] {len(PROBLEMS)} failure(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
