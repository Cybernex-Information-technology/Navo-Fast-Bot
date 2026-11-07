import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Adminlar ID ro'yxati (vergul bilan ajratilgan, masalan: 12345678,87654321)
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = set()
if raw_admins:
    for aid in raw_admins.split(","):
        aid = aid.strip()
        if aid.isdigit():
            ADMIN_IDS.add(int(aid))

# Ijtimoiy tarmoqlar va brending
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "@navofast_bot").strip()
if not BOT_USERNAME.startswith("@") and BOT_USERNAME:
    BOT_USERNAME = f"@{BOT_USERNAME}"
TEAM_NAME = os.getenv("TEAM_NAME", "CyberNexTeam").strip()

# Ma'lumotlar bazasi
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "bot.db")).strip()

# yt-dlp proksi va cookie sozlamalari (server bloklanishining oldini olish uchun)
YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip() or None
COOKIES_FILE = os.getenv("COOKIES_FILE", "").strip() or None
if COOKIES_FILE and not Path(COOKIES_FILE).is_file():
    COOKIES_FILE = None

# Cheklovlar
MAX_BYTES = 49 * 1024 * 1024  # Telegram Bot API limiti (50 MB)
MAX_AUDIO_MINUTES = 25
CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "4"))
