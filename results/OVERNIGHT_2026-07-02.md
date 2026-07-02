# Overnight status — 2026-07-02 (read me first)

## TL;DR

Two full review rounds happened tonight, both critic-gated. **Round 1:** the external
review's six blockers (B1–B6) were remediated and approved. **Round 2:** I ran a
6-lens adversarial audit of the *corrected* pipeline, which found **19 confirmed B7+
issues**; the code-addressable ones are fixed and the rest are documented with a plan.
The pipeline is now hardened (**72 hermetic tests**) and the paper's Methods,
Limitations, and Discussion are drafted and critic-approved.

**There is no citable headline number yet — and that is the correct outcome.** The
audit + critic caught that even the corrected SE recompute is only *exploratory*
(seeded SE is reproducible but not noise-free; the beam search's max over ~180
finite-sample estimates carries an attenuated bias). The confirmatory headline is
gated on a **null/noise-floor control** (built tonight, not yet run).

One thing to own plainly: mid-session I raised a false alarm that the GPU and data
cache were lost. That was my error — I was querying the wrong WSL distro. Everything
is intact; details below.

## What is done and critic-approved

| Item | Status |
| --- | --- |
| B1 detector-blind shared pool (`campaign_pool`, enforced) | APPROVE |
| B2 answer-invariance success metric (conjunction, same oracle) | APPROVE-WITH-NITS (landed) |
| B3 alias-aware span oracle | APPROVE-WITH-NITS |
| B4 review-compliant reporting (CIs, attrition, answer-flip, operating point) | APPROVE-WITH-NITS (landed) |
| B7 audit remediation (SRE seeding, paired AUROC-diff CI, artifact hygiene, proposer seed) | APPROVE-WITH-NITS (landed) |
| Methods / Limitations / Discussion prose | APPROVE-WITH-NITS (landed) |

Full gate record: `docs/critique_log.md` (entries 4–11). B7 findings + status:
`docs/audit_b7_findings.md`. Commits `e4678a1`…`69dcf30`.

## The B7 audit — headline points

- **[BLOCKER, fixed] SRE winner's curse.** SRE was fully unseeded, so its objective was
  a noisy draw and the beam search kept the luckiest one. Fixed by seeding SRE (now
  deterministic like SE). SE was already seeded — but see below.
- **[BLOCKER, blocks the SE headline] Null control missing.** Seeded SE is reproducible
  but each score is a finite N=10 estimate; the max over ~180 candidates is biased in
  the attacker's favour. The headline must report success/degradation **net of** a
  benign-paraphrase noise floor. Tooling built: `scripts/null_control.py` (unit-tested).
- **[fixed] No AUROC-degradation CI existed at all** → added a paired bootstrap
  (`stats.auroc_diff_ci`) and wired it into the fair recompute.
- **[fixed] Stale pre-B1 artifacts** (clean AUROC = 1.000) were the only committed
  numbers → SUPERSEDED banners + `wk10_matrix.py --tag` defaults to the fair pool.
- **[documented] Construct-validity depth** for the definitive resubmit: shared NLI model
  for clusterer AND gate (independent-clusterer check), human/LLM-judge equivalence audit
  (answer-flip is only a lower bound), greedy-vs-sampled status, SRE threat model.

## The only experimental signal so far (EXPLORATORY)

From the partial fair-pool recompute (`results/fair_recompute_report.md`):

> **SE / false-alarm, n=6:** B2-gated success **0.500 [0.167, 0.833]**, feasible rate
> 1.000, mean intended entropy move **+0.534 nats**.

Read this as: meaning-preserving paraphrases push a *correct* answer's SE past threshold
roughly half the time on the fair pool — **preliminary, wide CI, and not yet net of the
noise floor.** Not a headline.

## Infrastructure: fine (my false alarm, corrected)

The GPU and cache are healthy in the **`Ubuntu-24.04`** research distro (rocminfo sees
gfx1201; torch 2.9.1+rocm6.4, `cuda.is_available()` = True; cache 2000 lines each). The
*default* `Ubuntu` (26.04) distro has broken ROCm and an empty home — querying it is
what produced my false "loss" alarm. Lesson recorded in the `hardware_gpu` memory:
always `wsl -d Ubuntu-24.04`. (Kept improvement from the scare: `scripts/preflight.py`.)

## Morning path (in order)

1. **Finish the SE recompute** (`recompute_fair.py --tag _fair`, resumable) to a usable
   n; it is slow (~15–40 min/attack depending on machine load), so give it a clean run.
2. **Run the null control** (`scripts/null_control.py --tag _fair`) → success/degradation
   **net of the floor**. If the effect survives, the SE headline stands; if it collapses
   into the floor, *that* is the finding.
3. **Post-hoc** `frac_correct` pass (finding 16) for sampled-status alongside greedy.
4. **Definitive run:** larger n, SRE cells (now seeded), SQuAD; then the independent-
   clusterer robustness check and a human/LLM-judge equivalence audit for construct
   validity.

## What I deliberately did NOT do
- Did not fabricate or headline any number; the SE result is labelled exploratory.
- Did not kill the running SE recompute (critic: valid as exploratory).
- Did not reinstall drivers/torch (turned out unnecessary — my false alarm).

## Live dashboard
`Desktop/SE/dashboard.html` mirrors all of the above: the B1→B7 arc, every critic
verdict, the retracted false alarm, and the exploratory number.
