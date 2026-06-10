import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = None

def init_provider_framework():
    from src.core.database import DatabaseManager
    from src.provider.manager import ProviderManager

    try:
        from src.provider.sources import (
            ProviderOpenAI, ProviderDeepSeek, ProviderAnthropic,
            ProviderOllama, ProviderMoonshot, ProviderGemini,
            ProviderGroq, ProviderZhipu,
            ProviderEdgeTTS, ProviderOpenAITTS, ProviderGradioTTS,
            ProviderOpenAIImage
        )
        logger.debug("Provider adapters loaded successfully")
    except ImportError as e:
        logger.warning(f"Some provider adapters could not be loaded: {e}")

    db = DatabaseManager().config
    pm = ProviderManager.get_instance()
    pm.load_providers_from_db(db)
    logger.info(f"ProviderManager initialized with {len(pm.get_all_llm_providers())} LLM providers")


def init_agent_framework():
    """初始化 pydantic-ai Agent 框架。

    预加载 SkillManager 和 SkillEnabledState，确保技能在首次对话时可用。
    pydantic-ai 的 Agent 实例在每次 LLMWorker 运行时按需创建。
    """
    try:
        from src.agent.skills.state import SkillEnabledState
        from src.core.skill_manager import SkillManager

        # 加载技能启用状态
        state = SkillEnabledState.get_instance()
        state.load_from_settings()

        # 预加载技能管理器（触发技能发现）
        skill_manager = SkillManager()
        logger.info(f"[AgentFW] pydantic-ai ready: {len(skill_manager.skills)} skills discovered")
    except ImportError as e:
        logger.warning(f"[AgentFW] Not available: {e}")
    except Exception as e:
        logger.error(f"[AgentFW] Init error: {e}")

def setup_tray_icon(app, widget):
    """设置系统托盘"""
    from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
    from PyQt5.QtGui import QIcon
    from src.resource_utils import resource_path

    tray_icon = QSystemTrayIcon(app)
    
    # 尝试加载图标
    icon_path = resource_path("data/icons/app.png")
    if not os.path.exists(icon_path):
        icon_path = resource_path("data/icons/orange.ico")
        
    if os.path.exists(icon_path):
        tray_icon.setIcon(QIcon(icon_path))
    else:
        logger.warning("Tray icon not found.")
        
    # 托盘菜单
    tray_menu = QMenu()
    
    # === 快捷操作区 ===
    quick_chat_action = QAction("💬 沉浸聊天", app)
    quick_chat_action.setToolTip("打开沉浸聊天窗口，快速与 Doro 对话")
    def open_quick_chat():
        from src.ui.windows.quick_chat_window import QuickChatWindow
        from src.core.quick_chat_dependencies import get_quick_chat_deps
        if not hasattr(widget, 'quick_chat_window') or not widget.quick_chat_window:
            deps = get_quick_chat_deps()
            widget.quick_chat_window = QuickChatWindow(
                db=deps.chat_db,
                persona_db=deps.persona_db,
                live2d_widget=widget
            )
        widget.quick_chat_window.show()
        widget.quick_chat_window.raise_()
        widget.quick_chat_window.activateWindow()
    quick_chat_action.triggered.connect(open_quick_chat)
    tray_menu.addAction(quick_chat_action)
    
    tray_menu.addSeparator()
    
    # === 宠物控制区 ===
    pet_menu = QMenu("🐾 宠物控制", tray_menu)
    
    # 显示/隐藏桌宠
    action_toggle = QAction("显示/隐藏桌宠", app)
    def toggle_pet():
        if widget.isVisible():
            widget.hide()
            if hasattr(widget, 'status_overlay') and widget.status_overlay.isVisible():
                widget.status_overlay._fade_out()
        else:
            widget.show()
            widget.activateWindow()
    action_toggle.triggered.connect(toggle_pet)
    pet_menu.addAction(action_toggle)
    
    # 锁定/解锁
    action_lock = QAction(tr("tray.lock_unlock"), app)
    action_lock.setCheckable(True)
    action_lock.setChecked(False)
    def toggle_lock(checked):
        widget.set_locked(checked)
        if checked:
            action_lock.setText("解锁")
        else:
            action_lock.setText("锁定")
            
    action_lock.triggered.connect(toggle_lock)
    pet_menu.addAction(action_lock)
    
    tray_menu.addMenu(pet_menu)
    
    # === 界面管理区 ===
    view_menu = QMenu(tr("tray.view_management"), tray_menu)
    
    # 打开主界面
    action_settings = QAction(tr("tray.open_main"), app)
    action_settings.triggered.connect(widget.open_main_window)
    view_menu.addAction(action_settings)
    
    tray_menu.addMenu(view_menu)
    
    tray_menu.addSeparator()
    
    # === 系统区 ===
    # 退出程序
    action_quit = QAction(tr("tray.quit"), app)
    action_quit.triggered.connect(app.quit)
    tray_menu.addAction(action_quit)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # 双击托盘显示主界面
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.DoubleClick:
            widget.open_main_window()
            
    tray_icon.activated.connect(on_tray_activated)
    
    return tray_icon

def setup_startup_update_checker(widget):
    from src.core.startup_update_checker import StartupUpdateChecker

    update_checker = StartupUpdateChecker(widget)
    
    def on_update_available(version_info):
        logger.info(f"Update available: v{version_info.version}")
        show_update_dialog(widget, version_info, update_checker)
    
    def on_check_failed(error_msg):
        logger.warning(f"Startup update check failed: {error_msg}")
    
    update_checker.update_available.connect(on_update_available)
    update_checker.check_failed.connect(on_check_failed)
    
    return update_checker

