// Session status feed — rewritten by Claude at every checkpoint.
// Loaded as a plain <script> so the dashboard works under file:// (fetch would be CORS-blocked).
window.SESSION_STATUS = {
  updated: "2026-08-02T05:35:00+01:00",
  phase: "SESSION WOUND DOWN (6:00) — attack matrix continues unattended",
  headline: "MILESTONE: false-alarm cell COMPLETE at 80/80 (pre-registered scale). Hide at 15/80 (~12h left, resumable). Everything committed.",
  gpu: { job: "recompute_fair hide cell (PID 273)", detail: "safe to leave; to stop manually: wsl -d Ubuntu-24.04 pkill -f recompute_fair (resumes losslessly). NOTE: this STOP button only reaches Claude during a live session." },
  tasks: [
    { name: "FA attack matrix at n=80 (COMPLETE, 80/80)", state: "done" },
    { name: "Judge locked at 0.93 [0.90,0.96] n=300; paper swept", state: "done" },
    { name: "Checkpointing + ablation + dashboard (all committed)", state: "done" },
    { name: "Hide attack matrix 15/80 (running unattended)", state: "doing" },
    { name: "Null-objective ablation run (~4 GPU-h) — next session", state: "todo" },
    { name: "K=180 budget-matched null control (multiday) — after that", state: "todo" },
    { name: "Owed: messy-sample judge validation + differential over-split + human audit", state: "todo" },
  ],
  log: [
    "08:00 (Jul 11) — session resumed; dashboard + STOP button built",
    "09:10 — judge validation landed: hard-neg 0.930 n=300 (the locked number)",
    "09:25 — attack matrix launched: FA 53→80 + hide 0→80",
    "~05:00 (Aug 2) — FA cell COMPLETE at 80/80; hide progressing",
    "05:35 — session wound down at user request (6:00 cutoff); repo clean; see docs/START_HERE_overnight.md",
  ],
};
