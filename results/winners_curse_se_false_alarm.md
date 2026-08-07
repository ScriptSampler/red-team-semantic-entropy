# Winner's-curse re-evaluation — se_false_alarm (fresh seed 1)

The attack reports the MAXIMUM over ~181 noisy entropy estimates, so its move is inflated by selection-on-noise. Here the SELECTED paraphrase is re-scored on an INDEPENDENT sample (same N, different seed). Regression toward the mean measures the selection component directly; it does not answer whether benign paraphrasing achieves the same (that is the benign-floor control's job).

- n = 60
- mean move at selection: **+0.698** nats -> on fresh samples: **+0.315** nats
- **retention = 45%** of the selection-time effect
- median: +0.586 -> +0.165
- targets keeping a positive move: 36/60 (60%)
- shrinkage (fresh - selection): -0.383 [-0.529, -0.234] nats (a CI excluding 0 means the selection effect is provably inflated)
- corr(selection move, fresh move) = +0.456

READING: retention near 1.0 means the selected paraphrase's advantage is a property of the paraphrase, not of the sample it was selected on. Retention near 0 means the reported effect was largely selection-on-noise — which the benign floor would then also show.
