"""终端命令执行工具。

允许 AI 在本地终端 (CMD/PowerShell) 中执行命令并获取输出。
"""

import os
import json
import subprocess

from src.agent.tools._helpers import _get_project_dir
from src.core.logger import logger


async def run_terminal_command(
    command: str,
    working_dir: str = "",
    timeout_seconds: int = 60,
) -> str:
    """在本地终端执行一条命令，并返回标准输出和错误输出。

    适用于 Windows CMD 或 PowerShell 命令，例如：
    - dir, cd, type, findstr
    - git status, git diff
    - pip install, npm install
    - python script.py
    - echo, set, mkdir

    **重要规则**：
    - 默认在 DoroPet 项目目录下执行
    - 不允许执行可能造成不可逆破坏的命令（如 format、del /s 等）
    - 不要执行需要交互式输入的命令（如 ssh、python 交互模式）
    - 输出超过 8000 字符会自动截断
    - 超时默认 60 秒

    Args:
        command: 要执行的命令字符串。
        working_dir: 工作目录（可选，默认为 DoroPet 项目目录）。
        timeout_seconds: 超时秒数（默认 60，最大 120）。
    """
    if not command or not command.strip():
        return json.dumps({"status": "error", "message": "命令不能为空。"})

    # 确定工作目录
    project_dir = _get_project_dir()
    cwd = project_dir
    if working_dir:
        abs_wd = os.path.abspath(working_dir)
        if os.path.isdir(abs_wd):
            cwd = abs_wd
        else:
            return json.dumps({
                "status": "error",
                "message": f"工作目录不存在: {working_dir}"
            })

    # 限制超时
    timeout = min(max(timeout_seconds, 5), 120)

    logger.info(f"[Terminal] 执行命令: {command[:100]} (cwd={cwd}, timeout={timeout}s)")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": f"命令执行超时（{timeout} 秒）。请简化命令或增加超时时间。"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": f"命令执行失败: {str(e)}"})

    # 解码输出（Windows 可能用 gbk）
    def decode_bytes(b: bytes) -> str:
        if not b:
            return ""
        for encoding in ("utf-8", "gbk", "cp936"):
            try:
                return b.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return b.decode("utf-8", errors="replace")

    stdout = decode_bytes(result.stdout)
    stderr = decode_bytes(result.stderr)

    # 合并输出并截断
    output = stdout
    if stderr:
        if output:
            output += "\n"
        output += "[stderr]\n" + stderr

    truncated = False
    if len(output) > 8000:
        output = output[:8000] + f"\n\n... (输出截断，共 {len(output)} 字符)"
        truncated = True

    return json.dumps({
        "status": "success",
        "message": f"命令执行完成，退出码: {result.returncode}",
        "exit_code": result.returncode,
        "output": output,
        "truncated": truncated,
        "cwd": cwd,
    }, ensure_ascii=False)
