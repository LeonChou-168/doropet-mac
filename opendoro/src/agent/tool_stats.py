"""
工具调用统计收集器。

在 LLMWorker event_handler 中埋点，记录每次工具调用的完整信息，
对话结束后汇总统计，存入数据库并显示在 UI 上。
"""
import time
import uuid
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCallRecord:
    """单次工具调用记录。"""
    tool_name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    args: dict = field(default_factory=dict)
    result_summary: str = ""
    status: str = "running"
    error_message: str = ""

    def finish(self, result: str, status: str = "success", error: str = ""):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error_message = error
        self.result_summary = result[:200] + "..." if len(result) > 200 else result


@dataclass
class ConversationStats:
    """单次对话的汇总统计。"""
    conversation_id: str
    start_time: float
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    tool_calls: list = field(default_factory=list)
    model: str = ""
    provider: str = ""

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "duration_ms": self.total_duration_ms,
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "model": self.model,
            "provider": self.provider,
        }

    def to_ui_dict(self) -> dict:
        """返回仅 UI 需要的数据（Token + 耗时）。"""
        return {
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "duration_ms": self.total_duration_ms,
        }


class ToolStatsCollector:
    """工具调用统计收集器（单次对话生命周期）。"""

    def __init__(self, model: str = "", provider: str = ""):
        self.conversation_id = str(uuid.uuid4())[:8]
        self.model = model
        self.provider = provider
        self.start_time = time.time()
        self._active_calls: dict[str, ToolCallRecord] = {}
        self._finished_calls: list[ToolCallRecord] = []
        self.total_tokens_in = 0
        self.total_tokens_out = 0

    # ── 工具调用追踪 ──

    def on_tool_call_start(self, tool_call_id: str, tool_name: str,
                           args: dict) -> ToolCallRecord:
        record = ToolCallRecord(
            tool_name=tool_name,
            start_time=time.time(),
            args=args,
        )
        self._active_calls[tool_call_id] = record
        return record

    def on_tool_call_end(self, tool_call_id: str, result: str,
                         status: str = "success", error: str = ""):
        record = self._active_calls.pop(tool_call_id, None)
        if record:
            record.finish(result, status, error)
            self._finished_calls.append(record)

    # ── Token 追踪 ──

    def add_token_usage(self, tokens_in: int, tokens_out: int):
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out

    # ── 汇总 ──

    def to_stats(self) -> ConversationStats:
        stats = ConversationStats(
            conversation_id=self.conversation_id,
            start_time=self.start_time,
            model=self.model,
            provider=self.provider,
            total_tokens_in=self.total_tokens_in,
            total_tokens_out=self.total_tokens_out,
        )
        stats.end_time = time.time()
        stats.total_duration_ms = (stats.end_time - self.start_time) * 1000
        stats.tool_calls = list(self._finished_calls)
        return stats

    # ── JSON 输出 ──

    def to_json(self) -> str:
        return json.dumps(self.to_stats().to_dict(), ensure_ascii=False)

    def to_ui_json(self) -> str:
        """返回 UI 展示所需的简洁 JSON（Token + 耗时）。"""
        return json.dumps(self.to_stats().to_ui_dict(), ensure_ascii=False)
