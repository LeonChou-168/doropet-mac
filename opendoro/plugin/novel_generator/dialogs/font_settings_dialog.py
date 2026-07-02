from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    TitleLabel, BodyLabel, SpinBox, PrimaryPushButton, PushButton,
    FluentIcon, isDarkTheme
)
from src.core.i18n import I18nManager, tr


class FontSettingsDialog(QDialog):
    font_changed = pyqtSignal(int, int)

    def __init__(self, parent=None, story_size: int = 14, title_size: int = 16):
        super().__init__(parent)
        self._story_size = story_size
        self._title_size = title_size
        self.setWindowTitle(tr("galgame.dialog.font.title", default="字体设置"))
        self.setMinimumSize(450, 380)
        self.init_ui()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.title_label = TitleLabel(tr("galgame.dialog.font.size_title", default="字体大小设置"), self)
        layout.addWidget(self.title_label)

        story_layout = QHBoxLayout()
        self.story_label = BodyLabel(tr("galgame.dialog.font.story_label", default="故事正文:"), self)
        self.story_label.setFixedWidth(70)
        story_layout.addWidget(self.story_label)

        self.story_spin = SpinBox(self)
        self.story_spin.setRange(10, 24)
        self.story_spin.setValue(self._story_size)
        self.story_spin.setFixedWidth(110)
        story_layout.addWidget(self.story_spin)

        self.story_hint = BodyLabel(tr("galgame.dialog.font.story_hint", default="px (推荐: 14-16)"), self)
        self.story_hint.setStyleSheet("color: #7f8c8d;")
        story_layout.addWidget(self.story_hint)
        story_layout.addStretch()
        layout.addLayout(story_layout)

        title_font_layout = QHBoxLayout()
        self.title_font_label = BodyLabel(tr("galgame.dialog.font.title_label", default="章节标题:"), self)
        self.title_font_label.setFixedWidth(70)
        title_font_layout.addWidget(self.title_font_label)

        self.title_spin = SpinBox(self)
        self.title_spin.setRange(12, 28)
        self.title_spin.setValue(self._title_size)
        self.title_spin.setFixedWidth(110)
        title_font_layout.addWidget(self.title_spin)

        self.title_hint = BodyLabel(tr("galgame.dialog.font.title_hint", default="px (推荐: 16-20)"), self)
        self.title_hint.setStyleSheet("color: #7f8c8d;")
        title_font_layout.addWidget(self.title_hint)
        title_font_layout.addStretch()
        layout.addLayout(title_font_layout)

        layout.addSpacing(8)
        self.preview_label = BodyLabel(tr("galgame.dialog.font.preview_label", default="预览效果:"), self)
        layout.addWidget(self.preview_label)

        self.title_preview = QFrame(self)
        self.title_preview.setObjectName("titlePreview")
        title_preview_layout = QVBoxLayout(self.title_preview)
        title_preview_layout.setContentsMargins(16, 12, 16, 12)

        self.title_preview_label = QLabel(tr("galgame.dialog.font.preview_title", default="第1章 · 开始的旅程"), self.title_preview)
        self.title_preview_label.setAlignment(Qt.AlignCenter)
        title_preview_layout.addWidget(self.title_preview_label)

        layout.addWidget(self.title_preview)

        self.story_preview = QLabel(tr("galgame.dialog.font.preview_story", default="这是故事正文的预览效果。你可以在这里看到不同字体大小下的显示效果。"), self)
        self.story_preview.setWordWrap(True)
        self.story_preview.setObjectName("storyPreview")
        layout.addWidget(self.story_preview)

        self.story_spin.valueChanged.connect(self._update_preview)
        self.title_spin.valueChanged.connect(self._update_preview)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.reset_btn = PushButton(tr("galgame.dialog.font.reset", default="恢复默认"), self)
        self.reset_btn.clicked.connect(self._reset_default)
        btn_layout.addWidget(self.reset_btn)

        self.cancel_btn = PushButton(tr("galgame.dialog.font.cancel", default="取消"), self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.apply_btn = PrimaryPushButton(tr("galgame.dialog.font.apply", default="应用"), self)
        self.apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)

        self._update_preview()
        self.update_theme()

    def _update_preview(self):
        story_size = self.story_spin.value()
        title_size = self.title_spin.value()

        is_dark = isDarkTheme()
        preview_bg = "#3d3d3d" if is_dark else "#f0f4f8"
        preview_border = "#4a5568" if is_dark else "#cbd5e0"
        story_bg = "#2d2d2d" if is_dark else "#f8f9fa"
        story_border = "#404040" if is_dark else "#e0e0e0"
        title_color = "#e2e8f0" if is_dark else "#2d3748"
        story_color = "#e0e0e0" if is_dark else "#333333"

        self.title_preview.setStyleSheet(f"""
            #titlePreview {{
                background-color: {preview_bg};
                border: 2px solid {preview_border};
                border-radius: 8px;
            }}
        """)

        self.title_preview_label.setStyleSheet(f"""
            font-size: {title_size}px;
            font-weight: bold;
            color: {title_color};
        """)

        self.story_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {story_bg};
                border: 1px solid {story_border};
                border-radius: 8px;
                padding: 16px;
                font-size: {story_size}px;
                color: {story_color};
            }}
        """)

    def _reset_default(self):
        self.story_spin.setValue(14)
        self.title_spin.setValue(16)

    def _apply_settings(self):
        self._story_size = self.story_spin.value()
        self._title_size = self.title_spin.value()

        self.font_changed.emit(self._story_size, self._title_size)
        self.accept()

    def get_font_sizes(self):
        return self._story_size, self._title_size

    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.dialog.font.title", default="字体设置"))
        self.title_label.setText(tr("galgame.dialog.font.size_title", default="字体大小设置"))
        self.story_label.setText(tr("galgame.dialog.font.story_label", default="故事正文:"))
        self.story_hint.setText(tr("galgame.dialog.font.story_hint", default="px (推荐: 14-16)"))
        self.title_font_label.setText(tr("galgame.dialog.font.title_label", default="章节标题:"))
        self.title_hint.setText(tr("galgame.dialog.font.title_hint", default="px (推荐: 16-20)"))
        self.preview_label.setText(tr("galgame.dialog.font.preview_label", default="预览效果:"))
        self.title_preview_label.setText(tr("galgame.dialog.font.preview_title", default="第1章 · 开始的旅程"))
        self.story_preview.setText(tr("galgame.dialog.font.preview_story", default="这是故事正文的预览效果。你可以在这里看到不同字体大小下的显示效果。"))
        self.reset_btn.setText(tr("galgame.dialog.font.reset", default="恢复默认"))
        self.cancel_btn.setText(tr("galgame.dialog.font.cancel", default="取消"))
        self.apply_btn.setText(tr("galgame.dialog.font.apply", default="应用"))

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

        self._update_preview()
