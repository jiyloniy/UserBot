"""
RateLimiter — spam va ban'dan himoya qiladi.

Ikki qatlam:
  1. Per-chat cooldown  — bir chatda xabarlar orasida minimal pauza
  2. Global minuteli limit — bir daqiqada jami yuborish chegarasi
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict


class RateLimiter:
    def __init__(self, min_delay: float = 25.0, max_per_minute: int = 15) -> None:
        self._min_delay = min_delay
        self._max_per_minute = max_per_minute

        # chat_id → UNIX timestamp (oxirgi javob vaqti)
        self._last_response: Dict[int, float] = defaultdict(float)

        # global counter
        self._minute_count: int = 0
        self._minute_start: float = time.monotonic()

    # ── public interface ─────────────────────────────────────────

    def can_respond(self, chat_id: int) -> bool:
        """Javob berish mumkinligini tekshiradi (True = bersa bo'ladi)."""
        self._reset_minute_counter_if_needed()

        if self._minute_count >= self._max_per_minute:
            return False

        elapsed = time.monotonic() - self._last_response[chat_id]
        return elapsed >= self._min_delay

    def mark_responded(self, chat_id: int) -> None:
        """Javob yuborilganini qayd etadi."""
        self._last_response[chat_id] = time.monotonic()
        self._minute_count += 1

    def seconds_until_ready(self, chat_id: int) -> float:
        """Keyingi javobgacha qancha sekund qolganini qaytaradi."""
        elapsed = time.monotonic() - self._last_response[chat_id]
        return max(0.0, self._min_delay - elapsed)

    # ── internal ─────────────────────────────────────────────────

    def _reset_minute_counter_if_needed(self) -> None:
        if time.monotonic() - self._minute_start >= 60:
            self._minute_count = 0
            self._minute_start = time.monotonic()
