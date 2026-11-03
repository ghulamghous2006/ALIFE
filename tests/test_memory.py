"""Tests for long-term memory management."""

import tempfile
import unittest
from pathlib import Path

from memory.database import Database
from memory.memory_manager import MemoryManager


class TestMemoryManager(unittest.TestCase):
    """Unit tests for MemoryManager."""

    def setUp(self) -> None:
        """Create isolated memory manager for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test_alife.db")
        self.memory_manager = MemoryManager(self.database)

    def tearDown(self) -> None:
        """Remove temporary test data."""
        self.temp_dir.cleanup()

    def test_save_memory(self) -> None:
        """Saving a memory should persist it to the database."""
        memory = self.memory_manager.save_memory("My favorite language is Java")

        self.assertEqual(memory.content, "My favorite language is Java")
        self.assertGreater(memory.id, 0)

    def test_get_memories(self) -> None:
        """get_memories should return all saved memories."""
        self.memory_manager.save_memory("Memory one")
        self.memory_manager.save_memory("Memory two")

        memories = self.memory_manager.get_memories()

        self.assertEqual(len(memories), 2)
        self.assertEqual(memories[0].content, "Memory one")
        self.assertEqual(memories[1].content, "Memory two")

    def test_search_memories(self) -> None:
        """search_memories should find relevant entries."""
        self.memory_manager.save_memory("My favorite language is Java")
        self.memory_manager.save_memory("I enjoy hiking on weekends")

        results = self.memory_manager.search_memories("Java")

        self.assertEqual(len(results), 1)
        self.assertIn("Java", results[0].content)

    def test_delete_memory(self) -> None:
        """delete_memory should remove a specific memory."""
        memory = self.memory_manager.save_memory("Temporary memory")

        deleted = self.memory_manager.delete_memory(memory.id)
        remaining = self.memory_manager.get_memories()

        self.assertTrue(deleted)
        self.assertEqual(remaining, [])

    def test_clear_memories(self) -> None:
        """clear_memories should remove all stored memories."""
        self.memory_manager.save_memory("Memory one")
        self.memory_manager.save_memory("Memory two")

        deleted_count = self.memory_manager.clear_memories()
        remaining = self.memory_manager.get_memories()

        self.assertEqual(deleted_count, 2)
        self.assertEqual(remaining, [])

    def test_memory_persistence(self) -> None:
        """Memories should persist across manager instances."""
        memory = self.memory_manager.save_memory("Persistent memory")
        reloaded_manager = MemoryManager(Database(self.database.db_path))

        memories = reloaded_manager.get_memories()

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].id, memory.id)
        self.assertEqual(memories[0].content, "Persistent memory")

    def test_empty_memory_is_rejected(self) -> None:
        """Empty memory content should raise ValueError."""
        with self.assertRaises(ValueError):
            self.memory_manager.save_memory("   ")


if __name__ == "__main__":
    unittest.main()
