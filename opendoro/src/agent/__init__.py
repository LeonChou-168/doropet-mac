"""
DoroPet Agent 框架 — 基于 pydantic-ai。

核心模块：
- pydantic_agent.py: Agent 创建工厂和依赖定义
- pydantic_tools.py: 工具函数（文件操作、搜索、图片生成、宠物互动、技能管理）
- skills/: 技能管理（state.py 用于技能启停状态）
"""

from src.agent.pydantic_agent import (
    create_doro_agent,
    create_quick_agent,
    DoroDeps,
    DORO_SYSTEM_PROMPT,
    CAPABILITY_WEB_SEARCH,
    CAPABILITY_WEB_FETCH,
    CAPABILITY_THINKING,
    ALL_CAPABILITIES,
)

from src.agent.pydantic_tools import (
    get_filtered_tools,
    get_skill_tool_functions,
    ALL_TOOLS,
    TOOLS_BY_CATEGORY,
)

__all__ = [
    "create_doro_agent",
    "create_quick_agent",
    "DoroDeps",
    "DORO_SYSTEM_PROMPT",
    "CAPABILITY_WEB_SEARCH",
    "CAPABILITY_WEB_FETCH",
    "CAPABILITY_THINKING",
    "ALL_CAPABILITIES",
    "get_filtered_tools",
    "get_skill_tool_functions",
    "ALL_TOOLS",
    "TOOLS_BY_CATEGORY",
]
