#!/bin/bash
# Install ROCm 6.4 with WSL usecase inside Ubuntu-24.04.
# Run as root: wsl -d Ubuntu-24.04 -u root bash this-script
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
echo "=== Check available usecases ==="
amdgpu-install --list-usecase 2>&1 | head -40

echo
echo "=== Install ROCm 6.4 for WSL ==="
# --usecase=wsl,rocm pulls ROCm + the WSL DXG bridge (librocdxg.so)
# --no-dkms because WSL uses the Windows host driver, no kernel module needed
amdgpu-install --usecase=wsl,rocm --no-dkms -y

echo
echo "=== Verify librocdxg.so present ==="
find /opt/rocm* -name 'librocdxg*' 2>/dev/null

echo
echo "=== Verify rocminfo + libhsa versions ==="
which rocminfo
ls /opt/rocm/lib/libhsa-runtime*
ls /opt/rocm/lib/librocdxg* 2>/dev/null || echo "no librocdxg in /opt/rocm/lib"

echo
echo "=== Done. Run as user: rocminfo | grep -E 'gfx|Marketing' ==="
