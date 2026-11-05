"""
Agent 工具函数包。

每个子模块负责一类工具，__init__.py 汇总注册。
"""
from typing import Any

from src.agent.tools._helpers import (
    _get_project_dir, _format_permission_error, _format_file_not_found_error,
)
from src.agent.tools.file_tools import (
    read_file, write_file, list_files, search_files, edit_file,
    insert_at_line, delete_lines, find_in_file,
)
from src.agent.tools.code_tools import run_python_script
from src.agent.tools.terminal_tools import run_terminal_command
from src.agent.tools.search_tools import search_baidu, search_bing, visit_webpage
from src.agent.tools.pet_tools import set_expression, modify_pet_attribute
from src.agent.tools.image_tools import generate_image, analyze_image
from src.agent.tools.skill_mgmt_tools import (
    install_agent_skill, list_agent_skills, get_skill_content, remove_agent_skill,
)
from src.agent.tools.memory_tools import search_memories, add_memory, delete_memory
from src.agent.tools.browser_control import BROWSER_TOOLS
from src.agent.tools.browser_bridge import BRIDGE_TOOLS

# ── 分类注册表（仅用于插件过滤）──
TOOLS_BY_CATEGORY = {
    "file": ["read_file", "write_file", "list_files", "search_files", "edit_file",
             "insert_at_line", "delete_lines", "find_in_file"],
    "coding": ["run_python_script", "run_terminal_command"],
    "search": ["search_baidu", "search_bing", "visit_webpage"],
    "image": ["generate_image"],
    "vision": ["analyze_image"],
    "expression": ["set_expression", "modify_pet_attribute"],
    "memory": ["search_memories", "add_memory", "delete_memory"],
    "browser": ["browser_open", "browser_navigate", "browser_click", "browser_type",
                "browser_screenshot", "browser_get_content", "browser_execute_js", "browser_close"],
    "bridge": ["browser_bridge_start", "browser_bridge_stop", "browser_bridge_navigate",
               "browser_bridge_read_text", "browser_bridge_get_tree", "browser_bridge_screenshot",
               "browser_bridge_click", "browser_bridge_fill", "browser_bridge_wait_for",
               "browser_bridge_execute_js"],
}

# 始终启用的工具（不受插件过滤影响）
ALWAYS_ENABLED_TOOLS = [
    "install_agent_skill", "list_agent_skills",
    "get_skill_content", "remove_agent_skill",
]

# ── 全局工具注册表 ──
ALL_TOOLS: dict[str, Any] = {
    # 文件
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "search_files": search_files,
    "edit_file": edit_file,
    "insert_at_line": insert_at_line,
    "delete_lines": delete_lines,
    "find_in_file": find_in_file,
    # 代码执行
    "run_python_script": run_python_script,
    # 终端命令
    "run_terminal_command": run_terminal_command,
    # 搜索
    "search_baidu": search_baidu,
    "search_bing": search_bing,
    "visit_webpage": visit_webpage,
    # 图片
    "generate_image": generate_image,
    "analyze_image": analyze_image,
    # 宠物
    "set_expression": set_expression,
    "modify_pet_attribute": modify_pet_attribute,
    # 技能管理（始终启用）
    "install_agent_skill": install_agent_skill,
    "list_agent_skills": list_agent_skills,
    "get_skill_content": get_skill_content,
    "remove_agent_skill": remove_agent_skill,
    # 记忆
    "search_memories": search_memories,
    "add_memory": add_memory,
    "delete_memory": delete_memory,
    # 浏览器
    **BROWSER_TOOLS,
    # Bridge（用户真实 Chrome）
    **BRIDGE_TOOLS,
}

from src.agent.tools.registry import get_filtered_tools, get_skill_tool_functions

__all__ = [
    "ALL_TOOLS", "TOOLS_BY_CATEGORY", "ALWAYS_ENABLED_TOOLS",
    "get_filtered_tools", "get_skill_tool_functions",
    "read_file", "write_file", "list_files", "search_files", "edit_file",
    "insert_at_line", "delete_lines", "find_in_file", "run_python_script",
    "search_baidu", "search_bing", "visit_webpage",
    "set_expression", "modify_pet_attribute",
    "generate_image", "analyze_image",
    "install_agent_skill", "list_agent_skills",
    "get_skill_content", "remove_agent_skill",
    "search_memories", "add_memory", "delete_memory",
]
