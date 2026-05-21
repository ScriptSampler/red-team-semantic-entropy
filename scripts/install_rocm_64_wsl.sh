#!/bin/bash
# Install ROCm 6.4 with the WSL usecase inside Ubuntu 24.04.
# Run as root:
#   wsl -d Ubuntu-24.04 -u root bash this-script
set -euo pipefail

echo "=== Download amdgpu-install 6.4 for noble ==="
cd /tmp
INSTALLER="amdgpu-install_6.4.60400-1_all.deb"
URL="https://repo.radeon.com/amdgpu-install/6.4/ubuntu/noble/${INSTALLER}"
if [ ! -f "$INSTALLER" ]; then
    wget -q --show-progress "$URL"
fi
ls -la "$INSTALLER"

echo
echo "=== Install amdgpu-install ==="
apt install -y "./${INSTALLER}"

echo
echo "=== Available usecases ==="
amdgpu-install --list-usecase 2>&1 | head -40

echo
echo "=== Install ROCm 6.4 for WSL ==="
# --usecase=wsl,rocm pulls in ROCm plus the WSL HSA shim (hsa-runtime-rocr4wsl-amdgpu).
# --no-dkms because the kernel driver lives on the Windows host in WSL.
amdgpu-install --usecase=wsl,rocm --no-dkms -y

echo
echo "=== Verify rocminfo and libhsa versions ==="
which rocminfo
ls /opt/rocm/lib/libhsa-runtime*

echo
echo "Done. As user: rocminfo | grep -E 'gfx|Marketing'"
