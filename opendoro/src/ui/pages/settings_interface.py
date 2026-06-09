from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, CheckBox, Slider, TitleLabel,
                            StrongBodyLabel, CaptionLabel, PushButton, FluentIcon,
                            isDarkTheme, LineEdit, Pivot, CardWidget, BodyLabel,
                            ComboBox, SpinBox, InfoBar, TransparentToolButton)
from src.core.logger import logger
from src.core.i18n import I18nManager, tr


class SettingCard(CardWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        self.title_label = StrongBodyLabel(title, self)
        layout.addWidget(self.title_label)
        
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        layout.addWidget(self.content_widget)
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class GeneralSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings_interface = parent
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self._card = SettingCard(tr("settings.general.title"), self)
        
        self.check_autorun = CheckBox(tr("settings.general.autorun"), self)
        self.check_hide_pet_on_startup = CheckBox(tr("settings.general.hide_pet"), self)
        self.check_mouse_interact = CheckBox(tr("settings.general.mouse_interact"), self)
        self.check_mouse_interact.setChecked(True)
        
        self._card.addWidget(self.check_autorun)
        self._card.addWidget(self.check_hide_pet_on_startup)
        self._card.addWidget(self.check_mouse_interact)
        
        layout.addWidget(self._card)
        
        self._setup_language_card(layout)
        self._setup_cache_management(layout)
        
        self._shortcut_card = SettingCard(tr("settings.general.shortcut"), self)
        
        shortcut_info_layout = QHBoxLayout()
        self._shortcut_info_label = BodyLabel(tr("settings.general.create_shortcut_desc"), self)
        shortcut_info_layout.addWidget(self._shortcut_info_label)
        shortcut_info_layout.addStretch()
        self._shortcut_card.addLayout(shortcut_info_layout)
        
        self.btn_create_shortcut = PushButton(FluentIcon.SHARE, tr("settings.general.create_shortcut_btn"), self)
        self.btn_create_shortcut.setFixedWidth(160)
        
        btn_shortcut_layout = QHBoxLayout()
        btn_shortcut_layout.addStretch()
        btn_shortcut_layout.addWidget(self.btn_create_shortcut)
        self._shortcut_card.addLayout(btn_shortcut_layout)
        
        layout.addWidget(self._shortcut_card)
        layout.addStretch()
        
        self.btn_create_shortcut.clicked.connect(self._create_desktop_shortcut)
        self._refresh_all_cache_sizes()

    def _setup_language_card(self, parent_layout):
        """设置语言选择卡片。"""
        lang_card = SettingCard(tr("settings.general.language"), self)
        
        lang_layout = QHBoxLayout()
        lang_label = BodyLabel(tr("settings.general.language") + ":", self)
        lang_layout.addWidget(lang_label)
        
        self._lang_label = lang_label
        self.lang_combo = ComboBox(self)
        i18n = I18nManager.get_instance()
        for code, info in i18n.languages.items():
            self.lang_combo.addItem(info["display"], userData=code)
        # 设置当前语言
        current = i18n.current_language
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.setFixedWidth(180)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        lang_card.addLayout(lang_layout)
        
        parent_layout.addWidget(lang_card)

    def _on_language_changed(self, index):
        lang_code = self.lang_combo.itemData(index)
        logger.info(f"[I18n] GeneralSettingsPage._on_language_changed: index={index}, lang_code={lang_code}")
        if lang_code:
            i18n = I18nManager.get_instance()
            logger.info(f"[I18n] Calling i18n.set_language({lang_code}), current={i18n.current_language}")
            i18n.set_language(lang_code)

    def _setup_cache_management(self, parent_layout):
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QFrame, QSizePolicy
        from qfluentwidgets import PushButton, FluentIcon, InfoBar
        from src.core.cache_manager import get_cache_manager
        
        self._cache_manager = get_cache_manager()
        self._cache_labels = {}
        self._cache_buttons = {}
        
        self._cache_card = SettingCard(tr("settings.general.cache"), self)
        
        safe_cache_label = StrongBodyLabel(tr("settings.general.safe_cache"), self)
        self._cache_card.addWidget(safe_cache_label)
        self._safe_cache_label = safe_cache_label
        
        safe_caches = [
            ("tts", "settings.cache.tts", "settings.cache.tts_desc", "\ud83d\udd0a"),
            ("image", "settings.cache.image", "settings.cache.image_desc", "\ud83d\uddbc\ufe0f"),
            ("temp_images", "settings.cache.temp_images", "settings.cache.temp_images_desc", "\ud83d\udcc4"),
            ("musicdl", "settings.cache.musicdl", "settings.cache.musicdl_desc", "\ud83c\udfb5"),
            ("old_logs", "settings.cache.old_logs", "settings.cache.old_logs_desc", "\ud83d\udcdd"),
        ]
        
        self._safe_cache_rows = []
        for cache_key, name_key, desc_key, icon in safe_caches:
            row = self._add_cache_row(self._cache_card, cache_key, name_key, desc_key, icon, is_safe=True)
            self._safe_cache_rows.append(row)
        
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self._cache_card.addWidget(separator)
        
        warning_cache_label = StrongBodyLabel("\u26a0\ufe0f " + tr("settings.general.warning_cache"), self)
        self._cache_card.addWidget(warning_cache_label)
        self._warning_cache_label = warning_cache_label
        
        warning_caches = [
            ("music_downloads", "settings.cache.music_downloads", "settings.cache.music_downloads_desc", "\u26a0\ufe0f"),
        ]
        
        self._warning_cache_rows = []
        for cache_key, name_key, desc_key, icon in warning_caches:
            row = self._add_cache_row(self._cache_card, cache_key, name_key, desc_key, icon, is_safe=False)
            self._warning_cache_rows.append(row)
        
        separator2 = QFrame(self)
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        self._cache_card.addWidget(separator2)
        
        total_layout = QHBoxLayout()
        self._total_label = StrongBodyLabel("\ud83d\udcca " + tr("settings.general.total_cache_size") + ":", self)
        total_layout.addWidget(self._total_label)
        
        self._total_cache_label = CaptionLabel("0 MB", self)
        self._total_cache_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        total_layout.addWidget(self._total_cache_label)
        total_layout.addStretch()
        self._cache_card.addLayout(total_layout)
        
        clear_all_layout = QHBoxLayout()
        clear_all_layout.addStretch()
        
        self.btn_clear_all_safe = PushButton(FluentIcon.DELETE, tr("settings.general.clear_all_safe"), self)
        self.btn_clear_all_safe.setFixedWidth(160)
        self.btn_clear_all_safe.clicked.connect(self._clear_all_safe_caches)
        clear_all_layout.addWidget(self.btn_clear_all_safe)
        
        self._cache_card.addLayout(clear_all_layout)
        
        parent_layout.addWidget(self._cache_card)

    def _add_cache_row(self, parent_card, cache_key: str, name_key: str, desc_key: str, icon: str, is_safe: bool):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)
        
        icon_label = CaptionLabel(icon, self)
        icon_label.setFixedWidth(20)
        row_layout.addWidget(icon_label)
        
        name_label = BodyLabel(tr(name_key), self)
        name_label.setFixedWidth(120)
        row_layout.addWidget(name_label)
        
        size_label = CaptionLabel("0 MB", self)
        size_label.setFixedWidth(80)
        self._cache_labels[cache_key] = size_label
        row_layout.addWidget(size_label)
        
        btn = PushButton(tr("settings.general.clear_cache"), self)
        btn.setFixedSize(60, 28)
        btn.clicked.connect(lambda checked, k=cache_key: self._clear_cache(k))
        self._cache_buttons[cache_key] = btn
        row_layout.addWidget(btn)
        
        row_layout.addStretch()
        parent_card.addLayout(row_layout)
        
        desc_label = CaptionLabel(tr(desc_key), self)
        desc_label.setStyleSheet("color: gray; margin-left: 28px;")
        parent_card.addWidget(desc_label)
        
        return {
            "name_label": name_label,
            "desc_label": desc_label,
            "cache_key": cache_key,
            "name_key": name_key,
            "desc_key": desc_key,
        }

    def _refresh_all_cache_sizes(self):
        from PyQt5.QtCore import QTimer
        
        all_info = self._cache_manager.get_all_cache_info()
        
        for info in all_info:
            cache_key = self._get_cache_key_from_name(info.name)
            if cache_key in self._cache_labels:
                self._cache_labels[cache_key].setText(info.size_display)
        
        self._total_cache_label.setText(self._cache_manager.get_total_size_display())

    def _get_cache_key_from_name(self, name: str) -> str:
        # cache_manager.py 中返回的名称始终是中文，不随语言切换
        mapping = {
            tr("settings.cache_tts", default="TTS 语音缓存"): "tts",
            tr("settings.cache_images", default="网络图片缓存"): "image",
            tr("settings.cache_temp_images", default="临时图片"): "temp_images",
            tr("settings.cache_musicdl", default="musicdl 临时输出"): "musicdl",
            tr("settings.cache_logs", default="旧日志文件"): "old_logs",
            tr("settings.cache_music", default="音乐下载"): "music_downloads",
        }
        return mapping.get(name, "")

    def _clear_cache(self, cache_key: str):
        clear_methods = {
            "tts": self._cache_manager.clear_tts_cache,
            "image": self._cache_manager.clear_image_cache,
            "temp_images": self._cache_manager.clear_temp_images_cache,
            "musicdl": self._cache_manager.clear_musicdl_cache,
            "old_logs": self._cache_manager.clear_old_logs,
            "music_downloads": self._cache_manager.clear_music_downloads,
        }
        
        method = clear_methods.get(cache_key)
        if not method:
            return
        
        try:
            deleted, freed = method()
            freed_mb = freed / (1024 * 1024)
            
            if deleted > 0:
                InfoBar.success(
                    tr("settings.cache.cleared"),
                    f"\u5df2\u5220\u9664 {deleted} \u4e2a\u6587\u4ef6\uff0c\u91ca\u653e {freed_mb:.2f} MB",
                    duration=2000
                )
            else:
                InfoBar.warning(
                    tr("settings.cache.empty"),
                    tr("settings.cache.nothing_to_clear"),
                    duration=2000
                )
        except Exception as e:
            InfoBar.error(
                tr("settings.cache.failed"),
                tr("settings.cache.clear_error") + f": {str(e)}",
                duration=2000
            )
        
        self._refresh_all_cache_sizes()

    def _clear_all_safe_caches(self):
        try:
            deleted, freed = self._cache_manager.clear_all_safe_caches()
            freed_mb = freed / (1024 * 1024)
            
            if deleted > 0:
                InfoBar.success(
                    tr("settings.cache.cleared"),
                    f"\u5df2\u5220\u9664 {deleted} \u4e2a\u6587\u4ef6\uff0c\u91ca\u653e {freed_mb:.2f} MB",
                    duration=2000
                )
            else:
                InfoBar.warning(
                    tr("settings.cache.empty"),
                    tr("settings.cache.nothing_to_clear"),
                    duration=2000
                )
        except Exception as e:
            InfoBar.error(
                tr("settings.cache.failed"),
                tr("settings.cache.clear_error") + f": {str(e)}",
                duration=2000
            )
        
        self._refresh_all_cache_sizes()

    def refresh_cache_sizes(self):
        self._refresh_all_cache_sizes()
    
    def _create_desktop_shortcut(self):
        from src.core.shortcut_utils import create_desktop_shortcut
        
        success, message = create_desktop_shortcut(replace_existing=False)
        if success:
            InfoBar.success(
                tr("settings.shortcut.success"),
                message,
                duration=3000
            )
        else:
            InfoBar.error(
                tr("settings.shortcut.failed"),
                message,
                duration=3000
            )

    def refresh_ui(self):
        """语言切换时刷新所有 UI 文本。"""
        logger.info(f"[I18n] GeneralSettingsPage.refresh_ui start")
        self._card.title_label.setText(tr("settings.general.title"))
        self.check_autorun.setText(tr("settings.general.autorun"))
        self.check_hide_pet_on_startup.setText(tr("settings.general.hide_pet"))
        self.check_mouse_interact.setText(tr("settings.general.mouse_interact"))
        
        # 语言卡片
        self._lang_label.setText(tr("settings.general.language") + ":")
        # 更新语言下拉框
        i18n = I18nManager.get_instance()
        current_code = i18n.current_language
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for code, info in i18n.languages.items():
            self.lang_combo.addItem(info["display"], userData=code)
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current_code:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.blockSignals(False)
        
        # 快捷方式卡片
        self._shortcut_card.title_label.setText(tr("settings.general.shortcut"))
        self._shortcut_info_label.setText(tr("settings.general.create_shortcut_desc"))
        self.btn_create_shortcut.setText(tr("settings.general.create_shortcut_btn"))
        
        # 缓存管理卡片
        self._cache_card.title_label.setText(tr("settings.general.cache"))
        self._safe_cache_label.setText(tr("settings.general.safe_cache"))
        self._warning_cache_label.setText("\u26a0\ufe0f " + tr("settings.general.warning_cache"))
        self._total_label.setText("\ud83d\udcca " + tr("settings.general.total_cache_size") + ":")
        
        for row in self._safe_cache_rows:
            row["name_label"].setText(tr(row["name_key"]))
            row["desc_label"].setText(tr(row["desc_key"]))
        for row in self._warning_cache_rows:
            row["name_label"].setText(tr(row["name_key"]))
            row["desc_label"].setText(tr(row["desc_key"]))
        
        for btn in self._cache_buttons.values():
            btn.setText(tr("settings.general.clear_cache"))
        self.btn_clear_all_safe.setText(tr("settings.general.clear_all_safe"))


