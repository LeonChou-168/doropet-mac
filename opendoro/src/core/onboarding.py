"""新手引导管理器。

设计说明：
- 每个引导步骤有唯一的 step_id（如 "v1_chat"），存储在数据库 onboarding_progress 表中。
- 发布新功能时，只需在 GUIDE_STEPS 末尾追加新步骤即可，已有用户的旧步骤不会重复弹出。
- 用户可通过标题栏"新手指南"按钮随时重新播放全部引导。
- 引导顺序按新手上手逻辑排列：先配模型 → 再聊天 → 了解宠物 → 定制外观 → 设定性格 → 探索插件 → 调整设置。
"""
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from PyQt5.QtCore import QTimer, QEvent
from PyQt5.QtWidgets import QWidget, QPushButton, QMessageBox, QVBoxLayout
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    TeachingTip, TeachingTipView, TeachingTipTailPosition,
    FluentIconBase, FluentIcon,
)

from src.core.i18n import tr

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


@dataclass
class OnboardingStep:
    """一个引导步骤的定义。"""
    step_id: str                        # 唯一 ID，用于数据库追踪（如 "v1_chat"）
    target_key: str                     # MainWindow 上的接口属性名（如 "chat_interface"），用于定位导航项
    title: str                          # TeachingTip 标题
    content: str                        # TeachingTip 内容
    icon: Optional[FluentIconBase] = None  # 可选图标


# ============================================================================
# 引导步骤定义 —— 按新手最佳上手顺序排列
# ============================================================================
GUIDE_STEPS: List[OnboardingStep] = [
    OnboardingStep(
        step_id="v1_model_config",
        target_key="config_interface",
        title=tr("onboarding.step.model_config.title", default="① 配置 AI 模型"),
        content=tr("onboarding.step.model_config.content",
                   default="这是最重要的第一步！点击「添加模型」，填入 API Key、Base URL 和模型名称，然后设为激活。配置完成后，AI 聊天和所有智能功能才能使用。"),
        icon=FluentIcon.ROBOT,
    ),
    OnboardingStep(
        step_id="v1_chat",
        target_key="chat_interface",
        title=tr("onboarding.step.chat.title", default="② 与 Doro 聊天"),
        content=tr("onboarding.step.chat.content",
                   default="模型就绪后，来这里和 Doro 自由对话。支持多轮对话、图片识别、思考过程展示、代码块渲染。左侧可以创建多个会话，切换不同话题。"),
        icon=FluentIcon.CHAT,
    ),
    OnboardingStep(
        step_id="v1_pet_status",
        target_key="pet_status_interface",
        title=tr("onboarding.step.pet_status.title", default="③ 了解 Doro 的状态"),
        content=tr("onboarding.step.pet_status.content",
                   default="宠物状态面板：查看饥饿、心情、清洁、能量四大属性。完成任务可获得橙子币，在商店购买道具。下方「番茄钟」帮你专注工作。"),
        icon=FluentIcon.HOME,
    ),
    OnboardingStep(
        step_id="v1_live2d_config",
        target_key="live2d_config_interface",
        title=tr("onboarding.step.live2d_config.title", default="④ 定制 Doro 的外观"),
        content=tr("onboarding.step.live2d_config.content",
                   default="在这里更换桌面宠物的 Live2D 模型，调整缩放比例和宽高比。选择一个你喜欢的形象，让 Doro 在桌面上陪伴你。"),
        icon=FluentIcon.PHOTO,
    ),
    OnboardingStep(
        step_id="v1_prompt",
        target_key="prompt_interface",
        title=tr("onboarding.step.prompt.title", default="⑤ 设定 Doro 的性格"),
        content=tr("onboarding.step.prompt.content",
                   default="编辑系统提示词（人设），自定义 Doro 的说话风格、性格特点和互动方式。你也可以创建多个角色，随时切换不同人格。"),
        icon=FluentIcon.PEOPLE,
    ),
    OnboardingStep(
        step_id="v1_plugin",
        target_key="plugin_interface",
        title=tr("onboarding.step.plugin.title", default="⑥ 探索插件功能"),
        content=tr("onboarding.step.plugin.content",
                   default="安装第三方插件扩展功能：2048 小游戏、飞行棋、备忘录、小说生成器等。每个插件都是独立模块，按需加载。"),
        icon=FluentIcon.BOOK_SHELF,
    ),
    OnboardingStep(
        step_id="v1_settings",
        target_key="settings_interface",
        title=tr("onboarding.step.settings.title", default="⑦ 调整偏好设置"),
        content=tr("onboarding.step.settings.content",
                   default="在这里调整通用、显示、声音和 AI 偏好。底部还有「软件更新」入口，随时检查新版本。数据存储路径也可以自定义。"),
        icon=FluentIcon.SETTING,
    ),
]


