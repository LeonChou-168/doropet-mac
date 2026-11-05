"""
多语言国际化模块 (i18n / Internationalization)

支持动态切换语言，通过 JSON 翻译文件加载翻译。
通过 QSettings 持久化语言设置，使用 Signal 通知 UI 组件刷新。
"""

import json
import os
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from src.resource_utils import resource_path
from src.core.logger import logger

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "zh_CN": {"display": "中文（简体）", "flag": ""},
    "zh_TW": {"display": "中文（繁體）", "flag": ""},
    "en_US": {"display": "English (US)", "flag": ""},
    "ja_JP": {"display": "日本語", "flag": ""},
    "ko_KR": {"display": "한국어", "flag": ""},
}

TRANSLATION_DIR = resource_path("data/i18n")


class I18nManager(QObject):
    """多语言管理器（单例模式）。

    使用方式:
        i18n = I18nManager.get_instance()
        text = i18n.tr("settings.title")  # 返回当前语言的翻译文本
        i18n.languageChanged.connect(my_widget.refresh_ui)  # 监听语言切换
    """

    languageChanged = pyqtSignal(str)  # 参数: 新语言代码

    _instance = None

    @classmethod
    def get_instance(cls) -> "I18nManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        if I18nManager._instance is not None:
            raise RuntimeError("I18nManager is a singleton. Use get_instance() instead.")
        super().__init__(parent)
        self._translations: dict[str, dict] = {}  # {lang_code: {key: text}}
        self._current_lang = "zh_CN"
        self._loaded = False

    @property
    def current_language(self) -> str:
        return self._current_lang

    @property
    def languages(self) -> dict:
        return SUPPORTED_LANGUAGES

    def initialize(self) -> None:
        """从 QSettings 加载已保存的语言设置，加载翻译文件。"""
        if self._loaded:
            return
        settings = QSettings("DoroPet", "Settings")
        saved_lang = settings.value("language", "zh_CN")
        if saved_lang in SUPPORTED_LANGUAGES:
            self._current_lang = saved_lang
        else:
            self._current_lang = "zh_CN"
        self._load_all_translations()
        self._loaded = True
        logger.info(f"[I18n] Initialized with language: {self._current_lang}")

    def _load_all_translations(self) -> None:
        """加载所有语言的翻译文件。"""
        for lang_code in SUPPORTED_LANGUAGES:
            self._load_translation(lang_code)

    def _load_translation(self, lang_code: str) -> None:
        """加载指定语言的翻译 JSON 文件。"""
        file_path = os.path.join(TRANSLATION_DIR, f"{lang_code}.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
                logger.info(f"[I18n] Loaded translation: {lang_code} ({len(self._translations[lang_code])} keys)")
            else:
                logger.warning(f"[I18n] Translation file not found: {file_path}")
                self._translations[lang_code] = {}
        except Exception as e:
            logger.error(f"[I18n] Failed to load translation {lang_code}: {e}")
            self._translations[lang_code] = {}

    def tr(self, key: str, default: str = None) -> str:
        """翻译指定的键。

        Args:
            key: 翻译键，如 "settings.title"
            default: 未找到翻译时的默认文本

        Returns:
            翻译后的文本，若未找到则返回 default 或 key 本身
        """
        if not self._loaded:
            self.initialize()
        translations = self._translations.get(self._current_lang, {})
        value = translations.get(key)
        if value is None:
            return default if default is not None else key
        return value

    def set_language(self, lang_code: str) -> None:
        """切换当前语言。

        Args:
            lang_code: 语言代码，如 "zh_CN" 或 "en_US"
        """
        if lang_code not in SUPPORTED_LANGUAGES:
            logger.warning(f"[I18n] Unsupported language: {lang_code}")
            return
        if lang_code == self._current_lang:
            return
        self._current_lang = lang_code
        # 持久化到设置
        settings = QSettings("DoroPet", "Settings")
        settings.setValue("language", lang_code)
        logger.info(f"[I18n] Language switched to: {lang_code}, emitting languageChanged signal (receivers: {self.receivers(self.languageChanged)})")
        # 通知所有监听者刷新 UI
        self.languageChanged.emit(lang_code)
        logger.info(f"[I18n] languageChanged signal emitted")

    def get_current_display_name(self) -> str:
        """获取当前语言的显示名称。"""
        return SUPPORTED_LANGUAGES.get(self._current_lang, {}).get("display", self._current_lang)


# 便捷全局函数
def tr(key: str, default: str = None) -> str:
    """翻译键的全局快捷函数。"""
    return I18nManager.get_instance().tr(key, default)
