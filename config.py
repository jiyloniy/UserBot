"""
VodiySoft UserBot — Konfiguratsiya moduli
Barcha sozlamalar .env faylidan o'qiladi
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool = True) -> bool:
    return os.getenv(key, str(default)).lower().strip() in ("true", "1", "yes")


@dataclass
class Config:
    # ── Telegram MTProto ──────────────────────────────────────────
    API_ID: int = field(default_factory=lambda: _env_int("API_ID", 0))
    API_HASH: str = field(default_factory=lambda: _env_str("API_HASH"))
    PHONE_NUMBER: str = field(default_factory=lambda: _env_str("PHONE_NUMBER"))
    SESSION_NAME: str = "vodiysoftbot_session"

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = field(default_factory=lambda: _env_str("OPENAI_API_KEY"))
    GPT_MODEL: str = field(default_factory=lambda: _env_str("GPT_MODEL", "gpt-4o"))
    GPT_MAX_TOKENS: int = field(default_factory=lambda: _env_int("GPT_MAX_TOKENS", 500))

    # ── ElevenLabs TTS ───────────────────────────────────────────
    ELEVENLABS_API_KEY: str = field(default_factory=lambda: _env_str("ELEVENLABS_API_KEY"))
    ELEVENLABS_VOICE_ID: str = field(default_factory=lambda: _env_str("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"))
    ELEVENLABS_MODEL_ID: str = field(default_factory=lambda: _env_str("ELEVENLABS_MODEL_ID", "eleven_v3"))
    ELEVENLABS_AUTO_ENHANCE: bool = field(default_factory=lambda: _env_bool("ELEVENLABS_AUTO_ENHANCE", True))

    # ── Shaxsiy ma'lumotlar ───────────────────────────────────────
    OWNER_NAME: str = "Erkinjon Olimov"
    OWNER_CONTACT: str = "+998888150424"
    COMPANY_NAME: str = "VodiySoft"
    COMPANY_ROLE: str = "Sotuv Bo'limi Boshlig'i"

    # ── Bot xulq-atvori ───────────────────────────────────────────
    MAX_HISTORY: int = field(default_factory=lambda: _env_int("MAX_HISTORY", 25))
    RESPONSE_DELAY_MIN: float = field(default_factory=lambda: _env_float("RESPONSE_DELAY_MIN", 2.0))
    RESPONSE_DELAY_MAX: float = field(default_factory=lambda: _env_float("RESPONSE_DELAY_MAX", 5.5))
    RATE_LIMIT_SECONDS: int = field(default_factory=lambda: _env_int("RATE_LIMIT_SECONDS", 25))
    MAX_RESPONSES_PER_MINUTE: int = field(default_factory=lambda: _env_int("MAX_RESPONSES_PER_MINUTE", 15))

    # ── Javob berish joylari ──────────────────────────────────────
    RESPOND_IN_PRIVATE: bool = field(default_factory=lambda: _env_bool("RESPOND_IN_PRIVATE", True))
    RESPOND_IN_GROUPS: bool = field(default_factory=lambda: _env_bool("RESPOND_IN_GROUPS", True))
    RESPOND_IN_CHANNELS: bool = field(default_factory=lambda: _env_bool("RESPOND_IN_CHANNELS", True))

    def validate(self) -> None:
        """Barcha majburiy qiymatlarni tekshiradi. Xato bo'lsa ValueError ko'taradi."""
        errors: list[str] = []

        if not self.API_ID:
            errors.append("API_ID topilmadi — https://my.telegram.org/auth")
        if not self.API_HASH:
            errors.append("API_HASH topilmadi — https://my.telegram.org/auth")
        if not self.PHONE_NUMBER:
            errors.append("PHONE_NUMBER topilmadi (masalan: +998901234567)")
        if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.startswith("sk-proj-..."):
            errors.append("OPENAI_API_KEY topilmadi — https://platform.openai.com/api-keys")

        if errors:
            msg = "\n  ❌ ".join(errors)
            raise ValueError(f"\n  ❌ {msg}")
