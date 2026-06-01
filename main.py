"""
VodiySoft UserBot — Asosiy ishga tushirish fayli
Erkinjon Olimov | Sotuv Bo'limi Boshlig'i | VodiySoft Company

Ishga tushirish:
    python main.py

Birinchi marta ishga tushirganda telefon raqami va SMS kod so'raladi.
Sessiya saqlangandan so'ng keyingi ishga tushirishlarda so'ralmaydi.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, cast

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import Config
from handlers.ai_handler import AIHandler
from handlers.message_handler import MessageHandler
from handlers.session_handler import SessionHandler
from handlers.tts_handler import TTSHandler
from utils.context_manager import ContextManager
from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter


def _build_session(config: Config, logger: logging.Logger):
    """SQLite lock muammosidan qochish uchun StringSession ishlatadi."""
    session_file = Path(f"{config.SESSION_NAME}.session.txt")

    if session_file.exists():
        session_string = session_file.read_text(encoding="utf-8").strip()
        if session_string:
            return StringSession(session_string), session_file, False

    logger.info("Session backend: StringSession")
    return StringSession(), session_file, True


async def main() -> None:
    logger = setup_logger()

    # ── Konfiguratsiya ───────────────────────────────────────────
    config = Config()
    try:
        config.validate()
    except ValueError as exc:
        logger.critical(f"Konfiguratsiya xatosi:{exc}")
        logger.critical("💡 .env.example faylini .env ga nusxa ko'chiring va to'ldiring.")
        sys.exit(1)

    # ── Banner ───────────────────────────────────────────────────
    logger.info("=" * 58)
    logger.info("  🤖  VodiySoft UserBot  —  AI Yordamchi")
    logger.info(f"  👤  {config.OWNER_NAME}")
    logger.info(f"  🏢  {config.COMPANY_NAME}  |  {config.COMPANY_ROLE}")
    logger.info(f"  📞  {config.OWNER_CONTACT}")
    logger.info(f"  🧠  Model: {config.GPT_MODEL}")
    logger.info(f"  ⏱️   Javob kechikishi: {config.RESPONSE_DELAY_MIN}–{config.RESPONSE_DELAY_MAX}s")
    logger.info(f"  🛡️   Rate limit: har {config.RATE_LIMIT_SECONDS}s, max {config.MAX_RESPONSES_PER_MINUTE}/min")
    logger.info("=" * 58)

    # ── Komponentlar ─────────────────────────────────────────────
    ai_handler = AIHandler(config)
    context_manager = ContextManager(max_history=config.MAX_HISTORY)
    rate_limiter = RateLimiter(
        min_delay=config.RATE_LIMIT_SECONDS,
        max_per_minute=config.MAX_RESPONSES_PER_MINUTE,
    )

    session_backend, session_file, should_migrate = _build_session(config, logger)

    # ── Telegram client — haqiqiy mobil qurilmadek ko'rinadi ─────
    client = TelegramClient(
        session=session_backend,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        device_model="Samsung Galaxy S24 Ultra",
        system_version="Android 14",
        app_version="10.14.5",
        lang_code="uz",
        system_lang_code="uz-UZ",
    )

    msg_handler = MessageHandler(
        client=client,
        config=config,
        ai_handler=ai_handler,
        context_manager=context_manager,
        rate_limiter=rate_limiter,
    )

    # ── Ishga tushirish ──────────────────────────────────────────
    async with client:
        await cast(Awaitable[Any], client.start(phone=lambda: config.PHONE_NUMBER))

        if should_migrate:
            session = client.session
            exported = StringSession.save(cast(StringSession, session)) if session else ""
            if exported:
                session_file.write_text(exported, encoding="utf-8")
                logger.info(f"StringSession saqlandi: {session_file.name}")

        await msg_handler.initialize()

        # TTS handler — .tts buyrug'i uchun
        tts_handler = TTSHandler(client=client, config=config)
        tts_handler.register()

        # Session handler — .sessions va .cleansessions buyruqlari uchun
        session_handler = SessionHandler(client=client, config=config)
        session_handler.register()

        # Kiruvchi barcha yangi xabarlarni ushlaydi
        @client.on(events.NewMessage(incoming=True))
        async def on_new_message(event: events.NewMessage.Event) -> None:
            await msg_handler.handle(event)

        logger.info("✅  UserBot ishga tushdi! Xabarlar kutilmoqda…")
        logger.info("🛑  To'xtatish uchun:  Ctrl + C\n")

        await cast(Awaitable[Any], client.run_until_disconnected())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋  UserBot to'xtatildi. Xayr!\n")
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("vodiysoftbot").critical(
            f"💥  Kritik xato: {exc}", exc_info=True
        )
        sys.exit(1)
