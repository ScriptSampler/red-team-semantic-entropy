# Phase 2 code review outcome

An adversarial multi-perspective review (6 correctness dimensions, each
finding independently re-verified) ran over the Phase 2 attack code. It
raised 6 findings; 3 were confirmed by the verifier. I scrutinised all
three before acting, because automated review is not infallible.

## Finding 1 (optimizer guard) — REJECTED as a false positive

The reviewer flagged `if c.obj >= best_obj:` in `optimizer.py` as dead code,
reasoning that `improved_children` already filtered `c.obj > best_obj`, and
recommended removing the guard to update best unconditionally.

This is wrong, and applying it would introduce a bug. The filter uses
`best_obj`'s value from *before* the feasibility loop, but `best_obj` rises
as candidates are accepted *within* the loop. The guard is what keeps
`best_query` tracking the maximum feasible candidate. Removing it makes
`best_query` the last feasible candidate and lets `best_obj` decrease.

A regression test (`test_optimizer_keeps_max_not_last`) now locks the
correct behaviour: two feasible candidates in one iteration, the second
lower than the first, must leave the higher as best. I added a comment in
the code explaining why the guard is not redundant.

## Finding 2 (proposer label leak) — FIXED

`propose()` only split on newlines, so a single-line `"Answer: France"` or
`"New question: ..."` leaked through verbatim, contaminating the paraphrase
with the model's answer or a label. Fixed with a targeted leading-label
allowlist regex (`_LABEL_PREFIX`). I used an allowlist rather than the
reviewer's generic `^Word:` strip, because the generic form would corrupt a
legitimate question like "In 1969: which mission landed on the Moon?".
Tests `test_proposer_strips_known_labels` and
`test_proposer_preserves_legitimate_colon` cover both directions.

## Finding 3 (SRE fallback bias) — FIXED (documentation + warning)

When reformulation generation yields zero variants, SRE falls back to the
original question alone, pooling K samples instead of N*K and biasing the
entropy low. The fallback is intentional and was already visible via
`n_reform=0`, but it is now logged with a warning and documented in the
module docstring's deviations list.

## Result

3 findings reviewed: 1 rejected with reasoning, 2 fixed. 16 logic tests
pass. The rejection is the more important outcome: the reviewer's suggested
"fix" would have silently degraded the optimiser, and the regression test
now prevents that change from being made later by mistake.
