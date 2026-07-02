"""
数据迁移模块。

支持将用户数据从旧路径迁移到新路径，提供：
- 检查是否需要迁移
- 完整迁移所有数据目录
- 进度回调
- 复制或移动两种模式
"""

import os
import shutil
import logging
from typing import Optional, Callable, List, Tuple

logger = logging.getLogger("DoroPet.Core")


# 需要迁移的所有数据子目录/文件
MIGRATE_ITEMS = [
    "data",             # SQLite 数据库（chat.db, config.db, personas.db, cache.db, pet.db 等）
    "cookies",          # 音乐平台 Cookie
    "music",            # 播放列表和下载
    "attachments",      # 聊天附件
    "cache",            # TTS/图片缓存
    "log",              # 日志文件
    "generated_images", # AI 生成的图片
    "skills",           # 用户安装的技能
    "musicdl_outputs",  # musicdl 临时输出
    "temp",             # 临时文件（浏览器截图等）
    "browser_state.json",  # 浏览器状态
]

# 迁移时需要忽略的模式（如临时文件）
IGNORE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    "*.tmp",
]


def get_default_data_dir() -> Optional[str]:
    """获取默认的用户数据目录。"""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return os.path.join(local_app_data, "DoroPet")
    return None


def get_current_data_dir() -> str:
    """获取当前生效的用户数据目录。"""
    from src.core.database import get_user_data_dir
    return get_user_data_dir()


class DataMigrator:
    """数据迁移器。"""

    @classmethod
    def check_migration_needed(cls, old_path: str, new_path: str) -> bool:
        """
        检查是否需要迁移：
        - 旧路径存在且不为空
        - 新路径与旧路径不同
        - 新路径不存在或为空
        """
        if not old_path or not os.path.isdir(old_path):
            return False

        norm_old = os.path.normpath(old_path)
        norm_new = os.path.normpath(new_path)

        if norm_old == norm_new:
            return False

        if os.path.isdir(new_path):
            # 检查新路径是否为空
            try:
                if os.listdir(new_path):
                    return False  # 新路径已有数据，不覆盖
            except PermissionError:
                return False

        # 检查旧路径是否有数据可迁移
        has_data = False
        for item in MIGRATE_ITEMS:
            src = os.path.join(old_path, item)
            if os.path.exists(src):
                has_data = True
                break

        return has_data

    @classmethod
    def get_migration_info(cls, old_path: str, new_path: str) -> dict:
        """
        获取迁移信息：各项目的数量和大小。
        返回 {item_name: {"count": int, "size_bytes": int}, ...}
        """
        info = {"total_size": 0, "total_files": 0, "items": {}}

        for item in MIGRATE_ITEMS:
            src = os.path.join(old_path, item)
            if not os.path.exists(src):
                continue

            count = 0
            size = 0

            if os.path.isfile(src):
                try:
                    size = os.path.getsize(src)
                    count = 1
                except OSError:
                    pass
            elif os.path.isdir(src):
                for dirpath, dirnames, filenames in os.walk(src):
                    for fn in filenames:
                        fp = os.path.join(dirpath, fn)
                        try:
                            size += os.path.getsize(fp)
                            count += 1
                        except OSError:
                            pass

            info["items"][item] = {"count": count, "size_bytes": size}
            info["total_size"] += size
            info["total_files"] += count

        return info

    @classmethod
    def migrate(
        cls,
        old_path: str,
        new_path: str,
        method: str = "copy",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, List[str]]:
        """
        执行数据迁移。

        :param old_path: 源数据目录
        :param new_path: 目标数据目录
        :param method: "copy" 复制后保留原数据，或 "move" 移动后删除原数据
        :param progress_callback: 进度回调 (current, total, item_name)
        :return: (成功数, 错误列表)
        """
        os.makedirs(new_path, exist_ok=True)

        total = len(MIGRATE_ITEMS)
        success = 0
        errors = []

        for i, item in enumerate(MIGRATE_ITEMS):
            if progress_callback:
                progress_callback(i + 1, total, item)

            src = os.path.join(old_path, item)
            dst = os.path.join(new_path, item)

            if not os.path.exists(src):
                success += 1
                continue

            try:
                # 确保目标父目录存在
                dst_parent = os.path.dirname(dst)
                if dst_parent:
                    os.makedirs(dst_parent, exist_ok=True)

                if method == "move":
                    # 如果目标已存在，先删除
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst, ignore_errors=True)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)
                    logger.info(f"[DataMigrator] Moved: {item}")
                else:
                    # copy 模式
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst, ignore_errors=True)
                        shutil.copytree(
                            src, dst,
                            ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
                            symlinks=False,
                        )
                    else:
                        shutil.copy2(src, dst)
                    logger.info(f"[DataMigrator] Copied: {item}")

                success += 1
            except PermissionError as e:
                msg = f"权限不足 - {item}: {e}"
                errors.append(msg)
                logger.error(f"[DataMigrator] {msg}")
            except OSError as e:
                msg = f"IO 错误 - {item}: {e}"
                errors.append(msg)
                logger.error(f"[DataMigrator] {msg}")
            except Exception as e:
                msg = f"未知错误 - {item}: {e}"
                errors.append(msg)
                logger.error(f"[DataMigrator] {msg}")

        return success, errors

    @classmethod
    def get_total_data_size(cls, data_dir: str) -> Tuple[int, int]:
        """
        获取数据目录的总大小和文件数。
        :return: (total_size_bytes, file_count)
        """
        if not os.path.isdir(data_dir):
            return 0, 0

        total_size = 0
        file_count = 0

        for dirpath, dirnames, filenames in os.walk(data_dir):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass

        return total_size, file_count

    @classmethod
    def format_size(cls, size_bytes: int) -> str:
        """格式化字节大小为可读字符串。"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
