from typing import Optional
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import WorldSetting
from src.core.i18n import I18nManager, tr


class WorldDialog(QDialog):
    def __init__(self, world_setting: Optional[WorldSetting] = None, parent=None):
        super().__init__(parent)
        self._world_setting = world_setting or WorldSetting()
        self.setWindowTitle(tr("galgame.dialog.world.title", default="世界观配置"))
        self.setMinimumSize(500, 520)
        self.init_ui()
        self._load_data()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.title_label = TitleLabel(tr("galgame.dialog.world.title", default="世界观配置"), self)
        layout.addWidget(self.title_label)

        self.name_label = BodyLabel(tr("galgame.dialog.world.name_label", default="世界名称"), self)
        layout.addWidget(self.name_label)
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText(tr("galgame.dialog.world.name_placeholder", default="如：魔法学院、未来都市、奇幻大陆..."))
        layout.addWidget(self.name_input)

        self.era_label = BodyLabel(tr("galgame.dialog.world.era_label", default="时代背景"), self)
        layout.addWidget(self.era_label)
        self.era_input = LineEdit(self)
        self.era_input.setPlaceholderText(tr("galgame.dialog.world.era_placeholder", default="如：中世纪、现代、未来、架空..."))
        layout.addWidget(self.era_input)

        self.rules_label = BodyLabel(tr("galgame.dialog.world.rules_label", default="世界规则/设定"), self)
        layout.addWidget(self.rules_label)
        self.rules_input = PlainTextEdit(self)
        self.rules_input.setPlaceholderText(
            tr("galgame.dialog.world.rules_placeholder", default="描述这个世界的基本规则和设定...\n例如：这是一个魔法与科技共存的世界，人们通过魔力水晶获得魔法力量...")
        )
        self.rules_input.setMaximumHeight(100)
        layout.addWidget(self.rules_input)

        self.elements_label = BodyLabel(tr("galgame.dialog.world.elements_label", default="特殊元素 (用逗号分隔)"), self)
        layout.addWidget(self.elements_label)
        self.elements_input = LineEdit(self)
        self.elements_input.setPlaceholderText(tr("galgame.dialog.world.elements_placeholder", default="如：魔法, 魔物, 神秘遗迹, 古老预言"))
        layout.addWidget(self.elements_input)

        self.style_label = BodyLabel(tr("galgame.dialog.world.style_label", default="写作风格"), self)
        layout.addWidget(self.style_label)
        self.style_input = LineEdit(self)
        self.style_input.setPlaceholderText(tr("galgame.dialog.world.style_placeholder", default="如：轻松幽默、沉重悲伤、浪漫甜蜜..."))
        self.style_input.setReadOnly(True)
        layout.addWidget(self.style_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = PushButton(tr("galgame.dialog.world.cancel", default="取消"), self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("galgame.dialog.world.save", default="保存"), self)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.update_theme()

    def _load_data(self):
        self.name_input.setText(self._world_setting.name)
        self.era_input.setText(self._world_setting.era)
        self.rules_input.setPlainText(self._world_setting.rules)
        self.elements_input.setText(", ".join(self._world_setting.special_elements))
        self.style_input.setText(self._world_setting.writing_style)

    def _save(self):
        self._world_setting.name = self.name_input.text().strip() or tr("galgame.dialog.world.default_name", default="未知世界")
        self._world_setting.era = self.era_input.text().strip() or tr("galgame.dialog.world.default_era", default="未知时代")
        self._world_setting.rules = self.rules_input.toPlainText().strip()

        elements_text = self.elements_input.text().strip()
        self._world_setting.special_elements = [
            e.strip() for e in elements_text.split(",") if e.strip()
        ]

        self.accept()

    def get_world_setting(self) -> WorldSetting:
        return self._world_setting

    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.dialog.world.title", default="世界观配置"))
        self.title_label.setText(tr("galgame.dialog.world.title", default="世界观配置"))
        self.name_label.setText(tr("galgame.dialog.world.name_label", default="世界名称"))
        self.name_input.setPlaceholderText(tr("galgame.dialog.world.name_placeholder", default="如：魔法学院、未来都市、奇幻大陆..."))
        self.era_label.setText(tr("galgame.dialog.world.era_label", default="时代背景"))
        self.era_input.setPlaceholderText(tr("galgame.dialog.world.era_placeholder", default="如：中世纪、现代、未来、架空..."))
        self.rules_label.setText(tr("galgame.dialog.world.rules_label", default="世界规则/设定"))
        self.rules_input.setPlaceholderText(tr("galgame.dialog.world.rules_placeholder", default="描述这个世界的基本规则和设定...\n例如：这是一个魔法与科技共存的世界，人们通过魔力水晶获得魔法力量..."))
        self.elements_label.setText(tr("galgame.dialog.world.elements_label", default="特殊元素 (用逗号分隔)"))
        self.elements_input.setPlaceholderText(tr("galgame.dialog.world.elements_placeholder", default="如：魔法, 魔物, 神秘遗迹, 古老预言"))
        self.style_label.setText(tr("galgame.dialog.world.style_label", default="写作风格"))
        self.style_input.setPlaceholderText(tr("galgame.dialog.world.style_placeholder", default="如：轻松幽默、沉重悲伤、浪漫甜蜜..."))
        self.cancel_btn.setText(tr("galgame.dialog.world.cancel", default="取消"))
        self.save_btn.setText(tr("galgame.dialog.world.save", default="保存"))

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
