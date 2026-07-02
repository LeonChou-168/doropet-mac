"""
应用程序级别配置系统。

配置文件位置：%APPDATA%\DoroPet\config\doro_config.json
与用户数据目录（%LOCALAPPDATA%\DoroPet\）分离，确保配置在数据迁移后依然有效。
"""

import os
import json
from typing import Optional

CONFIG_FILENAME = "doro_config.json"


def get_config_dir():
    """获取配置文件目录。放在 %APPDATA% 下而非 %LOCALAPPDATA%，与用户数据分离。"""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "DoroPet", "config")


def get_config_path():
    """获取配置文件完整路径。"""
    return os.path.join(get_config_dir(), CONFIG_FILENAME)


def load_config() -> dict:
    """加载配置文件，返回 dict。文件不存在时返回空 dict。"""
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: dict):
    """保存配置文件。"""
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_data_dir() -> Optional[str]:
    """
    获取用户自定义的数据目录路径。
    优先级：config.json > 环境变量 DOROPET_DATA_DIR > None（使用默认）
    返回 None 表示未设置自定义路径，应使用默认路径。
    """
    config = load_config()
    custom_path = config.get("data_dir")
    if custom_path and os.path.isdir(custom_path):
        return custom_path

    env_path = os.environ.get("DOROPET_DATA_DIR")
    if env_path and os.path.isdir(env_path):
        return env_path

    return None


def set_data_dir(path: str):
    """设置自定义数据目录并保存到配置文件。"""
    config = load_config()
    config["data_dir"] = path
    save_config(config)


def clear_data_dir():
    """清除自定义数据目录配置，恢复默认路径。"""
    config = load_config()
    config.pop("data_dir", None)
    save_config(config)
