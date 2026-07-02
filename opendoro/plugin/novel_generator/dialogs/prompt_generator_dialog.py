from typing import Optional, Dict, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    PushButton, PrimaryPushButton,
    TitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
    PlainTextEdit, InfoBar, InfoBarPosition,
    isDarkTheme, ProgressBar, CardWidget
)

from ..prompt_generator import (
    GENRE_CATEGORIES, WRITING_STYLES, PromptGenerator
)
from ..models import Protagonist, Character, WorldSetting
from src.core.i18n import I18nManager, tr


class GenreCard(CardWidget):
    def __init__(self, genre_id: str, genre_info: Dict, parent=None):
        super().__init__(parent)
        self.genre_id = genre_id
        self._is_selected = False
        self.init_ui(genre_info)
    
    def init_ui(self, genre_info: Dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        name_label = StrongBodyLabel(genre_info['name'], self)
        layout.addWidget(name_label, alignment=Qt.AlignCenter)
        
        desc_label = CaptionLabel(genre_info['description'], self)
        desc_label.setWordWrap(True)
        desc_label.setMaximumWidth(120)
        layout.addWidget(desc_label, alignment=Qt.AlignCenter)
        
        self.setMinimumSize(130, 80)
        self.update_theme()
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update_theme()
    
    def is_selected(self) -> bool:
        return self._is_selected
    
    def update_theme(self):
        is_dark = isDarkTheme()
        if self._is_selected:
            bg_color = "#0078d4"
            text_color = "#ffffff"
            border_color = "#0078d4"
        else:
            bg_color = "#3a3a3a" if is_dark else "#f5f5f5"
            text_color = "#e0e0e0" if is_dark else "#333333"
            border_color = "#505050" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            GenreCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)


class StyleCard(CardWidget):
    def __init__(self, style_id: str, style_info: Dict, parent=None):
        super().__init__(parent)
        self.style_id = style_id
        self._is_selected = False
        self.init_ui(style_info)
    
    def init_ui(self, style_info: Dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        name_label = StrongBodyLabel(style_info['name'], self)
        layout.addWidget(name_label, alignment=Qt.AlignCenter)
        
        keywords = ', '.join(style_info.get('keywords', [])[:3])
        keyword_label = CaptionLabel(keywords, self)
        layout.addWidget(keyword_label, alignment=Qt.AlignCenter)
        
        self.setMinimumSize(120, 70)
        self.update_theme()
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update_theme()
    
    def is_selected(self) -> bool:
        return self._is_selected
    
    def update_theme(self):
        is_dark = isDarkTheme()
        if self._is_selected:
            bg_color = "#0078d4"
            text_color = "#ffffff"
            border_color = "#0078d4"
        else:
            bg_color = "#3a3a3a" if is_dark else "#f5f5f5"
            text_color = "#e0e0e0" if is_dark else "#333333"
            border_color = "#505050" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            StyleCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)


