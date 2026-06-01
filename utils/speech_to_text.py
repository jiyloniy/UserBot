"""
Speech-to-Text (STT) — ovozli xabarlarni matnga aylantiradi.
OpenAI Whisper API yoki vosk, vosk-server, Google Speech-to-Text ishlatish mumkin.
"""
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("vodiysoftbot.stt")

OPENAI_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

async def speech_to_text(file_path: str, api_key: str) -> Optional[str]:
    """
    Ovozli faylni OpenAI Whisper orqali matnga aylantiradi.
    file_path — yuklab olingan .ogg yoki .mp3 fayl
    api_key — OpenAI API kaliti
    """
    if not os.path.exists(file_path):
        logger.error(f"Fayl topilmadi: {file_path}")
        return None

    import mimetypes
    ext = os.path.splitext(file_path)[1].lower()
    # Ovozli xabarlar uchun eng yaxshi format: mp3 yoki wav
    content_type = mimetypes.guess_type(file_path)[0] or "audio/mpeg"
    if ext not in [".mp3", ".wav", ".ogg", ".m4a"]:
        logger.warning(f"Noto'g'ri audio format: {file_path}, content_type={content_type}")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    data = {
        "model": "whisper-1",
        "response_format": "text",
    }
    # Fallback: tilni majburan en yoki ru qilish
    fallback_languages = ["uz", "uzb", "uzbek", "ru", "en"]
    for lang in fallback_languages:
        try:
            form = aiohttp.FormData()
            with open(file_path, "rb") as f:
                form.add_field("file", f, filename=os.path.basename(file_path), content_type=content_type)
                for k, v in data.items():
                    form.add_field(k, v)
                # Avval tilsiz, keyin ru, keyin en
                if lang != "uz":
                    form.add_field("language", lang)
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_WHISPER_URL, headers=headers, data=form, timeout=60) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            return text.strip()
                        else:
                            err = await resp.text()
                            logger.error(f"Whisper API xato: {resp.status} — {err} (lang={lang})")
        except Exception as exc:
            logger.exception(f"STT xatosi (lang={lang}): {exc}")
    return None
