"""
Fayl o'lchamlari va parametrlarini tekshirish (ffprobe)
hamda videoni Telegram Dumaloq video (Video Note / Teleskop) formatiga o'tkazish.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger("media_probe")


def probe_video_dimensions(file_path: Path) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Videoning haqiqiy eni (width), bo'yi (height) va davomiyligini (duration)
    ffprobe orqali aniqlaydi. Rotatsiyani hisobga oladi (vertikal videolar uchun).
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:stream_tags=rotate:stream_side_data=rotation",
            "-of", "json",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None, None, None

        stream = streams[0]
        width = stream.get("width")
        height = stream.get("height")
        duration = stream.get("duration")
        duration_sec = int(float(duration)) if duration else None

        # Rotatsiya tekshiruvi (90 yoki 270 bo'lsa width va height almashadi)
        rotate = stream.get("tags", {}).get("rotate")
        if not rotate:
            side_data = stream.get("side_data_list", [])
            for sd in side_data:
                if "rotation" in sd:
                    rotate = sd["rotation"]
                    break

        if rotate in ("90", "270", 90, 270, "-90", "-270", -90, -270):
            if width and height:
                width, height = height, width

        return width, height, duration_sec
    except Exception as e:
        log.debug("ffprobe tekshiruvida ogohlantirish: %s", e)
        return None, None, None


def has_audio_stream(file_path: Path) -> bool:
    """Faylda audio oqimi mavjudligini tekshirish."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return "audio" in res.stdout
    except Exception:
        return False


def make_round_video_note(input_path: Path, output_path: Path) -> Path:
    """
    Videoni Telegram Dumaloq video (Teleskop / Video Note) formatiga o'tkazish:
    - 1:1 kvadratga markaziy proporsiyada kesish (480x480)
    - Maksimal 60 soniya (Telegram Video Note cheklovi)
    - H.264 video codec, YUV420P rang formati (barcha telefonlarda qotmasdan ochilishi uchun)
    - AAC audio codec (agar videoda ovoz bo'lmasa xato bermasdan sokin audio qo'shish)
    - faststart flagi (Telegramda video note darhol yuklanib aylanishi uchun)
    """
    has_audio = has_audio_stream(input_path)

    if has_audio:
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-t", "60",
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-movflags", "+faststart",
            str(output_path)
        ]
    else:
        # Ovoz bo'lmagan videolarga sokin audio qo'shish (Telegram video note qabul qilishi uchun)
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", "60",
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            "-c:a", "aac", "-b:a", "64k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]

    subprocess.run(cmd, check=True, capture_output=True, timeout=90)
    return output_path


def compress_video_to_size(
    input_path: Path,
    output_path: Path,
    target_bytes: int = 48 * 1024 * 1024,
    duration_sec: Optional[int] = None,
) -> bool:
    """
    Video hajmi Telegram bot limitidan (50 MB) oshib ketganda,
    uni sifatini maksimal saqlab 48 MB gacha siqadi.
    """
    try:
        if not duration_sec:
            _, _, duration_sec = probe_video_dimensions(input_path)
        if not duration_sec or duration_sec <= 0:
            duration_sec = 60

        # Bitrateni hisoblash
        total_bitrate_kbps = int((target_bytes * 8) / (duration_sec * 1024))
        audio_bitrate_kbps = 96
        video_bitrate_kbps = max(total_bitrate_kbps - audio_bitrate_kbps, 200)

        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", "scale='min(1080,iw)':-2,format=yuv420p",
            "-c:v", "libx264", "-b:v", f"{video_bitrate_kbps}k", "-maxrate", f"{int(video_bitrate_kbps * 1.3)}k",
            "-bufsize", f"{video_bitrate_kbps * 2}k",
            "-preset", "veryfast",
            "-c:a", "aac", "-b:a", f"{audio_bitrate_kbps}k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return output_path.is_file() and output_path.stat().st_size <= target_bytes
    except Exception as e:
        log.warning("Video siqishda xatolik: %s", e)
        return False
