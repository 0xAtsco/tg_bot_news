from datetime import datetime, timezone
from pathlib import Path

from messari_tg_bot.src.storage import Storage


def test_storage_deduplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    storage = Storage(db_path)
    item_id = "abc123"
    assert storage.is_processed(item_id) is False

    storage.mark_processed(item_id, "research", datetime.now(timezone.utc).isoformat())
    assert storage.is_processed(item_id) is True
