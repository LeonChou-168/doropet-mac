from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QProgressDialog
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import (ScrollArea, LineEdit, StrongBodyLabel, 
                            TitleLabel, PushButton, FluentIcon, 
                            BodyLabel, PrimaryPushButton, SwitchButton, 
                            CardWidget, IconWidget, HyperlinkButton, InfoBar, InfoBarPosition, isDarkTheme)
import os
from src.core.downloader import ModelDownloader
from src.core.i18n import I18nManager, tr

class VoiceConfigInterface(QWidget):
    settingsChanged = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("VoiceConfigInterface")
        
        self.init_ui()
        self.load_settings()
        self.update_theme()
        
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        # Title
        self._title_label = TitleLabel(tr("voice.title"), self)
        main_layout.addWidget(self._title_label)

        # --- Enable Switch ---
        self.enable_card = CardWidget(self)
        enable_layout = QHBoxLayout(self.enable_card)
        enable_layout.setContentsMargins(20, 10, 20, 10)
        
        icon_widget = IconWidget(FluentIcon.MICROPHONE, self.enable_card)
        icon_widget.setFixedSize(24, 24)
        enable_layout.addWidget(icon_widget)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        self._enable_title_label = StrongBodyLabel(tr("voice.enable"), self.enable_card)
        text_layout.addWidget(self._enable_title_label)
        self._enable_desc_label = BodyLabel(tr("voice.enable_desc"), self.enable_card)
        text_layout.addWidget(self._enable_desc_label)
        enable_layout.addLayout(text_layout)
        enable_layout.addStretch()
        
        self.enable_switch = SwitchButton(self.enable_card)
        self.enable_switch.setOnText(tr("voice.on"))
        self.enable_switch.setOffText(tr("voice.off"))
        self.enable_switch.checkedChanged.connect(self._on_enable_switch_changed)
        enable_layout.addWidget(self.enable_switch)
        
        main_layout.addWidget(self.enable_card)

        # --- Settings Area ---
        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        # scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.settings_widget = QWidget()
        self.settings_widget.setObjectName("settings_widget")
        form_layout = QVBoxLayout(self.settings_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(15)

        # 1. Wake Word
        self._wake_word_label = StrongBodyLabel(tr("voice.wake_word"), self.settings_widget)
        form_layout.addWidget(self._wake_word_label)
        self.wake_word_input = LineEdit(self.settings_widget)
        self.wake_word_input.setPlaceholderText(tr("voice.wake_word_hint"))
        form_layout.addWidget(self.wake_word_input)
        self._wake_word_tip_label = BodyLabel(tr("voice.wake_word_tip"), self.settings_widget)
        form_layout.addWidget(self._wake_word_tip_label)

        # 2. Model Paths
        self._kws_path_label = StrongBodyLabel(tr("voice.kws_path"), self.settings_widget)
        form_layout.addWidget(self._kws_path_label)
        kws_layout = QHBoxLayout()
        self.kws_input = LineEdit(self.settings_widget)
        self.kws_btn = PushButton(FluentIcon.FOLDER, tr("voice.select"), self.settings_widget)
        self.kws_btn.clicked.connect(lambda: self.select_folder(self.kws_input))
        kws_layout.addWidget(self.kws_input)
        kws_layout.addWidget(self.kws_btn)
        form_layout.addLayout(kws_layout)

        self._asr_path_label = StrongBodyLabel(tr("voice.asr_path"), self.settings_widget)
        form_layout.addWidget(self._asr_path_label)
        asr_layout = QHBoxLayout()
        self.asr_input = LineEdit(self.settings_widget)
        self.asr_btn = PushButton(FluentIcon.FOLDER, tr("voice.select"), self.settings_widget)
        self.asr_btn.clicked.connect(lambda: self.select_folder(self.asr_input))
        asr_layout.addWidget(self.asr_input)
        asr_layout.addWidget(self.asr_btn)
        form_layout.addLayout(asr_layout)

        # Download Link
        link_layout = QHBoxLayout()
        self._download_more_label = BodyLabel(tr("voice.download_more"), self.settings_widget)
        link_layout.addWidget(self._download_more_label)
        self.link_btn = HyperlinkButton("https://github.com/k2-fsa/sherpa-onnx/releases", tr("voice.model_repo"), self.settings_widget)
        self.link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/k2-fsa/sherpa-onnx/releases")))
        link_layout.addWidget(self.link_btn)
        
        # Download Button
        self.download_btn = PushButton(FluentIcon.DOWNLOAD, tr("voice.download_default"), self.settings_widget)
        self.download_btn.clicked.connect(self.download_default_models)
        link_layout.addWidget(self.download_btn)

        link_layout.addStretch()
        form_layout.addLayout(link_layout)

        form_layout.addStretch()
        
        scroll.setWidget(self.settings_widget)
        main_layout.addWidget(scroll)

        # --- Save Button ---
        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("voice.save_config"), self)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)

    def refresh_ui(self, lang=None):
        self._title_label.setText(tr("voice.title"))
        self._enable_title_label.setText(tr("voice.enable"))
        self._enable_desc_label.setText(tr("voice.enable_desc"))
        self.enable_switch.setOnText(tr("voice.on"))
        self.enable_switch.setOffText(tr("voice.off"))
        self._wake_word_label.setText(tr("voice.wake_word"))
        self.wake_word_input.setPlaceholderText(tr("voice.wake_word_hint"))
        self._wake_word_tip_label.setText(tr("voice.wake_word_tip"))
        self._kws_path_label.setText(tr("voice.kws_path"))
        self.kws_btn.setText(tr("voice.select"))
        self._asr_path_label.setText(tr("voice.asr_path"))
        self.asr_btn.setText(tr("voice.select"))
        self._download_more_label.setText(tr("voice.download_more"))
        self.link_btn.setText(tr("voice.model_repo"))
        self.download_btn.setText(tr("voice.download_default"))
        self.save_btn.setText(tr("voice.save_config"))

    def load_settings(self):
        settings = self.db.get_voice_settings()
        if settings:
            self.enable_switch.blockSignals(True)
            self.enable_switch.setChecked(bool(settings[0]))
            self.enable_switch.blockSignals(False)
            self.wake_word_input.setText(settings[1])
            self.kws_input.setText(settings[2])
            self.asr_input.setText(settings[3])

    def _on_enable_switch_changed(self, checked):
        is_enabled = 1 if checked else 0
        wake_word = self.wake_word_input.text().strip()
        kws_path = self.kws_input.text().strip()
        asr_path = self.asr_input.text().strip()
        
        self.db.update_voice_settings(is_enabled, wake_word, kws_path, asr_path)
        self.settingsChanged.emit()

    def save_settings(self):
        is_enabled = 1 if self.enable_switch.isChecked() else 0
        wake_word = self.wake_word_input.text().strip()
        kws_path = self.kws_input.text().strip()
        asr_path = self.asr_input.text().strip()
        
        self.db.update_voice_settings(is_enabled, wake_word, kws_path, asr_path)
        
        # Show success message
        InfoBar.success(
            title=tr("general.success"),
            content=tr("voice.save_success"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
        )
        
        self.settingsChanged.emit()

    def select_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, tr("voice.select_dir"))
        if folder:
            line_edit.setText(folder)

    def update_theme(self):
        # Styles are handled by global QSS
        pass

    def download_default_models(self):
        models_dir = os.path.join(os.getcwd(), "models", "voice")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        kws_model_name = "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
        asr_model_name = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
        
        # Prepare tasks
        tasks = []
        
        # KWS Task
        kws_target = os.path.join(models_dir, f"{kws_model_name}.tar.bz2")
        # Check if already extracted (simple check)
        if not os.path.exists(os.path.join(models_dir, kws_model_name, "tokens.txt")):
             tasks.append({
                "name": tr("voice.kws_model"),
                "filename": kws_target,
                "urls": [
                    f"https://mirror.ghproxy.com/https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/{kws_model_name}.tar.bz2",
                    f"https://ghproxy.net/https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/{kws_model_name}.tar.bz2",
                    f"https://moeyy.cn/gh-proxy/https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/{kws_model_name}.tar.bz2"
                ],
                "extract_to": models_dir
            })

        # ASR Task
        asr_target = os.path.join(models_dir, f"{asr_model_name}.tar.bz2")
        if not os.path.exists(os.path.join(models_dir, asr_model_name, "tokens.txt")):
            tasks.append({
                "name": tr("voice.asr_model"),
                "filename": asr_target,
                "urls": [
                    f"https://mirror.ghproxy.com/https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{asr_model_name}.tar.bz2",
                    f"https://ghproxy.net/https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{asr_model_name}.tar.bz2",
                    f"https://moeyy.cn/gh-proxy/https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{asr_model_name}.tar.bz2"
                ],
                "extract_to": models_dir
            })
            
        if not tasks:
            InfoBar.info(tr("general.tip"), tr("voice.model_exists"), parent=self)
            return

        # Setup Progress Dialog
        self.progress_dialog = QProgressDialog(tr("voice.preparing"), tr("general.cancel"), 0, 100, self)
        self.progress_dialog.setWindowTitle(tr("voice.download_model"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.resize(400, 100)
        
        # Start Downloader
        self.downloader = ModelDownloader(tasks)
        self.downloader.progress_updated.connect(self.update_download_progress)
        self.downloader.download_finished.connect(self.on_download_finished)
        self.progress_dialog.canceled.connect(self.downloader.cancel)
        
        self.downloader.start()
        self.progress_dialog.show()

    def update_download_progress(self, task_name, percent, speed):
        if self.progress_dialog.wasCanceled():
            return
        self.progress_dialog.setLabelText(tr("voice.download_speed", default="{task}\n速度: {speed}").format(task=task_name, speed=speed))
        self.progress_dialog.setValue(percent)

    def on_download_finished(self, success, message):
        self.progress_dialog.close()
        if success:
            InfoBar.success(tr("voice.download_complete"), tr("voice.download_complete"), parent=self)
            
            # Auto-fill paths
            cwd = os.getcwd()
            kws_model = "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
            asr_model = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
            
            kws_path = os.path.join(cwd, "models", "voice", kws_model)
            asr_path = os.path.join(cwd, "models", "voice", asr_model)
            
            self.kws_input.setText(kws_path)
            self.asr_input.setText(asr_path)
            
            # Save automatically
            self.save_settings()
        else:
            if "cancelled" in str(message).lower():
                InfoBar.warning(tr("voice.download_cancelled"), tr("voice.download_cancelled"), parent=self)
            else:
                InfoBar.error(tr("voice.download_failed"), str(message), parent=self)
