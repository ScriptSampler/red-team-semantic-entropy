// Session status feed — rewritten by Claude at every checkpoint.
// Loaded as a plain <script> so the dashboard works under file:// (fetch would be CORS-blocked).
window.SESSION_STATUS = {
  updated: "2026-07-11T08:55:00+01:00",
  phase: "Multiday-run engineering done — waiting on judge validation, doing paper polish",
  headline: "Checkpointing + null-objective ablation built and tested (119 tests). Judge still validating (~1500 pair judgements).",
  gpu: { job: "validate_judge (Qwen2.5-7B, symmetric, 300/stratum)", detail: "running; locks the B3 citation number, then the multiday pipeline launches" },
  tasks: [
    { name: "Dashboard + stop button", state: "done" },
    { name: "Null-control per-target checkpointing (627206a)", state: "done" },
    { name: "Null-objective beam ablation, built + tested (a9fc986)", state: "done" },
    { name: "B3: judge re-validation (deployed symmetric config)", state: "doing" },
    { name: "Paper polish: M12 hyperparams, notation, RW strands", state: "doing" },
    { name: "Attack matrix resume 53->80 FA + hide (~26 GPU-h)", state: "todo" },
    { name: "Ablation run (~4 GPU-h) then K=180 null control (multiday)", state: "blocked" },
  ],
  log: [
    "08:00 — session resumed; dashboard built + committed (602ffe6)",
    "08:15 — stop-button watcher armed (Downloads/STOP_SESSION*.txt + repo STOP.txt)",
    "08:20 — validate_judge launched on GPU (symmetric deployed config)",
    "08:40 — null_control per-target checkpointing landed (multiday run resumable)",
    "08:55 — null-objective beam ablation built + tested; 119 tests green",
  ],
};
