from enum import Enum

from src.core.i18n import tr


class PlayMode(Enum):
    SEQUENCE = "sequence"
    LIST_LOOP = "list_loop"
    SINGLE_LOOP = "single_loop"
    SHUFFLE = "shuffle"


class VinylConstants:
    WIDGET_SIZE = 420
    RECORD_RADIUS = 130
    LABEL_RADIUS = 65
    CENTER_HOLE_OUTER = 12
    CENTER_HOLE_INNER = 6
    ROTATION_SPEED = 2.0
    ROTATION_INTERVAL = 25
    NEEDLE_ANGLE_PLAYING = 30
    NEEDLE_ANGLE_STOPPED = 60
    NEEDLE_ANGLE_PAUSED = 60


class PlayerConstants:
    BOTTOM_PLAYER_HEIGHT = 70
    PROGRESS_BAR_HEIGHT = 24
    BOTTOM_PLAYER_MARGIN = 24
    MAX_RETRY_COUNT = 3
    RETRY_DELAY_MS = 1000


class PlaylistConstants:
    DOCK_WIDTH = 350
    DOCK_ANIMATION_DURATION = 300


class ColorConstants:
    DEFAULT_BACKGROUND = "rgba(42, 42, 42, 1)"
    DARK_BG_START = "rgb(60, 60, 80)"
    DARK_BG_END = "rgb(30, 30, 50)"


PLAY_MODE_CONFIG = {
    PlayMode.SEQUENCE: ("right_arrow", "顺序播放"),
    PlayMode.LIST_LOOP: ("sync", "列表循环"),
    PlayMode.SINGLE_LOOP: ("update", "单曲循环"),
    PlayMode.SHUFFLE: ("tiles", "随机播放"),
}

MUSIC_PLATFORMS = [
    ('netease', '奈缇斯', 'NeteaseMusicClient'),
    ('qq', '咕嘎', 'QQMusicClient'),
    ('kugou', '酷汪', 'KugouMusicClient'),
    ('kuwo', '酷me', 'KuwoMusicClient'),
    ('migu', '咪咕', 'MiguMusicClient'),
]

PLATFORM_MAP = {
    "全部平台": "NeteaseMusicClient,QQMusicClient,KuwoMusicClient,KugouMusicClient,MiguMusicClient",
    "🎵 奈缇斯": "NeteaseMusicClient",
    "🎶 咕嘎": "QQMusicClient",
    "🎧 酷汪": "KugouMusicClient",
    "📻 酷me": "KuwoMusicClient",
    "🎤 咪咕": "MiguMusicClient",
    "📺 B站音乐": "BilibiliMusicClient",
}


def get_play_mode_name(mode: PlayMode) -> str:
    """获取播放模式的翻译显示名称。"""
    key_map = {
        PlayMode.SEQUENCE: "music.play_mode.sequence",
        PlayMode.LIST_LOOP: "music.play_mode.list_loop",
        PlayMode.SINGLE_LOOP: "music.play_mode.single_loop",
        PlayMode.SHUFFLE: "music.play_mode.shuffle",
    }
    default_map = {
        PlayMode.SEQUENCE: "顺序播放",
        PlayMode.LIST_LOOP: "列表循环",
        PlayMode.SINGLE_LOOP: "单曲循环",
        PlayMode.SHUFFLE: "随机播放",
    }
    return tr(key_map[mode], default=default_map[mode])


def get_platform_display_name(key: str) -> str:
    """获取音乐平台的翻译显示名称。

    Args:
        key: PLATFORM_MAP 的键，如 "全部平台"、"🎵 奈缇斯" 等

    Returns:
        翻译后的显示名称
    """
    name_map = {
        "全部平台": ("music.platform.all", "全部平台"),
        "🎵 奈缇斯": ("music.platform.netease", "🎵 奈缇斯"),
        "🎶 咕嘎": ("music.platform.qq", "🎶 咕嘎"),
        "🎧 酷汪": ("music.platform.kugou", "🎧 酷汪"),
        "📻 酷me": ("music.platform.kuwo", "📻 酷me"),
        "🎤 咪咕": ("music.platform.migu", "🎤 咪咕"),
        "📺 B站音乐": ("music.platform.bilibili", "📺 B站音乐"),
    }
    if key in name_map:
        return tr(name_map[key][0], default=name_map[key][1])
    return key
