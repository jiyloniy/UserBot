"""
OpenAI GPT-4o audio input helper — audio faylni to'g'ridan-to'g'ri multimodal modelga yuboradi.
"""
import logging
from openai import AsyncOpenAI

logger = logging.getLogger("vodiysoftbot.audiohelper")

async def gpt4o_audio_chat(api_key: str, model: str, audio_path: str, system_prompt: str, history: list, max_tokens: int = 500) -> str:
    """
    OpenAI GPT-4o yoki audio-input modeliga audio faylni yuborib, javob oladi.
    """
    client = AsyncOpenAI(api_key=api_key)
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    try:
        with open(audio_path, "rb") as f:
            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_tokens,
                files=[f],
            )
        text = completion.choices[0].message.content or ""
        return text.strip()
    except Exception as exc:
        logger.exception(f"GPT-4o audio input xatosi: {exc}")
        return ""
