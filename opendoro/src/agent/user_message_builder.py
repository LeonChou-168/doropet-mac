"""
UserMessageBuilder — 在用户消息末尾追加动态上下文。

动态上下文包含（每次对话可能变化）：
  - 当前时间
  - 宠物属性状态
  - 用户记忆摘要
  - 对话压缩摘要
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserMessageContext:
    """每轮对话的动态上下文。"""
    current_time: str = ""                              # 当前时间
    pet_attributes: dict = field(default_factory=dict)  # {"hunger": 80, "mood": 70, ...}
    user_memory_summary: str = ""                       # 用户记忆摘要
    conversation_summary: str = ""                      # 对话压缩摘要


class UserMessageBuilder:
    """构建带有动态上下文的用户消息。

    不修改原始 user_prompt，而是在末尾追加上下文信息。
    """

    @staticmethod
    def build(original_message: str, context: UserMessageContext) -> str:
        """在用户原始消息末尾追加系统上下文信息。

        Args:
            original_message: 用户原始输入
            context: 当前运行时上下文

        Returns:
            拼接后的完整用户消息
        """
        suffix_parts = []

        # 1. 当前时间
        time_str = context.current_time or datetime.now().strftime("%Y-%m-%d %H:%M")
        suffix_parts.append(f"（当前时间: {time_str}）")

        # 2. 宠物属性
        if context.pet_attributes:
            attr_text = UserMessageBuilder._format_attributes(context.pet_attributes)
            if attr_text:
                suffix_parts.append(f"（宠物状态: {attr_text}）")

        # 3. 用户记忆摘要
        if context.user_memory_summary:
            suffix_parts.append(f"（关于用户的已知信息: {context.user_memory_summary}）")

        # 4. 对话摘要（来自上下文压缩）
        if context.conversation_summary:
            suffix_parts.append(f"（之前的对话摘要: {context.conversation_summary}）")

        if not suffix_parts:
            return original_message

        return original_message + "\n\n" + "\n".join(suffix_parts)

    @staticmethod
    def _format_attributes(attrs: dict) -> str:
        """格式化宠物属性为自然语言字符串。

        属性低于阈值时附加提醒信息。
        """
        names = {"hunger": "饱食度", "mood": "心情值", "cleanliness": "清洁度", "energy": "能量值"}
        alerts = {
            "hunger": (30, "饿了，需要喂食"),
            "mood": (30, "心情低落，需要互动"),
            "cleanliness": (30, "需要清洁"),
            "energy": (20, "能量不足，需要休息"),
        }
        parts = []
        for key, value in attrs.items():
            name = names.get(key, key)
            threshold, alert_msg = alerts.get(key, (None, None))
            if threshold is not None and value < threshold:
                parts.append(f"{name}{value}/100（{alert_msg}）")
            else:
                parts.append(f"{name}{value}/100")

        return "，".join(parts) if parts else ""
