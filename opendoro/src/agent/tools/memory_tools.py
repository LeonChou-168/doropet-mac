"""记忆管理工具 — 让 LLM 主动管理用户记忆。"""

import json
from typing import Any

from pydantic_ai.tools import RunContext


async def search_memories(ctx: RunContext[Any], query: str, top_n: int = 5) -> str:
    """搜索用户的长期记忆。

    搜索会智能匹配你查询中的关键词片段。例如搜索"喜欢什么饮料"也会匹配到"喜欢喝咖啡"。
    如果第一次搜索没有结果，请换一组关键词再试一次（比如用户说"我住aaa"，搜"住在"或"aaa"都能找到）。

    Args:
        query: 搜索关键词，尽量包含核心信息词（不包含的我你他吗呢等虚词也能搜到）
        top_n: 最多返回多少条记忆（默认 5 条）
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        results = mm.search_by_keywords(query, top_n)
        if not results:
            return '{"status":"ok","memories":[],"message":"未找到相关记忆"}'
        return json.dumps({"status": "ok", "memories": results}, ensure_ascii=False)
    except Exception as e:
        return '{"status":"error","message":"搜索记忆失败: '+str(e)+'"}'


async def add_memory(ctx: RunContext[Any], category: str, content: str, importance: int = 3) -> str:
    """记住一条关于用户的信息。当用户分享个人信息（名字、喜好、经历、约定等）时使用此工具主动记住。

    Args:
        category: 记忆类别（fact=事实信息, preference=偏好喜好, event=重要事件, emotion=情绪状态）
        content: 要记住的内容，简洁完整地描述
        importance: 重要程度 1-5（5=最重要，一般重要请用 3）
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        mm.save_to_long_term_memory(category, content, importance, [], content)
        return '{"status":"ok","message":"已记住"}'
    except Exception as e:
        return '{"status":"error","message":"保存记忆失败: '+str(e)+'"}'


async def delete_memory(ctx: RunContext[Any], memory_id: int) -> str:
    """删除一条指定的记忆。

    Args:
        memory_id: 要删除的记忆 ID
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        mm.delete_memory(memory_id)
        return '{"status":"ok","message":"记忆已删除"}'
    except Exception as e:
        return '{"status":"error","message":"删除记忆失败: '+str(e)+'"}'
