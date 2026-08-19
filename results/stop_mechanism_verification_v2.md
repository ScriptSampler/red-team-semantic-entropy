# STOP mechanism — adversarial verification of the v2 rewrite

Date: 2026-08-19 (session ~01:45–02:05)
Scope: `dashboard/session_dashboard.html`, `scripts/stop_watcher_v2.sh`, `scripts/watcher_supervisor.sh`
Method: real browsers on a real `file://` origin; isolated copies of both shell scripts in a
scratchpad with `SIMSIG_*` / `SIM*_MARKER` paths and process patterns. No live process was
signalled; nothing in the repo was edited except this file.

## Verdict

**The rewrite is not a regression on any axis I could test.** The change that mattered — the
status channel — is fixed and verified in a real browser. The kill path, the atomic writes, the
arbitration branches, the new watched paths and `progress_blob` all pass.

The two findings worth acting on are both in the **supervisor**, the component added last, and
both defeat the supervisor's own purpose rather than the watcher's. Neither is present in the
watcher itself.

Live state at end of session: PIDs 5751 (watcher), 6506 (supervisor), 457 (overnight), 473
(null_control) all alive; watcher last wrote its status 4 s before the final check.

---

## Findings, ranked by "how likely is this to leave the user unable to reclaim their machine"

### R1 — HIGH. The supervisor's `pgrep -f` can be fooled into thinking a dead watcher is alive

`watcher_pid()` is `pgrep -f 'stop_watcher_v2\.sh'`. `-f` matches the **whole argv of any
process**, so anything that merely names the file counts as a live watcher.

Demonstrated on the isolated copy: with no watcher running at all, a decoy process whose argv
merely contained the script name made `pgrep -cf` report `1`. Real-world triggers are ordinary:
`vim scripts/stop_watcher_v2.sh`, `tail -f dashboard/stop_watcher_v2.stdout`, `less`, a `grep`
over the repo — or a verification agent's own `pgrep`.

Consequence: the watcher dies, the supervisor sees a "live" watcher, never relaunches, and the
STOP button silently does nothing. That is precisely the failure the supervisor was built to
prevent, and it is masked for as long as the decoy process lives.

Suggested fix: anchor the match (`pgrep -f '^bash .*stop_watcher_v2\.sh$'`), or better, have the
watcher write a PID file and have the supervisor validate `/proc/<pid>/cmdline` directly.

### R2 — MODERATE. The terminal-state guard has a small race that relaunches a watcher over an already-stopped machine

The ordering you asked about **is correct**: `st=$(current_state)` runs before `watcher_pid()`.
Verified for both terminal states — with `stopped` / `stopped_dirty` in the status file and no
watcher running, the supervisor logged "the stop already happened", exited, and relaunched
nothing (`pgrep` count 0).

But the state read and the process check are two separate commands. If the supervisor reads the
state while the watcher is still inside `do_stop` (state still `running`/`stopping` — a ~12 s
window) and the watcher then writes `stopped` and exits before the supervisor's `pgrep` runs, the
guard is bypassed.

I staged that post-race world exactly (status `running`, no watcher, no GPU processes, signal
already consumed) and the supervisor relaunched. Resulting status:
`"state":"running","gpu_processes":0` — which the dashboard renders as **RUNNING with 0 GPU
processes and a re-enabled STOP button**, right after the user reclaimed the machine.

It is also self-perpetuating: the relaunched watcher overwrites `stopped` with `running`, so the
supervisor never afterwards sees a terminal state and never exits.

Window is the few milliseconds between two subshells against a 30 s poll — order 0.01–0.03% per
stop. Low probability, but the resulting state is confusing and does not self-heal.

Suggested fix: re-read `current_state` immediately after finding the watcher absent and before
relaunching.

### R3 — MODERATE, and the one link I deliberately did not test

Everything around the download path checks out: the Windows Downloads known folder resolves to
`C:\Users\Abhi\Downloads` (shell namespace and registry agree), matching the watcher's hardcoded
`DOWNLOADS`. Opera GX is the registered default handler for both `http` and `.html`. Neither
Opera GX nor Chrome sets `download.default_directory` or `prompt_for_download`, so a download
lands silently in Downloads.

**Not tested: actually clicking STOP.** Doing so would have killed the live run. The
browser-click → file-on-disk link therefore remains verified only by inspection.

