FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies separately to leverage Docker layer caching.
COPY messari_tg_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy source code.
COPY messari_tg_bot /app/messari_tg_bot

# Ensure runtime directories exist.
RUN mkdir -p /app/messari_tg_bot/out

CMD ["python", "-m", "messari_tg_bot.src.main"]
