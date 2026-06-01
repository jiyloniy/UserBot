"""
Text-to-Speech (TTS) — matnni ovozga aylantiradi.
ElevenLabs API orqali ishlaydi.

Foydalanish:
    from utils.text_to_speech import text_to_speech
    file_path = await text_to_speech("Salom, dunyo!", api_key, voice_id)
"""
import logging
import os
import tempfile
import uuid
from typing import Optional

import aiohttp

logger = logging.getLogger("vodiysoftbot.tts")

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def text_to_speech(
    text: str,
    api_key: str,
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
    model_id: str = "eleven_multilingual_v2",
    output_format: str = "mp3_44100_128",
) -> Optional[str]:
    """
    Matnni ElevenLabs API orqali ovozga aylantiradi.

    Args:
        text: Ovozga aylantiriladigan matn
        api_key: ElevenLabs API kaliti
        voice_id: Ovoz identifikatori (default: George)
        model_id: TTS model (default: eleven_multilingual_v2)
        output_format: Audio format (default: mp3_44100_128)

    Returns:
        Yaratilgan audio faylning yo'li yoki None (xato bo'lsa)
    """
    if not text or not text.strip():
        logger.warning("TTS: bo'sh matn berildi")
        return None

    if not api_key:
        logger.error("TTS: ELEVENLABS_API_KEY sozlanmagan")
        return None

    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                params={"output_format": output_format},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    temp_dir = tempfile.gettempdir()
                    file_path = os.path.join(temp_dir, f"tts_{uuid.uuid4().hex}.mp3")
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)
                    logger.info(f"TTS: audio yaratildi — {file_path}")
                    return file_path
                else:
                    error_text = await resp.text()
                    logger.error(
                        f"ElevenLabs API xato: {resp.status} — {error_text}"
                    )
                    return None

    except aiohttp.ClientError as exc:
        logger.exception(f"TTS ulanish xatosi: {exc}")
        return None
    except Exception as exc:
        logger.exception(f"TTS kutilmagan xato: {exc}")
        return None
