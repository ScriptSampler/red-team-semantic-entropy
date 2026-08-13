# START HERE — current state, 2026-08-12 (late)

Supersedes every earlier version. If you are reading a copy dated 2026-08-07 or earlier, it
carries the superseded `_def` ceiling numbers and predates the scoop concession; discard it.

**34 days to the 2026-09-15 arXiv target.** 149 tests pass, 24 citations resolve.

---

## What this paper is now

Not "we broke semantic entropy." It is a **measurement-validity paper about semantic
entropy**, with a paraphrase attack as the case study that exercises the protocol. That
reframe is deliberate and load-bearing: it means a null attack result does not kill the
paper, because the measurement findings stand either way.

**Novelty is narrow, and stated as such.** The false-alarm/inflation direction is an
established family (`rusert2025redherring` EMNLP 2025; `khanmohammadi2026answerpreserving`,
which was six days old when we found it). Constrained paraphrase search is a standard
primitive (`kaneko2026paa`, `liang2025seca`). We claim neither. What we claim is what a
sampling-based victim forces on the *evaluation* — see contribution (5).

---

## Findings that hold

1. **Ceiling saturation.** SE is capped at ln(10) = 2.3026 at N=10.
   **From the definitive `_defb` FA cell (n=80, complete):**
   - baseline already at ceiling: **8/80 = 10%**
   - at ceiling after attack: **42/80 = 52.5%**
   - attack-induced: **34/80 = 42.5%**
   - baseline in top tenth of range: **21/80 = 26.2%**
   - distinct baseline entropy values: **22**

   The superseded `_def` figures were 39/80, 31/80 = 38.75%. **The three clean-baseline
   statistics are IDENTICAL across both runs** — the ceiling/granularity finding does not
   depend on the attack instrumentation, which is the robustness check that matters.
   → `results/ceiling_saturation_finding.md` (bannered with both columns)

2. **Winner's curse — complete at n=60.** +0.698 → +0.315 nats on re-scoring.
   Shrinkage **−0.383 [−0.529, −0.234]**, CI excludes zero. Retention **45% [25%, 65%]**.
   Keep the two statements apart: *that* there is inflation is established; *how much* is
   not. 36/60 keep a positive move, r = +0.46. → `results/winners_curse_partial.md`

3. **Non-relaxability.** Raising N does not buy range because the baseline rises with the
   cap (n=15 pilot at N=20: 20% still pinned, mean move essentially unchanged). Discreteness
   alone is `sun2026granularity`, already in print — **non-relaxability is the part that is
   ours.** → `results/n20_verdict.md` (read its correction banner first)

4. **Judge.** Deployed symmetric config: hard-neg **0.930 [0.900, 0.957] n=300**, positives
   0.650 [0.593, 0.703], e5 near-chance at 0.51. `results/judge_validation.md` says
   explicitly: *"this number is the DEPLOYED config (symmetric) — cite THIS one."*
   **0.884 / 0.700 are the SUPERSEDED ASYMMETRIC run.** A critic gate flagged 0.93 as drift
   on 2026-08-12; that ruling was wrong and was overruled. Do not "fix" it back.

**Overturned — do not cite:** the N=20 verdict's original conclusion, "zero power / FA not
identifiable", and the class-separation-vs-noise claim (that used the quarantined pool).

---

## THE TWO POPULATIONS — the project's most-repeated error

**THEY ARE NESTED, NOT SEPARATE — read this before writing the word "separate".**
`_stratum_ids(want, seed, labels)` seed-shuffles a stratum and `select_stratified` takes
`[:n]`, so both pools are prefixes of the SAME seed-0 shuffle. Verified against the real
campaign ids: the 80 FA targets are exactly `right[:80]` (80/80, in order) — i.e. **40% of the
fair pool's correct stratum**; the hide targets are exactly `wrong[:41]`. Every attacked
target is *inside* the fair pool.

| | fair pool | attacked pool |
|---|---|---|
| composition | 200 correct + 200 hallucinating | 97 targets = 80 correct + 17 wrong |
| relation | the wider sample | **a prefix of it**, one stratum per direction |
| AUROC | **0.704** [0.653, 0.753] | 0.579 **[0.416, 0.728]** — contains 0.704 |
| separation | 0.463 nats, d ≈ 0.76 | 0.184 nats, d = 0.28 — **QUARANTINED** |
| carries | claims about "the detector" | ceiling + granularity statistics |

