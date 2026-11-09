FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Tizim paketlari: FFmpeg (audio ajratish va video konvertatsiya uchun)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha kodlarini nusxalash
COPY core/ ./core/
COPY services/ ./services/
COPY scripts/ ./scripts/
COPY bot.py .

# Ma'lumotlar va vaqtinchalik papkalar
RUN mkdir -p /app/data /app/temp

CMD ["python", "bot.py"]
