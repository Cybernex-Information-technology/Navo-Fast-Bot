# 🚀 Navo Fast Bot — Production Microservice Architecture

> **CyberNexTeam** tomonidan ishlab chiqilgan yuqori tezlikdagi media yuklovchi va musiqa aniqlovchi Telegram bot.

---

## 📌 Asosiy Imkoniyatlar va Yechilgan Muammolar

1. **🎬 Yuqori Sifatli Video (1080p gacha):**
   - Video sifati avvalgidek 360p ga tushib ketmaydi.
   - Vertikal videolarda (Instagram Reels, TikTok, YouTube Shorts) eni-bo'yi cho'zilib ketishi yoki qora hoshiyalar (black bars) paydo bo'lishining oldi olingan (`ffprobe` o'lchamlar tahlili).
2. **🎵 To'liq MP3 Qo'shiq:**
   - Videodan faqat 15 soniyalik parcha emas, butun original to'liq qo'shiq topib beriladi.
   - Metama'lumotlar tahlili + Shazam sun'iy intellekti integratsiya qilingan.
3. **⚡ Tugmalar Hech Qachon Eskirmaydi:**
   - Server qayta ishga tushganda yoki bot to'xtab qolganda `Bu tugma eskirgan...` xatosi chiqmaydi (to'g'ridan-to'g'ri YouTube ID va SQLite bazasi).
4. **📊 To'liq Admin Panel va Statistika:**
   - `/admin` yoki `/stat` orqali jami foydalanuvchilar soni, 24 soatlik faol odamlar va yuklashlar statistikasi.
   - `/broadcast <matn>` orqali barcha foydalanuvchilarga xabar tarqatish.
5. **🛡️ Server IP Bloklanishlaridan Himoya:**
   - YouTube `429 Too Many Requests` yoki `Sign in to confirm you're not a bot` muammolari uchun proksi va `cookies.txt` qo'llab-quvvatlanadi.
6. **💾 Ma'lumotlar Bazasi (SQLite WAL):**
   - Hech qanday JSON fayl buzilmaydi, parallel yozish 100% xavfsiz.
7. **🎉 Kreativ va Xushchaqchaq Yuklash Xabarlari:**
   - Yuklash jarayonida kayfiyatni ko'taruvchi qiziqarli gaplar almashib turadi.

---

## 🏗️ Arxitektura (Microservices & Modular Design)

```
├── core/
│   ├── config.py             # Muhit sozlamalari (.env)
│   ├── database.py           # Ma'lumotlar bazasi (Users, Kesh, Statistika)
│   └── fun_phrases.py        # Kreativ yuklash xabarlari
├── services/
│   ├── downloader/           # 1-Xizmat: Video va Audio yuklash (yt-dlp + ffprobe)
│   ├── recognizer/           # 2-Xizmat: Musiqani aniqlash (Shazam + Qidiruv)
│   └── bot/                  # 3-Xizmat: Telegram interfeysi (aiogram 3.x)
│       ├── handlers/         # Start, Media, Musiqa, Admin
│       ├── keyboards/        # Inline tugmalar
│       └── middlewares/      # Foydalanuvchilarni avtomatik ro'yxatga olish
├── bot.py                    # Asosiy ishga tushirish fayli
├── Dockerfile                # Docker konteyner
├── docker-compose.yml        # 1-buyruq bilan serverda ko'tarish
├── .env.example              # To'liq izohlangan konfiguratsiya
└── requirements.txt          # Kerakli kutubxonalar
```

---

## 🚀 Serverda Ishga Tushirish (Linux / Ubuntu VPS)

### 1-Usul: Docker Compose orqali (Tavsiya etiladi - Eng osoni)

1. Serverda Docker va Docker Compose o'rnatilganiga ishonch hosil qiling:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose
   ```
2. Loyihani serverga yuklang va papkaga kiring:
   ```bash
   cd my-project
   cp .env.example .env
   nano .env
   ```
   *(.env fayliga BOT_TOKEN va ADMIN_IDS ni yozing, saqlash uchun `Ctrl+O`, chiqish uchun `Ctrl+X`)*

3. Botni ishga tushiring:
   ```bash
   docker-compose up -d --build
   ```
4. Loglarni ko'rish:
   ```bash
   docker-compose logs -f
   ```

---

### 2-Usul: To'g'ridan-to'g'ri Python orqali (Systemd yoki PM2)

1. Tizim paketlarini o'rnatish:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv ffmpeg
   ```
2. Virtual muhit yaratish va kutubxonalarni o'rnatish:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. `.env` faylini to'ldirish:
   ```bash
   cp .env.example .env
   nano .env
   ```
4. Botni tekshirish:
   ```bash
   python3 bot.py
   ```

---

## 🔑 YouTube "Sign In" va Bloklanishlarni 100% Hal Qilish

Agar serveringizda `Musiqani yuklab bo'lmadi` yoki `Sign in` xatosi chiqsa:
1. Kompyuteringizdagi Chrome brauzeriga **"Get cookies.txt LOCALLY"** kengaytmasini o'rnating.
2. `youtube.com` ga kiring va kengaytma orqali `cookies.txt` faylini yuklab oling.
3. Ushbu `cookies.txt` faylini serverdagi bot papkasiga tashlang.
4. `.env` faylida quyidagi qatorni yoqing:
   ```env
   COOKIES_FILE=cookies.txt
   ```
5. Botni qayta ishga tushiring. Shundan so'ng hech qachon cheklovga tushmaysiz!

---

## 👑 Admin Buyruqlari

- `/stat` yoki `/admin` — Foydalanuvchilar va yuklashlar statistikasini ko'rish.
- `/broadcast <xabar>` — Barcha foydalanuvchilarga xabar tarqatish.
