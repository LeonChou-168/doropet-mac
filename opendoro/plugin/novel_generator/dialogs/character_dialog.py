from typing import List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpinBox
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    ListWidget, LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import Character
from src.core.i18n import I18nManager, tr


class CharacterDialog(QDialog):
    def __init__(self, characters: Optional[List[Character]] = None, parent=None):
        super().__init__(parent)
        self._characters = characters or []
        self._current_character = None
        self._current_item = None  # 当前正在编辑的列表项
        self.setWindowTitle(tr("galgame.dialog.character.title", default="角色配置"))
        self.setMinimumSize(600, 500)
        self.init_ui()
        self._load_data()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        left_panel = QFrame(self)
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(180)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.char_list_label = BodyLabel(tr("galgame.dialog.character.char_list", default="角色列表"), self)
        left_layout.addWidget(self.char_list_label)

        self.character_list = ListWidget(self)
        self.character_list.setWrapping(True)
        self.character_list.itemClicked.connect(self._on_character_selected)
        left_layout.addWidget(self.character_list)

        self.add_btn = PushButton(FluentIcon.ADD, tr("galgame.dialog.character.add", default="添加角色"), self)
        self.add_btn.clicked.connect(self._add_character)
        left_layout.addWidget(self.add_btn)

        self.delete_btn = PushButton(FluentIcon.DELETE, tr("galgame.dialog.character.delete", default="删除角色"), self)
        self.delete_btn.clicked.connect(self._delete_character)
        left_layout.addWidget(self.delete_btn)

        layout.addWidget(left_panel)

        right_panel = QFrame(self)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.detail_title = TitleLabel(tr("galgame.dialog.character.detail_title", default="角色详情"), self)
        right_layout.addWidget(self.detail_title)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        self.name_label = BodyLabel(tr("galgame.dialog.character.name_label", default="角色名称 *"), self)
        form_layout.addWidget(self.name_label)
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText(tr("galgame.dialog.character.name_placeholder", default="角色名称"))
        form_layout.addWidget(self.name_input)

        self.personality_label = BodyLabel(tr("galgame.dialog.character.personality_label", default="性格描述"), self)
        form_layout.addWidget(self.personality_label)
        self.personality_input = PlainTextEdit(self)
        self.personality_input.setPlaceholderText(tr("galgame.dialog.character.personality_placeholder", default="描述角色的性格特点..."))
        self.personality_input.setMaximumHeight(60)
        form_layout.addWidget(self.personality_input)

        self.background_label = BodyLabel(tr("galgame.dialog.character.background_label", default="背景故事"), self)
        form_layout.addWidget(self.background_label)
        self.background_input = PlainTextEdit(self)
        self.background_input.setPlaceholderText(tr("galgame.dialog.character.background_placeholder", default="角色的背景故事..."))
        self.background_input.setMaximumHeight(80)
        form_layout.addWidget(self.background_input)

        aff_layout = QHBoxLayout()
        self.affection_label = BodyLabel(tr("galgame.dialog.character.affection_label", default="初始好感度:"), self)
        aff_layout.addWidget(self.affection_label)
        self.affection_spin = QSpinBox(self)
        self.affection_spin.setRange(0, 100)
        self.affection_spin.setValue(50)
        aff_layout.addWidget(self.affection_spin)
        aff_layout.addStretch()
        form_layout.addLayout(aff_layout)

        self.relationship_label = BodyLabel(tr("galgame.dialog.character.relationship_label", default="与主角关系"), self)
        form_layout.addWidget(self.relationship_label)
        self.relationship_input = LineEdit(self)
        self.relationship_input.setPlaceholderText(tr("galgame.dialog.character.relationship_placeholder", default="如：陌生人、同学、青梅竹马..."))
        form_layout.addWidget(self.relationship_input)

        right_layout.addLayout(form_layout)
        right_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = PushButton(tr("galgame.dialog.character.cancel", default="取消"), self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("galgame.dialog.character.save", default="保存"), self)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        right_layout.addLayout(btn_layout)

        layout.addWidget(right_panel)

        self.update_theme()

    def _load_data(self):
        self.character_list.clear()
        for idx, char in enumerate(self._characters):
            self.character_list.addItem(char.name)
            item = self.character_list.item(idx)
            item.setData(Qt.UserRole, char)

        if self._characters:
            self.character_list.setCurrentRow(0)
            self._on_character_selected(self.character_list.item(0))

    def _on_character_selected(self, item):
        # 先保存当前编辑的角色数据
        self._save_current_character()

        # 然后加载新选中的角色
        char = item.data(Qt.UserRole)
        self._current_character = char
        self._current_item = item  # 记录当前编辑的列表项

        self.name_input.setText(char.name)
        self.personality_input.setPlainText(char.personality)
        self.background_input.setPlainText(char.background)
        self.affection_spin.setValue(char.initial_affection)
        self.relationship_input.setText(char.relationship)

    def _add_character(self):
        self._save_current_character()

        new_char = Character(name=tr("galgame.dialog.character.new_char_name", default="新角色") + str(len(self._characters) + 1))
        self._characters.append(new_char)

        self.character_list.addItem(new_char.name)
        idx = self.character_list.count() - 1
        item = self.character_list.item(idx)
        item.setData(Qt.UserRole, new_char)
        self.character_list.setCurrentRow(idx)
        self._current_character = new_char
        self._current_item = item  # 记录新添加的列表项

        self.name_input.setText(new_char.name)
        self.personality_input.clear()
        self.background_input.clear()
        self.affection_spin.setValue(50)
        self.relationship_input.clear()

    def _delete_character(self):
        current_item = self.character_list.currentItem()
        if not current_item:
            return

        char = current_item.data(Qt.UserRole)
        if char in self._characters:
            self._characters.remove(char)

        self.character_list.takeItem(self.character_list.row(current_item))
        self._current_character = None
        self._current_item = None  # 清除当前编辑的列表项引用

        if self.character_list.count() > 0:
            self.character_list.setCurrentRow(0)
            self._on_character_selected(self.character_list.item(0))
        else:
            self.name_input.clear()
            self.personality_input.clear()
            self.background_input.clear()
            self.affection_spin.setValue(50)
            self.relationship_input.clear()

    def _save_current_character(self):
        if self._current_character is None:
            return

        self._current_character.name = self.name_input.text().strip() or tr("galgame.dialog.character.default_name", default="未命名角色")
        self._current_character.personality = self.personality_input.toPlainText().strip()
        self._current_character.background = self.background_input.toPlainText().strip()
        self._current_character.initial_affection = self.affection_spin.value()
        self._current_character.relationship = self.relationship_input.text().strip() or tr("galgame.dialog.character.default_relationship", default="陌生人")

        # 更新当前编辑的列表项（使用保存的引用，而不是 currentItem()）
        if self._current_item:
            self._current_item.setText(self._current_character.name)
            self._current_item.setData(Qt.UserRole, self._current_character)

    def _save(self):
        self._save_current_character()
        self.accept()

    def get_characters(self) -> List[Character]:
        return self._characters

    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.dialog.character.title", default="角色配置"))
        self.char_list_label.setText(tr("galgame.dialog.character.char_list", default="角色列表"))
        self.add_btn.setText(tr("galgame.dialog.character.add", default="添加角色"))
        self.delete_btn.setText(tr("galgame.dialog.character.delete", default="删除角色"))
        self.detail_title.setText(tr("galgame.dialog.character.detail_title", default="角色详情"))
        self.name_label.setText(tr("galgame.dialog.character.name_label", default="角色名称 *"))
        self.name_input.setPlaceholderText(tr("galgame.dialog.character.name_placeholder", default="角色名称"))
        self.personality_label.setText(tr("galgame.dialog.character.personality_label", default="性格描述"))
        self.personality_input.setPlaceholderText(tr("galgame.dialog.character.personality_placeholder", default="描述角色的性格特点..."))
        self.background_label.setText(tr("galgame.dialog.character.background_label", default="背景故事"))
        self.background_input.setPlaceholderText(tr("galgame.dialog.character.background_placeholder", default="角色的背景故事..."))
        self.affection_label.setText(tr("galgame.dialog.character.affection_label", default="初始好感度:"))
        self.relationship_label.setText(tr("galgame.dialog.character.relationship_label", default="与主角关系"))
        self.relationship_input.setPlaceholderText(tr("galgame.dialog.character.relationship_placeholder", default="如：陌生人、同学、青梅竹马..."))
        self.cancel_btn.setText(tr("galgame.dialog.character.cancel", default="取消"))
        self.save_btn.setText(tr("galgame.dialog.character.save", default="保存"))

    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        panel_bg = "#3d3d3d" if is_dark else "#f5f5f5"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#404040" if is_dark else "#e0e0e0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            #leftPanel, #rightPanel {{
                background-color: {panel_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
            }}
            QListWidget::item:selected {{
                background-color: #0078d4;
                color: #ffffff;
            }}
            QListWidget::item:hover {{
                background-color: #3a3a3a;
            }}
        """)
