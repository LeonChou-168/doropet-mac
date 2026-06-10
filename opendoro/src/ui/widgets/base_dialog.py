"""
统一弹窗基类 - 所有弹窗/对话框继承此类，确保视觉一致性。
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QPoint, QSize
)
from PyQt5.QtGui import QColor, QFont
from qfluentwidgets import (
    PushButton, PrimaryPushButton, FluentIcon as FIF,
    isDarkTheme, setTheme, Theme
)
from src.ui.design_tokens import (
    get_tokens, get_token, BRAND_PRIMARY,
    ANIMATION_DURATION, SPACING, SHADOW_ELEVATION,
    glass_qss
)


class BaseDialog(QWidget):
    """
    统一弹窗基类。

    特性：
    - 无边框毛玻璃窗口
    - 统一阴影和圆角
    - 淡入入场动画
    - 标题栏拖拽移动
    - ESC 关闭
    - 自动主题适配
    - 标准布局：标题栏 + 内容区 + 按钮区

    使用方法:
        class MyDialog(BaseDialog):
            def __init__(self, parent=None):
                super().__init__(parent, title="标题", width=400, height=300)
                self.setup_content()    # 自定义内容区
                self.setup_buttons()    # 自定义按钮区

            def setup_content(self):
                label = QLabel("内容", self.content_widget)
                self.content_layout.addWidget(label)

            def setup_buttons(self):
                self.add_primary_button("确定", self.accept)
                self.add_cancel_button("取消")
    """

    accepted = pyqtSignal()
    rejected = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None, title: str = "",
                 width: int = 440, height: int = 360,
                 show_title_bar: bool = True,
                 show_close_btn: bool = True):
        super().__init__(parent)

        self._dialog_width = width
        self._dialog_height = height
        self._show_title_bar = show_title_bar
        self._show_close_btn = show_close_btn
        self._title_text = title
        self._is_dragging = False
        self._drag_pos = None
        self._entrance_anim = None

        # 设置窗口标志
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Dialog |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(width + 20, height + 20)  # +20 留给阴影

        self._setup_ui()
        self._apply_theme()
        self.center_on_parent()

        # 入场动画
        self._play_entrance_animation()

    def _setup_ui(self):
        """构建外层容器 + 阴影 + 内层布局。"""
        self.setObjectName("baseDialog")

        # 外层阴影容器
        self._container = QWidget(self)
        self._container.setObjectName("dialogContainer")
        self._container.setGeometry(
            10, 10, self._dialog_width, self._dialog_height
        )

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self._container)
        spec = SHADOW_ELEVATION[2]
        shadow.setBlurRadius(spec.blur)
        shadow.setOffset(spec.offset_x, spec.offset_y)
        shadow.setColor(QColor(0, 0, 0, 60 if isDarkTheme() else 20))
        self._container.setGraphicsEffect(shadow)
        self._shadow = shadow

        # 主布局
        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(
            SPACING["md"], SPACING["md"], SPACING["md"], SPACING["md"]
        )
        self._main_layout.setSpacing(SPACING["sm"])

        # 标题栏
        if self._show_title_bar:
            self._setup_title_bar()

        # 内容区
        self.content_widget = QWidget(self._container)
        self.content_widget.setObjectName("dialogContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(SPACING["sm"])
        self._main_layout.addWidget(self.content_widget, 1)

        # 按钮区占位（子类通过 add_buttons 填充）
        self._button_widget = QWidget(self._container)
        self._button_layout = QHBoxLayout(self._button_widget)
        self._button_layout.setContentsMargins(0, SPACING["xs"], 0, 0)
        self._button_layout.setSpacing(SPACING["sm"])
        self._button_layout.addStretch()
        self._main_layout.addWidget(self._button_widget)

    def _setup_title_bar(self):
        """构建标题栏。"""
        title_bar = QWidget(self._container)
        title_bar.setObjectName("dialogTitleBar")
        title_bar.setFixedHeight(36)

        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(SPACING["sm"])

        # 标题图标（可选，子类可设置）
        self._title_icon_label = QLabel("")
        self._title_icon_label.setFixedSize(22, 22)
        self._title_icon_label.hide()
        tb_layout.addWidget(self._title_icon_label)

        # 标题文字
        self._title_label = QLabel(self._title_text)
        self._title_label.setObjectName("dialogTitle")
        font = QFont("Microsoft YaHei", 12)
        font.setBold(True)
        self._title_label.setFont(font)
        tb_layout.addWidget(self._title_label, 1)

        # 关闭按钮
        if self._show_close_btn:
            self._close_btn = PushButton(FIF.CANCEL, "", self._container)
            self._close_btn.setFixedSize(28, 28)
            self._close_btn.clicked.connect(self.reject)
            tb_layout.addWidget(self._close_btn)

        self._main_layout.addWidget(title_bar)

    def _play_entrance_animation(self):
        """播放淡入 + 微弹入场动画。"""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._entrance_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._entrance_anim.setDuration(ANIMATION_DURATION["entrance"])
        self._entrance_anim.setStartValue(0.0)
        self._entrance_anim.setEndValue(1.0)
        self._entrance_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 同时做轻微的缩放效果（通过容器）
        self._container_opacity = QGraphicsOpacityEffect(self._container)
        self._container_opacity.setOpacity(0.7)
        self._container.setGraphicsEffect(self._shadow)

        # 注意：QGraphicsDropShadowEffect 和 QGraphicsOpacityEffect 不能同时设置
        # 所以我们只做整体淡入，不做缩放
        self._entrance_anim.start()

    def _apply_theme(self):
        """应用当前主题样式。"""
        dark = isDarkTheme()
        t = get_tokens()

        # 容器样式（毛玻璃效果）
        self._container.setStyleSheet(glass_qss())

        # 标题栏
        if self._show_title_bar:
            self._title_label.setStyleSheet(
                f"color: {t['text_primary']}; background: transparent;"
            )

        # 内容区
        self.content_widget.setStyleSheet("background: transparent;")

        # 更新阴影颜色
        if self._shadow:
            self._shadow.setColor(
                QColor(0, 0, 0, 60 if dark else 20)
            )

    def update_theme(self):
        """手动刷新主题（在主题切换时调用）。"""
        self._apply_theme()
        # 子类可覆写此方法以添加额外刷新逻辑

    def center_on_parent(self):
        """居中于父窗口或屏幕。"""
        if self.parent() and self.parent().isVisible():
            geo = self.parent().geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
        else:
            from PyQt5.QtWidgets import QDesktopWidget
            screen = QDesktopWidget().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
        self.move(max(0, x), max(0, y))

    def set_title_icon(self, text: str):
        """设置标题栏图标（emoji 或文本）。"""
        if hasattr(self, '_title_icon_label'):
            self._title_icon_label.setText(text)
            self._title_icon_label.show()
            self._title_icon_label.setStyleSheet(
                "font-size: 16px; background: transparent;"
            )

    def set_title(self, text: str):
        """设置标题文字。"""
        if hasattr(self, '_title_label'):
            self._title_label.setText(text)

    # ============================================================
    # 按钮快捷方法
    # ============================================================

    def add_primary_button(self, text: str, callback, icon=None):
        """添加主要按钮（品牌色）。"""
        btn = PrimaryPushButton(icon or FIF.ACCEPT, text, self._button_widget)
        btn.setMinimumHeight(34)
        btn.clicked.connect(callback)
        # 插入到 stretch 之前
        self._button_layout.insertWidget(
            self._button_layout.count() - 1, btn
        )
        return btn

    def add_secondary_button(self, text: str, callback, icon=None):
        """添加次要按钮。"""
        btn = PushButton(icon or FIF.CANCEL, text, self._button_widget)
        btn.setMinimumHeight(34)
        btn.clicked.connect(callback)
        self._button_layout.insertWidget(
            self._button_layout.count() - 1, btn
        )
        return btn

    def add_cancel_button(self, text: str = "取消"):
        """添加取消按钮（自动连接 reject）。"""
        return self.add_secondary_button(text, self.reject)

    # ============================================================
    # 交互事件
    # ============================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 只在标题栏区域可拖拽 (顶部 44px)
            if event.y() < 44:
                self._is_dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def accept(self):
        """确认操作。"""
        self.accepted.emit()
        self._play_exit_animation(self.close)

    def reject(self):
        """取消/关闭操作。"""
        self.rejected.emit()
        self._play_exit_animation(self.close)

    def _play_exit_animation(self, on_finished):
        """播放淡出动画后关闭。"""
        self._exit_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._exit_anim.setDuration(ANIMATION_DURATION["normal"])
        self._exit_anim.setStartValue(self._opacity_effect.opacity())
        self._exit_anim.setEndValue(0.0)
        self._exit_anim.setEasingCurve(QEasingCurve.InCubic)
        self._exit_anim.finished.connect(on_finished)
        self._exit_anim.start()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
