#!/usr/bin/env bash
# Unattended overnight GPU queue, shortest-decisive-first.
#
# Modelled on scripts/run_definitive_chain.sh, with three deliberate changes.
# Read them before editing this file.
#
# 1. A FAILING JOB DOES NOT BLOCK THE QUEUE. run_definitive_chain.sh is a chain:
#    `run_stage A || exit 1`. That is right for two stages where B consumes A's
#    output. It is wrong for a queue of four independent jobs -- one bad job would
#    idle the card for the rest of the night. Here every job is retried on its own
#    and, if it still fails, is logged and stepped over.
#
# 2. THE RETURN CODE IS ACTUALLY CAPTURED. run_definitive_chain.sh does
#
#        if "$@" >>"$LOG" 2>&1; then ... return 0; fi
#        local rc=$?                       # <-- always 0
#
#    `$?` after a failed `if` with no `else` is the exit status of the *if
#    statement*, which POSIX defines as zero when no branch ran. So `rc` was 0 on
#    every failure path: the rc=130/143 interrupt guard never fired, the log
#    printed "FAILED rc=0", and Ctrl-C was retried like a crash. Verified on this
#    box. Here the command is run bare and `rc=$?` is taken immediately.
#
# 3. AN INTERRUPT STOPS THE WHOLE QUEUE, not just the running job. In a chain,
#    returning from the stage ends the run anyway. In a queue, treating Ctrl-C as
#    "this job is done" would silently promote the next job -- so a human who kills
#    the n-scaling grid would find the null control running instead. rc 130/143, or
#    a signal to this script, aborts everything and the remainder is reported as
#    NOT_STARTED.
#
# Preserved from run_definitive_chain.sh: retry-with-backoff, and the rule that
# rc 130 (SIGINT) and rc 143 (SIGTERM) mean a human stopped us and must NOT retry.
#
# NO SECOND CHECKPOINT LAYER. Every job below is already per-unit checkpointed and
# resumes by being re-invoked with identical arguments. This runner adds no state of
# its own: relaunching it after any interruption is safe and costs at most the unit
# in flight in each job.
#
#   launch:  wsl -d Ubuntu-24.04 -- bash -c '"/mnt/i/GITHUBPROJECTS/SE Research/scripts/overnight_queue.sh"'
#   watch:   tail -f /tmp/overnight_queue.log

set -u

cd "/mnt/i/GITHUBPROJECTS/SE Research" || exit 1
export HF_HOME=/home/abhi/.cache/huggingface
# The caches are all local; refuse to let a 3am job block on a network call.
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1}
export HF_DATASETS_OFFLINE=${HF_DATASETS_OFFLINE:-1}

# Overridable so the queue can be dry-run without a GPU:  PY=echo ./scripts/overnight_queue.sh
PY=${PY:-./.venv-wsl/bin/python}
LOG=${LOG:-/tmp/overnight_queue.log}
MAX_RETRIES=${MAX_RETRIES:-3}
BACKOFF=${BACKOFF:-60}

# ---------------------------------------------------------------- knobs you may set
#
# NULL_EXTRA_FLAGS: scripts/null_control.py is BEING EDITED by another agent to add
# a --dump_judge_detail flag. This runner does not touch that file and does not
# assume the flag exists. Leave empty until the edit lands, then:
#
#     NULL_EXTRA_FLAGS="--dump_judge_detail" ./scripts/overnight_queue.sh
#
# Intentionally unquoted at the call site so multiple flags word-split.
#
# WARNING, read before setting it. null_control.py reuses a completed target only
# when the record's `cfg` matches, and cfg is
#     {K, n_seeds, embedding_model, embed_threshold, judge_model}   (null_control.py:338)
# --dump_judge_detail is not in that set TODAY, so resume keeps the 11 finished
# targets. If the agent adds the new flag to ckpt_cfg, every one of those 11 stops
# matching and the run silently restarts at target 1. Diff null_control.py:338
# after the edit lands and before setting this.
NULL_EXTRA_FLAGS="${NULL_EXTRA_FLAGS:-}"

