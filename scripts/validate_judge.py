"""Self-validate the LLM-judge equivalence oracle before it may adjudicate (critic 16).

Runs the judge on the SAME domain-matched short-answer strata used to disqualify e5
(TriviaQA gold aliases as positives; shared-token / numeric near-misses as HARD negatives)
and reports its accuracy per stratum. The judge is a trustworthy finding-14 adjudicator
ONLY IF it clears the HARD-negative stratum (where e5 was near-chance, 0.51). If it does
not, the finding-14 attribution stays the NLI/exact-match bracket.

    # in Ubuntu-24.04, GPU free (run AFTER the attack matrix):
    ./.venv-wsl/bin/python scripts/validate_judge.py --model Qwen/Qwen2.5-7B-Instruct
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))          # for _alias_strata

from se.config import RESULTS_DIR
from se.judge import load_judge
from se.stats import rate_ci
from calibrate_embed_threshold import _alias_strata


def _acc(judge, pairs, want):
    """Accuracy + bootstrap CI (critic: a judge at 0.82 and one at 0.95 both pass the
    0.8 bar but widen the bracket differently — propagate the CI, don't hide it)."""
    if not pairs:
        return float("nan"), float("nan"), float("nan"), 0
    flags = [judge(a, b) is want for a, b, _ in pairs]
    ci = rate_ci(flags)
    return ci.point, ci.lo, ci.hi, len(pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--n_per_stratum", type=int, default=300)
    ap.add_argument("--asymmetric", action="store_true",
                    help="judge a single ordering only (default: symmetric, both must agree)")
    args = ap.parse_args()

    judge = load_judge(args.model, symmetric=not args.asymmetric)
    print(f"[judge] {args.model} loaded", flush=True)
    st = _alias_strata(args.n_per_stratum)

    pos_p, pos_lo, pos_hi, npos = _acc(judge, st["pos"], True)          # should say YES
    easy_p, easy_lo, easy_hi, neasy = _acc(judge, st["easy_neg"], False)  # should say NO
    hard_p, hard_lo, hard_hi, nhard = _acc(judge, st["hard_neg"], False)  # HARD — the test

    usable = (hard_p == hard_p and hard_p >= 0.8 and pos_p >= 0.8)
    L = [f"# LLM-judge self-validation ({args.model})", "",
         "Accuracy (95% CI) on domain-matched short-answer strata (the set that disqualified "
         "e5). The judge may adjudicate finding 14 ONLY IF hard-negative accuracy is high "
         "(e5 was ~0.51 AUROC here). CAVEAT: these strata are clean gold aliases; the judge "
         "will cluster messy real answer SAMPLES (hedges, sentences) — validate on realistic "
         "sampled pairs too, and cross-check the judge against a human sample (finding 15) "
         "before trusting it as the sole oracle.", "",
         f"- positives (aliases -> SAME):          {pos_p:.3f} [{pos_lo:.3f}, {pos_hi:.3f}]  (n={npos})",
         f"- easy negatives (distant -> NOT):      {easy_p:.3f} [{easy_lo:.3f}, {easy_hi:.3f}]  (n={neasy})",
         f"- HARD negatives (near-miss -> NOT):    {hard_p:.3f} [{hard_lo:.3f}, {hard_hi:.3f}]  (n={nhard})  <-- CRITERION",
         "",
         f"Verdict: {'USABLE adjudicator (propagate the hard-negative CI into the bracket width).' if usable else 'NOT usable -> keep the NLI/exact-match bracket.'}"]
    out = RESULTS_DIR / "judge_validation.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
