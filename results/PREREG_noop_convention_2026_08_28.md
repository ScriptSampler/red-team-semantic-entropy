# Pre-registration: how no-op targets enter the null control

**Written 2026-08-28 23:5x, with 68 of 80 targets complete and the run still executing.**
**Locked before the final 12 land. Supersedes nothing; this convention did not previously exist.**

---

## 0. Disclosure first, because it is the thing that could invalidate this document

This is a pre-registration written **after 68 of 80 targets were visible**, and after their
effect on every candidate convention had been computed. It is therefore *not* blind, and it
must never be described as though it were. What follows states what was known at the time of
writing, so a reader can judge the decision against the information available to whoever made
it.

**What was known when this was written** (all four conventions, all three arms, n as shown,
20,000-resample paired bootstrap, seed 20260828):

| convention | NLI | exact | **judge (pre-registered adjudicator)** |
|---|---|---|---|
| (a) as-is | +0.1926 [+0.1130, +0.2847] | +0.0176 [−0.0384, +0.0868] | **−0.1515 [−0.3061, +0.0039]** — includes 0 |
| (b) neutralise no-op pairs to 0 | +0.1200 [+0.0619, +0.1864] | −0.0072 [−0.0456, +0.0387] | **−0.1675 [−0.3074, −0.0242]** — excludes 0 |
| (c) exclude no-op targets | +0.1432 [+0.0763, +0.2214] | −0.0086 [−0.0548, +0.0446] | **−0.1998 [−0.3656, −0.0330]** — excludes 0 |
| (d) benign arm may also decline | +0.1061 [+0.0549, +0.1638] | −0.0169 [−0.0541, +0.0277] | **−0.2042 [−0.3489, −0.0558]** — excludes 0 |

So the convention decides whether the judge arm's interval covers zero. That is exactly the
situation a pre-registration exists to prevent, and it is the situation we are in. The only
honest responses are to choose on a principle stated independently of the table, and to
disclose the table. Both are done here.

**The direction matters and is the strongest argument that this choice is not self-serving.**
Convention (d), adopted below, is the one **least favourable to our own attack** on every arm:
it gives the smallest NLI net, the most negative exact net, and the most negative judge net.
A negative judge net means the attack performs *worse* than budget-matched random paraphrasing
under the independent adjudicator. Choosing, after seeing the data, the convention that most
disfavours the hypothesis one might wish to support is the opposite of the bias
pre-registration guards against. If this document is attacked, that is the ground to attack it
on, and the answer is the table above.

---

## 1. The defect

`attack_move` is the change in score achieved by the attacker's chosen query. The optimiser
returns the **original question** when no candidate beats it, so on those targets
`attack_move = 0` exactly. Measured across the 68 completed targets: **`attack_move` is never
negative — its minimum is +0.0000.** The attack is therefore bounded below by zero by
construction, because declining to act is always available to it.

The benign arm is not symmetric. `feasibility.py` structurally forbids the null from drawing
the no-op — a benign "paraphrase" identical to the question is rejected — so the benign
maximum is an unconstrained maximum over K feasible paraphrases and **can be negative**, and
is: **9 of 65 targets have a negative benign maximum.**

The paired net is `attack_move − benign_max`. On a target where the attack declined to act and
the benign arm was forced to, the attack is credited with the benign arm's loss. `qb_6190`
contributes **+1.83 nats of net for zero attack effort**. Across the 11 no-op targets the
contribution is **+4.355 nats**.

This is the same asymmetry the July critique retracted a claim over — a maximum compared
against a differently-constrained maximum — reappearing per-target rather than per-design.

## 2. Why the obvious fixes are not the right one

**(a) Leave it.** Indefensible. It credits the attack for the benign arm's behaviour on targets
where the attack did nothing. Rejected on principle, independent of the numbers.

**(c) Exclude no-op targets.** Excluding the attack's failures and reporting the mean over its
successes inflates any effect estimate. This project has already retracted a claim for a
denominator error of that family. It also drops n from 65 to 57 against a pre-registered n ≥ 80
that is already unmet.

**(b) Neutralise no-op pairs to zero.** Better, and it preserves n — but it treats the problem
as a property of no-op *targets*. It is not. **2 of the 9 negative-benign-max targets are
targets the attack successfully attacked**, and (b) leaves those uncorrected. The asymmetry is
a property of the two arms' *action sets*, not of a subset of rows.

## 3. The convention, locked

> **(d) The benign arm is given the same option the attack already has: to decline.**
> The benign maximum enters the paired net as `max(0, benign_max)` on **every** target, not
> only on no-op ones. The paired net becomes `attack_move − max(0, benign_max)`.

The justification is a statement about the comparison, not about the data: the null control
asks whether the attack beats a benign search *of comparable budget and comparable freedom*.
The attack's freedom includes returning the original question. Denying the null that same
freedom does not make the null conservative — it makes it a different search, and the
difference accrues entirely to the attack. Equalising the action sets is the minimal change
that makes the two maxima comparable, and it is the only candidate that treats no-op targets
and attacked targets by the same rule.

**Targets with an empty benign arm** (`qb_565`, `qz_3393`, `qb_2689` — the feasibility gate
rejected all 250 attempts) have no benign maximum and are **excluded from the paired net**, as
they are today. They are reported explicitly rather than absorbed: with three empty arms the
paired-net denominator is 65 of 68, and will be reported as such.

## 4. What must be reported alongside it

1. **All four conventions**, with the table in section 0, so a reader can see the decision's
   sensitivity rather than take the chosen number on trust.
2. **The effective n.** It is not 80. Three targets have no benign arm; the pre-registered
   n ≥ 80 is unmet under every convention. State the achieved n and that the threshold was
   missed, in Methods and not only in Limitations.
3. **That this document was written with 68 of 80 visible.** Non-negotiable.
4. **The partial arms.** Six targets have 1–38 benign draws instead of 50, because
   `null_control.py:174` caps attempts at `K * 5` and the feasibility gate rejects the rest.
   The measured bias from this is **+0.008 nats (NLI)**, about 9% of the paired net's CI
   half-width, because the benign score distributions are extremely lumpy — a median of 5
   distinct values among 50 draws, with 28% of draws sitting exactly at the maximum, so a
   maximum over 26 draws equals a maximum over 50 with probability ≈ 0.9998. This is a
   disclosure item, not a correction.

## 5. What this does NOT change

The **exceedance test** is the pre-committed claim statistic (`docs/critique_log.md:1023`), not
the paired net. Its null is `BetaBinomial(m_j; 1, N)` carrying each target's own `m_j`, so short
benign arms cost it power rather than calibration. Exceedance p is 0.98–1.00 in all arms and no
claim currently in the paper turns on any number in section 0. The paired net is labelled
supplementary. This convention therefore changes a supplementary statistic and a disclosure,
not a headline — **today**. It is being locked now precisely so that it cannot be chosen after
the remaining 12 targets reveal which way it moves.

## 6. Owed before this is used

- Re-check `best_query` and `n_feasible_at_best` against the **live** campaign directory. The
  audit behind this document read `wk9_defb_snap` (2026-08-13); if `recompute_fair.py` has
  touched the false-alarm cell since, the no-op identification must be re-derived.
- The exceedance test's exchangeability assumption is violated by no-op targets in the NLI arm
  (7 donate an observed K = 0 against 1.65 expected), anti-conservatively. Convention (d) does
  not fix that; it is a separate question and is not settled here.
- `embed` is length 0 on all 68 targets because the run was launched with `embedding_model=""`.
  The embed arm does not exist in this campaign and must not be reported as null.
