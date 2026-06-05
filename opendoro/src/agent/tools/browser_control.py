"""
AI 浏览器操控模块。

基于 Playwright 的浏览器管理器，提供打开/导航/点击/输入/截图/获取内容/执行JS/关闭等操作。
所有工具函数返回 JSON 字符串，兼容 Doro 的现有工具模式。

浏览器运行在独立的事件循环线程中，不依赖 LLM 的 asyncio.run()，
因此跨对话持久化、登录态保持等行为稳定可靠。
"""

import os
import json
import threading
import asyncio
from typing import Optional

from src.core.logger import logger


# ---------------------------------------------------------------------------
# 截图保存目录
# ---------------------------------------------------------------------------

def _get_screenshot_dir() -> str:
    """获取截图保存目录。"""
    appdata_local = os.getenv('LOCALAPPDATA')
    if appdata_local:
        save_dir = os.path.join(appdata_local, "DoroPet", "temp")
    else:
        save_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "DoroPet", "temp")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def _get_storage_state_path() -> str:
    """获取浏览器状态（cookies/localStorage）持久化文件路径。"""
    appdata_local = os.getenv('LOCALAPPDATA')
    if appdata_local:
        state_dir = os.path.join(appdata_local, "DoroPet")
    else:
        state_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "DoroPet")
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "browser_state.json")


# ---------------------------------------------------------------------------
# BrowserManager 单例 — 独立事件循环线程
# ---------------------------------------------------------------------------

