"""Dynamic range of semantic entropy on CLEAN (unattacked) scores.

If the detector's clean scores are compressed against the log(N) ceiling, it has little
resolution exactly where a false-alarm attack operates — a property of the detector, not of
our attack, and independent of every pending run.
"""
import json, math, statistics as st, sys
import numpy as np

sys.path.insert(0, r"I:\GITHUBPROJECTS\SE Research\src")
base = r"C:\Users\Abhi\AppData\Local\Temp\claude\I--GITHUBPROJECTS-SE-Research\85d40e73-48d6-4927-b8b8-9fe3d295986d" + "\\scratchpad\\"
CAP = math.log(10)

fa = [json.loads(l) for l in open(base + "fa80.jsonl") if l.strip()]      # model CORRECT
hd = [json.loads(l) for l in open(base + "hide.jsonl") if l.strip()]      # model WRONG

right = np.array([r["entropy_before"] for r in fa])
wrong = np.array([r["entropy_before"] for r in hd])
allc = np.concatenate([right, wrong])

print(f"CLEAN semantic entropy, N=10, ceiling ln(10)={CAP:.4f} nats")
print(f"  correct answers (n={len(right)}): mean {right.mean():.3f}  median {np.median(right):.3f}"
      f"  min {right.min():.3f}  max {right.max():.3f}")
print(f"  wrong   answers (n={len(wrong)}): mean {wrong.mean():.3f}  median {np.median(wrong):.3f}"
      f"  min {wrong.min():.3f}  max {wrong.max():.3f}")
print()
for name, v in (("correct", right), ("wrong", wrong), ("all", allc)):
    at_cap = (v >= CAP - 1e-6).sum()
    top10 = (v >= CAP * 0.9).sum()
    print(f"  {name:8s}: at ceiling {at_cap}/{len(v)} = {at_cap/len(v):.0%} | "
          f"in top 10% of the scale (>= {CAP*0.9:.2f}) {top10}/{len(v)} = {top10/len(v):.0%}")

print()
# How much of the theoretical [0, ln N] range does the clean score actually occupy?
print(f"  clean scores occupy [{allc.min():.3f}, {allc.max():.3f}] of [0, {CAP:.3f}] "
      f"= {(allc.max()-allc.min())/CAP:.0%} of the theoretical range")
print(f"  interquartile range: {np.percentile(allc,75)-np.percentile(allc,25):.3f} nats "
      f"= {(np.percentile(allc,75)-np.percentile(allc,25))/CAP:.0%} of the scale")

# Separation: what an AUROC of ~0.70 looks like in nats
print()
print(f"  mean(wrong) - mean(correct) = {wrong.mean()-right.mean():+.3f} nats "
      f"({(wrong.mean()-right.mean())/CAP:+.1%} of the scale)")
pooled = math.sqrt((right.var(ddof=1)*(len(right)-1) + wrong.var(ddof=1)*(len(wrong)-1))
                   / (len(right)+len(wrong)-2))
print(f"  pooled SD = {pooled:.3f} nats -> Cohen's d = {(wrong.mean()-right.mean())/pooled:.2f}")

# The operational question: how many DISTINCT values does the estimator even produce?
# With N=10 samples the cluster count is an integer 1..10, so entropy takes few values.
vals = sorted(set(round(float(x), 6) for x in allc))
print()
print(f"  distinct clean entropy values across all {len(allc)} targets: {len(vals)}")
print(f"  the estimator is a function of a partition of 10 samples, so it is inherently discrete")
