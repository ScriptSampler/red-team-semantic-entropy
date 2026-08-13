# Paper review punch-list (multi-agent, 2026-07-10)

Source: a 4-dimension adversarial review workflow (overclaim / stats / positioning /
consistency), 5 agents, 31 raw findings deduped to 25 issues by an area-chair synthesis.
Corroboration (>1 reviewer) noted per item. Checkbox = fixed in this session.

Provenance: workflow wf_a59c1057-3ec; per-agent journal at
subagents/workflows/wf_a59c1057-3ec/journal.jsonl.

**Two findings (B2, B3) are methodology-critical and reshape the definitive run — gate the
fix DESIGN through the critic before implementing/running.**

**DONE this session (2026-07-11):** B1, M3, M4, M5, N1, N2, N4, M7, M10, M11, mi1, mi2,
mi4, M2 (prose/positioning/leaks); B2 code + reporting (paired_max_net + analytic baseline,
run K~180 owed); B3 code + committed artifact + main-text disclosure (deployed-config
re-validation owed); M1 single decision rule (Experiments+Methods+run-plan).
**STILL OPEN:** M6 (0.92 CI in more loci), M8, M9 (RW strands: LLM-as-judge, selection-bias;
CORVUS concede), M12 (name paraphraser + hyperparams), mi3, mi5, mi6; and the GPU-owed
B2/B3 items (K~180 budget-matched run, null-objective ablation, deployed-config judge
re-validation on messy samples + differential-over-splitting check).

---

## BLOCKER

- [ ] **B1 — Abstract states a bidirectional result; hide has zero outcomes.** (overclaim+consistency)
  `main.tex` Abstract 36–39 says the attack moves the detector "in both the
  hallucination-hiding and the false-alarm direction." n=6 was SE/FA-only. Scope to FA;
  hide = mirror direction built-but-not-yet-evaluated. (Matches the Conclusion fix, entry 20.)

- [ ] **B2 — Winner's-curse null control is not budget-matched.** (stats) **METHODOLOGY-CRITICAL**
  Attack move = MAX over ~180 optimiser candidates; benign/seed floors = K=5–8 individual
  draws. A max-over-180 sits high in a distribution of K individual draws under H₀ *by
  construction*, so `beats_benign_p90`, `mean percentile`, and `net_vs_benign_mean` are all
  upward-biased. entry-13's percentile fix removed the max-vs-max(8) bias but left
  max-vs-individual. FIX: budget-matched benign floor (attack-max vs benign-MAX-over-~180),
  and report the true H₀ expected percentile of a max-over-180 within K draws (≈100%, not
  50%). Stop calling the K-draw percentile "null-controlled" for the winner's curse.

- [ ] **B3 — LLM-judge fails its own pre-registered validation gate.** (stats; +M6,mi3) **CRITICAL**
  `validate_judge.py:53` gate = `hard>=0.8 AND pos>=0.8`. pos-recognition is 0.656(sym)/
  0.700(asym) < 0.8 → committed `judge_validation.md` says "NOT usable → keep NLI/exact
  bracket." Paper treats it as "the adjudicator." Also 0.92(sym) ≠ 0.884(asym) cited
  inconsistently. FIX: either re-earn a documented USABLE verdict under a pre-committed
  re-spec (hard-neg-only, with written rationale for dropping pos≥0.8 + cleaned-label pos),
  or revert to the bracket. ~~Reconcile 0.92↔0.884~~ **[CLOSED 2026-08-13 — see below]**;
  disclose the deviation in Limitations.

  > **CLOSED (2026-08-13): the "reconcile 0.92 vs 0.884" sub-item. There is nothing to
  > reconcile — they are different runs, and only one is deployed.**
  > `results/judge_validation.md` reports hard-negative accuracy **0.930 [0.900, 0.957],
  > n=300**, for the **DEPLOYED SYMMETRIC** config, and instructs in line 11: *"this number
  > is the DEPLOYED config (symmetric) — cite THIS one, not a mixed sym/asym pair."*
  > **0.884 / 0.700 are the SUPERSEDED ASYMMETRIC run** and must not be cited.
  > Provenance: a critic gate on 2026-08-12 read this as a drift 0.884 → 0.92 → 0.93 and
  > demanded reconciliation; **that ruling was overruled, and the overrule was sustained on
  > re-gate** — the gate had itself *required* the deployed-config re-measurement in its own
  > B3 ruling, then flagged the result of its own requirement from a stale read. Applying
  > the "fix" would have reverted the paper to the asymmetric 0.884 and *created* the drift
  > it warned of. See critique_log entry 33 §1 (and entry 31), and
  > `docs/START_HERE_overnight.md` item 6: *"Do not 'fix' it back."*
  > The rest of B3 stays OPEN: the hard-neg-primary re-spec rationale, the Limitations
  > disclosure, and the three still-owed validations (messy real sampled pairs, the
  > differential-over-splitting check, and reporting the NLI/exact bracket alongside).

---

## MAJOR

