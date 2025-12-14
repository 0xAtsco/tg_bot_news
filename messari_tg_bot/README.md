# RSS Telegram Bot (Research + Newsletter)

Этот бот опрашивает две RSS/Atom ленты (research + newsletter) и шлёт в Telegram русские TLDR-буллеты + `.docx` с полной переводной версией.

## Что делает
- Читает **Research feed** и **Newsletter feed** (RSS/Atom).
- Дедупликация в SQLite, безопасно при рестартах.
- Генерирует `.docx` через `python-docx`.
- Отправляет текст + файл через `python-telegram-bot`.
- `--dry-run` печатает, не шлёт.

> Ограничение: RSS/Atom часто содержат только `summary`. Полный текст в DOCX появится, если лента отдаёт `<content>` или подробный `<description>`.

## Setup
```bash
cd messari_tg_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in secrets
```

Environment variables (see `.env.example`):
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (обязательные).
- Ленты: либо через файл `feeds.json` (см. ниже), либо через env `RESEARCH_FEEDS`, `NEWSLETTER_FEEDS` (CSV). Если используете файл — можете оставить env пустыми.
- Тайминги: `POLL_INTERVAL_MIN`, `BOOTSTRAP_LOOKBACK_HOURS`, `MAX_ITEMS_PER_RUN`.
- Фильтры (поиск ключевых слов в title/summary): `RESEARCH_TAGS` (через запятую), `NEWSLETTER_SOURCE_TYPES` (тоже ключевые слова), `NEWSLETTER_SOURCE_IDS`, `NEWSLETTER_ASSET_IDS` (можно пустыми).
- Переводчик: `OPENROUTER_API_KEY`, `OPENROUTER_TRANSLATE_MODEL`, `OPENROUTER_TLDR_MODEL`, `TRANSLATOR_MODE=prod` для OpenRouter (`dev` — заглушка).

## Running
```bash
python -m messari_tg_bot.src.main --once        # single poll
python -m messari_tg_bot.src.main               # loop with interval
python -m messari_tg_bot.src.main --dry-run     # no Telegram sends
```

State/outputs:
- SQLite at `messari_tg_bot/state.db`.
- Generated docs in `messari_tg_bot/out/`.

## Tests
```bash
pytest messari_tg_bot/tests
```

## Translation & summaries
- `messari_tg_bot/src/translator.py` calls OpenRouter chat completions (`POST /api/v1/chat/completions`, `choices[0].message.content`) when `TRANSLATOR_MODE=prod`.
- Models: `OPENROUTER_TRANSLATE_MODEL`, `OPENROUTER_TLDR_MODEL` (defaults: `mistralai/mixtral-8x7b-instruct`).
- Requires `OPENROUTER_API_KEY`. If пусто — ошибка в прод-режиме. `dev` оставляет заглушку.

## feeds.json (опционально)
- Пример: `feeds.example.json`. Скопируйте в `feeds.json` и отредактируйте.
- Формат:
```json
{
  "research": ["https://example.com/research.xml"],
  "newsletter": ["https://example.com/news.xml"]
}
```
- Если файл есть — списки лент берутся из него, env `RESEARCH_FEEDS/NEWSLETTER_FEEDS` можно не задавать.

## File naming
- Research: `Messari_Research_<YYYY-MM-DD>_<slug_or_id>.docx`
- Newsletter: `Messari_Newsletter_<YYYY-MM-DD>_<id_or_slug>.docx`
