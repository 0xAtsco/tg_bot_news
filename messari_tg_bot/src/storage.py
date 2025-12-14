import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    published_at TEXT
);
"""


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def is_processed(self, item_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT 1 FROM processed_items WHERE id = ?", (item_id,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def mark_processed(self, item_id: str, item_type: str, published_at: Optional[str]) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO processed_items (id, type, published_at) VALUES (?, ?, ?)",
                (item_id, item_type, published_at),
            )
            conn.commit()
        finally:
            conn.close()