class PromptGeneratorDialog(QDialog):
    config_generated = pyqtSignal(object, object, object)
    
    def __init__(self, provider_manager, parent=None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        self._selected_genre = None
        self._selected_style = None
        self._generated_config = None
        self._prompt_generator = PromptGenerator(provider_manager)
        self._generation_worker = None
        
        self.setWindowTitle(tr("galgame.prompt_generator.title", default="✨ 智能生成配置"))
        self.setMinimumSize(700, 750)
        self.init_ui()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        
        self.title = TitleLabel(tr("galgame.prompt_generator.main_title", default="✨ 智能生成 Galgame 配置"), self)
        main_layout.addWidget(self.title)
        
        self.genre_label = StrongBodyLabel(tr("galgame.prompt_generator.genre_label", default="📚 选择题材分类"), self)
        main_layout.addWidget(self.genre_label)
        self.genre_scroll = self._create_genre_selection()
        main_layout.addWidget(self.genre_scroll)
        
        self.style_label = StrongBodyLabel(tr("galgame.prompt_generator.style_label", default="✒️ 选择写作风格"), self)
        main_layout.addWidget(self.style_label)
        self.style_scroll = self._create_style_selection()
        main_layout.addWidget(self.style_scroll)
        
        self.requirements_label = BodyLabel(tr("galgame.prompt_generator.requirements_label", default="💡 额外要求（可选）"), self)
        main_layout.addWidget(self.requirements_label)
        self.requirements_input = PlainTextEdit(self)
        self.requirements_input.setPlaceholderText(tr("galgame.prompt_generator.requirements_placeholder", default="例如：主角应该是女性，包含魔法战斗，有3个角色..."))
        self.requirements_input.setMaximumHeight(60)
        main_layout.addWidget(self.requirements_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton(tr("galgame.prompt_generator.cancel", default="取消"), self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.generate_btn = PrimaryPushButton(tr("galgame.prompt_generator.generate", default="✨ 开始生成"), self)
        self.generate_btn.clicked.connect(self._start_generation)
        btn_layout.addWidget(self.generate_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.preview_widget = QWidget()
        self.preview_widget.setVisible(False)
        self.preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.preview_widget)
        
        self.preview_actions_widget = QWidget()
        self.preview_actions_widget.setVisible(False)
        self.preview_actions_layout = QHBoxLayout(self.preview_actions_widget)
        self.preview_actions_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.preview_actions_widget)
        
        self.regenerate_btn = PushButton(tr("galgame.prompt_generator.regenerate", default="🔄 重新生成"), self)
        self.regenerate_btn.clicked.connect(self._reset_to_generation)
        self.preview_actions_layout.addWidget(self.regenerate_btn)
        
        self.apply_btn = PrimaryPushButton(tr("galgame.prompt_generator.apply", default="✓ 应用配置"), self)
        self.apply_btn.clicked.connect(self._apply_config)
        self.preview_actions_layout.addWidget(self.apply_btn)
        
        self.preview_actions_layout.addStretch()
        
        self.update_theme()
    
    def _create_genre_selection(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.genre_cards = []
        genres = list(GENRE_CATEGORIES.items())
        
        for idx, (genre_id, genre_info) in enumerate(genres):
            row = idx // 5
            col = idx % 5
            card = GenreCard(genre_id, genre_info, self)
            card.mousePressEvent = lambda event, c=card: self._on_genre_selected(c)
            layout.addWidget(card, row, col)
            self.genre_cards.append(card)
        
        layout.setRowStretch((len(genres) + 4) // 5, 1)
        scroll.setWidget(container)
        return scroll
    
    def _create_style_selection(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(140)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.style_cards = []
        styles = list(WRITING_STYLES.items())
        
        for idx, (style_id, style_info) in enumerate(styles):
            row = idx // 5
            col = idx % 5
            card = StyleCard(style_id, style_info, self)
            card.mousePressEvent = lambda event, c=card: self._on_style_selected(c)
            layout.addWidget(card, row, col)
            self.style_cards.append(card)
        
        layout.setRowStretch((len(styles) + 4) // 5, 1)
        scroll.setWidget(container)
        return scroll
    
    def _on_genre_selected(self, card: GenreCard):
        for c in self.genre_cards:
            c.set_selected(False)
        card.set_selected(True)
        self._selected_genre = card.genre_id
    
    def _on_style_selected(self, card: StyleCard):
        for c in self.style_cards:
            c.set_selected(False)
        card.set_selected(True)
        self._selected_style = card.style_id
    
    def _start_generation(self):
        if not self._selected_genre:
            InfoBar.warning(
                tr("galgame.prompt_generator.hint_title", default="提示"),
                tr("galgame.prompt_generator.hint_select_genre", default="请选择题材分类"),
                parent=self, duration=2000
            )
            return
        
        if not self._selected_style:
            InfoBar.warning(
                tr("galgame.prompt_generator.hint_title", default="提示"),
                tr("galgame.prompt_generator.hint_select_style", default="请选择写作风格"),
                parent=self, duration=2000
            )
            return
        
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText(tr("galgame.prompt_generator.generating", default="⏳ 生成中..."))
        
        self.progress_bar = ProgressBar(self)
        self.layout().insertWidget(self.layout().count() - 2, self.progress_bar)
        self.progress_bar.setRange(0, 0)
        
        custom_requirements = self.requirements_input.toPlainText().strip()
        
        model_id = self._get_current_model_id()
        
        self._generation_worker = self._prompt_generator.generate_config(
            self._selected_genre,
            self._selected_style,
            custom_requirements,
            model_id
        )
        
        self._generation_worker.generation_complete.connect(self._on_generation_complete)
        self._generation_worker.error_occurred.connect(self._on_generation_error)
        self._generation_worker.start()
    
    def _get_current_model_id(self) -> Optional[str]:
        parent = self.parent()
        model_id = None
        
        # 优先从 top_panel 的下拉框获取当前实际选中的模型
        if parent and hasattr(parent, 'top_panel'):
            model_id = parent.top_panel.get_current_model_id()
        
        # 如果 top_panel 没有，再从 _current_model_id 获取
        if not model_id and parent and hasattr(parent, '_current_model_id'):
            model_id = parent._current_model_id
        
        return model_id
    
    def _on_generation_complete(self, result: Dict):
        self._generated_config = result
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        
        self.generate_btn.setVisible(False)
        
        self._show_preview(result)
    
    def _on_generation_error(self, error: str):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText(tr("galgame.prompt_generator.generate", default="✨ 开始生成"))
        
        InfoBar.error(
            tr("galgame.prompt_generator.generate_failed", default="生成失败"),
            error,
            parent=self, duration=5000
        )
    
    def _show_preview(self, result: Dict):
        self.preview_widget.setVisible(True)
        self.preview_actions_widget.setVisible(True)
        
        for i in reversed(range(self.preview_layout.count())):
            widget = self.preview_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        genre_info = GENRE_CATEGORIES.get(self._selected_genre, {})
        style_info = WRITING_STYLES.get(self._selected_style, {})
        
        genre_prefix = tr("galgame.prompt_generator.genre_prefix", default="题材: ")
        style_prefix = tr("galgame.prompt_generator.style_prefix", default="风格: ")
        header_layout = QHBoxLayout()
        header_layout.addWidget(BodyLabel(f"{genre_prefix}{genre_info.get('name', self._selected_genre)}"))
        header_layout.addWidget(BodyLabel(f"{style_prefix}{style_info.get('name', self._selected_style)}"))
        self.preview_layout.addLayout(header_layout)
        
        unknown = tr("galgame.prompt_generator.unknown", default="未知")
        none_val = tr("galgame.prompt_generator.none", default="无")
        
        protagonist = result.get('protagonist', {})
        protagonist_label = StrongBodyLabel(tr("galgame.prompt_generator.protagonist_label", default="👤 主角设定"), self)
        self.preview_layout.addWidget(protagonist_label)
        
        name_prefix = tr("galgame.prompt_generator.name_prefix", default="名称: ")
        personality_prefix = tr("galgame.prompt_generator.personality_prefix", default="性格: ")
        background_prefix = tr("galgame.prompt_generator.background_prefix", default="背景: ")
        traits_prefix = tr("galgame.prompt_generator.traits_prefix", default="特点: ")
        
        protagonist_text = (
            f"{name_prefix}{protagonist.get('name', unknown)}\n"
            f"{personality_prefix}{protagonist.get('personality', none_val)}\n"
            f"{background_prefix}{protagonist.get('background', none_val)}\n"
            f"{traits_prefix}{', '.join(protagonist.get('traits', []))}"
        )
        self.preview_layout.addWidget(BodyLabel(protagonist_text, self))
        
        characters = result.get('characters', [])
        characters_label = StrongBodyLabel(tr("galgame.prompt_generator.characters_label", default="👥 角色设定"), self)
        self.preview_layout.addWidget(characters_label)
        char_prefix = tr("galgame.prompt_generator.character_prefix", default="【角色{idx}: {name}】")
        for idx, char in enumerate(characters, 1):
            char_name = char.get('name', unknown)
            char_text = (
                f"{char_prefix.format(idx=idx, name=char_name)}\n"
                f"  {personality_prefix}{char.get('personality', none_val)}\n"
                f"  {background_prefix}{char.get('background', none_val)}\n"
                f"  {tr('galgame.prompt_generator.initial_affection_prefix', default='初始好感度: ')}{char.get('initial_affection', 50)} | {tr('galgame.prompt_generator.relationship_prefix', default='关系: ')}{char.get('relationship', unknown)}"
            )
            self.preview_layout.addWidget(BodyLabel(char_text, self))
        
        world = result.get('world_setting', {})
        world_label = StrongBodyLabel(tr("galgame.prompt_generator.world_label", default="🌍 世界观设定"), self)
        self.preview_layout.addWidget(world_label)
        era_prefix = tr("galgame.prompt_generator.era_prefix", default="时代: ")
        rules_prefix = tr("galgame.prompt_generator.rules_prefix", default="规则: ")
        special_prefix = tr("galgame.prompt_generator.special_prefix", default="特殊元素: ")
        world_text = (
            f"{name_prefix}{world.get('name', unknown)}\n"
            f"{era_prefix}{world.get('era', none_val)}\n"
            f"{rules_prefix}{world.get('rules', none_val)}\n"
            f"{special_prefix}{', '.join(world.get('special_elements', []))}"
        )
        self.preview_layout.addWidget(BodyLabel(world_text, self))
        
        self.preview_layout.addStretch()
    
    def _reset_to_generation(self):
        self.preview_widget.setVisible(False)
        self.preview_actions_widget.setVisible(False)
        self.generate_btn.setVisible(True)
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText(tr("galgame.prompt_generator.generate", default="✨ 开始生成"))
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(True)
    
    def _apply_config(self):
        if not self._generated_config:
            return
        
        try:
            protagonist, characters, world_setting = PromptGenerator.parse_generated_config(
                self._generated_config
            )
            
            self.config_generated.emit(protagonist, characters, world_setting)
            
            InfoBar.success(
                tr("galgame.prompt_generator.apply_success_title", default="成功"),
                tr("galgame.prompt_generator.apply_success_content", default="配置已应用！"),
                parent=self, duration=2000
            )
            self.accept()
        except Exception as e:
            InfoBar.error(
                tr("galgame.prompt_generator.apply_failed", default="应用失败"),
                str(e),
                parent=self, duration=5000
            )
    
    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.prompt_generator.title", default="✨ 智能生成配置"))
        self.title.setText(tr("galgame.prompt_generator.main_title", default="✨ 智能生成 Galgame 配置"))
        self.genre_label.setText(tr("galgame.prompt_generator.genre_label", default="📚 选择题材分类"))
        self.style_label.setText(tr("galgame.prompt_generator.style_label", default="✒️ 选择写作风格"))
        self.requirements_label.setText(tr("galgame.prompt_generator.requirements_label", default="💡 额外要求（可选）"))
        self.requirements_input.setPlaceholderText(tr("galgame.prompt_generator.requirements_placeholder", default="例如：主角应该是女性，包含魔法战斗，有3个角色..."))
        self.cancel_btn.setText(tr("galgame.prompt_generator.cancel", default="取消"))
        self.generate_btn.setText(tr("galgame.prompt_generator.generate", default="✨ 开始生成"))
        self.regenerate_btn.setText(tr("galgame.prompt_generator.regenerate", default="🔄 重新生成"))
        self.apply_btn.setText(tr("galgame.prompt_generator.apply", default="✓ 应用配置"))
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#e0e0e0" if is_dark else "#333333"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
