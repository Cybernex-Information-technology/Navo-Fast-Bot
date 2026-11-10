"""
Tezkor va yuqori sifatli media yuklash dvigateli (yt-dlp).
Instagram, TikTok va YouTube dan 1080p Full HD sifatda yuklaydi,
qotmasdan va sifatni 360p ga tushirib yubormaydi.
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from core.config import COOKIES_FILE, MAX_BYTES, YTDLP_PROXY
from services.downloader.media_probe import (
    compress_video_to_size,
    probe_video_dimensions,
)

log = logging.getLogger("downloader")


def get_base_ydl_opts(outtmpl: str) -> Dict[str, Any]:
    """
    Umumiy barqarorlik va yuqori tezlik parametrlari.
    Eslatma: DASH va HLS oqimlari o'chirilmaydi, chunki 1080p va 720p HD faqat DASH da keladi!
    """
    opts: Dict[str, Any] = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 8,
        "socket_timeout": 25,
        "retries": 3,
        "no_check_certificates": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,uz;q=0.8,ru;q=0.7",
        },
    }
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
    if COOKIES_FILE and os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


def download_video_file(
    url: str, outdir: Path
) -> Tuple[Dict[str, Any], Path, Optional[int], Optional[int], Optional[int]]:
    """
    Videoni eng yuqori sifatda (1080p gacha Full HD, 60fps) yuklab oladi.
    Format_sort orqali 360p ga tushib qolishining oldi olingan.
    Agar fayl 50 MB dan oshsa, avtomatik ravishda eng maqbul sifatda siqiladi.
    """
    outtmpl = str(outdir / "%(id)s.%(ext)s")
    opts = get_base_ydl_opts(outtmpl)

    # 1080p Full HD gacha eng yaxshi video + audio oqimlari
    opts["format"] = (
        "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
        "bv*[height<=1080]+ba/"
        "b[height<=1080][ext=mp4]/"
        "b[height<=1080]/"
        "bv*+ba/"
        "best"
    )
    opts["format_sort"] = [
        "res:1080",
        "fps",
        "codec:h264:m4a",
        "size",
        "br",
    ]
    opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    files = [p for p in outdir.iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not files:
        raise RuntimeError("Video fayl topilmadi yoki yuklash bekor qilindi.")

    final_path = max(files, key=lambda p: p.stat().st_size)

    # ffprobe orqali haqiqiy o'lchamlarni aniqlash
    w, h, duration = probe_video_dimensions(final_path)
    if not duration:
        duration = int(info.get("duration") or 0) or None

    # Agar hajm 50 MB (Telegram bot limiti) dan oshib ketgan bo'lsa, siqish
    if final_path.stat().st_size > MAX_BYTES:
        compressed = outdir / "compressed_1080.mp4"
        if compress_video_to_size(final_path, compressed, target_bytes=47 * 1024 * 1024, duration_sec=duration):
            final_path = compressed
            w, h, duration = probe_video_dimensions(final_path)

    return info, final_path, w, h, duration


def download_audio_file(url: str, outdir: Path) -> Tuple[Dict[str, Any], Path]:
    """
    Audioni to'liq va toza MP3 formatda tez yuklaydi.
    192 kbps yuqori audio sifatini ta'minlaydi.
    """
    outtmpl = str(outdir / "%(id)s.%(ext)s")
    opts = get_base_ydl_opts(outtmpl)

    opts["format"] = "bestaudio/best"
    opts["postprocessors"] = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    mp3_files = [p for p in outdir.iterdir() if p.suffix.lower() == ".mp3"]
    if mp3_files:
        return info, max(mp3_files, key=lambda p: p.stat().st_size)

    all_files = [p for p in outdir.iterdir() if p.is_file() and not p.name.endswith(".part")]
    if not all_files:
        raise RuntimeError("Audio fayl topilmadi.")

    path = max(all_files, key=lambda p: p.stat().st_size)
    return info, path


def search_youtube_videos(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    YouTube bo'yicha musiqa qidirish.
    Natijalar ro'yxatini qaytaradi (id, title, artist, duration).
    """
    opts = get_base_ydl_opts("%(id)s.%(ext)s")
    opts["extract_flat"] = True
    opts["skip_download"] = True

    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch{count}:{query}", download=False)

    results = []
    for entry in data.get("entries", []):
        if not entry or not entry.get("id"):
            continue
        results.append({
            "id": entry["id"],
            "title": entry.get("title") or "Nomsiz",
            "artist": entry.get("uploader") or entry.get("channel") or "",
            "duration": int(entry.get("duration") or 0),
        })
    return results
