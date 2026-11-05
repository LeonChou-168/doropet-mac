#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This build script targets Apple Silicon (arm64)."
  exit 1
fi

if [[ ! -x ".venv-macos/bin/python" ]]; then
  echo "Missing .venv-macos. Run scripts/setup_macos.sh first."
  exit 1
fi

source .venv-macos/bin/activate
python -m PyInstaller --clean --noconfirm packaging/macos/DoroPet.spec

echo "Built dist/DoroPet.app"
echo "Unsigned local app bundle. For distribution, sign and notarize it separately."
