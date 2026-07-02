"""图片工具 — 生成 + 视觉分析。"""

import os
import json
import pathlib
from datetime import datetime
from typing import Any

import requests
from pydantic_ai.tools import RunContext

from src.core.logger import logger
from src.agent.tools_cache import cached


@cached(ttl_seconds=0)
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

        from src.core.database import get_user_data_dir
        save_dir = os.path.join(get_user_data_dir(), "generated_images")

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


@cached(ttl_seconds=0)
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
        # 延迟导入避免循环依赖
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
