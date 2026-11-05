# Navo Fast Bot (@navofast_bot)

Telegram bot: video yuklash, videodagi qo'shiqni aniqlash va MP3 yuklash.
Developed by CyberNexTeam.

## Imkoniyatlar
- Instagram / TikTok / YouTube havolasidan video yuklash
- Qo'shiq nomi bo'yicha qidiruv (5 variant) va MP3 yuklash
- Video, audio yoki ovozli xabardan qo'shiqni aniqlash (Shazam)
- Yuklangan fayllarni keshlash (qayta so'rovda darrov yuboriladi)

## Talablar
- Python 3.12
- ffmpeg (Ubuntu: `sudo apt install ffmpeg`)

## Serverda ishga tushirish (Linux)
```bash
git clone <repo-manzili> navo-fast-bot
cd navo-fast-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env        # tokenni va linklarni yozing
python bot.py
```

`.env` namunasi:
```
BOT_TOKEN=...
INSTAGRAM_URL=https://www.instagram.com/sarbon.k415
CHANNEL_URL=https://t.me/cybernex_uz
```

## Doimiy ishlatish
Bot yopilib qolmasligi uchun systemd yoki pm2/supervisor orqali ishga tushiring.
`yt-dlp` ni vaqti-vaqti bilan yangilab turing: `pip install -U yt-dlp`

## Muhim
- Bot tokeni faqat `.env` faylida turadi, GitHub'ga yuklanmaydi.
- Instagram/YouTube serverning IP manzilini bloklashi mumkin. Shunda proksi yoki cookies kerak bo'ladi.
