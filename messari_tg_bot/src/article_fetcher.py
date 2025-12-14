import asyncio
import logging
from typing import Optional
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)


class ArticleFetcher:
    """Fetches full article content from URLs."""

    def __init__(self):
        self.timeout = 30.0

    async def fetch_full_article(self, url: str) -> Optional[str]:
        """
        Fetch full article content from URL.
        Returns cleaned article text or None if failed.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        url,
                        follow_redirects=True,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                                        "Chrome/120.0.0.0 Safari/537.36"
                        }
                    )
                    response.raise_for_status()

                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extract article content based on common patterns
                    article_text = self._extract_article_content(soup, url)

                    if article_text:
                        logger.info(f"Successfully fetched article from {url} ({len(article_text)} chars)")
                        return article_text
                    else:
                        logger.warning(f"No article content found at {url}")
                        return None

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Network error fetching article (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch article after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching article from {url}: {e}", exc_info=True)
                return None

        return None

    def _extract_article_content(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract article content from parsed HTML."""

        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try different content selectors based on common blog platforms
        content = None

        # Substack patterns
        if 'substack.com' in url:
            content = soup.find('div', class_='available-content')
            if not content:
                content = soup.find('div', class_='body')
            if not content:
                content = soup.find('article')

        # Spotify/Anchor podcasts
        elif 'spotify.com' in url or 'anchor.fm' in url:
            content = soup.find('div', class_='episode-description')
            if not content:
                content = soup.find('div', {'data-testid': 'episode-description'})
            if not content:
                # For podcast episodes, description might be in meta tags
                meta_desc = soup.find('meta', {'property': 'og:description'})
                if meta_desc:
                    return meta_desc.get('content', '')

        # Generic article patterns
        if not content:
            content = soup.find('article')
        if not content:
            content = soup.find('div', class_='post-content')
        if not content:
            content = soup.find('div', class_='entry-content')
        if not content:
            content = soup.find('main')

        if content:
            return self._clean_text(content.get_text(separator='\n', strip=True))

        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize article text."""
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Remove very short lines (likely navigation/UI elements)
        cleaned_lines = []
        for line in lines:
            # Keep lines that are substantial or are clearly part of content
            if len(line) > 20 or line.endswith(':') or line.endswith('.'):
                cleaned_lines.append(line)

        return '\n\n'.join(cleaned_lines)
