import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
import calendar
from email.utils import parsedate_to_datetime


from .article_fetcher import ArticleFetcher
from .config import Settings
from .docx_renderer import ContentPayload, DocxRenderer
from .hn_client import HNClient, HNStory
from .rss_client import RSSClient
from .storage import Storage
from .telegram_client import TelegramClient
from .translator import Translator


logger = logging.getLogger(__name__)


@dataclass
class ProcessedItem:
    item_id: str
    slug: str
    title: str
    url: str
    publish_date: datetime
    content: str
    item_type: str  # research | newsletter | hn


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        rss_client: RSSClient,
        article_fetcher: ArticleFetcher,
        translator: Translator,
        docx_renderer: DocxRenderer,
        telegram_client: TelegramClient,
        hn_client: Optional[HNClient] = None,
    ):
        self.settings = settings
        self.storage = storage
        self.rss_client = rss_client
        self.article_fetcher = article_fetcher
        self.translator = translator
        self.docx_renderer = docx_renderer
        self.telegram_client = telegram_client
        self.hn_client = hn_client

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.poll_interval_minutes * 60)

    async def run_once(self) -> None:
        logger.info("Starting poll cycle")
        remaining = self.settings.max_items_per_run
        processed_total = 0

        processed_research = await self._process_research(remaining)
        processed_total += processed_research
        remaining -= processed_research

        if remaining > 0:
            processed_news = await self._process_newsletters(remaining)
            processed_total += processed_news
            remaining -= processed_news

        if remaining > 0 and self.hn_client and self.settings.hn_enabled:
            processed_hn = await self._process_hacker_news(remaining)
            processed_total += processed_hn

        logger.info("Poll cycle complete; processed %s items", processed_total)

    async def _process_research(self, limit: int) -> int:
        lookback = datetime.now(timezone.utc) - timedelta(hours=self.settings.bootstrap_lookback_hours)
        processed_count = 0

        entries = self._fetch_from_urls(self.settings.research_feeds)
        for entry in entries:
            if processed_count >= limit:
                break
            if self.settings.research_tags and not self._passes_filters(
                entry, self.settings.research_tags
            ):
                continue
            publish_date = self._entry_date(entry)
            if publish_date and publish_date < lookback:
                logger.debug("Skip (old): %s", entry.get("title"))
                continue

            entry_id = entry.get("id") or entry.get("link") or entry.get("title")
            if not entry_id or self.storage.is_processed(entry_id):
                continue

            try:
                # Get URL for full article fetch
                url = entry.get("link") or ""

                # Try to fetch full article from URL
                full_article = None
                if url:
                    logger.info(f"Fetching full article from {url}")
                    full_article = await self.article_fetcher.fetch_full_article(url)

                # Fallback to RSS content if article fetch failed
                if not full_article:
                    logger.info(f"Using RSS content for research: {entry.get('title')}")
                    full_article = self._entry_content(entry)

                # Translate and summarize
                translated_full = await self.translator.translate_full_text(full_article)
                bullets = await self.translator.summarize_to_bullets(full_article)

                item = ProcessedItem(
                    item_id=entry_id,
                    slug=self._slug(entry),
                    title=entry.get("title") or "Без названия",
                    url=entry.get("link") or "",
                    publish_date=publish_date or datetime.now(timezone.utc),
                    content=translated_full,
                    item_type="research",
                )

                await self._deliver_item(item, bullets)
                if not self.telegram_client.dry_run:
                    self.storage.mark_processed(item.item_id, item.item_type, item.publish_date.isoformat())
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process research entry '{entry.get('title')}': {e}", exc_info=True)
                continue

        return processed_count

    async def _process_newsletters(self, limit: int) -> int:
        lookback = datetime.now(timezone.utc) - timedelta(hours=self.settings.bootstrap_lookback_hours)
        processed_count = 0

        entries = self._fetch_from_urls(self.settings.newsletter_feeds)
        for entry in entries:
            if processed_count >= limit:
                break
            if self.settings.newsletter_source_types and not self._passes_filters(
                entry, self.settings.newsletter_source_types
            ):
                continue
            publish_date = self._entry_date(entry)
            if publish_date and publish_date < lookback:
                logger.debug("Skip (old): %s", entry.get("title"))
                continue

            entry_id = entry.get("id") or entry.get("link") or entry.get("title")
            if not entry_id or self.storage.is_processed(entry_id):
                continue

            try:
                # Get URL for full article fetch
                url = entry.get("link") or ""

                # Try to fetch full article from URL
                full_article = None
                if url:
                    logger.info(f"Fetching full article from {url}")
                    full_article = await self.article_fetcher.fetch_full_article(url)

                # Fallback to RSS content if article fetch failed
                if not full_article:
                    logger.info(f"Using RSS content for newsletter: {entry.get('title')}")
                    full_article = self._entry_content(entry)

                # Translate and summarize
                translated_full = await self.translator.translate_full_text(full_article)
                bullets = await self.translator.summarize_to_bullets(full_article)

                item = ProcessedItem(
                    item_id=entry_id,
                    slug=self._slug(entry),
                    title=entry.get("title") or "Без названия",
                    url=entry.get("link") or "",
                    publish_date=publish_date or datetime.now(timezone.utc),
                    content=translated_full,
                    item_type="newsletter",
                )

                await self._deliver_item(item, bullets)
                if not self.telegram_client.dry_run:
                    self.storage.mark_processed(item.item_id, item.item_type, item.publish_date.isoformat())
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process newsletter entry '{entry.get('title')}': {e}", exc_info=True)
                continue

        return processed_count

    async def _process_hacker_news(self, limit: int) -> int:
        if not self.hn_client:
            return 0

        processed_count = 0
        stories = self.hn_client.fetch_newest_stories(limit)

        for story in stories:
            if processed_count >= limit:
                break

            entry_id = f"hn_{story.id}"
            if self.storage.is_processed(entry_id):
                continue

            try:
                url = story.url or f"https://news.ycombinator.com/item?id={story.id}"

                full_article = None
                if story.url:
                    logger.info(f"Fetching full article from {url}")
                    full_article = await self.article_fetcher.fetch_full_article(url)

                if not full_article:
                    full_article = story.title

                translated_full = await self.translator.translate_full_text(full_article)
                bullets = await self.translator.summarize_to_bullets(full_article)

                publish_date = datetime.fromtimestamp(story.time, tz=timezone.utc)

                item = ProcessedItem(
                    item_id=entry_id,
                    slug=f"hn_{story.id}",
                    title=story.title or "Без названия",
                    url=url,
                    publish_date=publish_date,
                    content=translated_full,
                    item_type="hn",
                )

                await self._deliver_item(item, bullets)
                if not self.telegram_client.dry_run:
                    self.storage.mark_processed(item.item_id, item.item_type, item.publish_date.isoformat())
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process HN story '{story.title}': {e}", exc_info=True)
                continue

        return processed_count

    async def _deliver_item(self, item: ProcessedItem, bullets: List[str]) -> None:
        if item.item_type == "research":
            header = "#Research"
        elif item.item_type == "newsletter":
            header = "#Newsletter"
        else:
            header = "#HackerNews"

        bullet_lines = "\n".join(f"- {bullet}" for bullet in bullets[:7])
        message = f"{header}\nTLDR (RU):\n{bullet_lines}\nOriginal: {item.url}"

        await self.telegram_client.send_text(message)
        payload = ContentPayload(
            item_id=item.item_id,
            slug=item.slug,
            title=item.title,
            url=item.url,
            publish_date=item.publish_date,
            item_type=item.item_type,  # type: ignore[arg-type]
            translated_content=item.content,
        )
        docx_path = self.docx_renderer.render(payload)
        await self.telegram_client.send_document(docx_path)

    @staticmethod
    def _entry_date(entry: dict) -> Optional[datetime]:
        try:
            if "published_parsed" in entry and entry["published_parsed"]:
                return datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)
            if "updated_parsed" in entry and entry["updated_parsed"]:
                return datetime.fromtimestamp(calendar.timegm(entry.updated_parsed), tz=timezone.utc)
            if "published" in entry and entry["published"]:
                return parsedate_to_datetime(entry["published"]).astimezone(timezone.utc)
            if "updated" in entry and entry["updated"]:
                return parsedate_to_datetime(entry["updated"]).astimezone(timezone.utc)
        except Exception:
            logger.warning("Failed to parse date for entry: %s", entry.get("title"))
        return None

    @staticmethod
    def _entry_content(entry: dict) -> str:
        if "content" in entry and entry["content"]:
            content_list = entry["content"]
            if isinstance(content_list, list) and content_list:
                return content_list[0].get("value", "") or ""
        return entry.get("summary") or entry.get("description") or ""

    @staticmethod
    def _slug(entry: dict) -> str:
        link = entry.get("link") or ""
        if link:
            return link.rstrip("/").split("/")[-1][:80]
        title = entry.get("title") or ""
        return title[:80] or "item"

    @staticmethod
    def _passes_filters(entry: dict, keywords: List[str]) -> bool:
        haystack = f"{entry.get('title','')} {entry.get('summary','')} {entry.get('description','')}".lower()
        return any(keyword.lower() in haystack for keyword in keywords)

    def _fetch_from_urls(self, urls: List[str]) -> List[dict]:
        items: List[dict] = []
        for url in urls:
            try:
                entries = self.rss_client.fetch_entries(url)
                items.extend(entries)
                if not entries:
                    logger.warning("Feed %s returned 0 entries", url)
                else:
                    first_date = self._entry_date(entries[0])
                    logger.info(
                        "Feed %s latest date: %s",
                        url,
                        first_date.isoformat() if first_date else "unknown",
                    )
            except Exception:
                logger.exception("Failed to fetch feed %s", url)
        return items
