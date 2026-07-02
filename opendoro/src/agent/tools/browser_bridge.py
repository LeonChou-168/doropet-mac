"""
Browser Agent Bridge 集成模块。

通过 JSON-RPC over HTTP 调用本地 Chrome 扩展 + Native Host，
操控用户真实浏览器。相比 Playwright 方案的优势：
- 使用用户真实 Chrome（登录态、cookie 保留）
- 无障碍树 + ref 引用（精确定位，不需反复推导选择器）
- whatChanged 增量反馈（每次操作后知道页面哪里变了）
- Tab Group 隔离

如果 Bridge 未运行，所有工具返回明确的设置指引。
"""

import asyncio
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from src.core.logger import logger

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765
BRIDGE_BASE_URL = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}"

SETUP_GUIDE = """Browser Agent Bridge 未运行。请按以下步骤设置：

1. 克隆仓库：
   git clone https://github.com/TNJ2026/browser-agent-bridge.git

2. 加载扩展：打开 chrome://extensions → 开发者模式 → 加载已解压的扩展 → 选择 extension/ 目录

3. 安装 Native Host（Windows PowerShell）：
   .\scripts\install-native-host-win.ps1 lpemchcojepfkbgjgoehfknibdjjppig

4. 打开扩展侧边栏，点击 Start Bridge

5. 验证：python scripts/browser_bridge_client.py health"""


# ---------------------------------------------------------------------------
# BridgeClient — 异步 HTTP JSON-RPC 客户端
# ---------------------------------------------------------------------------

