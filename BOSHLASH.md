# Navo Fast Bot - kompyuterda ishga tushirish (Windows)

## 0. Token
Telegramda @BotFather -> /revoke -> @navofast_bot -> YANGI token oling.
(Eski token ochiq qolgan, uni ishlatmang.)

## 1. ffmpeg o'rnatish (bir marta)
CMD yoki PowerShell oching:

    winget install Gyan.FFmpeg

Oynani yoping, yangisini oching va tekshiring:

    ffmpeg -version

## 2. Loyiha papkasida kutubxonalarni o'rnatish
Shu papkada CMD oching (papka manziliga cmd deb yozib Enter bosing):

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

## 3. Tokenni qo'yish
    copy .env.example .env

.env faylini Notepad bilan oching va yangi tokenni yozing:

    BOT_TOKEN=123456:ABC...

## 4. Ishga tushirish
    python bot.py

"Bot ishga tushdi: @navofast_bot" degan yozuv chiqsa, tayyor.
To'xtatish: Ctrl+C. CMD oynasi yopilsa bot ham o'chadi.

## 5. Sinab ko'rish
- Instagram reel / TikTok / YouTube havolasini botga yuboring.
- Video ostidagi "Qo'shiqni yuklab olish" tugmasini bosing.
- Botga "Sadek L'ghayta" deb yozing, 5 variant chiqadi, raqamni bosing.

## Xato chiqsa
CMD oynasidagi matnni to'liq nusxalab menga yuboring.
YouTube/Instagram ba'zan "Sign in" yoki "429" xatosini beradi - bu bloklash, birga hal qilamiz.
Eski bo'lib qolsa: pip install -U yt-dlp
