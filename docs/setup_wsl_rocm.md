# WSL2 + Ubuntu 24.04 + ROCm 6.4 setup for RX 9070 XT

Runtime stack for the Red-Teaming SE project. All actual model inference runs inside **WSL2 Ubuntu-24.04** (not Ubuntu 26.04 — see note below).

## Why this exact stack
- RX 9070 XT is RDNA 4 (`gfx1201`). ROCm 6.3+ supports it.
- ROCm 6.4 ships the `hsa-runtime-rocr4wsl-amdgpu` package — the WSL-aware HSA shim that talks to `/dev/dxg`. Without it, `rocminfo` fails with `HSA_STATUS_ERROR_OUT_OF_RESOURCES` in WSL.
- **Ubuntu 26.04 does not yet have a working WSL ROCm stack.** AMD ships ROCm 7.13-pre2 for Resolute but the WSL HSA shim is missing; ROCm 6.x only ships for Jammy (22.04) and Noble (24.04). Ubuntu-24.04 + ROCm 6.4 is the working combination.

## Versions in use (2026-05-21 bootstrap)
- Windows host: Win11 Pro, Adrenalin driver 32.0.31007.5012 (2026-05-12)
- WSL2 kernel: 6.6.114.1-microsoft-standard-WSL2
- WSL distro: Ubuntu-24.04 LTS "Noble", Python 3.12.3
- ROCm: 6.4.0.60400 with `hsa-runtime-rocr4wsl-amdgpu` 25.10-2149029.24.04
- PyTorch: 2.9.1+rocm6.4 (cp312, from `https://download.pytorch.org/whl/rocm6.4`)
- Secondary distro (general use): Ubuntu (26.04 Resolute) — not used for research

## Step 1 — Install WSL2 + Ubuntu-24.04 (Windows side)

Elevated PowerShell:
```powershell
wsl --install                       # WSL2 itself (if first time)
wsl --install -d Ubuntu-24.04       # add 24.04 distro (no reboot needed if WSL2 already on)
```

Use `--no-launch` to skip the interactive first-launch user wizard; create the user from root afterwards (see [bootstrap_ubuntu_2404.sh](../scripts/bootstrap_ubuntu_2404.sh)).

## Step 2 — Bootstrap user + tooling (inside Ubuntu-24.04, as root)

```bash
wsl -d Ubuntu-24.04 -u root bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/bootstrap_ubuntu_2404.sh
```

Creates user `abhi` with passwordless sudo, in render+video groups; writes `/etc/wsl.conf` so subsequent launches default to `abhi`. Then `wsl --shutdown` to apply.

## Step 3 — Install ROCm 6.4 with WSL usecase (inside Ubuntu-24.04, as root)

```bash
wsl -d Ubuntu-24.04 -u root bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/install_rocm_64_wsl.sh
```

That script:
1. Downloads `amdgpu-install_6.4.60400-1_all.deb` (noble).
2. Runs `amdgpu-install --usecase=wsl,rocm --no-dkms -y`.
3. Pulls ~3GB including:
   - `rocm` 6.4 meta-package (HIP, math libs, MIOpen, RCCL, debugger, profiler)
   - `hsa-runtime-rocr4wsl-amdgpu` — **the critical WSL HSA shim**
   - libdrm, opencl, mivisionx, MIVisionX dev

## Step 4 — Verify GPU access

```bash
wsl -d Ubuntu-24.04 -- rocminfo | grep -E 'Agent|Marketing|gfx|Compute Unit'
```

Expected output includes:
```
Agent 2
  Name:                    gfx1201
  Marketing Name:          AMD Radeon RX 9070 XT
  Device Type:             GPU
  Compute Unit:            64
```

If `Agent 2` is missing or rocminfo errors:
- Ensure Adrenalin driver is 25.x+ on Windows host.
- `wsl --shutdown && wsl -d Ubuntu-24.04` to restart.
- Check `dpkg -l hsa-runtime-rocr4wsl-amdgpu` to confirm WSL shim package installed.

## Step 5 — Project venv inside Ubuntu-24.04

```bash
wsl -d Ubuntu-24.04 bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/setup_venv_wsl.sh
```

That script:
1. Creates `.venv-wsl/` inside the project at `/mnt/i/GITHUBPROJECTS/SE Research/`.
2. Installs `torch==2.9.1+rocm6.4` + `torchvision==0.24.1+rocm6.4` from PyTorch's rocm6.4 index.
3. Installs the rest of the project deps (transformers, datasets, accelerate, scipy, sklearn, etc.).
4. Smoke-tests `torch.cuda.is_available()` and prints the device name.

