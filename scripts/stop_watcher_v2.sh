#!/usr/bin/env bash
# STOP WATCHER v2. Polls for a stop signal; on finding one, frees the GPU and hands the
# machine back. Runs inside WSL so it can see and kill the CUDA/ROCm processes directly.
#
# WHY A FILE AND NOT A BUTTON CALLBACK: a browser page cannot write to disk. The dashboard's
# STOP button triggers a *download* of a file named STOP.txt, which lands in Downloads. This
# watcher polls every location that file could plausibly arrive in, so the user does not have
# to know which one worked.
#
# The watcher NEVER writes the stop file itself, and nothing in the agent pipeline may write
# it either -- it is the user's channel, and a self-triggering stop would make it useless.
#
# v2 fixes, all from a measured verification of v1 (results/stop_mechanism_verification.md):
#   1. Emits dashboard/session_status.js as well as .json. Chromium blocks fetch() from a
#      file:// origin, so the .json the page polled was NEVER readable and the page showed
#      "watcher may not be running" 100% of the time while the watcher was healthy.
#      <script src> does load from file://, so the .js is the channel that actually works.
#   2. Atomic writes (tmp + mv). Under a concurrent reader on drvfs the old in-place
#      `cat > $STATUS` was caught mid-truncate on 4.3% of reads.
#   3. STOP.txt.txt is watched. Explorer hides extensions on this machine, so a
#      hand-made "STOP.txt" is really STOP.txt.txt and v1 ignored it silently.
#   4. A signal that predates this watcher is only honoured if it is RECENT. An ancient
#      file from a previous session must not instantly kill a freshly started run; a press
#      from a minute ago, during a watcher handover, must not be swallowed.

set -u
REPO="/mnt/i/GITHUBPROJECTS/SE Research"
DOWNLOADS="/mnt/c/Users/Abhi/Downloads"
STATUS="$REPO/dashboard/session_status.json"
STATUS_JS="$REPO/dashboard/session_status.js"
PROGRESS="$REPO/dashboard/progress_status.json"
LOG="$REPO/dashboard/stop_watcher.log"
POLL=15
FRESH_SIGNAL_S=600          # a pre-existing signal newer than this is treated as genuine

# Every place a STOP signal may legitimately appear. The .txt.txt entries are not paranoia:
# HideFileExt=1 on this machine, so renaming a New Text Document to "STOP.txt" in Explorer
# produces STOP.txt.txt. The " (1)" entries catch a second download when the first is still
# sitting there unconsumed.
CANDIDATES=(
  "$DOWNLOADS/STOP.txt" "$DOWNLOADS/STOP.txt.txt" "$DOWNLOADS/STOP (1).txt"
  "$DOWNLOADS/STOP (2).txt" "$DOWNLOADS/STOP_SESSION.txt" "$DOWNLOADS/stop.txt"
  "$DOWNLOADS/STOP" 
  "$REPO/STOP.txt" "$REPO/STOP.txt.txt" "$REPO/STOP_SESSION.txt" "$REPO/stop.txt"
  "$REPO/STOP"
)

say () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

find_signal () {
  for f in "${CANDIDATES[@]}"; do
    [ -f "$f" ] && { echo "$f"; return 0; }
  done
  return 1
}

# Anything that holds the GPU. Deliberately a list of NAMES, not PIDs: the chain relaunches
# its stages, so a PID captured at start would be stale by the time STOP arrives. This is
# load-bearing for a second reason -- SIGTERM to the wrapper orphans its python child rather
# than taking it down, and the name sweep is what catches the orphan two seconds later.
gpu_procs () {
  pgrep -f 'venv-wsl/bin/python|run_definitive_chain|overnight_|null_control|recompute_fair|n_scaling_grid|wk_defense|rescore_likelihoods' 2>/dev/null
}

# Embed the progress monitor's JSON only if it parses. A torn read would be a syntax error
# in the .js, and a syntax error anywhere in the file kills the SESSION_STATUS assignment
# too -- the page would go blind for a reason that has nothing to do with the watcher.
progress_blob () {
  [ -f "$PROGRESS" ] || { echo "null"; return; }
  if python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$PROGRESS" 2>/dev/null; then
    cat "$PROGRESS"
  else
    echo "null"
  fi
}

write_status () {                    # $1 = state, $2 = detail
  local n; n=$(gpu_procs | wc -l)
  local now_h; now_h=$(date '+%F %T')
  local now_e; now_e=$(date +%s)

  cat > "$STATUS.tmp" <<EOF
{
  "state": "$1",
  "detail": "$2",
  "gpu_processes": $n,
  "updated": "$now_h",
  "updated_epoch": $now_e
}
EOF
  mv -f "$STATUS.tmp" "$STATUS"

  {
    echo "window.SESSION_STATUS = {"
    echo "  \"state\": \"$1\","
    echo "  \"detail\": \"$2\","
    echo "  \"gpu_processes\": $n,"
    echo "  \"updated\": \"$now_h\","
    echo "  \"updated_epoch\": $now_e,"
    echo "  \"watcher_pid\": $$,"
    echo "  \"watcher_version\": 2"
    echo "};"
    echo "window.PROGRESS_STATUS = $(progress_blob);"
    echo "window.STATUS_TICK = $now_e;"
  } > "$STATUS_JS.tmp"
  mv -f "$STATUS_JS.tmp" "$STATUS_JS"
}

do_stop () {                          # $1 = signal path
  local SIG="$1"
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
}

say "stop-watcher v2 armed (pid $$); polling every ${POLL}s"
say "  signal files watched: ${CANDIDATES[*]}"

# Startup arbitration. A signal already on disk is ambiguous: it may be a press from seconds
# ago that a dying watcher never saw, or a relic of a session that ended days back. Age
# decides, because the two failure modes are not symmetric -- swallowing a fresh press leaves
# the user unable to reclaim the machine, while acting on a relic only costs a restart.
if SIG=$(find_signal); then
  AGE=$(( $(date +%s) - $(stat -c %Y "$SIG") ))
  if [ "$AGE" -le "$FRESH_SIGNAL_S" ]; then
    say "pre-existing signal is ${AGE}s old (<= ${FRESH_SIGNAL_S}s) -- treating as GENUINE"
    do_stop "$SIG"
  else
    say "pre-existing signal is ${AGE}s old -- stale, consuming without acting"
    mv "$SIG" "$SIG.stale.$(date +%s)" 2>/dev/null
  fi
fi

write_status "running" "watcher armed"

while true; do
  if SIG=$(find_signal); then
    do_stop "$SIG"
  fi
  write_status "running" "$(gpu_procs | wc -l) GPU process(es)"
  sleep "$POLL"
done
