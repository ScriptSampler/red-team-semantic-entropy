#!/bin/bash
# Diagnose why torch.cuda.is_available() is False despite rocminfo seeing the GPU.
# Run inside .venv-wsl as user abhi.
set -uo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"
source .venv-wsl/bin/activate

echo "=== Step 1: which arches did this torch wheel compile for? ==="
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("hip:", torch.version.hip)
try:
    arches = torch.cuda.get_arch_list()
    print("compiled_arches:", arches)
except Exception as e:
    print("get_arch_list FAILED:", e)
PY

echo
echo "=== Step 2: rocminfo confirms gfx1201 ==="
rocminfo 2>&1 | grep -E 'Name:.*gfx|Marketing' | head -4

echo
echo "=== Step 3: torch with HSA_OVERRIDE_GFX_VERSION=12.0.1 (force gfx1201) ==="
HSA_OVERRIDE_GFX_VERSION=12.0.1 python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('device_name:', torch.cuda.get_device_name(0))
    x = torch.randn(128, 128, device='cuda')
    y = x @ x
    print('matmul OK, shape:', y.shape, 'mem MB:', torch.cuda.memory_allocated()/1024**2)
"

echo
echo "=== Step 4: HSA_OVERRIDE_GFX_VERSION=11.0.0 (RDNA 3 fallback) ==="
HSA_OVERRIDE_GFX_VERSION=11.0.0 python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('device_name:', torch.cuda.get_device_name(0))
    x = torch.randn(128, 128, device='cuda')
    y = x @ x
    print('matmul OK, shape:', y.shape, 'mem MB:', torch.cuda.memory_allocated()/1024**2)
" 2>&1 | head -20

echo
echo "=== Step 5: PYTORCH_ROCM_ARCH=gfx1201 without HSA override ==="
PYTORCH_ROCM_ARCH=gfx1201 python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
"

echo
echo "=== Step 6: detailed HSA log ==="
HSA_ENABLE_LOG=1 AMD_LOG_LEVEL=3 python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
" 2>&1 | tail -30
