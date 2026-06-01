"""
TTS Auto-Enhance — matnni ElevenLabs speech taglar bilan boyitadi.

ElevenLabs qo'llab-quvvatlaydigan taglar:
  [laughs], [chuckles], [sighs], [gasps], [clears throat],
  [speaking slowly], [speaking quickly], [thoughtful], [excited],
  [whispers], [sad], [serious], [angry], [surprised]

Bu modul GPT orqali matnni tahlil qilib, mos joylarga
tabiiy speech taglarni qo'shadi — natijada ovoz yanada
hayotiy va emotsional chiqadi.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger("vodiysoftbot.tts_enhancer")

# ElevenLabs tomonidan qo'llab-quvvatlanadigan speech taglar
ELEVENLABS_TAGS = [
    "[laughs]", "[chuckles]", "[sighs]", "[gasps]",
    "[clears throat]", "[speaking slowly]", "[speaking quickly]",
    "[thoughtful]", "[excited]", "[whispers]", "[sad]",
    "[serious]", "[angry]", "[surprised]",
]

ENHANCE_SYSTEM_PROMPT = """Sen matnni ElevenLabs TTS uchun boyituvchi yordamchisan.

Vazifang: berilgan matnni tabiiy va emotsional qilib ElevenLabs speech taglar bilan boyitish.

Qo'llash mumkin bo'lgan taglar:
[laughs], [chuckles], [sighs], [gasps], [clears throat],
[speaking slowly], [speaking quickly], [thoughtful], [excited],
[whispers], [sad], [serious], [angry], [surprised]

QOIDALAR:
1. Matn ma'nosini O'ZGARTIRMA — faqat taglar qo'sh
2. Taglarni tabiiy joylarga qo'y (gap boshida, vergul/nuqta oldidan)
3. Haddan ziyod tag qo'yma — har 1-2 gapda 1 ta yetarli
4. Kontekstga mos tag tanlash — xursand gap = [excited]/[chuckles], o'ylanish = [thoughtful]
5. Qisqa matnlarga (5 so'zdan kam) tag qo'yma
6. FAQAT boyitilgan matnni qaytar — hech qanday izoh yoki tushuntirish qo'shma

Misol:
Kirish: "Jigarim, bu loyihada qiziq narsa bor. Toshkentdagi kompaniya bilan ishladik, natija zo'r bo'ldi."
Chiqish: "[thoughtful] Jigarim, bu loyihada qiziq narsa bor. [excited] Toshkentdagi kompaniya bilan ishladik, natija zo'r bo'ldi."

Kirish: "Ha, tushundim. Keling ertaga gaplashamiz."
Chiqish: "Ha, tushundim. [speaking slowly] Keling ertaga gaplashamiz."
"""


async def enhance_text_for_tts(
    text: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Matnni ElevenLabs speech taglar bilan boyitadi.

    Agar GPT chaqiruvda xato bo'lsa — original matnni qaytaradi.

    Args:
        text: Boyitiladigan matn
        api_key: OpenAI API kaliti
        model: GPT model nomi (default: gpt-4o-mini — tez va arzon)

    Returns:
        Speech taglar bilan boyitilgan matn
    """
    # Juda qisqa matnlarni boyitishga hojat yo'q
    if not text or len(text.split()) < 5:
        return text

    # Agar matnda allaqachon taglar bo'lsa — qayta boyitmaslik
    if any(tag in text for tag in ELEVENLABS_TAGS):
        return text

    try:
        client = AsyncOpenAI(api_key=api_key, timeout=15.0)
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ENHANCE_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_completion_tokens=len(text) + 200,
            temperature=0.7,
        )
        enhanced = completion.choices[0].message.content or ""
        enhanced = enhanced.strip()

        # Xavfsizlik tekshiruvi — agar GPT matnni buzgan bo'lsa, originalni qaytar
        if not enhanced or len(enhanced) < len(text) * 0.5:
            logger.warning("TTS enhance: GPT matnni qisqartirdi, original ishlatiladi")
            return text

        # Faqat ruxsat etilgan taglar borligini tekshirish
        enhanced = _sanitize_tags(enhanced)

        logger.info(f"TTS enhance: {len(text)} → {len(enhanced)} belgi")
        return enhanced

    except Exception as exc:
        logger.warning(f"TTS enhance xatosi: {exc} — original matn ishlatiladi")
        return text


def _sanitize_tags(text: str) -> str:
    """
    Faqat ruxsat etilgan ElevenLabs taglarni qoldiradi,
    noto'g'ri taglarni olib tashlaydi.
    """
    # Barcha [...] formatdagi taglarni topish
    all_tags = re.findall(r"\[[^\]]+\]", text)

    for tag in all_tags:
        if tag.lower() not in [t.lower() for t in ELEVENLABS_TAGS]:
            text = text.replace(tag, "")

    # Ortiqcha bo'sh joylarni tozalash
    text = re.sub(r"  +", " ", text).strip()
    return text
