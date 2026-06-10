from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap
from src.resource_utils import resource_path
from src.ui.design_tokens import (
    get_tokens, BRAND_PRIMARY, ANIMATION_DURATION,
    glass_qss
)


class _AnimatedProgressBar(QWidget):
    """阶段性进度条 —— 平滑过渡到目标百分比，反映真实加载进度。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self.setFixedWidth(220)

        self._progress = 0.0    # 当前显示值 (0~100)
        self._target = 0.0      # 目标值
        self._anim = None

    def _get_progress(self):
        return self._progress

    def _set_progress(self, value):
        self._progress = value
        self.repaint()

    # 声明为 Qt 属性，供 QPropertyAnimation 驱动
    progress = pyqtProperty(float, _get_progress, _set_progress)

    def set_target(self, percent: float):
        """设置目标百分比，自动平滑动画过去。"""
        self._target = max(0.0, min(100.0, percent))
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(350)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(self._target)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def force_to(self, percent: float):
        """直接跳到指定百分比（无动画）。"""
        self._target = max(0.0, min(100.0, percent))
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()
        self._progress = self._target
        self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        r = h / 2

        # 背景轨道
        painter.setPen(Qt.NoPen)
        bg = self._token_color("input_bg", "rgba(0,0,0,10)")
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(0, 0, w, h, r, r)

        # 已填充部分
        fill_w = int(self._progress / 100.0 * w)
        if fill_w > 0:
            painter.setBrush(QColor(BRAND_PRIMARY))
            painter.drawRoundedRect(0, 0, fill_w, h, r, r)

    def _token_color(self, key, fallback):
        try:
            from src.ui.design_tokens import get_token
            return get_token(key) or fallback
        except Exception:
            return fallback

    def stop(self):
        if self._anim:
            self._anim.stop()


class SplashScreen(QWidget):
    """品牌启动页——毛玻璃背景 + 阶段式进度条 + 状态文字。"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(420, 340)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._tokens = get_tokens()
        self._setup_ui()
        self._start_icon_pulse()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignCenter)

        # 毛玻璃容器
        container = QWidget()
        container.setObjectName("splashContainer")
        container.setFixedSize(380, 300)
        container.setStyleSheet(glass_qss("16px"))

        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setContentsMargins(40, 24, 40, 24)
        container_layout.setSpacing(10)

        # ---- App 图标 ----
        self.icon_label = QLabel()
        icon_path = resource_path("data/icons/app.png")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(80)
        self.icon_label.setStyleSheet("background: transparent;")
        container_layout.addWidget(self.icon_label)

        # ---- 品牌标题 ----
        self.title_label = QLabel("DoroPet")
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont("Microsoft YaHei", 26)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; "
            f"color: {BRAND_PRIMARY}; background: transparent;"
        )
        container_layout.addWidget(self.title_label)

        # ---- 副标题 ----
        self.subtitle_label = QLabel("你的桌面 AI 伙伴")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(
            f"font-size: 13px; color: {self._tokens['text_secondary']}; "
            "background: transparent;"
        )
        container_layout.addWidget(self.subtitle_label)

        container_layout.addSpacing(8)

        # ---- 阶段式进度条 ----
        self.progress_bar = _AnimatedProgressBar()
        progress_wrapper = QWidget()
        progress_wrapper_layout = QVBoxLayout(progress_wrapper)
        progress_wrapper_layout.setAlignment(Qt.AlignCenter)
        progress_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        progress_wrapper_layout.addWidget(self.progress_bar)
        container_layout.addWidget(progress_wrapper)

        container_layout.addSpacing(4)

        # ---- 状态文字 ----
        self.status_label = QLabel("启动中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"font-size: 12px; color: {self._tokens['text_disabled']}; "
            "background: transparent;"
        )
        container_layout.addWidget(self.status_label)

        outer_layout.addWidget(container, 0, Qt.AlignCenter)

        screen = QDesktopWidget().screenGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _start_icon_pulse(self):
        """使用 QGraphicsOpacityEffect 实现图标呼吸脉冲。"""
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        self._icon_opacity = QGraphicsOpacityEffect(self.icon_label)
        self._icon_opacity.setOpacity(1.0)
        self.icon_label.setGraphicsEffect(self._icon_opacity)

        self._pulse_anim = QPropertyAnimation(self._icon_opacity, b"opacity")
        self._pulse_anim.setDuration(1400)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.4)
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.start()

    def set_status(self, text: str, progress: int = -1):
        """更新状态文字和进度。progress 为 -1 时不更新进度。"""
        self.status_label.setText(text)
        if progress >= 0:
            self.progress_bar.force_to(progress)

    def close_splash(self):
        """先填满进度条到 100%，再淡出关闭。"""
        self._pulse_anim.stop()

        # 冲到 100%
        self.progress_bar.set_target(100.0)

        # 等动画完成后再淡出
        QTimer.singleShot(400, self._start_fade_out)

    def _start_fade_out(self):
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(ANIMATION_DURATION["entrance"])
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.finished.connect(self.close)
        self._fade_anim.start()
