#!/usr/bin/env bash
# Source safely: do not change the caller's shell options or exit its terminal.
_clashtx_is_sourced() {
  if [[ -n "${ZSH_VERSION:-}" ]]; then
    [[ "${ZSH_EVAL_CONTEXT:-}" == *:file* ]]
  else
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
  fi
}

_clashtx_main() {
  local script_path
  if [[ -n "${ZSH_VERSION:-}" ]]; then
    script_path="${(%):-%x}"
  else
    script_path="${BASH_SOURCE[0]}"
  fi
  while [[ -L "$script_path" ]]; do
    local script_dir
    script_dir="$(cd "$(dirname "$script_path")" && pwd)" || return
    script_path="$(readlink "$script_path")" || return
    [[ "$script_path" != /* ]] && script_path="$script_dir/$script_path"
  done
  local root_dir config_dir proxy_env python_bin result
  root_dir="$(cd "$(dirname "$script_path")" && pwd)" || return
  config_dir="${CLASHTX_CONFIG_DIR:-$root_dir/.runtime/config}"
  proxy_env="$config_dir/proxy.env"
  if [[ "${1:-}" == source ]]; then
    if [[ ! -f "$proxy_env" ]]; then
      echo "ClashTX proxy env not found: $proxy_env" >&2
      return 1
    fi
    if ! _clashtx_is_sourced; then
      echo "Load proxy with: source $script_path source" >&2
      return 1
    fi
    source "$proxy_env" || return
    echo "Proxy environment loaded from $proxy_env"
    return 0
  fi
  python_bin="$root_dir/.venv/bin/python"
  if [[ ! -x "$python_bin" ]]; then
    echo "ClashTX virtualenv is missing. Run ./scripts/install.sh first." >&2
    return 1
  fi
  if PYTHONPATH="$root_dir/src${PYTHONPATH:+:$PYTHONPATH}" CLASHTX_SHELL=1 "$python_bin" -m clashtx "$@"; then
    result=0
  else
    result=$?
  fi
  if [[ $result -eq 0 && ( "${1:-}" == start || "${1:-}" == restart ) && -f "$proxy_env" ]]; then
    if _clashtx_is_sourced; then
      source "$proxy_env" || return
      echo "Proxy environment loaded from $proxy_env"
    else
      echo "Load proxy with: source $script_path source" >&2
    fi
  fi
  return "$result"
}

if _clashtx_main "$@"; then
  _clashtx_result=0
else
  _clashtx_result=$?
fi
if _clashtx_is_sourced; then
  return "$_clashtx_result"
fi
exit "$_clashtx_result"
