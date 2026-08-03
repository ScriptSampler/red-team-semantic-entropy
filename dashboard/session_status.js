// Session status feed — rewritten by Claude at every checkpoint.
window.SESSION_STATUS = {
  updated: "2026-08-03T00:40:00+01:00",
  phase: "Deep session — two major findings, both gated with the critic",
  headline: "FOUND: the FA attack saturates the ln(10) ceiling on 49% of targets (censors the effect + breaks the naive null). ALSO: an exact test that prices the search budget into the null — 9.5 GPU-days becomes ~21h.",
  gpu: { job: "null-objective beam ablation (1/10 targets)", detail: "~1h/target, resumable; now doubles as the VALIDITY CHECK for the new exact test's exchangeability null" },
  tasks: [
    { name: "FA cell complete at n=80 + first-look analysis", state: "done" },
    { name: "Exact budget-corrected exceedance test (+H0 calibration test)", state: "done" },
    { name: "Ceiling-saturation finding + conservative tie fix", state: "done" },
    { name: "Withdrew by-construction 'feasible rate 1.000' (critic catch, verified)", state: "done" },
    { name: "Paper consistency sweep + trajectory/prefix machinery", state: "done" },
    { name: "Null-objective ablation (GPU, running)", state: "doing" },
    { name: "Literature fixes: wrong COLM venue + uncited NeurIPS'25 neighbour", state: "doing" },
    { name: "Definitive judge run under the new test (~21h) — after critic ruling", state: "todo" },
  ],
  log: [
    "22:15 — session start; ablation launched, stop button re-armed, 3 agent teams dispatched",
    "23:00 — FA n=80 first look; caught 2 invalid-AUROC traps in the auto-report",
    "23:20 — critic: K=180 judge run = ~9.5 GPU-DAYS. Ruled prefix+split; also caught that",
    "         'feasible rate 1.000' is TRUE BY CONSTRUCTION (verified, withdrawn, real gate stat added)",
    "00:00 — stats researcher: EXACT beta-binomial test prices the budget into the null",
    "00:25 — CEILING FINDING: 49% of FA targets saturate ln(10); fixes the tie bug it exposed",
    "00:40 — both sent to critic for ruling; literature fixes next",
  ],
};
