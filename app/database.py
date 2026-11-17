import sqlite3
from pathlib import Path
from typing import Any
from config.settings import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT 'article',
            published_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')


def add_item(item: dict[str, Any]) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO content_items (title,url,source,summary,content_type,published_at,status) VALUES (?,?,?,?,?,?, 'pending')",
            (item['title'], item['url'], item['source'], item.get('summary', ''), item.get('content_type', 'article'), item.get('published_at')),
        )
        return cursor.rowcount == 1


def list_items(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as connection:
        if status:
            rows = connection.execute("SELECT * FROM content_items WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = connection.execute("SELECT * FROM content_items ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


def get_item(item_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None


def set_status(item_id: int, status: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute("UPDATE content_items SET status=? WHERE id=?", (status, item_id))
        return cursor.rowcount == 1
