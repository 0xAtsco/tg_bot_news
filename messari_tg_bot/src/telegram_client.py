import asyncio
import logging
from pathlib import Path
from typing import Optional

import telegram
from telegram.error import NetworkError, TimedOut

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, channel_id: Optional[str] = None, dry_run: bool = False):
        self.bot = telegram.Bot(bot_token)
        self.chat_id = chat_id
        self.channel_id = channel_id
        self.dry_run = dry_run

    async def send_text(self, text: str, to_channel: bool = False) -> None:
        target_id = self.channel_id if to_channel and self.channel_id else self.chat_id
        if self.dry_run:
            logger.info(f"[dry-run] Would send text message to {target_id}:\n%s", text)
            return

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.bot:
                    await self.bot.send_message(chat_id=target_id, text=text)
                return
            except (NetworkError, TimedOut) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Telegram network error (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send Telegram message after {max_retries} attempts: {e}")
                    raise

    async def send_document(self, file_path: Path, to_channel: bool = False) -> None:
        target_id = self.channel_id if to_channel and self.channel_id else self.chat_id
        if self.dry_run:
            logger.info(f"[dry-run] Would send document to {target_id}: %s", file_path)
            return

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.bot:
                    with file_path.open("rb") as f:
                        await self.bot.send_document(chat_id=target_id, document=f)
                return
            except (NetworkError, TimedOut) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Telegram network error sending document (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send Telegram document after {max_retries} attempts: {e}")
                    raise
