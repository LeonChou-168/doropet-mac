from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem
from PyQt5.QtCore import Qt
from qfluentwidgets import (ScrollArea, PlainTextEdit, PrimaryPushButton, PushButton,
                            TitleLabel, BodyLabel, FluentIcon, LineEdit, ListWidget, MessageBox,
                            StrongBodyLabel, CheckBox)
from src.core.database import ChatDatabase
from src.core.i18n import I18nManager, tr


class PromptInterface(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db if db else ChatDatabase()
        self.current_persona_id = None
        
        self.setObjectName("PromptInterface")
        self.init_ui()
        self.load_personas()

        self._i18n = I18nManager.get_instance()
        self._i18n.languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("promptLeftPanel")
        self.left_panel.setFixedWidth(250)
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(10)

        self.left_title = StrongBodyLabel(tr("prompt.title"), self.left_panel)
        left_layout.addWidget(self.left_title)

        self.persona_list = ListWidget(self.left_panel)
        self.persona_list.setObjectName("personaList")
        self.persona_list.itemClicked.connect(self.on_persona_selected)
        left_layout.addWidget(self.persona_list)

        self.add_btn = PushButton(FluentIcon.ADD, tr("prompt.new"), self.left_panel)
        self.add_btn.clicked.connect(self.create_new_persona)
        left_layout.addWidget(self.add_btn)

        main_layout.addWidget(self.left_panel)

        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        
        self.edit_widget = QWidget()
        self.edit_widget.setObjectName("promptEditWidget")
        
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(20)

        self.edit_title = TitleLabel(tr("prompt.edit_title"), self.edit_widget)
        right_layout.addWidget(self.edit_title)

        self.name_label = BodyLabel(tr("prompt.name"), self.edit_widget)
        right_layout.addWidget(self.name_label)
        self.name_input = LineEdit(self.edit_widget)
        self.name_input.setObjectName("promptNameInput")
        self.name_input.setPlaceholderText(tr("prompt.name_hint"))
        right_layout.addWidget(self.name_input)

        self.desc_label = BodyLabel(tr("prompt.description"), self.edit_widget)
        right_layout.addWidget(self.desc_label)
        self.desc_input = LineEdit(self.edit_widget)
        self.desc_input.setObjectName("promptDescInput")
        self.desc_input.setPlaceholderText(tr("prompt.desc_hint"))
        right_layout.addWidget(self.desc_input)

        self.prompt_label = BodyLabel(tr("prompt.system_prompt"), self.edit_widget)
        right_layout.addWidget(self.prompt_label)
        self.prompt_edit = PlainTextEdit(self.edit_widget)
        self.prompt_edit.setObjectName("promptContentEdit")
        self.prompt_edit.setPlaceholderText(tr("prompt.prompt_hint"))
        self.prompt_edit.setMinimumHeight(200)
        right_layout.addWidget(self.prompt_edit)
        
        self.doro_tools_checkbox = CheckBox(tr("prompt.enable_tools"), self.edit_widget)
        self.doro_tools_checkbox.setToolTip(tr("prompt.enable_tools_desc"))
        right_layout.addWidget(self.doro_tools_checkbox)

        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, tr("prompt.save"), self.edit_widget)
        self.save_btn.clicked.connect(self.save_persona)
        
        self.delete_btn = PushButton(FluentIcon.DELETE, tr("prompt.delete"), self.edit_widget)
        self.delete_btn.setObjectName("promptDeleteBtn")
        self.delete_btn.clicked.connect(self.delete_persona)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        main_layout.addWidget(right_panel)

    def load_personas(self):
        self.persona_list.clear()
        personas = self.db.get_personas()
        for p in personas:
            p_id, name, desc, prompt, avatar, enable_doro_tools, is_protected, live2d_model = p
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, p_id)
            item.setData(Qt.UserRole + 1, desc)
            item.setData(Qt.UserRole + 2, prompt)
            item.setData(Qt.UserRole + 3, bool(enable_doro_tools))
            item.setData(Qt.UserRole + 4, bool(is_protected))
            self.persona_list.addItem(item)
        
        if not personas:
            self.clear_inputs()
            self.current_persona_id = None

    def on_persona_selected(self, item):
        self.current_persona_id = item.data(Qt.UserRole)
        self.name_input.setText(item.text())
        self.desc_input.setText(item.data(Qt.UserRole + 1))
        self.prompt_edit.setPlainText(item.data(Qt.UserRole + 2))
        self.doro_tools_checkbox.setChecked(item.data(Qt.UserRole + 3) or False)
        
        is_protected = item.data(Qt.UserRole + 4) or False
        self.set_edit_mode(not is_protected)

    def set_edit_mode(self, editable):
        self.name_input.setReadOnly(not editable)
        self.desc_input.setReadOnly(not editable)
        self.prompt_edit.setReadOnly(not editable)
        self.doro_tools_checkbox.setEnabled(editable)
        self.save_btn.setEnabled(editable)
        self.delete_btn.setEnabled(editable)
        
        if not editable:
            self.name_input.setPlaceholderText(tr("prompt.protected"))
            self.desc_input.setPlaceholderText(tr("prompt.protected"))
            self.prompt_edit.setPlaceholderText(tr("prompt.protected"))
        else:
            self.name_input.setPlaceholderText(tr("prompt.name_hint"))
            self.desc_input.setPlaceholderText(tr("prompt.desc_hint"))
            self.prompt_edit.setPlaceholderText(tr("prompt.prompt_hint"))

    def create_new_persona(self):
        self.persona_list.clearSelection()
        self.clear_inputs()
        self.current_persona_id = None
        self.set_edit_mode(True)
        self.name_input.setFocus()

    def clear_inputs(self):
        self.name_input.clear()
        self.desc_input.clear()
        self.prompt_edit.clear()
        self.doro_tools_checkbox.setChecked(False)
        self.set_edit_mode(True)

    def save_persona(self):
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        enable_doro_tools = self.doro_tools_checkbox.isChecked()
        
        if not name:
            MessageBox(tr("general.error"), tr("prompt.name_required"), self).exec_()
            return

        if self.current_persona_id:
            self.db.update_persona(self.current_persona_id, name, desc, prompt, 
                                   enable_doro_tools=enable_doro_tools)
            MessageBox(tr("general.success"), tr("prompt.updated"), self).exec_()
        else:
            new_id = self.db.add_persona(name, desc, prompt, 
                                         enable_doro_tools=enable_doro_tools)
            self.current_persona_id = new_id
            MessageBox(tr("general.success"), tr("prompt.created"), self).exec_()
        
        self.load_personas()
        for i in range(self.persona_list.count()):
            item = self.persona_list.item(i)
            if item.data(Qt.UserRole) == self.current_persona_id:
                self.persona_list.setCurrentItem(item)
                break

    def delete_persona(self, checked=False):
        if not self.current_persona_id:
            return
        
        item = self.persona_list.currentItem()
        if item and item.data(Qt.UserRole + 4):
            MessageBox(tr("general.error"), tr("prompt.cannot_delete"), self).exec_()
            return
            
        w = MessageBox(tr("general.warning", default="确认删除"), tr("prompt.confirm_delete"), self)
        if w.exec_():
            if self.db.delete_persona(self.current_persona_id):
                self.load_personas()
                self.create_new_persona()
            else:
                MessageBox(tr("general.error"), tr("prompt.delete_failed"), self).exec_()

    def refresh_ui(self, lang_code: str = ""):
        """语言切换时刷新所有 UI 文本。"""
        self.left_title.setText(tr("prompt.title"))
        self.add_btn.setText(tr("prompt.new"))
        self.edit_title.setText(tr("prompt.edit_title"))
        self.name_label.setText(tr("prompt.name"))
        self.name_input.setPlaceholderText(tr("prompt.name_hint"))
        self.desc_label.setText(tr("prompt.description"))
        self.desc_input.setPlaceholderText(tr("prompt.desc_hint"))
        self.prompt_label.setText(tr("prompt.system_prompt"))
        self.prompt_edit.setPlaceholderText(tr("prompt.prompt_hint"))
        self.doro_tools_checkbox.setText(tr("prompt.enable_tools"))
        self.doro_tools_checkbox.setToolTip(tr("prompt.enable_tools_desc"))
        self.save_btn.setText(tr("prompt.save"))
        self.delete_btn.setText(tr("prompt.delete"))

    def update_theme(self):
        pass
