"""Long-term memory storage and retrieval for ALIFE."""

import logging
import re
from dataclasses import dataclass

from memory.database import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Memory:
    """A persisted long-term memory entry."""

    id: int
    content: str
    created_at: str


class MemoryManager:
    """Manages persistent long-term memories."""

    def __init__(self, database: Database) -> None:
        """Initialize the memory manager.

        Args:
            database: Shared database instance.
        """
        self._database = database

    def save_memory(self, content: str) -> Memory:
        """Save a new long-term memory.

        Args:
            content: Memory text to persist.

        Returns:
            The saved memory entry.

        Raises:
            ValueError: If content is empty or whitespace-only.
        """
        if not content.strip():
            raise ValueError("Memory content must not be empty.")

        with self._database.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO memories (content) VALUES (?)",
                (content.strip(),),
            )
            memory_id = int(cursor.lastrowid)
            row = conn.execute(
                "SELECT id, content, created_at FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()

        memory = Memory(id=row["id"], content=row["content"], created_at=row["created_at"])
        logger.info("Saved memory id=%s", memory.id)
        return memory

    def get_memories(self) -> list[Memory]:
        """Return all stored memories ordered by creation time.

        Returns:
            List of memory entries.
        """
        with self._database.connect() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at FROM memories ORDER BY id ASC"
            ).fetchall()

        return [
            Memory(id=row["id"], content=row["content"], created_at=row["created_at"])
            for row in rows
        ]

    def search_memories(self, query: str) -> list[Memory]:
        """Search memories using simple case-insensitive text matching.

        Args:
            query: Search text used to find relevant memories.

        Returns:
            Matching memory entries.
        """
        query = query.strip()
        if not query:
            return self.get_memories()

        terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
        if not terms:
            return self._search_by_substring(query)

        matches: dict[int, Memory] = {}
        for term in terms:
            for memory in self._search_by_substring(term):
                matches[memory.id] = memory

        return sorted(matches.values(), key=lambda memory: memory.id)

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory by identifier.

        Args:
            memory_id: Identifier of the memory to delete.

        Returns:
            True if a memory was deleted, False otherwise.
        """
        with self._database.connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted memory id=%s", memory_id)
        else:
            logger.warning("Memory id=%s not found for deletion", memory_id)
        return deleted

    def clear_memories(self) -> int:
        """Delete all stored memories.

        Returns:
            Number of deleted memories.
        """
        with self._database.connect() as conn:
            cursor = conn.execute("DELETE FROM memories")

        logger.info("Cleared %s memories", cursor.rowcount)
        return cursor.rowcount

    def _search_by_substring(self, query: str) -> list[Memory]:
        """Search memories where content contains the given substring."""
        pattern = f"%{query.lower()}%"
        with self._database.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, content, created_at
                FROM memories
                WHERE LOWER(content) LIKE ?
                ORDER BY id ASC
                """,
                (pattern,),
            ).fetchall()

        return [
            Memory(id=row["id"], content=row["content"], created_at=row["created_at"])
            for row in rows
        ]