### R4 — LOW/MODERATE. A syntactically invalid `.js` shows stale data as current for up to ~60 s

A `<script>` whose body fails to parse still fires **`onload`** — the resource loaded; the parse
error goes to `window.onerror`. So `fails` resets to 0, `render()` runs, and because the failed
parse left the previous globals in place, the page redisplays the **last good values with no
warning**.

Measured: with an invalid `.js` in place, the browser logged three `"Script error."` events while
the display sat unchanged and unflagged at the previous value.

Bounded by two existing nets: `age > 60` flips the card to "WATCHER NOT REPORTING", and the 90 s
`frozen` check adds "(page is reading a cached status — reload)". So worst-case exposure is ~60 s
of stale-looking-current data.

Currently unreachable in practice — see PASS 5, `progress_blob` never emitted invalid JSON under
any torn input — but this is the failure mode to remember if the `.js` format changes.

Suggested fix: inside `onload`, treat a `STATUS_TICK` that did not advance as a failed poll.

### R5 — LOW. A `stat` failure silently skips startup arbitration (but cannot crash the watcher)

You asked specifically whether a missing/unreadable file can crash the watcher before it arms.
**It cannot.** Confirmed by injecting a `stat` that always fails:

`AGE=$(( $(date +%s) - $(stat -c %Y "$SIG") ))` raises `syntax error: operand expected`. Bash
aborts the enclosing `if … fi` compound but does **not** exit the shell (no `set -e`; `set -u`
never fires because `[ "$AGE" … ]` is never reached — verified separately). The watcher then arms
normally and the main loop picks the signal up on its first pass and acts on it.

Two caveats: the requirement is met by accident rather than by design, and nothing is logged to
explain the skipped arbitration; and on that path a *stale* relic would be acted on. Given your
stated asymmetry — acting on a relic only costs a restart — the direction is right.

Suggested fix: `$(stat -c %Y "$SIG" 2>/dev/null || echo 0)`, and log when it happens.

### R6 — LOW. Negative ages are accepted as fresh

Observed `pre-existing signal is -1s old` and `-2s old`: drvfs mtimes can land slightly in the
future relative to the WSL clock. `-le 600` accepts any negative age, so a future-dated file is
always GENUINE. Safe direction (a fresh press is never swallowed) and self-limiting (the file is
consumed on the first pass). Only worth a lower bound for tidiness.

### R7 — Restart storm: unbounded retry is the right call. I agree with you.

Verified each failed attempt logs `WATCHER ABSENT -- relaunching (restart #N)`, then
`RELAUNCH FAILED -- the stop path is now manual only:` followed by the
`wsl -d Ubuntu-24.04 -- pkill -f venv-wsl` fallback. At the real cadence that is one attempt per
~38 s (POLL 30 + GRACE 8), three lines each — roughly 6.8k lines/day, well under a megabyte.

I agree with unbounded, for your reason: a supervisor that gives up converts a recoverable
condition into no stop path at all. Two refinements instead of a cap:

- **Add log rotation.** `watcher_supervisor.log` grows without bound; in a storm it is the only
  thing growing.
- Optionally back off to ~5 min after N consecutive failures — keeps the path alive forever while
  cutting log volume. Do not ever stop retrying.

### R8 — Double-arm: pattern is adequate; comm truncation is a non-issue

`pgrep`'s 15-character `comm` truncation does not apply here because `-f` matches full argv — and
the watcher's `comm` is `bash` anyway, so a non-`-f` pgrep would match nothing at all (`-f` is
required and correctly used). Argv-form sensitivity: `bash scripts/stop_watcher_v2.sh`,
`./scripts/stop_watcher_v2.sh` and an absolute path all match; only renaming the file would miss.

Two concurrent watchers would not corrupt anything — writes are atomic and the loser's `mv` fails
silently — so the harm would be cosmetic. The realistic double-arm risk is R2, not a pattern miss.

---

## Verified as working (no action needed)

**1. `?t=` on a `file://` origin — WORKS. This was the highest-risk unknown and it is clear.**

- Real Chrome (`--headless=new`) on the **real** dashboard at
  `file:///I:/GITHUBPROJECTS/SE%20Research/dashboard/session_dashboard.html` rendered live values:
  `RUNNING — the machine is in use`, `2 GPU process(es)`, procs `2`, plus the progress card.
