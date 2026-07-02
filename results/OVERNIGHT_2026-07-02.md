# Overnight status — 2026-07-02 (read me first)

## TL;DR

Every external-review blocker addressable in code is **fixed and critic-approved** —
B1, B2, the B4 reporting core, and the Methods prose. The critic signed off that the
pipeline is now review-compliant end-to-end.

**Correction (important):** partway through I raised a false alarm that "the Phase-1
cache is gone and there's no GPU." That was **my error** — I was querying the *default*
`Ubuntu` WSL distro (26.04, broken ROCm) and the Windows cpu-only venv, instead of the
`Ubuntu-24.04` research distro my own notes specify. In `Ubuntu-24.04` the GPU works
(rocminfo sees gfx1201, `torch.cuda.is_available()` = True, torch 2.9.1+rocm6.4) and
the cache is **fully intact** (samples/entropy/relabeled = 2000 lines each, all wk9
JSONLs present). **Nothing was lost.** The GPU recompute is therefore UNBLOCKED, and
I proceeded to run it (see the recompute section below). Retraction logged in
`docs/critique_log.md` entry 8.

## What cleared the critic gate (4 checkpoints, all approved)

| Blocker | What was wrong | Fix | Verdict |
| --- | --- | --- | --- |
| **B1** selection circularity / confounded SE-vs-SRE pool | wk9 branched on detector (`se`→stratified, `sre`→`_label_fresh`); shared pool only *asserted*, seed silently dropped | `campaign_pool()` has **no detector parameter** → SE/SRE draw the identical pool by construction; `assert_detector_blind` enforces it; wk9 routes every cell through it; `select_examples` forwards seed | **APPROVE** |
| **B2** success metric ignored hallucination status | success = entropy moved + NLI-feasible only | success is a **conjunction**: entropy moved AND feasible AND *status held under Q'* (hide→still wrong; false-alarm→still right), re-checked with the **same span oracle + pinned greedy decode** as the pool label | **APPROVE-WITH-NITS** |
| **B4** reporting: no CIs, wrong headline | entropy-only success, no CIs, no operating point | `report.py`: bootstrap 95% CIs on every rate; gated success is the headline with attrition beside it; answer-flip subcategory (meaning-shift bound); operating-point flip sweep {0.05,0.10,0.20} | **APPROVE-WITH-NITS** |
| **Methods** prose | selection/success/reporting undocumented; two NLI-fidelity overclaims | added target-selection / success-criterion / evaluation paragraphs; scoped down "meaning cannot drift" → cannot *accumulate*, dropped "admits the same answer" | **APPROVE-WITH-NITS** |

All nits from every verdict were **landed in the same session** (not deferred).
Tests: **60 pass** (was 41; +4 B1 enforcement incl. a hermetic squad SE==SRE-pool
test, +6 B2 truth-table, +9 reporting). Full gate record: `docs/critique_log.md`
entries 4–7. Commits: `2383892` (B1+B2), `cb0fa4f`+`ce96363` (reporting), `76dfd9e`+
`f562b49` (Methods), `4871ffd` (log/this note).

**B5 (NLI fidelity)** is the axis the critic flagged as the project's remaining weak
point. It is not "closed" — it *cannot* be closed by construction — but it is now
handled honestly: the optimizer anchors every candidate to the original q (verified:
`optimizer.py:107`), so equivalence error cannot accumulate across rounds, and the
**answer-flip subcategory** empirically bounds single-hop NLI-gate leakage. This is
the last thing a reviewer will push on; the recompute must report those numbers.

## Infrastructure: fine (my false alarm, corrected)

There is **no** infrastructure blocker. The GPU and cache are healthy in the
`Ubuntu-24.04` research distro:
- `wsl -d Ubuntu-24.04` → `rocminfo` sees the RX 9070 XT (`gfx1201`); `.venv-wsl`
  python → `torch 2.9.1+rocm6.4`, `torch.cuda.is_available()` = True.
- `~/.cache/se-research/samples/wk4_full_2000q/` → `samples.jsonl`, `entropy.jsonl`,
  `relabeled.jsonl` all **2000 lines**; `attacks/wk9/` has all four campaign JSONLs.

**The lesson (now in the `hardware_gpu` memory):** the *default* WSL distro is
`Ubuntu` (26.04) with broken ROCm; `wsl -e bash` and the Windows `.venv` (cpu-only by
design) both mislead. Always use `wsl -d Ubuntu-24.04`.

## What I did NOT do (deliberately)
- Did not fabricate or re-state any post-attack number as if re-verified.
- Did not reinstall drivers/torch — turned out unnecessary; the stack was fine.

## Live dashboard
`Desktop/SE/dashboard.html` reflects the corrected state: the four approved
checkpoints and the retracted false alarm.
