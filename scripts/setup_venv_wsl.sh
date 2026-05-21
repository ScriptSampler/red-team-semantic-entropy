#!/bin/bash
# Create the venv inside Ubuntu 24.04 WSL and install PyTorch ROCm 6.4 plus
# the project dependencies. Run as user abhi:
#   wsl -d Ubuntu-24.04 bash this-script
set -euo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"

echo "=== Python ==="
python3 --version
echo

echo "=== Create .venv-wsl ==="
if [ ! -d .venv-wsl ]; then
    python3 -m venv .venv-wsl
fi
source .venv-wsl/bin/activate
python --version
which python
which pip
echo

echo "=== Upgrade pip + base tools ==="
pip install --upgrade pip wheel setuptools

echo
echo "=== Install PyTorch ROCm 6.4 (torch 2.9.1, torchvision 0.24.1) ==="
pip install torch==2.9.1 torchvision==0.24.1 \
    --index-url https://download.pytorch.org/whl/rocm6.4

echo
echo "=== Verify torch GPU access ==="
python -c "
import torch
print('torch:', torch.__version__)
print('cuda_available:', torch.cuda.is_available())
print('device_count:', torch.cuda.device_count())
print('device_name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')
print('hip:', torch.version.hip)
print('cuda:', torch.version.cuda)
"

echo
echo "=== Install project dependencies (torch already pinned above) ==="
pip install \
    transformers==4.46.3 \
    datasets==3.1.0 \
    accelerate==1.1.1 \
    huggingface-hub==0.26.2 \
    safetensors==0.4.5 \
    tokenizers==0.20.3 \
    sentencepiece==0.2.0 \
    protobuf==5.28.3 \
    "numpy<2.2" \
    scipy==1.14.1 \
    scikit-learn==1.5.2 \
    pandas==2.2.3 \
    tqdm==4.67.0 \
    python-dotenv==1.0.1 \
    pyyaml==6.0.2 \
    click==8.1.7 \
    matplotlib==3.9.2 \
    seaborn==0.13.2 \
    jupyterlab==4.3.1 \
    ipykernel==6.29.5 \
    pytest==8.3.3

echo
echo "=== Apply the WSL libhsa fix ==="
# torch ships its own libhsa-runtime64.so that targets native Linux ROCm.
# In WSL we need the one from hsa-runtime-rocr4wsl-amdgpu. Symlink it.
TORCH_LIB="$(python -c 'import torch, os; print(os.path.dirname(torch.__file__))')/lib"
SYS_HSA="/opt/rocm-6.4.0/lib/libhsa-runtime64.so"
if [ -f "$SYS_HSA" ] && [ ! -L "$TORCH_LIB/libhsa-runtime64.so" ]; then
    mv "$TORCH_LIB/libhsa-runtime64.so" "$TORCH_LIB/libhsa-runtime64.so.bundled"
    ln -s "$SYS_HSA" "$TORCH_LIB/libhsa-runtime64.so"
    echo "Symlinked $TORCH_LIB/libhsa-runtime64.so to $SYS_HSA"
else
    echo "Symlink already in place, or system HSA not found. Skipping."
fi

echo
echo "=== Final verify: torch + transformers + datasets ==="
python -c "
import torch
import transformers
import datasets
print('torch:', torch.__version__, 'cuda:', torch.cuda.is_available(), 'hip:', torch.version.hip)
print('transformers:', transformers.__version__)
print('datasets:', datasets.__version__)
print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
"
