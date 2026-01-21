# Telegram News Bot

Automatically fetches articles from RSS feeds, Hacker News, and other sources, translates them to Russian, creates TLDR summaries, and posts to your Telegram chat and channel.

## Features

1. **Multiple Sources**: Fetches from RSS feeds (Substack, blogs) and Hacker News
2. **Full Article Fetching**: Downloads complete article content (not just RSS summary)
3. **Translation**: Translates full articles to Russian via OpenRouter API
4. **TLDR Summaries**: Creates 3-7 bullet point summaries in Russian
5. **Dual Posting**: Sends to both personal chat and Telegram channel
6. **Error Handling**: Skips posts with error patterns (load errors, authorization pages)
7. **Hacker News Integration**: Includes HN discussion links for HN posts

## Message Format

### Regular Posts
```
#Newsletter
TLDR (RU):
- First bullet point...
- Second bullet point...
- Third bullet point...

Original: https://example.com/article
```

### Hacker News Posts
```
#HackerNews
TLDR (RU):
- First bullet point...
- Second bullet point...

Original: https://example.com/article
HN Discussion: https://news.ycombinator.com/item?id=12345
```

## Quick Start with Docker

### 1. Configure Environment

Edit `messari_tg_bot/.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_CHANNEL_ID=@your_channel  # Optional, for public channel posting

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_TRANSLATE_MODEL=mistralai/devstral-2512:free
OPENROUTER_TLDR_MODEL=mistralai/devstral-2512:free

# Bot Settings
POLL_INTERVAL_MIN=10          # Check interval in minutes
BOOTSTRAP_LOOKBACK_HOURS=168  # Look back period in hours
MAX_ITEMS_PER_RUN=10          # Max items per run
TRANSLATOR_MODE=prod          # prod=real translation, dev=stubs

# Hacker News Integration
HN_ENABLED=true
HN_MAX_STORIES=5
```

### 2. Configure Feeds

Edit `messari_tg_bot/feeds.json`:

```json
{
  "research": [
    "https://messari.substack.com/feed"
  ],
  "newsletter": [
    "https://defi0xjeff.substack.com/feed",
    "https://a16zcrypto.substack.com/feed",
    "https://cryptocomresearch.substack.com/feed",
    "https://nystrom.substack.com/feed"
  ]
}
```

### 3. Run with Docker Compose

```bash
docker-compose up -d --build
```

### 4. View Logs

```bash
docker-compose logs -f
```

## Error Handling

The bot automatically skips posts with error patterns in summaries:
- "произошла ошибка при загрузке" (loading error)
- "необходимо перезагрузить страницу" (please refresh page)
- "для изменения настроек уведомлений требуется авторизация" (authorization required)
- "error occurred", "please refresh", "authorization required"

## Reliability Features

- **Retry Logic**: Up to 3 retries with exponential backoff (1s, 2s, 4s) for:
  - OpenRouter API calls
  - Telegram API messages
  - Article fetching
- **Graceful Failure**: If one post fails, the bot continues with others
- **RSS Resilience**: Skips unavailable feeds without crashing
- **Fallback**: Uses RSS content if full article fetch fails

## Advanced Configuration

### Add Bot to Channel

To post to a Telegram channel:

1. Add your bot as an administrator to the channel
2. Grant "Posting Messages" permission
3. Set `TELEGRAM_CHANNEL_ID=@your_channel` in `.env`

### Test Mode (Dry Run)

```bash
docker-compose run tg-bot python -m messari_tg_bot.src.main --once --dry-run
```

### Run Once

```bash
docker-compose run tg-bot python -m messari_tg_bot.src.main --once
```

## Project Structure

```
tg_bot_news/
├── messari_tg_bot/
│   ├── .env                  # Configuration (tokens, API keys)
│   ├── feeds.json            # RSS/Atom feed list
│   ├── state.db              # SQLite database (deduplication)
│   ├── data/
│   │   └── state.db         # Persistent state
│   └── src/
│       ├── main.py           # Entry point
│       ├── orchestrator.py   # Main logic
│       ├── config.py         # Configuration loader
│       ├── rss_client.py     # RSS/Atom fetching
│       ├── hn_client.py      # Hacker News API client
│       ├── translator.py     # OpenRouter translation
│       ├── article_fetcher.py # Article content fetching
│       └── telegram_client.py # Telegram posting
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker image definition
└── requirements.txt         # Python dependencies
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `TELEGRAM_CHAT_ID` | Personal chat ID | Yes |
| `TELEGRAM_CHANNEL_ID` | Channel username (@channel) | No |
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |
| `TRANSLATOR_MODE` | `prod` or `dev` | No |
| `POLL_INTERVAL_MIN` | Polling interval in minutes | No |
| `BOOTSTRAP_LOOKBACK_HOURS` | Initial lookback period | No |
| `MAX_ITEMS_PER_RUN` | Max items per run | No |
| `HN_ENABLED` | Enable Hacker News | No |
| `HN_MAX_STORIES` | Max HN stories per run | No |

## API Models

Recommended OpenRouter models (free tier available):

```env
OPENROUTER_TRANSLATE_MODEL=mistralai/devstral-2512:free
OPENROUTER_TLDR_MODEL=mistralai/devstral-2512:free
```

Other options:
- `mistralai/mixtral-8x7b-instruct`
- `anthropic/claude-3-haiku`
- `google/gemini-pro`

## Troubleshooting

### Bot can't post to channel
- Add bot as channel administrator
- Grant "Posting Messages" permission
- Verify `TELEGRAM_CHANNEL_ID` format (@channelname)

### Articles not translating
- Check OpenRouter API key is valid
- Verify `TRANSLATOR_MODE=prod`
- Check OpenRouter API credits

### Hacker News not working
- Verify `HN_ENABLED=true`
- Check logs for HN API errors

### Reset database
```bash
rm messari_tg_bot/state.db
docker-compose restart
```

## Development

### Run locally

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r messari_tg_bot/requirements.txt

# Run
python -m messari_tg_bot.src.main
```

### Run tests

```bash
pytest messari_tg_bot/tests/
```

## License

MIT License
