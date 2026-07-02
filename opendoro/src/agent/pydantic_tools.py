"""
DEPRECATED: 请使用 src.agent.tools 中的模块。

此文件保留用于向后兼容，计划在 v4.0 删除。
"""
import warnings
from src.agent.tools import *  # noqa: F403, E402

warnings.warn(
    "pydantic_tools.py is deprecated, use src.agent.tools instead",
    DeprecationWarning, stacklevel=2
)
