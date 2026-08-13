#!/usr/bin/env bash
# Overnight GPU queue, 2026-08-13. Shortest-decisive-first.
#
# WHY NOT THE NULL CONTROL FIRST. It has ~60 GPU-h left against a ~10 h night, so it
# yields nothing by morning; it decides the ATTACK verdict, which the paper's spine no
# longer rests on after the measurement reframe; and a critic gate ranked the N-scaling
# grid above it explicitly. The four jobs below total ~9.6 h and each closes an open
# question in the paper. The null control goes last and runs into tomorrow.
#
# A FAILING JOB MUST NOT BLOCK THE QUEUE. Each is retried twice, then skipped and logged.
# That is the difference between one bad job and a wasted night.
set -u
cd "/mnt/i/GITHUBPROJECTS/SE Research" || exit 1
export HF_HOME=/home/abhi/.cache/huggingface
PY=./.venv-wsl/bin/python
LOG=/tmp/overnight_20260813.log
MAX_TRIES=2

say () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

run_job () {                      # $1 = name, $2 = wall-clock cap (s), rest = command
  local name="$1"; shift
  local cap="$1"; shift
  local t=0
  while [ "$t" -lt "$MAX_TRIES" ]; do
    t=$((t+1))
    say "START  $name  (attempt $t, cap ${cap}s)"
    local t0=$SECONDS
    timeout --signal=TERM --kill-after=60 "$cap" "$@" >>"$LOG" 2>&1
    local rc=$?
    local el=$((SECONDS-t0))
    if [ "$rc" -eq 0 ]; then
      say "DONE   $name  in ${el}s"
      return 0
    fi
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
      say "TIMEOUT $name after ${el}s (cap ${cap}s) -- not retrying, moving on"
      return 124
    fi
    # 130/143 = a human stopped us on purpose. Do not fight it, and do not continue.
    if [ "$rc" -eq 130 ] || [ "$rc" -eq 143 ]; then
      say "INTERRUPTED $name (rc=$rc) -- stopping the whole queue"
      exit "$rc"
    fi
    say "FAIL   $name rc=$rc after ${el}s"
    [ "$t" -lt "$MAX_TRIES" ] && sleep 30
  done
  say "SKIP   $name -- gave up after $MAX_TRIES attempts, continuing queue"
  return 1
}

say "================ overnight queue begins ================"

# 1. Measure the real prefill throughput first; the estimate spans 0.1-5.5 h on an
#    assumption the benchmark replaces with a number. 2 minutes buys that.
run_job "rescore-benchmark" 600 \
  $PY scripts/rescore_likelihoods.py --benchmark 8

# 2. Settles whether the near-cap pile-up survives likelihood weighting. Limitations
#    currently declines to claim it in either direction.
run_job "rescore-likelihoods" 25200 \
  $PY scripts/rescore_likelihoods.py

# 3. BOTH Abstract numbers (-0.383 nats, 45% retention) are still from the superseded
#    _def run; 44 of _defb's 69 moved targets need fresh scoring.
run_job "winners-curse-defb" 5400 \
  $PY scripts/winners_curse_reeval.py --tag _defb --cell se_false_alarm --fresh_seed 1

# 4. Cheapest never-run capability; its CPU half is already validated.
run_job "seps-transfer" 5400 \
  $PY scripts/wk_seps_transfer.py

# 5. THE decisive experiment. One N=40 pass records the pairwise verdict matrix, so every
#    budget k <= 40 replays offline for free. Answers the "just raise N" rebuttal that the
#    paper's central claim currently concedes it has not measured.
run_job "n-scaling-N40" 43200 \
  $PY scripts/n_scaling_grid.py --n_samples 40 --strata both --n_per_stratum 200

say "================ queue complete ================"
say "null control NOT resumed by this queue -- it needs the --dump_judge_detail flag"
say "  that is still being added, and it has ~60 GPU-h left. Launch it separately."
grep -E "^\[.*\] (DONE|FAIL|SKIP|TIMEOUT)" "$LOG" | tee -a "$LOG"
