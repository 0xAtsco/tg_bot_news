import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx


logger = logging.getLogger(__name__)


@dataclass
class HNStory:
    id: int
    title: str
    url: Optional[str]
    by: str
    time: int
    score: int
    descendants: int


class HNClient:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self) -> None:
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True
        )

    def fetch_newest_stories(self, limit: int = 10) -> List[HNStory]:
        """Fetch newest stories from Hacker News."""
        try:
            response = self.client.get("/newstories.json")
            response.raise_for_status()
            story_ids = response.json()
            
            stories = []
            for story_id in story_ids[:limit]:
                try:
                    story = self._fetch_story(story_id)
                    if story and story.url:  # Only include stories with URLs
                        stories.append(story)
                except Exception as e:
                    logger.warning(f"Failed to fetch story {story_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(stories)} stories from Hacker News")
            return stories
        except Exception as e:
            logger.error(f"Failed to fetch newest stories: {e}")
            return []

    def _fetch_story(self, story_id: int) -> Optional[HNStory]:
        """Fetch details of a single story."""
        try:
            response = self.client.get(f"/item/{story_id}.json")
            response.raise_for_status()
            data = response.json()
            
            if not data or data.get("type") != "story":
                return None
            
            return HNStory(
                id=data["id"],
                title=data.get("title", ""),
                url=data.get("url"),
                by=data.get("by", ""),
                time=data.get("time", 0),
                score=data.get("score", 0),
                descendants=data.get("descendants", 0),
            )
        except Exception as e:
            logger.error(f"Failed to fetch story {story_id}: {e}")
            return None

    def close(self) -> None:
        self.client.close()
