"""
Pydantic-AI 工具函数 — 从 agent_tools.py 迁移。

所有工具使用 pydantic-ai 的 RunContext[DoroDeps] 作为第一个参数，
通过 ctx.deps 发射 UI 信号（表情变化、宠物属性变化等）。
"""

import os
import json
import glob
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Optional, Any

import requests
from bs4 import BeautifulSoup

from pydantic_ai.tools import RunContext

from src.core.logger import logger
from src.agent.tools.browser_control import BROWSER_TOOLS


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _get_project_dir() -> str:
    return os.getcwd()


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


# ---------------------------------------------------------------------------
# 文件操作工具
# ---------------------------------------------------------------------------

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

    return json.dumps({"status": "success", "message": f"File written to {file_path}"})


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

    return json.dumps({"status": "success", "message": f"Deleted {deleted_count} line(s) from {file_path}"})


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


# ---------------------------------------------------------------------------
# 搜索工具
# ---------------------------------------------------------------------------

async def search_baidu(query: str) -> str:
    """Search for real-time information on the internet using Baidu.

    Args:
        query: The search keywords.
    """
    if not query:
        return json.dumps({"status": "error", "message": "Query is required."})

    try:
        url = "https://www.baidu.com/s"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        params = {"wd": query}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select('.result.c-container, .result-op.c-container'):
            title_elem = item.select_one("h3")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            link = title_elem.select_one("a")["href"] if title_elem.select_one("a") else ""
            abstract_elem = item.select_one(".c-abstract") or item.select_one(".c-span18")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            if title and link:
                results.append({"title": title, "link": link, "snippet": abstract})
            if len(results) >= 5:
                break

        return json.dumps({
            "status": "success",
            "message": f"Found {len(results)} results.",
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def search_bing(query: str) -> str:
    """Search for real-time information using Bing. Optimized for Chinese users and general queries.

    Args:
        query: The search keywords.
    """
    if not query:
        return json.dumps({"status": "error", "message": "Query is required."})

    try:
        url = "https://cn.bing.com/search"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        params = {"q": query}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select('.b_algo'):
            title_elem = item.select_one("h2 a")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            link = title_elem["href"]
            snippet_elem = item.select_one(".b_caption p")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            if title and link:
                results.append({"title": title, "link": link, "snippet": snippet})
            if len(results) >= 5:
                break

        return json.dumps({
            "status": "success",
            "message": f"Found {len(results)} results from Bing.",
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def visit_webpage(url: str) -> str:
    """Visit a specific URL and extract its text content.

    Args:
        url: The URL to visit.
    """
    if not url:
        return json.dumps({"status": "error", "message": "URL is required."})

    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style", "nav", "footer", "header", "meta", "noscript"]):
            script.extract()

        text = soup.get_text(separator="\n", strip=True)
        content = text[:4000] + "..." if len(text) > 4000 else text

        return json.dumps({
            "status": "success",
            "message": f"Successfully visited {url}",
            "content": content or "No readable text found."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to visit webpage: {str(e)}"})


# ---------------------------------------------------------------------------
# 宠物互动工具（需要 UI 信号回传）
# ---------------------------------------------------------------------------

async def set_expression(expression_name: str) -> str:
    """Change the facial expression of the Live2D model. Use this to reflect the mood or emotion of the response.

    Args:
        expression_name: The name of the expression to set.
    """
    return json.dumps({
        "status": "success",
        "message": f"已修改为{expression_name}表情"
    }, ensure_ascii=False)


async def modify_pet_attribute(
    interaction: str = "",
    intensity: str = "moderate",
    attribute: str = "",
    action: str = ""
) -> str:
    """Modify the pet's attributes. Use for feeding, playing, cleaning, resting, or other interactions.

    Args:
        interaction: Semantic interaction type. Options: feed_snack, feed_meal, feed_feast, feed_bad, play_gentle, play_fun, play_exhausting, clean_wipe, clean_wash, rest_nap, rest_sleep, pet_affection, scold, comfort.
        intensity: Interaction intensity level. Options: light (0.5x), moderate (1.0x), heavy (1.5x).
        attribute: [Legacy] The attribute to modify. Use 'interaction' instead.
        action: [Legacy] The interaction action. Use 'interaction' instead.
    """
    from src.core.pet_constants import INTERACTION_NAMES

    if interaction:
        interaction_name = INTERACTION_NAMES.get(interaction, interaction)
        return json.dumps({
            "status": "success",
            "message": f"已执行{interaction_name}互动"
        }, ensure_ascii=False)

    legacy_action_names = {"feed": "投喂", "play": "玩耍", "clean": "清洁", "rest": "休息"}
    attr_names = {"hunger": "饱食度", "mood": "心情值", "cleanliness": "清洁度", "energy": "能量值"}

    attr_name = attr_names.get(attribute, attribute)
    action_name = legacy_action_names.get(action, action)

    return json.dumps({
        "status": "success",
        "message": f"已对{attr_name}执行{action_name}操作"
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 图片生成工具
# ---------------------------------------------------------------------------

async def generate_image(ctx: RunContext[Any] = None, prompt: str = "") -> str:
    """Generate an image based on a text prompt and save it locally.

    Use this when the user asks to generate, draw, or create an image/illustration.

    Args:
        prompt: The description of the image to generate.
    """
    try:
        from PyQt5.QtCore import QSettings
        from src.provider.manager import ProviderManager

        provider_manager = ProviderManager.get_instance()
        img_provider = provider_manager.get_image_provider()

        if img_provider:
            img_response = img_provider.generate(
                prompt=prompt,
                size="1024x1024",
                quality="standard"
            )
            if img_response.image_path:
                file_uri = pathlib.Path(img_response.image_path).as_uri()
                if ctx is not None:
                    ctx.deps.generated_images.append(img_response.image_path)
                return json.dumps({
                    "status": "success",
                    "message": f"Image generated successfully.\n![Generated Image]({file_uri})",
                    "image_path": img_response.image_path,
                    "revised_prompt": img_response.revised_prompt
                })
            else:
                return json.dumps({"status": "error", "message": "Image generation failed."})

        # Fallback: use QSettings for configuration
        settings = QSettings("DoroPet", "Settings")
        base_url = settings.value("img_base_url", "")
        api_key = settings.value("img_api_key", "")
        model = settings.value("img_model", "dall-e-3")

        if base_url and api_key:
            endpoint = f"{base_url.rstrip('/')}/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }
            response = requests.post(endpoint, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            res_json = response.json()

            if "data" in res_json and len(res_json["data"]) > 0:
                image_url = res_json["data"][0]["url"]
            elif "images" in res_json and len(res_json["images"]) > 0:
                image_url = res_json["images"][0]["url"]
            else:
                return json.dumps({"status": "error", "message": f"Invalid response: {res_json}"})
        else:
            # Default OpenAI DALL-E
            from openai import OpenAI
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            client = OpenAI(api_key=api_key or "placeholder", base_url=base_url)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url

        # Download image
        img_data = requests.get(image_url).content

        appdata_local = os.getenv('LOCALAPPDATA')
        if appdata_local:
            save_dir = os.path.join(appdata_local, "DoroPet", "generated_images")
        else:
            save_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "DoroPet", "generated_images")

        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gen_{timestamp}.png"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, 'wb') as handler:
            handler.write(img_data)

        file_uri = pathlib.Path(file_path).as_uri()
        if ctx is not None:
            ctx.deps.generated_images.append(file_path)
        return json.dumps({
            "status": "success",
            "message": f"Image generated successfully.\n![Generated Image]({file_uri})",
            "image_path": file_path,
            "image_url": image_url
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Agent 技能管理工具
# ---------------------------------------------------------------------------

_skill_manager_instance = None


def _get_skill_manager():
    global _skill_manager_instance
    if _skill_manager_instance is None:
        from src.core.skill_manager import SkillManager
        _skill_manager_instance = SkillManager()
    return _skill_manager_instance


async def install_agent_skill(source: str, skill_name: str = "") -> str:
    """Install an agent skill from various sources: GitHub (owner/repo), GitLab URL, zip URL, or local path.

    Args:
        source: The source to install from.
        skill_name: Optional custom name for the skill.
    """
    if not source:
        return json.dumps({"status": "error", "message": "Source parameter is required."})

    manager = _get_skill_manager()
    return manager.install_skill(source, skill_name if skill_name else None)


async def list_agent_skills() -> str:
    """List all installed agent skills with their descriptions and types."""
    manager = _get_skill_manager()
    skills = manager.list_skills()
    return json.dumps({
        "status": "success",
        "skills": skills,
        "count": len(skills)
    }, ensure_ascii=False)


async def get_skill_content(skill_name: str) -> str:
    """Get the full content/instructions of a document-type skill.

    Args:
        skill_name: The name of the skill to get content for.
    """
    if not skill_name:
        return json.dumps({"status": "error", "message": "skill_name parameter is required."})

    manager = _get_skill_manager()
    content = manager.get_skill_content(skill_name)
    if content is None:
        return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found."})

    return json.dumps({
        "status": "success",
        "skill_name": skill_name,
        "content": content
    }, ensure_ascii=False)


async def remove_agent_skill(skill_name: str) -> str:
    """Remove an installed agent skill.

    Args:
        skill_name: The name of the skill to remove.
    """
    if not skill_name:
        return json.dumps({"status": "error", "message": "skill_name parameter is required."})

    manager = _get_skill_manager()
    return manager.remove_skill(skill_name)


# ---------------------------------------------------------------------------
# 记忆工具 — 让 LLM 主动管理用户记忆
# ---------------------------------------------------------------------------

async def search_memories(ctx: RunContext[Any], query: str, top_n: int = 5) -> str:
    """搜索用户的长期记忆。

    搜索会智能匹配你查询中的关键词片段。例如搜索"喜欢什么饮料"也会匹配到"喜欢喝咖啡"。
    如果第一次搜索没有结果，请换一组关键词再试一次（比如用户说"我住aaa"，搜"住在"或"aaa"都能找到）。

    Args:
        query: 搜索关键词，尽量包含核心信息词（不包含的我你他吗呢等虚词也能搜到）
        top_n: 最多返回多少条记忆（默认 5 条）
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        results = mm.search_by_keywords(query, top_n)
        if not results:
            return '{"status":"ok","memories":[],"message":"未找到相关记忆"}'
        return json.dumps({"status": "ok", "memories": results}, ensure_ascii=False)
    except Exception as e:
        return '{"status":"error","message":"搜索记忆失败: '+str(e)+'"}'


async def add_memory(ctx: RunContext[Any], category: str, content: str, importance: int = 3) -> str:
    """记住一条关于用户的信息。当用户分享个人信息（名字、喜好、经历、约定等）时使用此工具主动记住。

    Args:
        category: 记忆类别（fact=事实信息, preference=偏好喜好, event=重要事件, emotion=情绪状态）
        content: 要记住的内容，简洁完整地描述
        importance: 重要程度 1-5（5=最重要，一般重要请用 3）
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        mm.save_to_long_term_memory(category, content, importance, [], content)
        return '{"status":"ok","message":"已记住"}'
    except Exception as e:
        return '{"status":"error","message":"保存记忆失败: '+str(e)+'"}'



async def delete_memory(ctx: RunContext[Any], memory_id: int) -> str:
    """删除一条指定的记忆。

    Args:
        memory_id: 要删除的记忆 ID
    """
    try:
        mm = ctx.deps.memory_manager
        if mm is None:
            return '{"status":"error","message":"记忆管理器不可用"}'
        mm.delete_memory(memory_id)
        return '{"status":"ok","message":"记忆已删除"}'
    except Exception as e:
        return '{"status":"error","message":"删除记忆失败: '+str(e)+'"}'


# ---------------------------------------------------------------------------
# 视觉读取工具
# ---------------------------------------------------------------------------

async def analyze_image(ctx: RunContext[Any], image_index: int = 1, prompt: str = "请详细描述这张图片。") -> str:
    """Analyze an image attached to the current conversation using a configured vision model.

    Use this only when the user asks about an attached image and the current chat model cannot see images directly.

    Args:
        image_index: The 1-based index of the attached image to analyze.
        prompt: What to inspect or describe in the image.
    """
    try:
        deps = ctx.deps
        images = list(getattr(deps, "available_images", []) or [])
        if not images:
            return json.dumps({"status": "error", "message": "当前对话没有可读取的图片附件。"}, ensure_ascii=False)

        if image_index < 1 or image_index > len(images):
            return json.dumps({
                "status": "error",
                "message": f"图片序号无效，可用范围为 1-{len(images)}。"
            }, ensure_ascii=False)

        file_path = images[image_index - 1]
        if not os.path.exists(file_path):
            return json.dumps({"status": "error", "message": f"图片文件不存在: {file_path}"}, ensure_ascii=False)

        db = getattr(deps, "db", None)
        cache_key = f"{file_path}|{prompt.strip()}"
        if db is not None:
            cached = db.get_image_description(cache_key) or db.get_image_description(file_path)
            if cached:
                return json.dumps({
                    "status": "success",
                    "image_index": image_index,
                    "cached": True,
                    "description": cached,
                }, ensure_ascii=False)

        vision_model_data = getattr(deps, "vision_model_data", None)
        if not vision_model_data:
            return json.dumps({"status": "error", "message": "未配置可用的视觉模型。"}, ensure_ascii=False)

        api_key, base_url, model = vision_model_data[:3]
        provider_id = vision_model_data[6] if len(vision_model_data) >= 7 else ""

        import base64
        import mimetypes
        from pydantic_ai.messages import TextContent, ImageUrl
        from src.agent.pydantic_agent import create_quick_agent

        mime_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        agent = create_quick_agent(
            model=model,
            base_url=base_url,
            api_key=api_key,
            provider_id=provider_id,
            system_prompt="你是图片理解助手。请准确、客观地读取图片内容，并只回答图片分析结果。",
        )
        result = await agent.run([
            TextContent(content=prompt or "请详细描述这张图片。"),
            ImageUrl(url=f"data:{mime_type};base64,{encoded}"),
        ])
        description = str(getattr(result, "output", "") or "").strip()

        if db is not None and description:
            db.save_image_description(cache_key, description)

        return json.dumps({
            "status": "success",
            "image_index": image_index,
            "cached": False,
            "description": description,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[analyze_image] Error: {e}")
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 工具注册表（用于插件过滤和 SkillManager 集成）
# ---------------------------------------------------------------------------

# 按类别分组的工具名
TOOLS_BY_CATEGORY = {
    "file": ["read_file", "write_file", "list_files", "search_files", "edit_file",
             "insert_at_line", "delete_lines", "find_in_file"],
    "search": ["search_baidu", "search_bing", "visit_webpage"],
    "image": ["generate_image"],
    "vision": ["analyze_image"],
    "expression": ["set_expression", "modify_pet_attribute"],
    "coding": ["run_python_script"],
    "memory": ["search_memories", "add_memory", "delete_memory"],
    "browser": ["browser_open", "browser_navigate", "browser_click", "browser_type",
                "browser_screenshot", "browser_get_content", "browser_execute_js", "browser_close"],
}

# 工具函数字典
ALL_TOOLS: dict[str, Any] = {
    # 文件
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "search_files": search_files,
    "edit_file": edit_file,
    "insert_at_line": insert_at_line,
    "delete_lines": delete_lines,
    "find_in_file": find_in_file,
    # 搜索
    "search_baidu": search_baidu,
    "search_bing": search_bing,
    "visit_webpage": visit_webpage,
    # 图片
    "generate_image": generate_image,
    "analyze_image": analyze_image,
    # 宠物
    "set_expression": set_expression,
    "modify_pet_attribute": modify_pet_attribute,
    # 代码执行
    "run_python_script": run_python_script,
    # 技能管理
    "install_agent_skill": install_agent_skill,
    "list_agent_skills": list_agent_skills,
    "get_skill_content": get_skill_content,
    "remove_agent_skill": remove_agent_skill,
    # 记忆
    "search_memories": search_memories,
    "add_memory": add_memory,
    "delete_memory": delete_memory,
    # 浏览器操控
    **BROWSER_TOOLS,
}


def get_filtered_tools(enabled_plugins: list[str]) -> list:
    """根据启用的插件过滤工具列表。"""
    filtered = []

    category_enabled = {
        cat: cat in enabled_plugins
        for cat in ["search", "image", "vision", "coding", "file", "expression", "memory", "browser"]
    }

    for cat, tool_names in TOOLS_BY_CATEGORY.items():
        if category_enabled.get(cat, False):
            for name in tool_names:
                if name in ALL_TOOLS:
                    filtered.append(ALL_TOOLS[name])

    # 始终包含技能管理工具
    for name in ["install_agent_skill", "list_agent_skills", "get_skill_content", "remove_agent_skill"]:
        if name in ALL_TOOLS:
            filtered.append(ALL_TOOLS[name])

    return filtered


def get_skill_tool_functions() -> list:
    """从 SkillManager 获取可执行技能的函数引用列表。"""
    manager = _get_skill_manager()
    tools = []
    try:
        from src.agent.skills.state import SkillEnabledState
        state = SkillEnabledState.get_instance()
    except ImportError:
        state = None

    for name, skill in manager.skills.items():
        if state is not None and not state.is_enabled(name):
            continue
        if skill.function:
            # 创建一个包装函数用作工具
            import re
            normalized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)

            def make_skill_wrapper(skill_obj, skill_name, func):
                async def wrapper(**kwargs) -> str:
                    try:
                        result = func(**kwargs)
                        if isinstance(result, str):
                            return result
                        return json.dumps({"status": "success", "result": result}, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"[SkillTool] Error executing '{skill_name}': {e}")
                        return json.dumps({"status": "error", "message": str(e)})

                wrapper.__name__ = normalized_name
                wrapper.__doc__ = skill_obj.description
                return wrapper

            tools.append(make_skill_wrapper(skill, name, skill.function))

    return tools
