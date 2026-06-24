#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE="${CLASHTX_CORE_PATH:-${ROOT_DIR}/vendor/mihomo/verge-mihomo}"
if [[ ! -x "${CORE}" ]]; then
  CORE="${ROOT_DIR}/vendor/mihomo/mihomo"
fi
CAPS="cap_net_admin,cap_net_bind_service+ep"

if ! command -v setcap >/dev/null 2>&1; then
  echo "setcap is required (install libcap2-bin)." >&2
  exit 1
fi

if command -v getcap >/dev/null 2>&1 && getcap "${CORE}" 2>/dev/null | grep -q cap_net_admin; then
  echo "Capabilities already set on ${CORE}"
  exit 0
fi

if setcap "${CAPS}" "${CORE}" 2>/dev/null; then
  echo "Granted ${CAPS} to ${CORE}"
  exit 0
fi

echo "Granting TUN capabilities requires root..." >&2
sudo setcap "${CAPS}" "${CORE}"
echo "Granted ${CAPS} to ${CORE}"
