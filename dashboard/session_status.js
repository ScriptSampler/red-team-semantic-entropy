// Session status feed — rewritten by Claude at every checkpoint.
window.SESSION_STATUS = {
  updated: "2026-08-02T04:25:00+01:00",
  phase: "Verdict in — the ceiling is structural. Reframing the paper around it.",
  headline: "N=20 does NOT rescue the FA analysis: baselines rise with N too, so real headroom gain is +0.11 median (not +0.69) and power stays 0.00. FA effect sizes are NOT identifiable at any feasible N — which is itself the finding.",
  gpu: { job: "winner's-curse re-evaluation (all 80 FA targets)", detail: "re-scores the SELECTED paraphrase at a fresh seed — isolates selection-on-noise with no judge and no benign floor" },
  tasks: [
    { name: "FA n=80 complete; ceiling finding (49% saturated)", state: "done" },
    { name: "Exact beta-binomial test + H0 calibration", state: "done" },
    { name: "Power under ceiling: ZERO at N=10 (critic's catch)", state: "done" },
    { name: "N=20 pilot -> VERDICT: ceiling is structural, do not proceed", state: "done" },
    { name: "SE dynamic range: d=0.28, 26% of clean correct in top decile", state: "done" },
    { name: "Verified N=20 draws are genuinely fresh (before claiming replication)", state: "done" },
    { name: "Winner's-curse re-eval on 80 targets (GPU, running)", state: "doing" },
    { name: "Independent verification of all 3 findings (agents, running)", state: "doing" },
    { name: "Framing ruling: FA-led paper whose FA effect size is unmeasurable", state: "doing" },
  ],
  log: [
    "22:15 — start; ablation + 3 agent teams launched, stop button armed",
    "23:20 — critic: K=180 judge run = 9.5 GPU-DAYS; caught 'feasible rate 1.000' as",
    "         TRUE BY CONSTRUCTION (verified, withdrawn, real gate counters added)",
    "00:00 — EXACT beta-binomial test: prices the search budget into the null",
    "00:25 — CEILING: 49% of FA targets saturate at ln(10)",
    "01:15 — critic's lead catch: ceiling KILLS the test's power. Confirmed: 0.00",
    "03:20 — noticed MY OWN pre-commitment was ambiguous; tightened it BEFORE the data",
    "04:05 — N=20 VERDICT: headroom gain only +0.11 median; power still 0.00 -> do not proceed",
    "04:15 — launched the clean winner's-curse test (fresh seed, same N)",
  ],
};
