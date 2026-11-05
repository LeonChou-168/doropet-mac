# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path.cwd()

datas = [
    (str(ROOT / "data"), "data"),
    (str(ROOT / "models"), "models"),
    (str(ROOT / "themes"), "themes"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "plugin"), "plugin"),
    (str(ROOT / "src" / "skills"), "src/skills"),
    (str(ROOT / "src" / "agent" / "prompts"), "src/agent/prompts"),
]
datas += collect_data_files("live2d", includes=["v3/FrameworkShaders/*"])

# pydantic-ai / genai-prices / logfire etc. call importlib.metadata.version()
# at import time, so their distribution metadata must ship inside the bundle.
try:
    from importlib.metadata import distributions

    _dist_names = sorted(
        {(dist.metadata["Name"] or "").strip() for dist in distributions() if dist.metadata["Name"]}
    )
    for _name in _dist_names:
        try:
            datas += copy_metadata(_name)
        except Exception:
            pass
except Exception:
    pass

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PyQt5.QtMultimedia",
        "PyQt5.QtOpenGL",
        "live2d.v3",
        "OpenGL",
        "objc",
        "AppKit",
        "Foundation",
        "sounddevice",
        "sherpa_onnx",
        "sentencepiece",
        "pygame",
        "pydantic_ai",
        "pydantic_ai_slim",
        "playwright.async_api",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pyaudiowpatch",
        "winreg",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DoroPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DoroPet",
)

app = BUNDLE(
    coll,
    name="DoroPet.app",
    icon=str(ROOT / "data" / "icons" / "app.icns") if (ROOT / "data" / "icons" / "app.icns").exists() else None,
    bundle_identifier="com.doropet.app",
    info_plist={
        "CFBundleName": "DoroPet",
        "CFBundleDisplayName": "DoroPet",
        "CFBundleShortVersionString": "3.6.8-macos",
        "CFBundleVersion": "3.6.8",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "DoroPet needs microphone access for wake-word detection and speech recognition.",
    },
)
