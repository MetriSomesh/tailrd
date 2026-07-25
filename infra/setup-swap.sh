#!/bin/bash
# Create a 2GB swapfile on EC2 t3.micro (1GB RAM).
# Swap is insurance against OOM when the agent subprocess spikes.
# vm.swappiness=10 means the kernel strongly prefers RAM and only swaps under pressure.
#
# Run once after provisioning: sudo bash setup-swap.sh

set -euo pipefail

SWAPFILE="/swapfile"
SWAP_SIZE="2G"

if [ -f "$SWAPFILE" ]; then
    echo "Swap already exists at $SWAPFILE. Skipping."
    swapon --show
    exit 0
fi

echo "Creating ${SWAP_SIZE} swapfile..."
fallocate -l "$SWAP_SIZE" "$SWAPFILE"
chmod 600 "$SWAPFILE"
mkswap "$SWAPFILE"
swapon "$SWAPFILE"

# Persist across reboots
echo "$SWAPFILE none swap sw 0 0" >> /etc/fstab

# Set swappiness low: only use swap under real pressure
echo "vm.swappiness=10" >> /etc/sysctl.conf
sysctl vm.swappiness=10

echo "Done. Swap status:"
swapon --show
free -h
