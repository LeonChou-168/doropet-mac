"""工具注册表 — get_filtered_tools + get_skill_tool_functions。"""

import json
import re

from src.core.logger import logger


def get_filtered_tools(enabled_plugins: list[str]) -> list:
    """根据启用的插件过滤工具列表。

    技能管理工具始终加载，不受插件过滤影响。
    """
    from src.agent.tools import TOOLS_BY_CATEGORY, ALL_TOOLS, ALWAYS_ENABLED_TOOLS

    filtered = []

    category_enabled = {
        cat: cat in enabled_plugins
        for cat in TOOLS_BY_CATEGORY
    }

    for cat, tool_names in TOOLS_BY_CATEGORY.items():
        if category_enabled.get(cat, False):
            for name in tool_names:
                if name in ALL_TOOLS:
                    filtered.append(ALL_TOOLS[name])

    # 始终包含技能管理工具
    for name in ALWAYS_ENABLED_TOOLS:
        if name in ALL_TOOLS:
            filtered.append(ALL_TOOLS[name])

    return filtered


def get_skill_tool_functions() -> list:
    """从 SkillManager 获取可执行技能的函数引用列表。"""
    # 延迟导入避免循环依赖
    from src.agent.tools.skill_mgmt_tools import _get_skill_manager

    manager = _get_skill_manager()
    tools = []
    try:
        from src.agent.skills.state import SkillEnabledState
        state = SkillEnabledState.get_instance()
    except ImportError:
        state = None

    for name, skill in manager.skills.items():
        if state is not None and not state.is_enabled(name):
            continue
        if skill.function:
            normalized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            tools.append(make_skill_wrapper(skill, name, skill.function, normalized_name))

    return tools


def make_skill_wrapper(skill_obj, skill_name, func, normalized_name):
    """创建技能工具包装器。"""

    async def wrapper(**kwargs) -> str:
        try:
            result = func(**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps({"status": "success", "result": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[SkillTool] Error executing '{skill_name}': {e}")
            return json.dumps({"status": "error", "message": str(e)})

    wrapper.__name__ = normalized_name
    wrapper.__doc__ = skill_obj.description
    return wrapper
