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
from calibrate_embed_threshold import _alias_strata


def _acc(judge, pairs, want):
    if not pairs:
        return float("nan"), 0
    ok = sum(1 for a, b, _ in pairs if judge(a, b) is want)
    return ok / len(pairs), len(pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--n_per_stratum", type=int, default=300)
    args = ap.parse_args()

    judge = load_judge(args.model)
    print(f"[judge] {args.model} loaded", flush=True)
    st = _alias_strata(args.n_per_stratum)

    pos_acc, npos = _acc(judge, st["pos"], True)          # should say YES
    easy_acc, neasy = _acc(judge, st["easy_neg"], False)  # should say NO (easy)
    hard_acc, nhard = _acc(judge, st["hard_neg"], False)  # should say NO (HARD — the test)

    L = [f"# LLM-judge self-validation ({args.model})", "",
         "Accuracy on domain-matched short-answer strata (the set that disqualified e5). "
         "The judge may adjudicate finding 14 ONLY IF hard-negative accuracy is high "
         "(e5 was ~0.51 AUROC here).", "",
         f"- positives (aliases -> should say SAME):        {pos_acc:.3f}  (n={npos})",
         f"- easy negatives (distant -> should say NOT):    {easy_acc:.3f}  (n={neasy})",
         f"- HARD negatives (near-miss -> should say NOT):  {hard_acc:.3f}  (n={nhard})  <-- REHABILITATION CRITERION",
         "",
         f"Balanced accuracy (pos vs HARD): {0.5 * (pos_acc + hard_acc):.3f}. "
         f"{'USABLE adjudicator.' if (hard_acc == hard_acc and hard_acc >= 0.8 and pos_acc >= 0.8) else 'NOT usable -> keep the NLI/exact-match bracket.'}"]
    out = RESULTS_DIR / "judge_validation.md"
    out.write_text("\n".join(L) + "\n")
    print(f"[report] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
