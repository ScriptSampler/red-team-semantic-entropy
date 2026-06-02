#!/bin/bash
# Quick start-of-session check: GPU, HF auth, cache location.
cd "/mnt/i/GITHUBPROJECTS/SE Research"
source .venv-wsl/bin/activate

echo "=== torch GPU ==="
python -c "import torch; print('cuda:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

echo
echo "=== HF auth (whoami) ==="
huggingface-cli whoami 2>&1 || echo "no token configured"

echo
echo "=== HF env vars ==="
env | grep -iE 'HF_TOKEN|HUGGING|HF_HOME' || echo "none set (HF cache defaults to ~/.cache/huggingface)"

echo
echo "=== disk free on Linux home + /mnt/i ==="
df -h "$HOME" /mnt/i 2>/dev/null | awk 'NR==1 || /home|mnt/'
