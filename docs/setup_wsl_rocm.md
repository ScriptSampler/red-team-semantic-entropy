# WSL2 + Ubuntu 24.04 + ROCm 6.4 setup for RX 9070 XT

This is the runtime stack for the project. All model inference runs inside WSL2 Ubuntu 24.04. Ubuntu 26.04 was tried first and did not work; see the note at the bottom.

## Why this combination

The RX 9070 XT is RDNA 4 (gfx1201) and needs ROCm 6.3 or newer. ROCm 6.4 ships the `hsa-runtime-rocr4wsl-amdgpu` package, which is the WSL-aware HSA shim that talks to `/dev/dxg` instead of `/dev/kfd`. Without that shim, `rocminfo` fails with `HSA_STATUS_ERROR_OUT_OF_RESOURCES` inside WSL.

Ubuntu 26.04 is too new for this. AMD ships ROCm 7.13 pre-release for Resolute but the WSL HSA shim is missing from those packages, and ROCm 6.x only publishes packages for Jammy (22.04) and Noble (24.04). So Ubuntu 24.04 with ROCm 6.4 is currently the only combination that works for this GPU under WSL.

## Versions used in the bootstrap

These are the exact versions verified on 21 May 2026:

- Windows 11 Pro, Adrenalin driver 32.0.31007.5012 (dated 12 May 2026)
- WSL2 kernel 6.6.114.1-microsoft-standard-WSL2
- WSL distro: Ubuntu-24.04 LTS (Noble), Python 3.12.3
- ROCm 6.4.0.60400 with `hsa-runtime-rocr4wsl-amdgpu` 25.10-2149029.24.04
- PyTorch 2.9.1+rocm6.4 (cp312, from `https://download.pytorch.org/whl/rocm6.4`)
- Ubuntu (26.04 Resolute) is installed but unused for research

## Step 1: install WSL2 and Ubuntu 24.04

From elevated PowerShell:

```powershell
wsl --install                       # WSL2 itself, if not already on
wsl --install -d Ubuntu-24.04       # add the 24.04 distro
```

If you want to skip the interactive first-launch user wizard, pass `--no-launch` to the second command and create the user from root afterwards (see [bootstrap_ubuntu_2404.sh](../scripts/bootstrap_ubuntu_2404.sh)).

## Step 2: bootstrap the user and tooling

Inside Ubuntu 24.04, run as root:

```bash
wsl -d Ubuntu-24.04 -u root bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/bootstrap_ubuntu_2404.sh
```

The script creates the user `abhi` with passwordless sudo, adds it to the `render` and `video` groups, installs build tools and Python, and writes `/etc/wsl.conf` so subsequent launches default to that user. Then run `wsl --shutdown` so the new default takes effect.

## Step 3: install ROCm 6.4 with the WSL usecase

Run as root inside Ubuntu 24.04:

```bash
wsl -d Ubuntu-24.04 -u root bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/install_rocm_64_wsl.sh
```

The script downloads `amdgpu-install_6.4.60400-1_all.deb` from AMD's noble repository, installs it, then runs `amdgpu-install --usecase=wsl,rocm --no-dkms -y`. That pulls about 3 GB: the ROCm 6.4 meta-package (HIP, math libs, MIOpen, RCCL, debugger, profiler), the WSL HSA shim `hsa-runtime-rocr4wsl-amdgpu`, libdrm, OpenCL, and MIVisionX. `--no-dkms` is right for WSL because the kernel driver lives on the Windows host.

## Step 4: verify GPU access

```bash
wsl -d Ubuntu-24.04 -- rocminfo | grep -E 'Agent|Marketing|gfx|Compute Unit'
```

You should see something like:

```
Agent 2
  Name:                    gfx1201
  Marketing Name:          AMD Radeon RX 9070 XT
  Device Type:             GPU
  Compute Unit:            64
```

If Agent 2 is missing, or `rocminfo` errors: check that the Windows Adrenalin driver is recent (25.x or newer ships the WSL GPU passthrough), then restart WSL with `wsl --shutdown` and try again. You can also confirm `dpkg -l hsa-runtime-rocr4wsl-amdgpu` shows the package installed.

## Step 5: project venv

```bash
wsl -d Ubuntu-24.04 bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/setup_venv_wsl.sh
```