- Chromium via puppeteer, real `file://` origin, five successive polls with changing values:
  `11 → 22 → 33 → 44 → 55`, `STATUS_TICK` advancing each time, **zero** page errors.
  (Requirement was 3 successive polls; 5 observed.)
- **The cache question is moot:** I ran the same page with the query string removed and it *also*
  updated (`55 → 66 → 77 → 88`). Chromium did not serve a cached `file://` script either.
  **Neither failure mode is real. Keep `?t=` as cheap insurance — it costs nothing and guards
  against a browser that does cache.**
- Degradation path confirmed: deleting the `.js` fires `onerror` and the page correctly reaches
  `NO STATUS FILE (n failed polls)` / "the watcher is probably not running".

*Substitution noted:* Opera GX is the machine's default browser but ships no working `--headless`
build, so I could not drive it directly. Both engines I did test are Chromium, as is Opera GX.

**2. Atomic writes — fixed.** 400 writes under a concurrent validating reader: **2,824 reads, 0
zero-length, 0 syntactically invalid, 0 leftover `.tmp`**. (v1 measured 4.3% torn.)

**3. Startup arbitration — both branches correct.** 599 s → GENUINE, 601 s → stale (boundary
arithmetic on `stat -c %Y` is right). Fresh → `do_stop`, signal renamed `.consumed.<epoch>`, final
state `stopped`. Stale → renamed `.stale.<epoch>`, watcher continues and arms with state
`running`. Crash-resistance covered in R5.

**4. New watched paths — all 12 matched.** `STOP.txt`, `STOP.txt.txt`, `STOP (1).txt`,
`STOP (2).txt`, `STOP_SESSION.txt`, `stop.txt`, extensionless `STOP`, in Downloads and repo root.
The **trailing space** after `"$DOWNLOADS/STOP"` is **harmless** — the array holds exactly 12
elements with no empty or whitespace entry, confirmed both in the isolated copy and in the live
watcher's own startup log line. Directories named like a signal are correctly ignored by `[ -f ]`.
Note `/mnt/c` and `I:` are case-insensitive, so `stop.txt` is redundant with `STOP.txt` — harmless,
and it means a lowercase hand-made file is caught too.

**5. `progress_blob` — robust.** python3 3.12.3 present at `/usr/bin/python3` (so it will not
silently emit `null` forever). Valid file → embedded (17 keys). Truncated mid-object,
zero-length, missing, and binary garbage → `null` **with the `.js` still structurally valid in
every case**. Cost 35 ms per call = **0.23% of one core** at the 15 s cadence (full `write_status`
109 ms) — not a meaningful load. `progress_monitor.py` also writes atomically
(`tmp.replace(outp)`, line 775), which closes the validate-then-`cat` TOCTOU window in
`progress_blob`; that dependency is worth remembering if the monitor's write is ever changed.

**6. Kill path — unchanged and still correct**, exercised end-to-end on the isolated copy via the
`STOP (1).txt` candidate with a fake wrapper, an orphaned child, and a TERM-ignoring child:

```
+00.03s  STOP SIGNAL FOUND: .../SIMSIG (1).txt
+00.06s    TERM wrapper 11940
+02.07s    TERM 11942        <- orphaned child, caught by the name sweep
+02.07s    TERM 11943
+10.10s    KILL 11943        <- SIGTERM-ignoring process escalated correctly
+12.13s  GPU FREE -- machine handed back
+12.17s    consumed .../SIMSIG (1).txt   -> .consumed.<epoch>
```

All four protected PIDs verified alive before, during and after.

**7. Supervisor `current_state` parse — safe in every malformed case.** Missing → `none`;
zero-length → empty; truncated mid-write → empty; unrecognised state → passed through. **None of
these is treated as terminal and none crashes the loop** — in every case the supervisor went on to
relaunch the watcher, which is the safe direction. `stopping` correctly does *not* count as
terminal. Extra spaces around the colon parse fine. A decoy `state` string inside `detail` cannot
win because `write_status` always emits `"state"` as the first key and `detail` is a
machine-generated path that cannot contain a double quote — safe by construction, though the parse
stays coupled to that format.

---

## Cosmetic, non-blocking

