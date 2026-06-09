"""
LLM Worker — 基于 pydantic-ai 的异步 LLM 处理线程。

使用 pydantic-ai Agent 替代原始 HTTP 调用和手动 tool calling 循环。
Agent 自动处理工具调用，通过 event_stream_handler 监控工具执行状态。

信号接口与原有 LLMWorker 完全兼容。
"""

import asyncio
import json
import time
from typing import Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal, QSettings, QMutex, QMutexLocker

from src.agent.pydantic_agent import create_doro_agent, DoroDeps
from src.agent.pydantic_tools import get_filtered_tools, get_skill_tool_functions
from src.core.skill_manager import SkillManager
from src.core.state_manager import StateManager, GenerationState
from src.core.memory_manager import MemoryManager
from src.core.logger import logger
from pydantic_ai import UsageLimits
from pydantic_ai.exceptions import UnexpectedModelBehavior


# ---------------------------------------------------------------------------
# OpenAI 多部分内容 → pydantic-ai UserContent 转换
# ---------------------------------------------------------------------------

def _parse_openai_content(content) -> str | list:
    """
    将 OpenAI 格式的 content 转换为 pydantic-ai 的 UserContent。

    支持：
    - 纯文本 → 返回 str
    - 多部分数组（text + image_url）→ 返回 [TextContent, ImageUrl, ...]
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)

    from pydantic_ai.messages import TextContent, ImageUrl

    parts: list = []
    for item in content:
        item_type = item.get("type", "")
        if item_type == "text":
            parts.append(TextContent(content=item.get("text", "")))
        elif item_type == "image_url":
            url = item.get("image_url", {}).get("url", "")
            parts.append(ImageUrl(url=url))

    # 如果只有文本，返回纯字符串以简化处理
    if len(parts) == 1 and isinstance(parts[0], TextContent):
        return parts[0].content

    return parts if parts else ""


# ---------------------------------------------------------------------------
# LLMWorker — 使用 pydantic-ai
# ---------------------------------------------------------------------------

class LLMWorker(QThread):
    """基于 pydantic-ai 的 LLM 工作线程。

    信号与原有版本完全兼容。
    """

    finished = pyqtSignal(str, str, list, list)   # content, reasoning, tool_calls, generated_images
    chunk_received = pyqtSignal(str)               # 流式文本块
    thinking_chunk = pyqtSignal(str)               # 思考内容块
    error = pyqtSignal(str)                        # 错误信息
    expression_changed = pyqtSignal(str)           # 表情变化
    pet_attribute_changed = pyqtSignal(str, str)   # 宠物属性变化
    tool_status_changed = pyqtSignal(str)          # 工具状态文本
    tool_execution_update = pyqtSignal(str, str, str, str, str)  # name, type, status, args, result
    stopped = pyqtSignal()                         # 用户停止

    def __init__(
        self,
        api_key: str,
        base_url: str,
        messages: list,
        model: str = "gpt-3.5-turbo",
        db: Any = None,
        is_thinking: int = 0,
        enabled_plugins: list = None,
        available_expressions: list = None,
        skip_tools_and_max_tokens: bool = False,
        provider_id: str = "",
        capabilities: Optional[list[str]] = None,
        retries: int = 999,
        usage_limits: Optional[UsageLimits] = None,
        available_images: Optional[list[str]] = None,
        vision_model_data: Any = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.messages = list(messages)
        self.model = model
        self.db = db
        self.is_thinking_model = bool(is_thinking)
        self.skip_tools_and_max_tokens = skip_tools_and_max_tokens
        self.provider_id = provider_id
        self.enabled_plugins = enabled_plugins if enabled_plugins is not None else ["search", "image", "coding", "file", "expression"]
        self.available_expressions = available_expressions if available_expressions else []
        self.capabilities = capabilities  # None = 启用全部 Capability
        self.retries = retries
        self.usage_limits = usage_limits or UsageLimits(request_limit=50)
        self.available_images = available_images or []
        self.vision_model_data = vision_model_data

        self.generated_images: list = []
        self.reasoning_accumulated = ""
        self.tool_calls_accumulated: list = []

        self.skill_manager = SkillManager()

        self._is_stopped = False
        self._stop_mutex = QMutex()

        self.state_manager = StateManager.get_instance()

        logger.info(f"[LLMWorker] Initialized (pydantic-ai): model={model}, plugins={self.enabled_plugins}")

    # ----- 停止控制 -----

    def stop(self):
        with QMutexLocker(self._stop_mutex):
            if self._is_stopped:
                return
            self._is_stopped = True
            logger.info("[LLMWorker] Stop requested")

    def is_stopped(self) -> bool:
        with QMutexLocker(self._stop_mutex):
            return self._is_stopped

    # ----- 主运行入口 -----

    def run(self):
        """QThread 入口 — 在后台线程中运行异步事件循环。"""
        try:
            asyncio.run(self._run_pydantic())
        except Exception as e:
            logger.error(f"[LLMWorker] Critical Error: {e}")
            if not self.is_stopped():
                self.error.emit(str(e))
        finally:
            if self.is_stopped():
                try:
                    self.state_manager.set_generation_state(GenerationState.STOPPED)
                    self.stopped.emit()
                except RuntimeError:
                    pass
            else:
                try:
                    self.state_manager.set_generation_state(GenerationState.COMPLETED)
                except RuntimeError:
                    pass

    # ----- pydantic-ai 核心逻辑 -----

    async def _run_pydantic(self):
        """使用 pydantic-ai Agent 运行完整对话。"""

        # 1. 提取系统提示词、用户输入和对话历史
        system_prompt = ""
        history_messages = []
        user_prompt = ""

        for msg in self.messages:
            role = msg.get("role", "")
            if role == "system":
                system_prompt = msg.get("content", "")
            elif role in ("user", "assistant", "tool"):
                history_messages.append(msg)

        # 最后一条用户消息作为 user_prompt
        for msg in reversed(history_messages):
            if msg.get("role") == "user":
                user_prompt = _parse_openai_content(msg.get("content", ""))
                break

        if not system_prompt:
            system_prompt = "You are Doro, a helpful desktop pet assistant."

        logger.info(f"[LLMWorker] Running pydantic-ai: model={self.model}, messages={len(history_messages)}")

        # 2. 构建消息历史（pydantic-ai 格式）
        # 注意：最后一条用户消息作为 user_prompt 单独传入，不放在 message_history 中
        from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart, ToolReturnPart, ToolCallPart

        message_history: list[ModelMessage] = []

        # 系统提示
        message_history.append(
            ModelRequest(parts=[UserPromptPart(content=system_prompt)])
        )

        # 找到最后一条 user 消息的索引
        last_user_idx = -1
        for i, msg in enumerate(history_messages):
            if msg.get("role") == "user":
                last_user_idx = i

        # 构建历史（排除最后一条用户消息）
        for i, msg in enumerate(history_messages):
            if i == last_user_idx:
                continue  # 这条作为 user_prompt 传入

            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and content:
                message_history.append(
                    ModelRequest(parts=[UserPromptPart(content=_parse_openai_content(content))])
                )
            elif role == "assistant":
                parts = []
                if content:
                    parts.append(TextPart(content=str(content)))
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}
                    parts.append(ToolCallPart(
                        tool_name=func.get("name", ""),
                        args=args,
                        tool_call_id=tc.get("id", "")
                    ))
                message_history.append(ModelResponse(parts=parts))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                tool_content = str(content)
                message_history.append(
                    ModelRequest(parts=[
                        ToolReturnPart(
                            tool_name="unknown",
                            content=tool_content,
                            tool_call_id=tool_call_id
                        )
                    ])
                )

        # 3. 创建 Agent
        deps = DoroDeps(
            generated_images=self.generated_images,
            db=self.db,
            memory_manager=MemoryManager(self.db) if self.db else None,
            available_images=self.available_images,
            vision_model_data=self.vision_model_data,
        )

        # 跳过工具时使用精简 Agent
        if self.skip_tools_and_max_tokens:
            from src.agent.pydantic_agent import create_quick_agent
            agent = create_quick_agent(
                model=self.model,
                base_url=self.base_url,
                api_key=self.api_key,
                system_prompt=system_prompt,
            )
        else:
            agent = create_doro_agent(
                model=self.model,
                base_url=self.base_url,
                api_key=self.api_key,
                provider_id=self.provider_id,
                enabled_plugins=self.enabled_plugins,
                system_prompt=system_prompt,
                deps=deps,
                capabilities=self.capabilities,
                retries=self.retries,
            )

        # 4. 流式运行 — 使用 event_stream_handler 实时捕获工具调用和思考
        self.state_manager.set_generation_state(GenerationState.STREAMING)

        full_content = ""
        current_reasoning = ""

        async def event_handler(ctx, event_stream):
            """实时处理 Agent 运行中的事件流。"""
            nonlocal full_content, current_reasoning

            from pydantic_ai.messages import (
                TextPartDelta, ThinkingPartDelta,
                FunctionToolCallEvent, FunctionToolResultEvent, PartStartEvent,
            )

            async for event in event_stream:
                if self.is_stopped():
                    break

                # 按事件类型分派 — 避免思考内容同时进入正文
                if hasattr(event, 'delta') and isinstance(event.delta, TextPartDelta):
                    content_delta = event.delta.content_delta
                    if content_delta:
                        full_content += content_delta
                        self.chunk_received.emit(content_delta)

                elif hasattr(event, 'delta') and isinstance(event.delta, ThinkingPartDelta):
                    thinking_delta = event.delta.content_delta
                    if thinking_delta:
                        current_reasoning += thinking_delta
                        self.thinking_chunk.emit(thinking_delta)

                # 工具调用开始
                if isinstance(event, PartStartEvent):
                    pass  # 可以用来通知前端"工具调用开始"

                if isinstance(event, FunctionToolCallEvent):
                    part = event.part
                    tool_name = getattr(part, 'tool_name', 'unknown')
                    tool_args = getattr(part, 'args', {})
                    if hasattr(part, 'args_as_dict'):
                        tool_args = part.args_as_dict()

                    args_str = json.dumps(tool_args, ensure_ascii=False) if tool_args else "{}"
                    tool_entry = {
                        "name": tool_name,
                        "type": "tool",
                        "args": args_str,
                        "result": "",
                        "status": "running"
                    }
                    self.tool_calls_accumulated.append(tool_entry)

                    self.tool_status_changed.emit(f"正在调用工具: {tool_name}")
                    self.tool_execution_update.emit(tool_name, "tool", "running", args_str, "")

                    # 表情变化
                    if tool_name == "set_expression":
                        if isinstance(tool_args, dict):
                            expr_name = tool_args.get("expression_name", "")
                            if expr_name:
                                self.expression_changed.emit(expr_name)

                    # 宠物属性变化
                    if tool_name == "modify_pet_attribute":
                        if isinstance(tool_args, dict):
                            interaction = tool_args.get("interaction", "")
                            intensity = tool_args.get("intensity", "moderate")
                            attribute = tool_args.get("attribute", "")
                            action = tool_args.get("action", "")
                            if interaction:
                                self.pet_attribute_changed.emit(interaction, intensity)
                            elif attribute and action:
                                self.pet_attribute_changed.emit(action, intensity)

                # 工具调用结果返回
                if isinstance(event, FunctionToolResultEvent):
                    for entry in reversed(self.tool_calls_accumulated):
                        if entry.get("status") == "running":
                            try:
                                result_content = event.result.model_response_str()
                            except Exception:
                                result_content = str(event.result)
                            entry["result"] = result_content
                            entry["status"] = "success"
                            self.tool_execution_update.emit(
                                entry["name"], "tool", "success", entry["args"], result_content
                            )
                            break

        try:
            run_result = await agent.run(
                user_prompt,
                message_history=message_history,
                deps=deps,
                event_stream_handler=event_handler,
                usage_limits=self.usage_limits,
            )

            if self.is_stopped():
                return

            # 获取最终输出
            final_output = run_result.output if hasattr(run_result, 'output') else full_content

            # 思考内容累积
            if current_reasoning:
                self.reasoning_accumulated = current_reasoning

            # 完成
            logger.info(f"[LLMWorker] Finished. Content length: {len(full_content) or len(final_output or '')}")
            self.finished.emit(
                final_output or full_content,
                self.reasoning_accumulated,
                self.tool_calls_accumulated,
                self.generated_images
            )

        except asyncio.CancelledError:
            if not self.is_stopped():
                self.error.emit("Request cancelled")
        except UnexpectedModelBehavior as e:
            # 工具重试耗尽等 — 优雅返回已有内容而非弹窗报错
            if self.is_stopped():
                return
            logger.warning(f"[LLMWorker] Unexpected model behavior (graceful): {e}")
            if full_content.strip():
                self.finished.emit(
                    full_content + f"\n\n(处理过程中遇到了一些问题，但以下是已获取的信息)",
                    current_reasoning,
                    self.tool_calls_accumulated,
                    self.generated_images
                )
            else:
                self.finished.emit(
                    f"抱歉，我在处理时遇到了一些困难: {e}\n\n请稍后重试或换个问法。",
                    "",
                    self.tool_calls_accumulated,
                    self.generated_images
                )
        except Exception as e:
            if self.is_stopped():
                return
            logger.error(f"[LLMWorker] pydantic-ai error: {e}")
            # 有多余的内容时礼貌地返回
            if full_content.strip():
                self.finished.emit(
                    full_content + f"\n\n(遇到错误，但以下是已获取的信息)",
                    current_reasoning,
                    self.tool_calls_accumulated,
                    self.generated_images
                )
            else:
                self.error.emit(str(e))


# ---------------------------------------------------------------------------
# ImageGenerationWorker — 保持原有实现
# ---------------------------------------------------------------------------

class ImageGenerationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, prompt):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            from src.agent.pydantic_tools import generate_image

            result = asyncio.run(generate_image(prompt=self.prompt))
            data = json.loads(result)
            if data.get("status") == "success":
                self.finished.emit(result)
            else:
                self.error.emit(data.get("message", "Image generation failed"))
        except Exception as e:
            logger.error(f"[ImageGenerationWorker] Error: {e}")
            self.error.emit(str(e))
