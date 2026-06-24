#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
# Using your conda env
# PYTHON_BIN="....../miniconda3/envs/....../bin/python"


if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ClashTX virtualenv is missing. Run ./scripts/install.sh first." >&2
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" -m clashtx "$@"
