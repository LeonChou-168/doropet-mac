"""
统一设计 Token 系统
所有窗口和弹窗的视觉常量集中管理，确保设计一致性。
支持深色/浅色双主题自动切换。
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from qfluentwidgets import isDarkTheme


# ============================================================
# 品牌色
# ============================================================
BRAND_PRIMARY = "#EB99B4"        # 主题粉
BRAND_PRIMARY_HOVER = "#F0AEC4"   # 悬停
BRAND_PRIMARY_PRESS = "#E085A0"   # 按下
BRAND_ACCENT = "#7EC8E3"          # 辅助蓝
BRAND_GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EB99B4, stop:1 #F5C6D3)"


# ============================================================
# 深色主题
# ============================================================
DARK = {
    # 背景层级 (由低到高)
    "bg_base": "#1a1a2e",
    "bg_surface": "#202430",
    "bg_container": "#262a36",
    "bg_elevated": "#2d3240",
    "bg_glass": "rgba(32, 36, 48, 220)",

    # 文字
    "text_primary": "rgba(235, 240, 250, 235)",
    "text_secondary": "rgba(180, 186, 200, 210)",
    "text_disabled": "rgba(120, 126, 140, 160)",

    # 边框
    "border_default": "rgba(255, 255, 255, 8)",
    "border_strong": "rgba(255, 255, 255, 12)",
    "border_focus": "rgba(235, 153, 180, 100)",

    # 分隔线
    "divider": "rgba(255, 255, 255, 6)",

    # 阴影
    "shadow_light": "rgba(0, 0, 0, 40)",
    "shadow_medium": "rgba(0, 0, 0, 60)",
    "shadow_heavy": "rgba(0, 0, 0, 80)",

    # 按钮背景
    "btn_bg": "rgba(60, 65, 75, 200)",
    "btn_hover": "rgba(80, 85, 100, 235)",
    "btn_pressed": "rgba(50, 55, 65, 220)",

    # 输入框
    "input_bg": "rgba(255, 255, 255, 6)",
    "input_border": "rgba(255, 255, 255, 10)",
    "input_focus_border": "rgba(235, 153, 180, 130)",

    # 状态色
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",

    # 滚动条
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "rgba(255, 255, 255, 40)",
    "scrollbar_handle_hover": "rgba(255, 255, 255, 70)",
}


# ============================================================
# 浅色主题
# ============================================================
LIGHT = {
    # 背景层级
    "bg_base": "#f5f5f5",
    "bg_surface": "#fafafa",
    "bg_container": "#ffffff",
    "bg_elevated": "#fefefe",
    "bg_glass": "rgba(255, 255, 255, 225)",

    # 文字
    "text_primary": "rgba(30, 30, 40, 220)",
    "text_secondary": "rgba(100, 105, 115, 200)",
    "text_disabled": "rgba(160, 165, 175, 180)",

    # 边框
    "border_default": "rgba(0, 0, 0, 8)",
    "border_strong": "rgba(0, 0, 0, 12)",
    "border_focus": "rgba(235, 153, 180, 180)",

    # 分隔线
    "divider": "rgba(0, 0, 0, 6)",

    # 阴影
    "shadow_light": "rgba(0, 0, 0, 12)",
    "shadow_medium": "rgba(0, 0, 0, 18)",
    "shadow_heavy": "rgba(0, 0, 0, 28)",

    # 按钮背景
    "btn_bg": "rgba(220, 225, 235, 200)",
    "btn_hover": "rgba(200, 208, 220, 235)",
    "btn_pressed": "rgba(190, 195, 210, 220)",

    # 输入框
    "input_bg": "rgba(0, 0, 0, 3)",
    "input_border": "rgba(0, 0, 0, 8)",
    "input_focus_border": "rgba(235, 153, 180, 180)",

    # 状态色
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",

    # 滚动条
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "rgba(0, 0, 0, 40)",
    "scrollbar_handle_hover": "rgba(0, 0, 0, 70)",
}


# ============================================================
# 圆角系统
# ============================================================
@dataclass
class BorderRadius:
    small: str = "4px"
    medium: str = "8px"
    large: str = "12px"
    xlarge: str = "16px"
    round: str = "20px"


# ============================================================
# 阴影系统
# ============================================================
@dataclass
class ShadowSpec:
    blur: int
    offset_x: int
    offset_y: int


SHADOW_ELEVATION = {
    1: ShadowSpec(8, 0, 2),     # 微弱提升（卡片）
    2: ShadowSpec(16, 0, 4),    # 中等提升（弹窗）
    3: ShadowSpec(24, 0, 8),    # 强提升（模态框）
}


# ============================================================
# 动画系统
# ============================================================
ANIMATION_DURATION = {
    "fast": 150,      # hover 反馈
    "normal": 250,    # 淡入淡出
    "slow": 400,      # 页面切换
    "entrance": 300,  # 弹窗入场
}


# ============================================================
# 间距系统
# ============================================================
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "xxl": 48,
}


# ============================================================
# 主题获取 API
# ============================================================
def get_tokens() -> Dict[str, str]:
    """获取当前主题的完整 Token 字典。"""
    return DARK if isDarkTheme() else LIGHT


def get_token(key: str) -> str:
    """获取单个 Token 值。"""
    tokens = get_tokens()
    return tokens.get(key, "")


def is_dark() -> bool:
    return isDarkTheme()


# ============================================================
# 常用 QSS 片段生成器
# ============================================================
def scrollbar_qss() -> str:
    """生成统一的滚动条 QSS。"""
    t = get_tokens()
    return f"""
        QScrollBar:vertical {{
            background-color: {t['scrollbar_bg']};
            width: 6px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {t['scrollbar_handle']};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {t['scrollbar_handle_hover']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background-color: {t['scrollbar_bg']};
            height: 6px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {t['scrollbar_handle']};
            border-radius: 3px;
            min-width: 24px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {t['scrollbar_handle_hover']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """


def card_qss(border_radius: str = "12px") -> str:
    """生成统一的卡片容器 QSS。"""
    t = get_tokens()
    return f"""
        background-color: {t['bg_container']};
        border: 1px solid {t['border_default']};
        border-radius: {border_radius};
    """


def glass_qss(border_radius: str = "14px") -> str:
    """生成统一的毛玻璃容器 QSS。"""
    t = get_tokens()
    return f"""
        background-color: {t['bg_glass']};
        border: 1px solid {t['border_strong']};
        border-radius: {border_radius};
    """


def input_qss() -> str:
    """生成统一的输入框 QSS。"""
    t = get_tokens()
    return f"""
        background-color: {t['input_bg']};
        border: 1px solid {t['input_border']};
        border-radius: 8px;
        color: {t['text_primary']};
        padding: 6px 10px;
    """