- On the `NO STATUS FILE` path the page clears the state text and detail but leaves
  `GPU processes` showing the last known number (observed `88` next to "NO STATUS FILE"). Mildly
  contradictory; consider clearing it.
- After a legitimate stop the watcher exits, so `STATUS_TICK` stops advancing and after 90 s the
  detail line reads "(page is reading a cached status — reload)". The headline still reads STOPPED
  and the button stays disabled, so this is only a confusing subtitle. (The `age > 60` staleness
  flip correctly does *not* fire, because it is gated on `state === "running"`.)
- `renderProgress` would print "undefined / undefined" for a progress object lacking `progress`.
- The rate-disagreement warning would render "NaN%" if `stable === false` while `disagreement` is
  `null`.

## What I did not test

- Clicking the STOP button (would kill the live run) — see R3.
- Opera GX directly (no headless build) — see the substitution note under PASS 1.
- The live watcher and supervisor were never signalled, restarted or modified; all simulation
  processes were reaped at the end.

---

# Supervisor v2 — verification of the repairs

Date: 2026-08-19 (~02:10–02:20). Subject: `scripts/watcher_supervisor_v2.sh`, live as PID 15254;
v1 (6506) confirmed gone. Watcher 5751, wrapper 457, run 473 untouched throughout; exactly one
watcher process on the system before, during and after.

**Both repairs work.** The race is gone (8/8 trials) and the detector rejects every decoy that
fooled v1. Two new items below, plus an answer on the `stat -c %Y` question.

## Ranked findings

### SV1 — MODERATE (was HIGH in v1). The detector is much tighter, but four false positives remain

Confirmed fixed — the v1 decoys no longer register:

| decoy | v1 | v2 |
|---|---|---|
| `tail -f dashboard/stop_watcher_v2.stdout` | MATCH | no match (wrong basename) |
| `vim scripts/stop_watcher_v2.sh` | MATCH | no match (argv[0] not a shell) |
| login shell, argv[0] = `-bash` | — | no match |

And no false negatives: all four legitimate launch forms are still found — `/usr/bin/bash
/abs/path/...`, `bash scripts/...` (relative), `./stop_watcher_v2.sh` (shebang exec), and the
supervisor's own `setsid nohup bash ...` form. Against the real system the detector returned
exactly one PID, 5751, with no second match.

But the rule "**any** argv element whose **basename** equals `stop_watcher_v2.sh`" is still
satisfiable by processes that are not a running watcher. Four confirmed, all reproduced live:

1. **`bash -n path/stop_watcher_v2.sh` — a syntax check, not a running watcher.** MATCHED. This is
   the sharpest one: linting the watcher (pre-commit hook, CI, or an operator checking it parses)
   makes the supervisor believe it is running. Short-lived, so it must coincide with the 30 s poll.
2. **A stale copy running from anywhere else** — `bash /oldbackup/stop_watcher_v2.sh`. MATCHED.
   The worst of the four because it **persists**: an old or test copy left running from a backup
   directory, pointed at a different `REPO`, makes the supervisor permanently believe the stop path
   is healthy while the real watcher is dead. Note this also means an isolated verification copy
   that keeps the real filename would register — I avoided that by naming mine `SIMWATCH_v2.sh`,
   but nothing enforces it.
3. **`sh -c 'cmd' /path/stop_watcher_v2.sh`** — the path in the `$0` slot. MATCHED.
4. **`find ... -exec sh -c 'lint "$0"' {} \;`** — the same shape, and a very common idiom. MATCHED.

Related: the argv[0] filter `*bash|*sh|*dash` is a suffix match, not a shell whitelist. It also
admits `ssh`, `zsh`, `fish`, `csh`, `ksh` — and `refresh`, or any binary ending in `sh`. That only
widens the surface for the above; the basename rule is the real gate.

**Cheapest effective fix:** require the basename match at **argv[0] or argv[1] only**, instead of
any element. That kills 1, 3 and 4 outright while keeping every true positive (the real watcher
always has the path at argv[0] or argv[1]). To also kill 2, resolve the argv path against
`/proc/<pid>/cwd` and require it to equal `$REPO/scripts/stop_watcher_v2.sh`. A watcher-written PID
file, validated against `/proc/<pid>/cmdline`, would settle all four.

