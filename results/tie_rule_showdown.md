# Which tie rule survives the ceiling — and why I was wrong twice

`scripts/tie_rule_showdown.py`. Each rule's null is simulated with the SAME rule as its
observed statistic — the consistency my first attempt lacked. H0: attack candidates and
benign draws exchangeable. H1: the attack is "worth `mult` x its budget". Atom of mass `q`
at the ceiling; P(sat) = 1-(1-q)^181 is the chance the attack's max is pinned there.

| q | P(sat) | rule | m | E[S]\|H0 | level | pow 2x | pow 5x |
|---|---|---|---|---|---|---|---|
| 0.000 | 0.00 | strict / conservative / randomized | 30 | 13.16 | 0.070 | 0.67 | 0.99 |
| 0.010 | 0.84 | strict | 30 | 5.98 | 0.110 | 0.90 | 1.00 |
| 0.010 | 0.84 | conservative | 30 | 26.02 | 0.055 | **0.13** | 0.09 |
| 0.010 | 0.84 | **randomized** | 30 | 12.01 | 0.068 | **0.68** | 0.98 |
| 0.050 | 1.00 | strict | 30 | 0.01 | **0.995** | — | — |
| 0.050 | 1.00 | conservative | 30 | 120.0 | 0.050 | **0.05** | 0.04 |
| 0.050 | 1.00 | **randomized** | 30 | 11.86 | 0.093 | **0.71** | 0.99 |

**With no atom all three rules agree.** With one, they diverge completely:
- **strict** blows up in level (0.995) — with S≈0 always it rejects under H0 too.
- **conservative** stays calibrated but loses ALL power (0.05 at a 2x effect). This is what
  I shipped, and what made the test look degenerate.
- **randomized** keeps both: level ≈ nominal, power 0.71/0.99 even at FULL saturation.

## Why randomized works, and what I missed

I reasoned that once the ceiling pins the max VALUE under both hypotheses, no statistic
seeing only the max can distinguish them. My own derivation
(`scripts/tie_derivation.py`, verified against simulation to 3 decimals) is correct as far
as it goes:

> P(benign > attack-max) = (1-q)^N · [q + (1-q)/(N+1)] → 0 as q grows.

But that is about the max's **value**, and I stopped there. The signal is in the
**multiplicity at the max**: a stronger attack lands MORE of its candidates on the ceiling,
which shrinks the `1/(b+1)` credit each tied benign draw receives. The randomized rule
reads that; strict and conservative both discard it, in opposite directions.

## The consequence: `b` must be MEASURED

`b` is the number of feasible attack candidates achieving the max. It cannot be estimated
from benign data — b is exactly where attack strength appears once the value is pinned, so
an H0-based estimate would erase the signal.

It was not recorded, and worse, was **unrecordable**: `optimizer.py` filtered candidates
with `c.obj > best_obj`, so everything tying the ceiling was dropped before the feasibility
gate ever saw it. Fixed — the filter is now `>=`, feasible objectives are retained, and
`n_feasible_at_best` is persisted on every outcome.

**This obliges a re-run of the attack campaign to obtain `b`.** The existing n=80 FA cell
predates the instrumentation and carries no tie multiplicity.
