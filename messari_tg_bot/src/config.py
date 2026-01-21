import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

from dotenv import load_dotenv


# Source URL to hashtag mapping
SOURCE_HASHTAGS: Dict[str, str] = {
    "messari.substack.com": "#Messari",
    "anchor.fm": "#AnchorFm",
    "defi0xjeff.substack.com": "#DeFi0xJeff",
    "degencamp.substack.com": "#DegenCamp",
    "no-bs-ai.substack.com": "#NoBSAI",
    "a16zcrypto.substack.com": "#a16zCrypto",
    "nystrom.substack.com": "#Nystrom",
    "cryptocomresearch.substack.com": "#CryptoCom",
    "hacker-news": "#HackerNews",
}


def get_source_hashtag(url: str) -> str:
    """Get hashtag for a source URL."""
    for source_domain, hashtag in SOURCE_HASHTAGS.items():
        if source_domain in url.lower():
            return hashtag
    return "#Unknown"


@dataclass
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_channel_id: Optional[str] = None
    research_feeds: List[str] = field(default_factory=list)
    newsletter_feeds: List[str] = field(default_factory=list)
    openrouter_api_key: str = ""
    openrouter_translate_model: str = "mistralai/mixtral-8x7b-instruct"
    openrouter_tldr_model: str = "mistralai/mixtral-8x7b-instruct"
    poll_interval_minutes: int = 10
    bootstrap_lookback_hours: int = 24
    max_items_per_run: int = 20
    research_tags: List[str] = field(default_factory=list)
    newsletter_source_types: List[str] = field(default_factory=list)
    newsletter_source_ids: List[str] = field(default_factory=list)
    newsletter_asset_ids: List[str] = field(default_factory=list)
    translator_mode: str = "dev"
    environment: str = "dev"
    hn_enabled: bool = False
    hn_max_stories: int = 5


def _parse_csv(value: str) -> List[str]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return parts


def load_settings() -> Settings:
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    feeds_from_file = _load_feeds_file(base_dir)

    required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    if not feeds_from_file:
        required_vars.extend(["RESEARCH_FEEDS", "NEWSLETTER_FEEDS"])

    missing = [env for env in required_vars if not os.getenv(env)]
    if missing:
        missing_list = ", ".join(missing)
        raise EnvironmentError(f"Missing required environment variables: {missing_list}")

    research_feeds: List[str]
    newsletter_feeds: List[str]
    if feeds_from_file:
        research_feeds, newsletter_feeds = feeds_from_file
    else:
        research_feeds = _parse_csv(os.environ["RESEARCH_FEEDS"])
        newsletter_feeds = _parse_csv(os.environ["NEWSLETTER_FEEDS"])

    return Settings(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
        telegram_channel_id=os.getenv("TELEGRAM_CHANNEL_ID"),
        research_feeds=research_feeds,
        newsletter_feeds=newsletter_feeds,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_translate_model=os.getenv(
            "OPENROUTER_TRANSLATE_MODEL", "mistralai/mixtral-8x7b-instruct"
        ),
        openrouter_tldr_model=os.getenv("OPENROUTER_TLDR_MODEL", "mistralai/mixtral-8x7b-instruct"),
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MIN", "10")),
        bootstrap_lookback_hours=int(os.getenv("BOOTSTRAP_LOOKBACK_HOURS", "24")),
        max_items_per_run=int(os.getenv("MAX_ITEMS_PER_RUN", "20")),
        research_tags=_parse_csv(os.getenv("RESEARCH_TAGS", "")),
        newsletter_source_types=_parse_csv(os.getenv("NEWSLETTER_SOURCE_TYPES", "")),
        newsletter_source_ids=_parse_csv(os.getenv("NEWSLETTER_SOURCE_IDS", "")),
        newsletter_asset_ids=_parse_csv(os.getenv("NEWSLETTER_ASSET_IDS", "")),
        translator_mode=os.getenv("TRANSLATOR_MODE", "dev"),
        environment=os.getenv("ENVIRONMENT", "dev"),
        hn_enabled=os.getenv("HN_ENABLED", "false").lower() in ("true", "1", "yes"),
        hn_max_stories=int(os.getenv("HN_MAX_STORIES", "5")),
    )


def _load_feeds_file(base_dir: Path) -> List[List[str]] | None:
    feeds_path = base_dir / "feeds.json"
    if not feeds_path.exists():
        return None
    data = json.loads(feeds_path.read_text())
    research = data.get("research", []) or []
    newsletter = data.get("newsletter", []) or []
    return [research, newsletter]
