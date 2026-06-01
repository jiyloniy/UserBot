"""
ChatEnhancer — Chattingni kuchayitirish uchun media yuborish moduli.

Haqiqiy oda sifatida suhbat olib borish uchun:
  • GIF yuborish (@gif inline bot orqali)
  • Stiker yuborish (saqlangan stikerlardan)
  • Rasm yuborish (inline bot orqali)

AI javobida maxsus tokenlar bo'lsa, ularni parse qilib media yuboradi:
  [GIF:kalit_soz]   — GIF qidiradi va yuboradi
  [STICKER:emoji]   — emoji ga mos stiker yuboradi
  [PHOTO:kalit_soz] — rasm qidiradi va yuboradi
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import TYPE_CHECKING, Optional, Tuple

from telethon import TelegramClient
from telethon.tl.functions.messages import GetStickerSetRequest, GetAllStickersRequest
from telethon.tl.types import InputStickerSetShortName

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("vodiysoftbot.enhancer")

# Media token pattern: [GIF:keyword], [STICKER:emoji], [PHOTO:keyword]
MEDIA_TOKEN_PATTERN = re.compile(
    r"\[(GIF|STICKER|PHOTO):([^\]]+)\]", re.IGNORECASE
)


class ChatEnhancer:
    """Chatga media (GIF, stiker, rasm) yuborish bilan boyitadi."""

    def __init__(self, client: TelegramClient, config: "Config") -> None:
        self.client = client
        self.config = config
        self._sticker_cache: dict[str, list] = {}  # emoji -> stickers

    # ── Asosiy metod ──────────────────────────────────────────────

    async def process_response(
        self, chat_id: int, response: str, reply_to: Optional[int] = None
    ) -> Tuple[str, bool]:
        """
        AI javobidan media tokenlarni ajratadi va media yuboradi.

        Returns:
            (tozalangan_matn, media_yuborildi_mi)
        """
        tokens = MEDIA_TOKEN_PATTERN.findall(response)
        clean_text = MEDIA_TOKEN_PATTERN.sub("", response).strip()
        media_sent = False

        for media_type, keyword in tokens:
            media_type = media_type.upper()
            keyword = keyword.strip()

            try:
                if media_type == "GIF":
                    sent = await self._send_gif(chat_id, keyword, reply_to)
                elif media_type == "STICKER":
                    sent = await self._send_sticker(chat_id, keyword, reply_to)
                elif media_type == "PHOTO":
                    sent = await self._send_photo(chat_id, keyword, reply_to)
                else:
                    sent = False

                if sent:
                    media_sent = True
                    logger.info(f"Media yuborildi: {media_type}:{keyword} -> chat {chat_id}")
            except Exception as exc:
                logger.warning(f"Media yuborishda xato ({media_type}:{keyword}): {exc}")

        return clean_text, media_sent

    # ── GIF yuborish ──────────────────────────────────────────────

    async def _send_gif(self, chat_id: int, keyword: str, reply_to: Optional[int] = None) -> bool:
        """@gif inline bot orqali GIF qidiradi va yuboradi."""
        try:
            results = await self.client.inline_query("gif", keyword)
            if not results:
                logger.debug(f"GIF topilmadi: {keyword}")
                return False

            # Tasodifiy tanlash (birinchi 10 tadan)
            top_results = results[:10]
            chosen = random.choice(top_results)

            await chosen.click(chat_id, reply_to=reply_to)
            return True
        except Exception as exc:
            logger.warning(f"GIF yuborishda xato: {exc}")
            return False

    # ── Stiker yuborish ───────────────────────────────────────────

    async def _send_sticker(self, chat_id: int, emoji: str, reply_to: Optional[int] = None) -> bool:
        """Emoji ga mos stiker topib yuboradi."""
        try:
            # Avval keshdan qidirish
            if emoji in self._sticker_cache and self._sticker_cache[emoji]:
                sticker = random.choice(self._sticker_cache[emoji])
                await self.client.send_file(chat_id, sticker, reply_to=reply_to)
                return True

            # Barcha stiker to'plamlarini olish
            all_stickers = await self.client(GetAllStickersRequest(hash=0))
            if not all_stickers or not all_stickers.sets:
                return False

            # Tasodifiy stiker to'plamdan emoji ga mos stiker qidirish
            matching_stickers = []
            # Faqat birinchi 5 ta set ni tekshirish (tezlik uchun)
            random_sets = random.sample(
                all_stickers.sets, min(5, len(all_stickers.sets))
            )

            for sticker_set in random_sets:
                try:
                    full_set = await self.client(
                        GetStickerSetRequest(
                            stickerset=InputStickerSetShortName(
                                short_name=sticker_set.short_name
                            ),
                            hash=0,
                        )
                    )
                    doc_map = {doc.id: doc for doc in full_set.documents}
                    for pack in full_set.packs:
                        if emoji in (pack.emoticon or ""):
                            for doc_id in pack.documents[:3]:
                                if doc_id in doc_map:
                                    matching_stickers.append(doc_map[doc_id])
                except Exception:
                    continue

            if matching_stickers:
                self._sticker_cache[emoji] = matching_stickers
                sticker = random.choice(matching_stickers)
                await self.client.send_file(chat_id, sticker, reply_to=reply_to)
                return True

            # Agar emoji ga mos stiker topilmasa — tasodifiy stiker
            return await self._send_random_sticker(chat_id, all_stickers.sets, reply_to)

        except Exception as exc:
            logger.warning(f"Stiker yuborishda xato: {exc}")
            return False

    async def _send_random_sticker(self, chat_id: int, sets, reply_to: Optional[int] = None) -> bool:
        """Tasodifiy stiker yuboradi."""
        try:
            if not sets:
                return False
            random_set = random.choice(sets)
            full_set = await self.client(
                GetStickerSetRequest(
                    stickerset=InputStickerSetShortName(
                        short_name=random_set.short_name
                    ),
                    hash=0,
                )
            )
            if full_set.documents:
                sticker = random.choice(full_set.documents)
                await self.client.send_file(chat_id, sticker, reply_to=reply_to)
                return True
        except Exception as exc:
            logger.warning(f"Tasodifiy stiker yuborishda xato: {exc}")
        return False

    # ── Rasm yuborish ─────────────────────────────────────────────

    async def _send_photo(self, chat_id: int, keyword: str, reply_to: Optional[int] = None) -> bool:
        """Inline bot orqali rasm qidiradi va yuboradi."""
        try:
            # @pic bot orqali rasm qidirish
            results = await self.client.inline_query("pic", keyword)
            if not results:
                # Muqobil — @bing orqali
                results = await self.client.inline_query("bing", keyword)
            if not results:
                logger.debug(f"Rasm topilmadi: {keyword}")
                return False

            top_results = results[:8]
            chosen = random.choice(top_results)
            await chosen.click(chat_id, reply_to=reply_to)
            return True
        except Exception as exc:
            logger.warning(f"Rasm yuborishda xato: {exc}")
            return False
