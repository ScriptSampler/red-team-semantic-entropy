# START HERE — session state as of Sat 2026-08-02 ~05:30 (wound down at 6:00)

## Headline: FA reached the pre-registered n=80 — the definitive pipeline is executing

The **false-alarm attack matrix is COMPLETE at 80/80** (first time at the pre-registered
scale; the resumed 27 ran at ~60% raw success). The **hide cell is running** (15/80 when
the session wound down, ~11 min/target ⇒ ~12h left; `recompute_fair.py` is per-target
resumable, so interrupting it loses nothing). All blockers' *engineering* is done and
committed; what remains is GPU hours + two owed validations.

## If the attack matrix is still running
Leave it — it appends per target. To stop it manually:
`wsl -d Ubuntu-24.04 pkill -f recompute_fair` (safe; resumes exactly where it stopped).
NOTE: the dashboard's STOP button only signals Claude DURING a session; between sessions
use the command above.

## The definitive-run sequence (per docs/definitive_run_plan.md, all decisions locked)
1. **[RUNNING] Attack matrix** `--only se_false_alarm,se_hide --n 80 --tag _def`
   — FA 80/80 done, hide in progress.
2. **[NEXT] Null-objective beam ablation** (~4 GPU-h, 10 targets, resumable):
   `./.venv-wsl/bin/python scripts/null_objective_ablation.py --tag _def --n_targets 10`
   Verdict semantics are in the script header; it gates how the K=180 floor is read.
3. **[THEN] K=180 budget-matched null control** (multiday, per-target checkpointed):
   `./.venv-wsl/bin/python scripts/null_control.py --tag _def --K 180 --n_seeds 3
    --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6
    --dump_diag results/diag_def.json`
   (checkpoint auto-writes results/null_control_ckpt_def.jsonl; safe to kill/resume.)
4. **[AFTER] Analysis**: `diagnose_benign_floor.py results/diag_def.json` (pre-registered
   H_split/H_rtm/H_noise); `prepare_equivalence_audit.py` on the 80-target pool for the
   human audit CSV; fill Experiments from the budget-matched paired net (the ONLY headline:
   attack-max − benign-max, paired CI + sign test; percentile/net-vs-mean are diagnostics).

## Locked numbers + decisions (do not re-litigate)
- **Judge = 0.93 [0.90, 0.96] (n=300, symmetric deployed config, 2026-07-11).** The one
  citation number everywhere. Pre-registered gate FAIL on pos (0.65) is DISCLOSED in
  Methods main text; FA-only re-scope; NLI/exact bracket reported alongside.
- **Benign budget = full ~180** (user 2026-07-11); **decision rule** = adjudicator's
  per-target paired net (attack-max − budget-matched benign-max) CI > 0 at n≥80
  (identical wording in Experiments/Methods/run-plan; both entry-15 deviations disclosed).
- Still owed before any (a) claim: ablation verdict, messy-real-sample judge validation,
  differential over-splitting check, benign-floor diagnosis, human equivalence audit.

## Session log (this session)
Dashboard + STOP button committed (602ffe6; watcher pattern: Downloads/STOP_SESSION*.txt
or repo STOP.txt). Null-control per-target checkpointing (627206a). Null-objective beam
ablation built + 4 tests (a9fc986). Judge re-validated on deployed config → 0.93 locked,
paper swept with CI+n at the validation locus (a86ca69). M12 paraphraser disclosure
(victim Llama itself, greedy, seeded instructions) + hyperparameter values + $M$/$K$/$k$
notation fixes (f77ddeb). RW "Evaluating the evaluation" strand, zheng2023judging verified
(a86ca69). Attack matrix launched and FA completed at 80/80. All tests green.

## Punch-list state: docs/paper_review_punchlist.md
Remaining open: number-landing items (gated on the runs) + the owed validations above.
Everything data-independent is done.
