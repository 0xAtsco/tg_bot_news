# Telegram Bot для Substack постов

Бот автоматически получает посты из Substack, переводит их на русский язык, создает TLDR и отправляет в ваш Telegram.

## Что делает бот

1. Получает посты из нескольких Substack фидов (список в `messari_tg_bot/feeds.json`)
2. **Загружает полный текст статьи** с оригинального URL (не только summary из RSS)
3. Переводит полную статью на русский язык через OpenRouter API
4. Создает краткое резюме (TLDR) из 3-7 пунктов на русском
5. Отправляет в Telegram:
   - Текстовое сообщение с TLDR и ссылкой на оригинал
   - **DOCX файл с полным переводом статьи** (красиво отформатированный)

## Надежность

Бот имеет встроенную защиту от временных проблем:
- **Retry логика для OpenRouter API**: автоматически повторяет запросы до 3 раз с экспоненциальной задержкой (1с, 2с, 4с)
- **Retry логика для Telegram API**: автоматически повторяет отправку сообщений при сбоях сети
- **Retry логика для загрузки статей**: повторяет попытки получить полный текст при сетевых ошибках
- **Обработка ошибок**: если один пост не удалось обработать, бот пропускает его и продолжает работу
- **Устойчивость к сбоям RSS**: если фид недоступен, бот просто пропускает его
- **Fallback**: если не удалось загрузить полную статью с URL, использует контент из RSS

## Быстрый старт

### 1. Запуск бота

Бот уже настроен и готов к работе. Запустите его:

```bash
# Активировать виртуальное окружение
source .venv/bin/activate

# Запустить один раз (обработает до 10 постов за последние 7 дней)
python -m messari_tg_bot.src.main --once

# Запустить в режиме цикла (каждые 10 минут проверяет новые посты)
python -m messari_tg_bot.src.main
```

### 2. Тестовый запуск (без отправки в Telegram)

```bash
# Dry-run режим - показывает что будет отправлено, но не отправляет
python -m messari_tg_bot.src.main --once --dry-run
```

## Настройки

Все настройки в файле `messari_tg_bot/.env`:

```env
# Telegram настройки (уже настроены)
TELEGRAM_BOT_TOKEN=ваш_токен
TELEGRAM_CHAT_ID=ваш_chat_id

# OpenRouter API для перевода (уже настроен)
OPENROUTER_API_KEY=ваш_ключ
TRANSLATOR_MODE=prod  # prod - использует API, dev - заглушки

# Настройки работы бота
POLL_INTERVAL_MIN=10          # Интервал проверки новых постов (в минутах)
BOOTSTRAP_LOOKBACK_HOURS=168  # Искать посты за последние 7 дней
MAX_ITEMS_PER_RUN=10          # Макс. постов за один запуск

# Модели для перевода
OPENROUTER_TRANSLATE_MODEL=mistralai/mixtral-8x7b-instruct
OPENROUTER_TLDR_MODEL=mistralai/mixtral-8x7b-instruct
```

## Список Substack фидов

Редактируйте `messari_tg_bot/feeds.json`:

```json
{
  "research": [
    "https://messari.substack.com/feed"
  ],
  "newsletter": [
    "https://defi0xjeff.substack.com/feed",
    "https://a16zcrypto.substack.com/feed",
    ...
  ]
}
```

## Полезные команды

```bash
# Очистить базу данных (чтобы повторно обработать старые посты)
rm messari_tg_bot/state.db

# Посмотреть созданные DOCX файлы
ls -lh messari_tg_bot/out/

# Посмотреть логи последнего запуска
python -m messari_tg_bot.src.main --once 2>&1 | tail -50
```

## Запуск в фоне (для постоянной работы)

### Вариант 1: screen

```bash
# Запустить в screen
screen -S telegram_bot
source .venv/bin/activate
python -m messari_tg_bot.src.main

# Отключиться: Ctrl+A, затем D
# Подключиться обратно: screen -r telegram_bot
```

### Вариант 2: nohup

```bash
nohup python -m messari_tg_bot.src.main > bot.log 2>&1 &
```

### Вариант 3: systemd (Linux)

Создайте файл `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Substack Bot
After=network.target

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/Users/absq/Desktop/deAI/tg_bot_news
ExecStart=/Users/absq/Desktop/deAI/tg_bot_news/.venv/bin/python -m messari_tg_bot.src.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## Структура проекта

```
tg_bot_news/
├── messari_tg_bot/
│   ├── .env                  # Настройки (токены, API ключи)
│   ├── feeds.json            # Список RSS/Atom фидов
│   ├── state.db              # База данных (дедупликация)
│   ├── out/                  # Созданные DOCX файлы
│   └── src/
│       ├── main.py           # Точка входа
│       ├── orchestrator.py   # Основная логика
│       ├── rss_client.py     # Получение RSS/Atom
│       ├── translator.py     # Перевод через OpenRouter
│       ├── telegram_client.py # Отправка в Telegram
│       └── docx_renderer.py  # Создание DOCX файлов
└── .venv/                    # Виртуальное окружение Python
```

## Формат сообщений в Telegram

```
#Newsletter
TLDR (RU):
- Первый пункт резюме...
- Второй пункт резюме...
- Третий пункт резюме...
Original: https://example.substack.com/p/post-title

+ DOCX файл с полным переводом
```

## Форматирование DOCX

Созданные DOCX файлы имеют профессиональное форматирование:
- Заголовок статьи (крупный, жирный шрифт)
- Метаданные (дата публикации, тип, ссылка на оригинал)
- Структурированный контент:
  - Заголовки разделов
  - Списки (маркированные и нумерованные)
  - Ссылки (синие, подчеркнутые)
  - Временные метки (для подкастов)
- Читаемые абзацы с нормальным межстрочным интервалом

## Поддержка

Проект работает и готов к использованию! Если нужны изменения:
- Изменить список фидов: отредактируйте `messari_tg_bot/feeds.json`
- Изменить настройки: отредактируйте `messari_tg_bot/.env`
- Изменить качество перевода: измените модели в `.env` файле