# RUN_SEPS: scripts/wk_seps_transfer.py has no --tag and hardcodes the SUPERSEDED
# wk9 campaign (15 targets, 12 improved, 2026-06-26) rather than wk9_defb (80/69).
# Its clean-set probe AUROC is campaign-independent and worth having; its transfer
# rate is not quotable. Set RUN_SEPS=0 to skip it entirely.
RUN_SEPS="${RUN_SEPS:-1}"

# Per-job wall-clock budgets, in seconds. 0 = no limit.
# A budget is a guard against a hung job, not a schedule: every job that can be
# stopped resumes from its checkpoint on the next launch.
B_BENCH=${B_BENCH:-900}          # 15 min  -- preflight, prints a number and exits
B_CURSE=${B_CURSE:-3600}         # 1 h     -- expected ~0.25-0.35 h
B_RESCORE=${B_RESCORE:-7200}     # 2 h     -- MEASURED 0.23 h (0.42 s/Q on 2026-08-13)
B_SEPS=${B_SEPS:-3600}           # 1 h     -- expected ~0.25 h, NOT resumable
B_NSCALE=${B_NSCALE:-32400}      # 9 h     -- central 8.22 h, bracket 4.9-10.3 h
B_NULL=${B_NULL:-0}              # no cap  -- deliberately runs into tomorrow

# ------------------------------------------------------------------- queue plumbing
ABORTED=0
# Assigned empty, not merely declared: under `set -u`, `${#arr[@]}` on a declared but
# never-assigned array is an unbound-variable error, which would kill the first job.
J_NAME=(); J_STATUS=(); J_DETAIL=(); J_SECS=()

log () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

on_signal () {
  ABORTED=1
  log "!! runner received a signal - aborting the queue"
}
trap on_signal INT TERM

