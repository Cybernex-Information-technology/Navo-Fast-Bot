"""
Tezkor va xavfsiz media yuklash dvigateli (yt-dlp).
Bloklanishlardan himoyalangan, ko'p oqimli (multithreaded) yuklash.
"""
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from core.config import COOKIES_FILE, YTDLP_PROXY
from services.downloader.media_probe import probe_video_dimensions

log = logging.getLogger("downloader")


def get_base_ydl_opts(outtmpl: str) -> Dict[str, Any]:
    """Umumiy tezlik va barqarorlik parametrlari."""
    opts: Dict[str, Any] = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 8,
        "socket_timeout": 20,
        "retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb", "web"],
                "skip": ["hls", "dash"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,uz;q=0.8",
        },
    }
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
    if COOKIES_FILE and os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


def download_video_file(url: str, outdir: Path) -> Tuple[Dict[str, Any], Path, Optional[int], Optional[int], Optional[int]]:
    """
    Videoni eng yuqori sifatda (1080p gacha) yuklab oladi.
    Sifat buzilishi (360p ga tushib ketish) va eni/bo'yi cho'zilishining oldini oladi.
    """
    outtmpl = str(outdir / "%(id)s.%(ext)s")
    opts = get_base_ydl_opts(outtmpl)

    # Eng yaxshi video + audio oqimlarini MP4 formatida birlashtirish
    opts["format"] = (
        "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
        "bv*[height<=1080]+ba/"
        "b[height<=1080][ext=mp4]/"
        "b[height<=1080]/"
        "best"
    )
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

    return info, final_path, w, h, duration


def download_audio_file(url: str, outdir: Path) -> Tuple[Dict[str, Any], Path]:
    """
    Audioni eng yuqori sifatda tez yuklaydi.
    MP3 yoki M4A formatida saqlanadi.
    """
    outtmpl = str(outdir / "%(id)s.%(ext)s")
    opts = get_base_ydl_opts(outtmpl)
    opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    files = [p for p in outdir.iterdir() if p.is_file() and not p.name.endswith(".part")]
    if not files:
        raise RuntimeError("Audio fayl topilmadi.")

    path = max(files, key=lambda p: p.stat().st_size)

    # Agar fayl m4a yoki mp3 bo'lmasa, ffmpeg bilan tezkor MP3 ga o'tkazish
    if path.suffix.lower() not in {".m4a", ".mp3"}:
        mp3_path = path.with_suffix(".mp3")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(path),
                    "-vn", "-codec:a", "libmp3lame",
                    "-b:a", "192k", "-threads", "0",
                    str(mp3_path)
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            path = mp3_path
        except Exception as e:
            log.warning("ffmpeg bilan MP3 ga o'tkazishda xatolik: %s", e)

    return info, path


def search_youtube_videos(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    YouTube bo'yicha musiqa/video qidirish.
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
