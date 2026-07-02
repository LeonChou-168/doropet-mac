import os
import sys
import ast
import importlib.util
import types
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListWidget,
                             QStackedWidget, QLabel, QFrame, QListWidgetItem,
                             QSplitter)
from PyQt5.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, FluentIcon,
                            isDarkTheme)
from src.core.i18n import I18nManager, tr


class PluginInterface(QWidget):
    LEFT_WIDTH = 250

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("PluginInterface")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal, self)

        # ---- Left Panel ----
        self.left_panel = QFrame(self.splitter)
        self.left_panel.setObjectName("leftPanel")
        self._apply_left_panel_style()

        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(8, 12, 8, 12)
        self.left_layout.setSpacing(6)

        self.lbl_title = SubtitleLabel(tr("plugin.title"), self)
        self.left_layout.addWidget(self.lbl_title)

        self.btn_refresh = PrimaryPushButton(tr("plugin.refresh"), self)
        self.btn_refresh.setIcon(FluentIcon.SYNC)
        self.btn_refresh.clicked.connect(self.load_plugins)
        self.left_layout.addWidget(self.btn_refresh)

        self.plugin_list = QListWidget()
        self._apply_list_style()
        self.plugin_list.currentRowChanged.connect(self.on_plugin_selected)
        self.left_layout.addWidget(self.plugin_list, stretch=1)

        # ---- Right Panel ----
        self.right_panel = QStackedWidget(self.splitter)
        self.right_panel.setStyleSheet("background-color: transparent;")

        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        self.welcome_lbl = SubtitleLabel(tr("plugin.select_hint"), self.welcome_widget)
        self.welcome_lbl.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(self.welcome_lbl)
        self.right_panel.addWidget(self.welcome_widget)

        self.splitter.setSizes([self.LEFT_WIDTH, 600])
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

        self.loaded_plugins = {}

        self.load_plugins()

        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)

    # -------- 主题样式 --------
    def _apply_left_panel_style(self):
        border_color = "#404040" if isDarkTheme() else "#E0E0E0"
        self.left_panel.setStyleSheet(
            f"QFrame#leftPanel {{ border-right: 1px solid {border_color}; "
            "background-color: transparent; }"
        )

    def _apply_list_style(self):
        text_color = "#ccc" if isDarkTheme() else "#333"
        border_color = "#404040" if isDarkTheme() else "#E0E0E0"
        hover_color = "rgba(255,255,255,0.06)" if isDarkTheme() else "#F0F0F0"
        selected_bg = "#EB99B4"
        selected_text = "#fff"
        self.plugin_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {border_color};
                border-radius: 5px;
                background-color: transparent;
                color: {text_color};
            }}
            QListWidget::item {{
                height: 35px;
                padding-left: 10px;
            }}
            QListWidget::item:selected {{
                background-color: {selected_bg};
                color: {selected_text};
                border-radius: 4px;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {hover_color};
                border-radius: 4px;
            }}
        """)

    def update_theme(self):
        self._apply_left_panel_style()
        self._apply_list_style()
        # 通知已加载的插件进行主题更新
        for key, widget in list(self.loaded_plugins.items()):
            try:
                if hasattr(widget, 'update_theme'):
                    widget.update_theme()
                # 检查内部包装的 galgame 等子组件
                elif hasattr(widget, 'galgame') and hasattr(widget.galgame, 'update_theme'):
                    widget.galgame.update_theme()
            except RuntimeError:
                del self.loaded_plugins[key]

    # -------- 插件扫描 --------
    def get_plugin_name(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == "Plugin":
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "name":
                                    if isinstance(item.value, ast.Constant):
                                        return item.value.value
                                    elif isinstance(item.value, ast.Str):
                                        return item.value.s
        except Exception:
            pass
        return None

    def load_plugins(self):
        self.plugin_list.clear()
        self.loaded_plugins = {}

        plugin_dir = os.path.join(os.getcwd(), "plugin")
        if not os.path.exists(plugin_dir):
            try:
                os.makedirs(plugin_dir)
            except Exception as e:
                self.show_error(tr("plugin.dir_create_failed").format(error=e))
                return

        valid_plugins = []
        try:
            items = os.listdir(plugin_dir)
            for item in items:
                item_path = os.path.join(plugin_dir, item)

                if os.path.isdir(item_path):
                    main_py = os.path.join(item_path, "main.py")
                    if os.path.exists(main_py):
                        valid_plugins.append({
                            "type": "dir",
                            "name": item,
                            "path": item_path,
                            "entry": main_py,
                        })
                elif item.endswith(".py") and item != "__init__.py":
                    valid_plugins.append({
                        "type": "file",
                        "name": item,
                        "path": item_path,
                        "entry": item_path,
                    })

            valid_plugins.sort(key=lambda x: x["name"])

            if not valid_plugins:
                placeholder = QListWidgetItem(tr("plugin.no_plugins"))
                placeholder.setFlags(Qt.NoItemFlags)
                self.plugin_list.addItem(placeholder)
                return

            for p in valid_plugins:
                display_name = self.get_plugin_name(p["entry"]) or p["name"]
                list_item = QListWidgetItem(display_name)
                list_item.setData(Qt.UserRole, p)
                self.plugin_list.addItem(list_item)

        except Exception as e:
            self.show_error(tr("plugin.scan_failed") + f": {e}")

    def on_plugin_selected(self, row):
        if row < 0:
            return

        item = self.plugin_list.item(row)
        if item.flags() & Qt.NoItemFlags:
            return

        plugin_info = item.data(Qt.UserRole)
        if not plugin_info:
            return

        self._load_plugin(plugin_info)

    def _load_plugin(self, plugin_info: dict):
        plugin_id = plugin_info["name"]

        if plugin_id in self.loaded_plugins:
            try:
                self.right_panel.setCurrentWidget(self.loaded_plugins[plugin_id])
                return
            except RuntimeError:
                del self.loaded_plugins[plugin_id]

        try:
            entry_point_file = plugin_info["entry"]
            module_name_suffix = (
                f"{plugin_info['name']}.main" if plugin_info["type"] == "dir"
                else plugin_info["name"][:-3]
            )

            # 目录型插件需要注册父级包，让相对导入 (from .xxx import) 生效
            if plugin_info["type"] == "dir":
                package_name = f"plugin.{plugin_info['name']}"
                if package_name not in sys.modules:
                    parent = types.ModuleType(package_name)
                    parent.__path__ = [plugin_info["path"]]
                    parent.__package__ = package_name
                    sys.modules[package_name] = parent

            # 使用完整包路径创建 spec，让相对导入正确解析
            full_module_name = f"plugin.{module_name_suffix}"
            spec = importlib.util.spec_from_file_location(
                full_module_name, entry_point_file,
                submodule_search_locations=[plugin_info["path"]] if plugin_info["type"] == "dir" else None
            )
            if spec is None:
                self.show_error(
                    tr("plugin.load_spec_failed").format(file=entry_point_file)
                )
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[full_module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "Plugin"):
                plugin_class = getattr(module, "Plugin")
                if issubclass(plugin_class, QWidget):
                    widget = plugin_class()
                    self.right_panel.addWidget(widget)
                    self.right_panel.setCurrentWidget(widget)
                    self.loaded_plugins[plugin_id] = widget
                else:
                    self.show_error(
                        tr("plugin.class_not_qwidget").format(name=plugin_info["name"])
                    )
            else:
                self.show_error(
                    tr("plugin.class_not_defined").format(name=plugin_info["name"])
                )
        except Exception as e:
            self.show_error(
                tr("plugin.load_failed").format(
                    name=plugin_info["name"], error=str(e)
                )
            )
            import traceback
            traceback.print_exc()

    # -------- UI 刷新 --------
    def refresh_ui(self, lang_code: str = ""):
        self.lbl_title.setText(tr("plugin.title"))
        self.btn_refresh.setText(tr("plugin.refresh"))
        self.welcome_lbl.setText(tr("plugin.select_hint"))

    def show_error(self, message):
        error_widget = QWidget()
        layout = QVBoxLayout(error_widget)
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: red; font-size: 14px;")
        layout.addWidget(lbl)
        self.right_panel.addWidget(error_widget)
        self.right_panel.setCurrentWidget(error_widget)
