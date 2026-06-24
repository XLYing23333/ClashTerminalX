#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${ROOT_DIR}/vendor/geodata"
CDN="https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release"

mkdir -p "${TARGET_DIR}"

curl -L --connect-timeout 30 --max-time 600 \
  -o "${TARGET_DIR}/geoip.metadb" \
  "${CDN}/geoip.metadb"

curl -L --connect-timeout 30 --max-time 600 \
  -o "${TARGET_DIR}/geosite.dat" \
  "${CDN}/geosite.dat"

ls -lh "${TARGET_DIR}"
