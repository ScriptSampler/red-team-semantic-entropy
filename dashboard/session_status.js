// Session status feed — rewritten by Claude at every checkpoint.
window.SESSION_STATUS = {
  updated: "2026-08-02T02:25:00+01:00",
  phase: "Chasing the ceiling — it may be the paper's real finding",
  headline: "The exact test has ZERO power at N=10 (ceiling ties swamp it). N=20 pilot running: target 1 STILL saturates, and baselines rise with N so headroom barely grows. If this holds, N is not the fix — and 'SE has no dynamic range at the top' becomes the finding.",
  gpu: { job: "pilot_n20_ceiling (1/15 targets)", detail: "~4 min/target; decides whether FA nats are identifiable at ANY feasible N" },
  tasks: [
    { name: "FA n=80 complete + ceiling finding (49% saturated)", state: "done" },
    { name: "Exact beta-binomial test (replaces brute-force budget matching)", state: "done" },
    { name: "Power re-sim under ceiling: ZERO power at N=10 (critic's catch, confirmed)", state: "done" },
    { name: "Methods: measurement-headroom section; Intro: narrowed novelty gap", state: "done" },
    { name: "Literature: wrong COLM venue fixed, 3 venues upgraded, closest neighbour cited", state: "done" },
    { name: "N=20 pilot (GPU) — the gate on the whole FA analysis", state: "doing" },
    { name: "Fallback: censoring-robust statistics (flips + rank + headroom fraction)", state: "todo" },
    { name: "Null-objective ablation (paused at 1/10, checkpointed)", state: "todo" },
  ],
  log: [
    "22:15 — start: ablation launched, 3 agent teams dispatched, stop button armed",
    "23:20 — critic: K=180 judge run = 9.5 GPU-DAYS; also caught 'feasible rate 1.000' is",
    "         TRUE BY CONSTRUCTION (verified in code, withdrawn, real gate counters added)",
    "00:00 — stats researcher: EXACT beta-binomial test prices budget into the null",
    "00:25 — CEILING: 49% of FA targets saturate at ln(10); fixed the tie bug it exposed",
    "01:15 — critic's lead catch: the ceiling KILLS the test's power. Re-simulated: 0.00",
    "         power at m=30/50/60. N=20 is the enabling condition, not a refinement.",
    "01:45 — paused ablation (1/10 after 3.3h), launched the N=20 pilot as critical path",
    "02:25 — pilot target 1: STILL saturates at N=20; baselines rise too, headroom +0.11 not +0.69",
  ],
};
