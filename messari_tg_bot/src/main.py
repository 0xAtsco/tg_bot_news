import argparse
import asyncio
import logging
from pathlib import Path

from .article_fetcher import ArticleFetcher
from .config import load_settings
from .docx_renderer import DocxRenderer
from .orchestrator import Orchestrator
from .rss_client import RSSClient
from .storage import Storage
from .telegram_client import TelegramClient
from .translator import Translator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Messari -> Telegram relay bot")
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending messages")
    return parser


async def async_main() -> None:
    args = build_arg_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = load_settings()

    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "state.db"
    output_dir = project_root / "out"

    storage = Storage(db_path=db_path)
    rss_client = RSSClient()
    article_fetcher = ArticleFetcher()
    translator = Translator(
        mode=settings.translator_mode,
        openrouter_api_key=settings.openrouter_api_key,
        translate_model=settings.openrouter_translate_model,
        tldr_model=settings.openrouter_tldr_model,
    )
    docx_renderer = DocxRenderer(output_dir=output_dir)
    telegram_client = TelegramClient(
        bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id, dry_run=args.dry_run
    )

    orchestrator = Orchestrator(
        settings=settings,
        storage=storage,
        rss_client=rss_client,
        article_fetcher=article_fetcher,
        translator=translator,
        docx_renderer=docx_renderer,
        telegram_client=telegram_client,
    )

    if args.once:
        await orchestrator.run_once()
    else:
        await orchestrator.run_forever()


if __name__ == "__main__":
    asyncio.run(async_main())
