#!/usr/bin/env bash
# WATCHER SUPERVISOR v2. Keeps scripts/stop_watcher_v2.sh alive.
#
# WHY THIS EXISTS: the watcher and the GPU wrapper were launched from different wsl.exe
# interop sessions and can die independently. If the watcher dies quietly, the dashboard's
# STOP button silently does nothing -- the download lands in Downloads and no one is polling
# for it. This makes the stop path survive the loss of either process.
#
# It NEVER writes a stop signal and never kills anything. It only starts a watcher.
#
# v1 HAD TWO DEFECTS, both found by adversarial verification, and both of which defeated the
# supervisor's own purpose rather than the watcher's:
#
#   1. HIGH. `pgrep -f 'stop_watcher_v2\.sh'` matches any process whose command line merely
#      CONTAINS that string. `tail -f dashboard/stop_watcher_v2.stdout`, `vim` on the script,
#      or an operator running `ps | grep stop_watcher_v2` all satisfy it -- and that last one
#      is not hypothetical, it is how the run gets health-checked. The watcher could die while
#      the supervisor reported it alive, and the STOP button would silently do nothing: the
#      exact failure this component was added to prevent.
#      FIX: walk /proc and require an argv ELEMENT whose basename is stop_watcher_v2.sh, with
#      argv[0] a shell. A substring can no longer satisfy it -- `tail ...stop_watcher_v2.stdout`
#      has the wrong basename, and `vim scripts/stop_watcher_v2.sh` has the wrong argv[0].
#
#   2. MODERATE. The terminal-state guard read the state and then checked for the process, as
#      two separate commands. If the watcher wrote "stopped" and exited in between, the
#      supervisor relaunched it over an idle machine -- and the relaunched watcher overwrote
#      "stopped" with "running", so the dashboard showed RUNNING with zero GPU processes and
#      re-enabled the STOP button. Self-perpetuating, and it tells the user their machine is
#      busy immediately after they reclaimed it.
#      FIX: re-read the state AFTER finding the watcher absent, and only then relaunch.
#
# Also added: log rotation. An unbounded restart storm was judged correct -- a supervisor that
# gives up leaves no stop path at all, and a line every 38 s is cheap -- but at ~6.8k lines a
# day this log is the only thing growing during one, so it must not grow without bound.

set -u
REPO="/mnt/i/GITHUBPROJECTS/SE Research"
STATUS="$REPO/dashboard/session_status.json"
LOG="$REPO/dashboard/watcher_supervisor.log"
WATCHER="scripts/stop_watcher_v2.sh"
WATCHER_BASE="stop_watcher_v2.sh"
POLL=30
GRACE=8                 # let a fresh watcher write its first status before judging it
LOG_MAX=2097152         # 2 MiB, then rotate

rotate_log () {
  [ -f "$LOG" ] || return 0
  local sz; sz=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
  [ "$sz" -gt "$LOG_MAX" ] 2>/dev/null && mv -f "$LOG" "$LOG.1" && : > "$LOG"
  return 0
}

say () { rotate_log; echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# Exact argv match, not a substring of the command line. See defect 1 above.
watcher_pid () {
  local d pid argv0 base
  for d in /proc/[0-9]*; do
    [ -r "$d/cmdline" ] || continue
    pid=${d#/proc/}
    [ "$pid" = "$$" ] && continue
    argv0=$(tr '\0' '\n' < "$d/cmdline" 2>/dev/null | head -1)
    case "$argv0" in
      *bash|*sh|*dash) ;;
      *) continue ;;
    esac
    while IFS= read -r arg; do
      base=${arg##*/}
      if [ "$base" = "$WATCHER_BASE" ]; then
        echo "$pid"
        return 0
      fi
    done < <(tr '\0' '\n' < "$d/cmdline" 2>/dev/null)
  done
  return 1
}

# Read the state without a JSON parser: we write the file ourselves, one key per line. An
# unreadable, empty or unrecognised file must NOT read as terminal -- treating "I cannot tell"
# as "the stop already happened" would retire the supervisor while the run is still live.
current_state () {
  [ -f "$STATUS" ] || { echo "unknown"; return; }
  local s
  s=$(sed -n 's/.*"state"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATUS" 2>/dev/null | head -1)
  [ -n "$s" ] && echo "$s" || echo "unknown"
}

is_terminal () {
  case "$1" in
    stopped|stopped_dirty) return 0 ;;
    *) return 1 ;;
  esac
}

cd "$REPO" || { say "FATAL: cannot cd to $REPO"; exit 1; }
say "watcher-supervisor v2 armed (pid $$); checking every ${POLL}s; exact-argv match on $WATCHER_BASE"

restarts=0
while true; do
  st=$(current_state)
  if is_terminal "$st"; then
    say "status reads '$st' -- the stop already happened. Supervisor exiting; the machine is the user's."
    exit 0
  fi

  if [ -z "$(watcher_pid)" ]; then
    # Re-read AFTER observing the absence. The watcher writes its terminal state and then
    # exits, so an absence observed here is ambiguous until the state is checked again.
    st=$(current_state)
    if is_terminal "$st"; then
      say "watcher gone and status reads '$st' -- it finished its job. Supervisor exiting."
      exit 0
    fi

    restarts=$((restarts + 1))
    say "WATCHER ABSENT (state='$st') -- relaunching (restart #$restarts)"
    setsid nohup bash "$WATCHER" >> dashboard/stop_watcher_v2.stdout 2>&1 < /dev/null &
    sleep "$GRACE"
    newpid=$(watcher_pid)
    if [ -n "$newpid" ]; then
      say "  relaunched OK as $newpid"
    else
      say "  RELAUNCH FAILED -- the stop path is now manual only:"
      say "  wsl -d Ubuntu-24.04 -- pkill -f venv-wsl"
    fi
  fi
  sleep "$POLL"
done
