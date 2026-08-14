# Budget scaling of the achievable-FPR grid: measured

Generated 2026-08-14 by `scripts/n_scaling_grid.py`.
Budgets measured directly: [40]. Budgets derived by replaying the
recorded pairwise verdicts on random subsets: everything else below.

## 1. Floor and grid, by budget

The floor is the ceiling-atom mass: every threshold above ln N flags nothing, so
the first threshold that fires flags exactly the targets at the cap. That is the
smallest false-alarm rate an operator can buy at this budget.

| budget N | source | n negatives | floor = min non-zero FPR | next FPR | firing points at or below 5% | at or below 10% | at or below 25% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | Week-4 cache | 200 | 19/200 = 9.5% [6.2%, 14.4%] | 21.5% | 0 | 1 | 2 |
| 20 | replay of N=40, replicate 0 | 200 | 6/200 = 3.0% [1.4%, 6.4%] | 7.5% | 1 | 4 | 19 |
| 40 | measured | 200 | 0/200 = 0.0% [0.0%, 1.9%] | 2.5% | 5 | 14 | 43 |

**The subsetting control.** Everything at a budget below the one actually run
is a replay of random subsets, so the method has to be checked against a
directly measured grid at the same budget. The Week-4 cache is exactly that at
N=10.

- Week-4 cache, direct N=10: floor = 19/200 = 9.5% [6.2%, 14.4%]
- replay of 10-subsets of the N=40 run, 20 replicates: floor median 12.0%, range 10.0%-14.5%

If those disagree beyond the Wilson interval, the subsetting is unsound and
**no replayed budget in this report may be quoted** -- the direct
measurement at the top budget still stands on its own.

## 2. The ceiling atom against the sample budget (the curve the paper needs)

Exact per target, not an extrapolation: a set of samples is all-singletons iff
no pair inside it is equivalent, so the recorded verdict matrix answers it for
every subset size directly.

| budget k | 2 | 3 | 5 | 10 | 15 | 20 | 30 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| correct (n=200) | 0.721 | 0.521 | 0.300 | 0.120 | 0.060 | 0.031 | 0.007 | 0.000 |
| hallucinating (n=200) | 0.905 | 0.792 | 0.580 | 0.277 | 0.147 | 0.085 | 0.039 | 0.025 |

The `correct` row IS the achievable-FPR floor as a function of the sample
budget. Compare it against the pre-registered prediction in
`results/n_scaling_plan.md` section 5 before writing any prose about it.

## 3. The operator's menu at each budget

| budget | target FPR | `at_most` achieved | TPR | `closest` achieved | TPR |
| --- | --- | --- | --- | --- | --- |
| 10 | 1% | 0.0% (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% |
| 10 | 5% | 0.0% (flags nothing) | 0.0% | 9.5% **over budget** | 27.5% |
| 10 | 10% | 9.5% | 27.5% | 9.5% | 27.5% |
| 10 | 20% | 9.5% | 27.5% | 21.5% **over budget** | 44.5% |
| 20 | 1% | 0.0% (flags nothing) | 0.0% | 3.0% **over budget** | 9.5% |
| 20 | 5% | 3.0% | 9.5% | 3.0% | 9.5% |
| 20 | 10% | 10.0% | 25.5% | 10.0% | 25.5% |
| 20 | 20% | 19.0% | 42.5% | 20.5% **over budget** | 44.0% |
| 40 | 1% | 0.0% (flags nothing) | 0.0% | 2.0% **over budget** | 6.0% |
| 40 | 5% | 5.0% | 11.0% | 5.0% | 11.0% |
| 40 | 10% | 10.0% | 24.0% | 10.0% | 24.0% |
| 40 | 20% | 20.0% | 44.5% | 20.0% | 44.5% |

## 4. Measured throughput (this replaces every cost estimate that preceded it)

| N | evals | median s/eval | median s in NLI | model predicted | ratio |
| --- | --- | --- | --- | --- | --- |
| 40 | 400 | 46.7 | 33.5 | 73.9 | 0.63x |

- measured, N=40: n=400 evals -> 5.19 GPU-h [46.7 s/eval]

## 5. Provenance

- checkpoint: `/mnt/i/GITHUBPROJECTS/SE Research/results/n_scaling_ckpt.jsonl` (400 evaluations)
- ids: fair pool, `select_stratified(want, 200, seed=0)`
- generation: max_new_tokens=48, T=1.0, top_p=1.0, seed=0
- plan, cost model and the derivations that need no data: `results/n_scaling_plan.md`

