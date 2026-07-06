#!/usr/bin/env bash
set -euo pipefail

if [[ -e /dev/net/tun ]]; then
  exit 0
fi

if command -v modprobe >/dev/null 2>&1; then
  modprobe tun 2>/dev/null || true
fi

if [[ -e /dev/net/tun ]]; then
  exit 0
fi

echo "TUN device /dev/net/tun is unavailable." >&2
echo "Load the kernel module (modprobe tun) or run with CAP_NET_ADMIN." >&2
exit 1
