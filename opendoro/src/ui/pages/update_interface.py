import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QTextEdit, QProgressBar, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush
from qfluentwidgets import (
    ScrollArea, TitleLabel, StrongBodyLabel, BodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, ProgressRing, CardWidget,
    FluentIcon as FIF, InfoBar, InfoBarPosition, SwitchButton,
    SubtitleLabel, isDarkTheme, MessageBox
)
from src.core.version_manager import (
    VersionManager, VersionInfo, ReleaseType, get_version_type_display,
    compare_versions, __version__
)
from src.core.logger import logger
from src.core.i18n import I18nManager, tr


class VersionListItem(QWidget):
    def __init__(self, version_info: VersionInfo, is_current: bool, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.is_current = is_current
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        version_row = QHBoxLayout()
        version_label = StrongBodyLabel(f"v{self.version_info.version}", self)
        version_row.addWidget(version_label)
        
        type_label = CaptionLabel(get_version_type_display(self.version_info.release_type), self)
        type_label.setObjectName("versionTypeLabel")
        type_label.setProperty("releaseType", self.version_info.release_type.value)
        type_label.setAttribute(Qt.WA_StyledBackground, True)
        version_row.addWidget(type_label)
        
        if self.is_current:
            current_label = CaptionLabel(tr("update.current_version"), self)
            current_label.setObjectName("currentVersionLabel")
            current_label.setAttribute(Qt.WA_StyledBackground, True)
            version_row.addWidget(current_label)
        
        version_row.addStretch()
        info_layout.addLayout(version_row)
        
        date_label = CaptionLabel(tr("update.published").format(date=self.version_info.release_date), self)
        date_label.setObjectName("versionDateLabel")
        info_layout.addWidget(date_label)
        
        layout.addLayout(info_layout, 1)
        
        if self.version_info.file_size > 0:
            size_label = CaptionLabel(self.version_info.display_size, self)
            size_label.setObjectName("versionSizeLabel")
            layout.addWidget(size_label)


class UpdateWidget(CardWidget):
    update_available = pyqtSignal(VersionInfo)
    download_completed = pyqtSignal(str)
    
    def __init__(self, parent=None, version_manager=None):
        super().__init__(parent)
        self.version_manager = version_manager if version_manager else VersionManager(self)
        self.selected_version: VersionInfo = None
        self._is_loading = False
        self._external_version_manager = version_manager is not None
        self.setup_ui()
        self.connect_signals()
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)
        if not self._external_version_manager:
            self.load_versions()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        self._title_label = TitleLabel(tr("update.title"), self)
        title_layout.addWidget(self._title_label)
        
        current_version_text = f"{tr('update.current_version')}: v{self.version_manager.current_version}"
        self.current_version_label = BodyLabel(current_version_text, self)
        self.current_version_label.setObjectName("currentVersionTextLabel")
        title_layout.addWidget(self.current_version_label)
        
        header_layout.addLayout(title_layout, 1)
        
        self.refresh_btn = PushButton(FIF.SYNC, tr("update.check_update"), self)
        self.refresh_btn.clicked.connect(self.check_for_updates)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        self.status_card = QWidget(self)
        self.status_card.setObjectName("updateStatusCard")
        status_layout = QHBoxLayout(self.status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        
        self.status_icon = ProgressRing(self)
        self.status_icon.setFixedSize(24, 24)
        self.status_icon.setStrokeWidth(3)
        self.status_icon.hide()
        status_layout.addWidget(self.status_icon)
        
        self.status_label = BodyLabel("", self)
        status_layout.addWidget(self.status_label, 1)
        
        self.update_btn = PrimaryPushButton(FIF.DOWNLOAD, tr("update.update_now"), self)
        self.update_btn.hide()
        self.update_btn.clicked.connect(self.on_update_clicked)
        status_layout.addWidget(self.update_btn)
        
        self.status_card.hide()
        main_layout.addWidget(self.status_card)
        
        self.download_widget = QWidget(self)
        self.download_widget.setObjectName("downloadProgressWidget")
        download_layout = QVBoxLayout(self.download_widget)
        download_layout.setContentsMargins(12, 12, 12, 12)
        download_layout.setSpacing(8)
        
        download_header = QHBoxLayout()
        self.download_label = BodyLabel(tr("update.downloading"), self)
        download_header.addWidget(self.download_label, 1)
        
        self.download_speed = CaptionLabel("", self)
        download_header.addWidget(self.download_speed)
        
        self.download_percent = CaptionLabel("0%", self)
        download_header.addWidget(self.download_percent)
        download_layout.addLayout(download_header)
        
        self.download_progress = QProgressBar(self)
        self.download_progress.setObjectName("downloadProgressBar")
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setTextVisible(False)
        self.download_progress.setFixedHeight(6)
        download_layout.addWidget(self.download_progress)
        
        download_btn_layout = QHBoxLayout()
        download_btn_layout.addStretch()
        self.cancel_download_btn = PushButton(tr("update.cancel_download"), self)
        self.cancel_download_btn.clicked.connect(self.cancel_download)
        download_btn_layout.addWidget(self.cancel_download_btn)
        download_layout.addLayout(download_btn_layout)
        
        self.download_widget.hide()
        main_layout.addWidget(self.download_widget)
        
        self.install_widget = QWidget(self)
        self.install_widget.setObjectName("installProgressWidget")
        install_layout = QVBoxLayout(self.install_widget)
        install_layout.setContentsMargins(12, 12, 12, 12)
        install_layout.setSpacing(8)
        
        install_header = QHBoxLayout()
        self.install_label = BodyLabel(tr("update.installing"), self)
        install_header.addWidget(self.install_label, 1)
        
        self.install_percent = CaptionLabel("", self)
        install_header.addWidget(self.install_percent)
        install_layout.addLayout(install_header)
        
        self.install_progress = QProgressBar(self)
        self.install_progress.setObjectName("installProgressBar")
        self.install_progress.setRange(0, 100)
        self.install_progress.setValue(0)
        self.install_progress.setTextVisible(False)
        self.install_progress.setFixedHeight(6)
        install_layout.addWidget(self.install_progress)
        
        self.install_step_label = CaptionLabel("", self)
        install_layout.addWidget(self.install_step_label)
        
        self._install_info_label = CaptionLabel(tr("update.will_restart"), self)
        self._install_info_label.setObjectName("installInfoLabel")
        install_layout.addWidget(self._install_info_label)
        
        self.install_widget.hide()
        main_layout.addWidget(self.install_widget)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        list_header = QHBoxLayout()
        self._list_title_label = StrongBodyLabel(tr("update.history_versions"), self)
        list_header.addWidget(self._list_title_label, 1)
        
        self.show_beta_switch = SwitchButton(tr("update.include_beta"), self)
        self.show_beta_switch.setChecked(False)
        self.show_beta_switch.checkedChanged.connect(self.on_show_beta_changed)
        list_header.addWidget(self.show_beta_switch)
        
        left_layout.addLayout(list_header)
        
        self.version_list = QListWidget(self)
        self.version_list.setObjectName("versionListWidget")
        self.version_list.setFixedHeight(250)
        self.version_list.currentItemChanged.connect(self.on_version_selected)
        left_layout.addWidget(self.version_list)
        
        content_layout.addWidget(left_widget, 2)
        
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        self._changelog_title_label = StrongBodyLabel(tr("update.changelog"), self)
        right_layout.addWidget(self._changelog_title_label)
        
        self.changelog_text = QTextEdit(self)
        self.changelog_text.setObjectName("changelogTextEdit")
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setFixedHeight(250)
        self.changelog_text.setPlaceholderText(tr("update.select_version"))
        right_layout.addWidget(self.changelog_text)
        
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.download_version_btn = PrimaryPushButton(FIF.DOWNLOAD, tr("update.download_version"), self)
        self.download_version_btn.setEnabled(False)
        self.download_version_btn.clicked.connect(self.on_download_version_clicked)
        action_layout.addWidget(self.download_version_btn)
        
        right_layout.addLayout(action_layout)
        content_layout.addWidget(right_widget, 3)
        
        main_layout.addLayout(content_layout)
    
    def refresh_ui(self, lang=None):
        self._title_label.setText(tr("update.title"))
        self.current_version_label.setText(f"{tr('update.current_version')}: v{self.version_manager.current_version}")
        self.refresh_btn.setText(tr("update.check_update"))
        self.update_btn.setText(tr("update.update_now"))
        self.download_label.setText(tr("update.downloading"))
        self.cancel_download_btn.setText(tr("update.cancel_download"))
        self.install_label.setText(tr("update.installing"))
        self._install_info_label.setText(tr("update.will_restart"))
        self._list_title_label.setText(tr("update.history_versions"))
        self.show_beta_switch.setText(tr("update.include_beta"))
        self._changelog_title_label.setText(tr("update.changelog"))
        self.changelog_text.setPlaceholderText(tr("update.select_version"))
        self.download_version_btn.setText(tr("update.download_version"))
        self.refresh_version_list(self.version_manager.get_all_versions())
    
    def connect_signals(self):
        self.version_manager.versions_loaded.connect(self.on_versions_loaded)
        self.version_manager.load_error.connect(self.on_load_error)
        self.version_manager.download_progress.connect(self.on_download_progress)
        self.version_manager.download_completed.connect(self.on_download_completed)
        self.version_manager.download_error.connect(self.on_download_error)
        self.version_manager.install_progress.connect(self.on_install_progress)
        self.version_manager.install_completed.connect(self.on_install_completed)
        self.version_manager.install_error.connect(self.on_install_error)
    
    def load_versions(self):
        self._is_loading = True
        self.version_list.clear()
        self.changelog_text.clear()
        self.download_version_btn.setEnabled(False)
        
        self.status_card.show()
        self.status_icon.show()
        self.status_label.setText(tr("update.fetching"))
        self.update_btn.hide()
        
        self.version_manager.fetch_remote_versions()
    
    def on_versions_loaded(self, versions):
        self._is_loading = False
        self.refresh_version_list(versions)
        self.check_for_updates()
    
    def set_versions(self, versions):
        self._is_loading = False
        self.refresh_version_list(versions)
        self._check_update_status()
    
    def _check_update_status(self):
        include_beta = self.show_beta_switch.isChecked()
        latest = self.version_manager.check_for_updates(include_beta)
        
        self.refresh_btn.setEnabled(True)
        self.status_icon.hide()
        
        if latest:
            self.status_label.setText(tr("update.new_version_found").replace("{latest.version}", str(latest.version)))
            self.update_btn.show()
            self.selected_version = latest
            self.status_card.setProperty("status", "updateAvailable")
        else:
            self.status_label.setText(tr("update.already_latest"))
            self.status_card.setProperty("status", "upToDate")
        
        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.show()
    
    def on_load_error(self, error_msg):
        self._is_loading = False
        self.status_icon.hide()
        self.status_label.setText(tr("update.fetch_failed").replace("{error_msg}", error_msg))
        self.status_card.show()
        
        versions = self.version_manager.get_all_versions()
        if versions:
            self.refresh_version_list(versions)
    
    def refresh_version_list(self, versions):
        self.version_list.clear()
        show_beta = self.show_beta_switch.isChecked()
        current_ver = self.version_manager.current_version
        
        for v in versions:
            if not show_beta and v.release_type != ReleaseType.STABLE:
                continue
            
            item = QListWidgetItem(self.version_list)
            is_current = v.version == current_ver
            widget = VersionListItem(v, is_current)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, v)
            self.version_list.addItem(item)
            self.version_list.setItemWidget(item, widget)
    
    def on_show_beta_changed(self, checked):
        versions = self.version_manager.get_all_versions()
        self.refresh_version_list(versions)
    
    def check_for_updates(self):
        self.refresh_btn.setEnabled(False)
        self.status_card.show()
        self.status_icon.show()
        self.status_label.setText(tr("update.checking"))
        self.update_btn.hide()
        
        if self._is_loading:
            return
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._do_check_update)
    
    def _do_check_update(self):
        include_beta = self.show_beta_switch.isChecked()
        latest = self.version_manager.check_for_updates(include_beta)
        
        self.refresh_btn.setEnabled(True)
        self.status_icon.hide()
        
        if latest:
            self.status_label.setText(tr("update.new_version_found").replace("{latest.version}", str(latest.version)))
            self.update_btn.show()
            self.selected_version = latest
            self.status_card.setProperty("status", "updateAvailable")
        else:
            self.status_label.setText(tr("update.already_latest"))
            self.status_card.setProperty("status", "upToDate")
        
        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.show()
    
    def on_version_selected(self, current, previous):
        if not current:
            self.changelog_text.clear()
            self.download_version_btn.setEnabled(False)
            return
        
        version_info = current.data(Qt.UserRole)
        if version_info:
            self.selected_version = version_info
            self.changelog_text.setMarkdown(version_info.changelog)
            
            current_ver = self.version_manager.current_version
            can_download = compare_versions(version_info.version, current_ver) != 0
            self.download_version_btn.setEnabled(can_download)
    
    def on_update_clicked(self):
        if self.selected_version:
            self.start_download(self.selected_version)
    
    def on_download_version_clicked(self):
        if self.selected_version:
            self.start_download(self.selected_version)
    
    def start_download(self, version: VersionInfo):
        if not version.download_url:
            InfoBar.warning(
                title=tr("update.no_download_link"),
                content=tr("update.no_download_link"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        box = MessageBox(
            tr("update.confirm_update"),
            tr("update.confirm_message").replace("{version}", str(version.version)),
            self
        )
        box.yesButton.setText(tr("update.start_update"))
        box.cancelButton.setText(tr("general.cancel"))
        
        if not box.exec_():
            return
        
        self.download_widget.show()
        self.status_card.hide()
        self.install_widget.hide()
        self.download_label.setText(tr("update.downloading"))
        self.download_progress.setValue(0)
        self.download_percent.setText("0%")
        self.download_speed.setText("")
        
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "DoroPet_Updates")
        self.version_manager.download_update(version, default_path, auto_install=True)
    
    def on_download_progress(self, percent, total_bytes, speed_str=""):
        self.download_progress.setValue(percent)
        self.download_percent.setText(f"{percent}%")
        if speed_str:
            self.download_speed.setText(speed_str)
    
    def on_download_completed(self, file_path):
        self.download_widget.hide()
        self.install_widget.show()
        self.install_label.setText(tr("update.installing"))
        self.install_progress.setValue(0)
        self.install_percent.setText("0%")
        self.install_step_label.setText(tr("update.installing_ready"))
        
        self.download_completed.emit(file_path)
    
    def on_download_error(self, error_msg):
        self.download_widget.hide()
        self.install_widget.hide()
        self.status_card.show()
        
        InfoBar.error(
            title=tr("update.download_failed"),
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def on_install_progress(self, step_text: str, percent: int):
        self.install_progress.setValue(percent)
        self.install_percent.setText(f"{percent}%")
        self.install_step_label.setText(step_text)
    
    def on_install_completed(self):
        self.install_step_label.setText(tr("update.restarting"))
        self.install_progress.setValue(100)
        self.install_percent.setText("100%")
        
        InfoBar.success(
            title=tr("update.update_complete"),
            content=tr("update.will_restart_3s"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, self._restart_application)
    
    def on_install_error(self, error_msg):
        self.install_widget.hide()
        self.status_card.show()
        
        InfoBar.error(
            title=tr("update.install_failed"),
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def _restart_application(self):
        import sys
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
        sys.exit(0)
    
    def cancel_download(self):
        self.version_manager.cancel_download()
        self.download_widget.hide()
        self.status_card.show()
        self.install_widget.hide()
        
        InfoBar.warning(
            title=tr("update.cancelled"),
            content=tr("update.cancelled"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )


class AboutWidget(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        self._about_title = TitleLabel(tr("update.about"), self)
        layout.addWidget(self._about_title)
        
        info_widget = QWidget(self)
        info_widget.setObjectName("aboutInfoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)
        
        info_layout.addWidget(StrongBodyLabel("DoroPet", self))
        
        self._version_label = BodyLabel(tr("update.version_prefix").format(version=__version__), self)
        info_layout.addWidget(self._version_label)
        
        self._desc_label = BodyLabel(tr("update.description"), self)
        info_layout.addWidget(self._desc_label)
        self._copyright_label = CaptionLabel("", self)
        info_layout.addWidget(self._copyright_label)
        
        layout.addWidget(info_widget)
        
        disclaimer_widget = QWidget(self)
        disclaimer_widget.setObjectName("aboutInfoWidget")
        disclaimer_layout = QVBoxLayout(disclaimer_widget)
        disclaimer_layout.setContentsMargins(12, 12, 12, 12)
        disclaimer_layout.setSpacing(8)
        
        self._author_statement_label = StrongBodyLabel(tr("update.author_statement"), self)
        disclaimer_layout.addWidget(self._author_statement_label)
        
        self._disclaimer_label = BodyLabel(tr("update.disclaimer"), self)
        self._disclaimer_label.setWordWrap(True)
        disclaimer_layout.addWidget(self._disclaimer_label)
        
        self._footer_text = BodyLabel(tr("update.free_notice"), self)
        self._footer_text.setWordWrap(True)
        disclaimer_layout.addWidget(self._footer_text)
        
        layout.addWidget(disclaimer_widget)
        
        link_layout = QHBoxLayout()
        link_layout.setSpacing(16)
        
        self._gitee_btn = PushButton(FIF.GITHUB, tr("update.gitee"), self)
        self._gitee_btn.clicked.connect(self.open_gitee)
        link_layout.addWidget(self._gitee_btn)
        
        self._github_btn = PushButton(FIF.GITHUB, tr("update.github"), self)
        self._github_btn.clicked.connect(self.open_github)
        link_layout.addWidget(self._github_btn)
        
        self._website_btn = PushButton(FIF.LINK, tr("update.website"), self)
        self._website_btn.clicked.connect(self.open_official)
        link_layout.addWidget(self._website_btn)
        
        self._qq_btn = PushButton(FIF.PEOPLE, tr("update.qq_group"), self)
        self._qq_btn.clicked.connect(self.open_qq_group)
        link_layout.addWidget(self._qq_btn)
        
        self._donate_btn = PushButton(FIF.HEART, tr("update.donate"), self)
        self._donate_btn.clicked.connect(self.open_sponsor)
        link_layout.addWidget(self._donate_btn)
        
        link_layout.addStretch()
        layout.addLayout(link_layout)
    
    def refresh_ui(self, lang=None):
        self._about_title.setText(tr("update.about"))
        self._version_label.setText(tr("update.version_prefix").format(version=__version__))
        self._desc_label.setText(tr("update.description"))
        self._author_statement_label.setText(tr("update.author_statement"))
        self._copyright_label.setText(tr("update.copyright"))
        self._disclaimer_label.setText(tr("update.disclaimer"))
        self._footer_text.setText(tr("update.free_notice"))
        self._gitee_btn.setText(tr("update.gitee"))
        self._github_btn.setText(tr("update.github"))
        self._website_btn.setText(tr("update.website"))
        self._qq_btn.setText(tr("update.qq_group"))
        self._donate_btn.setText(tr("update.donate"))
    
    def open_gitee(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://gitee.com/waterfeet/DoroPet_V3"))
    
    def open_github(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://github.com/waterfeet/DoroPet_V3"))
    
    def open_official(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://www.waterfeetbot.top/"))
    
    def open_qq_group(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://qm.qq.com/q/oOprHW3Rv4"))
    
    def open_sponsor(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://www.ifdian.net/a/waterfeet"))


class UpdateNotificationDialog(QWidget):
    """更新通知弹窗 —— 继承 BaseDialog 的统一视觉风格。"""
    update_now = pyqtSignal()
    remind_later = pyqtSignal()

    def __init__(self, version_info: VersionInfo, current_version: str, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.current_version = current_version

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 420)

        self._setup_ui()
        self._center_on_parent()

    def _setup_ui(self):
        from src.ui.design_tokens import get_tokens, get_token, BRAND_PRIMARY, scrollbar_qss
        t = get_tokens()

        self.setObjectName("updateNotificationDialog")

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60 if isDarkTheme() else 20))
        shadow.setOffset(0, 5)

        # 容器
        self._container = QWidget(self)
        self._container.setObjectName("updateDialogContainer")
        self._container.setGeometry(10, 10, 440, 400)
        self._container.setGraphicsEffect(shadow)

        # 毛玻璃背景
        bg_color = t['bg_glass'] if 'bg_glass' in t else (
            "rgba(32, 36, 48, 220)" if isDarkTheme() else "rgba(255, 255, 255, 230)"
        )
        border_color = t['border_strong'] if 'border_strong' in t else (
            "rgba(255,255,255,12)" if isDarkTheme() else "rgba(0,0,0,10)"
        )
        self._container.setStyleSheet(f"""
            QWidget#updateDialogContainer {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # ---- 标题栏 ----
        header_layout = QHBoxLayout()

        self.title_icon = QLabel("🎁")
        self.title_icon.setFixedSize(28, 28)
        self.title_icon.setStyleSheet("font-size: 20px; background: transparent;")
        header_layout.addWidget(self.title_icon)

        self.title_label = TitleLabel(tr("update.new_version_found"), self._container)
        header_layout.addWidget(self.title_label, 1)

        self.close_btn = PushButton(FIF.CANCEL, "", self._container)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(self.close_btn)

        main_layout.addLayout(header_layout)

        # ---- 版本对比卡片 ----
        ver_card = QWidget(self._container)
        card_bg = t['input_bg'] if 'input_bg' in t else (
            "rgba(255,255,255,6)" if isDarkTheme() else "rgba(0,0,0,4)"
        )
        ver_card.setStyleSheet(
            f"background-color: {card_bg}; border-radius: 10px;"
        )
        version_layout = QHBoxLayout(ver_card)
        version_layout.setContentsMargins(14, 10, 14, 10)
        version_layout.setSpacing(16)

        old_ver_layout = QVBoxLayout()
        old_ver_layout.setSpacing(2)
        old_label = QLabel(tr("update.current_version"))
        old_label.setStyleSheet(
            f"color: {t.get('text_secondary','#888')}; font-size: 12px; background: transparent;"
        )
        old_label.setAlignment(Qt.AlignCenter)
        old_ver_layout.addWidget(old_label)

        old_value = QLabel(f"v{self.current_version}")
        old_value.setAlignment(Qt.AlignCenter)
        old_value.setStyleSheet(
            f"color: {t.get('text_primary','#fff')}; font-size: 16px; font-weight: bold; background: transparent;"
        )
        old_ver_layout.addWidget(old_value)
        version_layout.addLayout(old_ver_layout)

        arrow = QLabel("→")
        arrow.setStyleSheet(
            f"font-size: 18px; color: {BRAND_PRIMARY}; background: transparent;"
        )
        version_layout.addWidget(arrow)

        new_ver_layout = QVBoxLayout()
        new_ver_layout.setSpacing(2)
        new_label = QLabel(tr("update.latest_version"))
        new_label.setAlignment(Qt.AlignCenter)
        new_label.setStyleSheet(
            f"color: {t.get('text_secondary','#888')}; font-size: 12px; background: transparent;"
        )
        new_ver_layout.addWidget(new_label)

        new_value = QLabel(f"v{self.version_info.version}")
        new_value.setAlignment(Qt.AlignCenter)
        new_value.setStyleSheet(
            f"color: {BRAND_PRIMARY}; font-size: 16px; font-weight: bold; background: transparent;"
        )
        new_ver_layout.addWidget(new_value)
        version_layout.addLayout(new_ver_layout)

        version_layout.addStretch()

        type_text = get_version_type_display(self.version_info.release_type)
        type_label = QLabel(type_text)
        type_label.setStyleSheet(
            f"background-color: {BRAND_PRIMARY}; color: white; "
            "padding: 2px 10px; border-radius: 4px; font-size: 12px;"
        )
        version_layout.addWidget(type_label)

        main_layout.addWidget(ver_card)

        # ---- 更新内容 ----
        changelog_header = QLabel(tr("update.update_content"))
        changelog_header.setStyleSheet(
            f"color: {t.get('text_primary','#333')}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        main_layout.addWidget(changelog_header)

        text_bg = t['input_bg'] if 'input_bg' in t else (
            "rgba(255,255,255,6)" if isDarkTheme() else "rgba(0,0,0,3)"
        )
        text_color = t.get('text_primary', '#333')
        border_c = t.get('border_default', 'rgba(0,0,0,10)')
        self.changelog_text = QTextEdit(self._container)
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setFixedHeight(110)
        self.changelog_text.setStyleSheet(
            f"background-color: {text_bg}; "
            f"border: 1px solid {border_c}; "
            f"border-radius: 8px; "
            f"color: {text_color}; font-size: 12px; padding: 6px;"
            + scrollbar_qss()
        )
        changelog = self.version_info.changelog or tr("update.no_changelog")
        self.changelog_text.setMarkdown(changelog[:500] + ("..." if len(changelog) > 500 else ""))
        main_layout.addWidget(self.changelog_text)

        # ---- 日期和大小信息 ----
        info_layout = QHBoxLayout()
        info_style = f"color: {t.get('text_disabled','#888')}; font-size: 12px; background: transparent;"
        if self.version_info.release_date:
            date_lbl = QLabel(tr("update.published").format(date=self.version_info.release_date))
            date_lbl.setStyleSheet(info_style)
            info_layout.addWidget(date_lbl)
        if self.version_info.file_size > 0:
            size_lbl = QLabel(tr("update.size").format(size=self.version_info.display_size))
            size_lbl.setStyleSheet(info_style)
            info_layout.addWidget(size_lbl)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        main_layout.addStretch()

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        remind_btn = PushButton(FIF.CALENDAR, tr("update.remind_later"), self._container)
        remind_btn.setFixedHeight(36)
        remind_btn.clicked.connect(self._on_remind_later)
        btn_layout.addWidget(remind_btn)

        update_btn = PrimaryPushButton(FIF.UPDATE, tr("update.update_now"), self._container)
        update_btn.setFixedHeight(36)
        update_btn.clicked.connect(self._on_update_now)
        btn_layout.addWidget(update_btn, 1)

        main_layout.addLayout(btn_layout)

    def _center_on_parent(self):
        if self.parent() and self.parent().isVisible():
            geo = self.parent().geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(max(0, x), max(0, y))
        else:
            from PyQt5.QtWidgets import QDesktopWidget
            screen = QDesktopWidget().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def _on_update_now(self):
        self.close()
        self.update_now.emit()

    def _on_remind_later(self):
        self.close()
        self.remind_later.emit()

    def _on_close(self):
        self.remind_later.emit()
        self.close()

    # 拖拽支持
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < 44:
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_is_dragging') and self._is_dragging and hasattr(self, '_drag_pos'):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        if hasattr(self, '_drag_pos'):
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()


class UpdateInterface(ScrollArea):
    def __init__(self, parent=None, version_manager=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("updateView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("UpdateInterface")
        self._version_manager = version_manager
        
        self.setup_ui()
        
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)
    
    def setup_ui(self):
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        
        self.update_widget = UpdateWidget(self, self._version_manager)
        layout.addWidget(self.update_widget)
        
        self.about_widget = AboutWidget(self)
        layout.addWidget(self.about_widget)
        
        layout.addStretch()
    
    def refresh_ui(self, lang=None):
        self.update_widget.refresh_ui(lang)
        self.about_widget.refresh_ui(lang)
    
    def set_versions(self, versions):
        self.update_widget.set_versions(versions)
