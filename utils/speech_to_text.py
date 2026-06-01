"""
Speech-to-Text (STT) — ovozli xabarlarni matnga aylantiradi.
OpenAI gpt-4o-transcribe modeli — eng kuchli va aniq STT model.
"""
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("vodiysoftbot.stt")

OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"


async def speech_to_text(file_path: str, api_key: str, model: str = "gpt-4o-transcribe") -> Optional[str]:
    """
    Ovozli faylni OpenAI gpt-4o-transcribe orqali matnga aylantiradi.
    file_path — yuklab olingan .ogg yoki .mp3 fayl
    api_key — OpenAI API kaliti
    model — STT model nomi (default: gpt-4o-transcribe)
    """
    if not os.path.exists(file_path):
        logger.error(f"Fayl topilmadi: {file_path}")
        return None

    import mimetypes
    ext = os.path.splitext(file_path)[1].lower()
    content_type = mimetypes.guess_type(file_path)[0] or "audio/mpeg"
    if ext not in [".mp3", ".wav", ".ogg", ".m4a", ".webm", ".flac"]:
        logger.warning(f"Noto'g'ri audio format: {file_path}, content_type={content_type}")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    data = {
        "model": model,
        "response_format": "text",
    }
    # Avval tilsiz (auto-detect), keyin uz, keyin ru, keyin en
    fallback_languages = ["auto", "uz", "ru", "en"]
    for lang in fallback_languages:
        try:
            form = aiohttp.FormData()
            with open(file_path, "rb") as f:
                form.add_field("file", f, filename=os.path.basename(file_path), content_type=content_type)
                for k, v in data.items():
                    form.add_field(k, v)
                # auto = tilsiz yuborish (model o'zi aniqlaydi)
                if lang != "auto":
                    form.add_field("language", lang)
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_TRANSCRIPTION_URL, headers=headers, data=form, timeout=120) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            text = text.strip()
                            if text:
                                return text
                        else:
                            err = await resp.text()
                            logger.error(f"STT API xato: {resp.status} — {err} (model={model}, lang={lang})")
        except Exception as exc:
            logger.exception(f"STT xatosi (model={model}, lang={lang}): {exc}")
    return None