# run_job <name> <budget_seconds> <command...>
run_job () {
  local name="$1" budget="$2"; shift 2
  local idx=${#J_NAME[@]}
  J_NAME[idx]="$name"; J_STATUS[idx]="NOT_STARTED"; J_DETAIL[idx]=""; J_SECS[idx]=0

  if [ "$ABORTED" -ne 0 ]; then
    return 0
  fi

  local tries=0 rc=0 t0 t1 elapsed
  t0=$(date +%s)
  while [ "$tries" -lt "$MAX_RETRIES" ]; do
    tries=$((tries+1))
    log "START $name (attempt $tries/$MAX_RETRIES, budget ${budget}s)"
    log "      cmd: $*"

    # Bare invocation, rc captured immediately -- see note 2 in the header.
    # --kill-after gives a job that ignores SIGTERM 120s before SIGKILL.
    timeout --signal=TERM --kill-after=120 "$budget" "$@" >>"$LOG" 2>&1
    rc=$?

    t1=$(date +%s); elapsed=$((t1-t0)); J_SECS[idx]=$elapsed

    if [ "$rc" -eq 0 ]; then
      log "DONE  $name (rc=0, ${elapsed}s)"
      J_STATUS[idx]="OK"; J_DETAIL[idx]="rc=0"
      return 0
    fi

    # 124 = timeout fired; 137 = it had to SIGKILL after --kill-after.
    # Logged distinctly from a crash, and NOT retried: the budget exists to stop a
    # job eating the night, and retrying would spend it two more times. Whatever
    # the job checkpointed is kept; relaunch to resume.
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
      log "TIMEOUT $name after ${elapsed}s (budget ${budget}s, rc=$rc) - not retrying, moving on"
      J_STATUS[idx]="TIMEOUT"; J_DETAIL[idx]="rc=$rc after ${elapsed}s"
      return 0
    fi

    # 130 = SIGINT, 143 = SIGTERM: a human stopped us on purpose. Do not fight it,
    # and do not promote the next job over the one they just killed.
    if [ "$rc" -eq 130 ] || [ "$rc" -eq 143 ]; then
      log "$name INTERRUPTED (rc=$rc) - not retrying, aborting the queue"
      J_STATUS[idx]="INTERRUPTED"; J_DETAIL[idx]="rc=$rc"
      ABORTED=1
      return 0
    fi

    if [ "$tries" -lt "$MAX_RETRIES" ]; then
      log "$name FAILED rc=$rc - resuming from its own checkpoint in ${BACKOFF}s"
      sleep "$BACKOFF"
      if [ "$ABORTED" -ne 0 ]; then
        J_STATUS[idx]="INTERRUPTED"; J_DETAIL[idx]="signalled during backoff"
        return 0
      fi
    fi
  done

  log "GAVE UP on $name after $MAX_RETRIES attempts (last rc=$rc) - moving to the next job"
  J_STATUS[idx]="FAILED"; J_DETAIL[idx]="rc=$rc after $MAX_RETRIES attempts"
  return 0
}

skip_job () {                       # record a job we chose not to run
  local idx=${#J_NAME[@]}
  J_NAME[idx]="$1"; J_STATUS[idx]="SKIPPED"; J_DETAIL[idx]="$2"; J_SECS[idx]=0
}

# =============================================================== concurrency guard
# On 2026-08-13 a second agent wrote scripts/overnight_2026_08_13.sh and launched it,
# so two overnight queues existed at once. Both would have run
# rescore_likelihoods.py against the SAME append-only checkpoint
# (results/rescore_likelihoods_ckpt.jsonl) with two 8B models resident on one 16 GB
# card. Interleaved appends of records larger than PIPE_BUF corrupt JSONL lines, and
# that is a silent failure discovered days later. Refuse to start instead.
#
# Override with FORCE=1 only after reading the process list yourself.
BUSY=$(ps -eo args= | grep -E '[.]venv-wsl/bin/python scripts/' | grep -v grep || true)
if [ -n "$BUSY" ] && [ "${FORCE:-0}" != "1" ]; then
  log "REFUSING TO START - a project GPU job is already running:"
  printf '%s\n' "$BUSY" | while IFS= read -r l; do log "    $l"; done
  log "Stop it, or re-run with FORCE=1 if you are certain the two cannot collide."
  exit 3
fi

# ============================================================================ queue
log "================ overnight queue starting ================"
log "log=$LOG  retries=$MAX_RETRIES  backoff=${BACKOFF}s"
log "NULL_EXTRA_FLAGS='${NULL_EXTRA_FLAGS}'  RUN_SEPS=${RUN_SEPS}"

# --- 0. preflight: measure the throughput job 2 is costed on -----------------------
# rescore_likelihoods' own cost table spans 0.10 to 5.48 GPU-h -- a 55x range, because
# the 80 tok/s anchor is a pessimistic bound on prefill, not a measurement. Its
# docstring prescribes exactly this: --estimate-only, then --benchmark, then the real
# pass. Two minutes here turns the night's widest unknown into a number, and it
# writes no checkpoint, so it cannot pollute the run that follows.
#
# ALREADY ANSWERED on 2026-08-13 22:57: 8 questions, 6078 token-positions in 3.2 s
# = 1899 tok/s, and the live pass then held 0.42 s/Q -> 0.23 GPU-h for all 2000.
# Kept in the queue because it costs 90 s and re-pins the number on the night's
# actual machine state; delete this job if you would rather have the 90 s.
run_job "0. rescore --benchmark 8 (preflight, no checkpoint written)" "$B_BENCH" \
  $PY scripts/rescore_likelihoods.py --benchmark 8

# --- 1. winner's curse under _defb -------------------------------------------------
# --tag DEFAULTS TO _def, the superseded campaign. _defb is mandatory here.
# Fixes two numbers that are live and stale in the manuscript right now:
# introduction.tex:119,159 and limitations.tex:54,56 quote -0.383 nats and 45%
# retention from the _def run. 69 targets moved in _defb; 44 need fresh scoring.
# Checkpoint: results/winners_curse_ckpt_se_false_alarm_defb.jsonl (fresh, resumable).
run_job "1. winner's curse re-eval, tag _defb" "$B_CURSE" \
  $PY scripts/winners_curse_reeval.py --tag _defb --cell se_false_alarm

# --- 2. likelihood re-scoring ------------------------------------------------------
# Settles what limitations.tex:32-36 explicitly declines to claim: the real spread s
# of length-normalised sequence log-likelihoods. The simulation says the ceiling atom
# is gone by s=0.001 but nothing in the repo calibrates s. All defaults are correct;
# no arguments needed. Per-question checkpointed at
# results/rescore_likelihoods_ckpt.jsonl, so a timeout is resumable and
# --report-only rebuilds the comparison on CPU.
run_job "2. rescore likelihoods, full 2000-question pass" "$B_RESCORE" \
  $PY scripts/rescore_likelihoods.py

# --- 3. SE -> SEP transfer ---------------------------------------------------------
# CAVEAT, and it is the reason this job is switchable: the script has no --tag and
# hardcodes attacks/wk9 (15 outcomes, 12 improved, 2026-06-26). The definitive
# campaign is wk9_defb (80 outcomes, 69 improved). The probe's own clean AUROC is
# campaign-independent and is the new capability; the transfer percentages it prints
# are measured on the superseded campaign and must not be quoted. It writes
# results/seps_transfer.md unconditionally. No checkpoint: a timeout loses the job.
if [ "$RUN_SEPS" = "1" ]; then
  run_job "3. SE->SEP transfer (clean AUROC only; transfer half is wk9-scoped)" "$B_SEPS" \
    $PY scripts/wk_seps_transfer.py
else
  skip_job "3. SE->SEP transfer" "RUN_SEPS=0 (points at the superseded wk9 campaign)"
fi

# --- 4. the N-scaling grid ---------------------------------------------------------
# The decisive one. N=40, both strata, n=400 evals -> 8.22 GPU-h central
# (results/n_scaling_plan.md section 2; bracket 4.87-10.34 h). Records the full
# C(N,2) verdict matrix per target, so every k <= 40 replays offline for free.
# --n_samples 40 and --strata both are the script's defaults; passed explicitly so
# the log records what was bought. Checkpointed per evaluation at
# results/n_scaling_ckpt.jsonl; if the budget stops it, --report-only rebuilds every
# table from the targets that finished, at zero GPU cost.
run_job "4. N-scaling grid, N=40, both strata" "$B_NSCALE" \
  $PY scripts/n_scaling_grid.py --n_samples 40 --strata both

# --- 5. definitive null control, resume ---------------------------------------------
# 11 of 80 targets done; resumes at target 12. Arguments are byte-identical to
# scripts/run_definitive_chain.sh, which is what wrote the existing checkpoint --
# changing K, n_seeds, embedding_model, embed_threshold or judge_model would
# invalidate all 11. FALSE-ALARM ONLY, deliberately: the judge is validated for that
# direction only and the hide cell would cost ~70 GPU-h for an un-adjudicable number.
# No budget: this one is expected to run into tomorrow.
run_job "5. null control _defb resume (FALSE-ALARM ONLY, from target 12/80)" "$B_NULL" \
  $PY scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 \
      --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 \
      --dump_diag results/diag_defb.json --checkpoint auto $NULL_EXTRA_FLAGS

# ========================================================================== summary
log ""
log "======================= QUEUE SUMMARY ======================="
n_ok=0; n_fail=0; n_timeout=0; n_skip=0; n_never=0; n_int=0
for i in "${!J_NAME[@]}"; do
  s="${J_STATUS[i]}"
  printf -v hms '%02d:%02d:%02d' $(( J_SECS[i] / 3600 )) $(( (J_SECS[i] % 3600) / 60 )) $(( J_SECS[i] % 60 ))
  log "$(printf '%-11s %-9s %s' "$s" "$hms" "${J_NAME[i]}")${J_DETAIL[i]:+   (${J_DETAIL[i]})}"
  case "$s" in
    OK)          n_ok=$((n_ok+1)) ;;
    FAILED)      n_fail=$((n_fail+1)) ;;
    TIMEOUT)     n_timeout=$((n_timeout+1)) ;;
    SKIPPED)     n_skip=$((n_skip+1)) ;;
    INTERRUPTED) n_int=$((n_int+1)) ;;
    NOT_STARTED) n_never=$((n_never+1)) ;;
  esac
done
log "-------------------------------------------------------------"
log "completed=$n_ok  failed=$n_fail  timed_out=$n_timeout  interrupted=$n_int  skipped=$n_skip  never_started=$n_never"
log "full log: $LOG"
log "================ overnight queue finished ================="

# Non-zero iff something needs a human, so a wrapper can tell at a glance.
[ $((n_fail + n_timeout + n_int)) -eq 0 ]
