"""Every DERIVED number the paper quotes that had no producing artifact.

WHY THIS SCRIPT EXISTS. A provenance sweep of paper/*.tex against results/ and docs/ found a
residue of numbers that are arithmetic on sourced inputs but appear, as printed, nowhere
outside the .tex: the censoring bias-bound chain in discussion.tex (2.6% of pairs -> 0.013,
against a 0.050 half-width, and the 2.9x counterfactual), and the headroom / step-size
figures in methods.tex (0.923 nats, 0.277 nats, 1/30). "Derivable" is not "reproducible":
nobody could check the arithmetic without redoing it, and the one place a factor of 1/2 was
doing real work — the bias bound — was nowhere written down. This computes each of them from
its inputs and states the derivation.

INPUT GUARD. Every input below carries the artifact it comes from and a literal that must
still appear in that artifact. If an upstream number is revised and this script is not, it
FAILS rather than quietly recomputing a stale chain. That is the whole point: the failure
mode being closed is a number that was right once and then drifted.

    .venv/Scripts/python.exe scripts/derived_paper_quantities.py
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from se.config import RESULTS_DIR                          # noqa: E402


@dataclass(frozen=True)
class Input:
    """A number lifted from an artifact, with the literal that must still be there."""
    name: str
    value: float
    literal: str
    source: str

    def check(self) -> None:
        p = ROOT / self.source
        if not p.exists():
            raise SystemExit(f"input '{self.name}': missing source {self.source}")
        if self.literal not in p.read_text(encoding="utf-8", errors="replace"):
            raise SystemExit(
                f"input '{self.name}': {self.source} no longer contains {self.literal!r}. "
                f"The upstream artifact changed; re-derive rather than trusting this script.")


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
    Input("null-control benign draws per target (K)", 5,
          "K=5 benign", "results/null_control_report.md"),
    Input("judge-arm cost of the matched design, GPU-hours", 228,
          "228 GPU-h", "docs/critique_log.md"),
    Input("greedy-correct count, SUBSTRING oracle", 1440,
          "old correct rate: 1440/2000", "results/relabel_report.md"),
    Input("greedy-correct count, SPAN oracle", 1424,
          "new correct rate: 1424/2000", "results/relabel_report.md"),
]

CAP = math.log(10)
N_STRATUM = 200                 # fair pool: 200 correct + 200 hallucinating
N_TARGETS_NULL_CONTROL = 6      # the n=6 machinery pass
AUROC_LO, AUROC_HI = 0.653, 0.753
PINNED_HALLUCINATING = 55
PINNED_CORRECT = 19

# What the paper prints today, so the check is against a stated claim.
PAPER = {
    "headroom_correct": 0.923,
    "headroom_next_lattice": 0.277,
    "pinned_pair_fraction": 0.026,
    "bias_bound": 0.013,
    "ci_half_width": 0.050,
    "counterfactual_ratio": 2.9,
    "arm_step": 1 / 30,
    "gpu_days": 9,
}


def main() -> int:
    for i in INPUTS:
        i.check()
    src = {i.name: i.value for i in INPUTS}

    L: list[str] = []
    def log(s: str = "") -> None:
        print(s, flush=True); L.append(s)

    def row(label, derivation, value, claimed, dp=3):
        ok = round(value, dp) == round(claimed, dp)
        log(f"| {label} | {derivation} | {value:.{dp+1}f} | {claimed:.{dp}f} | "
            f"{'MATCHES' if ok else '**DIFFERS**'} |")
        return ok

    log("# Derived quantities the paper quotes, with their arithmetic")
    log("")
    log("Producing script: `scripts/derived_paper_quantities.py`. These are numbers that are")
    log("arithmetic on artifact-sourced inputs but were printed only in the .tex, so no reader")
    log("(and no future run) could check them. Each input is guarded: the script refuses to")
    log("run if the artifact it claims to read no longer contains the literal it needs.")
    log("")
    log("## Inputs, and where they come from")
    log("")
    log("| input | value | artifact | literal checked |")
    log("|---|---|---|---|")
    for i in INPUTS:
        log(f"| {i.name} | {i.value} | `{i.source}` | `{i.literal}` |")
    log("")
    log(f"Ceiling: log(10) = {CAP:.6f} nats.")
    log("")

    log("## methods.tex — headroom to the ceiling")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    h_corr = CAP - src["mean clean entropy, correct answers, fair pool"]
    row("headroom from the correct-answer mean", "log(10) - 1.380", h_corr,
        PAPER["headroom_correct"])
    h_next = CAP - src["K=8 lattice point (next attainable value below the cap)"]
    row("headroom at the next lattice point down", "log(10) - 2.0253", h_next,
        PAPER["headroom_next_lattice"])
    h_wrong = CAP - src["mean clean entropy, wrong answers, fair pool"]
    log(f"| (not quoted) headroom from the wrong-answer mean | log(10) - 1.843 | "
        f"{h_wrong:.4f} | - | - |")
    log("")
    log("The second row is the one that carries an argument: the whole gap between the")
    log("correct-answer mean and the cap is 0.923 nats, but the score cannot occupy it")
    log("continuously — the last attainable step below the cap already leaves 0.277 nats, so")
    log("a move smaller than one lattice step is unrepresentable, not merely small.")
    log("")

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
        f"{pinned_pairs}/{n_pairs}", frac, PAPER["pinned_pair_fraction"])
    row("bound on the downward AUROC bias", "1/2 x 2.6% (a tie contributes 1/2; truth in [0,1])",
        0.5 * frac, PAPER["bias_bound"])
    hw = (AUROC_HI - AUROC_LO) / 2
    row("half-width of the clean fair-pool AUROC CI",
        f"({AUROC_HI} - {AUROC_LO}) / 2", hw, PAPER["ci_half_width"])
    cf = (PINNED_HALLUCINATING / N_STRATUM) ** 2
    row("counterfactual: both strata censored at the higher rate",
        f"0.275^2 / [0.275 x 0.095] = {cf:.4f} / {frac:.4f}", cf / frac,
        PAPER["counterfactual_ratio"], dp=1)
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

    log("## methods.tex — resolution of the n=6 arm statistic")
    log("")
    log("| quantity | derivation | computed | paper | verdict |")
    log("|---|---|---|---|---|")
    step = 1.0 / (N_TARGETS_NULL_CONTROL * src["null-control benign draws per target (K)"])
    row("step of the arm-level statistic",
        f"1 / (n={N_TARGETS_NULL_CONTROL} targets x K="
        f"{int(src['null-control benign draws per target (K)'])} benign draws)",
        step, PAPER["arm_step"])
    log("")
    log("A per-target rank among K=5 benign draws moves in fifths; averaging over 6 targets")
    log("makes the arm statistic move in thirtieths. Any arm-to-arm gap smaller than that is")
    log("below the machinery pass's resolution and cannot be read as a difference.")
    log("")

    log("## experiments.tex — cost of the matched design")
    log("")
    days = src["judge-arm cost of the matched design, GPU-hours"] / 24
    log(f"{src['judge-arm cost of the matched design, GPU-hours']:.0f} GPU-hours / 24 = "
        f"**{days:.1f} GPU-days**. The paper says \"roughly nine GPU-days\"; the logged figure")
    log(f"is {days:.1f}, so \"roughly nine\" rounds the wrong way. \"About nine and a half\" or")
    log("\"over nine\" is the accurate phrasing; nothing else depends on it.")
    log("")

    log("## Flagged inconsistency (not a derivation): 1440 vs 1424")
    log("")
    log("`limitations.tex` describes \"the 1440 greedy-correct questions of our 2000-question")
    log("replication pass\" in the same paragraph that quotes the span-oracle AUROC 0.694.")
    log(f"But {int(src['greedy-correct count, SUBSTRING oracle'])} is the SUBSTRING-oracle")
    log(f"count; under the span oracle the same pass gives "
        f"{int(src['greedy-correct count, SPAN oracle'])} "
        f"(`results/relabel_report.md`, corroborated by `results/replication_conventions.md`).")
    log("The paragraph mixes the two oracles. This script does not edit the paper; it records")
    log("the discrepancy so it cannot be lost again.")
    log("")
    log("| oracle | greedy-correct of 2000 | rate |")
    log("|---|---|---|")
    for k, n in (("substring", int(src["greedy-correct count, SUBSTRING oracle"])),
                 ("span (operative)", int(src["greedy-correct count, SPAN oracle"]))):
        log(f"| {k} | {n} | {n / 2000:.1%} |")

    out = RESULTS_DIR / "derived_paper_quantities.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
