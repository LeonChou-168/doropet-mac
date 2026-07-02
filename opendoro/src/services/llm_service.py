"""
LLM Worker — 基于 pydantic-ai 的异步 LLM 处理线程。

使用 pydantic-ai Agent 替代原始 HTTP 调用和手动 tool calling 循环。
Agent 自动处理工具调用，通过 event_stream_handler 监控工具执行状态。

信号接口与原有 LLMWorker 完全兼容。
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal, QSettings, QMutex, QMutexLocker

from src.agent.pydantic_agent import create_doro_agent, DoroDeps
from src.agent.tools import get_filtered_tools, get_skill_tool_functions
from src.agent.prompt_builder import PromptBuilder, SystemPromptContext
from src.agent.user_message_builder import UserMessageBuilder, UserMessageContext
from src.agent.tool_stats import ToolStatsCollector
from src.core.skill_manager import SkillManager
from src.core.state_manager import StateManager, GenerationState
from src.core.memory_manager import MemoryManager
from src.core.logger import logger
from src.agent.tools_cache import clear_cache
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

    finished = pyqtSignal(str, str, list, list, str)   # content, reasoning, tool_calls, generated_images, stats_json
    chunk_received = pyqtSignal(str)               # 流式文本块
    thinking_chunk = pyqtSignal(str)               # 思考内容块
    error = pyqtSignal(str)                        # 错误信息
    expression_changed = pyqtSignal(str)           # 表情变化
    pet_attribute_changed = pyqtSignal(str, str)   # 宠物属性变化
    tool_status_changed = pyqtSignal(str)          # 工具状态文本
    tool_execution_update = pyqtSignal(str, str, str, str, str)  # name, type, status, args, result
    stopped = pyqtSignal()                         # 用户停止
    tool_confirmation_requested = pyqtSignal(str, str, object)  # msg, confirm_id, callback

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
        user_confirmation_enabled: bool = True,
        confirmation_threshold: str = "medium",
        confirmation_timeout: int = 30,
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
        self.enabled_plugins = enabled_plugins if enabled_plugins is not None else ["search", "image", "coding", "file", "expression", "bridge"]
        self.available_expressions = available_expressions if available_expressions else []
        self.capabilities = capabilities  # None = 启用全部 Capability
        self.retries = retries
        self.usage_limits = usage_limits or UsageLimits(request_limit=50)
        self.available_images = available_images or []
        self.vision_model_data = vision_model_data

        self.user_confirmation_enabled = user_confirmation_enabled
        self.confirmation_threshold = confirmation_threshold
        self.confirmation_timeout = confirmation_timeout

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

    # ----- Prompt 辅助方法 -----

    def _get_enabled_skill_descriptions(self) -> list[str]:
        """获取已启用技能的描述列表。"""
        descriptions = []
        try:
            for name, skill in self.skill_manager.skills.items():
                descriptions.append(f"{name}: {skill.description}")
        except Exception:
            pass
        return descriptions

    def _get_current_pet_attributes(self) -> dict:
        """获取当前宠物属性。
        子类或调用方可覆盖此方法以接入 PetAttributesManager。
        """
        return {}

    def _get_memory_summary(self) -> str:
        """获取用户记忆摘要。
        子类或调用方可覆盖此方法。
        """
        return ""

    def _get_conversation_summary(self) -> str:
        """获取对话压缩摘要。
        子类或调用方可覆盖此方法。
        """
        return ""

    # ----- 确认管理器辅助 -----

    def _emit_confirmation(self, msg: str, confirm_id: str, callback):
        """发送确认请求到 UI 线程（线程安全）。"""
        try:
            self.tool_confirmation_requested.emit(msg, confirm_id, callback)
        except RuntimeError:
            # Qt 信号在跨线程 emit 时偶尔会 RuntimeError，忽略
            pass

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
            clear_cache()

    # ----- pydantic-ai 核心逻辑 -----

    async def _run_pydantic(self):
        """使用 pydantic-ai Agent 运行完整对话。"""

        # 初始化统计收集器
        stats_collector = ToolStatsCollector(model=self.model, provider=self.provider_id)

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

        # ── 使用 PromptBuilder 构建增强的系统提示词 ──
        # 只在默认 Doro 人格时才使用 PromptBuilder，自定义 persona 保持原样
        _is_default_doro = (
            not system_prompt
            or "你是一只名叫 Doro" in system_prompt
            or system_prompt.startswith("You are Doro")
            or system_prompt == "You are a helpful assistant."
        )
        if _is_default_doro:
            builder = PromptBuilder()
            system_prompt = builder.build(SystemPromptContext(
                available_expressions=self.available_expressions or [],
                skill_descriptions=self._get_enabled_skill_descriptions(),
            ))

        # ── 在用户消息末尾追加动态上下文 ──
        user_ctx = UserMessageContext(
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            pet_attributes=self._get_current_pet_attributes(),
            user_memory_summary=self._get_memory_summary(),
            conversation_summary=self._get_conversation_summary(),
        )
        user_prompt = UserMessageBuilder.build(user_prompt, user_ctx)

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
            available_expressions=self.available_expressions,
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
            # 创建工具确认管理器（如果启用）
            confirm_mgr = None
            if self.user_confirmation_enabled:
                from src.agent.tool_confirmation import ToolConfirmationManager, RiskLevel
                _threshold_map = {
                    "off": RiskLevel.CRITICAL,  # 实际上不会创建
                    "low": RiskLevel.LOW,
                    "medium": RiskLevel.MEDIUM,
                    "high": RiskLevel.HIGH,
                    "critical": RiskLevel.CRITICAL,
                }
                risk_threshold = _threshold_map.get(
                    self.confirmation_threshold, RiskLevel.MEDIUM
                )
                confirm_mgr = ToolConfirmationManager(
                    confirm_callback=lambda msg, cid, cb: self._emit_confirmation(msg, cid, cb),
                    default_timeout_seconds=self.confirmation_timeout,
                    risk_threshold=risk_threshold,
                )
                logger.info(
                    f"[LLMWorker] Tool confirmation enabled: threshold={self.confirmation_threshold}, "
                    f"timeout={self.confirmation_timeout}s"
                )

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
                confirmation_manager=confirm_mgr,
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
                    tool_call_id = getattr(event, 'tool_call_id', None)
                    tool_args = getattr(part, 'args', {})
                    if hasattr(part, 'args_as_dict'):
                        tool_args = part.args_as_dict()

                    # 统计收集
                    stats_collector.on_tool_call_start(tool_call_id, tool_name, tool_args)

                    args_str = json.dumps(tool_args, ensure_ascii=False) if tool_args else "{}"
                    tool_entry = {
                        "name": tool_name,
                        "type": "tool",
                        "args": args_str,
                        "result": "",
                        "status": "running",
                        "tool_call_id": tool_call_id,
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
                    result_tool_call_id = getattr(event, 'tool_call_id', None)
                    # 统计收集
                    try:
                        result_content = event.result.model_response_str()
                    except Exception:
                        result_content = str(event.result)
                    stats_collector.on_tool_call_end(
                        result_tool_call_id or "",
                        result_content,
                        status="success",
                    )
                    # 优先用 tool_call_id 精确匹配，fallback 到找第一个 running 的
                    matched_entry = None
                    if result_tool_call_id:
                        for entry in reversed(self.tool_calls_accumulated):
                            if entry.get("tool_call_id") == result_tool_call_id:
                                matched_entry = entry
                                break
                    if matched_entry is None:
                        for entry in reversed(self.tool_calls_accumulated):
                            if entry.get("status") == "running":
                                matched_entry = entry
                                break
                    if matched_entry:
                        try:
                            result_content = event.result.model_response_str()
                        except Exception:
                            result_content = str(event.result)
                        matched_entry["result"] = result_content
                        matched_entry["status"] = "success"
                        self.tool_execution_update.emit(
                            matched_entry["name"], "tool", "success", matched_entry["args"], result_content
                        )

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

            # 获取最终输出 — 优先使用流式累积的完整内容
            final_output = full_content or (
                run_result.output if hasattr(run_result, 'output') else ""
            )

            # 思考内容累积
            if current_reasoning:
                self.reasoning_accumulated = current_reasoning

            # Token 用量统计
            try:
                usage = getattr(run_result, 'usage', None)
                if usage:
                    stats_collector.add_token_usage(
                        getattr(usage, 'request_tokens', 0) or 0,
                        getattr(usage, 'response_tokens', 0) or 0,
                    )
            except Exception:
                pass

            # 完成 — 附带统计信息
            logger.info(f"[LLMWorker] Finished. Content length: {len(full_content) or len(final_output or '')}")
            stats_json = stats_collector.to_ui_json()
            self.finished.emit(
                final_output or full_content,
                self.reasoning_accumulated,
                self.tool_calls_accumulated,
                self.generated_images,
                stats_json,
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
                    self.generated_images,
                    stats_collector.to_ui_json(),
                )
            else:
                self.finished.emit(
                    f"抱歉，我在处理时遇到了一些困难: {e}\n\n请稍后重试或换个问法。",
                    "",
                    self.tool_calls_accumulated,
                    self.generated_images,
                    "{}",
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
                    self.generated_images,
                    stats_collector.to_ui_json(),
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
            from src.agent.tools import generate_image

            result = asyncio.run(generate_image(prompt=self.prompt))
            data = json.loads(result)
            if data.get("status") == "success":
                self.finished.emit(result)
            else:
                self.error.emit(data.get("message", "Image generation failed"))
        except Exception as e:
            logger.error(f"[ImageGenerationWorker] Error: {e}")
            self.error.emit(str(e))
