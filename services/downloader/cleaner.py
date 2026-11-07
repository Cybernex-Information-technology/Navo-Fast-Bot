"""
Vaqtinchalik fayllarni xavfsiz boshqarish va tozalash.
Server diski to'lib qolishining (disk leak) 100% oldini oladi.
"""
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from core.config import TEMP_DIR


@contextmanager
def temporary_directory(prefix: str = "navo_"):
    """Vazifa bajarilib bo'lgach avtomatik o'chadigan xavfsiz papka."""
    d = Path(tempfile.mkdtemp(prefix=prefix, dir=TEMP_DIR))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cleanup_old_temp_files(max_age_seconds: int = 3600):
    """Eski qolib ketgan fayllarni tozalash (masalan bot to'satdan o'chganda)."""
    now = time.time()
    for item in TEMP_DIR.iterdir():
        try:
            if item.is_dir() and item.name.startswith("navo_"):
                if now - item.stat().st_mtime > max_age_seconds:
                    shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                if now - item.stat().st_mtime > max_age_seconds:
                    item.unlink(missing_ok=True)
        except Exception:
            pass
