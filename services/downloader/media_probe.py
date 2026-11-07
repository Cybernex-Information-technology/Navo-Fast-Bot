"""
Fayl o'lchamlari va parametrlarini tekshirish (ffprobe).
Videoni qora hoshiyasiz (black bars) va buzilmagan (squished/stretched) 
asl vertikal/gorizontal holatda Telegramda to'g'ri ko'rsatishni ta'minlaydi.
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
    ffprobe orqali aniqlaydi. Agar video 90 yoki 270 darajaga aylantirilgan bo'lsa,
    o'lchamlarni avtomatik to'g'rilaydi.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:stream_tags=rotate",
            "-of", "json",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None, None, None

        stream = streams[0]
        width = stream.get("width")
        height = stream.get("height")
        duration = stream.get("duration")
        duration_sec = int(float(duration)) if duration else None

        # Rotatsiya (Instagram va TikTok vertikal videolari ba'zan 90 yoki 270 teg bilan keladi)
        rotate = stream.get("tags", {}).get("rotate") or stream.get("rotation")
        if rotate in ("90", "270", 90, 270, "-90", "-270", -90, -270):
            width, height = height, width

        return width, height, duration_sec
    except Exception as e:
        log.debug("ffprobe bilan tekshirishda ogohlantirish (avtomatik rejimga o'tildi): %s", e)
        return None, None, None
