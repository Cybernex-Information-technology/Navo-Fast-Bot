"""
Navo Fast Bot - by CyberNexTeam

  1) Video havolasi            -> videoni yuklab beradi
  2) Video ostidagi tugma      -> to'liq qo'shiqni topib beradi
  3) Qo'shiq nomi              -> 5 ta variant, tanlanganini yuboradi
  4) Video / audio / ovozli xabar -> qo'shiq nomini aniqlaydi (Shazam) va to'liq MP3 beradi
"""
import asyncio
import html
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import yt_dlp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "").strip()   # masalan https://instagram.com/cybernexteam
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()       # masalan https://t.me/cybernexteam

BOT_USERNAME = "@navofast_bot"
TEAM_NAME = "CyberNexTeam"
THANKS = "🙏 Bizni tanlaganingiz uchun rahmat!"
CAPTION = f"📥 {BOT_USERNAME} orqali yuklab olindi\n{THANKS}"
AUDIO_CAPTION = f"🎧 {BOT_USERNAME} orqali yuklab olindi\n{THANKS}"

# Yuklash paytida ko'rsatiladigan xushchaqchaq xabarlar
FUN = [
    "⏳ Yuklanmoqda... Shu orada bir tabassum qiling 😊",
    "🎶 Yaxshi musiqa - yaxshi kayfiyat!",
    "😄 Kulgan odam doim yosh qoladi",
    "🚀 Navo tezkor ishlayapti, ozgina sabr...",
    "☕ Bir qultum choy ichib turing, deyarli tayyor",
    "🌟 Bugun sizga omad kulib boqsin!",
    "💙 Yaxshi kun tilaymiz!",
]

MAX_BYTES = 49 * 1024 * 1024
MAX_AUDIO_MINUTES = 20
SEM = asyncio.Semaphore(3)

URL_RE = re.compile(r"https?://\S+")
router = Router()
log = logging.getLogger("navo")

# ---------------------------------------------------------------- xotira va kesh
STORE: dict[str, dict] = {}          # tugma bosilganda kerak bo'ladigan vaqtinchalik ma'lumotlar
CACHE_FILE = Path(__file__).with_name("cache.json")   # bir marta yuklangan narsa keyin darrov yuboriladi
try:
    CACHE: dict = json.loads(CACHE_FILE.read_text("utf-8"))
except Exception:
    CACHE = {}


def cache_set(key: str, value):
    CACHE[key] = value
    try:
        CACHE_FILE.write_text(json.dumps(CACHE, ensure_ascii=False), "utf-8")
    except Exception:
        log.warning("Keshni saqlab bo'lmadi")


def put(data: dict) -> str:
    key = uuid.uuid4().hex[:10]
    STORE[key] = data
    while len(STORE) > 2000:
        STORE.pop(next(iter(STORE)))
    return key


def normalize_url(url: str) -> str:
    if "instagram.com" in url:
        return url.split("?")[0]
    return url


