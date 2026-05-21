#!/bin/bash
# Point torch at the WSL-aware libhsa-runtime64 from the system ROCm
# install, instead of the native-Linux one bundled in the wheel.
# Re-run this after any pip install or upgrade of torch.
set -uo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"
source .venv-wsl/bin/activate

TORCH_LIB="$(python -c 'import torch, os; print(os.path.dirname(torch.__file__))')/lib"
SYS_HSA="/opt/rocm-6.4.0/lib/libhsa-runtime64.so"

echo "=== Bundled libhsa (before) ==="
ls -la "$TORCH_LIB/libhsa-runtime64.so"*

echo
echo "=== System WSL libhsa ==="
ls -la /opt/rocm-6.4.0/lib/libhsa-runtime64.so*
echo "from package:"
dpkg -S /opt/rocm-6.4.0/lib/libhsa-runtime64.so.1.14.0

echo
echo "=== Sanity test with LD_PRELOAD ==="
LD_PRELOAD="$SYS_HSA" python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('device_name:', torch.cuda.get_device_name(0))
    x = torch.randn(128,128,device='cuda')
    y = (x @ x).sum().item()
    print('matmul OK:', y)
"

echo
echo "=== Rename bundled lib and symlink to the system one ==="
if [ ! -L "$TORCH_LIB/libhsa-runtime64.so" ]; then
    cp "$TORCH_LIB/libhsa-runtime64.so" "$TORCH_LIB/libhsa-runtime64.so.bundled"
    rm "$TORCH_LIB/libhsa-runtime64.so"
    ln -s "$SYS_HSA" "$TORCH_LIB/libhsa-runtime64.so"
    echo "Symlinked $TORCH_LIB/libhsa-runtime64.so to $SYS_HSA"
    ls -la "$TORCH_LIB/libhsa-runtime64.so"*
fi

echo
echo "=== Verify torch GPU access without LD_PRELOAD ==="
python -c "
import torch
print('cuda_avail:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('device_name:', torch.cuda.get_device_name(0))
    x = torch.randn(128,128,device='cuda')
    y = (x @ x).sum().item()
    print('matmul OK:', y)
    print('mem MB:', torch.cuda.memory_allocated()/1024**2)
"
