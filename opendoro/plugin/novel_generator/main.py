"""
Galgame 插件入口。

将 galgame 模块包装为 Plugin 类，供插件系统动态加载。
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from .galgame_interface import GalgameInterface


class Plugin(QWidget):
    name = "小说生成器"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.galgame = GalgameInterface(self)
        layout.addWidget(self.galgame)
