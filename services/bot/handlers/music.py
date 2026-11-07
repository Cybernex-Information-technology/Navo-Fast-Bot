"""
Musiqa bilan ishlash bo'limi:
- Nom bo'yicha qidiruv (5 ta variant)
- Shazam orqali videodan to'liq MP3 qo'shiqni ajratib berish
- Ovozli xabar (voice) yoki audio fayllardan musiqani aniqlash
- Hech qachon eskirmaydigan tugmalar (direct callback)
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
import yt_dlp

from core.config import (
    BOT_USERNAME,
    CONCURRENCY_LIMIT,
    MAX_AUDIO_MINUTES,
    MAX_BYTES,
    TEAM_NAME,
)
from core.database import Database
from core.fun_phrases import FUN_PHRASES, get_random_phrase
from services.bot.keyboards.inline import make_promo_keyboard
from services.downloader.cleaner import temporary_directory
from services.downloader.ytdlp_engine import download_audio_file, search_youtube_videos
from services.recognizer.search_service import build_search_response
from services.recognizer.shazam_service import recognize_track

log = logging.getLogger("music_handler")
router = Router(name="music")

AUDIO_SEMAPHORE = asyncio.Semaphore(CONCURRENCY_LIMIT)
THANKS = "🙏 Bizni tanlaganingiz uchun rahmat!"
AUDIO_CAPTION = f"🎧 {BOT_USERNAME} orqali yuklab olindi\n{THANKS}"


async def animate_audio_progress(status_msg: Message, task: asyncio.Task):
    """Musiqa yuklanayotganda qiziqarli xabarlar ko'rsatish."""
    idx = 0
    while not task.done():
        try:
            await asyncio.wait({task}, timeout=3.0)
            if task.done():
                break
            idx += 1
            await status_msg.edit_text(FUN_PHRASES[idx % len(FUN_PHRASES)])
        except Exception:
            pass


