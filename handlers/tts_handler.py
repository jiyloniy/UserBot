"""
TTS Handler — .tts buyrug'i orqali matnni ovozga aylantiradi va yuboradi.

Foydalanish (Telegram chatda):
    .tts Salom, dunyo!

Natija: Ovozli xabar sifatida javob yuboriladi.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from telethon import TelegramClient, events

from utils.text_to_speech import text_to_speech

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("vodiysoftbot.tts_handler")


class TTSHandler:
    """Telegram chatda .tts buyrug'ini qayta ishlaydi."""

    COMMAND_PREFIX = ".tts "

    def __init__(self, client: TelegramClient, config: "Config") -> None:
        self.client = client
        self.config = config

    def register(self) -> None:
        """Event handlerni ro'yxatga oladi."""

        @self.client.on(events.NewMessage(outgoing=True, pattern=r"\.tts\s+.+"))
        async def on_tts_command(event: events.NewMessage.Event) -> None:
            await self._handle_tts(event)

    async def _handle_tts(self, event: events.NewMessage.Event) -> None:
        """TTS buyrug'ini qayta ishlaydi."""
        # Pattern: .tts <matn> — prefixdan keyingi hamma narsa matn
        raw = event.message.text or ""
        # ".tts" dan keyingi barcha matnni olish
        text = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""

        if not text:
            await event.edit("⚠️ Matn kiriting: `.tts Salom dunyo`")
            return

        if not self.config.ELEVENLABS_API_KEY:
            await event.edit("⚠️ ELEVENLABS_API_KEY sozlanmagan. .env faylini tekshiring.")
            return

        await event.edit("🎙️ Ovoz yaratilmoqda...")

        file_path = await text_to_speech(
            text=text,
            api_key=self.config.ELEVENLABS_API_KEY,
            voice_id=self.config.ELEVENLABS_VOICE_ID,
            model_id=self.config.ELEVENLABS_MODEL_ID,
            auto_enhance=self.config.ELEVENLABS_AUTO_ENHANCE,
            openai_api_key=self.config.OPENAI_API_KEY,
        )

        if file_path and os.path.exists(file_path):
            try:
                await self.client.send_file(
                    event.chat_id,
                    file_path,
                    voice_note=True,
                    reply_to=event.message.reply_to_msg_id,
                )
                await event.delete()
            except Exception as exc:
                logger.exception(f"TTS fayl yuborishda xato: {exc}")
                await event.edit(f"❌ Ovoz yuborishda xato: {exc}")
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            await event.edit("❌ Ovoz yaratishda xato yuz berdi.")
