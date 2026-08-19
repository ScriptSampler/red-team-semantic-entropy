#!/usr/bin/env bash
# WATCHER SUPERVISOR. Keeps scripts/stop_watcher_v2.sh alive.
#
# WHY THIS EXISTS: the watcher and the GPU wrapper were launched from different wsl.exe
# interop sessions and can die independently. If the watcher dies quietly, the dashboard's
# STOP button silently does nothing -- the download lands in Downloads and no one is polling
# for it. The page does now say "WATCHER NOT REPORTING" after 60 s, but that only helps a
# user who is awake and looking at it. This makes the stop path survive the loss of either
# process: both the watcher and this supervisor have to die before the button stops working.
#
# It NEVER writes a stop signal and never kills anything. It only starts a watcher.
#
# THE ONE CASE IT MUST NOT RESTART: a watcher that has already done its job exits 0 after
# freeing the GPU. Restarting it there would re-arm a watcher over an idle machine, flip the
# dashboard from STOPPED back to RUNNING with zero GPU processes, and re-enable the STOP
# button -- telling the user their machine is busy when they have just reclaimed it. So a
# terminal state in the status file ends the supervisor too.

set -u
REPO="/mnt/i/GITHUBPROJECTS/SE Research"
STATUS="$REPO/dashboard/session_status.json"
LOG="$REPO/dashboard/watcher_supervisor.log"
WATCHER="scripts/stop_watcher_v2.sh"
POLL=30
GRACE=8            # seconds to let a fresh watcher write its first status before judging it

say () { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

watcher_pid () { pgrep -f 'stop_watcher_v2\.sh' 2>/dev/null | head -1; }

# Read the state without a JSON parser: the file is written by us, one key per line.
current_state () {
  [ -f "$STATUS" ] || { echo "none"; return; }
  sed -n 's/.*"state"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATUS" | head -1
}

cd "$REPO" || { say "FATAL: cannot cd to $REPO"; exit 1; }
say "watcher-supervisor armed (pid $$); checking every ${POLL}s"

restarts=0
while true; do
  st=$(current_state)
  case "$st" in
    stopped|stopped_dirty)
      say "status reads '$st' -- the stop already happened. Supervisor exiting; the machine is the user's."
      exit 0
      ;;
  esac

  if [ -z "$(watcher_pid)" ]; then
    restarts=$((restarts + 1))
    say "WATCHER ABSENT -- relaunching (restart #$restarts)"
    setsid nohup bash "$WATCHER" >> dashboard/stop_watcher_v2.stdout 2>&1 < /dev/null &
    sleep "$GRACE"
    if [ -n "$(watcher_pid)" ]; then
      say "  relaunched OK as $(watcher_pid)"
    else
      say "  RELAUNCH FAILED -- the stop path is now manual only:"
      say "  wsl -d Ubuntu-24.04 -- pkill -f venv-wsl"
    fi
  fi
  sleep "$POLL"
done
