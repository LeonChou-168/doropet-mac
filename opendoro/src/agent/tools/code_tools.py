"""代码执行工具。"""

import os
import json
import subprocess
import sys

from src.agent.tools._helpers import _get_project_dir, _format_permission_error, _format_file_not_found_error


async def run_python_script(file_path: str) -> str:
    """Run a Python script from the local filesystem and return the output.

    Args:
        file_path: The path of the python file to run (e.g., 'plugin/hello.py').
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
            return json.dumps({"status": "error", "message": "Permission denied: Cannot run scripts from protected directory."})

    if not os.path.exists(abs_path):
        return _format_file_not_found_error(file_path, project_dir)

    try:
        result = subprocess.run([sys.executable, abs_path], capture_output=True, text=False, timeout=30)

        def decode_bytes(b):
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return b.decode('gbk')
                except UnicodeDecodeError:
                    return b.decode('utf-8', errors='replace')

        output = decode_bytes(result.stdout)
        if result.stderr:
            output += "\nErrors:\n" + decode_bytes(result.stderr)

        return json.dumps({
            "status": "success",
            "message": f"Script executed. Exit code: {result.returncode}",
            "output": output
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "Script execution timed out."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
