#!/usr/bin/env bash
# WATCHER SUPERVISOR v3. Keeps scripts/stop_watcher_v2.sh alive.
#
# WHY THIS EXISTS: the watcher and the GPU wrapper were launched from different wsl.exe
# interop sessions and can die independently. A quietly dead watcher makes the dashboard's
# STOP button do nothing -- the download lands in Downloads and no one is polling for it.
# This makes the stop path survive the loss of either process.
#
# It NEVER writes a stop signal and never kills anything. It only starts a watcher.
#
# THE WHOLE DIFFICULTY IS "IS THE WATCHER ALIVE", AND IT HAS BEEN WRONG TWICE.
#
#   v1 used pgrep -f 'stop_watcher_v2\.sh', which matches any process whose command line
#   merely CONTAINS the string -- including `tail -f dashboard/stop_watcher_v2.stdout` and
#   `ps | grep stop_watcher_v2`, which is how the run gets health-checked. A dead watcher
#   would have been reported alive.
#
#   v2 required an argv ELEMENT whose basename was the script, with argv[0] a shell. Better,
#   but verification found four surviving false positives, every one reproduced live:
#     - `bash -n path/stop_watcher_v2.sh`             (a syntax check registers as a watcher)
#     - `bash /some/other/copy/stop_watcher_v2.sh`    (a stale or test copy, running against a
#                                                      different REPO, permanently masks a dead
#                                                      watcher -- the worst, because it persists)
#     - `sh -c 'cmd' /path/stop_watcher_v2.sh`        (path sitting in the $0 slot)
#     - `find ... -exec sh -c 'lint "$0"' {} \;`      (the same idiom, common)
#   v2 also matched the shell by SUFFIX (*bash|*sh|*dash), which admits ssh, fish and refresh.
#
# v3 requires all four of: argv[0] is EXACTLY a known shell by basename; argv[1] exists and is
# not an option; argv[1]'s basename is the watcher script; and argv[1], resolved against that
# process's own /proc/<pid>/cwd and canonicalised, is THIS repo's copy. A false positive here
# is the failure that costs the user their machine, so it is worth four conditions. A false
# negative only costs a duplicate watcher, which is noisy but safe.
#
# ALSO FIXED IN v3: v2 checked the status file at the TOP of the loop and exited on a terminal
# state without confirming the watcher was actually gone. A live watcher plus a stale "stopped"
# status -- realistically, the supervisor starting before the watcher -- made it exit
# immediately and stop supervising, silently. The fix is a deletion: the only terminal check
# is the one AFTER an absence is observed, which gives the same behaviour following a real stop
# with none of the hazard.

set -u
REPO="/mnt/i/GITHUBPROJECTS/SE Research"
STATUS="$REPO/dashboard/session_status.json"
LOG="$REPO/dashboard/watcher_supervisor.log"
WATCHER="scripts/stop_watcher_v2.sh"
WATCHER_BASE="stop_watcher_v2.sh"
WATCHER_CANON=$(readlink -f "$REPO/$WATCHER" 2>/dev/null || echo "$REPO/$WATCHER")
POLL=30
GRACE=8                 # let a fresh watcher write its first status before judging it
LOG_MAX=2097152         # 2 MiB per file, one .1 generation

rotate_one () {
  local f=$1 sz
  [ -f "$f" ] || return 0
  sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
  case "$sz" in ''|*[!0-9]*) return 0 ;; esac
  [ "$sz" -gt "$LOG_MAX" ] && mv -f "$f" "$f.1" 2>/dev/null && : > "$f"
  return 0
}

# All three files that grow during a restart storm, not just the one v2 rotated.
rotate_logs () {
  rotate_one "$LOG"
  rotate_one "$REPO/dashboard/watcher_supervisor.stdout"
  rotate_one "$REPO/dashboard/stop_watcher_v2.stdout"
  return 0
}

say () { rotate_logs; echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

watcher_pid () {
  local d pid argv0 argv1 cwd cand
  for d in /proc/[0-9]*; do
    [ -r "$d/cmdline" ] || continue
    pid=${d#/proc/}
    [ "$pid" = "$$" ] && continue

    { IFS= read -r -d '' argv0 || argv0=""; IFS= read -r -d '' argv1 || argv1=""; } < "$d/cmdline" 2>/dev/null

    # argv[0] must BE a shell, not merely end in one: a suffix test admits ssh and fish.
    case "${argv0##*/}" in bash|sh|dash|ash) ;; *) continue ;; esac

    # argv[1] must be the script itself. An option in that slot means the shell is doing
    # something to the file (-n syntax check, -c inline command), not running it.
    [ -n "$argv1" ] || continue
    case "$argv1" in -*) continue ;; esac
    [ "${argv1##*/}" = "$WATCHER_BASE" ] || continue

    # And it must be OUR copy. A stale copy elsewhere running against a different REPO would
    # otherwise mask a dead watcher indefinitely.
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
    case "$argv1" in
      /*) cand="$argv1" ;;
      *)  cand="$cwd/$argv1" ;;
    esac
    cand=$(readlink -f "$cand" 2>/dev/null) || continue
    [ "$cand" = "$WATCHER_CANON" ] || continue

    echo "$pid"
    return 0
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
say "watcher-supervisor v3 armed (pid $$); every ${POLL}s; canonical target $WATCHER_CANON"

restarts=0
while true; do
  if [ -z "$(watcher_pid)" ]; then
    # Only NOW does the status matter. A watcher writes its terminal state and then exits, so
    # an observed absence is what makes a terminal reading meaningful.
    st=$(current_state)
    if is_terminal "$st"; then
      say "watcher gone and status reads '$st' -- it finished its job. Supervisor exiting; the machine is the user's."
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
