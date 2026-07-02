"""
高风险工具用户确认机制。

通过 Qt 信号向 UI 请求用户确认，支持超时自动取消 + 会话内"记住选择"。
"""

import asyncio
import json
import functools
import inspect
from enum import Enum
from typing import Optional, Callable

from src.core.logger import logger


# ---------------------------------------------------------------------------
# 风险等级定义
# ---------------------------------------------------------------------------

class RiskLevel(Enum):
    SAFE = "safe"           # 只读操作，无需确认
    LOW = "low"             # 可能产生副作用但不破坏
    MEDIUM = "medium"       # 可能修改用户数据
    HIGH = "high"           # 可能删除/覆盖/执行代码
    CRITICAL = "critical"   # 可能影响系统安全

    def value_index(self) -> int:
        """返回风险等级数值，用于比较。"""
        _order = {
            RiskLevel.SAFE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        return _order[self]


# ---------------------------------------------------------------------------
# 工具 → 风险等级映射
# ---------------------------------------------------------------------------

TOOL_RISK_LEVELS: dict[str, RiskLevel] = {
    # SAFE — 只读
    "read_file": RiskLevel.SAFE,
    "list_files": RiskLevel.SAFE,
    "search_files": RiskLevel.SAFE,
    "find_in_file": RiskLevel.SAFE,
    "search_baidu": RiskLevel.SAFE,
    "search_bing": RiskLevel.SAFE,
    "visit_webpage": RiskLevel.SAFE,
    "list_agent_skills": RiskLevel.SAFE,
    "get_skill_content": RiskLevel.SAFE,
    "search_memories": RiskLevel.SAFE,
    "browser_screenshot": RiskLevel.SAFE,
    "browser_get_content": RiskLevel.SAFE,
    "analyze_image": RiskLevel.SAFE,

    # LOW — 有副作用但不破坏
    "set_expression": RiskLevel.LOW,
    "modify_pet_attribute": RiskLevel.LOW,
    "browser_execute_js": RiskLevel.LOW,
    "add_memory": RiskLevel.LOW,

    # MEDIUM — 修改用户数据
    "write_file": RiskLevel.MEDIUM,
    "edit_file": RiskLevel.MEDIUM,
    "insert_at_line": RiskLevel.MEDIUM,
    "browser_navigate": RiskLevel.MEDIUM,
    "install_agent_skill": RiskLevel.MEDIUM,
    "generate_image": RiskLevel.MEDIUM,
    # 浏览器点击/输入是沙箱操作，不影响本地文件 → LOW
    "browser_type": RiskLevel.LOW,
    "browser_click": RiskLevel.LOW,

    # HIGH — 破坏性操作
    "delete_lines": RiskLevel.HIGH,
    "delete_memory": RiskLevel.HIGH,
    "remove_agent_skill": RiskLevel.HIGH,
    "run_python_script": RiskLevel.HIGH,
    "run_terminal_command": RiskLevel.HIGH,

    # CRITICAL — 系统安全
    "browser_open": RiskLevel.CRITICAL,
    "browser_close": RiskLevel.LOW,

    # Bridge 工具（用户真实 Chrome，Tab Group 隔离，扩展内置审批）
    "browser_bridge_start": RiskLevel.MEDIUM,
    "browser_bridge_stop": RiskLevel.LOW,
    "browser_bridge_navigate": RiskLevel.MEDIUM,
    "browser_bridge_read_text": RiskLevel.SAFE,
    "browser_bridge_get_tree": RiskLevel.SAFE,
    "browser_bridge_screenshot": RiskLevel.SAFE,
    "browser_bridge_click": RiskLevel.LOW,
    "browser_bridge_fill": RiskLevel.LOW,
    "browser_bridge_wait_for": RiskLevel.SAFE,
    "browser_bridge_execute_js": RiskLevel.LOW,
}


# ---------------------------------------------------------------------------
# 确认结果
# ---------------------------------------------------------------------------

class ConfirmResult(Enum):
    CONFIRMED = "confirmed"
    DENIED = "denied"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# ToolConfirmationManager
# ---------------------------------------------------------------------------

class ToolConfirmationManager:
    """工具确认管理器。

    与 LLMWorker 协作，在工具实际执行前插入确认环节。
    通过 Qt 信号机制向 UI 请求用户确认。
    """

    def __init__(
        self,
        confirm_callback: Optional[Callable] = None,
        default_timeout_seconds: int = 30,
        risk_threshold: RiskLevel = RiskLevel.MEDIUM,
    ):
        self.confirm_callback = confirm_callback
        self.default_timeout = default_timeout_seconds
        self.risk_threshold = risk_threshold
        self._pending_confirmations: dict[str, asyncio.Future] = {}
        self._session_allowlist: set[str] = set()  # 会话内免确认工具
        self._counter = 0  # 用于生成唯一 ID

    def needs_confirmation(self, tool_name: str) -> bool:
        """判断工具是否需要用户确认。"""
        if tool_name in self._session_allowlist:
            return False
        risk = TOOL_RISK_LEVELS.get(tool_name, RiskLevel.SAFE)
        return risk.value_index() >= self.risk_threshold.value_index()

    def get_risk_level(self, tool_name: str) -> str:
        """获取工具的风险等级字符串。"""
        return TOOL_RISK_LEVELS.get(tool_name, RiskLevel.SAFE).value

    def build_confirmation_message(self, tool_name: str, args: dict) -> str:
        """构建面向用户的确认弹窗消息。"""
        tool_display = self._display_name(tool_name)
        risk = self.get_risk_level(tool_name)
        key_info = self._extract_key_info(tool_name, args)

        return json.dumps({
            "tool": tool_name,
            "display_name": tool_display,
            "risk": risk,
            "info": key_info,
            "message": f"Doro 想要{key_info}\n\n风险等级: {risk}\n是否允许？",
            "timeout": self.default_timeout,
        }, ensure_ascii=False)

    async def request_confirmation(self, tool_name: str, args: dict) -> ConfirmResult:
        """请求用户确认，返回确认结果。

        如果没有配置 confirm_callback，则自动确认。
        """
        if not self.confirm_callback:
            return ConfirmResult.CONFIRMED

        self._counter += 1
        confirm_id = f"{tool_name}_{self._counter}"

        msg = self.build_confirmation_message(tool_name, args)

        # 创建 Future 等待用户响应
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_confirmations[confirm_id] = future

        # 发送确认信号到 UI（通过 Qt 信号跨线程调用）
        try:
            self.confirm_callback(msg, confirm_id, lambda confirmed: self._on_user_response(confirm_id, confirmed))
        except Exception as e:
            logger.error(f"[Confirm] Failed to send confirmation request: {e}")
            self._pending_confirmations.pop(confirm_id, None)
            return ConfirmResult.CONFIRMED  # 发送失败则自动确认

        # 等待用户响应或超时
        try:
            result = await asyncio.wait_for(future, timeout=self.default_timeout)
            return result
        except asyncio.TimeoutError:
            logger.info(f"[Confirm] Timeout for '{tool_name}', auto-denying")
            return ConfirmResult.TIMEOUT
        finally:
            self._pending_confirmations.pop(confirm_id, None)

    def _on_user_response(self, confirm_id: str, confirmed: bool):
        """用户点击确认/取消的回调（从主线程调用）。

        使用 call_soon_threadsafe 安全地将结果传回工作线程的事件循环。
        """
        future = self._pending_confirmations.get(confirm_id)
        if future and not future.done():
            result = ConfirmResult.CONFIRMED if confirmed else ConfirmResult.DENIED
            try:
                loop = future.get_loop()
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                logger.error(f"[Confirm] Failed to set result for {confirm_id}: {e}")

    def allow_session(self, tool_name: str):
        """会话内免确认（用户勾选"总是允许"）。"""
        self._session_allowlist.add(tool_name)
        logger.info(f"[Confirm] Session allowlist added: {tool_name}")

    # ----- 展示辅助 -----

    @staticmethod
    def _display_name(tool_name: str) -> str:
        names = {
            "write_file": "写入文件",
            "edit_file": "编辑文件",
            "delete_lines": "删除代码行",
            "run_python_script": "运行 Python 脚本",
            "remove_agent_skill": "删除技能",
            "delete_memory": "删除记忆",
            "browser_open": "打开浏览器",
            "browser_click": "点击网页元素",
            "browser_type": "在网页输入内容",
            "browser_navigate": "跳转网页",
            "install_agent_skill": "安装技能",
            "generate_image": "生成图片",
            "insert_at_line": "插入代码行",
            "browser_close": "关闭浏览器",
            "run_terminal_command": "执行终端命令",
        }
        return names.get(tool_name, tool_name)

    @staticmethod
    def _extract_key_info(tool_name: str, args: dict) -> str:
        """提取关键参数用于确认展示。"""
        if tool_name == "write_file":
            return f"写入文件: {args.get('file_path', '?')}"
        if tool_name == "edit_file":
            return f"编辑文件: {args.get('file_path', '?')}"
        if tool_name == "delete_lines":
            return f"删除 {args.get('file_path', '?')} 的第 {args.get('start_line', '?')}-{args.get('end_line', '?')} 行"
        if tool_name == "insert_at_line":
            return f"在 {args.get('file_path', '?')} 第 {args.get('line_number', '?')} 行插入内容"
        if tool_name == "run_python_script":
            script = args.get('script', args.get('file_path', '?'))
            if len(str(script)) > 60:
                script = str(script)[:57] + "..."
            return f"执行代码: {script}"
        if tool_name == "run_terminal_command":
            cmd = args.get('command', '?')
            if len(str(cmd)) > 60:
                cmd = str(cmd)[:57] + "..."
            return f"执行终端命令: {cmd}"
        if tool_name == "remove_agent_skill":
            return f"删除技能: {args.get('skill_name', '?')}"
        if tool_name == "delete_memory":
            return f"删除记忆 ID: {args.get('memory_id', '?')}"
        if tool_name == "browser_open":
            return f"打开浏览器"
        if tool_name == "browser_close":
            return f"关闭浏览器"
        if tool_name == "browser_click":
            return f"点击网页元素: {args.get('selector', args.get('index', '?'))}"
        if tool_name == "browser_type":
            return f"在 {args.get('selector', args.get('index', '?'))} 输入文本"
        if tool_name == "browser_navigate":
            return f"跳转网页: {args.get('url', '?')}"
        if tool_name == "install_agent_skill":
            return f"安装技能: {args.get('skill_url', args.get('skill_name', '?'))}"
        if tool_name == "generate_image":
            return f"生成图片: {str(args.get('prompt', ''))[:50]}..."
        return f"执行 {tool_name}"


# ---------------------------------------------------------------------------
# 工具包装函数
# ---------------------------------------------------------------------------

def make_tool_with_confirmation(tool_fn, tool_name: str, confirm_mgr: ToolConfirmationManager):
    """包装工具函数，在执行前检查是否需要用户确认。

    使用 functools.wraps 保留原始函数签名，
    确保 pydantic-ai 能正确解析工具参数。
    """

    @functools.wraps(tool_fn)
    async def wrapper(*args, **kwargs):
        if confirm_mgr.needs_confirmation(tool_name):
            # 将 *args 和 **kwargs 合并为参数字典
            try:
                sig = inspect.signature(tool_fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                args_dict = dict(bound.arguments)
            except Exception:
                args_dict = kwargs if kwargs else {}

            result = await confirm_mgr.request_confirmation(tool_name, args_dict)
            if result == ConfirmResult.DENIED:
                return json.dumps({
                    "status": "denied",
                    "message": "用户取消了此操作。"
                }, ensure_ascii=False)
            if result == ConfirmResult.TIMEOUT:
                return json.dumps({
                    "status": "denied",
                    "message": "操作超时未确认。"
                }, ensure_ascii=False)

        # 确认通过或无需确认 → 执行原始函数
        return await tool_fn(*args, **kwargs)

    return wrapper


def wrap_tools_with_confirmation(tools: list, confirm_mgr: ToolConfirmationManager) -> list:
    """对工具列表中的高风险工具进行包装。

    Args:
        tools: 原始工具函数列表
        confirm_mgr: 确认管理器

    Returns:
        包装后的工具函数列表
    """
    wrapped = []
    for tool_fn in tools:
        tool_name = getattr(tool_fn, '__name__', 'unknown')
        if confirm_mgr.needs_confirmation(tool_name):
            wrapped.append(make_tool_with_confirmation(tool_fn, tool_name, confirm_mgr))
        else:
            wrapped.append(tool_fn)
    return wrapped
