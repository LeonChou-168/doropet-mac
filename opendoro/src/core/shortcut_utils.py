import os
from pathlib import Path

from src.core.logger import logger
from src.core.platform_integration import create_desktop_launcher
from src.core.platform_paths import APP_NAME, is_macos, is_windows


def create_desktop_shortcut(shortcut_name: str = APP_NAME, replace_existing: bool = False) -> tuple[bool, str]:
    success, message = create_desktop_launcher(shortcut_name, replace_existing)
    if success:
        logger.info(message)
    else:
        logger.warning(message)
    return success, message


def remove_desktop_shortcut(shortcut_name: str = APP_NAME) -> tuple[bool, str]:
    try:
        suffix = ".command" if is_macos() else ".lnk"
        shortcut_path = Path.home() / "Desktop" / f"{shortcut_name}{suffix}"
        if not shortcut_path.exists():
            return True, "快捷方式不存在"
        shortcut_path.unlink()
        logger.info(f"Desktop shortcut removed: {shortcut_path}")
        return True, "快捷方式已删除"
    except Exception as e:
        logger.error(f"Error removing desktop shortcut: {e}")
        return False, f"删除快捷方式时出错: {e}"


def shortcut_exists(shortcut_name: str = APP_NAME) -> bool:
    suffix = ".command" if is_macos() else ".lnk"
    return (Path.home() / "Desktop" / f"{shortcut_name}{suffix}").exists()


def _get_desktop_path() -> str | None:
    desktop = Path.home() / "Desktop"
    return str(desktop) if desktop.exists() else None


def _get_app_directory() -> str | None:
    try:
        current_file = os.path.abspath(__file__)
        src_core_dir = os.path.dirname(current_file)
        src_dir = os.path.dirname(src_core_dir)
        return os.path.dirname(src_dir)
    except Exception:
        return None
