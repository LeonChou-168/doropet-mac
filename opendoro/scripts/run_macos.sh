#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv-macos/bin/python" ]]; then
  echo "Missing .venv-macos. Run scripts/setup_macos.sh first."
  exit 1
fi

export QT_MAC_WANTS_LAYER=1
export PYTHONUTF8=1
exec .venv-macos/bin/python main.py
