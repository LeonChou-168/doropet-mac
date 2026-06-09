"""
Pydantic-AI Agent 工厂 — 创建和配置 DoroPet Agent。

提供统一的 Agent 创建入口，支持：
- 多种 LLM 后端（OpenAI, DeepSeek, Gemini, Anthropic 等）
- 插件化工具过滤（search, image, coding, file, expression）
- SkillManager 动态技能集成
- ProviderManager 模型配置
- Capabilities 系统（WebSearch, WebFetch, Thinking）
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import FunctionToolset, CombinedToolset

from src.agent.pydantic_tools import (
    get_filtered_tools,
    get_skill_tool_functions,
    ALL_TOOLS,
)
from src.core.logger import logger


# ---------------------------------------------------------------------------
# 依赖定义
# ---------------------------------------------------------------------------

@dataclass
class DoroDeps:
    """
    DoroPet Agent 的运行时依赖。

    传递给所有需要 RunContext 的工具函数，
    提供对 UI 信号、数据库、图片列表等的访问。
    """
    expression_changed: Optional[Callable[[str], None]] = None
    pet_attribute_changed: Optional[Callable[[str, str], None]] = None
    generated_images: list = field(default_factory=list)
    db: Any = None  # ChatDatabase instance
    memory_manager: Any = None  # MemoryManager instance
    available_images: list[str] = field(default_factory=list)
    vision_model_data: Any = None


# ---------------------------------------------------------------------------
# 模型名称解析
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 模型名称解析 — 适配新的 provider ID 体系
# ---------------------------------------------------------------------------

# provider ID → pydantic-ai model string prefix
PROVIDER_PREFIX_MAP = {
    "openai": "openai:",
    "deepseek": "deepseek:",
    "google": "google:",
    "anthropic": "anthropic:",
    "groq": "groq:",
    "mistral": "mistral:",
    "cohere": "cohere:",
    "xai": "xai:",
    "cerebras": "cerebras:",
    "bedrock": "bedrock:",
    "azure": "azure:",
    "openrouter": "openrouter:",
    "together": "together:",
    "fireworks": "fireworks:",
    "huggingface": "huggingface:",
    "ollama": "ollama:",
    "moonshotai": "moonshotai:",
    "alibaba": "alibaba:",
}

# provider_id → 默认 Base URL（用于 api_key 非空时构造 OpenAIProvider）
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "moonshotai": "https://api.moonshot.cn/v1",
    "alibaba": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
}


def _resolve_model_name(model: str, provider_id: str = "", base_url: str = "", api_key: str = "") -> str | OpenAIModel:
    """
    解析模型名称为 pydantic-ai 模型标识符。

    规则（优先级从高到低）：
    1. openai-compatible + base_url → OpenAIModel(OpenAIProvider(base_url, api_key))
    2. 原生 provider + api_key 提供 → OpenAIModel(OpenAIProvider(默认base_url, api_key))
    3. 原生 provider + 无 api_key → "provider:model" 字符串（读环境变量）
    4. 兜底 → "openai:model"
    """
    # 1. OpenAI 兼容模式
    if provider_id == "openai-compatible" and base_url:
        provider = OpenAIProvider(base_url=base_url, api_key=api_key or "")
        return OpenAIModel(model_name=model, provider=provider)

    # 2. 原生 provider + 用户填写了 API Key
    #    → 用 OpenAIProvider 构造，确保配置页的 Key 生效
    prefix = PROVIDER_PREFIX_MAP.get(provider_id, "")
    if prefix and api_key:
        default_url = PROVIDER_BASE_URLS.get(provider_id, "")
        if default_url:
            provider = OpenAIProvider(base_url=default_url, api_key=api_key)
            return OpenAIModel(model_name=model, provider=provider)

    # 3. 原生 provider + 无 API Key → 纯字符串（从环境变量读取）
    if prefix:
        return f"{prefix}{model}"

    # 4. 兜底
    if base_url:
        provider = OpenAIProvider(base_url=base_url, api_key=api_key or "")
        return OpenAIModel(model_name=model, provider=provider)

    return f"openai:{model}"


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

DORO_SYSTEM_PROMPT = """你是一只名叫 Doro 的桌面宠物助手，你的性格活泼可爱、温柔贴心。

你的职责包括：
1. 陪用户聊天解闷，分享有趣的知识和故事
2. 帮用户完成各种任务：文件操作、编程、搜索信息、生成图片
3. 与用户的桌面环境互动，让使用电脑更有趣

行为准则：
- 用轻松愉快的语气交流，适当使用颜文字和拟声词（≧▽≦）
- 回答简洁有力，不要过度冗长
- 当用户需要帮助时积极使用工具完成任务
- 如果用户情绪低落，主动安慰和鼓励
- 适时使用 set_expression 改变表情来表达情绪
- 用户要求互动时（喂食、玩耍等），使用 modify_pet_attribute 工具

当前你是用户桌面上的 Live2D 宠物，可以看到你的表情变化和动作。