def show_update_dialog(widget, version_info, update_checker):
    from src.ui.pages.update_interface import UpdateNotificationDialog
    from src.core.version_manager import __version__
    
    main_window = None
    if hasattr(widget, 'main_window') and widget.main_window:
        main_window = widget.main_window
    else:
        main_window = widget.open_main_window()
    
    dialog = UpdateNotificationDialog(version_info, __version__, main_window)
    
    def on_update_now():
        main_window.switchTo(main_window.update_interface)
        
        update_widget = main_window.update_interface.update_widget
        if update_widget:
            update_widget.selected_version = version_info
            update_widget.start_download(version_info)
    
    def on_remind_later():
        logger.info("User chose to be reminded later")
    
    dialog.update_now.connect(on_update_now)
    dialog.remind_later.connect(on_remind_later)
    dialog.show()

def check_and_create_shortcut_async():
    """后台线程：按需检查并创建桌面快捷方式"""
    def _worker():
        from src.core.shortcut_utils import shortcut_exists, create_desktop_shortcut
        if not shortcut_exists():
            success, message = create_desktop_shortcut(replace_existing=False)
            if success:
                logger.debug(f"Auto-created desktop shortcut: {message}")
    threading.Thread(target=_worker, daemon=True).start()

def main():
    global logger, tr

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import QSettings
    from src.splash_screen import SplashScreen
    from src.core.i18n import I18nManager, tr
    from src.core.logger import setup_logger
    from src.resource_utils import resource_path

    app = QApplication(sys.argv)
    # 显示启动画面（立即显示，让用户知道程序正在启动）
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    logger = setup_logger()

    from qfluentwidgets import setThemeColor
    from src.core.app_theme import THEME_COLOR
    setThemeColor(THEME_COLOR)

    splash.set_status(tr("splash.checking_dependencies", default="正在检查运行环境..."), 5)
    app.processEvents()
    from src.core.dependency_checker import check_and_exit_on_failure
    check_and_exit_on_failure()

    logger.info("Application started.")

    # 初始化多语言模块
    i18n = I18nManager.get_instance()
    i18n.initialize()
    logger.info(f"Language: {i18n.current_language}")

    icon_path = resource_path("data/icons/app.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    try:
        import ctypes
        app_id = "DoroPet.Application.v3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        logger.warning(f"Failed to set AppUserModelID: {e}")

    app.setQuitOnLastWindowClosed(False)

    splash.set_status(tr("splash.loading_provider"), 20)
    app.processEvents()
    init_provider_framework()

    splash.set_status(tr("splash.loading_agent"), 35)
    app.processEvents()
    init_agent_framework()

    qss_path = resource_path("themes/light.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            logger.info(f"Loaded stylesheet: {qss_path}")
        except Exception as e:
            logger.error(f"Failed to load stylesheet: {e}")
    else:
        logger.warning(f"Stylesheet not found: {qss_path}")

    logger.info("Initializing Live2DWidget...")
    splash.set_status(tr("splash.loading_live2d", default="正在加载 Live2D 模型..."), 50)
    app.processEvents()

    from src.core.database import DatabaseManager
    from src.live2dview import Live2DWidget
    from src.ui.main_window import MainWindow
    db_manager = DatabaseManager()
    default_model_path = resource_path("models/Doro/Doro.model3.json")

    try:
        personas = db_manager.personas.get_personas()
        if personas:
            first_persona = personas[0]
            if len(first_persona) > 7 and first_persona[7]:
                saved_model = first_persona[7]
                if os.path.exists(saved_model):
                    default_model_path = saved_model
                    logger.info(f"Using saved model from persona: {saved_model}")
    except Exception as e:
        logger.warning(f"Failed to load model from database: {e}")

    w = Live2DWidget(path=default_model_path)

    settings = QSettings("DoroPet", "Settings")
    hide_pet_on_startup = settings.value("hide_pet_on_startup", False, type=bool)

    # ---- 提前初始化主界面（避免首次打开时的创建延迟）----
    splash.set_status(tr("splash.loading_live2d", default="正在准备主界面..."), 75)
    app.processEvents()
    w.main_window = MainWindow(version_manager=None)
    w.main_window.set_live2d_widget(w)
    w.main_window.hide()  # 隐藏，等用户点击时才显示
    logger.info("MainWindow pre-initialized")

    if hide_pet_on_startup:
        w.hide()
        w.main_window.show()
        logger.info("Pet hidden on startup, showing main window instead.")
    else:
        w.show()

    tray_icon = setup_tray_icon(app, w)

    if not hide_pet_on_startup:
        w.talk(tr("pet.welcome_back"))

    splash.set_status(tr("splash.loading_live2d", default="即将完成..."), 92)
    app.processEvents()

    splash.close_splash()
    logger.info("Splash screen closed")

    # 后台检查并创建桌面快捷方式（已禁用自动创建）
    # check_and_create_shortcut_async()

    update_checker = setup_startup_update_checker(w)
    w._startup_checker = update_checker
    # 将更新检查器的 version_manager 同步到主窗口
    if hasattr(w, 'main_window') and w.main_window:
        version_mgr = update_checker.get_version_manager()
        w.main_window.set_version_manager(version_mgr)
    update_checker.start_check(delay_ms=3000)

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
