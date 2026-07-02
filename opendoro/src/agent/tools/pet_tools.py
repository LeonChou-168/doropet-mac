"""宠物互动工具 — Live2D 表情和属性修改。"""

import json
from typing import Any

from pydantic_ai.tools import RunContext


async def set_expression(ctx: RunContext[Any], expression_name: str) -> str:
    """Change the facial expression of the Live2D model. Use this to reflect the mood or emotion of the response.

    Args:
        ctx: Run context (injected by pydantic-ai).
        expression_name: The name of the expression to set.
    """
    available = getattr(ctx.deps, 'available_expressions', [])
    if available and expression_name not in available:
        return json.dumps({
            "status": "error",
            "message": f"表情 '{expression_name}' 不存在。可用表情: {', '.join(available)}",
        }, ensure_ascii=False)

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