class BrowserManager:
    """管理 Playwright 浏览器实例的生命周期。

    在后台线程中运行独立 asyncio 事件循环，避免 Playwright 的 CDP WebSocket
    连接随 LLM 的 ``asyncio.run()`` 切换而断开。
    """

    _instance: Optional["BrowserManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._loop: Optional[asyncio.AbstractEventLoop] = None
            cls._instance._thread: Optional[threading.Thread] = None
            cls._instance._playwright = None
            cls._instance._browser = None
            cls._instance._context = None
            cls._instance._page = None
            cls._instance._running = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        # 属性在 __new__ 中已初始化
        self._initialized = True

    # -- 专用事件循环管理 ------------------------------------------------

    def _ensure_loop(self):
        """确保浏览器专用事件循环线程已启动。"""
        if self._loop is None or (self._thread and not self._thread.is_alive()):
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="browser-event-loop")
            self._thread.start()
            logger.debug("[BrowserManager] 专用事件循环线程已启动")

    def _run_loop(self):
        """后台线程入口：永远运行事件循环。"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _run_on_loop(self, coro):
        """在浏览器专用事件循环上执行协程，返回结果。

        可从任意线程/事件循环安全调用。
        """
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return await asyncio.wrap_future(future)

    # -- 浏览器生命周期 ---------------------------------------------------

    def _get_launch_options(self) -> dict:
        """获取浏览器启动参数。"""
        return dict(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
            ],
        )

    async def _launch_browser(self):
        """在专用事件循环上启动 Playwright 和浏览器。"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        opts = self._get_launch_options()

        # 优先 Edge → Chrome → Chromium
        for channel in ("msedge", "chrome", None):
            try:
                kwargs = dict(opts)
                if channel:
                    kwargs["channel"] = channel
                self._browser = await self._playwright.chromium.launch(**kwargs)
                logger.info(f"[BrowserManager] 已启动浏览器 (channel={channel})")
                return
            except Exception:
                continue

        raise RuntimeError("无法启动任何支持的浏览器 (Edge/Chrome/Chromium)")

    async def _start_impl(self):
        """专用事件循环上的实际启动逻辑。"""
        if self._running:
            return

        await self._launch_browser()

        # 加载之前保存的登录状态
        storage_path = _get_storage_state_path()
        self._context = await self._browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            storage_state=storage_path if os.path.exists(storage_path) else None,
        )
        self._page = await self._context.new_page()
        self._running = True
        logger.info("[BrowserManager] 浏览器已就绪")

    async def start(self):
        """启动浏览器（跨事件循环安全）。"""
        await self._run_on_loop(self._start_impl())

    async def _save_state_impl(self):
        """在专用事件循环上保存登录状态。"""
        if not self._context:
            return
        try:
            state = await self._context.storage_state()
            path = _get_storage_state_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"cookies": state.get("cookies", []), "origins": state.get("origins", [])}, f)
            n = len(state.get("cookies", []))
            if n:
                logger.info(f"[BrowserManager] 已保存 {n} 条 cookies")
        except Exception as e:
            logger.error(f"[BrowserManager] 保存状态失败: {e}")

    async def save_state(self):
        """保存浏览器状态（跨事件循环安全）。"""
        await self._run_on_loop(self._save_state_impl())

    async def _close_impl(self):
        """在专用事件循环上关闭所有资源。"""
        self._running = False
        # 保存状态
        await self._save_state_impl()

        errors = []
        for name, obj in [("page", self._page), ("context", self._context),
                          ("browser", self._browser), ("playwright", self._playwright)]:
            if obj is None:
                continue
            try:
                close_fn = getattr(obj, "close" if name != "playwright" else "stop")
                await close_fn()
            except Exception as e:
                errors.append(f"{name}: {e}")
            setattr(self, f"_{name}", None)

        if errors:
            logger.warning(f"[BrowserManager] 关闭资源时部分失败: {'; '.join(errors)}")
        logger.info("[BrowserManager] 浏览器已关闭")

    async def close(self):
        """关闭浏览器（跨事件循环安全）。"""
        if not self._running:
            return
        await self._run_on_loop(self._close_impl())

    # -- 页面操作 ---------------------------------------------------------

    async def _ensure_page_impl(self) -> bool:
        """检查页面是否可用，不可用则尝试恢复。"""
        if self._page:
            try:
                await self._page.evaluate("1+1")
                return True
            except Exception:
                logger.warning("[BrowserManager] page 已失效，尝试重建")
                self._page = None
        if self._context:
            try:
                self._page = await self._context.new_page()
                logger.info("[BrowserManager] 已重建 page")
                return True
            except Exception:
                logger.warning("[BrowserManager] context 已失效，需要重启")
                self._context = None
                self._page = None
        return False

    async def _navigate_impl(self, url: str) -> str:
        """在专用事件循环上执行导航。"""
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})

        if not await self._ensure_page_impl():
            return json.dumps({"status": "error", "message": "浏览器连接已断开，请重新调用 browser_open。"})

        try:
            if not url.startswith("http"):
                url = "https://" + url
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self._page.title()
            await self._save_state_impl()
            return json.dumps({
                "status": "success",
                "message": f"已导航到 {url}",
                "title": title,
                "url": self._page.url,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"导航失败: {str(e)}"})

    async def navigate(self, url: str) -> str:
        """导航到 URL。"""
        return await self._run_on_loop(self._navigate_impl(url))

    async def _click_impl(self, selector: str) -> str:
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动。"})
        try:
            await self._page.click(selector, timeout=10000)
            return json.dumps({"status": "success", "message": f"已点击 {selector}"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"点击失败: {str(e)}"})

    async def click(self, selector: str) -> str:
        return await self._run_on_loop(self._click_impl(selector))

    async def _type_text_impl(self, selector: str, text: str) -> str:
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动。"})
        try:
            await self._page.fill(selector, text, timeout=10000)
            return json.dumps({"status": "success", "message": f"已在 {selector} 输入文本"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"输入失败: {str(e)}"})

    async def type_text(self, selector: str, text: str) -> str:
        return await self._run_on_loop(self._type_text_impl(selector, text))

    async def _screenshot_impl(self) -> str:
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动。"})
        try:
            from datetime import datetime
            save_dir = _get_screenshot_dir()
            path = os.path.join(save_dir, f"browser_screenshot_{datetime.now():%Y%m%d_%H%M%S}.png")
            await self._page.screenshot(path=path, full_page=False)
            return json.dumps({"status": "success", "message": f"截图已保存", "path": path}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"截图失败: {str(e)}"})

    async def screenshot(self) -> str:
        return await self._run_on_loop(self._screenshot_impl())

    async def _get_content_impl(self) -> str:
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动。"})
        try:
            content = await self._page.evaluate("() => document.body.innerText")
            if len(content) > 8000:
                content = content[:8000] + f"\n... (截断，共 {len(content)} 字符)"
            return json.dumps({"status": "success", "message": f"页面内容 ({len(content)} 字符)", "content": content},
                              ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"获取内容失败: {str(e)}"})

    async def get_content(self) -> str:
        return await self._run_on_loop(self._get_content_impl())

    async def _execute_js_impl(self, script: str) -> str:
        if not self._page:
            return json.dumps({"status": "error", "message": "浏览器未启动。"})
        try:
            result = await self._page.evaluate(script)
            return json.dumps({"status": "success", "result": str(result)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": f"JS 执行失败: {str(e)}"})

    async def execute_js(self, script: str) -> str:
        return await self._run_on_loop(self._execute_js_impl(script))

    @property
    def is_running(self) -> bool:
        return self._running


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def get_browser_manager() -> BrowserManager:
    """获取 BrowserManager 单例。"""
    return BrowserManager()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

async def browser_open(url: str = "") -> str:
    """打开浏览器。如果已有浏览器则复用；可选的 url 参数用于打开后导航到指定页面。

    重要规则：如果页面出现登录框/验证码/弹窗遮挡内容，立即停止操作并返回信息
    '需要用户手动登录/处理弹窗才能继续'，不要尝试自行填写账号密码或绕过验证。

    Args:
        url: 可选的初始导航 URL。
    """
    manager = get_browser_manager()
    if manager.is_running:
        if url:
            return await manager.navigate(url)
        return json.dumps({"status": "success", "message": "浏览器已在运行中。"})
    try:
        await manager.start()
        result = {"status": "success", "message": "浏览器已打开。"}
        if url:
            nav_result = await manager.navigate(url)
            nav_data = json.loads(nav_result)
            result["message"] += f" 已导航到 {url}"
            result["title"] = nav_data.get("title", "")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"打开浏览器失败: {str(e)}"})


