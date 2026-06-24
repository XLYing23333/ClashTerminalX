#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python 3 is required but was not found: ${PYTHON_BIN}" >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install \
  "fastapi>=0.115" \
  "httpx>=0.27" \
  "platformdirs>=4.2" \
  "pyyaml>=6.0" \
  "rich>=13.7" \
  "textual>=0.70" \
  "uvicorn>=0.32" \
  "pytest>=8.2"

cat > "${ROOT_DIR}/clashtx.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ClashTX virtualenv is missing. Run ./scripts/install.sh first." >&2
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" -m clashtx "$@"
EOF

chmod +x "${ROOT_DIR}/clashtx.sh"

chmod +x "${ROOT_DIR}/vendor/tun/ensure-tun.sh" 2>/dev/null || true
chmod +x "${ROOT_DIR}/vendor/tun/grant-caps.sh" 2>/dev/null || true

echo "ClashTX installed."
echo "Run: ${ROOT_DIR}/clashtx.sh help"
echo "For TUN mode, grant Mihomo capabilities once:"
echo "  ${ROOT_DIR}/vendor/tun/grant-caps.sh"
