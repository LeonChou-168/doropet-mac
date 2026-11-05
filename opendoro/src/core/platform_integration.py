import os
import plistlib
import subprocess
import sys
from pathlib import Path

from src.core.platform_paths import (
    APP_NAME,
    BUNDLE_ID,
    get_app_root,
    get_executable_path,
    is_macos,
    is_windows,
    resource_path,
)


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def open_path(path: str) -> bool:
    """Open a file or directory with the platform default application."""
    try:
        if is_macos():
            subprocess.Popen(["open", path])
        elif is_windows():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _mac_run_script_path() -> str:
    return str((Path(get_app_root()) / "scripts" / "run_macos.sh").resolve())


def is_autorun_enabled() -> bool:
    if is_macos():
        return _launch_agent_path().exists()
    if is_windows():
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False
    return False


def set_autorun_enabled(enabled: bool) -> tuple[bool, str]:
    if is_macos():
        return _set_macos_autorun(enabled)
    if is_windows():
        return _set_windows_autorun(enabled)
    return False, "当前平台暂不支持开机启动配置"


def _set_macos_autorun(enabled: bool) -> tuple[bool, str]:
    plist_path = _launch_agent_path()
    try:
        if enabled:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            program = get_executable_path() if getattr(sys, "frozen", False) else _mac_run_script_path()
            plist = {
                "Label": BUNDLE_ID,
                "ProgramArguments": [program],
                "RunAtLoad": True,
                "WorkingDirectory": get_app_root(),
                "StandardOutPath": str(Path.home() / "Library" / "Logs" / f"{APP_NAME}.out.log"),
                "StandardErrorPath": str(Path.home() / "Library" / "Logs" / f"{APP_NAME}.err.log"),
            }
            with open(plist_path, "wb") as f:
                plistlib.dump(plist, f)
            return True, f"已启用 macOS 开机启动: {plist_path}"

        if plist_path.exists():
            plist_path.unlink()
        return True, "已关闭 macOS 开机启动"
    except Exception as e:
        return False, f"macOS 开机启动配置失败: {e}"


def _set_windows_autorun(enabled: bool) -> tuple[bool, str]:
    try:
        import winreg

        app_dir = get_app_root()
        bat_path = os.path.join(app_dir, "start_app_background.bat")
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE,
        )
        try:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, bat_path)
                return True, f"已启用 Windows 开机启动: {bat_path}"
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            return True, "已关闭 Windows 开机启动"
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        return False, f"Windows 开机启动配置失败: {e}"


def create_desktop_launcher(shortcut_name: str = APP_NAME, replace_existing: bool = False) -> tuple[bool, str]:
    if is_macos():
        return _create_macos_launcher(shortcut_name, replace_existing)
    if is_windows():
        return _create_windows_shortcut(shortcut_name, replace_existing)
    return False, "当前平台暂不支持创建桌面启动器"


def _create_macos_launcher(shortcut_name: str, replace_existing: bool) -> tuple[bool, str]:
    try:
        desktop = Path.home() / "Desktop"
        desktop.mkdir(exist_ok=True)
        launcher = desktop / f"{shortcut_name}.command"
        if launcher.exists() and not replace_existing:
            return False, "启动器已存在"
        run_script = _mac_run_script_path()
        launcher.write_text(
            "#!/bin/zsh\n"
            f"cd {sh_quote(get_app_root())}\n"
            f"exec {sh_quote(run_script)}\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        return True, f"桌面启动器已创建: {launcher}"
    except Exception as e:
        return False, f"创建 macOS 桌面启动器失败: {e}"


def _create_windows_shortcut(shortcut_name: str, replace_existing: bool) -> tuple[bool, str]:
    try:
        app_dir = get_app_root()
        bat_path = os.path.join(app_dir, "start_app_background.bat")
        icon_path = resource_path("data/icons/app.ico")
        if not os.path.exists(bat_path):
            return False, f"启动脚本不存在: {bat_path}"

        result = subprocess.run(
            ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return False, "无法获取桌面路径"

        shortcut_path = os.path.join(result.stdout.strip(), f"{shortcut_name}.lnk")
        if os.path.exists(shortcut_path) and not replace_existing:
            return False, "快捷方式已存在"

        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{bat_path}"
$Shortcut.WorkingDirectory = "{app_dir}"
$Shortcut.Description = "DoroPet Desktop Pet"
{f'$Shortcut.IconLocation = "{icon_path}"' if os.path.exists(icon_path) else ''}
$Shortcut.Save()
'''
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            return True, f"快捷方式已创建: {shortcut_path}"
        return False, result.stderr.strip() or "创建快捷方式失败"
    except Exception as e:
        return False, f"创建 Windows 快捷方式失败: {e}"
