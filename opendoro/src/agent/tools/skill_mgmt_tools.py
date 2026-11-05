"""Agent 技能管理工具 + _get_skill_manager 模块单例。"""

import json

from src.core.logger import logger
from src.agent.tools_cache import cached

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


@cached(ttl_seconds=60)
async def list_agent_skills() -> str:
    """List all installed agent skills with their descriptions and types."""
    manager = _get_skill_manager()
    skills = manager.list_skills()
    return json.dumps({
        "status": "success",
        "skills": skills,
        "count": len(skills)
    }, ensure_ascii=False)


@cached(ttl_seconds=0)
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
