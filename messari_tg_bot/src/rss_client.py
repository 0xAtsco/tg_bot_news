import logging
import ssl
import urllib.request
from typing import Dict, List

import certifi
import feedparser

logger = logging.getLogger(__name__)


class RSSClient:
    def __init__(self) -> None:
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.handlers = [urllib.request.HTTPSHandler(context=self.ssl_context)]

    def fetch_entries(self, url: str) -> List[Dict]:
        parsed = feedparser.parse(
            url,
            request_headers={
                "User-Agent": "Mozilla/5.0 (feed-fetcher; +https://github.com/kurtmckee/feedparser)"
            },
            handlers=self.handlers,
        )
        entries = parsed.get("entries", [])
        status = parsed.get("status")
        bozo = getattr(parsed, "bozo", False)
        if status and status >= 400:
            logger.warning("Feed %s returned status %s", url, status)
        if bozo:
            logger.warning("Feed %s bozo=%s error=%s", url, bozo, getattr(parsed, "bozo_exception", None))
        logger.info("Feed %s: %s entries", url, len(entries))
        return entries
