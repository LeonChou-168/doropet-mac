from typing import List, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    PrimaryPushButton, PushButton, TitleLabel, BodyLabel,
    FluentIcon, isDarkTheme, InfoBar, InfoBarPosition
)

from ..models import GameState
from src.core.i18n import I18nManager, tr


class InventoryDialog(QDialog):
    item_used = pyqtSignal(dict)

    def __init__(self, state: GameState, parent=None):
        super().__init__(parent)
        self._state = state
        self._used_item = None
        self.setWindowTitle(tr("galgame.dialog.inventory.title", default="背包"))
        self.setMinimumSize(450, 400)
        self.init_ui()
        I18nManager.get_instance().languageChanged.connect(self.refresh_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()

        self.title_label = TitleLabel(tr("galgame.dialog.inventory.title", default="背包"), self)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.currency_label = BodyLabel(f"💰 {tr('galgame.dialog.inventory.gold', default='金币:')} {self._state.currency}", self)
        header_layout.addWidget(self.currency_label)

        layout.addLayout(header_layout)

        if not self._state.inventory:
            self.empty_label = BodyLabel(
                tr("galgame.dialog.inventory.empty", default="背包空空如也...\n\n可以在商店购买物品，或在冒险中获得！"),
                self
            )
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.empty_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
            layout.addWidget(self.empty_label)
        else:
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            self.items_container = QWidget()
            self.items_layout = QVBoxLayout(self.items_container)
            self.items_layout.setContentsMargins(0, 0, 0, 0)
            self.items_layout.setSpacing(8)

            for item in self._state.inventory:
                card = self._create_item_card(item)
                self.items_layout.addWidget(card)

            self.items_layout.addStretch()

            scroll.setWidget(self.items_container)
            layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.close_btn = PushButton(tr("galgame.dialog.inventory.close", default="关闭"), self)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        self.update_theme()

    def refresh_ui(self):
        self.setWindowTitle(tr("galgame.dialog.inventory.title", default="背包"))
        self.title_label.setText(tr("galgame.dialog.inventory.title", default="背包"))
        self.currency_label.setText(f"💰 {tr('galgame.dialog.inventory.gold', default='金币:')} {self._state.currency}")
        self.close_btn.setText(tr("galgame.dialog.inventory.close", default="关闭"))

        if hasattr(self, 'empty_label') and self.empty_label:
            self.empty_label.setText(
                tr("galgame.dialog.inventory.empty", default="背包空空如也...\n\n可以在商店购买物品，或在冒险中获得！")
            )

        # Refresh item card buttons
        if hasattr(self, 'items_layout'):
            for i in range(self.items_layout.count()):
                card = self.items_layout.itemAt(i).widget()
                if card and isinstance(card, QFrame):
                    for child in card.findChildren(PrimaryPushButton):
                        child.setText(tr("galgame.dialog.inventory.use", default="使用"))

    def _create_item_card(self, item: Dict) -> QFrame:
        card = QFrame()
        card.setObjectName("inventoryCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = BodyLabel(item.get('name', tr("galgame.dialog.inventory.unknown_item", default="未知物品")), card)
        name_label.setObjectName("itemName")
        font = name_label.font()
        font.setBold(True)
        name_label.setFont(font)
        info_layout.addWidget(name_label)

        desc_label = BodyLabel(item.get('description', tr("galgame.dialog.inventory.no_description", default="无描述")), card)
        desc_label.setObjectName("itemDesc")
        info_layout.addWidget(desc_label)

        effect = item.get('effect', {})
        effect_text = self._get_effect_description(effect)
        if effect_text:
            effect_label = BodyLabel(f"{tr('galgame.dialog.inventory.effect_label', default='效果:')} {effect_text}", card)
            effect_label.setObjectName("itemEffect")
            effect_label.setStyleSheet("color: #63b3ed; font-size: 12px;")
            info_layout.addWidget(effect_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        use_btn = PrimaryPushButton(tr("galgame.dialog.inventory.use", default="使用"), card)
        use_btn.setProperty("item_data", item)
        use_btn.clicked.connect(self._use_item)
        layout.addWidget(use_btn)

        return card

    def _get_effect_description(self, effect: Dict) -> str:
        if not effect:
            return ""

        effect_type = effect.get('type', '')

        if effect_type == 'affection_all':
            return tr("galgame.dialog.inventory.effect.affection_all", default="所有角色好感度+{value}").format(value=effect.get('value', 0))
        elif effect_type == 'affection_single':
            return tr("galgame.dialog.inventory.effect.affection_single", default="单个角色好感度+{value}").format(value=effect.get('value', 0))
        elif effect_type == 'protect_affection':
            return tr("galgame.dialog.inventory.effect.protect_affection", default="防止一次好感度下降")
        elif effect_type == 'unlock_story':
            return tr("galgame.dialog.inventory.effect.unlock_story", default="解锁隐藏剧情")
        elif effect_type == 'rollback':
            return tr("galgame.dialog.inventory.effect.rollback", default="回退到上一个选择点")
        elif effect_type == 'currency':
            return tr("galgame.dialog.inventory.effect.currency", default="获得{value}金币").format(value=effect.get('value', 0))

        return ""

    def _use_item(self):
        btn = self.sender()
        if not btn:
            return

        item_data = btn.property("item_data")
        if not item_data:
            return

        effect = item_data.get('effect', {})
        effect_type = effect.get('type', '')

        if effect_type == 'affection_all':
            value = effect.get('value', 5)
            for aff in self._state.affections:
                aff.affection = min(100, aff.affection + value)

            self._state.inventory.remove(item_data)
            self._used_item = item_data

            InfoBar.success(
                title=tr("galgame.dialog.inventory.use_success", default="使用成功"),
                content=tr("galgame.dialog.inventory.use_success_affection_all", default="所有角色好感度+{value}！").format(value=value),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

            self.item_used.emit(item_data)
            self.accept()

        elif effect_type == 'currency':
            value = effect.get('value', 50)
            self._state.currency += value
            self._state.inventory.remove(item_data)
            self._used_item = item_data

            InfoBar.success(
                title=tr("galgame.dialog.inventory.use_success", default="使用成功"),
                content=tr("galgame.dialog.inventory.use_success_currency", default="获得{value}金币！").format(value=value),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

            self.item_used.emit(item_data)
            self.accept()

        elif effect_type == 'affection_single':
            from PyQt5.QtWidgets import QInputDialog
            char_names = [aff.character_name for aff in self._state.affections]
            if char_names:
                name, ok = QInputDialog.getItem(
                    self,
                    tr("galgame.dialog.inventory.select_character", default="选择角色"),
                    tr("galgame.dialog.inventory.select_character_prompt", default="选择要增加好感度的角色："),
                    char_names, 0, False
                )
                if ok and name:
                    value = effect.get('value', 10)
                    for aff in self._state.affections:
                        if aff.character_name == name:
                            aff.affection = min(100, aff.affection + value)
                            break

                    self._state.inventory.remove(item_data)
                    self._used_item = item_data

                    InfoBar.success(
                        title=tr("galgame.dialog.inventory.use_success", default="使用成功"),
                        content=tr("galgame.dialog.inventory.use_success_single", default="{name}的好感度+{value}！").format(name=name, value=value),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

                    self.item_used.emit(item_data)
                    self.accept()
        else:
            InfoBar.warning(
                title=tr("galgame.dialog.inventory.hint", default="提示"),
                content=tr("galgame.dialog.inventory.use_scene_hint", default="该物品需要在特定场景中使用"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def get_updated_state(self) -> GameState:
        return self._state

    def get_used_item(self) -> Dict:
        return self._used_item

    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        card_bg = "#3d3d3d" if is_dark else "#f8f8f8"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#404040" if is_dark else "#e0e0e0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            #inventoryCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #itemName {{
                color: {text_color};
                font-size: 14px;
            }}
            #itemDesc {{
                color: #a0aec0;
                font-size: 12px;
            }}
        """)
