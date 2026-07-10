# START HERE — overnight session (Fri 21:30 → Sat ~06:00)

## The headline: the night found and fixed two methodology-critical flaws before they shipped

The plan was to land the n≥80 "multiday" judge result and polish the paper. Instead, a
4-dimension adversarial review of the whole paper (a workflow I ran) surfaced **two blockers
that would have sunk the paper at review**, the critic **verified both and BLOCKED the
definitive-run launch**, and I built the honest fixes. Catching these *before* spending the
multiday GPU budget on a biased control is the most valuable outcome available tonight.

### B2 — the winner's-curse null control was not budget-matched (the big one)
The attack move is the optimiser's **max over ~180 candidates**; the benign floor was only
**K=8 individual draws**. A max-of-180 beats individual draws *by construction* — under H₀
its expected percentile is **~99%, not 50%** (closed form m/(m+1)). So the old "attack at
80th percentile / net > 0" headline was **upward-biased and possibly below the null**.
- FIX BUILT: `se.stats.paired_max_net` (per-target paired attack-max vs **budget-matched
  benign-max**, bootstrap net-CI + sign test) + `analytic_max_percentile` companion. The
  null_control report now flags the old stats as biased and prints the budget-matched
  control as the headline. Tests pass (Monte-Carlo-verified).
- STILL OWED (task 23): the definitive run must use **K~180** (budget-matched), plus a
  **null-objective beam ablation** the critic required (the beam concentrates on noise, so
  even random-180 is anti-conservative). Design of the ablation is owed + needs a quick
  critic confirm.

### B3 — the LLM-judge FAILED its own pre-registered gate (an integrity issue)
The gate was `hard≥0.8 AND pos≥0.8`; the judge gets hard-neg **0.884** (pass) but pos
**0.700** (FAIL), and `results/judge_validation.md` literally said **"NOT usable"** — while
the paper promoted it as "the validated adjudicator." Also **0.92 (cited) ≠ 0.884
(committed)**.
- FIX BUILT: re-spec'd `validate_judge.py` to report BOTH the pre-registered verdict (FAIL)
  and a **disclosed, outcome-triggered hard-neg-primary re-spec for FA only** (over-splitting
  is conservative for false-alarm, not hide); rewrote the committed artifact (no standing
  "NOT usable"); added the deviation **in the Methods main text**; report the NLI/exact
  bracket alongside.
- STILL OWED (task 24): re-run validation on the **deployed (symmetric) config** to lock ONE
  number (kill 0.92-vs-0.884), validate on **messy real sampled pairs**, and do the
  **differential-over-splitting check** (attack vs benign cluster counts) — all GPU.

## The other big win: found + fixed the GPU bottleneck (batched judge)
The judge null control ran at **~35 min/target** (n≥80 would be ~33h — intractable) because
the judge scored 90 sample-pairs one at a time. I built a **batched judge** (`load_judge(
batched=True)` + `cluster_samples_judge_batched`), proved it **verdict- and
entropy-identical** to the unbatched path (GPU probe 18/18; and the n=53 run's target-1
matches the old run exactly), and it runs **~10× faster**. Memory tuning: 3 models in 16GB is
tight — use `--judge_batched --judge_batch_size 6` (12 OOMs). **Running now:** an n=53
K=8 *diagnostic* (PID 366; NOT the headline — correctly scoped to attack-max +
reframe-b + `--dump_diag`; writes `results/null_control_report.md` + `diag_n53_diag.json`).

## What's BLOCKED and the path to the definitive result
The definitive n≥80 run is BLOCKED (task 22) until: B2 budget-matched run (K~180) + the
null-objective ablation, and B3's deployed-config re-validation. Run recipe is in
`docs/definitive_run_plan.md` (updated). Decision rule is now single + identical in
Experiments/Methods/run-plan (critique_log 21, M1).

## Also done tonight (ungated)
Paper honesty fixes (Abstract scoped to FA — hide was overclaimed; Conclusion/Intro deferred
the verdict; +0.64 stale number removed; fair-pool AUROC 0.69→0.704+CI; "affiliation TBD"
gone); bib `%TODO` citations verified vs arXiv (3 wrong TITLES fixed) + `note→annote` so
scaffolding won't leak into References; the `--dump_diag` + `diagnose_benign_floor.py`
benign-floor tooling; the `prepare_equivalence_audit.py` B5 audit harness. Full punch-list
(25 issues) in `docs/paper_review_punchlist.md` with checkboxes.

## Still-open punch-list items (not yet done): M2, M6, M7–M10, M12, mi3/mi5/mi6 —
positioning (add Kernel Language Entropy + LLM-as-judge + selection-bias RW strands; reframe
the over-stacked novelty sentence; concede CORVUS), reproducibility (name the paraphraser +
hyperparameters), notation overloads. All data-independent; see the punch-list.

## Decisions that may want your input
1. **B2 ablation semantics** — the critic specified a null-objective beam ablation; the exact
   "scrambled objective" implementation is a design choice I'd like to confirm before coding.
2. **The multiday budget** — the budget-matched K~180 run is genuinely multi-day (~180×
   more benign generation). Worth confirming you want to spend it, vs. a moderate budget
   (~40) + the analytic correction.
