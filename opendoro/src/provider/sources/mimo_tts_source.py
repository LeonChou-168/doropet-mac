import os
import base64
import tempfile
from typing import Optional, List, Dict
from openai import OpenAI

from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, MIMO_TTS_CONFIG_FIELDS
from src.core.logger import logger


@register_provider_adapter(
    "mimo_tts",
    "小米 MiMo TTS (语音合成)",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "base_url": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5-tts",
        "voice": "冰糖",
    },
    provider_display_name="MiMo TTS",
    config_fields=MIMO_TTS_CONFIG_FIELDS
)
class ProviderMimoTTS(TTSProvider):
    """小米 MiMo TTS Provider。

    支持三种模型：
    - mimo-v2.5-tts: 预置音色
    - mimo-v2.5-tts-voicedesign: 文本描述设计音色
    - mimo-v2.5-tts-voiceclone: 音频样本复刻音色

    API 使用 chat/completions 端点（非 audio/speech），音频以 base64 返回。
    """

    PRESET_VOICES = [
        {"id": "冰糖",   "name": "冰糖 - 中文女性",  "language": "zh"},
        {"id": "茉莉",   "name": "茉莉 - 中文女性",  "language": "zh"},
        {"id": "苏打",   "name": "苏打 - 中文男性",  "language": "zh"},
        {"id": "白桦",   "name": "白桦 - 中文男性",  "language": "zh"},
        {"id": "Mia",    "name": "Mia - 英文女性",   "language": "en"},
        {"id": "Chloe",  "name": "Chloe - 英文女性", "language": "en"},
        {"id": "Milo",   "name": "Milo - 英文男性",  "language": "en"},
        {"id": "Dean",   "name": "Dean - 英文男性",  "language": "en"},
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._http_client = None
        self._openai_client = None

    def _get_provider_type(self):
        return ProviderType.TEXT_TO_SPEECH

    def _is_voice_design(self) -> bool:
        """判断当前模型是否为音色设计模式。"""
        model = (self.model_name or "").lower()
        return "voicedesign" in model

    def _is_voice_clone(self) -> bool:
        """判断当前模型是否为音色复刻模式。"""
        model = (self.model_name or "").lower()
        return "voiceclone" in model

    def _get_client(self) -> OpenAI:
        if self._openai_client is None:
            api_key = self.config.api_key or os.environ.get("MIMO_API_KEY", "")
            base_url = self.config.base_url or "https://api.xiaomimimo.com/v1"

            import httpx
            self._http_client = httpx.Client(timeout=self.config.timeout)
            self._openai_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=self._http_client
            )
        return self._openai_client

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        client = self._get_client()
        model = self.model_name or "mimo-v2.5-tts"
        voice_id = voice or self.config.voice or ""
        response_format = kwargs.get("response_format", "wav")

        # 构造 messages
        messages = []
        if self._is_voice_design():
            # 音色设计模式：user 消息 = 音色描述
            voice_prompt = voice_id or "Give me a natural, clear voice."
            messages.append({"role": "user", "content": voice_prompt})
        elif self._is_voice_clone():
            # 音色复刻模式：需要参考音频（从 extra_config 获取）
            prompt_audio = kwargs.get("prompt_audio", "")
            prompt_text = kwargs.get("prompt_text", "")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text or "Clone this voice."},
                    {"type": "audio_url", "audio_url": {"url": prompt_audio}}
                ] if prompt_audio else "Clone this voice."
            })
        else:
            # 预置音色模式：user 消息为风格控制指令（可选）
            style_instruction = kwargs.get("style_instruction", "")
            if style_instruction:
                messages.append({"role": "user", "content": style_instruction})

        # assistant 消息 = 待合成文本
        messages.append({"role": "assistant", "content": text})

        # 构造 audio 参数
        audio_params = {"format": response_format}
        if not self._is_voice_design():
            # 预置音色 / 音色复刻模式：传入 voice
            audio_params["voice"] = voice_id if voice_id else "mimo_default"
        else:
            # 音色设计模式：启用智能润色
            audio_params["optimize_text_preview"] = True

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                audio=audio_params,
                extra_body={"enable_enhancement": True} if kwargs.get("enable_enhancement") else {}
            )

            message = response.choices[0].message
            if not hasattr(message, 'audio') or not message.audio:
                raise ValueError("MiMo TTS 未返回音频数据")

            audio_bytes = base64.b64decode(message.audio.data)

            with tempfile.NamedTemporaryFile(suffix=f".{response_format}", delete=False) as tmp_file:
                output_path = tmp_file.name
                tmp_file.write(audio_bytes)

            return TTSResponse(
                audio_path=output_path,
                format=response_format
            )

        except Exception as e:
            logger.error(f"MiMo TTS synthesis failed: {e}")
            raise

    def get_voices(self) -> List[Dict]:
        """返回预置音色列表（仅 mimo-v2.5-tts 适用）。"""
        if self._is_voice_design():
            # 音色设计模式没有预置音色，返回说明
            return [{"id": "", "name": "音色设计模式 — 请在音色字段输入描述文本", "language": ""}]
        return self.PRESET_VOICES

    def test(self) -> bool:
        try:
            self.synthesize("测试语音")
            return True
        except Exception as e:
            logger.error(f"MiMo TTS test failed: {e}")
            return False

    def close(self):
        if self._http_client:
            try:
                self._http_client.close()
            except:
                pass
        super().close()
