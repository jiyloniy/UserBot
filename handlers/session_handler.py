"""
SessionHandler — Telegram sessiyalarini boshqarish buyruqlari.

Foydalanish (Telegram chatda):
    .sessions         → Barcha faol sessiyalar ro'yxatini ko'rsatadi
    .cleansessions    → Joriy sessiyadan tashqari barcha sessiyalarni tugatadi

Natija: Boshqa qurilmalardagi sessiyalar o'chiriladi.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telethon import TelegramClient, events
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("vodiysoftbot.session_handler")


class SessionHandler:
    """Telegram chatda sessiyalarni boshqarish buyruqlarini qayta ishlaydi."""

    def __init__(self, client: TelegramClient, config: "Config") -> None:
        self.client = client
        self.config = config

    def register(self) -> None:
        """Event handlerlarni ro'yxatga oladi."""

        @self.client.on(events.NewMessage(outgoing=True, pattern=r"\.sessions$"))
        async def on_sessions_command(event: events.NewMessage.Event) -> None:
            await self._handle_list_sessions(event)

        @self.client.on(events.NewMessage(outgoing=True, pattern=r"\.cleansessions$"))
        async def on_clean_sessions_command(event: events.NewMessage.Event) -> None:
            await self._handle_clean_sessions(event)

    async def _handle_list_sessions(self, event: events.NewMessage.Event) -> None:
        """Barcha faol sessiyalar ro'yxatini ko'rsatadi."""
        await event.edit("🔍 Sessiyalar tekshirilmoqda...")

        try:
            result = await self.client(GetAuthorizationsRequest())
            authorizations = result.authorizations

            if not authorizations:
                await event.edit("📱 Hech qanday faol sessiya topilmadi.")
                return

            lines = [f"📱 **Faol sessiyalar: {len(authorizations)} ta**\n"]

            for i, auth in enumerate(authorizations, 1):
                current = " ✅ (joriy)" if auth.current else ""
                device = auth.device_model or "Noma'lum qurilma"
                platform = auth.platform or ""
                app = auth.app_name or ""
                country = auth.country or ""

                lines.append(
                    f"**{i}.** {device} {platform}{current}\n"
                    f"    📲 {app} | 🌍 {country}\n"
                )

            await event.edit("\n".join(lines))

        except Exception as exc:
            logger.exception(f"Sessiyalarni olishda xato: {exc}")
            await event.edit(f"❌ Sessiyalarni olishda xato: {exc}")

    async def _handle_clean_sessions(self, event: events.NewMessage.Event) -> None:
        """Joriy sessiyadan tashqari barcha sessiyalarni tugatadi."""
        await event.edit("🧹 Sessiyalar tozalanmoqda...")

        try:
            result = await self.client(GetAuthorizationsRequest())
            authorizations = result.authorizations

            # Joriy sessiyadan tashqari boshqalarni topish
            other_sessions = [auth for auth in authorizations if not auth.current]

            if not other_sessions:
                await event.edit("✅ Boshqa faol sessiya yo'q. Faqat joriy sessiya mavjud.")
                return

            terminated = 0
            failed = 0

            for auth in other_sessions:
                try:
                    await self.client(ResetAuthorizationRequest(hash=auth.hash))
                    terminated += 1
                except Exception as exc:
                    logger.warning(f"Sessiyani tugatishda xato (hash={auth.hash}): {exc}")
                    failed += 1

            # Natija xabarini tayyorlash
            msg_parts = [f"🧹 **Sessiyalar tozalandi!**\n"]
            msg_parts.append(f"✅ Tugatildi: **{terminated}** ta sessiya")

            if failed:
                msg_parts.append(f"⚠️ Xato: **{failed}** ta sessiya tugatilmadi")

            msg_parts.append(f"\n📱 Faqat joriy sessiya qoldi.")

            await event.edit("\n".join(msg_parts))

        except Exception as exc:
            logger.exception(f"Sessiyalarni tozalashda xato: {exc}")
            await event.edit(f"❌ Sessiyalarni tozalashda xato: {exc}")
