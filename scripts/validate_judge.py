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

    # Pre-registered gate (critique_log 18, critic-approved): usable IFF hard AND pos >= 0.8.
    pre_pass = (hard_p == hard_p and hard_p >= 0.8 and pos_p >= 0.8)
    # Outcome-triggered re-spec (critique_log 21, B3), disclosed — NOT a silent gate rewrite:
    # the pos>=0.8 leg is NOT met (the judge over-splits genuine aliases, partly TriviaQA
    # label noise it correctly rejects). For the FALSE-ALARM direction ONLY, over-splitting
    # inflates baseline entropy -> the judge is CONSERVATIVE (a surviving FA effect is
    # understated), so hard-neg-primary is defensible FOR FA. It does NOT license hide
    # adjudication (over-splitting OVERSTATES hide). Report BOTH verdicts.
    mode = "symmetric" if not args.asymmetric else "asymmetric"
    fa_usable = (hard_p == hard_p and hard_p >= 0.8)
    L = [f"# LLM-judge self-validation ({args.model}, {mode})", "",
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
         f"PRE-REGISTERED gate (hard>=0.8 AND pos>=0.8): "
         f"{'PASS' if pre_pass else f'FAIL — pos {pos_p:.3f} < 0.8'}.",
         "",
         f"HARD-NEG-PRIMARY re-spec for FALSE-ALARM adjudication (critique_log 21, B3): "
         f"{'USABLE for FA' if fa_usable else 'NOT usable'} (hard-neg {hard_p:.3f} >= 0.8). "
         "OUTCOME-TRIGGERED DEVIATION, disclosed: the pos shortfall is over-splitting of "
         "genuine aliases, CONSERVATIVE for false-alarm (inflates baseline entropy -> a "
         "surviving FA effect is understated) but NOT for hide; scope this oracle to FA only. "
         "STILL OWED before the paper cites it as sole adjudicator: (i) this number is the "
         f"DEPLOYED config ({mode}) — cite THIS one, not a mixed sym/asym pair; (ii) validate "
         "on messy real sampled pairs, not just clean gold aliases; (iii) a "
         "differential-over-splitting check (attack vs benign cluster counts must not diverge); "
         "(iv) report the NLI/exact-match bracket ALONGSIDE so no headline rests solely on this."]
    out = RESULTS_DIR / "judge_validation.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
