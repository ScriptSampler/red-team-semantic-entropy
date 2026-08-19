#!/usr/bin/env bash
# STOP WATCHER. Polls for a stop signal; on finding one, frees the GPU and hands the
# machine back. Runs inside WSL so it can see and kill the CUDA/ROCm processes directly.
#
# WHY A FILE AND NOT A BUTTON CALLBACK: a browser page cannot write to disk. The dashboard's
# STOP button triggers a *download* of a file named STOP.txt, which lands in Downloads. This
# watcher polls every location that file could plausibly arrive in, so the user does not have
# to know which one worked.
#
# The watcher NEVER writes the stop file itself, and nothing in the agent pipeline may write
# it either -- it is the user's channel, and a self-triggering stop would make it useless.

set -u
REPO="/mnt/i/GITHUBPROJECTS/SE Research"
DOWNLOADS="/mnt/c/Users/Abhi/Downloads"
STATUS="$REPO/dashboard/session_status.json"
LOG="$REPO/dashboard/stop_watcher.log"
POLL=15

# Every place a STOP signal may legitimately appear.
CANDIDATES=(
  "$DOWNLOADS/STOP.txt" "$DOWNLOADS/STOP_SESSION.txt" "$DOWNLOADS/stop.txt"
  "$REPO/STOP.txt" "$REPO/STOP_SESSION.txt" "$REPO/stop.txt"
)

say () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

find_signal () {
  for f in "${CANDIDATES[@]}"; do
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

# Anything that holds the GPU. Deliberately a list of NAMES, not PIDs: the chain relaunches
# its stages, so a PID captured at start would be stale by the time STOP arrives.
gpu_procs () {
  pgrep -f 'venv-wsl/bin/python|run_definitive_chain|overnight_|null_control|recompute_fair|n_scaling_grid|wk_defense|rescore_likelihoods' 2>/dev/null
}

write_status () {                    # $1 = state, $2 = detail
  local n; n=$(gpu_procs | wc -l)
  cat > "$STATUS" <<EOF
{
  "state": "$1",
  "detail": "$2",
  "gpu_processes": $n,
  "updated": "$(date '+%F %T')",
  "updated_epoch": $(date +%s)
}
EOF
}

say "stop-watcher armed; polling every ${POLL}s"
say "  signal files watched: ${CANDIDATES[*]}"
write_status "running" "watcher armed"

while true; do
  if SIG=$(find_signal); then
    say "STOP SIGNAL FOUND: $SIG"
    write_status "stopping" "signal at $SIG"

    # Kill the wrapper FIRST so its retry loop cannot relaunch a stage underneath us.
    for p in $(pgrep -f 'run_definitive_chain|overnight_' 2>/dev/null); do
      kill -TERM "$p" 2>/dev/null && say "  TERM wrapper $p"
    done
    sleep 2
    for p in $(gpu_procs); do
      kill -TERM "$p" 2>/dev/null && say "  TERM $p"
    done
    sleep 8
    for p in $(gpu_procs); do
      kill -KILL "$p" 2>/dev/null && say "  KILL $p"
    done
    sleep 2

    if [ -z "$(gpu_procs)" ]; then
      say "GPU FREE -- machine handed back. Checkpoints are per-target; nothing is lost."
      write_status "stopped" "GPU free, safe to use the PC"
    else
      say "WARNING: processes survived SIGKILL: $(gpu_procs | tr '\n' ' ')"
      write_status "stopped_dirty" "some processes survived; check manually"
    fi

    # Consume the signal so a later relaunch is not instantly killed by a stale file.
    mv "$SIG" "$SIG.consumed.$(date +%s)" 2>/dev/null && say "  consumed $SIG"
    say "watcher exiting"
    exit 0
  fi

  write_status "running" "$(gpu_procs | wc -l) GPU process(es)"
  sleep "$POLL"
done
