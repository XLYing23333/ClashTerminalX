#!/usr/bin/env bash
# Optional shell integration for auto-loading proxy on start/restart.
#
# Add to ~/.bashrc or ~/.zshrc:
#   export CLASHTX_ROOT=/path/to/ClashTerminalX
#   source /path/to/ClashTerminalX/scripts/clashtx-shell.sh

: "${CLASHTX_ROOT:?Set CLASHTX_ROOT to your ClashTX install directory}"

_clashtx_script="${CLASHTX_ROOT}/clashtx.sh"

if [[ ! -x "${_clashtx_script}" ]]; then
  echo "ClashTX entry script not found: ${_clashtx_script}" >&2
  return 1 2>/dev/null || exit 1
fi

clashtx() {
  case "${1:-}" in
    start|restart|source)
      # shellcheck source=/dev/null
      source "${_clashtx_script}" "$@" ;;
    *)
      "${_clashtx_script}" "$@" ;;
  esac
}
