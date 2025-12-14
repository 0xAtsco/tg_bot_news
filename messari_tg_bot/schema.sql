CREATE TABLE IF NOT EXISTS processed_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    published_at TEXT
);
