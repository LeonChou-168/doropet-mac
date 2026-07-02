import os
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QUrl, QSettings
from PyQt5.QtGui import QIcon, QDesktopServices

from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentTranslator, 
                            NavigationAvatarWidget, SplashScreen, TransparentToolButton,
                            setTheme, Theme, isDarkTheme, setThemeColor)
from qfluentwidgets import FluentIcon as FIF

# 导入子界面
from .pages.chat_interface import ChatInterface
from .pages.config_interface import ConfigInterface
from .pages.settings_interface import SettingsInterface
from .pages.prompt_interface import PromptInterface
from .pages.log_interface import LogInterface
from .pages.voice_config_interface import VoiceConfigInterface
from .pages.plugin_interface import PluginInterface
from .pages.skills_interface import SkillsInterface
from .pages.update_interface import UpdateInterface
from .pages.pet_status_interface import PetStatusInterface
from .pages.live2d_config_interface import Live2DConfigInterface
from .pages.memory_interface import MemoryInterface
from .music import MusicInterface
from .pomodoro import PomodoroInterface
from src.core.database import ChatDatabase
from src.resource_utils import resource_path
from src.core.logger import logger
from src.core.font_scale_utils import apply_font_scale
from src.core.app_theme import THEME_COLOR
from src.core.orange_manager import OrangeManager
from src.core.i18n import I18nManager, tr
from src.core.onboarding import OnboardingManager

