from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import isDarkTheme

from src.core.i18n import I18nManager, tr


class ChapterTitleCard(QFrame):
    def __init__(self, chapter_number: int, chapter_name: str, parent=None):
        super().__init__(parent)
        self._chapter_number = chapter_number
        self._chapter_name = chapter_name
        self._font_size = 16
        self.setObjectName("chapterTitleCard")
        self.init_ui()
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_text = self._build_title_text()
        
        self.title_label = QLabel(title_text, self)
        self.title_label.setObjectName("chapterTitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.update_theme()
    
    def _build_title_text(self) -> str:
        chapter_prefix = tr("galgame.status_bar.chapter", default="第{}章").format(self._chapter_number)
        if self._chapter_name:
            title_text = f"{chapter_prefix} · {self._chapter_name}"
        else:
            title_text = f"{chapter_prefix} · {tr('galgame.chapter.untitled', default='无题')}"
        return title_text
    
    def refresh_ui(self, lang_code: str = None):
        self.title_label.setText(self._build_title_text())
    
    def set_font_size(self, size: int):
        self._font_size = size
        self.update_theme()
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#1a1a2e" if is_dark else "#f0f4f8"
        text_color = "#e2e8f0" if is_dark else "#2d3748"
        border_color = "#4a5568" if is_dark else "#cbd5e0"
        
        self.setStyleSheet(f"""
            #chapterTitleCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
                margin: 8px 0;
            }}
            #chapterTitleLabel {{
                color: {text_color};
                font-size: {self._font_size}px;
                font-weight: bold;
            }}
        """)
