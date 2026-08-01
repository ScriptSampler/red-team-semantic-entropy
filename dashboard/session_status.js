// Session status feed — rewritten by Claude at every checkpoint.
// Loaded as a plain <script> so the dashboard works under file:// (fetch would be CORS-blocked).
window.SESSION_STATUS = {
  updated: "2026-07-11T09:25:00+01:00",
  phase: "Multiday pipeline launched — attack matrix running",
  headline: "Judge locked at 0.93 [0.90,0.96] (deployed config); paper swept; attack matrix resuming 53→80 FA + 0→80 hide (~26 GPU-h, resumable).",
  gpu: { job: "recompute_fair --n 80 (FA + hide)", detail: "~26h, per-target resumable; then ablation (~4h), then K=180 null control (multiday)" },
  tasks: [
    { name: "Dashboard + stop button", state: "done" },
    { name: "Null-control per-target checkpointing (627206a)", state: "done" },
    { name: "Null-objective beam ablation, built + tested (a9fc986)", state: "done" },
    { name: "B3: judge locked at 0.93, paper swept (a86ca69)", state: "done" },
    { name: "Paper polish: M12/mi5/mi6/M8/mi3/M6 (f77ddeb, a86ca69)", state: "done" },
    { name: "Attack matrix resume 53→80 FA + hide", state: "doing" },
    { name: "Ablation run (~4 GPU-h) after matrix", state: "todo" },
    { name: "K=180 budget-matched null control (multiday)", state: "todo" },
    { name: "Owed: messy-sample judge validation + differential over-split check", state: "todo" },
  ],
  log: [
    "08:00 — session resumed; dashboard built + committed (602ffe6)",
    "08:15 — stop-button watcher armed (Downloads/STOP_SESSION*.txt + repo STOP.txt)",
    "08:20 — validate_judge launched on GPU (symmetric deployed config)",
    "08:40 — null_control per-target checkpointing landed (multiday run resumable)",
    "08:55 — null-objective beam ablation built + tested; 119 tests green",
    "09:10 — judge validation landed: hard-neg 0.930 [0.900,0.957] n=300; pos 0.650 (gate FAIL disclosed)",
    "09:20 — paper swept to the ONE number (0.93) + M6/mi3/M8 fixes (a86ca69)",
    "09:25 — attack matrix launched: FA 53→80 + hide 0→80 (b4aq6y8mx)",
  ],
};
