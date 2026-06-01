# UserBot

VodiySoft UserBot — AI yordamchi Telegram userbot.

## Xususiyatlar

- 🤖 OpenAI GPT orqali aqlli javoblar
- 🎙️ Ovozli xabarlarni matnga aylantirish (Whisper STT)
- 🔊 Matnni ovozga aylantirish (ElevenLabs TTS)
- 📱 Shaxsiy chat, guruh va kanallarda ishlaydi
- ⏱️ Rate limiting va tabiiy kutish vaqti

## O'rnatish

1. Repozitoriyani klonlang
2. `.env.example` faylini `.env` ga nusxa ko'chiring va to'ldiring
3. Kerakli paketlarni o'rnating:

```bash
pip install -r requirements.txt
```

4. Ishga tushiring:

```bash
python main.py
```

## ElevenLabs TTS

Matnni ovozga aylantirish uchun ElevenLabs API ishlatiladi.

### Sozlash

1. [ElevenLabs](https://elevenlabs.io) saytida ro'yxatdan o'ting
2. [API Keys](https://elevenlabs.io/app/settings/api-keys) sahifasidan kalit oling
3. `.env` fayliga qo'shing:

```env
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
```

### Foydalanish

Telegram chatda quyidagi buyruqni yozing:

```
.tts Salom, dunyo!
```

Bot matnni ovozga aylantirib, ovozli xabar sifatida yuboradi.

## Muhit o'zgaruvchilari

Barcha sozlamalar `.env.example` faylida batafsil tavsiflangan.
