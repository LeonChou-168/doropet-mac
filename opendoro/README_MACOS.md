# DoroPet macOS Apple Silicon

This macOS port targets Apple Silicon (`arm64`) and keeps the original PyQt5 + Live2D architecture.

## Requirements

- macOS on Apple Silicon
- Python 3.12 or 3.11 for arm64
- Optional: VLC in `/Applications/VLC.app` or Homebrew if you prefer the VLC music backend

The system `python3` may be too new for native packages. Use Homebrew Python 3.12 when possible:

```bash
brew install python@3.12
```

## Setup

```bash
cd /path/to/opendoro
scripts/setup_macos.sh
scripts/run_macos.sh
```

You can also double-click `DoroPet.command` after setup.

## Data Locations

Runtime data is stored outside the app bundle:

- App data: `~/Library/Application Support/DoroPet`
- Logs: `~/Library/Logs/DoroPet`
- Caches: `~/Library/Caches/DoroPet`
- Voice models: `~/Library/Application Support/DoroPet/models/voice`

## macOS Permissions

Voice features need microphone permission. If voice input fails, open:

`System Settings > Privacy & Security > Microphone`

Allow the terminal app you used to start DoroPet, or allow `DoroPet.app` after packaging.

## Music and Spectrum

macOS uses Qt Multimedia by default. VLC is optional and detected from `/Applications/VLC.app` or Homebrew library paths. If VLC is not installed, DoroPet logs a warning and keeps using Qt Multimedia.

The spectrum analyzer uses input-device capture on macOS. Capturing system output like Windows WASAPI loopback requires a virtual audio device; otherwise DoroPet falls back to simulated spectrum data.

## Build `.app`

```bash
scripts/build_macos_app.sh
open dist/DoroPet.app
```

The generated app is unsigned and intended for local use. For distribution, sign and notarize the app with an Apple Developer ID, then create a DMG.

## Notes

- This port is Apple Silicon-only.
- Windows `.bat` launchers are kept for Windows users.
- `pyaudiowpatch` is intentionally excluded from macOS dependencies because it targets Windows WASAPI loopback.
