"""
Video havolalarini qabul qilish va yuklab berish (Instagram, TikTok, YouTube).
Yuqori sifat (1080p gacha), to'g'ri proporsiya va Telegram Dumaloq video (Teleskop).
"""
import asyncio
import logging
import re
import uuid
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
import yt_dlp

from core.config import (
    BOT_USERNAME,
    CONCURRENCY_LIMIT,
    MAX_BYTES,
    TEAM_NAME,
)
from core.database import Database
from core.fun_phrases import FUN_PHRASES, get_random_phrase
from services.bot.keyboards.inline import make_media_keyboard
from services.downloader.cleaner import temporary_directory
from services.downloader.media_probe import make_round_video_note
from services.downloader.ytdlp_engine import download_video_file

log = logging.getLogger("media_handler")
router = Router(name="media")

URL_REGEX = re.compile(r"https?://\S+")
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(CONCURRENCY_LIMIT)

THANKS = "🙏 Bizni tanlaganingiz uchun rahmat!"
CAPTION = f"📥 {BOT_USERNAME} orqali yuqori sifatda yuklab olindi\n{THANKS}"


def normalize_media_url(url: str) -> str:
    """Keraksiz kuzatuv (tracking) parametrlarini olib tashlash."""
    try:
        parsed = urlparse(url)
        clean_path = parsed.path.rstrip("/") + "/" if "/reel/" in parsed.path or "/p/" in parsed.path else parsed.path

        # Instagram havolalarida barcha query parametrlarni tozalash
        if "instagram.com" in parsed.netloc:
            return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))

        # YouTube da si, feature kabi tracking parametrlarni tozalash
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            query_params = parse_qs(parsed.query)
            clean_query = {k: v for k, v in query_params.items() if k in ("v", "t")}
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(clean_query, doseq=True), ""))

        return url.split("?")[0] if "?" in url else url
    except Exception:
        return url


async def animate_progress(status_msg: Message, task: asyncio.Task):
    """Foydalanuvchiga kreativ va xushchaqchaq yuklash xabarlarini navbat bilan ko'rsatish."""
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


@router.message(F.text)
async def on_text_message(message: Message):
    text = message.text.strip()
    match = URL_REGEX.search(text)
    if match:
        url = match.group(0)
        await process_video_download(message, normalize_media_url(url))
    elif 2 <= len(text) <= 120:
        # Agar havola emas, oddiy matn bo'lsa - qo'shiq qidirishga yo'naltirish
        from services.bot.handlers.music import process_music_search
        await process_music_search(message, text)


async def process_video_download(message: Message, url: str):
    # 1. Keshni tekshirish (agar avval yuklangan bo'lsa, soniyada yuboriladi!)
    cached = await Database.get_cached_media(url, "video")
    button_key = uuid.uuid4().hex[:12]
    await Database.save_button_data(button_key, {"url": url})
    keyboard = make_media_keyboard(button_key=button_key)

    if cached:
        file_id, extra = cached
        try:
            await message.answer_video(
                video=file_id,
                caption=CAPTION,
                reply_markup=keyboard,
                supports_streaming=True,
            )
            await Database.increment_user_downloads(message.from_user.id, "video")
            return
        except Exception as e:
            log.warning("Keshdagi file_id orqali yuborib bo'lmadi, qayta yuklanadi: %s", e)

    # 2. Yangitdan yuklab olish
    status = await message.answer(get_random_phrase())
    try:
        with temporary_directory("navo_vid_") as workdir:
            async def _download_job():
                async with DOWNLOAD_SEMAPHORE:
                    return await asyncio.to_thread(download_video_file, url, workdir)

            job_task = asyncio.create_task(_download_job())
            await animate_progress(status, job_task)
            info, video_path, width, height, duration = job_task.result()

            sent_msg = await message.answer_video(
                video=FSInputFile(video_path),
                caption=CAPTION,
                reply_markup=keyboard,
                width=width,
                height=height,
                duration=duration,
                supports_streaming=True,
            )

            # Keshga saqlash
            if sent_msg.video:
                await Database.set_cached_media(
                    url=url,
                    media_type="video",
                    file_id=sent_msg.video.file_id,
                    title=info.get("title", ""),
                )

            await Database.increment_user_downloads(message.from_user.id, "video")
            await status.delete()

    except yt_dlp.utils.DownloadError as de:
        log.warning("yt-dlp yuklab ololmadi: %s", de)
        await status.edit_text(
            "😕 Bu havoladan video yuklab bo'lmadi.\n"
            "Havola to'g'riligini yoki video yopiq (profil private) emasligini tekshiring."
        )
    except Exception as e:
        log.exception("Kutilmagan video yuklash xatosi: %s", e)
        await status.edit_text("⚠️ Xatolik yuz berdi. Server birozdan so'ng qayta urinib ko'rishni tavsiya qiladi.")


@router.callback_query(F.data.startswith("dl_round:"))
async def on_make_round_video(call: CallbackQuery, bot: Bot):
    """
    @SongFastBot kabi videoni Telegram Dumaloq video (Teleskop / Video Note / Krujochek)
    qilib beruvchi professional xizmat.
    """
    await call.answer()
    key = call.data.split(":")[1]
    data = await Database.get_button_data(key)
    if not data or "url" not in data:
        await call.message.answer("⌛ Bu havola eskirgan, videoni botga qaytadan yuboring.")
        return

    url = data["url"]

    # Keshda avval tayyorlangan video_note bormi?
    cached_round = await Database.get_cached_media(url, "video_note")
    if cached_round:
        file_id, _ = cached_round
        try:
            await bot.send_video_note(chat_id=call.message.chat.id, video_note=file_id)
            await Database.increment_user_downloads(call.from_user.id, "round_video")
            return
        except Exception as e:
            log.warning("Keshdagi video_note yuborilmadi: %s", e)

    status = await call.message.answer("🔄 Dumaloq video (Teleskop) tayyorlanmoqda...")
    try:
        with temporary_directory("navo_round_") as workdir:
            async def _round_job():
                async with DOWNLOAD_SEMAPHORE:
                    _, vid_path, _, _, _ = await asyncio.to_thread(download_video_file, url, workdir)
                    out_round = workdir / "round_note.mp4"
                    await asyncio.to_thread(make_round_video_note, vid_path, out_round)
                    return out_round

            round_file = await _round_job()
            sent_note = await bot.send_video_note(
                chat_id=call.message.chat.id,
                video_note=FSInputFile(round_file),
                length=480,
            )

            if sent_note.video_note:
                await Database.set_cached_media(
                    url=url,
                    media_type="video_note",
                    file_id=sent_note.video_note.file_id,
                )

            await Database.increment_user_downloads(call.from_user.id, "round_video")
            await status.delete()

    except Exception as e:
        log.exception("Dumaloq video tayyorlashda xatolik: %s", e)
        await status.edit_text("⚠️ Dumaloq video tayyorlashda xatolik yuz berdi.")
