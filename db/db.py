"""Database initialization and schema management.

This module owns the SQLite DB path and setup logic, separating persistence concerns
from the Flask application code.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Iterable

# Project root (parent of this directory)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "db" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
OLD_DB_PATH = BASE_DIR / "app.db"

USER_TABLE_DDL = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    company_name TEXT,
    company_description TEXT,
    assistant_name TEXT,
    background_image TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

# Columns that may be added over time (id/username/password_hash always exist)
OPTIONAL_COLUMNS = [
    "email",
    "company_name",
    "company_description",
    "assistant_name",
    "background_image",
    "logo_image",
]


def init_db() -> None:
    """Create the database if missing, else ensure schema compatibility."""
    # Migrate legacy DB if present at project root
    if OLD_DB_PATH.exists() and not DB_PATH.exists():
        try:
            OLD_DB_PATH.replace(DB_PATH)
        except Exception:
            # If move fails, we'll just create a fresh DB at new location
            pass
    if DB_PATH.exists():
        ensure_schema()
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(USER_TABLE_DDL)
    conn.commit()
    conn.close()


def ensure_schema() -> None:
    """Add any missing optional columns to the users table.

    Safe to call on every startup; only applies ALTERs when needed.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cur.fetchall()}
    to_add: Iterable[str] = [col for col in OPTIONAL_COLUMNS if col not in existing]
    for col in to_add:
        cur.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    if to_add:
        conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """Return a raw sqlite3 connection (non-Flask context)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["DB_PATH", "init_db", "ensure_schema", "get_connection"]
