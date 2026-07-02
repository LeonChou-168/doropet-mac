from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import Protagonist
from src.core.i18n import I18nManager, tr


class ProtagonistDialog(QDialog):
    def __init__(self, protagonist: Optional[Protagonist] = None, parent=None):
        super().__init__(parent)
        self._protagonist = protagonist or Protagonist()
        self.setWindowTitle(tr("galgame.dialog.protagonist.title", default="主角配置"))
        self.setMinimumSize(450, 400)
        self.init_ui()
        self._load_data()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.title_label = TitleLabel(tr("galgame.dialog.protagonist.title", default="主角配置"), self)
        layout.addWidget(self.title_label)

        self.name_label = BodyLabel(tr("galgame.dialog.protagonist.name_label", default="主角名称"), self)
        layout.addWidget(self.name_label)
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText(tr("galgame.dialog.protagonist.name_placeholder", default="输入主角名称"))
        layout.addWidget(self.name_input)

        self.personality_label = BodyLabel(tr("galgame.dialog.protagonist.personality_label", default="性格描述"), self)
        layout.addWidget(self.personality_label)
        self.personality_input = PlainTextEdit(self)
        self.personality_input.setPlaceholderText(tr("galgame.dialog.protagonist.personality_placeholder", default="描述主角的性格特点，如：勇敢、善良、有些内向..."))
        self.personality_input.setMaximumHeight(80)
        layout.addWidget(self.personality_input)

        self.background_label = BodyLabel(tr("galgame.dialog.protagonist.background_label", default="背景故事"), self)
        layout.addWidget(self.background_label)
        self.background_input = PlainTextEdit(self)
        self.background_input.setPlaceholderText(tr("galgame.dialog.protagonist.background_placeholder", default="描述主角的背景故事..."))
        self.background_input.setMaximumHeight(100)
        layout.addWidget(self.background_input)

        self.traits_label = BodyLabel(tr("galgame.dialog.protagonist.traits_label", default="特殊特点 (用逗号分隔)"), self)
        layout.addWidget(self.traits_label)
        self.traits_input = LineEdit(self)
        self.traits_input.setPlaceholderText(tr("galgame.dialog.protagonist.traits_placeholder", default="如：善于观察, 有领导力, 擅长魔法"))
        layout.addWidget(self.traits_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = PushButton(tr("galgame.dialog.protagonist.cancel", default="取消"), self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("galgame.dialog.protagonist.save", default="保存"), self)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.update_theme()

    def _load_data(self):
        self.name_input.setText(self._protagonist.name)
        self.personality_input.setPlainText(self._protagonist.personality)
        self.background_input.setPlainText(self._protagonist.background)
        self.traits_input.setText(", ".join(self._protagonist.traits))

    def _save(self):
        self._protagonist.name = self.name_input.text().strip() or tr("galgame.dialog.protagonist.default_name", default="主角")
        self._protagonist.personality = self.personality_input.toPlainText().strip()
        self._protagonist.background = self.background_input.toPlainText().strip()

        traits_text = self.traits_input.text().strip()
        self._protagonist.traits = [
            t.strip() for t in traits_text.split(",") if t.strip()
        ]

        self.accept()

    def get_protagonist(self) -> Protagonist:
        return self._protagonist

    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.dialog.protagonist.title", default="主角配置"))
        self.title_label.setText(tr("galgame.dialog.protagonist.title", default="主角配置"))
        self.name_label.setText(tr("galgame.dialog.protagonist.name_label", default="主角名称"))
        self.name_input.setPlaceholderText(tr("galgame.dialog.protagonist.name_placeholder", default="输入主角名称"))
        self.personality_label.setText(tr("galgame.dialog.protagonist.personality_label", default="性格描述"))
        self.personality_input.setPlaceholderText(tr("galgame.dialog.protagonist.personality_placeholder", default="描述主角的性格特点，如：勇敢、善良、有些内向..."))
        self.background_label.setText(tr("galgame.dialog.protagonist.background_label", default="背景故事"))
        self.background_input.setPlaceholderText(tr("galgame.dialog.protagonist.background_placeholder", default="描述主角的背景故事..."))
        self.traits_label.setText(tr("galgame.dialog.protagonist.traits_label", default="特殊特点 (用逗号分隔)"))
        self.traits_input.setPlaceholderText(tr("galgame.dialog.protagonist.traits_placeholder", default="如：善于观察, 有领导力, 擅长魔法"))
        self.cancel_btn.setText(tr("galgame.dialog.protagonist.cancel", default="取消"))
        self.save_btn.setText(tr("galgame.dialog.protagonist.save", default="保存"))

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
