"""
模型配置界面 — 适配 pydantic-ai。

LLM 模式直接对应 pydantic-ai 的 provider 体系：
- OpenAI 兼容: 自定义 base_url（DeepSeek/Ollama/Moonshot/Zhipu 等）
- OpenAI / Gemini / Anthropic / Groq: pydantic-ai 原生 provider

TTS / IMAGE 模式保持原有 ProviderManager 体系不变。
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
                             QListWidgetItem, QLineEdit, QDialog, QLabel,
                             QListWidget as QtListWidget, QDialogButtonBox,
                             QApplication, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
from qfluentwidgets import (ScrollArea, ComboBox, LineEdit, StrongBodyLabel,
                            TitleLabel, PushButton, FluentIcon, ListWidget,
                            BodyLabel, PrimaryPushButton, isDarkTheme,
                            SegmentedWidget, CheckBox, InfoBar, InfoBarPosition,
                            ToolButton, CardWidget, SubtitleLabel, CaptionLabel,
                            TransparentToolButton, HyperlinkLabel, ExpandLayout,
                            ExpandGroupSettingCard, SettingCardGroup, MessageBox)

from src.provider.register import (
    provider_registry, provider_cls_map,
    get_all_providers_by_type, get_provider_metadata
)
from src.provider.entities import ProviderType, ProviderConfig
from src.provider.manager import ProviderManager
from src.core.i18n import I18nManager, tr


# ---------------------------------------------------------------------------
# pydantic-ai LLM Provider 完整列表
# ---------------------------------------------------------------------------

PYDANTIC_LLM_PROVIDERS = [
    # ---- 第一组：OpenAI 兼容（自定义接口，适用于绝大多数国产/第三方服务） ----
    {
        "id": "openai-compatible",
        "name": "OpenAI 兼容 (自定义接口)",
        "prefix": None,               # None = 使用 OpenAIModel + OpenAIProvider
        "default_model": "gpt-4o-mini",
        "default_base_url": "",
        "needs_base_url": True,
        "api_key_url": "",
        "doc_url": "",
        "desc": "适用于 DeepSeek、Ollama、智谱、硅基流动、月之暗面、阿里百炼等所有兼容 OpenAI API 格式的服务。"
    },
    # ---- 第二组：pydantic-ai 原生 Provider（provider:model 字符串格式）----
    {
        "id": "openai",
        "name": "OpenAI",
        "prefix": "openai:",
        "default_model": "gpt-4o",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://platform.openai.com/api-keys",
        "doc_url": "https://platform.openai.com/docs",
        "desc": "ChatGPT / GPT-4o / o1 系列模型。API Key 设置: OPENAI_API_KEY 环境变量"
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "prefix": "deepseek:",
        "default_model": "deepseek-chat",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://platform.deepseek.com/api_keys",
        "doc_url": "https://platform.deepseek.com/docs",
        "desc": "国产高性价比大模型。API Key 设置: DEEPSEEK_API_KEY 环境变量"
    },
    {
        "id": "moonshotai",
        "name": "月之暗面 Moonshot (Kimi)",
        "prefix": "moonshotai:",
        "default_model": "moonshot-v1-8k",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://platform.moonshot.cn/console/api-keys",
        "doc_url": "https://platform.moonshot.cn/docs",
        "desc": "Kimi 长文本大模型。API Key 设置: MOONSHOT_API_KEY 环境变量"
    },
    {
        "id": "alibaba",
        "name": "阿里云百炼 (通义千问)",
        "prefix": "alibaba:",
        "default_model": "qwen-max",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://bailian.console.aliyun.com/",
        "doc_url": "https://help.aliyun.com/zh/model-studio/",
        "desc": "通义千问系列模型。API Key 设置: DASHSCOPE_API_KEY 环境变量"
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "prefix": "google:",
        "default_model": "gemini-2.0-flash",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://aistudio.google.com/app/apikey",
        "doc_url": "https://ai.google.dev/docs",
        "desc": "Gemini 多模态大模型。API Key 设置: GEMINI_API_KEY 环境变量"
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "prefix": "anthropic:",
        "default_model": "claude-sonnet-4-20250514",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://console.anthropic.com/settings/keys",
        "doc_url": "https://docs.anthropic.com",
        "desc": "Claude 系列模型。API Key 设置: ANTHROPIC_API_KEY 环境变量"
    },
    {
        "id": "groq",
        "name": "Groq",
        "prefix": "groq:",
        "default_model": "llama-3.1-8b-instant",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://console.groq.com/keys",
        "doc_url": "https://console.groq.com/docs",
        "desc": "超快推理速度。API Key 设置: GROQ_API_KEY 环境变量"
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "prefix": "mistral:",
        "default_model": "mistral-large-latest",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://console.mistral.ai/api-keys/",
        "doc_url": "https://docs.mistral.ai/",
        "desc": "欧洲领先大模型。API Key 设置: MISTRAL_API_KEY 环境变量"
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "prefix": "cohere:",
        "default_model": "command-r-plus",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://dashboard.cohere.com/api-keys",
        "doc_url": "https://docs.cohere.com/",
        "desc": "企业级 RAG 优化模型。API Key 设置: CO_API_KEY 环境变量"
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "prefix": "xai:",
        "default_model": "grok-2-latest",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://console.x.ai/",
        "doc_url": "https://docs.x.ai/",
        "desc": "Elon Musk 的 xAI 模型。API Key 设置: XAI_API_KEY 环境变量"
    },
    {
        "id": "cerebras",
        "name": "Cerebras",
        "prefix": "cerebras:",
        "default_model": "llama3.1-8b",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://cloud.cerebras.ai/",
        "doc_url": "https://docs.cerebras.ai/",
        "desc": "超快推理芯片。API Key 设置: CEREBRAS_API_KEY 环境变量"
    },
    {
        "id": "bedrock",
        "name": "AWS Bedrock",
        "prefix": "bedrock:",
        "default_model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://console.aws.amazon.com/bedrock/",
        "doc_url": "https://docs.aws.amazon.com/bedrock/",
        "desc": "AWS 托管模型服务。需要 AWS 凭证配置"
    },
    {
        "id": "azure",
        "name": "Azure OpenAI",
        "prefix": "azure:",
        "default_model": "gpt-4o",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://portal.azure.com/",
        "doc_url": "https://learn.microsoft.com/azure/ai-services/openai/",
        "desc": "Azure 托管的 OpenAI 服务。需要 AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY"
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "prefix": "openrouter:",
        "default_model": "openai/gpt-4o",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://openrouter.ai/keys",
        "doc_url": "https://openrouter.ai/docs",
        "desc": "聚合 200+ 模型的一站式 API。API Key 设置: OPENROUTER_API_KEY 环境变量"
    },
    {
        "id": "together",
        "name": "Together AI",
        "prefix": "together:",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://api.together.xyz/settings/api-keys",
        "doc_url": "https://docs.together.ai/",
        "desc": "开源模型推理平台。API Key 设置: TOGETHER_API_KEY 环境变量"
    },
    {
        "id": "fireworks",
        "name": "Fireworks AI",
        "prefix": "fireworks:",
        "default_model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://fireworks.ai/account/api-keys",
        "doc_url": "https://docs.fireworks.ai/",
        "desc": "快速推理平台。API Key 设置: FIREWORKS_API_KEY 环境变量"
    },
    {
        "id": "huggingface",
        "name": "HuggingFace Inference",
        "prefix": "huggingface:",
        "default_model": "meta-llama/Llama-3.1-8B-Instruct",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "https://huggingface.co/settings/tokens",
        "doc_url": "https://huggingface.co/docs/api-inference/",
        "desc": "HuggingFace 推理端点。API Key 设置: HF_TOKEN 环境变量"
    },
    {
        "id": "ollama",
        "name": "Ollama (本地)",
        "prefix": "ollama:",
        "default_model": "llama3",
        "default_base_url": "",
        "needs_base_url": False,
        "api_key_url": "",
        "doc_url": "https://ollama.com/",
        "desc": "本地运行开源模型，无需联网，免费使用"
    },
    # {
    #     "id": "vercel",
    #     "name": "Vercel AI SDK",
    #     "prefix": "vercel:",
    #     ...
    # },
    # {
    #     "id": "github",
    #     "name": "GitHub Models",
    #     "prefix": "github:",
    #     ...
    # },
    # {
    #     "id": "nebius",
    #     "name": "Nebius AI",
    #     "prefix": "nebius:",
    #     ...
    # },
    # {
    #     "id": "sambanova",
    #     "name": "SambaNova",
    #     "prefix": "sambanova:",
    #     ...
    # },
]

# 快捷 provider 别名（一键填充 Base URL + 模型名，适用于 OpenAI 兼容模式）
QUICK_FILL_PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "desc": "国产高性价比大模型"
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "desc": "本地运行，无需联网"
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "desc": "智谱 GLM 系列"
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "desc": "月之暗面 Kimi，长文本"
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "desc": "硅基流动，模型种类丰富"
    },
    "alibaba": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
        "desc": "阿里百炼，通义千问系列"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "desc": "聚合 200+ 模型"
    },
}


# ---------------------------------------------------------------------------
# Widget 组件（复用原有）
# ---------------------------------------------------------------------------

class HelpLabel(QWidget):
    def __init__(self, text: str, help_text: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.label = BodyLabel(text, self)
        layout.addWidget(self.label)
        if help_text:
            self.help_btn = ToolButton(FluentIcon.HELP, self)
            self.help_btn.setFixedSize(16, 16)
            self.help_btn.setToolTip(help_text)
            self.help_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
            layout.addWidget(self.help_btn)


class FormField(QWidget):
    def __init__(self, label: str, widget, help_text: str = "",
                 link_text: str = "", link_url: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("formField")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)

        self.label = BodyLabel(label, self)
        label_layout.addWidget(self.label)

        if help_text:
            help_btn = ToolButton(FluentIcon.HELP, self)
            help_btn.setFixedSize(16, 16)
            help_btn.setToolTip(help_text)
            help_btn.setStyleSheet("QToolButton { border: none; background: transparent; opacity: 0.6; }")
            label_layout.addWidget(help_btn)

        if link_text and link_url:
            link = HyperlinkLabel(self)
            link.setUrl(link_url)
            link.setText(link_text)
            link.setStyleSheet("font-size: 12px;")
            label_layout.addWidget(link)

        label_layout.addStretch()
        layout.addLayout(label_layout)

        self.widget = widget
        layout.addWidget(widget)

    def set_visible(self, visible: bool):
        self.setVisible(visible)


class SettingCard(CardWidget):
    def __init__(self, title: str, icon: FluentIcon = None, parent=None):
        super().__init__(parent)
        self.setObjectName("settingCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(12)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        if icon:
            icon_label = ToolButton(icon, self)
            icon_label.setFixedSize(20, 20)
            icon_label.setStyleSheet("QToolButton { border: none; background: transparent; }")
            header_layout.addWidget(icon_label)
        self.title_label = SubtitleLabel(title, self)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self._layout.addLayout(header_layout)
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self._layout.addWidget(self.content_widget)

    def add_field(self, field: FormField):
        self.content_layout.addWidget(field)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)


class CollapsibleCard(CardWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, title: str, icon: FluentIcon = None, collapsed: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleCard")
        self._collapsed = collapsed
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 20, 12)
        self._layout.setSpacing(0)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        if icon:
            icon_label = ToolButton(icon, self)
            icon_label.setFixedSize(18, 18)
            icon_label.setStyleSheet("QToolButton { border: none; background: transparent; }")
            header_layout.addWidget(icon_label)
        self.title_label = BodyLabel(title, self)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.toggle_btn = ToolButton(FluentIcon.CHEVRON_DOWN_MED, self)
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self.toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self.toggle_btn)
        self._layout.addLayout(header_layout)
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 12, 0, 0)
        self.content_layout.setSpacing(12)
        self._layout.addWidget(self.content_widget)
        if collapsed:
            self.content_widget.setVisible(False)
            self.toggle_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content_widget.setVisible(not self._collapsed)
        self.toggle_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED if self._collapsed else FluentIcon.CHEVRON_DOWN_MED)
        self.toggled.emit(not self._collapsed)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def set_collapsed(self, collapsed: bool):
        if self._collapsed != collapsed:
            self._toggle()


class ModelSelectDialog(QDialog):
    def __init__(self, items: list, title: str = None, parent=None):
        super().__init__(parent)
        if title is None:
            title = tr("config.select_model_title", default="选择模型")
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.selected_model = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("config.select_from_list", default="从列表中选择:")))
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText(tr("config.search_placeholder", default="搜索..."))
        self.search_input.textChanged.connect(self.filter_models)
        layout.addWidget(self.search_input)
        self.model_list = QtListWidget(self)
        self.model_list.addItems(items)
        self.model_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.model_list)
        self.all_items = items
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def filter_models(self, text: str):
        self.model_list.clear()
        filtered = [m for m in self.all_items if text.lower() in m.lower()]
        self.model_list.addItems(filtered)

    def accept(self):
        current_item = self.model_list.currentItem()
        if current_item:
            self.selected_model = current_item.text()
        super().accept()


class QuickAddDialog(QDialog):
    """快速添加 LLM 配置对话框 — 适配 pydantic-ai provider。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("config.quick_add_title", default="快速添加 LLM 配置"))
        self.setMinimumWidth(520)
        self.selected_provider = None
        self.api_key = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        layout.addWidget(SubtitleLabel(tr("config.select_ai_platform", default="选择 AI 平台"), self))
        hint = CaptionLabel(tr("config.quick_add_desc", default="选择平台后，只需填入 API 密钥即可完成配置"), self)
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        provider_grid = QWidget(self)
        grid_layout = QVBoxLayout(provider_grid)
        grid_layout.setSpacing(8)

        self.provider_buttons = []
        for p in PYDANTIC_LLM_PROVIDERS:
            btn = PushButton(p["name"], provider_grid)
            btn.setFixedHeight(40)
            btn.setToolTip(p.get("desc", ""))
            btn.clicked.connect(lambda checked, provider=p: self._select_provider(provider))
            self.provider_buttons.append((btn, p))
            grid_layout.addWidget(btn)

        layout.addWidget(provider_grid)

        # API Key
        self.api_section = QWidget(self)
        api_layout = QVBoxLayout(self.api_section)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(8)
        self.api_label = BodyLabel(tr("config.api_key_label", default="API 密钥"), self)
        api_layout.addWidget(self.api_label)
        self.api_input = LineEdit(self)
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText(tr("config.api_key_placeholder", default="粘贴您的 API Key..."))
        api_layout.addWidget(self.api_input)
        self.help_link = HyperlinkLabel(self)
        self.help_link.setText(tr("config.how_to_get", default="如何获取?"))
        api_layout.addWidget(self.help_link)
        self.api_section.setVisible(False)
        layout.addWidget(self.api_section)

        # Config Name
        self.name_section = QWidget(self)
        name_layout = QVBoxLayout(self.name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        name_layout.addWidget(BodyLabel(tr("config.config_name_optional", default="配置名称 (可选)"), self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText(tr("config.default_platform_name", default="默认使用平台名称"))
        name_layout.addWidget(self.name_input)
        self.name_section.setVisible(False)
        layout.addWidget(self.name_section)

        layout.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _select_provider(self, provider: dict):
        self.selected_provider = provider
        for btn, p in self.provider_buttons:
            btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }" if p == provider else "")
        self.api_section.setVisible(True)
        self.name_section.setVisible(True)
        self.api_label.setText(tr("config.api_key_for_provider", default="{provider} API 密钥").format(provider=provider['name']))
        if provider.get("api_key_url"):
            self.help_link.setUrl(provider["api_key_url"])
            self.help_link.setVisible(True)
        else:
            self.help_link.setVisible(False)
        self.api_input.setFocus()

    def accept(self):
        if not self.selected_provider:
            InfoBar.warning(tr("general.tip"), tr("config.select_ai_platform_hint", default="请先选择一个 AI 平台"), duration=2000, parent=self)
            return
        self.api_key = self.api_input.text().strip()
        self.config_name = self.name_input.text().strip()
        pi = self.selected_provider
        if not self.api_key and not pi["id"].startswith("ollama"):
            InfoBar.warning(tr("general.tip"), tr("config.enter_api_key", default="请输入 API 密钥"), duration=2000, parent=self)
            return
        super().accept()


# ---------------------------------------------------------------------------
# 主配置界面
# ---------------------------------------------------------------------------

class ConfigInterface(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("ModelConfigInterface")
        self.current_model_id = None
        self.current_mode = "LLM"

        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)

        self.init_ui()
        self.load_models()
        self.update_form_visibility()

    # ---------- 初始化 ----------

    # ---------- 获取 LLM Provider 列表 ----------

    def _get_llm_provider_info(self, provider_id: str) -> dict:
        for p in PYDANTIC_LLM_PROVIDERS:
            if p["id"] == provider_id:
                return p
        return PYDANTIC_LLM_PROVIDERS[0]  # fallback

    # ---------- UI 构建 ----------

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self._init_left_panel(main_layout)
        self._init_right_panel(main_layout)
        self.edit_widget.setEnabled(False)
        self._refresh_provider_combo()
        self.update_theme()

    def _init_left_panel(self, parent_layout):
        self.left_panel = QWidget()
        self.left_panel.setObjectName("left_panel")
        self.left_panel.setMinimumWidth(260)
        self.left_panel.setMaximumWidth(340)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(16, 20, 16, 20)
        left_layout.setSpacing(12)

        self.pivot = SegmentedWidget(self.left_panel)
        self.pivot.addItem("LLM", tr("config.chat_model.short", default=tr("config.chat_model")))
        self.pivot.addItem("TTS", tr("config.tts.short", default=tr("config.tts")))
        self.pivot.addItem("IMAGE", tr("config.image_gen.short", default=tr("config.image_gen")))
        self.pivot.setCurrentItem("LLM")
        self.pivot.currentItemChanged.connect(self.switch_mode)
        self._update_pivot_nav()
        left_layout.addWidget(self.pivot)

        list_header = QHBoxLayout()
        list_header.addWidget(StrongBodyLabel(tr("config.config_list"), self.left_panel))
        list_header.addStretch()
        left_layout.addLayout(list_header)

        self.model_list = ListWidget(self.left_panel)
        self.model_list.setObjectName("model_list")
        self.model_list.itemClicked.connect(self.on_model_selected)
        left_layout.addWidget(self.model_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.quick_add_btn = PushButton(FluentIcon.ADD_TO, tr("config.quick_add"), self.left_panel)
        self.quick_add_btn.setFixedHeight(32)
        self.quick_add_btn.clicked.connect(self.quick_add_model)
        btn_layout.addWidget(self.quick_add_btn, 1)
        self.add_btn = PushButton(FluentIcon.ADD, tr("config.manual_add"), self.left_panel)
        self.add_btn.setFixedHeight(32)
        self.add_btn.clicked.connect(self.create_new_model)
        btn_layout.addWidget(self.add_btn)
        left_layout.addLayout(btn_layout)
        parent_layout.addWidget(self.left_panel)

    def _update_pivot_nav(self):
        nav_items = {
            "LLM": (tr("config.chat_model.short", default=tr("config.chat_model")), tr("config.chat_model")),
            "TTS": (tr("config.tts.short", default=tr("config.tts")), tr("config.tts")),
            "IMAGE": (tr("config.image_gen.short", default=tr("config.image_gen")), tr("config.image_gen")),
        }
        metrics = QFontMetrics(self.pivot.font())
        item_widths = []
        for key, (label, full_text) in nav_items.items():
            item = self.pivot.items.get(key)
            if not item:
                continue
            item.setText(label)
            item.setToolTip(full_text)
            item_widths.append(metrics.horizontalAdvance(label) + 44)
        target_width = min(340, max(260, sum(item_widths) + 48))
        self.left_panel.setFixedWidth(target_width)
        self.pivot.setFixedWidth(target_width - 32)

    def _init_right_panel(self, parent_layout):
        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        right_panel.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.edit_widget = QWidget()
        self.edit_widget.setObjectName("configEditWidget")
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        self.page_title = TitleLabel(tr("config.title"), self.edit_widget)
        header_layout.addWidget(self.page_title)
        header_layout.addStretch()
        self.status_label = CaptionLabel("", self.edit_widget)
        self.status_label.setStyleSheet("color: #0078d4;")
        header_layout.addWidget(self.status_label)
        right_layout.addLayout(header_layout)

        right_layout.addWidget(self._create_basic_card())
        right_layout.addWidget(self._create_auth_card())
        right_layout.addWidget(self._create_advanced_card())
        self._create_action_buttons(right_layout)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        parent_layout.addWidget(right_panel)

    # ---------- LLM 基础配置卡 ----------

    def _create_basic_card(self) -> SettingCard:
        self.basic_card = SettingCard(tr("config.basic_config"), FluentIcon.SETTING, self)

        # 配置名称
        self.name_field = FormField(tr("config.config_name"), LineEdit(self), tr("config.config_name_hint"), parent=self)
        self.name_field.widget.setPlaceholderText(tr("config.config_name_placeholder"))
        self.basic_card.add_field(self.name_field)

        # AI 平台
        provider_widget = QWidget(self)
        provider_layout = QVBoxLayout(provider_widget)
        provider_layout.setContentsMargins(0, 0, 0, 0)
        provider_layout.setSpacing(6)

        self.provider_combo = ComboBox(provider_widget)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        self.provider_desc_label = CaptionLabel("", provider_widget)
        self.provider_desc_label.setStyleSheet("color: gray; font-size: 12px;")
        self.provider_desc_label.setWordWrap(True)
        provider_layout.addWidget(self.provider_desc_label)

        self.provider_help_link = HyperlinkLabel(provider_widget)
        self.provider_help_link.setText(tr("config.get_api_key"))
        self.provider_help_link.setVisible(False)
        provider_layout.addWidget(self.provider_help_link)

        self.provider_field = FormField(tr("config.ai_platform"), provider_widget, tr("config.ai_platform_hint"), parent=self)
        self.basic_card.add_field(self.provider_field)

        # 快捷填充（仅 OpenAI 兼容模式显示）
        self.quick_fill_widget = QWidget(self)
        qf_layout = QHBoxLayout(self.quick_fill_widget)
        qf_layout.setContentsMargins(0, 0, 0, 0)
        qf_layout.setSpacing(6)
        qf_label = CaptionLabel(tr("config.quick_fill"), self.quick_fill_widget)
        qf_label.setStyleSheet("color: gray;")
        qf_layout.addWidget(qf_label)

        self.quick_fill_combo = ComboBox(self.quick_fill_widget)
        self.quick_fill_combo.setFixedWidth(150)
        self.quick_fill_combo.addItem(tr("config.select_provider"), userData=None)
        for key, info in QUICK_FILL_PROVIDERS.items():
            self.quick_fill_combo.addItem(f"{key} - {tr(f'config.quick_fill.{key}', default=info['desc'])}", userData=key)
        self.quick_fill_combo.currentIndexChanged.connect(self._on_quick_fill)
        qf_layout.addWidget(self.quick_fill_combo)
        qf_layout.addStretch()
        self.quick_fill_widget.setVisible(False)
        self.basic_card.add_widget(self.quick_fill_widget)

        # 模型名称
        model_widget = QWidget(self)
        model_layout = QHBoxLayout(model_widget)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(8)
        self.model_id_input = LineEdit(model_widget)
        self.model_id_input.setPlaceholderText(tr("config.model_name_placeholder"))
        model_layout.addWidget(self.model_id_input, 1)
        self.fetch_models_btn = PushButton(FluentIcon.SEARCH, tr("config.search_models"), model_widget)
        self.fetch_models_btn.setFixedHeight(32)
        self.fetch_models_btn.setToolTip(tr("config.fetch_models"))
        self.fetch_models_btn.clicked.connect(self.fetch_models_from_provider)
        model_layout.addWidget(self.fetch_models_btn)
        self.model_field = FormField(tr("config.model_name"), model_widget, tr("config.model_name_hint"), parent=self)
        self.basic_card.add_field(self.model_field)

        # ===== TTS 专用字段 =====
        voice_widget = QWidget(self)
        voice_layout = QHBoxLayout(voice_widget)
        voice_layout.setContentsMargins(0, 0, 0, 0)
        voice_layout.setSpacing(8)
        self.voice_input = LineEdit(voice_widget)
        self.voice_input.setPlaceholderText(tr("config.voice_placeholder"))
        voice_layout.addWidget(self.voice_input, 1)
        self.fetch_voices_btn = PushButton(FluentIcon.SEARCH, tr("config.get_voices"), voice_widget)
        self.fetch_voices_btn.setFixedHeight(32)
        self.fetch_voices_btn.clicked.connect(self.fetch_voices_from_provider)
        voice_layout.addWidget(self.fetch_voices_btn)
        self.voice_field = FormField(tr("config.voice_package"), voice_widget, tr("config.voice_package_hint"), parent=self)
        self.basic_card.add_field(self.voice_field)

        self.api_name_field = FormField(tr("config.api_endpoint"), LineEdit(self), tr("config.api_endpoint_hint"), parent=self)
        self.api_name_field.widget.setPlaceholderText(tr("config.api_endpoint_placeholder"))
        self.api_name_field.widget.setText("/tts_request")
        self.basic_card.add_field(self.api_name_field)

        self.prompt_audio_field = FormField(tr("config.ref_audio_path"), LineEdit(self), tr("config.ref_audio_path_hint"), parent=self)
        self.prompt_audio_field.widget.setPlaceholderText(tr("config.ref_audio_path_placeholder"))
        self.basic_card.add_field(self.prompt_audio_field)

        self.prompt_text_field = FormField(tr("config.ref_audio_text"), LineEdit(self), tr("config.ref_audio_text_hint"), parent=self)
        self.prompt_text_field.widget.setPlaceholderText(tr("config.ref_audio_text_placeholder"))
        self.basic_card.add_field(self.prompt_text_field)

        return self.basic_card

    # ---------- 认证卡 ----------

    def _create_auth_card(self) -> SettingCard:
        self.auth_card = SettingCard(tr("config.auth_info"), FluentIcon.FINGERPRINT, self)
        self.api_key_field = FormField(tr("config.api_key"), LineEdit(self), tr("config.api_key_hint"), parent=self)
        self.api_key_field.widget.setEchoMode(QLineEdit.Password)
        self.api_key_field.widget.setPlaceholderText("sk-...")
        self.auth_card.add_field(self.api_key_field)
        return self.auth_card

    # ---------- 高级卡 ----------

    def _create_advanced_card(self) -> CollapsibleCard:
        self.advanced_card = CollapsibleCard(tr("config.advanced"), FluentIcon.SETTING, collapsed=True, parent=self)

        self.base_url_field = FormField(tr("config.base_url"), LineEdit(self),
                                         tr("config.base_url_hint"),
                                         parent=self)
        self.base_url_field.widget.setPlaceholderText(tr("config.base_url_placeholder"))
        self.advanced_card.add_widget(self.base_url_field)

        self.proxy_field = FormField(tr("config.proxy"), LineEdit(self), tr("config.proxy_hint"), parent=self)
        self.proxy_field.widget.setPlaceholderText(tr("config.proxy_placeholder"))
        self.advanced_card.add_widget(self.proxy_field)

        options_widget = QWidget(self)
        options_layout = QHBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(16)
        self.chk_visual = CheckBox(tr("config.vision_model"), options_widget)
        self.chk_visual.setToolTip(tr("config.vision_model_desc"))
        options_layout.addWidget(self.chk_visual)
        self.chk_thinking = CheckBox(tr("config.thinking_model"), options_widget)
        self.chk_thinking.setToolTip(tr("config.thinking_model_desc"))
        options_layout.addWidget(self.chk_thinking)
        options_layout.addStretch()
        self.advanced_card.add_widget(options_widget)

        return self.advanced_card

    # ---------- 操作按钮 ----------

    def _create_action_buttons(self, layout: QVBoxLayout):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("config.save_config"), self.edit_widget)
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self.save_model)
        btn_layout.addWidget(self.save_btn)
        self.use_btn = PushButton(FluentIcon.ACCEPT, tr("config.enable_config"), self.edit_widget)
        self.use_btn.setFixedHeight(36)
        self.use_btn.setToolTip(tr("config.enable_desc"))
        self.use_btn.clicked.connect(self.set_active_model_handler)
        btn_layout.addWidget(self.use_btn)
        btn_layout.addStretch()
        self.delete_btn = PushButton(FluentIcon.DELETE, tr("config.delete_config"), self.edit_widget)
        self.delete_btn.setToolTip(tr("config.delete_desc"))
        self.delete_btn.clicked.connect(self.delete_model)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

    # ---------- Provider ComboBox 填充 ----------

    def _refresh_provider_combo(self):
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()

        if self.current_mode == "LLM":
            for p in PYDANTIC_LLM_PROVIDERS:
                self.provider_combo.addItem(tr(f"config.provider.{p['id']}.name", default=p["name"]), userData=p["id"])
        elif self.current_mode == "TTS":
            providers = get_all_providers_by_type(ProviderType.TEXT_TO_SPEECH)
            for pm in providers:
                self.provider_combo.addItem(pm.provider_display_name, userData=pm.type)
        elif self.current_mode == "IMAGE":
            providers = get_all_providers_by_type(ProviderType.IMAGE_GENERATION)
            for pm in providers:
                self.provider_combo.addItem(pm.provider_display_name, userData=pm.type)

        self.provider_combo.blockSignals(False)

    # ---------- 属性访问器 ----------

    @property
    def name_input(self): return self.name_field.widget
    @property
    def api_key_input(self): return self.api_key_field.widget
    @property
    def base_url_input(self): return self.base_url_field.widget
    @property
    def proxy_input(self): return self.proxy_field.widget
    @property
    def api_name_input(self): return self.api_name_field.widget
    @property
    def prompt_audio_input(self): return self.prompt_audio_field.widget
    @property
    def prompt_text_input(self): return self.prompt_text_field.widget

    # ---------- 模式切换 ----------

    def switch_mode(self, item_key):
        self.current_mode = item_key
        self.create_new_model()
        self.edit_widget.setEnabled(False)
        self._refresh_provider_combo()
        self.load_models()
        self.update_form_visibility()
        mode_titles = {"LLM": tr("config.chat_model_config", default="对话模型配置"), 
                       "TTS": tr("config.tts_config", default="语音合成配置"), 
                       "IMAGE": tr("config.image_gen_config", default="图像生成配置")}
        self.page_title.setText(mode_titles.get(item_key, tr("config.title")))

    def refresh_ui(self, lang_code: str = None):
        """语言切换时刷新所有 UI 文本。"""
        # 更新分段导航按钮文本
        self._update_pivot_nav()

        # 左侧面板
        self._update_list_header()
        self.quick_add_btn.setText(tr("config.quick_add"))
        self.add_btn.setText(tr("config.manual_add"))

        # 右侧标题
        mode_titles = {"LLM": tr("config.chat_model_config", default="对话模型配置"),
                       "TTS": tr("config.tts_config", default="语音合成配置"),
                       "IMAGE": tr("config.image_gen_config", default="图像生成配置")}
        self.page_title.setText(mode_titles.get(self.current_mode, tr("config.title")))

        # 基本配置卡
        self.basic_card.title_label.setText(tr("config.basic_config"))
        self.name_field.label.setText(tr("config.config_name"))
        self.name_field.widget.setPlaceholderText(tr("config.config_name_placeholder"))
        self.provider_field.label.setText(tr("config.ai_platform"))
        self.provider_help_link.setText(tr("config.get_api_key"))
        self.model_field.label.setText(tr("config.model_name"))
        self.model_id_input.setPlaceholderText(tr("config.model_name_placeholder"))
        self.fetch_models_btn.setText(tr("config.search_models"))
        self.fetch_models_btn.setToolTip(tr("config.fetch_models"))
        self.voice_field.label.setText(tr("config.voice_package"))
        self.voice_input.setPlaceholderText(tr("config.voice_placeholder"))
        self.fetch_voices_btn.setText(tr("config.get_voices"))
        self.api_name_field.label.setText(tr("config.api_endpoint"))
        self.api_name_field.widget.setPlaceholderText(tr("config.api_endpoint_placeholder"))
        self.prompt_audio_field.label.setText(tr("config.ref_audio_path"))
        self.prompt_audio_field.widget.setPlaceholderText(tr("config.ref_audio_path_placeholder"))
        self.prompt_text_field.label.setText(tr("config.ref_audio_text"))
        self.prompt_text_field.widget.setPlaceholderText(tr("config.ref_audio_text_placeholder"))

        # 快捷填充
        self.quick_fill_combo.blockSignals(True)
        self.quick_fill_combo.clear()
        self.quick_fill_combo.addItem(tr("config.select_provider"), userData=None)
        for key, info in QUICK_FILL_PROVIDERS.items():
            self.quick_fill_combo.addItem(f"{key} - {tr(f'config.quick_fill.{key}', default=info['desc'])}", userData=key)
        self.quick_fill_combo.setCurrentIndex(0)
        self.quick_fill_combo.blockSignals(False)

        # 刷新 provider 下拉框（LLM 模式）
        saved_provider_id = self.provider_combo.currentData()
        self._refresh_provider_combo()
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == saved_provider_id:
                self.provider_combo.setCurrentIndex(i)
                break

        # 认证卡
        self.auth_card.title_label.setText(tr("config.auth_info"))
        self.api_key_field.label.setText(tr("config.api_key"))

        # 高级卡
        self.advanced_card.title_label.setText(tr("config.advanced"))
        self.base_url_field.label.setText(tr("config.base_url"))
        self.base_url_field.widget.setPlaceholderText(tr("config.base_url_placeholder"))
        self.proxy_field.label.setText(tr("config.proxy"))
        self.proxy_field.widget.setPlaceholderText(tr("config.proxy_placeholder"))
        self.chk_visual.setText(tr("config.vision_model"))
        self.chk_visual.setToolTip(tr("config.vision_model_desc"))
        self.chk_thinking.setText(tr("config.thinking_model"))
        self.chk_thinking.setToolTip(tr("config.thinking_model_desc"))

        # 操作按钮
        self.save_btn.setText(tr("config.save_config"))
        self.use_btn.setText(tr("config.enable_config"))
        self.use_btn.setToolTip(tr("config.enable_desc"))
        self.delete_btn.setText(tr("config.delete_config"))
        self.delete_btn.setToolTip(tr("config.delete_desc"))

        # 状态标签
        if self.current_model_id:
            self.status_label.setText(tr("config.editing"))
        else:
            self.status_label.setText(tr("config.new_config"))

    def _update_list_header(self):
        """更新模型列表头标签。"""
        headers = self.left_panel.findChildren(StrongBodyLabel)
        for lbl in headers:
            if lbl.parent() is self.left_panel:
                lbl.setText(tr("config.config_list"))
                break

    def update_form_visibility(self):
        is_llm = (self.current_mode == "LLM")
        is_tts = (self.current_mode == "TTS")

        # LLM 特有
        self.chk_visual.setVisible(is_llm)
        self.chk_thinking.setVisible(is_llm)
        self.provider_desc_label.setVisible(is_llm)

        # TTS 特有
        self.voice_field.setVisible(is_tts)
        self.fetch_voices_btn.setVisible(is_tts)
        self.api_name_field.setVisible(is_tts)
        self.prompt_audio_field.setVisible(is_tts)
        self.prompt_text_field.setVisible(is_tts)

        # 通用
        self.fetch_models_btn.setVisible(is_llm)

        # 根据 provider 进一步调整（on_provider_changed 处理）
        if is_llm:
            self.on_provider_changed(self.provider_combo.currentIndex())

    # ---------- 模型列表加载 ----------

    def load_models(self):
        self.model_list.clear()
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
        for m in models:
            item = QListWidgetItem(m[1], self.model_list)
            item.setData(Qt.UserRole, m[0])
            self.model_list.addItem(item)
            is_active_idx = 7 if self.current_mode == "TTS" else 6
            if m[is_active_idx] == 1:
                self.model_list.setCurrentItem(item)
                self.on_model_selected(item)

    def on_model_selected(self, item):
        if not item: return
        self.edit_widget.setEnabled(True)
        model_id = item.data(Qt.UserRole)
        self.current_model_id = model_id
        self.status_label.setText(tr("config.editing"))

        target = None
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()

        for m in models:
            if m[0] == model_id:
                target = m
                break
        if not target: return

        self.name_input.setText(target[1])
        provider = target[2]

        # 设置 provider combo
        index = 0
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                index = i
                break
        self.provider_combo.setCurrentIndex(index)

        if self.current_mode == "IMAGE":
            self.base_url_input.setText(target[3])
            self.api_key_input.setText(target[4])
            self.model_id_input.setText(target[5])
        else:
            self.api_key_input.setText(target[3])
            self.base_url_input.setText(target[4])
            self.model_id_input.setText(target[5])

        if self.current_mode == "TTS":
            self.voice_input.setText(target[6])
            proxy = target[8] if len(target) > 8 else ''
            self.proxy_input.setText(proxy)
            api_name = target[9] if len(target) > 9 else '/tts_request'
            self.api_name_input.setText(api_name)
            prompt_audio = target[10] if len(target) > 10 else ''
            self.prompt_audio_input.setText(prompt_audio)
            prompt_text = target[11] if len(target) > 11 else ''
            self.prompt_text_input.setText(prompt_text)
        elif self.current_mode == "LLM":
            if len(target) > 7:
                self.chk_visual.setChecked(bool(target[7]))
                self.chk_thinking.setChecked(bool(target[8]) if len(target) > 8 else False)
            proxy = target[9] if len(target) > 9 else ''
            self.proxy_input.setText(proxy)
        elif self.current_mode == "IMAGE":
            proxy = target[7] if len(target) > 7 else ''
            self.proxy_input.setText(proxy)

    # ---------- Provider 切换 ----------

    def on_provider_changed(self, index):
        if self.current_mode != "LLM":
            # TTS/IMAGE 保持原有逻辑
            provider_type = self.provider_combo.currentData()
            self.provider_help_link.setVisible(False)
            if provider_type:
                metadata = get_provider_metadata(provider_type)
                if metadata and metadata.default_config_tmpl:
                    dc = metadata.default_config_tmpl
                    if "base_url" in dc:
                        self.base_url_input.setText(dc["base_url"])
                    if "model" in dc:
                        self.model_id_input.setText(dc["model"])
                    if "voice" in dc:
                        self.voice_input.setText(dc["voice"])
            return

        provider_id = self.provider_combo.currentData()
        if not provider_id:
            return

        pi = self._get_llm_provider_info(provider_id)

        # 描述
        self.provider_desc_label.setText(tr(f"config.provider.{provider_id}.desc", default=pi.get("desc", "")))

        # 帮助链接
        if pi.get("api_key_url"):
            self.provider_help_link.setUrl(pi["api_key_url"])
            self.provider_help_link.setVisible(True)
        else:
            self.provider_help_link.setVisible(False)

        # Base URL 可见性
        self.base_url_field.set_visible(pi["needs_base_url"])
        if pi["needs_base_url"] and not self.base_url_input.text():
            self.base_url_input.setText(pi.get("default_base_url", ""))

        # 快捷填充可见性
        self.quick_fill_widget.setVisible(pi["needs_base_url"])

        # 默认模型
        if not self.model_id_input.text():
            self.model_id_input.setText(pi.get("default_model", ""))

        # API Key 提示
        self.api_key_input.setPlaceholderText(
            tr("config.local_no_key") if "ollama" in provider_id else
            tr("config.enter_api_key")
        )

    def _on_quick_fill(self, index):
        # 使用 int(index) 确保拿到的是数字索引
        idx = int(index) if not isinstance(index, int) else index
        key = self.quick_fill_combo.itemData(idx)
        if not key or key not in QUICK_FILL_PROVIDERS:
            return
        info = QUICK_FILL_PROVIDERS[key]

        print(f"[QuickFill] Selected: {key}, base_url={info['base_url']}, model={info['default_model']}")

        self.base_url_input.setText(info["base_url"])
        self.model_id_input.setText(info["default_model"])

        # 展开高级选项卡让用户看到填充结果
        self.advanced_card.set_collapsed(False)

        InfoBar.success(
            tr("config.filled", default="已填充").format(name=key),
            f"Base URL → {info['base_url']}\nModel → {info['default_model']}",
            duration=3000,
            parent=self
        )

        # 重置下拉框（阻塞信号避免重复触发）
        self.quick_fill_combo.blockSignals(True)
        self.quick_fill_combo.setCurrentIndex(0)
        self.quick_fill_combo.blockSignals(False)

    # ---------- 创建 / 快速添加 ----------

    def create_new_model(self):
        self.model_list.clearSelection()
        self.edit_widget.setEnabled(True)
        self.current_model_id = None
        self.status_label.setText(tr("config.new_config"))
        self.name_input.clear()
        self.provider_combo.setCurrentIndex(0)
        self.api_key_input.clear()
        self.base_url_input.clear()
        self.model_id_input.clear()
        self.voice_input.clear()
        self.api_name_input.clear()
        self.api_name_input.setText("/tts_request")
        self.prompt_audio_input.clear()
        self.prompt_text_input.clear()
        self.proxy_input.clear()
        self.chk_visual.setChecked(False)
        self.chk_thinking.setChecked(False)
        self.advanced_card.set_collapsed(True)
        self.quick_fill_combo.setCurrentIndex(0)
        self.name_input.setFocus()

    def quick_add_model(self):
        if self.current_mode != "LLM":
            # TTS/IMAGE: 使用旧的快速添加
            self._quick_add_tts_or_image()
            return

        dialog = QuickAddDialog(self)
        if dialog.exec_() != QDialog.Accepted or not dialog.selected_provider:
            return

        provider = dialog.selected_provider
        name = dialog.config_name or provider["name"]
        self.name_input.setText(name)
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider["id"]:
                self.provider_combo.setCurrentIndex(i)
                break
        self.api_key_input.setText(dialog.api_key)
        if provider.get("default_base_url"):
            self.base_url_input.setText(provider["default_base_url"])
        self.model_id_input.setText(provider.get("default_model", ""))
        self.edit_widget.setEnabled(True)
        self.current_model_id = None
        self.status_label.setText(tr("config.new_config"))
        InfoBar.success(tr("config.quick_add_title"), 
                        tr("config.quick_add_filled_msg", default="已填充 {name} 的默认配置，请检查后保存").format(name=provider['name']),
                        duration=3000, parent=self)

    def _quick_add_tts_or_image(self):
        """TTS / IMAGE 的快速添加逻辑 — 复用 QuickAddDialog 但传入 provider 列表。"""
        providers = get_all_providers_by_type(
            ProviderType.TEXT_TO_SPEECH if self.current_mode == "TTS" else ProviderType.IMAGE_GENERATION
        )
        provider_list = []
        for pm in providers:
            provider_list.append({
                "id": pm.type,
                "name": pm.provider_display_name,
                "desc": pm.desc or "",
                "default_model": pm.default_config_tmpl.get("model", "") if pm.default_config_tmpl else "",
                "default_base_url": pm.default_config_tmpl.get("base_url", "") if pm.default_config_tmpl else "",
                "needs_base_url": True,
                "api_key_url": "",
                "doc_url": "",
                "prefix": None,
            })

        dialog = QuickAddLegacyDialog(provider_list, self.current_mode, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_provider:
            provider = dialog.selected_provider
            name = dialog.config_name or provider["name"]
            self.name_input.setText(name)
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == provider["id"]:
                    self.provider_combo.setCurrentIndex(i)
                    break
            self.api_key_input.setText(dialog.api_key)
            if provider.get("default_base_url"):
                self.base_url_input.setText(provider["default_base_url"])
            self.model_id_input.setText(provider.get("default_model", ""))
            self.edit_widget.setEnabled(True)
            self.current_model_id = None
            self.status_label.setText(tr("config.new_config"))

    # ---------- 获取模型列表 ----------

    def fetch_models_from_provider(self):
        if self.current_mode == "LLM":
            base_url = self.base_url_input.text().strip()
            api_key = self.api_key_input.text().strip()
            if not base_url:
                InfoBar.warning(tr("general.tip"), tr("config.fill_base_url_first"), duration=2000, parent=self)
                return
            if not api_key:
                InfoBar.warning(tr("general.tip"), tr("config.fill_api_key_first"), duration=2000, parent=self)
                return

            self.fetch_models_btn.setEnabled(False)
            self.fetch_models_btn.setToolTip(tr("config.models_fetching"))
            QApplication.processEvents()

            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
                models_resp = client.models.list()
                models = sorted([m.id for m in models_resp.data])
                if models:
                    dialog = ModelSelectDialog(models, tr("config.select_model_title"), self)
                    if dialog.exec_() == QDialog.Accepted and dialog.selected_model:
                        self.model_id_input.setText(dialog.selected_model)
                        InfoBar.success(tr("general.success"),
                                        tr("config.models_fetched", default="已选择: {name}").format(name=dialog.selected_model),
                                        duration=2000, parent=self)
                else:
                    InfoBar.warning(tr("general.tip"), tr("config.no_models"), duration=2000, parent=self)
            except Exception as e:
                InfoBar.error(tr("general.error"),
                              tr("config.fetch_models_failed", default="获取失败: {error}").format(error=e),
                              duration=3000, parent=self)
            finally:
                self.fetch_models_btn.setEnabled(True)
                self.fetch_models_btn.setToolTip(tr("config.fetch_models"))
            return

        # TTS / IMAGE: 旧逻辑
        self._fetch_models_legacy_provider()

    def _fetch_models_legacy_provider(self):
        provider_type = self.provider_combo.currentData()
        if not provider_type:
            InfoBar.warning(tr("general.tip"), tr("config.select_ai_platform_hint", default="请先选择一个 AI 平台"), duration=2000, parent=self)
            return
        metadata = get_provider_metadata(provider_type)
        if not metadata or not metadata.cls_type:
            InfoBar.error(tr("general.error"), tr("config.cannot_get_provider_info", default="无法获取服务商信息"), duration=2000, parent=self)
            return
        config = ProviderConfig(
            id="temp_fetch", name="temp", type=provider_type,
            provider_type="chat_completion",
            api_key=self.api_key_input.text().strip(),
            base_url=self.base_url_input.text().strip(),
            model="", proxy=self.proxy_input.text().strip()
        )
        self.fetch_models_btn.setEnabled(False)
        QApplication.processEvents()
        provider = None
        try:
            provider = metadata.cls_type(config)
            models = provider.get_models()
            if models:
                dialog = ModelSelectDialog(models, tr("config.select_model", default="选择模型"), self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_model:
                    self.model_id_input.setText(dialog.selected_model)
            else:
                InfoBar.warning(tr("general.tip"), tr("config.no_models_found", default="未能获取到模型列表"), duration=3000, parent=self)
        except Exception as e:
            InfoBar.error(tr("general.error"), tr("config.fetch_failed", default="获取失败: {error}").format(error=e), duration=3000, parent=self)
        finally:
            if provider:
                try: provider.close()
                except: pass
            self.fetch_models_btn.setEnabled(True)

    def fetch_voices_from_provider(self):
        provider_type = self.provider_combo.currentData()
        if not provider_type:
            InfoBar.warning(tr("general.tip"), tr("config.select_voice_provider_hint", default="请先选择一个语音服务商"), duration=2000, parent=self)
            return
        metadata = get_provider_metadata(provider_type)
        if not metadata or not metadata.cls_type:
            InfoBar.error(tr("general.error"), tr("config.cannot_get_provider_info", default="无法获取服务商信息"), duration=2000, parent=self)
            return
        config = ProviderConfig(
            id="temp_fetch", name="temp", type=provider_type, provider_type="text_to_speech",
            api_key=self.api_key_input.text().strip(), base_url=self.base_url_input.text().strip(),
            model=self.model_id_input.text().strip(), proxy=self.proxy_input.text().strip()
        )
        self.fetch_voices_btn.setEnabled(False)
        QApplication.processEvents()
        provider = None
        try:
            provider = metadata.cls_type(config)
            voices_data = provider.get_voices()
            voices = [v.get("id", v.get("name", str(v))) if isinstance(v, dict) else str(v) for v in voices_data]
            if voices:
                dialog = ModelSelectDialog(voices, tr("config.select_voice", default="选择语音"), self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_model:
                    self.voice_input.setText(dialog.selected_model)
            else:
                InfoBar.warning(tr("general.tip"), tr("config.no_voices_found", default="未能获取到语音列表"), duration=3000, parent=self)
        except Exception as e:
            InfoBar.error(tr("general.error"), tr("config.fetch_failed", default="获取失败: {error}").format(error=e), duration=3000, parent=self)
        finally:
            if provider:
                try: provider.close()
                except: pass
            self.fetch_voices_btn.setEnabled(True)

    # ---------- 保存 / 删除 / 启用 ----------

    def save_model(self):
        name = self.name_input.text().strip() or tr("config.unnamed", default="未命名配置")
        provider = self.provider_combo.currentData() or ""
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model_name = self.model_id_input.text().strip()
        proxy = self.proxy_input.text().strip()

        if self.current_mode == "TTS":
            voice = self.voice_input.text().strip()
            api_name = self.api_name_input.text().strip() or "/tts_request"
            prompt_audio = self.prompt_audio_input.text().strip()
            prompt_text = self.prompt_text_input.text().strip()
            if self.current_model_id:
                self.db.update_tts_model(self.current_model_id, name, provider, api_key, base_url, model_name, voice, proxy, api_name, prompt_audio, prompt_text)
            else:
                self.current_model_id = self.db.add_tts_model(name, provider, api_key, base_url, model_name, voice, proxy, api_name, prompt_audio, prompt_text)
        elif self.current_mode == "IMAGE":
            if self.current_model_id:
                self.db.update_image_model(self.current_model_id, name, provider, base_url, api_key, model_name, proxy)
            else:
                self.current_model_id = self.db.add_image_model(name, provider, base_url, api_key, model_name, proxy)
        else:
            is_visual = 1 if self.chk_visual.isChecked() else 0
            is_thinking = 1 if self.chk_thinking.isChecked() else 0
            if self.current_model_id:
                self.db.update_model(self.current_model_id, name, provider, api_key, base_url, model_name, is_visual, is_thinking, proxy)
            else:
                self.current_model_id = self.db.add_model(name, provider, api_key, base_url, model_name, is_visual, is_thinking, proxy)

        self._reload_provider_manager()
        self._refresh_model_list_keep_selection()
        self.status_label.setText(tr("config.saved", default="已保存"))
        InfoBar.success(tr("config.save_success", default="保存成功"), tr("config.save_success_msg", default="配置 \"{name}\" 已保存").format(name=name), duration=2000, parent=self)

    def _reload_provider_manager(self):
        try:
            pm = ProviderManager.get_instance()
            pm.load_providers_from_db(self.db)
        except Exception as e:
            print(f"Warning: Failed to reload provider manager: {e}")

    def _refresh_model_list_keep_selection(self):
        saved_id = self.current_model_id
        self.model_list.clear()
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
        saved_item = None
        for m in models:
            item = QListWidgetItem(m[1], self.model_list)
            item.setData(Qt.UserRole, m[0])
            self.model_list.addItem(item)
            if m[0] == saved_id:
                saved_item = item
        if saved_item:
            self.model_list.setCurrentItem(saved_item)

    def delete_model(self):
        if not self.current_model_id: return
        name = self.name_input.text().strip() or tr("config.this_config", default="此配置")
        box = MessageBox(tr("general.confirm_delete", default="确认删除"), tr("config.confirm_delete_msg", default="确定要删除 \"{name}\" 吗？").format(name=name), self)
        box.yesButton.setText(tr("general.delete", default="删除"))
        box.cancelButton.setText(tr("general.cancel", default="取消"))
        if not box.exec_(): return
        if self.current_mode == "TTS":
            self.db.delete_tts_model(self.current_model_id)
        elif self.current_mode == "IMAGE":
            self.db.delete_image_model(self.current_model_id)
        else:
            self.db.delete_model(self.current_model_id)
        self.create_new_model()
        self.load_models()
        InfoBar.success(tr("config.deleted", default="已删除"), tr("config.deleted_msg", default="配置 \"{name}\" 已删除").format(name=name), duration=2000, parent=self)

    def set_active_model_handler(self):
        if not self.current_model_id: return
        name = self.name_input.text().strip() or tr("config.unnamed", default="未命名配置")
        if self.current_mode == "TTS":
            self.db.set_active_tts_model(self.current_model_id)
            InfoBar.success(tr("config.enabled", default="已启用"), tr("config.enabled_tts_msg", default="\"{name}\" 设为默认语音配置").format(name=name), duration=2500, parent=self)
        elif self.current_mode == "IMAGE":
            self.db.set_active_image_model(self.current_model_id)
            InfoBar.success(tr("config.enabled", default="已启用"), tr("config.enabled_image_msg", default="\"{name}\" 设为默认绘图配置").format(name=name), duration=2500, parent=self)
        else:
            self.db.set_active_model(self.current_model_id)
            InfoBar.success(tr("config.enabled", default="已启用"), tr("config.enabled_llm_msg", default="\"{name}\" 设为默认对话模型").format(name=name), duration=2500, parent=self)
        self._reload_provider_manager()
        self.load_models()

    def update_theme(self):
        pass


class QuickAddLegacyDialog(QDialog):
    """TTS / IMAGE 模式的快速添加对话框。"""

    def __init__(self, providers: list, mode: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("config.quick_add_title", default="快速添加配置"))
        self.setMinimumWidth(500)
        self.selected_provider = None
        self.api_key = ""
        self.config_name = ""
        self.providers = providers
        self.mode = mode
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel(tr("config.select_ai_platform", default="选择 AI 平台"), self))
        hint = CaptionLabel(tr("config.quick_add_desc", default="选择平台后，只需填入 API 密钥即可完成配置"), self)
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        provider_grid = QWidget(self)
        grid_layout = QVBoxLayout(provider_grid)
        grid_layout.setSpacing(8)
        self.provider_buttons = []
        for p in self.providers:
            btn = PushButton(p["name"], provider_grid)
            btn.setFixedHeight(40)
            btn.setToolTip(p.get("desc", ""))
            btn.clicked.connect(lambda checked, provider=p: self._select_provider(provider))
            self.provider_buttons.append((btn, p))
            grid_layout.addWidget(btn)
        layout.addWidget(provider_grid)

        self.api_section = QWidget(self)
        api_layout = QVBoxLayout(self.api_section)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(8)
        self.api_label = BodyLabel(tr("config.api_key_label", default="API 密钥"), self)
        api_layout.addWidget(self.api_label)
        self.api_input = LineEdit(self)
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText(tr("config.api_key_placeholder", default="粘贴您的 API Key..."))
        api_layout.addWidget(self.api_input)
        self.help_link = HyperlinkLabel(self)
        self.help_link.setText(tr("config.how_to_get", default="如何获取?"))
        api_layout.addWidget(self.help_link)
        self.api_section.setVisible(False)
        layout.addWidget(self.api_section)

        self.name_section = QWidget(self)
        name_layout = QVBoxLayout(self.name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        name_layout.addWidget(BodyLabel(tr("config.config_name_optional", default="配置名称 (可选)"), self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText(tr("config.default_platform_name", default="默认使用平台名称"))
        name_layout.addWidget(self.name_input)
        self.name_section.setVisible(False)
        layout.addWidget(self.name_section)

        layout.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _select_provider(self, provider: dict):
        self.selected_provider = provider
        for btn, p in self.provider_buttons:
            btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }" if p == provider else "")
        self.api_section.setVisible(True)
        self.name_section.setVisible(True)
        self.api_label.setText(tr("config.api_key_for_provider", default="{provider} API 密钥").format(provider=provider['name']))
        if provider.get("api_key_url"):
            self.help_link.setUrl(provider["api_key_url"])
            self.help_link.setVisible(True)
        else:
            self.help_link.setVisible(False)
        self.api_input.setFocus()

    def accept(self):
        if not self.selected_provider:
            InfoBar.warning(tr("general.tip"), tr("config.select_platform_hint", default="请先选择一个平台"), duration=2000, parent=self)
            return
        self.api_key = self.api_input.text().strip()
        self.config_name = self.name_input.text().strip()
        if not self.api_key:
            InfoBar.warning(tr("general.tip"), tr("config.enter_api_key", default="请输入 API 密钥"), duration=2000, parent=self)
            return
        super().accept()
