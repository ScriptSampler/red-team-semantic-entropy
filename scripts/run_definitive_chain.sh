#!/usr/bin/env bash
# Definitive _defb chain with auto-restart.
#
# WHY THE RESTART LOOP: the previous chain was a bare `A && B`. A transient failure at
# hour 40 of a multi-day run left the GPU idle until a human noticed. Both stages are
# per-target checkpointed, so a relaunch costs at most one target (~10 min) -- which makes
# an automatic retry strictly better than waiting for someone to look.
#
# WHY --only false_alarm ON THE NULL CONTROL: null_control.py's CELLS contains both cells
# and has no selector by default. But the paper evaluates ONLY the false-alarm direction
# under the null control (paper/sections/introduction.tex), and the LLM judge is scoped to
# FA only (results/judge_validation.md: over-splitting is conservative for false-alarm but
# NOT for hide). Running the hide cell here costs ~70 GPU-h for a number that is both
# unused and un-adjudicable. The MATRIX stage still runs both cells -- the hide attack
# results are needed; it is only the null control that is FA-only.
set -u
cd "/mnt/i/GITHUBPROJECTS/SE Research" || exit 1
export HF_HOME=/home/abhi/.cache/huggingface
PY=./.venv-wsl/bin/python
LOG=/tmp/defb_chain.log
MAX_RETRIES=20

run_stage () {           # $1 = human name, rest = command
  local name="$1"; shift
  local tries=0
  while [ "$tries" -lt "$MAX_RETRIES" ]; do
    tries=$((tries+1))
    echo "[$(date '+%F %T')] START $name (attempt $tries)" | tee -a "$LOG"
    if "$@" >>"$LOG" 2>&1; then
      echo "[$(date '+%F %T')] DONE  $name" | tee -a "$LOG"
      return 0
    fi
    local rc=$?
    # 130/143 = Ctrl-C / SIGTERM: a human stopped us on purpose, do not fight it.
    if [ "$rc" -eq 130 ] || [ "$rc" -eq 143 ]; then
      echo "[$(date '+%F %T')] $name interrupted (rc=$rc) - not retrying" | tee -a "$LOG"
      return "$rc"
    fi
    echo "[$(date '+%F %T')] $name FAILED rc=$rc - resuming from checkpoint in 60s" | tee -a "$LOG"
    sleep 60
  done
  echo "[$(date '+%F %T')] $name gave up after $MAX_RETRIES attempts" | tee -a "$LOG"
  return 1
}

run_stage "matrix _defb (both cells)" \
  $PY scripts/recompute_fair.py --only se_false_alarm,se_hide --n 80 --tag _defb || exit 1

run_stage "null control _defb (FALSE-ALARM ONLY)" \
  $PY scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 \
      --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 \
      --dump_diag results/diag_defb.json --checkpoint auto || exit 1

echo "[$(date '+%F %T')] CHAIN COMPLETE" | tee -a "$LOG"
