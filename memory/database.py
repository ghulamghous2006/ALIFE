"""SQLite database setup and connection management for ALIFE."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "alife.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Database:
    """Manages the ALIFE SQLite database."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        """Initialize the database connection manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = Path(db_path)
        self.initialize()

    @property
    def db_path(self) -> Path:
        """Return the configured database file path."""
        return self._db_path

    def initialize(self) -> None:
        """Create the database file and tables if they do not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as conn:
            conn.executescript(SCHEMA)

        logger.info("Database initialized at %s", self._db_path)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a transactional database connection.

        Yields:
            An open SQLite connection with row factory enabled.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