class MainWindow(FluentWindow):
    def __init__(self, version_manager=None):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.setObjectName("MainWindow")
        self._version_manager = version_manager
        
        # 1. 初始化窗口
        self.setWindowTitle("Doro Pet")
        self.resize(1024, 800)
        
        # 2. 初始化数据库 (单一实例)
        self.db = ChatDatabase()

        # 3. 创建子界面（分批创建，每批之后刷新事件循环以保持启动动画流畅）
        self.chat_interface = ChatInterface(self.db, self)
        self.config_interface = ConfigInterface(self.db, self)
        self.voice_config_interface = VoiceConfigInterface(self.db, self)
        self.live2d_config_interface = Live2DConfigInterface(self.db, self)
        QApplication.processEvents()

        self.prompt_interface = PromptInterface(self.db, self)
        self.plugin_interface = PluginInterface(self)
        self.skills_interface = SkillsInterface(self)
        self.log_interface = LogInterface(self)
        self.update_interface = UpdateInterface(self, version_manager)
        self.settings_interface = SettingsInterface(self)
        QApplication.processEvents()

        self.attr_manager = None
        self._orange_manager = OrangeManager(self)
        QApplication.processEvents()

        self.pomodoro_interface = PomodoroInterface(self)
        self.pet_status_interface = PetStatusInterface(None, self.db, self, self.pomodoro_interface)
        self.music_interface = MusicInterface(self)
        self.memory_interface = MemoryInterface(self.db, self)
        QApplication.processEvents()

        self.pomodoro_interface.set_orange_manager(self._orange_manager)
        self.pet_status_interface.set_orange_manager(self._orange_manager)

        # 4. 初始化导航栏
        self.init_navigation()
        QApplication.processEvents()

        # 5. 初始化新手引导管理器
        self._onboarding_manager = OnboardingManager(self, self.db._config)

        # 6. 初始化标题栏功能 (置顶、主题切换、新手指南)
        self.init_title_bar()

        setThemeColor(THEME_COLOR)
        if isDarkTheme():
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
        else:
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))
        QApplication.processEvents()

        # 6. 初始化窗口属性
        self.init_window()

    def init_navigation(self):
        self.addSubInterface(self.pet_status_interface, FIF.HOME, tr("nav.pet_status"))
        self.addSubInterface(self.chat_interface, FIF.CHAT, tr("nav.ai_chat"))
        self.addSubInterface(self.music_interface, FIF.MUSIC, tr("nav.music"))
        self.addSubInterface(self.config_interface, FIF.ROBOT, tr("nav.model_config"))
        self.addSubInterface(self.voice_config_interface, FIF.MICROPHONE, tr("nav.voice_config"))
        self.addSubInterface(self.live2d_config_interface, FIF.PHOTO, tr("nav.live2d_config"))
        self.addSubInterface(self.prompt_interface, FIF.PEOPLE, tr("nav.role_play"))
        self.addSubInterface(self.memory_interface, FIF.SAVE, tr("nav.memory"))
        self.addSubInterface(self.plugin_interface, FIF.BOOK_SHELF, tr("nav.plugin"))
        self.addSubInterface(self.skills_interface, FIF.PALETTE, tr("nav.skills"))
        self.addSubInterface(self.log_interface, FIF.COMMAND_PROMPT, tr("nav.logs"))
        
        # Connect signals
        self.voice_config_interface.settingsChanged.connect(self.chat_interface.update_voice_ui_visibility)
        self.pet_status_interface.start_chat_requested.connect(self._switch_to_chat)
        self.pet_status_interface.music_player_card.switch_to_music_interface.connect(self._switch_to_music)

        self.pomodoro_interface.doro_focus_started.connect(self._on_doro_focus_started)
        self.pomodoro_interface.doro_pomodoro_completed.connect(self._on_doro_pomodoro_completed)
        self.pomodoro_interface.doro_focus_interrupted.connect(self._on_doro_focus_interrupted)
        self.pomodoro_interface.doro_streak_warning.connect(self._on_doro_streak_warning)
        self.pomodoro_interface.doro_idle_reminder.connect(self._on_doro_idle_reminder)

        self.navigationInterface.setCurrentItem(self.pet_status_interface.objectName())
        
        # 添加设置到底部
        self.addSubInterface(self.update_interface, FIF.UPDATE, tr("nav.update"), NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings_interface, FIF.SETTING, tr("nav.settings"), NavigationItemPosition.BOTTOM)

        # 监听语言切换，刷新导航栏
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self._refresh_navigation_labels)

    def init_window(self):
        icon_path = resource_path("data/icons/app.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def init_title_bar(self):
        # 1. 创建按钮
        self.pin_btn = TransparentToolButton(FIF.PIN, self)
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip(tr("titlebar.pin"))
        self.pin_btn.clicked.connect(self.toggle_pinning)

        self.theme_btn = TransparentToolButton(FIF.CONSTRACT, self)
        self.theme_btn.setToolTip(tr("titlebar.toggle_theme"))
        self.theme_btn.clicked.connect(self.toggle_theme)

        self.guide_btn = TransparentToolButton(FIF.HELP, self)
        self.guide_btn.setToolTip(tr("titlebar.guide"))
        self.guide_btn.clicked.connect(self._on_guide_clicked)

        # 2. 添加到标题栏布局
        # 在最小化按钮之前插入 (通常布局倒数第3个是Min，但要视具体实现而定)
        # 我们插入到 layout 的倒数位置之前
        self.titleBar.layout().insertWidget(self.titleBar.layout().count() - 3, self.pin_btn, 0, Qt.AlignRight)
        self.titleBar.layout().insertWidget(self.titleBar.layout().count() - 3, self.theme_btn, 0, Qt.AlignRight)
        self.titleBar.layout().insertWidget(self.titleBar.layout().count() - 3, self.guide_btn, 0, Qt.AlignRight)
        
        # 添加间距
        self.titleBar.layout().insertSpacing(self.titleBar.layout().count() - 3, 10)

    def _refresh_navigation_labels(self, lang_code: str):
        """语言切换时刷新导航栏标签和标题栏提示。"""
        nav_items = [
            (self.pet_status_interface, "nav.pet_status"),
            (self.chat_interface, "nav.ai_chat"),
            (self.music_interface, "nav.music"),
            (self.config_interface, "nav.model_config"),
            (self.voice_config_interface, "nav.voice_config"),
            (self.live2d_config_interface, "nav.live2d_config"),
            (self.prompt_interface, "nav.role_play"),
            (self.memory_interface, "nav.memory"),
            (self.plugin_interface, "nav.plugin"),
            (self.skills_interface, "nav.skills"),
            (self.log_interface, "nav.logs"),
            (self.update_interface, "nav.update"),
            (self.settings_interface, "nav.settings"),
        ]
        for widget, key in nav_items:
            self.navigationInterface.widget(widget.objectName()).setText(tr(key))
        # 刷新标题栏提示
        self.pin_btn.setToolTip(tr("titlebar.pin") if not self.pin_btn.isChecked() else tr("titlebar.unpin"))
        self.theme_btn.setToolTip(tr("titlebar.toggle_theme"))
        self.guide_btn.setToolTip(tr("titlebar.guide"))

    def toggle_pinning(self):
        hwnd = int(self.winId())
        
        # Windows Constants
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        
        # Ensure correct argument types for 64-bit compatibility
        SetWindowPos = ctypes.windll.user32.SetWindowPos
        SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        SetWindowPos.restype = wintypes.BOOL
        
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        
        if self.pin_btn.isChecked():
            # Set Always on Top
            SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
            self.pin_btn.setToolTip(tr("titlebar.unpin"))
        else:
            # Remove Always on Top
            SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
            self.pin_btn.setToolTip(tr("titlebar.pin"))

    def _switch_to_chat(self):
        self.switchTo(self.chat_interface)
    
    def _switch_to_music(self):
        self.switchTo(self.music_interface)

    def _on_doro_focus_started(self):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            self.live2d_widget.talk(tr("pet.encourage"), 3000)

    def _on_doro_pomodoro_completed(self, focus_minutes: int = 0):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            orange_count = self._orange_manager.balance if self._orange_manager else 0
            self.live2d_widget.talk(tr("pet.pomodoro_done").format(orange_count=orange_count), 4000)
            try:
                self.live2d_widget.set_expression_safe("stars")
            except Exception:
                pass

    def _on_doro_focus_interrupted(self):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            self.live2d_widget.talk(tr("pet.distracted"), 3500)
            try:
                self.live2d_widget.set_expression_safe("question")
            except Exception:
                pass

    def _on_doro_streak_warning(self, minutes: int):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            hours = minutes / 60
            self.live2d_widget.talk(tr("pet.streak_warning").format(hours=hours), 4000)
            try:
                self.live2d_widget.set_expression_safe("bag")
            except Exception:
                pass

    def _on_doro_idle_reminder(self):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            self.live2d_widget.talk(tr("pet.idle_reminder"), 4000)
            try:
                self.live2d_widget.set_expression_safe("exclamation")
            except Exception:
                pass

    def _on_guide_clicked(self):
        """标题栏"新手指南"按钮点击 —— 重置进度并重新播放全部引导。"""
        self._onboarding_manager.reset_and_start()

    def showEvent(self, event):
        """窗口显示时触发：首次打开自动弹出新手引导。"""
        super().showEvent(event)
        if hasattr(self, '_onboarding_manager') and not hasattr(self, '_onboarding_checked'):
            self._onboarding_checked = True
            if self._onboarding_manager.has_pending_steps():
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(800, self._onboarding_manager.start_guide)

    def _on_doro_level_changed(self, level: int, title: str):
        if hasattr(self, 'live2d_widget') and self.live2d_widget:
            self.live2d_widget.talk(tr("pet.level_up").format(level=level, title=title), 5000)
            try:
                self.live2d_widget.set_expression_safe("stars")
            except Exception:
                pass

    def toggle_theme(self):
        setThemeColor(THEME_COLOR)
        if isDarkTheme():
            logger.info("Switching to Light theme.")
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))
        else:
            logger.info("Switching to Dark theme.")
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
            
        is_dark = isDarkTheme()
        if hasattr(self, 'pet_status_interface'):
            self.pet_status_interface.update_theme(is_dark)
        if hasattr(self, 'config_interface'):
            self.config_interface.update_theme()
        if hasattr(self, 'prompt_interface'):
            self.prompt_interface.update_theme()
        if hasattr(self, 'chat_interface'):
            self.chat_interface.update_theme()
        if hasattr(self, 'settings_interface'):
            self.settings_interface.update_theme()
        if hasattr(self, 'log_interface'):
            self.log_interface.update_theme()
        if hasattr(self, 'voice_config_interface'):
            self.voice_config_interface.update_theme()
        if hasattr(self, 'live2d_config_interface'):
            self.live2d_config_interface.update_theme()
        
        if hasattr(self, 'music_interface'):
            self.music_interface.update_theme(is_dark)
        
        if hasattr(self, 'pomodoro_interface'):
            self.pomodoro_interface.update_theme()

        if hasattr(self, 'skills_interface'):
            self.skills_interface.update_theme()

        if hasattr(self, 'memory_interface'):
            self.memory_interface.update_theme()

        if hasattr(self, 'plugin_interface'):
            self.plugin_interface.update_theme()

        if hasattr(self, 'live2d_widget') and hasattr(self.live2d_widget, 'quick_chat_window'):
            if self.live2d_widget.quick_chat_window:
                self.live2d_widget.quick_chat_window.update_theme()

    def load_stylesheet(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
            settings = QSettings("DoroPet", "Settings")
            font_scale = settings.value("font_scale", 1.0, type=float)
            qss = apply_font_scale(qss, font_scale)
            QApplication.instance().setStyleSheet(qss)
        else:
            logger.warning(f"Stylesheet not found: {path}")

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget

        if hasattr(widget, 'attr_manager'):
            self.attr_manager = widget.attr_manager
            if self._orange_manager:
                self.attr_manager.set_orange_manager(self._orange_manager)

        if hasattr(widget, 'orange_manager'):
            pass

        if hasattr(self, 'settings_interface'):
            self.settings_interface.set_live2d_widget(widget)

        if hasattr(self, 'chat_interface'):
            self.chat_interface.set_live2d_widget(widget)

        if hasattr(self, 'live2d_config_interface'):
            self.live2d_config_interface.set_live2d_widget(widget)

        if hasattr(self, 'pet_status_interface') and self.attr_manager:
            self.pet_status_interface.set_attr_manager(self.attr_manager)

        if hasattr(widget, '_startup_checker') and widget._startup_checker:
            widget._startup_checker.set_main_window(self)

        if self._orange_manager:
            self._orange_manager.level_changed.connect(self._on_doro_level_changed)

    def set_version_manager(self, version_manager):
        """设置版本管理器（在启动阶段延迟注入）。"""
        self._version_manager = version_manager
        if hasattr(self, 'update_interface'):
            self.update_interface.update_widget.set_version_manager(version_manager)
        
    def closeEvent(self, event):
        """重写关闭事件，使其隐藏而不是关闭"""
        logger.info("MainWindow hidden to tray.")
        self.hide()
        event.ignore()