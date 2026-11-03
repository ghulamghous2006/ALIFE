"""Tests for SQLite database initialization."""

import tempfile
import unittest
from pathlib import Path

from memory.database import Database


class TestDatabase(unittest.TestCase):
    """Unit tests for database creation and schema."""

    def setUp(self) -> None:
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_alife.db"
        self.database = Database(self.db_path)

    def tearDown(self) -> None:
        """Remove the temporary database directory."""
        self.temp_dir.cleanup()

    def test_database_file_is_created(self) -> None:
        """Database file should be created automatically."""
        self.assertTrue(self.db_path.exists())

    def test_tables_exist(self) -> None:
        """Required tables should exist after initialization."""
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            ).fetchall()

        table_names = {row["name"] for row in rows}
        self.assertIn("conversation_messages", table_names)
        self.assertIn("memories", table_names)

    def test_reinitialize_preserves_existing_database(self) -> None:
        """Re-initializing an existing database should not fail."""
        Database(self.db_path)
        self.assertTrue(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
