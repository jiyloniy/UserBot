"""
ContextManager — har bir chat uchun suhbat tarixini saqlaydi.

Xususiyatlari:
• Har bir chat_id uchun alohida deque (navbat)
• TTL (time-to-live) — uzoq jim turgan chatning tarixin tozalaydi
• Thread-safe emas (asyncio single-thread muhitda ishlatiladi)
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Dict, Deque, List


class ContextManager:
    def __init__(
        self,
        max_history: int = 25,
        context_ttl_seconds: int = 3_600,   # 1 soat
    ) -> None:
        self._max_history = max_history
        self._ttl = context_ttl_seconds

        # chat_id → deque of {"role": ..., "content": ...}
        self._histories: Dict[int, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=self._max_history)
        )
        # chat_id → oxirgi faollik vaqti
        self._last_activity: Dict[int, float] = {}

    # ── public interface ─────────────────────────────────────────

    def add_message(self, chat_id: int, role: str, content: str) -> None:
        """
        Xabarni tarixga qo'shadi.
        role: 'user' | 'assistant'
        """
        self._expire_if_stale(chat_id)
        self._histories[chat_id].append({"role": role, "content": content})
        self._last_activity[chat_id] = time.monotonic()

    def get_history(self, chat_id: int) -> List[dict]:
        """OpenAI messages formatida tarixni qaytaradi."""
        return list(self._histories[chat_id])

    def clear(self, chat_id: int) -> None:
        """Bitta chatning tarixini o'chiradi."""
        self._histories.pop(chat_id, None)
        self._last_activity.pop(chat_id, None)

    def clear_all(self) -> None:
        """Barcha tarixni tozalaydi."""
        self._histories.clear()
        self._last_activity.clear()

    def message_count(self, chat_id: int) -> int:
        return len(self._histories[chat_id])

    # ── internal ─────────────────────────────────────────────────

    def _expire_if_stale(self, chat_id: int) -> None:
        """Agar chat uzoq vaqt jim turgan bo'lsa, kontekstini reset qiladi."""
        last = self._last_activity.get(chat_id)
        if last is not None and (time.monotonic() - last) > self._ttl:
            self._histories[chat_id].clear()
