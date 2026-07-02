"""
工具函数结果缓存。

支持两级缓存：
  - L1: 内存 LRU 缓存（会话生命周期）
  - L2: 数据库持久化缓存（跨会话，TODO）

提供失效 API，供写操作主动清除读缓存。
"""

import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable
from collections import OrderedDict

from src.core.logger import logger


def _is_run_context(obj: Any) -> bool:
    """延迟导入 RunContext 做 instanceof 检查，避免循环依赖。"""
    try:
        from pydantic_ai.tools import RunContext
        return isinstance(obj, RunContext)
    except ImportError:
        return False


class ToolCache:
    """工具函数结果缓存管理器，基于 OrderedDict 的 LRU 淘汰策略。"""

    def __init__(self, max_size: int = 200):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.max_size = max_size

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键，包含模块限定名避免同名函数冲突。"""
        raw = json.dumps(
            {"f": func_name, "a": args, "k": kwargs},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, key: str, ttl: float) -> Any | None:
        """获取缓存值，过期返回 None。"""
        if key not in self._cache:
            return None
        timestamp, value = self._cache[key]
        if time.monotonic() - timestamp > ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)  # LRU: 移到末尾
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # 淘汰最旧
        self._cache[key] = (time.monotonic(), value)

    def invalidate_by_prefix(self, func_prefix: str) -> int:
        """按函数名前缀批量失效缓存。

        例如: invalidate_by_prefix("read_file") 清除所有 read_file 缓存。
        返回清除的条目数。
        """
        to_remove = [
            k for k in self._cache
            if self._cache[k][1] is not None and func_prefix in k
        ]
        # 重建 key 检查: 由于 key 是 md5 hash，无法直接匹配；
        # 改为在 value 中存储 metadata，或改为在 cache 中用前缀索引。
        # 为简单起见，直接全部清除时传到缓存。
        return 0  # 当前不支持按前缀失效（md5 哈希无法逆匹配）

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


# 全局单例
_cache = ToolCache(max_size=200)


def cached(ttl_seconds: float = 300):
    """工具函数缓存装饰器。

    Args:
        ttl_seconds: 缓存过期时间（秒）。0 表示永不过期（仅对幂等操作）。

    自动过滤 ctx (RunContext) 参数，避免不可序列化对象影响缓存键。
    """

    def deco(func: Callable) -> Callable:
        # 检查 func 是否包含名为 ctx 的参数（通常是第一个）
        _has_ctx_param = "ctx" in func.__code__.co_varnames[: func.__code__.co_argcount]
        _qualname = f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 过滤 ctx 参数（kwargs 按名字过滤，args 按 isinstance 过滤）
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "ctx"}
            if _has_ctx_param:
                cache_args = tuple(a for a in args if not _is_run_context(a))
            else:
                cache_args = args

            key = _cache._make_key(_qualname, cache_args, cache_kwargs)

            effective_ttl = float("inf") if ttl_seconds <= 0 else ttl_seconds
            cached_value = _cache.get(key, effective_ttl)

            if cached_value is not None:
                logger.debug(f"[ToolCache] HIT  {_qualname}({cache_kwargs})")
                return cached_value

            logger.debug(f"[ToolCache] MISS {_qualname}({cache_kwargs})")
            result = await func(*args, **kwargs)
            _cache.set(key, result)
            return result

        return wrapper

    return deco


def clear_cache() -> None:
    """清空所有工具缓存。"""
    _cache.clear()
    logger.info("[ToolCache] Cache cleared")


def invalidate_read_cache(file_path: str) -> None:
    """写操作后主动失效对应 read_file 缓存。

    由于缓存键是 md5 哈希无法逆匹配，当前实现清空全部缓存。
    后续可优化为在缓存值中记录文件路径元数据。
    """
    _cache.clear()
    logger.debug(f"[ToolCache] Invalidated all cache after writing to {file_path}")
