#!/bin/bash
# Bootstrap Ubuntu 24.04 WSL. Creates the user 'abhi', sets it as the default,
# and installs build tools. Run as root:
#   wsl -d Ubuntu-24.04 -u root bash this-script
set -euo pipefail

USERNAME="abhi"

echo "=== System update ==="
apt update
apt install -y wget curl gnupg ca-certificates build-essential sudo \
                python3 python3-venv python3-pip python3-dev git pciutils \
                vim less

echo
echo "=== Create user $USERNAME ==="
if ! id "$USERNAME" >/dev/null 2>&1; then
    useradd -m -s /bin/bash -G sudo,render,video "$USERNAME"
    # Passwordless sudo, consistent with the WSL convention.
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME
    chmod 0440 /etc/sudoers.d/$USERNAME
    # Set a password too, in case sudo NOPASSWD is ever revoked.
    echo "$USERNAME:abhi" | chpasswd
fi
id "$USERNAME"

echo
echo "=== Set default user in /etc/wsl.conf ==="
cat > /etc/wsl.conf <<EOF
[boot]
systemd=true

[user]
default=$USERNAME
EOF

echo
echo "Done. Run 'wsl --shutdown', then wsl -d Ubuntu-24.04 launches as $USERNAME."