class BridgeClient:
    """Browser Agent Bridge 的异步 HTTP 客户端。

    自动加载认证 token，所有调用在线程池中执行以避免阻塞事件循环。
    """

    _instance: Optional["BridgeClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._token: Optional[str] = None
            cls._instance._token_loaded = False
            cls._instance._session_id: Optional[str] = None
            cls._instance._tab_id: Optional[int] = None
            cls._instance._available: Optional[bool] = None
        return cls._instance

    # -- token 加载 --------------------------------------------------------

    def _load_token(self) -> Optional[str]:
        """从环境变量或 token 文件加载认证 token。"""
        if self._token_loaded:
            return self._token

        token = os.environ.get("BROWSER_AGENT_BRIDGE_TOKEN", "")
        if token:
            self._token = token
            self._token_loaded = True
            return token

        # Windows: %USERPROFILE%\.browser-agent-bridge.env
        # macOS/Linux: ~/.browser-agent-bridge.env
        env_file = Path.home() / ".browser-agent-bridge.env"
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("BROWSER_AGENT_BRIDGE_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip("'\"")
                        break
            except Exception:
                pass

        if token:
            self._token = token
        self._token_loaded = True
        return token or None

    # -- 健康检查 ----------------------------------------------------------

    async def check_health(self) -> dict:
        """检查 Bridge 是否可用。"""
        try:
            result = await self._request("GET", "/health", auth=False)
            self._available = True
            return result
        except Exception:
            self._available = False
            return {"status": "unavailable"}

    @property
    def is_available(self) -> bool:
        if self._available is None:
            return False
        return self._available

    # -- 会话管理 ----------------------------------------------------------

    async def ensure_session(self, url: str = "") -> dict:
        """确保有一个活跃的 Bridge 会话。已存在则复用，否则创建新的。"""
        if self._session_id:
            try:
                result = await self.rpc("session.get", {"sessionId": self._session_id})
                tabs = result.get("tabs", [])
                if tabs:
                    self._tab_id = tabs[0].get("id")
                return {"session_id": self._session_id, "tab_id": self._tab_id}
            except Exception:
                logger.info("[Bridge] Session lost, creating new one")
                self._session_id = None
                self._tab_id = None

        result = await self.rpc("session.start", {
            "name": "DoroPet",
            "url": url or "about:blank",
            "active": True,
        })
        self._session_id = result.get("session", {}).get("id")
        self._tab_id = result.get("tab", {}).get("id")
        logger.info(f"[Bridge] Session started: {self._session_id}, tab: {self._tab_id}")
        return {"session_id": self._session_id, "tab_id": self._tab_id}

    async def stop_session(self):
        """停止当前会话。"""
        if self._session_id:
            try:
                await self.rpc("session.stop", {"sessionId": self._session_id})
                logger.info(f"[Bridge] Session stopped: {self._session_id}")
            except Exception as e:
                logger.warning(f"[Bridge] Error stopping session: {e}")
            self._session_id = None
            self._tab_id = None

    # -- JSON-RPC ----------------------------------------------------------

    async def rpc(self, method: str, params: dict = None, request_id: str = None) -> dict:
        """发送 JSON-RPC 请求并返回 result。"""
        body = {
            "jsonrpc": "2.0",
            "id": request_id or method,
            "method": method,
            "params": params or {},
        }
        response = await self._request("POST", "/rpc", body, auth=True)
        if "error" in response:
            error = response["error"]
            raise BridgeError(error.get("message", "JSON-RPC error"), error.get("data"))
        return response.get("result", {})

    # -- HTTP 底层 ---------------------------------------------------------

    async def _request(self, method: str, path: str, body: dict = None, auth: bool = True) -> dict:
        """在 asyncio 线程池中执行 HTTP 请求。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._request_sync, method, path, body, auth)

    def _request_sync(self, method: str, path: str, body: dict, auth: bool) -> dict:
        """同步 HTTP 请求实现。"""
        url = f"{BRIDGE_BASE_URL}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if auth:
            token = self._load_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise BridgeError(f"HTTP {e.code}: {body_text}")
        except urllib.error.URLError as e:
            raise BridgeError(f"连接失败: {e.reason}")


class BridgeError(Exception):
    """Bridge JSON-RPC 错误。"""
    def __init__(self, message: str, data=None):
        super().__init__(message)
        self.data = data


# ---------------------------------------------------------------------------
# 全局客户端获取
# ---------------------------------------------------------------------------

def get_bridge() -> BridgeClient:
    return BridgeClient()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _bridge_unavailable() -> str:
    return json.dumps({
        "status": "error",
        "message": SETUP_GUIDE,
    }, ensure_ascii=False)


async def _get_tab_id(bridge: BridgeClient) -> Optional[int]:
    """获取当前活跃 tab ID，如果需要则创建 session。"""
    info = await bridge.ensure_session()
    return info.get("tab_id")


# ── session 管理 ────────────────────────────────────────────────────────


async def browser_bridge_start(url: str = "") -> str:
    """启动浏览器桥接会话（在用户真实 Chrome 中创建隔离标签组）。

    使用前请确保已安装 Browser Agent Bridge 扩展并点击 Start Bridge。

    Args:
        url: 可选的初始导航 URL（例如 "https://www.google.com"）。
    """
    bridge = get_bridge()

    if not bridge.is_available:
        health = await bridge.check_health()
        if not bridge.is_available:
            return _bridge_unavailable()

    try:
        info = await bridge.ensure_session(url)
        return json.dumps({
            "status": "success",
            "message": f"Bridge 会话已启动。",
            "session_id": info["session_id"],
            "tab_id": info["tab_id"],
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_stop() -> str:
    """停止浏览器桥接会话，关闭隔离标签组。"""
    bridge = get_bridge()
    try:
        await bridge.stop_session()
        return json.dumps({"status": "success", "message": "Bridge 会话已停止。"}, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# ── 页面操作 ────────────────────────────────────────────────────────────


async def browser_bridge_navigate(url: str) -> str:
    """在 Bridge 标签中导航到指定 URL。

    Args:
        url: 目标 URL。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        result = await bridge.rpc("page.navigate", {
            "tabId": tab_id,
            "url": url,
            "wait": True,
            "timeoutMs": 30000,
        })
        return json.dumps({
            "status": "success",
            "message": f"已导航到 {url}",
            "url": result.get("url", url),
            "title": result.get("title", ""),
            "whatChanged": result.get("whatChanged"),
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_read_text() -> str:
    """获取当前页面的可见文本内容。

    比 Playwright 版更准确——会过滤脚本、样式等不可见内容。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        result = await bridge.rpc("page.readText", {"tabId": tab_id})
        text = result.get("text", "")
        if len(text) > 8000:
            text = text[:8000] + f"\n... (截断，共 {len(text)} 字符)"
        return json.dumps({
            "status": "success",
            "message": f"页面内容 ({len(text)} 字符)",
            "content": text,
            "url": result.get("url", ""),
            "title": result.get("title", ""),
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_get_tree(max_nodes: int = 200) -> str:
    """获取页面无障碍树（结构化元素列表，每个元素带有 ref 标识）。

    这是 Bridge 最核心的优势功能。返回的元素列表包含：
    - ref: 唯一引用标识（可用于后续 clickRef/fillRef 精确定位）
    - role: 元素角色（button, link, textbox 等）
    - name: 元素名称/文本
    - tag: HTML 标签

    相比截图和原始文本，AI 能更准确理解页面结构和交互元素。

    Args:
        max_nodes: 最大返回节点数（默认 200，compact 模式下控制输出大小）。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        result = await bridge.rpc("page.accessibilityTree", {
            "tabId": tab_id,
            "maxNodes": max_nodes,
        })
        tree = result.get("tree", result)
        return json.dumps({
            "status": "success",
            "message": f"无障碍树 ({len(str(tree))} 字符)",
            "tree": tree,
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_screenshot() -> str:
    """截取当前 Bridge 标签页的截图。"""
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        result = await bridge.rpc("page.screenshot", {
            "tabId": tab_id,
            "format": "png",
        })
        return json.dumps({
            "status": "success",
            "message": "截图已生成",
            "dataUrl": result.get("dataUrl", ""),
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# ── 交互操作 ────────────────────────────────────────────────────────────


async def browser_bridge_click(
    selector: str = None,
    text: str = None,
    role: str = None,
    name: str = None,
    ref: str = None,
    wait_for_navigation: bool = False,
) -> str:
    """点击页面元素。支持四种定位方式（按优先级）：

    1. ref: 来自 browser_bridge_get_tree 的元素引用（最精确）
    2. selector: CSS 选择器，如 "button.submit"
    3. text: 匹配元素文本
    4. role + name: 按 ARIA 角色和名称，如 role="button" name="搜索"

    如果点击后会触发页面跳转，设置 wait_for_navigation=True，
    工具会等待新页面加载完成后返回，返回的 whatChanged 会显示页面变化。

    Args:
        selector: CSS 选择器。
        text: 元素文本内容（模糊匹配）。
        role: ARIA 角色（button, link, textbox 等）。
        name: 元素可访问名称。
        ref: 无障碍树 ref 引用。
        wait_for_navigation: 是否等待点击后的页面跳转完成。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        if ref:
            result = await bridge.rpc("locator.clickRef", {
                "tabId": tab_id,
                "ref": ref,
                "waitForNavigation": wait_for_navigation,
            })
        else:
            locator_params = {"tabId": tab_id}
            if selector:
                locator_params["selector"] = selector
            if text:
                locator_params["text"] = text
            if role:
                locator_params["role"] = role
            if name:
                locator_params["name"] = name
            if wait_for_navigation:
                locator_params["waitForNavigation"] = True

            result = await bridge.rpc("locator.click", locator_params)

        what_changed = result.get("whatChanged")
        msg_parts = [f"已点击"]
        if selector:
            msg_parts.append(selector)
        elif text:
            msg_parts.append(f"'{text}'")
        elif ref:
            msg_parts.append(f"ref={ref}")
        if what_changed and what_changed.get("urlChanged"):
            msg_parts.append(f"，页面跳转到 {what_changed.get('toUrl', '')}")

        return json.dumps({
            "status": "success",
            "message": " ".join(msg_parts),
            "whatChanged": what_changed,
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_fill(
    selector: str = None,
    text_value: str = "",
    label: str = None,
    ref: str = None,
    role: str = None,
    name: str = None,
) -> str:
    """在输入框中填写文本。支持多种定位方式。

    Args:
        selector: CSS 选择器。
        text_value: 要填入的文本。
        label: 通过 label 文本定位输入框。
        ref: 无障碍树 ref 引用。
        role: ARIA 角色。
        name: 元素可访问名称。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        if ref:
            result = await bridge.rpc("locator.fillRef", {
                "tabId": tab_id,
                "ref": ref,
                "text": text_value,
            })
        else:
            locator_params = {
                "tabId": tab_id,
                "text": text_value,
            }
            if selector:
                locator_params["selector"] = selector
            if label:
                locator_params["label"] = label
            if role:
                locator_params["role"] = role
            if name:
                locator_params["name"] = name

            result = await bridge.rpc("locator.fill", locator_params)

        what_changed = result.get("whatChanged")
        return json.dumps({
            "status": "success",
            "message": f"已在 {selector or label or ref or '输入框'} 填入文本",
            "whatChanged": what_changed,
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_wait_for(
    selector: str = None,
    text: str = None,
    state: str = "visible",
    timeout_ms: int = 30000,
) -> str:
    """等待页面元素出现或满足指定状态。

    用于等待页面加载完成、弹窗出现、按钮变为可点击等场景。

    Args:
        selector: CSS 选择器。
        text: 等待特定文本出现。
        state: 等待状态 — "visible"（可见）, "hidden"（隐藏）, "attached"（存在于 DOM）。
        timeout_ms: 超时毫秒数（默认 30000）。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        if text:
            result = await bridge.rpc("page.waitForText", {
                "tabId": tab_id,
                "text": text,
                "timeoutMs": timeout_ms,
            })
        else:
            result = await bridge.rpc("locator.waitFor", {
                "tabId": tab_id,
                "selector": selector,
                "state": state,
                "timeoutMs": timeout_ms,
            })

        return json.dumps({
            "status": "success",
            "message": f"等待条件满足: {selector or text}",
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def browser_bridge_execute_js(script: str) -> str:
    """在当前页面执行 JavaScript 代码。

    Args:
        script: 要执行的 JavaScript 代码。
    """
    bridge = get_bridge()
    if not bridge.is_available:
        return _bridge_unavailable()

    tab_id = await _get_tab_id(bridge)
    if not tab_id:
        return json.dumps({"status": "error", "message": "请先调用 browser_bridge_start 启动会话。"})

    try:
        result = await bridge.rpc("page.executeJavaScript", {
            "tabId": tab_id,
            "script": script,
        })
        return json.dumps({
            "status": "success",
            "result": str(result.get("result", "")),
        }, ensure_ascii=False)
    except BridgeError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 工具注册表
# ---------------------------------------------------------------------------

BRIDGE_TOOLS = {
    "browser_bridge_start": browser_bridge_start,
    "browser_bridge_stop": browser_bridge_stop,
    "browser_bridge_navigate": browser_bridge_navigate,
    "browser_bridge_read_text": browser_bridge_read_text,
    "browser_bridge_get_tree": browser_bridge_get_tree,
    "browser_bridge_screenshot": browser_bridge_screenshot,
    "browser_bridge_click": browser_bridge_click,
    "browser_bridge_fill": browser_bridge_fill,
    "browser_bridge_wait_for": browser_bridge_wait_for,
    "browser_bridge_execute_js": browser_bridge_execute_js,
}