# ---------------------------------------------------------------- tugmalar
def promo_rows():
    rows = []
    links = []
    if INSTAGRAM_URL:
        links.append(InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL))
    if CHANNEL_URL:
        links.append(InlineKeyboardButton(text="📢 Telegram kanal", url=CHANNEL_URL))
    if links:
        rows.append(links)
    rows.append(
        [InlineKeyboardButton(text="➕ Guruhga qo'shish", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true")]
    )
    return rows


def kb(*first_rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[*first_rows, *promo_rows()])


async def run_with_fun(status: Message, coro):
    """Ish bajarilayotganda har 3 soniyada xushchaqchaq xabarni almashtirib turadi."""
    task = asyncio.create_task(coro)
    i = 0
    while not task.done():
        await asyncio.wait({task}, timeout=3)
        if task.done():
            break
        i += 1
        try:
            await status.edit_text(FUN[i % len(FUN)])
        except Exception:
            pass
    return task.result()


# ---------------------------------------------------------------- yuklash
def download_video(url: str, outdir: Path):
    opts = {
        "format": (
            "bv*[vcodec^=avc1][height<=1080][filesize<?48M]+ba[acodec^=mp4a]/"
            "b[ext=mp4][filesize<?48M]/b[filesize<?48M]/b"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(outdir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 4,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    files = [p for p in outdir.iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not files:
        raise RuntimeError("Video fayl topilmadi")
    return info, max(files, key=lambda p: p.stat().st_size)


def download_audio(url: str, outdir: Path):
    """Audioni tez yuklaydi (m4a bo'lsa qayta kodlamaydi, boshqa bo'lsa MP3 qiladi)."""
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(outdir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 4,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    files = [p for p in outdir.iterdir() if p.is_file()]
    if not files:
        raise RuntimeError("Audio fayl topilmadi")
    path = max(files, key=lambda p: p.stat().st_size)
    if path.suffix.lower() not in {".m4a", ".mp3"}:
        mp3 = path.with_suffix(".mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-vn", "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3)],
            check=True,
            capture_output=True,
        )
        path = mp3
    return info, path


def search_youtube(query: str, count: int = 5):
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    results = []
    for e in data.get("entries", []):
        if not e or not e.get("id"):
            continue
        results.append(
            {
                "id": e["id"],
                "title": e.get("title") or "Nomsiz",
                "artist": e.get("uploader") or e.get("channel") or "",
                "duration": int(e.get("duration") or 0),
            }
        )
    return results


def fmt_duration(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}" if sec else "--:--"


# ---------------------------------------------------------------- buyruqlar
@router.message(CommandStart())
async def cmd_start(message: Message):
    name = html.escape(message.from_user.first_name or "do'stim")
    await message.answer(
        f"👋 Salom, <b>{name}</b>!\n\n"
        "Men <b>Navo Fast Bot</b> - videolar va qo'shiqlarni tez yuklaydigan botman 🎬🎵\n\n"
        "📥 Instagram, TikTok, YouTube havolasini yuboring - videoni yuklab beraman\n"
        "🎵 Qo'shiq yoki ijrochi nomini yozing - topib beraman\n"
        "🎧 Video, audio yoki ovozli xabar yuboring - qo'shiq nomini aniqlayman\n\n"
        f"Developed by <b>{TEAM_NAME}</b>\n\n"
        "📣 <b>Foydali ma'lumotlar</b> uchun Telegram va Instagram sahifalarimizga obuna bo'ling. "
        "Bu majburiy emas, lekin sizni jamoamiz orasida ko'rsak xursand bo'lamiz.",
        parse_mode="HTML",
        reply_markup=kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Qanday ishlaydi</b>\n\n"
        "1. Video havolasini yuboring, video keladi.\n"
        "2. Video ostidagi «Qo'shiqni yuklab olish» tugmasi to'liq qo'shiqni topib beradi.\n"
        "3. Qo'shiq nomini yozing, 5 ta variantdan birini tanlang.\n"
        "4. Video, audio yoki ovozli xabar yuboring, qo'shiqni aniqlayman.\n\n"
        f"Developed by <b>{TEAM_NAME}</b>",
        parse_mode="HTML",
        reply_markup=kb(),
    )


# ---------------------------------------------------------------- matn
@router.message(F.text)
async def on_text(message: Message):
    text = message.text.strip()
    m = URL_RE.search(text)
    if m:
        await handle_link(message, normalize_url(m.group(0)))
    elif 2 <= len(text) <= 100:
        await handle_search(message, text)


async def handle_link(message: Message, url: str):
    key = put({"url": url})
    markup = kb([InlineKeyboardButton(text="📥 Qo'shiqni yuklab olish", callback_data=f"m:{key}")])

    cached = CACHE.get("v:" + url)
    if cached:  # avval yuklangan bo'lsa, darrov yuboramiz
        try:
            await message.answer_video(cached, caption=CAPTION, reply_markup=markup)
            return
        except Exception:
            log.warning("Keshdagi video yuborilmadi, qayta yuklanadi")

    status = await message.answer(FUN[0])
    workdir = Path(tempfile.mkdtemp(prefix="navo_"))
    try:
        async def job():
            async with SEM:
                return await asyncio.to_thread(download_video, url, workdir)

        info, path = await run_with_fun(status, job())
        if path.stat().st_size > MAX_BYTES:
            await status.edit_text("😕 Video juda katta (50 MB dan oshiq), yubora olmayman.")
            return
        sent = await message.answer_video(
            FSInputFile(path),
            caption=CAPTION,
            reply_markup=markup,
            width=info.get("width"),
            height=info.get("height"),
            duration=int(info.get("duration") or 0) or None,
            supports_streaming=True,
        )
        if sent.video:
            cache_set("v:" + url, sent.video.file_id)
        await status.delete()
    except yt_dlp.utils.DownloadError as e:
        log.warning("Yuklab bo'lmadi: %s", e)
        await status.edit_text(
            "😕 Bu havoladan video yuklab bo'lmadi.\n"
            "Havola to'g'riligini va video yopiq (private) emasligini tekshiring."
        )
    except Exception:
        log.exception("Kutilmagan xato")
        await status.edit_text("⚠️ Xatolik yuz berdi, birozdan keyin qayta urinib ko'ring.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def handle_search(message: Message, query: str):
    status = await message.answer("🔎 Qidirilmoqda...")
    try:
        results = await asyncio.to_thread(search_youtube, query)
    except Exception:
        log.exception("Qidiruvda xato")
        await status.edit_text("⚠️ Qidirishda xatolik yuz berdi.")
        return
    if not results:
        await status.edit_text("😕 Hech narsa topilmadi. Boshqacha yozib ko'ring.")
        return
    text, markup = results_message(query, results)
    await status.edit_text(text, parse_mode="HTML", reply_markup=markup)


def results_message(query: str, results: list):
    key = put({"results": results})
    safe_q = html.escape(query)
    lines = [f"🎵 <b>{safe_q}</b>\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"<b>{i}.</b> {html.escape(r['title'])} <b>{fmt_duration(r['duration'])}</b>")
    row = [
        InlineKeyboardButton(text=str(i), callback_data=f"s:{key}:{i - 1}")
        for i in range(1, len(results) + 1)
    ]
    lines.append("\n👇 Kerakli variantni tanlang")
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=[row])


# ---------------------------------------------------------------- MP3 yuborish
async def send_mp3(msg: Message, url: str, title: str = None, artist: str = None):
    markup = kb()
    cached = CACHE.get("a:" + url)
    if cached:
        try:
            await msg.answer_audio(cached, caption=AUDIO_CAPTION, reply_markup=markup)
            return
        except Exception:
            log.warning("Keshdagi audio yuborilmadi, qayta yuklanadi")

    status = await msg.answer(FUN[1])
    workdir = Path(tempfile.mkdtemp(prefix="navo_"))
    try:
        async def job():
            async with SEM:
                return await asyncio.to_thread(download_audio, url, workdir)

        info, path = await run_with_fun(status, job())
        if (info.get("duration") or 0) > MAX_AUDIO_MINUTES * 60:
            await status.edit_text(f"😕 Audio {MAX_AUDIO_MINUTES} daqiqadan uzun.")
            return
        if path.stat().st_size > MAX_BYTES:
            await status.edit_text("😕 Audio fayl juda katta.")
            return
        sent = await msg.answer_audio(
            FSInputFile(path),
            title=title or info.get("track") or info.get("title"),
            performer=artist or info.get("artist") or info.get("uploader"),
            caption=AUDIO_CAPTION,
            reply_markup=markup,
        )
        if sent.audio:
            cache_set("a:" + url, sent.audio.file_id)
        await status.delete()
    except yt_dlp.utils.DownloadError as e:
        log.warning("Audio yuklanmadi: %s", e)
        await status.edit_text("😕 Musiqani yuklab bo'lmadi.")
    except Exception:
        log.exception("Audioda xato")
        await status.edit_text("⚠️ Xatolik yuz berdi.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------- qo'shiqni aniqlash
def prep_audio(path: Path) -> Path:
    """Shazam uchun audioni toza WAV (mono, 25 soniya) qilib tayyorlaydi."""
    out = path.with_name("shazam_in.wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "44100", "-t", "25", str(out)],
            check=True,
            capture_output=True,
            timeout=90,
        )
        return out
    except Exception:
        log.warning("ffmpeg bilan tayyorlab bo'lmadi, asl fayl ishlatiladi")
        return path


async def recognize(path: Path):
    """Qo'shiq nomi va ijrochisini aniqlaydi. Topilmasa None."""
    try:
        from shazamio import Shazam
    except ImportError:
        log.warning("shazamio o'rnatilmagan: pip install shazamio")
        return None
    try:
        src = await asyncio.to_thread(prep_audio, path)
        shazam = Shazam()
        fn = getattr(shazam, "recognize", None) or shazam.recognize_song
        out = await fn(str(src))
        track = out.get("track")
        if track and track.get("title"):
            log.info("Shazam topdi: %s - %s", track.get("subtitle"), track.get("title"))
            return track["title"], track.get("subtitle", "")
        log.info("Shazam topa olmadi (javobda 'track' yo'q)")
    except Exception:
        log.exception("Shazam xatosi")
    return None


async def reply_with_track(msg: Message, status: Message, title: str, artist: str):
    try:
        results = await asyncio.to_thread(search_youtube, f"{artist} - {title}")
    except Exception:
        log.exception("Qidiruvda xato")
        await status.edit_text(f"🎵 {artist} - {title}\n⚠️ To'liq variantni qidirishda xatolik.")
        return
    if not results:
        await status.edit_text(f"🎵 {artist} - {title}\n😕 To'liq variant topilmadi.")
        return
    text, markup = results_message(f"{artist} — {title}", results)
    await status.edit_text(text, parse_mode="HTML", reply_markup=markup)


async def identify_and_reply(
    msg: Message, clip: Path, clip_title: str = None, fallback_clip: bool = False, cache_key: str = None
):
    status = await msg.answer("🎧 Qo'shiq aniqlanmoqda...")
    track = await recognize(clip)
    if not track:
        if fallback_clip:
            await status.edit_text("😕 Qo'shiq nomini aniqlay olmadim, videodagi audioni yuboraman.")
            await msg.answer_audio(
                FSInputFile(clip), title=clip_title, caption=AUDIO_CAPTION, reply_markup=kb()
            )
        else:
            await status.edit_text(
                "😕 Qo'shiq aniqlanmadi.\n"
                "Musiqa aniqroq eshitiladigan 10-15 soniyalik parcha yuboring yoki nomini yozing."
            )
        return
    if cache_key:
        cache_set("r:" + cache_key, list(track))
    await reply_with_track(msg, status, *track)


async def full_song_from_video(msg: Message, url: str):
    cached = CACHE.get("r:" + url)
    if cached:  # bu videodagi qo'shiq avval aniqlangan
        status = await msg.answer("🎧 Qo'shiq topilmoqda...")
        await reply_with_track(msg, status, cached[0], cached[1])
        return

    status = await msg.answer("⏳ Audio ajratilmoqda...")
    workdir = Path(tempfile.mkdtemp(prefix="navo_"))
    try:
        async with SEM:
            info, clip = await asyncio.to_thread(download_audio, url, workdir)
        await status.delete()
        await identify_and_reply(msg, clip, info.get("title"), fallback_clip=True, cache_key=url)
    except yt_dlp.utils.DownloadError as e:
        log.warning("Audio yuklanmadi: %s", e)
        await status.edit_text("😕 Musiqani ajratib bo'lmadi.")
    except Exception:
        log.exception("Aniqlashda xato")
        await status.edit_text("⚠️ Xatolik yuz berdi.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------- video / audio / ovozli xabar
@router.message(F.voice | F.audio | F.video | F.video_note)
async def on_media(message: Message, bot: Bot):
    media = message.voice or message.audio or message.video or message.video_note
    if media.file_size and media.file_size > 20 * 1024 * 1024:
        await message.answer("😕 Fayl juda katta. 20 MB gacha bo'lgan fayl yuboring.")
        return
    workdir = Path(tempfile.mkdtemp(prefix="navo_"))
    try:
        if message.voice:
            ext = ".ogg"
        elif message.audio:
            ext = Path(message.audio.file_name or "").suffix or ".mp3"
        else:
            ext = ".mp4"
        path = workdir / f"input{ext}"
        await bot.download(media, destination=path)
        await identify_and_reply(message, path)
    except Exception:
        log.exception("Faylni qayta ishlashda xato")
        await message.answer("⚠️ Faylni qayta ishlab bo'lmadi.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------- tugmalar
@router.callback_query(F.data.startswith("m:"))
async def cb_music(call: CallbackQuery):
    await call.answer()
    data = STORE.get(call.data.split(":")[1])
    if not data:
        await call.message.answer("⌛ Bu tugma eskirgan, havolani qayta yuboring.")
        return
    await full_song_from_video(call.message, data["url"])


@router.callback_query(F.data.startswith("s:"))
async def cb_pick(call: CallbackQuery):
    await call.answer()
    _, key, idx = call.data.split(":")
    data = STORE.get(key)
    if not data:
        await call.message.answer("⌛ Natijalar eskirgan, nomni qayta yozing.")
        return
    video_id = data["results"][int(idx)]["id"]
    await send_mp3(call.message, f"https://www.youtube.com/watch?v={video_id}")


# ---------------------------------------------------------------- ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not BOT_TOKEN:
        raise SystemExit(".env faylida BOT_TOKEN topilmadi")
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