Robustness of the walk itself is good: 41 kernel threads with empty `cmdline` were traversed
without error, no stderr, clean exit 1 when absent, no `hidepid` in effect, and 71 ms per walk
every 30 s (~0.24% duty).

### SV2 — LOW/MODERATE. The mirror hazard you asked about is real: v2 can retire while the run is live

Staged a **live watcher plus a stale `stopped` status** and the supervisor exited immediately:

```
status reads 'stopped' -- the stop already happened. Supervisor exiting; the machine is the user's.
watcher still alive after supervisor exit? 1
```

The top-of-loop terminal check fires on the state alone — it does not confirm the watcher is
absent or the GPU idle. Realistic trigger: the supervisor is started **before** the watcher (a
plausible boot order), reads the previous session's terminal state, and retires within a second.

Severity is below SV1 because the watcher is alive, so STOP still works — the loss is supervision,
silently. It does not cost the user their machine on its own; it removes the safety net.

**Fix, and it is a deletion:** drop the top-of-loop terminal check and rely solely on the
post-absence re-read you already added. After a real stop the watcher exits, absence is observed,
the re-read returns `stopped`, and the supervisor exits — same outcome, no mirror hazard.

Note `current_state()` returning literal `unknown` for missing/empty/unparseable, with `unknown`
explicitly non-terminal, is right and I verified it: none of those cases is treated as terminal.

### SV3 — LOW. Rotation covers the log but not the `.stdout` files

`say()` uses `tee -a "$LOG"`, so every line also goes to stdout, which the launcher redirects into
`dashboard/watcher_supervisor.stdout`. That file, and `dashboard/stop_watcher_v2.stdout` which
receives each relaunched watcher's output, have **no rotation at all** — so during the restart
storm rotation was added for, two of the three growing files are still unbounded.

## Confirmed fixed / correct

**The race (your MODERATE finding) is fixed.** Restaged exactly as before — status `running`, no
watcher, flipped to `stopped` during the ~71 ms `/proc` walk so the second read lands after the
transition. **8 trials, the second read caught the terminal state 8 times, zero relaunches.** v1
relaunched in this scenario every time. Log line is unambiguous:
`watcher gone and status reads 'stopped' -- it finished its job.`

**The double read does not delay a genuine relaunch.** With the watcher truly dead and state
non-terminal, `WATCHER ABSENT (state='running') -- relaunching` was logged in the same second as
arming. The second read costs one extra `sed` (~ms); no extra poll, no added window.

**Log rotation is correct on every axis I tested:**

- Missing log: `say()` survives and creates it.
- Oversized log (2.64 MB): rotates to `.1`, live log drops to 45 B, **the line being written is
  present in the new log and all 220,000 old lines are intact in `.1`** — because `rotate_log`
  runs *before* the `echo | tee`, the in-flight line cannot be lost.
- Single `.1` generation; a second rotation discards the older one, as designed.
- **`stat` failing while the log exists is non-fatal** — the line is still logged and `say()`
  returns 0. Same for `stat` emitting non-numeric garbage. The `|| echo 0` plus the unconditional
  `return 0` do their job, so logging cannot go down at the moment it matters most.

## Your `stat -c %Y` decision: you were right, don't churn it

Your reasoning holds for the dominant case. I probed for a path where `stat` fails while the file
still exists:

- **Permissions.** `stat` needs `+x` on the parent directory, and `find_signal`'s `[ -f ]` stats
  too — so if `stat` fails for permissions, `find_signal` would not have returned the path in the
  first place. Consistent with your reasoning.
- **Dangling symlink.** `[ -f ]` follows and rejects it. Not a path.
- **A second watcher consuming the signal in between** (possible, given double-arm). `stat` fails,
  arbitration is skipped, the main loop finds nothing because the other instance renamed it. Benign.
- **A transient drvfs/9p error between `find_signal` and `stat`.** This is the one real gap: the
  file exists, `stat` fails anyway, and the main loop then acts on it regardless of age. Requires a
  transient FS error in a microseconds-wide window *and* a stale relic present at startup.

Even in that last case the consequence does not threaten the property we care about. The failure
direction is "a relic gets acted on" — the machine gets **freed**, which is the safe direction for
"can the user reclaim their PC". It is also self-limiting: the watcher renames the file, so it
happens at most once. And I verified in the v1 pass that the watcher still **arms** in every
`stat`-failure case, so the stop path is never lost.

