#!/usr/bin/env bash
set -euo pipefail

_resolve_script_path() {
  local script_path="${BASH_SOURCE[0]}"
  while [[ -L "${script_path}" ]]; do
    local script_dir
    script_dir="$(cd "$(dirname "${script_path}")" && pwd)"
    script_path="$(readlink "${script_path}")"
    [[ "${script_path}" != /* ]] && script_path="${script_dir}/${script_path}"
  done
  printf '%s\n' "${script_path}"
}

_is_sourced() {
  [[ "${BASH_SOURCE[0]}" != "${0}" ]]
}

SCRIPT_PATH="$(_resolve_script_path)"
ROOT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
CONFIG_DIR="${CLASHTX_CONFIG_DIR:-${ROOT_DIR}/.runtime/config}"
PROXY_ENV="${CONFIG_DIR}/proxy.env"

_load_proxy_env() {
  if [[ ! -f "${PROXY_ENV}" ]]; then
    return 0
  fi
  if _is_sourced; then
    # shellcheck source=/dev/null
    source "${PROXY_ENV}"
    echo "Proxy environment loaded from ${PROXY_ENV}"
    return 0
  fi
  echo "Load proxy into the current shell with:" >&2
  echo "  source ${SCRIPT_PATH} start" >&2
  echo "  source ${SCRIPT_PATH} source" >&2
}

if [[ "${1:-}" == "source" ]]; then
  if [[ ! -f "${PROXY_ENV}" ]]; then
    echo "ClashTX proxy env not found: ${PROXY_ENV}" >&2
    echo "Enable system mode first: clashtx mode system" >&2
    exit 1
  fi
  if ! _is_sourced; then
    echo "Load proxy into the current shell with:" >&2
    echo "  source ${SCRIPT_PATH} source" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source "${PROXY_ENV}"
  echo "Proxy environment loaded from ${PROXY_ENV}"
  exit 0
fi

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
# Using your conda env
# please execute `pip install -e .` first.
# PYTHON_BIN="....../miniconda3/envs/....../bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ClashTX virtualenv is missing. Run ./scripts/install.sh first." >&2
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

_run_python() {
  export CLASHTX_SHELL=1
  "${PYTHON_BIN}" -m clashtx "$@"
}

case "${1:-}" in
  start|restart)
    _run_python "$@"
    exit_code=$?
    if [[ ${exit_code} -eq 0 ]]; then
      _load_proxy_env
    fi
    exit "${exit_code}"
    ;;
esac

exec "${PYTHON_BIN}" -m clashtx "$@"
