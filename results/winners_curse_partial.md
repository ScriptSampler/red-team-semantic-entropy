# Winner's curse measured directly: ~2/3 of the raw FA effect is selection-on-noise

**PARTIAL (n = 10 of 80; the run is checkpointed and continuing).** Direction is stark
enough to record now; the final number replaces this one.

## Design

The attack reports the **maximum** over ~181 noisy entropy estimates, so its move is
inflated by selection-on-noise. The classical diagnostic is to re-evaluate the *selected*
item on independent data. Here: re-score the attack's chosen paraphrase **at the same N=10
with a different sampling seed**. No scale change, no judge, no benign floor needed. A
prerequisite was verified on GPU first — a seeded 20-sample draw is *not* a prefix-superset
of the seeded 10-sample draw, so re-scoring really does use fresh randomness.

## Result

| quantity | value |
|---|---|
| mean move at **selection** (seed 0, the reported figure) | **+0.811 nats** |
| mean move on a **fresh sample** (seed 1) | **+0.263 nats** |
| **retention** | **32%** |
| targets keeping a positive move | 8/10 |
| corr(selection move, fresh move) | +0.45 |

**Roughly two-thirds of the reported false-alarm effect does not survive re-evaluation on
an independent sample.** The selected paraphrase's advantage was substantially a property
of the draw it was selected on, not of the paraphrase.

There is still real signal: 8 of 10 targets keep a positive move and the two measurements
correlate at +0.45. But the magnitude of the raw effect is inflated by about 3×.

## Why this matters, and exactly what it does and does not show

- **It vindicates the B2 programme.** The winner's-curse concern that reshaped this project
  was not hypothetical; it is measured here at roughly 3× inflation on real data.
- **It supersedes the N=20-based estimate.** The pilot accidentally gave a retention figure
  of 94%, but that re-scored at N=20, conflating regression-to-the-mean with a change in the
  entropy scale. This same-N, different-seed measurement is the clean one, and it disagrees
  sharply. The 94% figure should not be quoted.
- **It does NOT replace the benign floor.** This bounds *one* component of the problem — how
  much of the effect is selection noise. It says nothing about whether a *random* paraphrase
  achieves the same move, which is a different question and remains the null control's job.
  A reader must not read 32% retention as "the attack works, just weaker": the remaining
  0.263 nats might still be entirely matched by benign rephrasing.
- **It compounds with the censoring finding.** The 0.811 figure is itself censored (49% of
  targets sit at the ceiling), so both the raw number and its inflation are measured on a
  truncated scale.

Method: `scripts/winners_curse_reeval.py`. Checkpoint:
`results/winners_curse_ckpt_se_false_alarm_def.jsonl`. Approved as correctly scoped in
critique_log 24(d).