- [ ] **M1 — Decision rule stated inconsistently + gates on the disowned net + post-hoc adjudicator swap.** (stats)
  Experiments: net-CI-only; run-plan: percentile AND net; entry-15: net-CI-only naming the
  EMBEDDING arm (later swapped to judge). Lock ONE rule identically everywhere; gate on the
  budget-matched scale-free statistic (B2), not the inflated net; document the e5→judge swap
  as a deviation with its trigger (hard-neg AUROC 0.51).
- [ ] **M2 — Table-1 "expect seed < benign < attack" is inverted by the pilot.** (stats)
  n=6: judge seed −0.081 vs benign −0.190; benign floor negative-in-FA in every arm — which
  is what inflates the net. Drop/redo the ordering framing; report benign-negative + the
  seed<benign failure + the H_split/H_rtm diagnosis.
- [ ] **M3 — Conclusion states the FA result as settled** (missing deferred-verdict + confounded-clusterer hedges). (overclaim+consistency)
- [ ] **M4 — Conclusion asserts a defense result the body marks "[Pending.]".** (consistency)
- [ ] **M5 — Intro NLI-arm +0.64 is stale/inconsistent** with Discussion +0.46 (move) / results +0.57 (net), mislabeled, no CI. (overclaim+stats+consistency — 3, highest corroboration) Reconcile to one quantity+label+CI or delete pending the run.
- [ ] **M6 — "0.92 vs 0.51" stated 7× with no CI/validation-set size.** (overclaim) Add hard-neg stratum size + CI at the Methods/Experiments validation locus.
- [ ] **M7 — Novelty sentence stacks 4 conjunctive qualifiers + sells the shared-NLI constraint as a differentiator** (the paper's thesis is that same constraint is the confound). (positioning+overclaim) Reduce to bidirectional+input-side; reframe NLI as a design choice; scope to "formulates" (hide unrun).
- [ ] **M8 — Related Work situates only the attack; the protocol + judge (now the primary contributions) are un-situated.** (positioning) Add an evaluation-methodology/selection-bias strand + an LLM-as-judge strand.
- [ ] **M9 — CORVUS underplayed** (it already red-teams SEP = the probe form of SE). (positioning) Concede it, defend the sampling-based distinction on substance.
- [ ] **M10 — Missing Kernel Language Entropy (Nikitin et al. NeurIPS 2024)** — replaces hard-NLI clustering *because* it's brittle; the neighbour closest to our thesis. (positioning) Survey it; state transfer expectation.
- [ ] **M11 — `plainnat` prints the `.bib` note field: internal scaffolding + live `%TODO`s render in References.** (consistency) **submission-blocking** Move notes to `annote`/outside braces; resolve the 2 venues.
- [ ] **M12 — Attack paraphraser unnamed + hyperparameters unvalued** (δ, beam P, proposals/beam, iteration budget, target FPR). (consistency) Reproducibility. Give a values table now.

## MINOR
- [ ] **mi1** — Conclusion "verified equivalent by bidirectional NLI" overstates the automatic gate → "certified by an automatic gate (not yet human-audited)."
- [ ] **mi2** — Intro describes the unrun hide attack in present indicative ("suppresses") → conditionalize to "designed to."
- [ ] **mi3** — 0.92 validated on a proxy (clean gold-alias strata), not the deployed sampled-answer clustering. Reword; add owed real-sample validation to Limitations.
- [ ] **mi4** — Literal "[Quantitative bracket placeholder …]" in Intro running prose → hedge + \ref now (number gated on run).
- [ ] **mi5** — `$M$` overloaded (victim model AND proposals/beam) → rename proposals to $B$.
- [ ] **mi6** — `$K$` overloaded 3 ways (SRE samples, benign-floor count, defense count) → distinct symbols.

## NIT
- [ ] **N1** — Discussion heading "Why the attack works." presupposes the deferred result → "Hypothesised mechanism."
- [ ] **N2** — Fair-pool AUROC mislabeled (full-pool 0.69 cited as fair-pool; fair is 0.704 [0.653,0.753]); add CI.
- [ ] **N3** — (optional) residual title keyword overlap with the AdvParaphrasing/CoPA line; disclaimer already mitigates.
- [ ] **N4** — Visible "(affiliation TBD)" placeholder in the author block.

---

## Highest-value order
1. Clear the 3 blockers: B1 (scope Abstract to FA) now; B2 (budget-matched null) + B3
   (judge gate) via critic-gated design, then implement + run.
2. Lock one decision rule + reconcile every number before the definitive run
   (+0.64→+0.57+CI, ~~0.92↔0.884~~ **[CLOSED 2026-08-13: cite the deployed symmetric
   hard-neg 0.930 [0.900, 0.957] n=300; 0.884/0.700 are the superseded asymmetric run — see
   B3]**, fair-pool 0.70), hedge Conclusion FA+defense.
3. Positioning + hygiene (data-independent): add the RW strands (KLE, LLM-as-judge,
   selection-bias) + reframe novelty; scrub leaks (bib note/%TODO, affiliation, placeholder).