class DisplaySettingsPage(QWidget):
    ASPECT_RATIOS = [
        ("settings.aspect_1_1", 1.0),
        ("settings.aspect_4_3", 4.0 / 3.0),
        ("settings.aspect_3_4", 3.0 / 4.0),
        ("settings.aspect_16_9", 16.0 / 9.0),
        ("settings.aspect_9_16", 9.0 / 16.0),
        ("settings.aspect_16_10", 16.0 / 10.0),
        ("settings.aspect_10_16", 10.0 / 16.0),
        ("settings.aspect_custom", -1),
    ]
    
    FONT_OPTIONS = [
        ("settings.display.font_small", 90),
        ("settings.display.font_medium", 100),
        ("settings.display.font_large", 115),
        ("settings.display.font_xlarge", 135),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self._card = SettingCard(tr("settings.display.title"), self)
        self.sliders = {}
        
        self.check_show_pet_status = CheckBox(tr("settings.display.show_pet_status"), self)
        self.check_show_pet_status.setChecked(True)
        self._card.addWidget(self.check_show_pet_status)
        
        self.add_slider_option(self._card, "settings.display.model_scale", 20, 150, 100, "%")
        self.add_slider_option(self._card, "settings.display.window_opacity", 10, 100, 100, "%")
        self.add_slider_option(self._card, "settings.display.bubble_duration", 1000, 10000, 3000, " ms")
        
        layout.addWidget(self._card)
        
        self._aspect_card = SettingCard(tr("settings.display.aspect_ratio"), self)
        
        self._aspect_label = StrongBodyLabel(tr("settings.display.aspect_label"), self)
        self._aspect_card.addWidget(self._aspect_label)
        
        aspect_h_layout = QHBoxLayout()
        self.aspect_combo = ComboBox(self)
        self.aspect_combo.addItems([tr(ratio[0], default=ratio[0]) for ratio in self.ASPECT_RATIOS])
        self.aspect_combo.setCurrentIndex(0)
        self.aspect_combo.setFixedWidth(150)
        self.aspect_combo.currentIndexChanged.connect(self._on_aspect_preset_changed)
        aspect_h_layout.addWidget(self.aspect_combo)
        aspect_h_layout.addStretch()
        self._aspect_card.addLayout(aspect_h_layout)
        
        custom_layout = QHBoxLayout()
        self._custom_label = BodyLabel(tr("settings.display.custom_ratio") + ":", self)
        custom_layout.addWidget(self._custom_label)
        
        self.width_spin = SpinBox(self)
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(550)
        self.width_spin.setFixedWidth(130)
        self.width_spin.setEnabled(False)
        custom_layout.addWidget(self.width_spin)
        
        x_label = BodyLabel("\u00d7", self)
        custom_layout.addWidget(x_label)
        
        self.height_spin = SpinBox(self)
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(500)
        self.height_spin.setFixedWidth(130)
        self.height_spin.setEnabled(False)
        custom_layout.addWidget(self.height_spin)
        
        custom_layout.addStretch()
        self._aspect_card.addLayout(custom_layout)
        
        self.width_spin.valueChanged.connect(self._on_custom_size_changed)
        self.height_spin.valueChanged.connect(self._on_custom_size_changed)
        
        self._apply_btn = PushButton(FluentIcon.ACCEPT, tr("settings.display.apply_ratio"), self)
        self._apply_btn.clicked.connect(self._apply_aspect_ratio)
        self._aspect_card.addWidget(self._apply_btn)
        
        layout.addWidget(self._aspect_card)
        
        self._monitor_card = SettingCard(tr("settings.display.monitor"), self)

        self.check_system_monitor = CheckBox(tr("settings.display.monitor_enable"), self)
        self.check_system_monitor.setChecked(True)
        self._monitor_card.addWidget(self.check_system_monitor)

        self.add_slider_option(self._monitor_card, "settings.display.cpu_threshold", 50, 100, 70, "%")
        self.add_slider_option(self._monitor_card, "settings.display.mem_threshold", 50, 100, 80, "%")

        layout.addWidget(self._monitor_card)

        self._font_card = SettingCard(tr("settings.display.font_size"), self)

        self._font_label = StrongBodyLabel(tr("settings.display.font_label"), self)
        self._font_card.addWidget(self._font_label)

        font_h_layout = QHBoxLayout()
        font_h_layout.setSpacing(8)

        self.font_buttons = {}
        self._font_button_keys = {}

        for key, value in self.FONT_OPTIONS:
            btn = PushButton(tr(key), self)
            btn.setFixedSize(60, 32)
            btn.setCursor(Qt.PointingHandCursor)
            self.font_buttons[value] = btn
            self._font_button_keys[btn] = key
            font_h_layout.addWidget(btn)

        font_h_layout.addStretch()

        for value, btn in self.font_buttons.items():
            btn.clicked.connect(lambda checked, v=value: self._on_font_button_clicked(v))

        self._font_card.addLayout(font_h_layout)

        layout.addWidget(self._font_card)
        layout.addStretch()

        self._update_font_buttons_style(100)

    def _on_font_button_clicked(self, value):
        settings_interface = self._find_settings_interface()
        if settings_interface:
            settings_interface._on_font_size_clicked(value)

    def _find_settings_interface(self):
        widget = self.parent()
        while widget:
            if isinstance(widget, SettingsInterface):
                return widget
            widget = widget.parent()
        return None

    def _update_font_buttons_style(self, selected_value):
        is_dark = isDarkTheme()
        font_sizes = {90: 12, 100: 14, 115: 16, 135: 18}
        for value, btn in self.font_buttons.items():
            font_size = font_sizes.get(value, 14)
            if value == selected_value:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(0, 120, 212, 0.2);
                        border: 1px solid rgba(0, 120, 212, 0.5);
                        border-radius: 4px;
                        color: #0078d4;
                        font-weight: bold;
                        font-size: {font_size}px;
                    }}
                """ if not is_dark else f"""
                    QPushButton {{
                        background-color: rgba(96, 165, 250, 0.2);
                        border: 1px solid rgba(96, 165, 250, 0.5);
                        border-radius: 4px;
                        color: #60a5fa;
                        font-weight: bold;
                        font-size: {font_size}px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                        color: #333333;
                        font-size: {font_size}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(0, 0, 0, 0.05);
                    }}
                """ if not is_dark else f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                        color: #e0e0e0;
                        font-size: {font_size}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.05);
                    }}
                """)

    def _init_font_buttons_style(self, saved_value=100):
        if saved_value not in self.font_buttons:
            saved_value = 100
        self._update_font_buttons_style(saved_value)

    def _on_aspect_preset_changed(self, index):
        is_custom = self.ASPECT_RATIOS[index][1] < 0
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
    
    def _on_custom_size_changed(self):
        pass
    
    def _apply_aspect_ratio(self):
        pass
    
    def get_current_aspect_ratio(self):
        index = self.aspect_combo.currentIndex()
        ratio = self.ASPECT_RATIOS[index][1]
        
        if ratio < 0:
            return self.width_spin.value(), self.height_spin.value()
        else:
            base_size = 500
            width = int(base_size * ratio) if ratio >= 1 else base_size
            height = int(base_size / ratio) if ratio < 1 else base_size
            if ratio >= 1:
                height = int(width / ratio)
            else:
                width = int(height * ratio)
            return width, height
    
    def set_custom_size(self, width, height):
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
    
    def add_slider_option(self, parent_card, key, min_val, max_val, default_val, unit_suffix=""):
        parent_card.addWidget(StrongBodyLabel(tr(key), self))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        val_label = CaptionLabel(f"{default_val}{unit_suffix}", self)
        val_label.setFixedWidth(150)
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}{unit_suffix}"))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        parent_card.addLayout(h_layout)
        
        self.sliders[key] = slider

    def refresh_ui(self):
        """语言切换时刷新所有 UI 文本。"""
        self._card.title_label.setText(tr("settings.display.title"))
        self.check_show_pet_status.setText(tr("settings.display.show_pet_status"))
        self._aspect_card.title_label.setText(tr("settings.display.aspect_ratio"))
        self._aspect_label.setText(tr("settings.display.aspect_label"))
        self._custom_label.setText(tr("settings.display.custom_ratio") + ":")
        self._apply_btn.setText(tr("settings.display.apply_ratio"))
        self._monitor_card.title_label.setText(tr("settings.display.monitor"))
        self.check_system_monitor.setText(tr("settings.display.monitor_enable"))
        self._font_card.title_label.setText(tr("settings.display.font_size"))
        self._font_label.setText(tr("settings.display.font_label"))
        
        for btn, key in self._font_button_keys.items():
            btn.setText(tr(key))

        # 刷新宽高比下拉框
        self.aspect_combo.blockSignals(True)
        current_idx = self.aspect_combo.currentIndex()
        self.aspect_combo.clear()
        self.aspect_combo.addItems([tr(ratio[0], default=ratio[0]) for ratio in self.ASPECT_RATIOS])
        self.aspect_combo.setCurrentIndex(current_idx)
        self.aspect_combo.blockSignals(False)


class SoundSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self._card = SettingCard(tr("settings.sound.title"), self)
        self.sliders = {}
        
        self.add_slider_option(self._card, "settings.sound.tts_volume", 0, 100, 80, "%")
        
        layout.addWidget(self._card)
        layout.addStretch()
    
    def add_slider_option(self, parent_card, key, min_val, max_val, default_val, unit_suffix=""):
        parent_card.addWidget(StrongBodyLabel(tr(key), self))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        val_label = CaptionLabel(f"{default_val}{unit_suffix}", self)
        val_label.setFixedWidth(60)
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}{unit_suffix}"))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        parent_card.addLayout(h_layout)
        
        self.sliders[key] = slider

    def refresh_ui(self):
        """语言切换时刷新所有 UI 文本。"""
        self._card.title_label.setText(tr("settings.sound.title"))


class AISettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self._card = SettingCard(tr("settings.ai.title"), self)
        self.sliders = {}
        
        self.check_inject_time = CheckBox(tr("settings.ai.inject_time"), self)
        self.check_expression_response = CheckBox(tr("settings.ai.expression_response"), self)
        self.check_enable_memory = CheckBox(tr("settings.ai.enable_memory"), self)
        
        self._card.addWidget(self.check_inject_time)
        self._card.addWidget(self.check_expression_response)
        self._card.addWidget(self.check_enable_memory)

        self._card.addWidget(StrongBodyLabel(tr("settings.ai.memory_max_count"), self))

        h_mem_layout = QHBoxLayout()
        mem_slider = Slider(Qt.Horizontal, self)
        mem_slider.setRange(1, 30)
        mem_slider.setValue(10)

        self._mem_val_label = CaptionLabel(f"10 {tr('memory.count_unit')}", self)
        self._mem_val_label.setFixedWidth(60)

        mem_slider.valueChanged.connect(lambda v: self._mem_val_label.setText(f"{v} {tr('memory.count_unit')}"))

        h_mem_layout.addWidget(mem_slider)
        h_mem_layout.addWidget(self._mem_val_label)
        self._card.addLayout(h_mem_layout)

        self.sliders["memory_max_count"] = mem_slider

        layout.addWidget(self._card)
        layout.addStretch()

    def refresh_ui(self):
        """语言切换时刷新所有 UI 文本。"""
        self._card.title_label.setText(tr("settings.ai.title"))
        self.check_inject_time.setText(tr("settings.ai.inject_time"))
        self.check_expression_response.setText(tr("settings.ai.expression_response"))
        self.check_enable_memory.setText(tr("settings.ai.enable_memory"))


class SettingsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("settingsView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingsInterface")
        
        self.live2d_widget = None
        self.settings = QSettings("DoroPet", "Settings")
        
        main_layout = QVBoxLayout(self.view)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)
        
        self._title = TitleLabel(tr("settings.title"), self.view)
        main_layout.addWidget(self._title)
        
        self.pivot = Pivot(self.view)
        self.pivot.setFixedHeight(40)
        main_layout.addWidget(self.pivot)
        
        self.stacked_widget = QStackedWidget(self.view)
        main_layout.addWidget(self.stacked_widget)
        
        self.general_page = GeneralSettingsPage(self)
        self.display_page = DisplaySettingsPage(self)
        self.sound_page = SoundSettingsPage(self)
        self.ai_page = AISettingsPage(self)
        
        self.stacked_widget.addWidget(self.general_page)
        self.stacked_widget.addWidget(self.display_page)
        self.stacked_widget.addWidget(self.sound_page)
        self.stacked_widget.addWidget(self.ai_page)
        
        self.pivot.addItem(routeKey="general", text="\u2699\ufe0f " + tr("settings.tab.general"), 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.general_page))
        self.pivot.addItem(routeKey="display", text="\ud83d\udda5\ufe0f " + tr("settings.tab.display"), 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.display_page))
        self.pivot.addItem(routeKey="sound", text="\ud83d\udd0a " + tr("settings.tab.sound"), 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.sound_page))
        self.pivot.addItem(routeKey="ai", text="\ud83e\udd16 " + tr("settings.tab.ai"), 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.ai_page))
        
        self.pivot.setCurrentItem("general")
        
        self.connect_signals()
        self.load_settings()

        # 监听语言切换
        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self._on_language_changed)

    def _on_language_changed(self, lang_code: str):
        """语言切换时刷新整个设置界面。"""
        logger.info(f"[I18n] SettingsInterface._on_language_changed: lang_code={lang_code}")
        # 刷新标题
        self._title.setText(tr("settings.title"))
        # 刷新 Pivot 标签（PivotItem 是 PushButton，直接 setText）
        self.pivot.items["general"].setText("\u2699\ufe0f " + tr("settings.tab.general"))
        self.pivot.items["display"].setText("\ud83d\udda5\ufe0f " + tr("settings.tab.display"))
        self.pivot.items["sound"].setText("\ud83d\udd0a " + tr("settings.tab.sound"))
        self.pivot.items["ai"].setText("\ud83e\udd16 " + tr("settings.tab.ai"))
        # 刷新各子页面
        logger.info(f"[I18n] Refreshing sub-pages...")
        self.general_page.refresh_ui()
        self.display_page.refresh_ui()
        self.sound_page.refresh_ui()
        self.ai_page.refresh_ui()
        logger.info(f"[I18n] SettingsInterface refresh complete")

    def connect_signals(self):
        self.general_page.check_autorun.stateChanged.connect(self.on_autorun_changed)
        self.general_page.check_hide_pet_on_startup.stateChanged.connect(self.on_hide_pet_on_startup_changed)
        self.general_page.check_mouse_interact.stateChanged.connect(self.on_mouse_interact_changed)
        
        self.display_page.check_show_pet_status.stateChanged.connect(self.on_show_pet_status_changed)
        self.display_page.sliders["settings.display.model_scale"].valueChanged.connect(self.on_scale_changed)
        self.display_page.sliders["settings.display.window_opacity"].valueChanged.connect(self.on_window_opacity_changed)
        self.display_page.sliders["settings.display.bubble_duration"].valueChanged.connect(self.on_bubble_duration_changed)
        self.display_page.aspect_combo.currentIndexChanged.connect(self.on_aspect_ratio_changed)
        self.display_page.width_spin.valueChanged.connect(self.on_custom_aspect_changed)
        self.display_page.height_spin.valueChanged.connect(self.on_custom_aspect_changed)
        
        self.display_page.check_system_monitor.stateChanged.connect(self.on_system_monitor_changed)
        self.display_page.sliders["settings.display.cpu_threshold"].valueChanged.connect(self.on_cpu_threshold_changed)
        self.display_page.sliders["settings.display.mem_threshold"].valueChanged.connect(self.on_mem_threshold_changed)

        self.sound_page.sliders["settings.sound.tts_volume"].valueChanged.connect(self.on_volume_changed)
        
        self.ai_page.check_inject_time.stateChanged.connect(self.on_inject_time_changed)
        self.ai_page.check_expression_response.stateChanged.connect(self.on_expression_response_changed)
        self.ai_page.check_enable_memory.stateChanged.connect(self.on_enable_memory_changed)
        self.ai_page.sliders["memory_max_count"].valueChanged.connect(self.on_memory_max_count_changed)

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        self.on_scale_changed(self.display_page.sliders["settings.display.model_scale"].value())
        self.on_mouse_interact_changed(self.general_page.check_mouse_interact.isChecked())

    def update_theme(self):
        pass

    def _sync_live2d_config_to_db(self, scale=None):
        """同步 Live2D 缩放/宽高比配置到数据库。"""
        if not self.live2d_widget:
            return
        if scale is None:
            scale = self.display_page.sliders["settings.display.model_scale"].value()
        aspect_index = self.display_page.aspect_combo.currentIndex()
        custom_w = self.display_page.width_spin.value()
        custom_h = self.display_page.height_spin.value()
        self.live2d_widget.save_size_to_db(scale, aspect_index, custom_w, custom_h)

    def on_scale_changed(self, value):
        scale = value / 100.0
        if self.live2d_widget:
            width, height = self.display_page.get_current_aspect_ratio()
            new_w = int(width * scale)
            new_h = int(height * scale)
            self.live2d_widget.resize(new_w, new_h)
            # 同步写入数据库
            self._sync_live2d_config_to_db(value)
        self.settings.setValue("scale", value)

    def on_window_opacity_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.model_opacity = value
            self.live2d_widget.set_model_opacity(value / 100.0)
        self.settings.setValue("window_opacity", value)

    def on_bubble_duration_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.default_bubble_duration = value
        self.settings.setValue("bubble_duration", value)

    def on_volume_changed(self, value):
        try:
            chat_interface = self.window().chat_interface
            if hasattr(chat_interface, 'tts_manager') and chat_interface.tts_manager:
                tts = chat_interface.tts_manager
                if hasattr(tts, 'player') and tts.player:
                    tts.player.setVolume(value)
        except Exception as e:
            logger.warning(f"Error setting volume: {e}")
        self.settings.setValue("volume", value)

    def on_mouse_interact_changed(self, checked):
        is_locked = not checked
        if self.live2d_widget:
            self.live2d_widget.set_locked(is_locked, silent=True)
        self.settings.setValue("mouse_interact", checked)

    def on_show_pet_status_changed(self, checked):
        if self.live2d_widget and hasattr(self.live2d_widget, 'status_overlay'):
            self.live2d_widget.status_overlay.set_visible_by_setting(checked)
        self.settings.setValue("show_pet_status", checked)

    def on_system_monitor_changed(self, checked):
        if self.live2d_widget:
            self.live2d_widget.set_system_monitor_enabled(checked)
        self.settings.setValue("system_monitor_enabled", checked)

    def on_cpu_threshold_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.cpu_threshold = value
        self.settings.setValue("cpu_threshold", value)

    def on_mem_threshold_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.mem_threshold = value
        self.settings.setValue("mem_threshold", value)

    def _on_font_size_clicked(self, value):
        font_scale = value / 100.0
        self.settings.setValue("font_scale", font_scale)
        self.display_page._update_font_buttons_style(value)
        main_window = self.window()
        if main_window and hasattr(main_window, 'load_stylesheet'):
            from qfluentwidgets import isDarkTheme
            if isDarkTheme():
                from src.resource_utils import resource_path
                main_window.load_stylesheet(resource_path("themes/dark.qss"))
            else:
                from src.resource_utils import resource_path
                main_window.load_stylesheet(resource_path("themes/light.qss"))

    def on_aspect_ratio_changed(self, index):
        is_custom = self.display_page.ASPECT_RATIOS[index][1] < 0
        self.display_page.width_spin.setEnabled(is_custom)
        self.display_page.height_spin.setEnabled(is_custom)
        
        if not is_custom:
            self._apply_aspect_ratio()
        
        self.settings.setValue("aspect_ratio_index", index)
    
    def on_custom_aspect_changed(self):
        if self.display_page.aspect_combo.currentIndex() == len(self.display_page.ASPECT_RATIOS) - 1:
            width = self.display_page.width_spin.value()
            height = self.display_page.height_spin.value()
            self.settings.setValue("custom_aspect_width", width)
            self.settings.setValue("custom_aspect_height", height)
    
    def _apply_aspect_ratio(self):
        if not self.live2d_widget:
            return
        
        width, height = self.display_page.get_current_aspect_ratio()
        scale = self.display_page.sliders["settings.display.model_scale"].value() / 100.0
        
        final_width = int(width * scale)
        final_height = int(height * scale)
        
        self.live2d_widget.resize(final_width, final_height)
        
        if hasattr(self.live2d_widget, 'flash_border'):
            self.live2d_widget.flash_border()
        
        self.settings.setValue("window_width", final_width)
        self.settings.setValue("window_height", final_height)
        
        if self.display_page.aspect_combo.currentIndex() == len(self.display_page.ASPECT_RATIOS) - 1:
            self.settings.setValue("custom_aspect_width", width)
            self.settings.setValue("custom_aspect_height", height)

        # 同步写入数据库
        self._sync_live2d_config_to_db()

    def on_inject_time_changed(self, checked):
        self.settings.setValue("inject_time", checked)

    def on_expression_response_changed(self, checked):
        self.settings.setValue("enable_expression_response", checked)

    def on_enable_memory_changed(self, checked):
        self.settings.setValue("enable_memory", checked)

    def on_memory_max_count_changed(self, value):
        self.settings.setValue("memory_max_count", value)

    def on_autorun_changed(self, checked):
        import sys
        import os
        import winreg
        
        app_name = "DoroPet"
        bat_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "start_app_background.bat")
        
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
            if checked:
                winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, bat_path)
            else:
                try:
                    winreg.DeleteValue(registry_key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(registry_key)
            self.settings.setValue("autorun", checked)
            logger.info(f"Autorun set to {checked}, path: {bat_path}")
        except Exception as e:
            logger.warning(f"Autorun error: {e}")

    def on_hide_pet_on_startup_changed(self, checked):
        self.settings.setValue("hide_pet_on_startup", checked)

    def load_settings(self):
        scale = self.settings.value("scale", 100, type=int)
        bubble_duration = self.settings.value("bubble_duration", 3000, type=int)
        volume = self.settings.value("volume", 80, type=int)
        mouse_interact = self.settings.value("mouse_interact", True, type=bool)
        autorun = self.settings.value("autorun", False, type=bool)
        hide_pet_on_startup = self.settings.value("hide_pet_on_startup", False, type=bool)
        inject_time = self.settings.value("inject_time", False, type=bool)
        expression_response = self.settings.value("enable_expression_response", True, type=bool)
        show_pet_status = self.settings.value("show_pet_status", True, type=bool)
        system_monitor_enabled = self.settings.value("system_monitor_enabled", True, type=bool)
        cpu_threshold = self.settings.value("cpu_threshold", 70, type=int)
        mem_threshold = self.settings.value("mem_threshold", 80, type=int)
        
        aspect_ratio_index = self.settings.value("aspect_ratio_index", 0, type=int)
        custom_aspect_width = self.settings.value("custom_aspect_width", 550, type=int)
        custom_aspect_height = self.settings.value("custom_aspect_height", 500, type=int)
        
        self.general_page.check_autorun.setChecked(autorun)
        self.general_page.check_hide_pet_on_startup.setChecked(hide_pet_on_startup)
        self.general_page.check_mouse_interact.setChecked(mouse_interact)
        
        self.display_page.check_show_pet_status.setChecked(show_pet_status)
        self.display_page.sliders["settings.display.model_scale"].setValue(scale)
        window_opacity = self.settings.value("window_opacity", 100, type=int)
        self.display_page.sliders["settings.display.window_opacity"].setValue(window_opacity)
        self.display_page.sliders["settings.display.bubble_duration"].setValue(bubble_duration)
        self.display_page.check_system_monitor.setChecked(system_monitor_enabled)
        self.display_page.sliders["settings.display.cpu_threshold"].setValue(cpu_threshold)
        self.display_page.sliders["settings.display.mem_threshold"].setValue(mem_threshold)
        
        self.display_page.aspect_combo.setCurrentIndex(aspect_ratio_index)
        self.display_page.width_spin.setValue(custom_aspect_width)
        self.display_page.height_spin.setValue(custom_aspect_height)
        
        self.sound_page.sliders["settings.sound.tts_volume"].setValue(volume)
        
        self.ai_page.check_inject_time.setChecked(inject_time)
        self.ai_page.check_expression_response.setChecked(expression_response)
        enable_memory = self.settings.value("enable_memory", True, type=bool)
        memory_max_count = self.settings.value("memory_max_count", 10, type=int)
        self.ai_page.check_enable_memory.setChecked(enable_memory)
        self.ai_page.sliders["memory_max_count"].setValue(memory_max_count)

        self._init_font_buttons_style()

    def _init_font_buttons_style(self):
        saved_scale = self.settings.value("font_scale", 1.0, type=float)
        saved_value = int(saved_scale * 100)
        self.display_page._init_font_buttons_style(saved_value)