**Why the quarantine still holds — and the reason has changed.** Not because the attacked
pool is a different set of questions (it is not), but because it is a *selected sub-sample of
a single correctness stratum per direction*, truncated on the hide side, and the sample the
optimiser ran on. Within-stratum frequencies (ceiling, granularity) belong there;
correct-vs-hallucinating contrasts do not.

**Do NOT say the attacked pool "separates worse".** It is a score-independent sub-sample of
the same strata, so 0.579 estimates the *same* quantity as 0.704 and its CI [0.416, 0.728]
comfortably contains it. The gap is sampling error over ~1/30 as many ranked pairs. At the
hide arm's current n=41 it is 0.641 [0.535, 0.742].

This error has been found at **seven** sites. Sites 1–3 were fixed manually; site 4
(Conclusion, "on the same pool") and site 5 (Discussion, by adjacency) were found by a
44-agent sweep; **site 6 was found by the automated linter, in text written the same hour.**
Site 7 (2026-08-13) is the "separate populations" framing corrected here — it reached a
*pre-registration* (critique_log 32's tau rationale), which the linter cannot catch because it
checks that numbers name a pool, not that a claimed relation between pools is true.

**`scripts/check_population_labels.py` now runs in the test suite.** It anchors on NUMBERS,
never phrases — a manual grep for "fair pool" missed `conclusion.tex` because the source
reads `\emph{fair} pool`. Markup and math delimiters are stripped before matching.

---

## Running now

```
recompute_fair.py --only se_false_alarm,se_hide --n 80 --tag _defb
  -> null_control.py --tag _defb --K 50 --n_seeds 3 --judge_batched --judge_batch_size 6
```

- **FA cell: 80/80 COMPLETE.** Hide cell: in progress. Null control: not started (~67 GPU-h).
- Per-target cache at `~/.cache/se-research/samples/attacks/wk9_defb/` **inside WSL, not in
  the repo** — repo-scoped searches will find nothing and it is not evidence of failure.
- Fully resumable: `recompute_fair.py` skips completed qids. Killing it costs one target.
- **`recompute_fair.py` writes its report only at the very end** (single `write_text`). Watch
  the per-target JSONL for progress, not `results/`.

---

## Owed, in priority order

1. **Task #24 — judge conditions (ii) and (iii)**, which `judge_validation.md` itself lists
   as unmet "before the paper cites it as sole adjudicator": validation on messy real
   sampled pairs (current 0.93 is clean gold aliases), and a differential-over-splitting
   check (attack vs benign cluster counts must not diverge). **Needs GPU.** The Abstract is
   scoped for now, not closed.
2. **Task #27 — the definitive null control.** This is the gate on the attack verdict.
3. **Table 1 fill-in.** Caption already names the population; attach n per row as written.
4. **Human equivalence audit** — harness exists (`prepare_equivalence_audit.py`), unrun.
5. **Unverified citations**, deliberately out of the bib: Calibration Attacks (TMLR),
   ConfSmooth (NLDL 2026), DEPO (2606.00392). Verify before citing.
6. Regenerate `fair_recompute_report.md` from `_defb` when the matrix finishes.

---

## Process rules, learned the hard way

- **Check every gate ruling against the committed artifact before applying it.** The critic
  was wrong once (the judge number) and applying it on authority would have shipped an error.
- **Sweep on numbers, not phrases.** LaTeX markup defeats phrase matching.
- **Verify agent claims yourself.** A literature sweep called `zheng2026matchedctrl` a
  structural twin of our budget-matched control; reading it showed it is a format-matched
  control for VLM test-time scaling. Every bib `annote` now records who verified what, when.
- **Do not assert run state — read it.** Both directions have burned us in one session:
  a stale "FA 58/80" reported to the user, and a false "nothing has been written in 9 hours"
  that was just a repo-scoped search missing the WSL cache.
- **Unmeasured claims are the worst failure mode.** The Abstract asserted that benign
  rephrasing reaches the ceiling comparably to the attack. Never measured — and
  `critique_log` 826/1126 had *pre-committed* not to say it until it was.
