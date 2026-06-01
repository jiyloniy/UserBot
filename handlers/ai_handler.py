"""
AIHandler — OpenAI GPT bilan ishlash moduli.

Xususiyatlari:
• Async API chaqiruvlari
• Eksponensial qayta urinish (RateLimitError, ConnectionError)
• Har bir so'rovda frash system prompt
• presence_penalty + frequency_penalty → takrorlanishni kamaytiradi
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List

from openai import AsyncOpenAI
from openai import (
    RateLimitError,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
)

from prompts.system_prompt import get_system_prompt

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("vodiysoftbot.ai")


class AIHandler:
    def __init__(self, config: "Config") -> None:
        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=30.0,
            max_retries=0,   # biz o'zimiz retry qilamiz
        )
    def _build_kwargs(self, messages: list) -> dict:
        # Faqat universal parametrlar — temperature/penalty yangi modellarda ishlamaydi
        return dict(
            model=self.config.GPT_MODEL,
            messages=messages,
            max_completion_tokens=self.config.GPT_MAX_TOKENS,
        )

    async def get_response(
        self,
        history: List[dict],
        chat_name: str = "",
        chat_type: str = "private",
        max_retries: int = 3,
    ) -> str:
        """
        GPT'dan javob oladi.
        Qaytadi: javob matni (bo'sh string = xato yoki bo'sh javob)
        """
        system_prompt = get_system_prompt(chat_name, chat_type)
        messages = [{"role": "system", "content": system_prompt}, *history]

        for attempt in range(1, max_retries + 1):
            try:
                kwargs = self._build_kwargs(messages)
                completion = await self._client.chat.completions.create(**kwargs)
                text = completion.choices[0].message.content or ""
                return text.strip()

            except RateLimitError:
                wait = attempt * 25
                logger.warning(f"OpenAI rate limit — {wait}s kutilmoqda (urinish {attempt}/{max_retries})")
                await asyncio.sleep(wait)

            except (APIConnectionError, APITimeoutError):
                wait = attempt * 6
                logger.warning(f"Ulanish xatosi — {wait}s kutilmoqda (urinish {attempt}/{max_retries})")
                await asyncio.sleep(wait)

            except APIStatusError as exc:
                detail = exc.message or str(exc)
                logger.error(f"OpenAI API xatosi [{exc.status_code}]: {detail}")
                # 4xx — boshqa mijoz xatolari, qayta urinish bekor
                if 400 <= exc.status_code < 500:
                    return ""
                if attempt == max_retries:
                    return ""
                await asyncio.sleep(5)

            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Kutilmagan AI xatosi: {exc}")
                return ""

        logger.error("Barcha urinishlar muvaffaqiyatsiz tugadi.")
        return ""
