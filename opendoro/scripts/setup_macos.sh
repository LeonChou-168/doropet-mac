#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This setup script targets Apple Silicon (arm64)."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$candidate")"
      break
    fi
  done
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3.12 or 3.11 was not found."
  echo "Install one with Homebrew, for example: brew install python@3.12"
  exit 1
fi

VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$VERSION" != "3.12" && "$VERSION" != "3.11" ]]; then
  echo "Unsupported Python version: $VERSION. Please use Python 3.12 or 3.11."
  exit 1
fi

"$PYTHON_BIN" -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-macos.txt

echo "macOS environment is ready."
echo "Run: scripts/run_macos.sh"
