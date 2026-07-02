"""文件 CRUD 工具 — 读/写/列/搜/编辑/插入/删除/查找。"""

import os
import json
import glob
import pathlib
from typing import Optional

from src.agent.tools._helpers import _get_project_dir, _format_permission_error, _format_file_not_found_error
from src.agent.tools_cache import cached, invalidate_read_cache


@cached(ttl_seconds=30)
async def read_file(file_path: str) -> str:
    """Read the content of a file from the local filesystem.

    Args:
        file_path: The absolute or relative path to the file to read.
    """
    if not file_path:
        return json.dumps({"status": "error", "message": "File path is required."})

    project_dir = _get_project_dir()
    abs_path = os.path.abspath(file_path)

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, project_dir)
    if not os.path.isfile(abs_path):
        return json.dumps({"status": "error", "message": f"Path is not a file: {file_path}"})

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(abs_path, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception:
            return json.dumps({"status": "error", "message": "Failed to decode file content."})

    MAX_CHARS = 100000
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + f"\n... (truncated, total {len(content)} chars)"

    return json.dumps({
        "status": "success",
        "message": f"Read {len(content)} characters from {file_path}",
        "content": content
    }, ensure_ascii=False)


async def write_file(file_path: str, content: str) -> str:
    """Write content to a file in the local filesystem. Overwrites if exists. Creates directories if needed.

    Args:
        file_path: The path to the file to write (e.g., 'plugin/my_script.py').
        content: The content to write to the file.
    """
    if not file_path:
        return json.dumps({"status": "error", "message": "File path is required."})

    abs_path = os.path.abspath(file_path)
    project_dir = _get_project_dir()

    if not abs_path.startswith(project_dir):
        return _format_permission_error(abs_path, project_dir)

    protected_dirs = [os.path.join(project_dir, "src", "core")]
    for protected in protected_dirs:
        if abs_path.startswith(protected):
            return json.dumps({"status": "error", "message": f"Permission denied: Cannot write to protected directory."})

    dir_name = os.path.dirname(abs_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)

    invalidate_read_cache(abs_path)
    return json.dumps({"status": "success", "message": f"File written to {file_path}"})


@cached(ttl_seconds=10)
async def list_files(dir_path: str = ".") -> str:
    """List all files and directories in a specific directory.

    Args:
        dir_path: The path to the directory to list (defaults to current directory).
    """
    target_dir = os.path.abspath(dir_path)
    if not os.path.exists(target_dir):
        return json.dumps({"status": "error", "message": f"Directory not found: {dir_path}"})

    items = os.listdir(target_dir)
    dirs = sorted([i + "/" for i in items if os.path.isdir(os.path.join(target_dir, i))])
    files = sorted([i for i in items if not os.path.isdir(os.path.join(target_dir, i))])

    return json.dumps({
        "status": "success",
        "message": f"Found {len(items)} items in {dir_path}",
        "items": dirs + files,
        "cwd": target_dir
    }, ensure_ascii=False)


@cached(ttl_seconds=60)
async def search_files(pattern: str, dir_path: str = ".") -> str:
    """Search for files by name pattern (glob) in a directory.

    Args:
        pattern: The glob pattern to match (e.g., '*.py', 'src/**/*.ts').
        dir_path: The root directory to search in (defaults to current directory).
    """
    if not pattern:
        return json.dumps({"status": "error", "message": "Pattern is required."})

    target_dir = os.path.abspath(dir_path)
    search_pattern = os.path.join(target_dir, pattern)
    matches = glob.glob(search_pattern, recursive=True)
    rel_matches = []
    for m in matches:
        try:
            rel_matches.append(os.path.relpath(m, target_dir))
        except Exception:
            rel_matches.append(m)

    return json.dumps({
        "status": "success",
        "message": f"Found {len(matches)} files matching '{pattern}'",
        "matches": rel_matches[:100]
    }, ensure_ascii=False)


async def edit_file(
    file_path: str,
    search: str,
    replace: str,
    replace_all: bool = False,
    fuzzy_match: bool = False,
    context_before: str = "",
    context_after: str = ""
) -> str:
    """Edit a file by searching for specific content and replacing it with new content.

    Args:
        file_path: The path to the file to edit.
        search: The exact text to search for in the file.
        replace: The text to replace the search content with.
        replace_all: If true, replace all occurrences.
        fuzzy_match: 是否启用模糊匹配（忽略空格和制表符差异）。
        context_before: 目标内容前的上下文，帮助定位重复内容。
        context_after: 目标内容后的上下文。
    """
    import re
    if not file_path or not search:
        return json.dumps({"status": "error", "message": "File path and search are required."})

    abs_path = os.path.abspath(file_path)
    project_dir = _get_project_dir()

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, project_dir)
    if not abs_path.startswith(project_dir):
        return _format_permission_error(abs_path, project_dir)

    with open(abs_path, "r", encoding="utf-8") as f:
        content = f.read()

    if search in content:
        if replace_all:
            new_content = content.replace(search, replace)
            count = content.count(search)
        else:
            new_content = content.replace(search, replace, 1)
            count = 1
    elif fuzzy_match:
        normalized_content = re.sub(r'[ \t]+', ' ', content)
        normalized_search = re.sub(r'[ \t]+', ' ', search)
        if normalized_search in normalized_content:
            new_content = content.replace(search, replace, 1)
            count = 1
        else:
            return json.dumps({"status": "error", "message": f"搜索内容未找到（模糊匹配也失败）。"})
    else:
        return json.dumps({"status": "error", "message": "Search content not found. Try fuzzy_match=true."})

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    invalidate_read_cache(abs_path)
    return json.dumps({"status": "success", "message": f"Replaced {count} occurrence(s) in {file_path}"})


