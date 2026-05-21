#!/bin/bash
set -uo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"
source .venv-wsl/bin/activate

echo "=== torch package location ==="
python -c "import torch; print(torch.__file__)"
TORCH_DIR=$(python -c "import torch, os; print(os.path.dirname(torch.__file__))")
echo "torch dir: $TORCH_DIR"

echo
echo "=== libs in torch/lib/ ==="
ls "$TORCH_DIR/lib/" 2>/dev/null | head -40

echo
echo "=== libamdhip64 / libhsa in torch/lib ==="
ls "$TORCH_DIR/lib/" 2>/dev/null | grep -iE 'hip|hsa|amd|rocm' | head -20

echo
echo "=== Check rocBLAS kernel arch list inside torch ==="
find "$TORCH_DIR" -name '*.dat' -path '*rocblas*' 2>/dev/null | head -5
find "$TORCH_DIR" -name '*gfx*' 2>/dev/null | head -20

echo
echo "=== torch internal lookup of arches ==="
python <<'PY'
import torch
# torch.cuda.get_arch_list() returns from internal table; let's also try the build info
try:
    print("get_arch_list:", torch.cuda.get_arch_list())
except Exception as e:
    print("get_arch_list err:", e)
try:
    print("torch._C._cuda_getArchFlags:", torch._C._cuda_getArchFlags() if hasattr(torch._C, '_cuda_getArchFlags') else 'N/A')
except Exception as e:
    print("getArchFlags err:", e)
# print torch.__config__.show()
print()
print("=== torch config dump ===")
print(torch.__config__.show())
PY

echo
echo "=== Library load: which libhsa does torch use? ==="
python -c "
import torch
import ctypes
# Force load torch's HIP runtime, then check
hip = torch._C
print('torch._C loaded:', hip)
" 2>&1 | head -10

echo
echo "=== Direct ldd on torch's libamdhip ==="
ldd "$TORCH_DIR/lib/libamdhip64.so" 2>&1 | grep -E 'hsa|hip|amd|rocm|not found' | head -20

echo
echo "=== rocminfo as user abhi (sanity) ==="
rocminfo 2>&1 | grep -E 'Marketing|gfx1201' | head -4
