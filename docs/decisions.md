# Decisions log

Short, dated entries for choices that diverge from the original plan, so future-me has a single place to look before reading commit messages.

## 2026-05-21. Runtime stack: WSL2 + Ubuntu 24.04 + ROCm 6.4

Tried Ubuntu 26.04 Resolute with ROCm 7.13 first because it is the newest. AMD ships ROCm 7.13 for Resolute but the WSL HSA shim is missing from those packages, so `rocminfo` fails with `HSA_STATUS_ERROR_OUT_OF_RESOURCES`. Moved to Ubuntu 24.04 Noble with ROCm 6.4, which ships `hsa-runtime-rocr4wsl-amdgpu`. That works. The 26.04 distro is kept for general use.

Separately, the `torch==2.9.1+rocm6.4` wheel bundles its own `libhsa-runtime64.so` for native Linux, which returns `hipErrorNoDevice` inside WSL. Workaround: symlink torch's bundled file to `/opt/rocm-6.4.0/lib/libhsa-runtime64.so`. Re-apply after any torch reinstall. `scripts/setup_venv_wsl.sh` does this at the end of install; `scripts/fix_torch_wsl_hsa.sh` does it on demand.

## 2026-05-21. 4-bit quantisation: upstream bitsandbytes, no AMD fork

Pre-flighted before committing to the plan's quantisation stack. Upstream `bitsandbytes==0.49.2` auto-detects ROCm on gfx1201 and Linear4bit forward plus a 4-bit Qwen2.5-0.5B load both run clean. No need to build the AMD fork from source or pivot to AWQ.

## 2026-05-30. Week 4 eval scope: 2000-question subset at N=10

The plan called for "full TriviaQA at N=10" for Week 4 replication. Friday's sustained N=10 sampling number on 100 questions came in at 14.27 s per question (~35 generated tokens per second on Llama 3.1 8B 4-bit). Extrapolated to the 17,944-question validation split, that is 71 hours, over the plan's 12 to 36 hour budget.

Per the plan's pre-authorised mitigations in the "Weeks 1 to 4 setup risks" section ("Inference too slow. Mitigation: N=10 to N=5; eval set to 2000-question subset"), Week 4 will:

1. Run a 2000 question subset at N=10 first. Projected wall-clock about 8 hours. The subset is sampled with a fixed seed so it is reproducible.
2. If the AUROC lands within plus or minus three percentage points of Farquhar et al., tag `phase-1-complete` and move to Phase 2.
3. If not, fall back to either full validation at N=5 (about 36 hours, overnight) or a wider subset at N=10, depending on which axis the audit flags.

Speed optimisations (vLLM or sglang for batched serving, shorter `max_new_tokens` if outputs are short enough on average, attention backend tuning) are deferred. If we still cannot hit the budget after the N=5 fallback, that is the audit week to revisit.

The Monday projection of 6 to 7 hours was based on a single-question warmup measurement and was wrong; Friday's sustained 100-question number is the real baseline.