So: **no handover needed.** If you touch that block for another reason, `$(stat -c %Y "$SIG"
2>/dev/null || echo 0)` plus a log line converts a silent skip into an explicit one for free — but
it does not justify churning a verified watcher on its own.

---

# Supervisor v3 — final hardening round

Date: 2026-08-19 (~02:25–02:32). Subject: `scripts/watcher_supervisor_v3.sh`, live as PID 25204;
v2 (15254) confirmed gone. Watcher 5751, wrapper 457, run 473 untouched; one watcher throughout.
Simulated watchers named `SIMW3_watcher.sh`, never the real filename.

**Verdict: v3 is clean on the axis that matters, and I agree you should stop here.** No false
positive survived any probe. Every residual is a false *negative* — a duplicate watcher, bounded
at one — or a silent-but-harmless rotation edge. Nothing below can leave the user unable to
reclaim the machine.

## Answers to the four things you asked

### 1. Bind mount / hardlink / symlink canonicalisation — no false positive found

| construction | result |
|---|---|
| symlink at another path -> the real script | **FOUND** (correct: it is the real watcher) |
| symlink named `SIMW3_watcher.sh` -> a *different* script | rejected (correct) |
| **hardlink**: same inode, second path | rejected — false negative, safe |
| launched via a **symlinked repo path** (cwd is the symlink) | **FOUND** (correct) |

The hardlink case is the interesting one and it lands the safe way: `readlink -f` canonicalises by
*path*, and a hardlink has no distinguished "original", so the second path is simply not the
canonical target. Same inode, genuinely the same script, reported absent — a duplicate watcher, not
a masked dead one.

**Bind mount: not tested, and I judge it out of scope.** I run as uid 1000 and `mount --bind`
requires root. An unprivileged user cannot bind-mount over the watcher path in the supervisor's
mount namespace, and a mount made inside a private namespace (`unshare -m`) is invisible to the
supervisor — so neither is a route to a false positive. Anyone able to bind-mount as root over the
repo already owns the machine. Your instinct to distrust drvfs path handling was reasonable, but
`readlink -f` behaved correctly on 9p in every case above, including through a symlinked cwd.

### 2. Unreadable / deleted cwd — two confirmed false negatives, both safe

- **Different user.** `/proc/<pid>/cwd` is owner-only. Demonstrated on pid 1 (root): `cmdline`
  reads fine, `readlink cwd` returns empty. A watcher running as another user is invisible.
- **Deleted cwd.** `readlink` returns `/tmp/gonedir (deleted)`; `readlink -f` on that path then
  fails and the code `continue`s. Confirmed.

Both cost a duplicate watcher, nothing worse. One free improvement: the `cwd=$(readlink …) ||
continue` line gates **every** candidate, including those whose `argv[1]` is already absolute and
needs no cwd at all. Moving that read inside the relative-path branch of the `case` removes both
false negatives for absolute-path launches at zero risk.

### 3. argv[1] legitimately being an option — yes, and it costs exactly one duplicate

All five forms are false negatives, confirmed live: `bash -x`, `bash --norc`, `bash --posix`,
`bash -e`, and `bash -- scripts/…`.

`bash -x scripts/stop_watcher_v2.sh` is a realistic debug launch, so this will happen eventually.
I measured the consequence rather than assuming it: **bounded at exactly one duplicate.** The
supervisor logs one `WATCHER ABSENT` and one `relaunched OK`, and because the relaunched process
has the canonical form it is then detected, so there is no relaunch loop — two watchers, stable.
Two watchers sweeping one signal is safe: the second's kills are no-ops and the loser's `mv` of the
signal fails silently. If you want it gone, skip leading `-*` arguments and test the first
non-option instead of hard-requiring `argv[1]`.

### 4. The `read -r -d ''` construct — correct, and it cannot hang

- **Single-element cmdline** (`bash` with no args): `argv0=bash`, `argv1` empty, `[ -n "$argv1" ]`
  rejects it. No block, no error.
- **Entirely empty cmdline**: both come back empty and the `argv0` case rejects it.
- **No hang is possible.** 200 reads spanning a process's death took 3 ms total; procfs reads are
  synchronous and return EOF/ENOENT rather than blocking. Your "silent death of the supervisor"
  concern does not materialise here.

