# Semantic entropy has very little dynamic range where it matters (2026-08-02)

Measured on the **clean, unattacked** scores of the definitive pool (SE, N=10, TriviaQA,
Llama-3.1-8B-Instruct 4-bit): 80 targets the model answers correctly, 17 it answers wrongly.
Nothing here depends on any pending run, and none of it depends on our attack working.

## The detector's own signal is small, and its scale is crowded at the top

| quantity | value |
|---|---|
| clean entropy, **correct** answers (n=80) | mean 1.477, median 1.554 |
| clean entropy, **wrong** answers (n=17) | mean 1.661, median 1.748 |
| **class separation** mean(wrong) − mean(correct) | **+0.184 nats** = 8.0% of the scale |
| pooled SD | 0.656 nats |
| **Cohen's d** | **0.28** |
| correct answers already at the ln(10) ceiling | **8/80 = 10%** |
| correct answers already in the top 10% of the scale | **21/80 = 26%** |
| distinct entropy values across all 97 targets | **22** |

The separation the detector relies on is about **one quarter of a standard deviation**, and
it lives on a scale where a quarter of the correct answers are already pressed against the
top. This is consistent with the fair-pool clean AUROC of 0.704 [0.653, 0.753] — that AUROC
is not an artifact of our pool, it is what a d = 0.28 separation looks like.

## The consequence for the attack: express the effect in units of the detector's own signal

The false-alarm attack's mean intended move on this pool is **0.524 nats**. Against the
detector's own yardstick:

- **0.524 / 0.184 ≈ 2.8×** the entire mean gap between correct and wrong answers.
- **0.524 / 0.656 ≈ 0.80** pooled standard deviations, versus the 0.28 SD that separates the
  classes in the first place.

So a meaning-preserving paraphrase moves a correct answer roughly **three times the distance
that separates correct answers from hallucinations**. That statement is *scale-free*, needs
no ceiling correction, and is far more informative than the raw nats it is computed from.

**It is not yet a claim.** It uses the raw attack move, which is winner's-curse biased
(the max over ~181 candidates); the null control replaces the numerator with a
floor-corrected effect. But the *denominator* — the detector's own separation — is a fixed
property of the detector measured on clean data, so this ratio is the right currency for the
final number whatever the null control returns, and it is immune to the log(N) censoring
that makes raw nats unreportable for the false-alarm direction.

## Why this matters independently of our attack

A detector with d = 0.28, a coarse 22-value discrete output, and 10% of clean correct
answers already pinned at its maximum has almost no resolution at the top of its range.
An attacker aiming to induce false alarms therefore does not need to be subtle: the metric
runs out of room. Read together with the saturation finding (49% of attacked targets finish
exactly at the ceiling — `ceiling_saturation_finding.md`), the picture is less "we found a
clever attack" and more "the score has nowhere to go, and getting it there is easy". That is
a statement about the paradigm, which is what the protocol-led framing is for.

Data: `wk9_def/triviaqa_se_{false_alarm,hide}.jsonl`. Analysis: `scripts/dynamic_range.py`.