async def insert_at_line(file_path: str, line_number: int, content: str) -> str:
    """Insert content at a specific line number in a file. Lines are 1-indexed.

    Args:
        file_path: The path to the file to modify.
        line_number: The line number where to insert content (1-indexed). Use 0 to prepend.
        content: The content to insert.
    """
    if not file_path:
        return json.dumps({"status": "error", "message": "File path is required."})

    abs_path = os.path.abspath(file_path)
    project_dir = _get_project_dir()

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, project_dir)
    if not abs_path.startswith(project_dir):
        return _format_permission_error(abs_path, project_dir)

    with open(abs_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not content.endswith("\n"):
        content += "\n"

    if line_number < 0:
        line_number = 0
    elif line_number > len(lines):
        line_number = len(lines)

    lines.insert(line_number, content)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    invalidate_read_cache(abs_path)
    return json.dumps({"status": "success", "message": f"Inserted content at line {line_number} in {file_path}"})


async def delete_lines(file_path: str, start_line: int, end_line: Optional[int] = None) -> str:
    """Delete a range of lines from a file. Lines are 1-indexed and inclusive.

    Args:
        file_path: The path to the file to modify.
        start_line: The starting line number to delete (1-indexed, inclusive).
        end_line: The ending line number to delete (1-indexed, inclusive). If not specified, only the start_line is deleted.
    """
    if not file_path or start_line < 1:
        return json.dumps({"status": "error", "message": "Valid file_path and start_line are required."})

    abs_path = os.path.abspath(file_path)
    project_dir = _get_project_dir()

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, project_dir)
    if not abs_path.startswith(project_dir):
        return _format_permission_error(abs_path, project_dir)

    with open(abs_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    if end_line is None:
        end_line = start_line
    if start_line > total_lines:
        return json.dumps({"status": "error", "message": f"Start line exceeds file length ({total_lines} lines)."})
    if end_line > total_lines:
        end_line = total_lines

    deleted_count = end_line - start_line + 1
    del lines[start_line - 1:end_line]

    with open(abs_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    invalidate_read_cache(abs_path)
    return json.dumps({"status": "success", "message": f"Deleted {deleted_count} line(s) from {file_path}"})


@cached(ttl_seconds=60)
async def find_in_file(file_path: str, pattern: str, context_lines: int = 2) -> str:
    """在文件中搜索内容并返回精确位置信息。支持正则表达式。

    Args:
        file_path: 要搜索的文件路径。
        pattern: 搜索模式（支持正则表达式）。
        context_lines: 返回匹配行前后的上下文行数（默认2行）。
    """
    import re
    if not file_path or not pattern:
        return json.dumps({"status": "error", "message": "File path and pattern are required."})

    abs_path = os.path.abspath(file_path)

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, _get_project_dir())

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(abs_path, 'r', encoding='gbk') as f:
                lines = f.readlines()
        except Exception:
            return json.dumps({"status": "error", "message": "Failed to decode file content."})

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    matches = []
    for i, line in enumerate(lines, 1):
        if regex.search(line):
            start = max(0, i - context_lines - 1)
            end = min(len(lines), i + context_lines)
            context = "".join(lines[start:end])
            matches.append({
                "line_number": i,
                "line_content": line.rstrip('\n\r'),
                "context": context.rstrip('\n\r')
            })

    if not matches:
        return json.dumps({"status": "info", "message": f"Pattern not found.", "matches": []})

    return json.dumps({
        "status": "success",
        "message": f"Found {len(matches)} match(es)",
        "matches": matches[:20]
    }, ensure_ascii=False)