**Correction to my own v2 report.** I wrote that "41 kernel threads with empty `cmdline` were
traversed". That count came from `[ ! -s ]`, and every procfs file reports `st_size` 0, so the
number was meaningless. Counting by actual read: **34 readable `/proc` entries, 0 with a genuinely
empty cmdline** in this distro. The robustness conclusion stands — the construct handles the empty
case correctly, verified directly against pid 2 — but the figure was wrong and I am retracting it.

## New finding — SV3-1 (LOW, safe direction): `local argv0 argv1` plus a failed redirect

If the cmdline redirect fails (the process vanished between `[ -r ]` and the redirect), the
assignments never execute:

- **Before any successful read**, `${argv0##*/}` is an unbound variable under `set -u`. The
  subshell running `$(watcher_pid)` dies, the substitution yields empty, and the supervisor
  concludes `WATCHER ABSENT` and relaunches once. Verified: the parent shell survives, so this is a
  spurious duplicate, not a supervisor death. Safe direction.
- **Otherwise** `argv0`/`argv1` retain the *previous* process's values, so a later pid is evaluated
  against an earlier process's argv.

**I checked whether that staleness can produce a false positive, and it cannot.** The very next
line, `cwd=$(readlink "/proc/$pid/cwd") || continue`, fails for the same vanished process — cmdline
and cwd share the `/proc/<pid>` directory, so anything that kills one kills the other. Verified on
a just-exited pid: `cmdline readable=no`, `cwd=[]`. The staleness is dead-ended before it can be
used. The only real asymmetry runs the other way (cmdline readable, cwd not — another user's
process), which is finding 2 above.

Fix is hygiene, not safety: `argv0=""; argv1=""` before the redirect.

## New finding — SV3-2 (LOW, silent): `mv -f "$f" "$f.1"` when `$f.1` is a directory

`mv file dir` **moves the file into the directory and returns 0**, so `: > "$f"` then runs. Proved
in isolation: `mv -f x.log x.log.1` with `x.log.1/` a directory exits 0 and leaves the content at
`x.log.1/x.log` while the live log restarts empty. Rotation is then permanently broken and that
directory accumulates one buried copy per rotation, silently.

Nothing realistic creates a directory at that name — I only hit it because it was my sabotage for
the isolation test — so this is worth knowing rather than fixing. A `[ -d "$f.1" ] && return 0`
guard closes it.

## Confirmed fixed and correct

**The four v2 false positives are gone**, and the detector returns exactly one result — pid 5751 —
against the real system, with no second match. The `argv[0]` suffix bug is fixed: `ssh`, `fish`,
`csh`, `ksh` and `refresh` are no longer admitted, since the test is now an exact basename.

**The mirror hazard is fixed by the deletion.** Staged a live watcher plus a stale `stopped`
status: v2 exited immediately here; **v3 did not retire and kept supervising**, watcher still alive.

**Behaviour after a real stop is unchanged.** With a watcher that writes `running`, then writes
`stopped` and exits — exactly the real sequence — the supervisor observed the absence, re-read the
state, logged `watcher gone and status reads 'stopped' -- it finished its job`, and exited with
**zero relaunches**. Absence plus a terminal state still retires it correctly.

**Rotation.** All three files rotate once over 2 MiB, with the in-flight line preserved (rotation
runs before the `tee`) and the old content intact in `.1`. A failure on the first file does **not**
prevent the other two — sabotaged `$LOG` while `watcher_supervisor.stdout` and
`stop_watcher_v2.stdout` both rotated normally. A hard `mv` failure (parent directory mode 500 on
ext4, where permissions are enforced) leaves the log **intact and untruncated**, because `: > "$f"`
is correctly gated behind `mv &&`. Non-numeric `stat` output, a failing `stat`, and missing files
are all no-ops. In every one of these cases `say()` logged its line and returned 0.

## Recommendation

**Stop here; record the component as verified.** The only failure class that costs the user their
machine is a false positive, and after three rounds none survives: substring matching is gone,
option slots are rejected, non-shells are rejected, foreign copies are rejected by canonical path,
and the one staleness path is dead-ended by the cwd guard. What remains are duplicate-watcher false
negatives — each bounded at one, each safe — and two silent-but-harmless edges. Further iteration
on this redundancy layer would be optimising the safe direction.
