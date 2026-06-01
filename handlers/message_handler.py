"""
MessageHandler — Telegram xabarlarini qayta ishlaydi.

Javob berish mantiqи:
  • Shaxsiy chat (private)     → doim javob beradi (rate limit bilan)
  • Guruh / kanal kommentlari  → faqat:
        a) @mention (tag) bo'lsa
        b) faqat bizning o'z xabarimizga reply bo'lsa
  • O'z xabarlari              → o'tkazib yuboradi
  • Botlar                     → o'tkazib yuboradi
  • Bloklangan foydalanuvchi   → tinch o'tkazadi
  • FloodWait                  → Telegram talab qilgan vaqtcha kutadi
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Optional

from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    UserIsBlockedError,
    ChatWriteForbiddenError,
    SlowModeWaitError,
    MsgIdInvalidError,
)
from telethon.tl.types import (
    User,
    MessageMediaDocument,
    DocumentAttributeSticker,
    MessageMediaPhoto,
)

from prompts.system_prompt import get_system_prompt
from handlers.chat_enhancer import ChatEnhancer

if TYPE_CHECKING:
    from config import Config
    from handlers.ai_handler import AIHandler
    from utils.context_manager import ContextManager
    from utils.rate_limiter import RateLimiter

logger = logging.getLogger("vodiysoftbot.handler")


class MessageHandler:
    def __init__(
        self,
        client: TelegramClient,
        config: "Config",
        ai_handler: "AIHandler",
        context_manager: "ContextManager",
        rate_limiter: "RateLimiter",
    ) -> None:
        self.client = client
        self.config = config
        self.ai = ai_handler
        self.ctx = context_manager
        self.rl = rate_limiter
        self.enhancer = ChatEnhancer(client, config)
        self._me_id: Optional[int] = None
        self._me_username: Optional[str] = None

    # ── Initialization ───────────────────────────────────────────

    async def initialize(self) -> None:
        """Login bo'lgan akkaunt ma'lumotlarini yuklaydi."""
        me = await self.client.get_me()
        self._me_id = me.id
        self._me_username = (me.username or "").lower()
        logger.info(f"Akkaunt: {me.first_name}  (@{me.username})  ID={me.id}")

    # ── Main entry ───────────────────────────────────────────────

    async def handle(self, event: events.NewMessage.Event) -> None:
        """Yangi kiruvchi xabarni qayta ishlaydi."""
        try:
            if not await self._should_respond(event):
                return

            chat_id = event.chat_id

            # Rate limit tekshiruvi
            if not self.rl.can_respond(chat_id):
                wait = self.rl.seconds_until_ready(chat_id)
                logger.debug(f"Rate limit: chat {chat_id} uchun {wait:.0f}s qoldi")
                return


            # Ovozli xabarni aniqlash va multimodal modelga yuborish
            user_text = None
            msg = event.message
            is_voice = msg.voice or (msg.media and getattr(msg.media, 'document', None) and getattr(msg.media.document, 'mime_type', '').startswith('audio/ogg'))
            if is_voice:
                import tempfile, os
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, f"voice_{msg.id}.ogg")
                await self.client.download_media(msg, file_path)
                # Model nomi multimodal bo'lsa — audio faylni to'g'ridan-to'g'ri yuboramiz
                model_name = self.config.GPT_MODEL.lower()
                if any(x in model_name for x in ["audio", "tts", "gpt-4o"]):
                    from handlers.openai_audio_helper import gpt4o_audio_chat
                    chat_name, chat_type = await self._get_chat_info(event)
                    system_prompt = self.ai.config.OWNER_NAME + ": " + get_system_prompt(chat_name, chat_type)
                    history = self.ctx.get_history(chat_id)
                    user_text = await gpt4o_audio_chat(
                        api_key=self.config.OPENAI_API_KEY,
                        model='gpt-realtime-whisper',
                        audio_path=file_path,
                        system_prompt=system_prompt,
                        history=history,
                        max_tokens=self.config.GPT_MAX_TOKENS,
                    )
                    if not user_text:
                        logger.warning(f"Chat {chat_id}: GPT-4o audio input javob bermadi")
                        return
                    logger.info(f"Chat {chat_id}: GPT-4o audio javobi: {user_text}")
                else:
                    # Standart: Whisper orqali matnga o‘girish
                    from utils.speech_to_text import speech_to_text
                    user_text = await speech_to_text(file_path, self.config.OPENAI_API_KEY)
                    if not user_text:
                        logger.warning(f"Chat {chat_id}: Ovozli xabarni matnga o‘girishda xato")
                        return
                    logger.info(f"Chat {chat_id}: Ovozli xabar matni: {user_text}")
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            else:
                user_text = self._extract_text(event)
                if user_text is None:
                    return

            # Chat kontekstini aniqlash
            chat_name, chat_type = await self._get_chat_info(event)

            # Reply kontekstini qo'shish (agar reply bo'lsa)
            reply_ctx = await self._get_reply_context(event)

            # Yuboruvchi haqida ma'lumot
            sender_ctx = await self._get_sender_info(event)

            # Kontekstga saqlash
            full_user_msg = " ".join(filter(None, [sender_ctx, reply_ctx, user_text]))
            self.ctx.add_message(chat_id, "user", full_user_msg)

            # Typing animatsiyasi + haqiqiy kutish (human-like)
            typing_time = random.uniform(
                self.config.RESPONSE_DELAY_MIN,
                self.config.RESPONSE_DELAY_MAX,
            )
            async with self.client.action(event.chat_id, "typing"):
                history = self.ctx.get_history(chat_id)
                response = await self.ai.get_response(
                    history=history,
                    chat_name=chat_name,
                    chat_type=chat_type,
                )
                # Qolgan vaqtni to'ldiramiz (typing realroq ko'rinsin)
                elapsed = 0.0
                await asyncio.sleep(max(0.0, typing_time - elapsed))

            if not response:
                logger.warning(f"Chat {chat_id}: AI bo'sh javob qaytardi")
                return

            # Xabar yuborish — agar user voice jo'natgan bo'lsa, voice bilan javob ber
            if is_voice and self.config.ELEVENLABS_API_KEY:
                from utils.text_to_speech import text_to_speech
                import os
                tts_path = await text_to_speech(
                    text=response,
                    api_key=self.config.ELEVENLABS_API_KEY,
                    voice_id=self.config.ELEVENLABS_VOICE_ID,
                    model_id=self.config.ELEVENLABS_MODEL_ID,
                    auto_enhance=self.config.ELEVENLABS_AUTO_ENHANCE,
                    openai_api_key=self.config.OPENAI_API_KEY,
                )
                if tts_path and os.path.exists(tts_path):
                    try:
                        await self.client.send_file(
                            event.chat_id,
                            tts_path,
                            voice_note=True,
                            reply_to=event.message.id,
                        )
                    except Exception as exc:
                        logger.warning(f"Voice javob yuborishda xato: {exc}, matn sifatida yuboriladi")
                        await event.reply(response)
                    finally:
                        try:
                            os.remove(tts_path)
                        except OSError:
                            pass
                else:
                    # TTS ishlamasa matn sifatida yuborish
                    await event.reply(response)
            else:
                # Media tokenlarni qayta ishlash (GIF, stiker, rasm)
                clean_text, media_sent = await self.enhancer.process_response(
                    chat_id=event.chat_id,
                    response=response,
                    reply_to=event.message.id,
                )

                # Agar matn ham bor bo'lsa — yuborish
                if clean_text:
                    await event.reply(clean_text)
                elif not media_sent:
                    # Media ham, matn ham yo'q — original javobni yuborish
                    await event.reply(response)

            # Holat yangilash
            self.rl.mark_responded(chat_id)
            self.ctx.add_message(chat_id, "assistant", response)
            logger.info(f"[{chat_type}] {chat_name or chat_id} → {response[:60]}…")

        except FloodWaitError as exc:
            logger.warning(f"FloodWait: {exc.seconds}s kutilmoqda")
            await asyncio.sleep(exc.seconds)

        except SlowModeWaitError as exc:
            logger.warning(f"SlowMode: {exc.seconds}s kutilmoqda")
            await asyncio.sleep(exc.seconds)

        except (UserIsBlockedError, ChatWriteForbiddenError):
            logger.warning(f"Yozish taqiqlangan: chat {event.chat_id}")

        except MsgIdInvalidError:
            # Reply bekor bo'lib qolgan — oddiy xabar sifatida yuborish
            try:
                if response:  # type: ignore[possibly-undefined]
                    await self.client.send_message(event.chat_id, response)
            except Exception:
                pass

        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Kutilmagan xato (chat {event.chat_id}): {exc}")

    # ── Decision logic ────────────────────────────────────────────

    async def _should_respond(self, event: events.NewMessage.Event) -> bool:
        """True qaytarsa — javob beriladi."""

        # O'z xabarlarimiz
        if event.out:
            return False

        # Xabar yo'q
        if not event.message:
            return False

        # Botlar
        sender = await event.get_sender()
        if isinstance(sender, User) and sender.bot:
            return False

        # Foydalanuvchi o'chib ketgan (deleted account)
        if isinstance(sender, User) and sender.deleted:
            return False

        # ── Private chat ─────────────────────────────────────────
        if event.is_private:
            return self.config.RESPOND_IN_PRIVATE


        # ── Guruh / Kanal kommentlari ────────────────────────────
        if event.is_group or event.is_channel:
            if not (self.config.RESPOND_IN_GROUPS or self.config.RESPOND_IN_CHANNELS):
                return False

            # @mention
            if event.message.mentioned:
                return True

            # Faqat bizning xabarimizga reply bo'lsa javob berish
            if event.message.reply_to:
                try:
                    replied = await event.message.get_reply_message()
                    if replied and replied.sender_id == self._me_id:
                        return True
                except Exception:
                    pass
                return False

            return False

        return False

    # ── Text extraction ───────────────────────────────────────────

    def _extract_text(self, event: events.NewMessage.Event) -> Optional[str]:
        """
        Xabardan matn chiqaradi.
        Stiker, rasm, media — maxsus belgilar bilan ifodalanadi.
        """
        msg = event.message

        # Matn xabar
        if msg.text:
            return msg.text

        # Stiker
        if self._is_sticker(msg):
            sticker_emoji = self._get_sticker_emoji(msg)
            return f"[STICKER {sticker_emoji}]" if sticker_emoji else "[STICKER]"

        # Rasm
        if isinstance(msg.media, MessageMediaPhoto):
            caption = msg.message or ""
            return f"[RASM yubordi{': ' + caption if caption else ''}]"

        # Boshqa media (fayl, video, ovoz)
        if msg.media:
            return "[MEDIA FAYL yubordi]"

        return None

    # ── Sticker helpers ───────────────────────────────────────────

    @staticmethod
    def _is_sticker(message) -> bool:
        if not isinstance(message.media, MessageMediaDocument):
            return False
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return True
        return False

    @staticmethod
    def _get_sticker_emoji(message) -> str:
        if not isinstance(message.media, MessageMediaDocument):
            return ""
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return attr.alt or ""
        return ""

    # ── Context helpers ───────────────────────────────────────────

    async def _get_chat_info(self, event: events.NewMessage.Event):
        """(chat_name, chat_type) qaytaradi."""
        try:
            chat = await event.get_chat()
            name = getattr(chat, "title", "") or getattr(chat, "first_name", "") or ""
        except Exception:
            name = ""

        if event.is_private:
            chat_type = "private"
        elif event.is_channel:
            chat_type = "channel"
        else:
            chat_type = "group"

        return name, chat_type

    async def _get_sender_info(self, event: events.NewMessage.Event) -> str:
        """[Kimdan: Ism @username] formatida qaytaradi."""
        try:
            sender = await event.get_sender()
            if not sender:
                return ""
            first = getattr(sender, "first_name", "") or ""
            uname = getattr(sender, "username", "") or ""
            parts = [p for p in [first, f"@{uname}" if uname else ""] if p]
            return f"[{' '.join(parts)} yozdi]" if parts else ""
        except Exception:
            return ""

    async def _get_reply_context(self, event: events.NewMessage.Event) -> str:
        """Agar reply bo'lsa, qaysi xabarga reply qilinganini qaytaradi."""
        if not event.message.reply_to:
            return ""
        try:
            replied = await event.message.get_reply_message()
            if replied and replied.text:
                preview = replied.text[:120].replace("\n", " ")
                return f'["{preview}" xabariga javob]'
        except Exception:
            pass
        return ""

    async def _safe_get_reply(self, event: events.NewMessage.Event):
        """Xavfsiz reply xabarni oladi (xato bo'lsa None qaytaradi)."""
        try:
            return await event.message.get_reply_message()
        except Exception:
            return None
