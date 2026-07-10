# Benign-floor diagnosis (pre-registered)

Written 2026-07-10, **before** the n>=80 (or interim n=53) `--dump_diag` data lands, to
pre-commit the analysis and avoid post-hoc rationalisation. Open gate named by the critic
(critique_log 19-20): explain the judge benign floor before any reframe-(a) claim.

## The observation (n=6, machinery pass)

Mean benign-paraphrase move per arm, SE/false-alarm:

| arm | benign floor (nats) |
|-----|--------------------:|
| shared NLI | -0.021 |
| exact-match | -0.062 |
| **LLM-judge** | **-0.190** |

The judge's benign floor is ~9x more negative than NLI's. Because the reported net is
`attack - mean_benign`, a more-negative benign floor **inflates the judge net** (and hence
the survival ratio). We already demote the net to supplementary and lead with the
percentile-in-benign (scale-free, invariant to the floor level). The diagnosis is not to
fix the headline — it is to understand the mechanism, because it determines how to READ a
judge null result: is a small/negative judge net evidence the attack is an artifact, or an
artifact of the JUDGE over-splitting baselines?

## Competing hypotheses (discriminated by the dump'd per-target data)

- **H_split — the judge over-splits the baseline.** The judge's positive-recognition is
  ~0.7 (it splits some genuine aliases; validate_judge.md), so it inflates the *baseline*
  (`before`) judge-entropy relative to NLI. A benign paraphrase that happens to yield
  less-diverse samples then *reduces* judge-entropy -> a systematic negative benign move.
  Prediction: mean `baseline_judge > baseline_nli` (paired), and benign_judge_move
  correlates negatively with `(baseline_judge - baseline_nli)`.
- **H_rtm — regression to the mean of selected targets.** FA targets are chosen for a
  property of their baseline; benign rephrasing moves entropy back toward the mean.
  Prediction: benign_judge_move correlates with the baseline_judge *level* (high baseline
  -> negative move), roughly symmetric across arms once scaled.
- **H_noise — it is n=6 noise.** -0.19 has a wide interval at n=6.
  Prediction: at n=53/80 the judge floor regresses toward ~0 or stabilises with a tight CI
  that no longer stands out from the other arms.

## Analysis (run on the `--dump_diag` JSON from the definitive judge run)

1. Paired `baseline_judge` vs `baseline_nli` across targets (mean diff + bootstrap CI). A
   large positive diff supports H_split.
2. Regress per-target `mean(benign_judge)` on (a) `baseline_judge` and (b)
   `baseline_judge - baseline_nli`. The sign/magnitude discriminates H_rtm from H_split.
3. Report the n>=80 judge benign floor with its CI (tests H_noise), alongside NLI/exact.
4. Cross-check: does the negative judge floor concentrate in targets whose baseline the
   judge splits more than NLI does? (join per-target baseline diff with benign move.)

## Consequence for the claim (pre-committed reading)

- **If H_split dominates:** the judge is *conservative* for the false-alarm direction — it
  inflates baselines, so the attack must clear an over-split baseline; a surviving effect
  is then, if anything, understated. This strengthens a positive (a) finding but makes a
  *null* judge result ambiguous (over-splitting could mask a real effect). The percentile
  headline remains valid (scale-free); the net/ratio must carry the H_split caveat.
- **If H_rtm dominates:** the floor is a target-selection property, broadly symmetric
  across arms; the net inflation is real and percentile is the right headline, no judge-
  specific caveat needed.
- **If H_noise:** floor ~0 at scale; net and percentile agree; no special handling.

Bottom line: the percentile-in-benign is the pre-registered headline *because* it is
invariant to the benign-floor level. This diagnosis fixes how we read a judge net/ratio
and whether a null judge result is dispositive (H_rtm/H_noise) or confounded by
over-splitting (H_split). It does not change the reframe-(a) gate (adjudicator net CI > 0
at n>=80), but it is required to interpret that gate honestly.
