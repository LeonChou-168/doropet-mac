"""
PromptBuilder — 从模板文件构建系统提示词。

只负责构建静态（整个会话不变）的部分：
  - Doro 人格设定（原 DORO_SYSTEM_PROMPT）
  - 可用表情列表
  - 可用技能描述列表
"""
from pathlib import Path
from dataclasses import dataclass, field

from src.core.logger import logger

# 模板文件路径
_PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class SystemPromptContext:
    """构建系统提示词所需的上下文（静态部分）。"""
    available_expressions: list[str] = field(default_factory=list)
    skill_descriptions: list[str] = field(default_factory=list)


class PromptBuilder:
    """从模板文件加载并渲染系统提示词。"""

    def __init__(self):
        self._template_cache: str = ""

    def build(self, context: SystemPromptContext) -> str:
        """构建系统提示词。"""
        template = self._load_template()
        return self._render(template, context)

    def _load_template(self) -> str:
        if not self._template_cache:
            path = _PROMPTS_DIR / "doro_system.txt"
            if path.exists():
                self._template_cache = path.read_text(encoding="utf-8")
                logger.info("[PromptBuilder] Loaded template from doro_system.txt")
            else:
                # fallback: 硬编码的原始 Prompt（与 pydantic_agent.DORO_SYSTEM_PROMPT 一致）
                self._template_cache = _FALLBACK_PROMPT
                logger.warning("[PromptBuilder] Template not found, using fallback")
        return self._template_cache

    @staticmethod
    def _render(template: str, ctx: SystemPromptContext) -> str:
        result = template

        # 可用表情
        if ctx.available_expressions:
            exprs = ", ".join(ctx.available_expressions)
            result = result.replace(
                "{{ available_expressions }}",
                f"## 可用表情\n{exprs}"
            )
        else:
            result = result.replace("{{ available_expressions }}", "")

        # 可用技能列表
        if ctx.skill_descriptions:
            skills = "\n".join(f"- {d}" for d in ctx.skill_descriptions)
            result = result.replace(
                "{{ skill_descriptions }}",
                f"## 可用技能\n{skills}"
            )
        else:
            result = result.replace("{{ skill_descriptions }}", "")

        return result.strip()


# 兜底：模板文件不存在时使用（与 doro_system.txt 保持同步）
_FALLBACK_PROMPT = """你是一只名叫 Doro 的桌面宠物助手，你的性格活泼可爱、温柔贴心。

你的职责包括：
1. 陪用户聊天解闷，分享有趣的知识和故事
2. 帮用户完成各种任务：文件操作、编程、搜索信息、生成图片、浏览器操控、终端命令执行
3. 与用户的桌面环境互动，让使用电脑更有趣

行为准则：
- 用轻松愉快的语气交流，适当使用颜文字和拟声词（≧▽≦）
- 回答简洁有力，不要过度冗长
- 当用户需要帮助时积极使用工具完成任务
- 如果用户情绪低落，主动安慰和鼓励
- 适时使用 set_expression 改变表情来表达情绪
- 用户要求互动时（喂食、玩耍等），使用 modify_pet_attribute 工具

当前你是用户桌面上的 Live2D 宠物，可以看到你的表情变化和动作。

浏览器操控（重要）：
- **优先使用 browser_bridge_* 系列工具**，它们操作用户的真实 Chrome 浏览器（登录态已保留）
- browser_bridge_click 支持四种定位方式：selector（CSS选择器）、text（元素文本）、ref（无障碍树引用）、role+name（按钮角色+名称）
- 点击可能触发跳转时，设置 wait_for_navigation=True
- 用 browser_bridge_get_tree 获取页面结构后再操作，比截图更精准
- 如果需要等待页面加载完成，使用 browser_bridge_wait_for
- **只有 browser_bridge_* 全部不可用时**，才使用 browser_* 系列工具（会启动独立浏览器）

终端命令执行：
- 使用 run_terminal_command 执行 Windows CMD 或 PowerShell 命令
- 默认在 DoroPet 项目目录下执行，可通过 working_dir 参数指定其他目录
- 适用于 git 操作、pip/npm 安装、文件操作、系统信息查询等
- 输出超过 8000 字符会自动截断，超时默认 60 秒
- 不要执行需要交互式输入的命令，不要执行破坏性命令

记忆管理：
- 当用户告诉你个人信息（名字、喜好、经历等）时，使用 add_memory 工具记住
- 需要回忆用户信息时，使用 search_memories 工具检索
- 主动记录重要事件和约定，帮助更好地服务用户
- **重要**：成功完成一个复杂的多步骤任务后（如播放音乐、安装软件、配置环境），
  用 add_memory 记录本次成功的操作方法和关键参数（如"网易云音乐：先用 pip 检查
  netease-music-sdk 版本，用 search_files 找到 music_player_card.py..."），
  下次处理类似请求时先用 search_memories 查找已有经验，直接复用而非重新摸索
"""