class OnboardingManager(QObject):
    """新手引导管理器。

    用法::

        manager = OnboardingManager(main_window, config_db)
        # 首次启动自动触发（只显示未完成的步骤）
        manager.start_guide()
        # 用户点击"新手指南"按钮时重播全部
        manager.reset_and_start()
    """

    def __init__(self, main_window: "MainWindow", config_db):
        super().__init__()
        self._main_window = main_window
        self._config_db = config_db
        self._current_tip: Optional[TeachingTip] = None
        self._steps_pending: List[OnboardingStep] = []
        self._current_index = 0
        self._overlay: Optional[QWidget] = None
        self._skip_btn: Optional[QPushButton] = None
        self._is_active = False

    # ---- public API ----

    def has_pending_steps(self) -> bool:
        """是否有未完成的引导步骤。"""
        completed = self._config_db.get_completed_onboarding_steps()
        return any(s.step_id not in completed for s in GUIDE_STEPS)

    def start_guide(self):
        """开始引导：显示欢迎对话框，然后仅显示未完成的步骤（首次启动用）。"""
        completed = self._config_db.get_completed_onboarding_steps()
        pending = [s for s in GUIDE_STEPS if s.step_id not in completed]
        if not pending:
            return
        self._show_welcome_dialog(pending)

    def reset_and_start(self):
        """清除全部进度并重新引导（"新手指南"按钮用）。"""
        self._config_db.reset_onboarding()
        self._show_welcome_dialog(list(GUIDE_STEPS))

    def _show_welcome_dialog(self, steps: List[OnboardingStep]):
        """弹出欢迎对话框，确认后开始引导。"""
        self._is_active = True
        msg = QMessageBox(self._main_window)
        msg.setWindowTitle(tr("onboarding.welcome.title", default="欢迎使用 DoroPet！"))
        msg.setText(tr("onboarding.welcome.text",
                       default="接下来将用 7 个步骤带你快速上手。\n\n"
                               "引导期间主界面暂时不可操作，\n"
                               "关闭每个提示框即可进入下一步。"))
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.button(QMessageBox.Ok).setText(
            tr("onboarding.welcome.start", default="开始引导"))
        msg.button(QMessageBox.Cancel).setText(
            tr("onboarding.welcome.skip", default="跳过"))
        msg.setDefaultButton(QMessageBox.Ok)

        result = msg.exec_()
        if result == QMessageBox.Ok:
            self._run_sequence(steps)
        else:
            # 用户点击跳过，标记所有步骤为完成
            for s in steps:
                self._config_db.mark_onboarding_step_completed(s.step_id)
            self._is_active = False

    # ---- internal ----

    def _run_sequence(self, steps: List[OnboardingStep]):
        """开始依次播放引导步骤。"""
        self._steps_pending = steps
        self._current_index = 0
        self._is_active = True
        # 显示半透明遮罩 + 跳过按钮
        self._show_overlay()
        # 先切换到第一个步骤对应的页面，再延迟弹出 TeachingTip
        first_step = steps[0]
        interface = getattr(self._main_window, first_step.target_key, None)
        if interface:
            self._main_window.switchTo(interface)
        QTimer.singleShot(500, lambda: self._show_current_step())

    def _show_current_step(self):
        """显示当前步骤的 TeachingTip。"""
        if not self._is_active or self._current_index >= len(self._steps_pending):
            self._cleanup()
            return

        step = self._steps_pending[self._current_index]

        # 切换导航到目标页面
        interface = getattr(self._main_window, step.target_key, None)
        if interface:
            self._main_window.switchTo(interface)

        # 延迟弹出 tip，确保页面和导航高亮已更新
        QTimer.singleShot(350, lambda: self._show_tip(step))

    def _show_tip(self, step: OnboardingStep):
        """弹出 TeachingTip 指向导航项。"""
        if not self._is_active:
            return
        target = self._get_nav_widget(step.target_key)
        if target is None:
            self._mark_and_next(step.step_id)
            return

        # 关闭上一个 tip
        self._close_current_tip()

        view = TeachingTipView(
            title=step.title,
            content=step.content,
            icon=step.icon,
            isClosable=True,
            tailPosition=TeachingTipTailPosition.LEFT,
            parent=self._main_window,
        )
        # 固定宽度 + 内容自动换行
        view.setFixedWidth(320)
        view.contentLabel.setWordWrap(True)
        view.contentLabel.setMaximumWidth(290)

        tip = TeachingTip(
            view=view,
            target=target,
            duration=-1,
            tailPosition=TeachingTipTailPosition.LEFT,
            parent=self._main_window,
            isDeleteOnClose=True,
        )
        view.closed.connect(lambda sid=step.step_id: self._mark_and_next(sid))
        tip.show()
        tip.raise_()
        self._current_tip = tip

    def _get_nav_widget(self, target_key: str):
        """根据 target_key 获取导航栏中的控件。"""
        interface = getattr(self._main_window, target_key, None)
        if interface is None:
            return None
        try:
            return self._main_window.navigationInterface.widget(interface.objectName())
        except Exception:
            return None

    def _mark_and_next(self, step_id: str):
        """标记当前步骤完成，播放下一个。"""
        if not self._is_active:
            return
        self._config_db.mark_onboarding_step_completed(step_id)
        self._current_index += 1
        self._show_current_step()

    def _close_current_tip(self):
        """安全关闭当前 tip。"""
        if self._current_tip is not None:
            try:
                self._current_tip.closed.disconnect()
            except Exception:
                pass
            try:
                self._current_tip.close()
            except Exception:
                pass
            self._current_tip = None

    def _skip_all(self):
        """跳过所有剩余步骤。"""
        for i in range(self._current_index, len(self._steps_pending)):
            step = self._steps_pending[i]
            self._config_db.mark_onboarding_step_completed(step.step_id)
        self._cleanup()

    def _cleanup(self):
        """引导序列结束后的清理。"""
        self._is_active = False
        self._close_current_tip()
        self._hide_overlay()
        self._steps_pending.clear()
        self._current_index = 0

    def _show_overlay(self):
        """显示半透明遮罩层 + 跳过按钮。"""
        if self._overlay is not None:
            return

        self._overlay = QWidget(self._main_window)
        self._overlay.setAttribute(Qt.WA_StyledBackground, True)
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 80);")
        self._overlay.setGeometry(self._main_window.rect())
        self._overlay.show()
        self._overlay.raise_()

        # 右下角「跳过引导」按钮
        self._skip_btn = QPushButton(
            tr("onboarding.skip_all", default="跳过引导"), self._overlay)
        self._skip_btn.setFont(QFont("Microsoft YaHei", 10))
        self._skip_btn.setFixedSize(110, 36)
        self._skip_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 30);
                color: white;
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 60);
            }
        """)
        self._skip_btn.clicked.connect(self._skip_all)
        self._reposition_skip_btn()
        self._skip_btn.show()

        self._main_window.installEventFilter(self)

    def _reposition_skip_btn(self):
        """将跳过按钮定位到右下角。"""
        if self._skip_btn and self._overlay:
            w = self._overlay.width()
            h = self._overlay.height()
            self._skip_btn.move(w - 130, h - 50)

    def _hide_overlay(self):
        """隐藏遮罩层和跳过按钮。"""
        if self._skip_btn is not None:
            self._skip_btn.deleteLater()
            self._skip_btn = None
        if self._overlay is not None:
            self._main_window.removeEventFilter(self)
            self._overlay.deleteLater()
            self._overlay = None

    def eventFilter(self, obj, event):
        """监听主窗口 resize 事件，同步遮罩尺寸和按钮位置。"""
        if obj is self._main_window and event.type() == QEvent.Resize:
            if self._overlay is not None:
                self._overlay.setGeometry(self._main_window.rect())
                self._reposition_skip_btn()
        return False
