import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, 
                             QHBoxLayout, QLabel, QMessageBox)
from qfluentwidgets import (CardWidget, PushButton, PrimaryPushButton, 
                           LineEdit, BodyLabel, StrongBodyLabel)

from src.core.i18n import tr
from src.core.cookie_manager import CookieManager
from ..constants import MUSIC_PLATFORMS


class CookieSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("music.cookie.title", default="Cookie 设置"))
        self.cookie_manager = CookieManager.get_instance()
        self.platforms = MUSIC_PLATFORMS
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        
        self.platform_tabs = {}
        self.cookie_inputs = {}
        
        for platform_key, platform_name, music_client_name in self.platforms:
            has_cookies = self.cookie_manager.has_cookies(platform_key)
            status = tr("music.cookie.set", default="✓ 已设置") if has_cookies else tr("music.cookie.not_set", default="✗ 未设置")
            
            card = CardWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            
            header_layout = QHBoxLayout()
            title_label = StrongBodyLabel(platform_name)
            header_layout.addWidget(title_label)
            
            self.platform_tabs[platform_key] = QLabel(status)
            self.platform_tabs[platform_key].setObjectName("statusLabel")
            header_layout.addWidget(self.platform_tabs[platform_key])
            header_layout.addStretch()
            
            card_layout.addLayout(header_layout)
            
            instruction_label = BodyLabel(tr("music.cookie.instruction", default="请从浏览器开发者工具中复制 Cookie 字符串，格式为 name=value; 形式"))
            instruction_label.setWordWrap(True)
            card_layout.addWidget(instruction_label)
            
            self.cookie_inputs[platform_key] = LineEdit()
            self.cookie_inputs[platform_key].setPlaceholderText(tr("music.cookie.placeholder", default="输入 Cookie 字符串..."))
            existing_cookies = self.cookie_manager.get_cookies(platform_key)
            if existing_cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in existing_cookies.items()])
                self.cookie_inputs[platform_key].setText(cookie_str)
            card_layout.addWidget(self.cookie_inputs[platform_key])
            
            btn_layout = QHBoxLayout()
            save_btn = PrimaryPushButton(tr("music.cookie.save", default="保存"))
            save_btn.clicked.connect(lambda _, p=platform_key: self._save_cookies(p))
            btn_layout.addWidget(save_btn)
            
            test_btn = PushButton(tr("music.cookie.test", default="测试"))
            test_btn.clicked.connect(lambda _, p=platform_key: self._test_cookies(p))
            btn_layout.addWidget(test_btn)
            
            clear_btn = PushButton(tr("music.cookie.clear", default="清除"))
            clear_btn.clicked.connect(lambda _, p=platform_key: self._clear_cookies(p))
            btn_layout.addWidget(clear_btn)
            
            card_layout.addLayout(btn_layout)
            content_layout.addWidget(card)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        close_btn = PrimaryPushButton(tr("music.cookie.close", default="关闭"))
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setMinimumSize(500, 500)
        self.setMaximumSize(600, 700)
    
    def _parse_cookie_string(self, cookie_str: str) -> dict:
        cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookies[name.strip()] = value.strip()
        return cookies
    
    def _save_cookies(self, platform: str):
        cookie_str = self.cookie_inputs[platform].text()
        if cookie_str:
            cookies = self._parse_cookie_string(cookie_str)
            self.cookie_manager.set_cookies(platform, cookies)
            self.platform_tabs[platform].setText(tr("music.cookie.set", default="✓ 已设置"))
            QMessageBox.information(self, tr("music.cookie.success", default="成功"),
                                    tr("music.cookie.saved_msg", default="已保存 {name} 的 Cookie\n\n注意：Cookie 是否有效取决于 Cookie 是否过期以及是否包含必要的登录信息。").format(name=self._get_platform_name(platform)))
        else:
            self.cookie_manager.clear_cookies(platform)
            self.platform_tabs[platform].setText(tr("music.cookie.not_set", default="✗ 未设置"))
            QMessageBox.information(self, tr("music.cookie.success", default="成功"),
                                    tr("music.cookie.cleared_msg", default="已清除 {name} 的 Cookie").format(name=self._get_platform_name(platform)))
    
    def _test_cookies(self, platform: str):
        cookies = self.cookie_manager.get_cookies(platform)
        if not cookies:
            QMessageBox.warning(self, tr("music.cookie.test_failed", default="测试失败"),
                                tr("music.cookie.no_cookie_msg", default="【{name}】\n\n当前没有设置 Cookie，请先保存 Cookie 后再测试。").format(name=self._get_platform_name(platform)))
            return
        
        platform_name = self._get_platform_name(platform)
        music_client_name = self._get_music_client_name(platform)
        
        try:
            from musicdl import musicdl
            
            os.makedirs(os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'), exist_ok=True)
            
            init_cfg = {
                music_client_name: {
                    'work_dir': os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'),
                    'default_search_cookies': cookies,
                    'default_parse_cookies': cookies,
                }
            }
            
            music_client = musicdl.MusicClient(
                music_sources=[music_client_name],
                init_music_clients_cfg=init_cfg
            )
            
            results = music_client.search(keyword="test")
            
            if results and any(results.values()):
                song_count = sum(len(songs) for songs in results.values())
                QMessageBox.information(self, tr("music.cookie.test_success", default="测试成功"),
                                        tr("music.cookie.test_success_msg", default="【{name}】\n\n✓ Cookie 配置有效！\n✓ 共获取到 {count} 首测试歌曲。").format(name=platform_name, count=song_count))
            else:
                QMessageBox.warning(self, tr("music.cookie.test_result", default="测试结果"),
                                    tr("music.cookie.test_result_msg", default="【{name}】\n\n⚠ Cookie 配置可能有效，但没有返回结果。\n⚠ 可能需要更长的登录 Cookie（包含登录 token）。").format(name=platform_name))
        except Exception as e:
            QMessageBox.critical(self, tr("music.cookie.test_failed", default="测试失败"),
                                 tr("music.cookie.test_error_msg", default="【{name}】\n\n✗ 测试过程中发生错误：\n{error}").format(name=platform_name, error=str(e)))
    
    def _clear_cookies(self, platform: str):
        self.cookie_manager.clear_cookies(platform)
        self.cookie_inputs[platform].clear()
        self.platform_tabs[platform].setText(tr("music.cookie.not_set", default="✗ 未设置"))
        QMessageBox.information(self, tr("music.cookie.success", default="成功"),
                                tr("music.cookie.cleared_msg", default="已清除 {name} 的 Cookie").format(name=self._get_platform_name(platform)))
    
    def _get_platform_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_name
        return platform
    
    def _get_music_client_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_client
        return platform