async def browser_navigate(url: str) -> str:
    """导航到指定 URL。

    重要规则：如果页面出现登录框/验证码/弹窗遮挡内容，立即停止操作并返回信息
    '需要用户手动登录/处理弹窗才能继续'，不要尝试自行填写账号密码或绕过验证。

    Args:
        url: 要导航到的 URL。
    """
    manager = get_browser_manager()
    if not manager.is_running:
        await manager.start()
    return await manager.navigate(url)


async def browser_click(selector: str) -> str:
    """点击页面中的元素，使用 CSS 选择器。

    遇到登录/注册按钮时需谨慎——如果页面是登录状态，先用 browser_get_content 检查
    是否已登录（看页面是否显示用户头像/用户名等）。如果检测到登录页面/弹窗遮挡，
    返回信息让用户手动处理，不要自行填写。

    Args:
        selector: CSS 选择器。
    """
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})
    return await manager.click(selector)


async def browser_type(selector: str, text: str) -> str:
    """在输入框中输入文本。

    Args:
        selector: CSS 选择器。
        text: 要输入的文本。
    """
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})
    return await manager.type_text(selector, text)


async def browser_screenshot() -> str:
    """截图当前页面。"""
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})
    return await manager.screenshot()


async def browser_get_content() -> str:
    """获取当前页面的文本内容。

    导航后先调用此工具获取页面内容，检查页面是否正常加载。
    如果内容包含"登录""注册""验证"等关键词，说明需要用户手动登录才能继续操作，
    此时应返回信息让用户处理。
    """
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})
    return await manager.get_content()


async def browser_execute_js(script: str) -> str:
    """执行 JavaScript 代码。

    Args:
        script: 要执行的 JavaScript 代码。
    """
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "error", "message": "浏览器未启动，请先调用 browser_open。"})
    return await manager.execute_js(script)


async def browser_close() -> str:
    """关闭浏览器。"""
    manager = get_browser_manager()
    if not manager.is_running:
        return json.dumps({"status": "info", "message": "浏览器未在运行。"})
    await manager.close()
    return json.dumps({"status": "success", "message": "浏览器已关闭。"})


# ---------------------------------------------------------------------------
# 工具注册表
# ---------------------------------------------------------------------------

BROWSER_TOOLS = {
    "browser_open": browser_open,
    "browser_navigate": browser_navigate,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_screenshot": browser_screenshot,
    "browser_get_content": browser_get_content,
    "browser_execute_js": browser_execute_js,
    "browser_close": browser_close,
}
