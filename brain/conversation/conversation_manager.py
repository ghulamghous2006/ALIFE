"""Conversation history and context management."""

import logging
from dataclasses import dataclass

from brain.providers.ollama_provider import OllamaProvider
from memory.database import Database
from memory.memory_manager import Memory, MemoryManager
from tools.confirmation import ConfirmationManager
from tools.orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 20


@dataclass(frozen=True)
class ConversationMessage:
    """A persisted conversation message."""

    id: int
    role: str
    content: str
    timestamp: str


class ConversationManager:
    """Manages conversation history, memory integration, and response generation."""

    def __init__(
        self,
        provider: OllamaProvider,
        memory_manager: MemoryManager,
        database: Database,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        tool_orchestrator: ToolOrchestrator | None = None,
        confirmation_manager: ConfirmationManager | None = None,
    ) -> None:
        """Initialize the conversation manager.

        Args:
            provider: Ollama provider used for response generation.
            memory_manager: Long-term memory manager.
            database: Shared database instance.
            history_limit: Maximum recent messages included in context.
            tool_orchestrator: Optional tool router and executor.
            confirmation_manager: Optional destructive-action confirmation manager.
        """
        self._provider = provider
        self._memory_manager = memory_manager
        self._database = database
        self._history_limit = history_limit
        self._tool_orchestrator = tool_orchestrator
        self._confirmation_manager = confirmation_manager or ConfirmationManager()

    def add_message(self, role: str, content: str) -> ConversationMessage:
        """Persist a conversation message.

        Args:
            role: Message role (``user`` or ``assistant``).
            content: Message text.

        Returns:
            The saved conversation message.

        Raises:
            ValueError: If role or content is invalid.
        """
        role = role.strip().lower()
        if role not in {"user", "assistant"}:
            raise ValueError("Role must be 'user' or 'assistant'.")
        if not content.strip():
            raise ValueError("Message content must not be empty.")

        with self._database.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversation_messages (role, content)
                VALUES (?, ?)
                """,
                (role, content.strip()),
            )
            message_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT id, role, content, timestamp
                FROM conversation_messages
                WHERE id = ?
                """,
                (message_id,),
            ).fetchone()

        message = ConversationMessage(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            timestamp=row["timestamp"],
        )
        logger.debug("Saved conversation message id=%s role=%s", message.id, message.role)
        return message

    def get_recent_messages(self, limit: int = DEFAULT_HISTORY_LIMIT) -> list[ConversationMessage]:
        """Return the most recent conversation messages.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            Recent messages ordered oldest to newest.
        """
        with self._database.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, timestamp
                FROM conversation_messages
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        messages = [
            ConversationMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
            )
            for row in reversed(rows)
        ]
        return messages

    def clear_history(self) -> int:
        """Delete all conversation messages.

        Returns:
            Number of deleted messages.
        """
        with self._database.connect() as conn:
            cursor = conn.execute("DELETE FROM conversation_messages")

        logger.info("Cleared %s conversation messages", cursor.rowcount)
        return cursor.rowcount

    def handle_command(self, user_input: str) -> str | None:
        """Handle slash commands.

        Args:
            user_input: Raw user input.

        Returns:
            Command response if handled, otherwise ``None``.
        """
        if not user_input.startswith("/"):
            return None

        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command == "/remember":
            return self._command_remember(argument)
        if command == "/recall":
            return self._command_recall()
        if command == "/forget":
            return self._command_forget(argument)
        if command == "/memories":
            return self._command_memories()
        if command == "/clear-memory":
            return self._command_clear_memory()
        if command == "/history":
            return self._command_history()
        if command == "/clear-history":
            return self._command_clear_history()
        if command in {"/voice", "/exit"}:
            return None

        return f"Unknown command: {command}"

    def generate_response(self, user_message: str) -> str:
        """Generate an assistant response for a user message.

        Args:
            user_message: Current user message.

        Returns:
            Generated assistant response.
        """
        if self._confirmation_manager.has_pending():
            confirmation_response = self._confirmation_manager.handle_response(user_message)
            if confirmation_response is not None:
                self.add_message("user", user_message)
                self.add_message("assistant", confirmation_response)
                return confirmation_response

        if self._tool_orchestrator is not None:
            tool_result = self._tool_orchestrator.try_handle(user_message)
            if tool_result is not None:
                self.add_message("user", user_message)
                self.add_message("assistant", tool_result.message)
                return tool_result.message

        self.add_message("user", user_message)

        recent_messages = self.get_recent_messages(limit=self._history_limit)
        try:
            relevant_memories = self._memory_manager.search_memories(user_message)
        except Exception as exc:
            logger.exception("Memory retrieval failed: %s", exc)
            relevant_memories = []
        prompt = self._build_prompt(user_message, recent_messages, relevant_memories)

        response = self._provider.generate(prompt)
        if not response.strip():
            response = "I generated an empty reply. Please try again."
        self.add_message("assistant", response)
        return response

    def _build_prompt(
        self,
        user_message: str,
        recent_messages: list[ConversationMessage],
        relevant_memories: list[Memory],
    ) -> str:
        """Build the model prompt from history and memories."""
        sections: list[str] = []

        if relevant_memories:
            memory_lines = "\n".join(f"- {memory.content}" for memory in relevant_memories)
            sections.append(f"Relevant memories:\n{memory_lines}")

        history_lines: list[str] = []
        for message in recent_messages:
            if message.role == "user" and message.content == user_message:
                continue
            speaker = "User" if message.role == "user" else "ALIFE"
            history_lines.append(f"{speaker}: {message.content}")

        if history_lines:
            sections.append("Recent conversation:\n" + "\n".join(history_lines))

        sections.append(f"Current user message:\n{user_message}")
        return "\n\n".join(sections)

    def _command_remember(self, content: str) -> str:
        if not content:
            return "Usage: /remember <text>"
        self._memory_manager.save_memory(content)
        return "I'll remember that."

    def _command_recall(self) -> str:
        memories = self._memory_manager.get_memories()
        if not memories:
            return "I don't have any stored memories yet."
        lines = [f"[{memory.id}] {memory.content}" for memory in memories]
        return "Stored memories:\n" + "\n".join(lines)

    def _command_forget(self, argument: str) -> str:
        if not argument.isdigit():
            return "Usage: /forget <memory_id>"
        memory_id = int(argument)
        if self._memory_manager.delete_memory(memory_id):
            return f"Forgot memory {memory_id}."
        return f"No memory found with id {memory_id}."

    def _command_memories(self) -> str:
        return self._command_recall()

    def _command_clear_memory(self) -> str:
        count = self._memory_manager.clear_memories()
        return f"Cleared {count} memories."

    def _command_history(self) -> str:
        messages = self.get_recent_messages(limit=50)
        if not messages:
            return "No conversation history yet."
        lines = []
        for message in messages:
            speaker = "You" if message.role == "user" else "ALIFE"
            lines.append(f"{speaker}: {message.content}")
        return "Conversation history:\n" + "\n".join(lines)

    def _command_clear_history(self) -> str:
        count = self.clear_history()
        return f"Cleared {count} conversation messages."