> I/O note: `/mnt/i/` is slower than the WSL Linux filesystem. For the full TriviaQA eval (Week 4), keep the HuggingFace cache on the Linux side: `export HF_HOME=$HOME/.cache/huggingface`.

### Step 5b — Force torch to use the WSL libhsa (critical workaround)

The pip-installed `torch==2.9.1+rocm6.4` wheel ships its own `libhsa-runtime64.so` in `torch/lib/`. That bundled lib targets native Linux ROCm (`/dev/kfd`) and returns `hipErrorNoDevice` in WSL — torch.cuda.is_available() will be False even though `rocminfo` sees the GPU and `torch._C._cuda_getArchFlags` confirms gfx1201 kernels are compiled in.

The fix: symlink torch's bundled libhsa to the system's WSL-aware one from `hsa-runtime-rocr4wsl-amdgpu`.

```bash
wsl -d Ubuntu-24.04 bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/fix_torch_wsl_hsa.sh
```

What that script does:
1. Saves `torch/lib/libhsa-runtime64.so` as `libhsa-runtime64.so.bundled`.
2. Replaces it with `ln -s /opt/rocm-6.4.0/lib/libhsa-runtime64.so torch/lib/libhsa-runtime64.so`.
3. Verifies `torch.cuda.is_available()` is True.

The symlink survives across processes — no `LD_PRELOAD` env var needed for normal use. **Redo this fix any time torch is reinstalled or upgraded** (the bundled lib comes back with each pip install of torch).

## Step 6 — Daily workflow

```powershell
# From Windows PowerShell, jump into project root inside Ubuntu-24.04
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research"
```

Then in WSL:
```bash
source .venv-wsl/bin/activate
python src/...
```

Or run one-off commands directly:
```powershell
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research" -- bash -c "source .venv-wsl/bin/activate && python -c 'import torch; print(torch.cuda.is_available())'"
```

---

## Troubleshooting

**`rocminfo` says `HSA_STATUS_ERROR_OUT_OF_RESOURCES`**
- The WSL HSA shim isn't installed. Verify: `dpkg -l hsa-runtime-rocr4wsl-amdgpu`. If missing, `amdgpu-install --usecase=wsl,rocm --no-dkms` again.

**`torch.cuda.is_available()` is False but rocminfo works**
- Most likely cause in WSL: torch's bundled `libhsa-runtime64.so` is the native-Linux one, not the WSL-aware one. Run [scripts/fix_torch_wsl_hsa.sh](../scripts/fix_torch_wsl_hsa.sh) — see Step 5b.
- If the fix script's symlink is already in place, ensure `dpkg -l hsa-runtime-rocr4wsl-amdgpu` shows the package installed and `/opt/rocm-6.4.0/lib/libhsa-runtime64.so` resolves.
- If still failing: `export HSA_OVERRIDE_GFX_VERSION=12.0.1` (force gfx1201) or `11.0.0` (RDNA 3 compat kernels).

**bitsandbytes errors on 4-bit load**
- Upstream `bitsandbytes` officially supports CUDA. For ROCm, build from source:
  `git clone -b rocm-7-major https://github.com/ROCm/bitsandbytes.git && cd bitsandbytes && pip install -r requirements-dev.txt && cmake -DCOMPUTE_BACKEND=hip -S . && make && pip install -e .`
- Or skip bitsandbytes and use a pre-quantised AWQ/GPTQ Llama 3.1 8B model via `transformers` + `autoawq` / `auto-gptq`.

**Slow I/O on full TriviaQA eval**
- `export HF_HOME=$HOME/.cache/huggingface` to put HF cache on WSL Linux fs.
- Consider running the model from `~/se-research` (Linux copy) and writing results back to `/mnt/i/...` only at checkpoint boundaries.

---

## What about Ubuntu 26.04?

The first install attempt was on Ubuntu 26.04 Resolute. AMD has ROCm 7.13 packages for resolute but no working WSL HSA shim yet — `rocminfo` fails because `librocdxg.so` is missing. We keep the Ubuntu 26.04 install around for non-research use but all research work runs in Ubuntu-24.04.

When AMD ships the resolute WSL bridge (likely with ROCm 7.x stable), we can revisit.