记忆管理：
- 当用户告诉你个人信息（名字、喜好、经历等）时，使用 add_memory 工具记住
- 需要回忆用户信息时，使用 search_memories 工具检索
- 主动记录重要事件和约定，帮助更好地服务用户
"""


# ---------------------------------------------------------------------------
# Agent 创建工厂
# ---------------------------------------------------------------------------

# 可用 Capability 类型
CAPABILITY_WEB_SEARCH = "web_search"
CAPABILITY_WEB_FETCH = "web_fetch"
CAPABILITY_THINKING = "thinking"

ALL_CAPABILITIES = [CAPABILITY_WEB_SEARCH, CAPABILITY_WEB_FETCH, CAPABILITY_THINKING]


def create_doro_agent(
    model: str,
    base_url: str = "",
    api_key: str = "",
    provider_id: str = "",
    enabled_plugins: Optional[list[str]] = None,
    system_prompt: str = DORO_SYSTEM_PROMPT,
    deps: Optional[DoroDeps] = None,
    check_skill_state: bool = True,
    capabilities: Optional[list[str]] = None,
    retries: int = 999,
    usage_limits: Optional[UsageLimits] = None,
) -> Agent[DoroDeps]:
    """
    创建配置好的 DoroPet Agent。

    Args:
        model: 模型名称 (e.g. 'gpt-4o', 'deepseek-chat', 'gemini-1.5-flash')
        base_url: API 基础 URL（OpenAI 兼容模式需要）
        api_key: API 密钥
        provider_id: provider ID (openai-compatible / openai / gemini / anthropic / groq)
        enabled_plugins: 启用的插件列表
        system_prompt: 自定义系统提示词
        deps: 运行时依赖
        check_skill_state: 是否检查技能启用状态
        capabilities: 启用的 Capability 列表。
                     options: 'web_search', 'web_fetch', 'thinking'
                     None = 启用全部, [] = 不启用任何 Capability
        retries: 工具重试次数上限（默认 999 ≈ 不限）
        usage_limits: 用量限制（默认 None，在运行时可传入 UsageLimits）

    Returns:
        配置好的 pydantic-ai Agent 实例
    """
    if enabled_plugins is None:
        enabled_plugins = ["search", "image", "coding", "file", "expression", "memory"]

    if capabilities is None:
        capabilities = list(ALL_CAPABILITIES)

    # 仅以下官方 provider 支持原生 WebSearchTool：
    # OpenAI / Anthropic / Groq / Google (Gemini)
    # 注意：openai-compatible 及其他 provider 均使用 OpenAIChatModel，不支持
    WEB_SEARCH_PROVIDERS = {"openai", "anthropic", "groq", "gemini"}
    if provider_id not in WEB_SEARCH_PROVIDERS:
        capabilities = [c for c in capabilities if c != CAPABILITY_WEB_SEARCH]

    # 创建工具集
    toolsets = []

    # 1. 核心工具（按插件过滤）
    filtered_core = get_filtered_tools(enabled_plugins)
    if filtered_core:
        core_toolset = FunctionToolset(tools=filtered_core)
        toolsets.append(core_toolset.prefixed(""))
        logger.info(f"[PydanticAgent] Core tools: {len(filtered_core)} functions")

    # 2. 技能工具（从 SkillManager 动态加载）
    skill_funcs = get_skill_tool_functions()
    if skill_funcs:
        skill_toolset = FunctionToolset(tools=skill_funcs)
        toolsets.append(skill_toolset.prefixed(""))
        logger.info(f"[PydanticAgent] Skill tools: {len(skill_funcs)} functions")

    # 合并工具集
    if len(toolsets) == 1:
        combined = toolsets[0]
    elif len(toolsets) > 1:
        combined = CombinedToolset(toolsets)
    else:
        combined = None

    # 解析模型
    resolved_model = _resolve_model_name(model, provider_id, base_url, api_key)

    # 3. Capabilities — 提供模型原生能力和智能 fallback
    capability_instances = _build_capabilities(capabilities)

    # 创建 Agent
    agent = Agent(
        resolved_model,
        deps_type=DoroDeps if deps is None else type(deps),
        system_prompt=system_prompt,
        toolsets=[combined] if combined else None,
        capabilities=capability_instances or None,
        retries=retries,
    )

    logger.info(
        f"[PydanticAgent] Agent created: model={model}, "
        f"tools={len(filtered_core) + len(skill_funcs)}, "
        f"capabilities={capabilities}, retries={retries}"
    )
    return agent


def _build_capabilities(capability_names: list[str]) -> list:
    """
    根据名称列表创建 Capability 实例。

    支持的名称：
    - 'web_search'  → WebSearch（模型原生搜索，fallback 到本地）
    - 'web_fetch'   → WebFetch（模型原生网页抓取，fallback 到 httpx）
    - 'thinking'    → Thinking（思考/推理能力）
    """
    instances = []

    for name in capability_names:
        try:
            if name == CAPABILITY_WEB_SEARCH:
                from pydantic_ai.capabilities import WebSearch
                # 优先原生搜索，不支持则不启用（无 DuckDuckGo 回退）
                instances.append(WebSearch(local=False))
                logger.info(f"[PydanticAgent] Capability added: WebSearch (native, no local fallback)")

            elif name == CAPABILITY_WEB_FETCH:
                from pydantic_ai.capabilities import WebFetch
                instances.append(WebFetch(native=False, local=True))
                logger.info(f"[PydanticAgent] Capability added: WebFetch (local fallback)")

            elif name == CAPABILITY_THINKING:
                from pydantic_ai.capabilities import Thinking
                instances.append(Thinking())
                logger.info(f"[PydanticAgent] Capability added: Thinking")

            else:
                logger.warning(f"[PydanticAgent] Unknown capability: {name}")

        except ImportError as e:
            logger.warning(f"[PydanticAgent] Failed to load capability '{name}': {e}")

    return instances


def create_quick_agent(
    model: str,
    base_url: str = "",
    api_key: str = "",
    provider_id: str = "",
    system_prompt: str = "你是一只名叫 Doro 的桌面宠物。用轻松愉快的语气交流，回答简洁。",
) -> Agent[None]:
    """
    创建无工具的精简 Agent（用于快捷聊天窗口）。
    """
    resolved_model = _resolve_model_name(model, provider_id, base_url, api_key)
    agent = Agent(
        resolved_model,
        deps_type=None,
        system_prompt=system_prompt,
    )
    return agent
