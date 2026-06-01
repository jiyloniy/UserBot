"""
TTS Auto-Enhance — matnni ElevenLabs v3 model uchun boyitadi.

ElevenLabs v3 qo'llab-quvvatlaydigan kreativ boshqaruv usullari:
  - Emotsiya: matn konteksti orqali (masalan: "he said excitedly")
  - Pauza: "..." yoki "—" yoki yangi qator orqali
  - Tezlik: matn oqimi va tinish belgilari orqali
  - Ovoz effektlari: <sfx> tagi orqali
  - Ko'p nutqchi: dialog formati orqali

MUHIM: v3 modelida SSML break taglar QOLLAB-QUVVATLANMAYDI.
Buning o'rniga matn asosidagi boshqaruv ishlatiladi.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger("vodiysoftbot.tts_enhancer")

# ElevenLabs v3 tomonidan qo'llab-quvvatlanadigan kreativ taglar va usullar
ELEVENLABS_V3_TAGS = [
    "[laughs]", "[chuckles]", "[sighs]", "[gasps]",
    "[clears throat]", "[speaking slowly]", "[speaking quickly]",
    "[thoughtful]", "[excited]", "[whispers]", "[sad]",
    "[serious]", "[angry]", "[surprised]",
]

ENHANCE_SYSTEM_PROMPT = """Sen matnni ElevenLabs v3 TTS uchun boyituvchi yordamchisan.

Vazifang: berilgan matnni tabiiy va emotsional qilib v3 modeliga mos usullar bilan boyitish.

== EMOTSIYA va TON BOSHQARUVI ==
Qo'llash mumkin bo'lgan taglar:
[laughs], [chuckles], [sighs], [gasps], [clears throat],
[speaking slowly], [speaking quickly], [thoughtful], [excited],
[whispers], [sad], [serious], [angry], [surprised]

== PAUZA BOSHQARUVI (v3 uchun) ==
- Qisqa pauza: "..." (uch nuqta)
- O'rta pauza: "—" (tire)
- Uzun pauza: yangi qator (\\n)
MUHIM: SSML <break> tagi ISHLAMAYDI! Faqat yuqoridagi usullarni ishlat.

== TEZLIK va RITM ==
- Sekin o'qish: vergullar va nuqtalar ko'proq qo'y
- Tez o'qish: qisqa gaplar, kam tinish belgilari

== OVOZ EFFEKTLARI ==
- Fon ovozlari uchun: <sfx>tavsif</sfx> (masalan: <sfx>crowd cheering</sfx>)

QOIDALAR:
1. Matn ma'nosini O'ZGARTIRMA — faqat taglar va tinish belgilari qo'sh
2. Taglarni tabiiy joylarga qo'y (gap boshida, vergul/nuqta oldidan)
3. Haddan ziyod tag qo'yma — har 1-2 gapda 1 ta yetarli
4. Kontekstga mos tag tanlash — xursand gap = [excited]/[chuckles], o'ylanish = [thoughtful]
5. Qisqa matnlarga (5 so'zdan kam) tag qo'yma
6. FAQAT boyitilgan matnni qaytar — hech qanday izoh yoki tushuntirish qo'shma
7. Pauzalar uchun "..." va "—" ishlatish — SSML ishlatma!

Misol:
Kirish: "Jigarim, bu loyihada qiziq narsa bor. Toshkentdagi kompaniya bilan ishladik, natija zo'r bo'ldi."
Chiqish: "[thoughtful] Jigarim, bu loyihada qiziq narsa bor... [excited] Toshkentdagi kompaniya bilan ishladik — natija zo'r bo'ldi."

Kirish: "Ha, tushundim. Keling ertaga gaplashamiz."
Chiqish: "Ha, tushundim... [speaking slowly] Keling — ertaga gaplashamiz."
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
    if any(tag in text for tag in ELEVENLABS_V3_TAGS):
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
    Faqat ruxsat etilgan ElevenLabs v3 taglarni qoldiradi,
    noto'g'ri taglarni olib tashlaydi.
    """
    # Barcha [...] formatdagi taglarni topish
    all_tags = re.findall(r"\[[^\]]+\]", text)

    for tag in all_tags:
        if tag.lower() not in [t.lower() for t in ELEVENLABS_V3_TAGS]:
            text = text.replace(tag, "")

    # Ortiqcha bo'sh joylarni tozalash
    text = re.sub(r"  +", " ", text).strip()
    return text