The script creates `.venv-wsl/` at the project root, installs `torch==2.9.1+rocm6.4` and `torchvision==0.24.1+rocm6.4` from PyTorch's rocm6.4 index, then installs the rest of the dependencies (transformers, datasets, accelerate, scipy, scikit-learn, and so on). At the end it applies the libhsa fix described below, and runs a smoke test that prints torch, transformers, and datasets versions plus the detected device.

Note on I/O: `/mnt/i/` is significantly slower than the native WSL Linux filesystem. For the full TriviaQA eval in Week 4, keep the HuggingFace cache on the Linux side with `export HF_HOME=$HOME/.cache/huggingface`.

### Step 5b: torch's libhsa needs to be the WSL one

The `torch==2.9.1+rocm6.4` wheel ships its own `libhsa-runtime64.so` inside `torch/lib/`. That bundled lib targets native Linux ROCm and looks for `/dev/kfd`, which doesn't exist in WSL, so `torch.cuda.is_available()` returns False even though `rocminfo` sees the GPU and the wheel does have gfx1201 kernels compiled in.

The fix is to point torch at the system's WSL-aware libhsa, the one installed by `hsa-runtime-rocr4wsl-amdgpu`:

```bash
wsl -d Ubuntu-24.04 bash /mnt/i/GITHUBPROJECTS/SE\ Research/scripts/fix_torch_wsl_hsa.sh
```

The script saves the bundled file as `libhsa-runtime64.so.bundled`, replaces it with a symlink to `/opt/rocm-6.4.0/lib/libhsa-runtime64.so`, and verifies `torch.cuda.is_available()` is now True. Setup_venv_wsl.sh already does this at the end, but you'll need to re-apply it any time torch is reinstalled or upgraded, since pip will put the native-Linux file back.

## Step 6: daily workflow

Drop into the project from PowerShell:

```powershell
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research"
```

Then in bash:

```bash
source .venv-wsl/bin/activate
python src/...
```

Or run a one-off command directly:

```powershell
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research" -- bash -c "source .venv-wsl/bin/activate && python -c 'import torch; print(torch.cuda.is_available())'"
```

## Troubleshooting

**`rocminfo` says `HSA_STATUS_ERROR_OUT_OF_RESOURCES`.** The WSL HSA shim is missing. Check `dpkg -l hsa-runtime-rocr4wsl-amdgpu`. If it's not there, rerun `amdgpu-install --usecase=wsl,rocm --no-dkms`.

**`torch.cuda.is_available()` is False but `rocminfo` works.** Almost always it's the bundled torch libhsa. Run `scripts/fix_torch_wsl_hsa.sh`. If the symlink is already in place, check that `dpkg -l hsa-runtime-rocr4wsl-amdgpu` is installed and that `/opt/rocm-6.4.0/lib/libhsa-runtime64.so` resolves. As a last resort, try `export HSA_OVERRIDE_GFX_VERSION=12.0.1` to force the gfx1201 path, or `11.0.0` to fall back to RDNA 3 kernels.

**bitsandbytes errors on a 4-bit load.** Upstream `bitsandbytes` 0.49 and newer auto-detects ROCm on gfx1201 and worked in our pre-flight (see [scripts/preflight_bnb.sh](../scripts/preflight_bnb.sh)). If it doesn't on your machine, you can build the AMD fork from source, or switch to a pre-quantised AWQ or GPTQ Llama via transformers and autoawq or auto-gptq.

**Slow I/O on the full TriviaQA eval.** Move the HF cache to the WSL Linux filesystem with `export HF_HOME=$HOME/.cache/huggingface`. If you're doing a very long run, consider checking out a working copy under `~/se-research` and writing results back to `/mnt/i/` only at checkpoint boundaries.

## Why not Ubuntu 26.04

The first install attempt was on Ubuntu 26.04 Resolute. AMD ships ROCm 7.13 packages for resolute, but the WSL HSA shim isn't published for that release yet, so `rocminfo` fails with `librocdxg.so: cannot open shared object file`. The Ubuntu 26.04 install stays on the machine for general use, but research happens in 24.04. When AMD ships the resolute WSL bridge, probably with a future stable ROCm 7.x, this stack is worth revisiting.
