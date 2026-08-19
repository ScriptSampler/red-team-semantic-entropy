#!/usr/bin/env bash
# Overnight 2026-08-14: the definitive null control, resumed.
#
# Top of the critic's 33-day priority order after the N-scaling grid landed. ~25 GPU-h
# measured (1191 s/target x 69 remaining), so it runs into tomorrow; 11 of 80 targets are
# already checkpointed and it resumes at target 12.
#
# judge_batch_size stays at 6. An audit noted 8/10 might buy ~4 GPU-h, but 6 is the
# known-good value after a documented HSA allocator failure at 12, and an OOM at hour 12
# of a 25-hour run costs more than the speedup saves. Reliability over throughput here.
#
# rc capture is deliberate: run_definitive_chain.sh used `if "$@"; then ... fi; rc=$?`,
# which POSIX defines as the exit status of the IF, i.e. always 0 -- so its Ctrl-C guard
# never fired. This invokes bare and captures immediately.
set -u
cd "/mnt/i/GITHUBPROJECTS/SE Research" || exit 1
export HF_HOME=/home/abhi/.cache/huggingface
PY=./.venv-wsl/bin/python
LOG=/mnt/i/GITHUBPROJECTS/SE\ Research/dashboard/overnight_20260814.log
MAX_TRIES=20

say () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "================ null control, resumed ================"
t=0
while [ "$t" -lt "$MAX_TRIES" ]; do
  t=$((t+1))
  say "START null-control (attempt $t)"
  $PY scripts/null_control.py --tag _defb --only false_alarm --K 50 --n_seeds 3 \
      --judge_model Qwen/Qwen2.5-7B-Instruct --judge_batched --judge_batch_size 6 \
      --dump_diag results/diag_defb.json --checkpoint auto >>"$LOG" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then say "DONE null-control"; break; fi
  if [ "$rc" -eq 130 ] || [ "$rc" -eq 143 ]; then
    say "INTERRUPTED (rc=$rc) -- a human stopped us; not retrying"; exit "$rc"
  fi
  say "FAIL rc=$rc -- resuming from checkpoint in 60s"
  sleep 60
done
say "================ complete ================"