async def process_music_search(message: Message, query: str):
    """Qo'shiq nomi bo'yicha YouTube qidiruv."""
    status = await message.answer("🔎 Qo'shiq qidirilmoqda...")
    try:
        results = await asyncio.to_thread(search_youtube_videos, query, 5)
    except Exception as e:
        log.exception("Qidiruvda xatolik: %s", e)
        await status.edit_text("⚠️ Qidirish jarayonida xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    if not results:
        await status.edit_text("😕 Hech narsa topilmadi. Qo'shiq yoki ijrochi nomini boshqacha yozib ko'ring.")
        return

    text, keyboard = build_search_response(query, results)
    await status.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


async def send_full_mp3(
    message: Message,
    url: str,
    user_id: int,
    title: Optional[str] = None,
    artist: Optional[str] = None,
):
    """MP3 faylni xavfsiz yuklab olib, foydalanuvchiga yuborish."""
    # 1. Keshni tekshirish
    cached = await Database.get_cached_media(url, "audio")
    keyboard = make_promo_keyboard()

    if cached:
        file_id, extra = cached
        try:
            await message.answer_audio(
                audio=file_id,
                caption=AUDIO_CAPTION,
                reply_markup=keyboard,
            )
            await Database.increment_user_downloads(user_id, "audio")
            return
        except Exception as e:
            log.warning("Keshdagi audio yuborilmadi: %s", e)

    # 2. Yuklab olish
    status = await message.answer("⏳ To'liq MP3 qo'shiq yuklanmoqda...")
    try:
        with temporary_directory("navo_aud_") as workdir:
            async def _download_audio_job():
                async with AUDIO_SEMAPHORE:
                    return await asyncio.to_thread(download_audio_file, url, workdir)

            task = asyncio.create_task(_download_audio_job())
            await animate_audio_progress(status, task)
            info, audio_path = task.result()

            # Cheklovlar
            duration = int(info.get("duration") or 0)
            if duration > MAX_AUDIO_MINUTES * 60:
                await status.edit_text(f"😕 Audio davomiyligi juda uzun ({MAX_AUDIO_MINUTES} daqiqadan ko'p).")
                return

            if audio_path.stat().st_size > MAX_BYTES:
                await status.edit_text("😕 Audio fayl hajmi juda katta (50 MB dan oshiq).")
                return

            sent_msg = await message.answer_audio(
                audio=FSInputFile(audio_path),
                title=title or info.get("track") or info.get("title") or "Musiqa",
                performer=artist or info.get("artist") or info.get("uploader") or TEAM_NAME,
                duration=duration or None,
                caption=AUDIO_CAPTION,
                reply_markup=keyboard,
            )

            # Keshga saqlash
            if sent_msg.audio:
                await Database.set_cached_media(
                    url=url,
                    media_type="audio",
                    file_id=sent_msg.audio.file_id,
                    title=info.get("title", ""),
                )

            await Database.increment_user_downloads(user_id, "audio")
            await status.delete()

    except yt_dlp.utils.DownloadError as de:
        log.warning("Audio yuklanmadi: %s", de)
        await status.edit_text("😕 Musiqani yuklab bo'lmadi. YouTube bu videoga cheklov o'rnatgan bo'lishi mumkin.")
    except Exception as e:
        log.exception("MP3 yuborishda xato: %s", e)
        await status.edit_text("⚠️ Musiqani yuklashda xatolik yuz berdi.")


@router.callback_query(F.data.startswith("dl_yt:"))
async def on_pick_youtube_song(call: CallbackQuery):
    """
    Qidiruv ro'yxatidan raqam tanlanganda ishlaydi.
    Callback data: dl_yt:{video_id} — HECH QACHON ESKIRMAYDI!
    """
    await call.answer()
    video_id = call.data.split(":")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    await send_full_mp3(call.message, url, call.from_user.id)


@router.callback_query(F.data.startswith("dl_aud:"))
async def on_extract_song_from_video(call: CallbackQuery):
    """
    Video ostidagi «Qo'shiqni yuklab olish» tugmasi bosilganda.
    Videoni qisqa parchasi emas, butun to'liq original qo'shiqni topib yuboradi!
    """
    await call.answer()
    key = call.data.split(":")[1]
    data = await Database.get_button_data(key)

    if not data or "url" not in data:
        await call.message.answer("⌛ Bu havola eskirgan, videoni botga qaytadan yuboring.")
        return

    url = data["url"]

    # Keshda bu videoning to'liq qo'shig'i bormi?
    cached_track = await Database.get_cached_media(url, "shazam_track")
    if cached_track:
        file_id, extra = cached_track
        if extra and "yt_id" in extra:
            yt_url = f"https://www.youtube.com/watch?v={extra['yt_id']}"
            await send_full_mp3(call.message, yt_url, call.from_user.id, extra.get("title"), extra.get("artist"))
            return

    status = await call.message.answer("🎧 Musiqa nomi aniqlanmoqda (Shazam)...")
    try:
        with temporary_directory("navo_shz_") as workdir:
            # Videoning audiosini ajratib olish
            async def _extract_job():
                async with AUDIO_SEMAPHORE:
                    return await asyncio.to_thread(download_audio_file, url, workdir)

            info, audio_clip = await _extract_job()

            # Musiqani aniqlash (avval metama'lumot, keyin Shazam)
            recognized = await recognize_track(audio_clip, media_info=info)

            if recognized:
                title, artist = recognized
                query = f"{artist} - {title}".strip(" -")
                await status.edit_text(f"✨ <b>Topildi:</b> {title} ({artist})\n🔎 To'liq MP3 varianti qidirilmoqda...", parse_mode="HTML")

                # YouTube bo'yicha to'liq qo'shiqni qidirish
                search_res = await asyncio.to_thread(search_youtube_videos, query, 1)
                if search_res:
                    best = search_res[0]
                    yt_url = f"https://www.youtube.com/watch?v={best['id']}"

                    # Keshga saqlash
                    await Database.set_cached_media(
                        url=url,
                        media_type="shazam_track",
                        file_id="",
                        title=title,
                        extra={"yt_id": best["id"], "title": title, "artist": artist}
                    )
                    await status.delete()
                    # To'liq MP3 qo'shiqni yuborish
                    await send_full_mp3(call.message, yt_url, call.from_user.id, title=best["title"], artist=artist)
                    return

            # Agar Shazam orqali to'liq nomi topilmasa, videodagi audio parchasini yuborish
            await status.edit_text("ℹ️ Qo'shiqning to'liq versiyasi topilmadi, videodagi asl audio yuborilmoqda...")
            await call.message.answer_audio(
                audio=FSInputFile(audio_clip),
                title=info.get("title") or "Video audio",
                performer=TEAM_NAME,
                caption=AUDIO_CAPTION,
                reply_markup=make_promo_keyboard()
            )
            await status.delete()

    except Exception as e:
        log.exception("Audioni ajratishda xatolik: %s", e)
        await status.edit_text("⚠️ Qo'shiqni ajratib olishda xatolik yuz berdi.")


@router.message(F.voice | F.audio | F.video | F.video_note)
async def on_user_media_message(message: Message, bot: Bot):
    """
    Foydalanuvchi ovozli xabar, audio yoki video fayl yuborganda
    musiqani aniqlab to'liq variantini topib berish.
    """
    media = message.voice or message.audio or message.video or message.video_note
    if not media:
        return

    if media.file_size and media.file_size > 25 * 1024 * 1024:
        await message.answer("😕 Fayl hajmi juda katta (25 MB dan kichik audio yoki video yuboring).")
        return

    status = await message.answer("🎧 Musiqa aniqlanmoqda...")
    try:
        with temporary_directory("navo_identify_") as workdir:
            ext = ".mp4" if (message.video or message.video_note) else ".ogg"
            if message.audio and message.audio.file_name:
                ext = Path(message.audio.file_name).suffix or ".mp3"

            sample_path = workdir / f"input{ext}"
            await bot.download(media, destination=sample_path)

            recognized = await recognize_track(sample_path)
            if not recognized:
                await status.edit_text(
                    "😕 Musiqa aniqlanmadi.\n"
                    "Iltimos, musiqa aniqroq eshitiladigan 10-15 soniyalik parcha yuboring yoki qo'shiq nomini yozing."
                )
                return

            title, artist = recognized
            query = f"{artist} - {title}".strip(" -")
            await status.edit_text(f"✨ <b>Topildi:</b> {title} ({artist})\n🔎 Qidirilmoqda...", parse_mode="HTML")

            results = await asyncio.to_thread(search_youtube_videos, query, 5)
            if not results:
                await status.edit_text(f"🎵 <b>{title} — {artist}</b>\n😕 To'liq audio topilmadi.", parse_mode="HTML")
                return

            text, keyboard = build_search_response(f"{artist} — {title}", results)
            await status.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        log.exception("Media faylni aniqlashda xato: %s", e)
        await status.edit_text("⚠️ Faylni tahlil qilishda xatolik yuz berdi.")
