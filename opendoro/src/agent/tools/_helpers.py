"""通用辅助函数 — 供 file_tools, code_tools 等模块使用。"""

import os
import json
import glob

from src.core.platform_paths import get_app_root


def _get_project_dir() -> str:
    return get_app_root()


def _format_permission_error(abs_path: str, project_dir: str) -> str:
    return json.dumps({
        "status": "error",
        "message": f"Permission denied: 只能访问项目目录 '{project_dir}' 内的文件。",
        "allowed_dir": project_dir
    }, ensure_ascii=False)


def _format_file_not_found_error(file_path: str, project_dir: str) -> str:
    similar_files = glob.glob(os.path.join(project_dir, '**', f'*{os.path.basename(file_path)}*'), recursive=True)
    similar_names = [os.path.relpath(f, project_dir) for f in similar_files[:5]]
    suggestion = f" 相似文件: {', '.join(similar_names)}" if similar_names else ""
    return json.dumps({
        "status": "error",
        "message": f"File not found: {file_path}.{suggestion}",
        "suggestion": "请检查文件路径是否正确"
    }, ensure_ascii=False)
