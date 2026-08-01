// Session status feed — rewritten by Claude at every checkpoint.
// Loaded as a plain <script> so the dashboard works under file:// (fetch would be CORS-blocked).
window.SESSION_STATUS = {
  updated: "2026-07-11T08:00:00+01:00",
  phase: "Session starting",
  headline: "Dashboard initialised — setting up the stop-button watcher.",
  gpu: { job: "idle", detail: "GPU free" },
  tasks: [
    { name: "Dashboard + stop button", state: "doing" },
    { name: "B3: judge re-validation (deployed symmetric config)", state: "todo" },
    { name: "Null-objective beam ablation (build)", state: "todo" },
    { name: "Null-control per-target checkpointing (for multiday K=180)", state: "todo" },
    { name: "Definitive run pipeline (attack matrix -> K=180 null control)", state: "todo" },
  ],
  log: [
    "08:00 — session resumed; building dashboard",
  ],
};
