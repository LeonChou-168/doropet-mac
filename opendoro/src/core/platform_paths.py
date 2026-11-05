import os
import sys
from pathlib import Path

APP_NAME = "DoroPet"
APP_AUTHOR = "DoroPet"
BUNDLE_ID = "com.doropet.app"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform == "win32"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_app_root() -> str:
    """Return the resource root in dev and frozen PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS).resolve())
    return str(_source_root())


def get_executable_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return str((Path(get_app_root()) / "main.py").resolve())


def resource_path(relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute():
        return str(path.resolve())
    return str((Path(get_app_root()) / path).resolve())


def ensure_dir(path: str | Path) -> str:
    target = Path(path).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    return str(target.resolve())


def get_user_data_dir() -> str:
    override = os.environ.get("DOROPET_USER_DATA_DIR")
    if override:
        return ensure_dir(override)
    if is_windows():
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return ensure_dir(Path(base) / APP_NAME)
        return ensure_dir(Path.home() / "AppData" / "Local" / APP_NAME)
    if is_macos():
        return ensure_dir(Path.home() / "Library" / "Application Support" / APP_NAME)
    return ensure_dir(Path.home() / ".local" / "share" / APP_NAME)


def get_log_dir() -> str:
    override = os.environ.get("DOROPET_LOG_DIR")
    if override:
        return ensure_dir(override)
    if is_macos():
        return ensure_dir(Path.home() / "Library" / "Logs" / APP_NAME)
    return ensure_dir(Path(get_user_data_dir()) / "log")


def get_cache_dir() -> str:
    override = os.environ.get("DOROPET_CACHE_DIR")
    if override:
        return ensure_dir(override)
    if is_macos():
        return ensure_dir(Path.home() / "Library" / "Caches" / APP_NAME)
    if is_windows():
        return ensure_dir(Path(get_user_data_dir()) / "cache")
    return ensure_dir(Path.home() / ".cache" / APP_NAME)


def get_generated_images_dir() -> str:
    return ensure_dir(Path(get_user_data_dir()) / "generated_images")


def get_voice_models_dir() -> str:
    return ensure_dir(Path(get_user_data_dir()) / "models" / "voice")


def get_user_skills_dir() -> str:
    return ensure_dir(Path(get_user_data_dir()) / "skills")


def get_attachments_dir() -> str:
    return ensure_dir(Path(get_user_data_dir()) / "attachments")


def get_music_outputs_dir() -> str:
    return ensure_dir(Path(get_user_data_dir()) / "musicdl_outputs")
