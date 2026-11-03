"""Tests for conversation history management."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from brain.conversation.conversation_manager import ConversationManager
from memory.database import Database
from memory.memory_manager import MemoryManager


class TestConversationManager(unittest.TestCase):
    """Unit tests for ConversationManager."""

    def setUp(self) -> None:
        """Create isolated conversation manager for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test_alife.db")
        self.memory_manager = MemoryManager(self.database)
        self.provider = MagicMock()
        self.provider.generate.return_value = "Test response"
        self.conversation = ConversationManager(
            self.provider,
            self.memory_manager,
            self.database,
        )

    def tearDown(self) -> None:
        """Remove temporary test data."""
        self.temp_dir.cleanup()

    def test_add_message(self) -> None:
        """add_message should persist a conversation message."""
        message = self.conversation.add_message("user", "Hello")

        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, "Hello")

    def test_get_recent_messages(self) -> None:
        """get_recent_messages should return saved messages in order."""
        self.conversation.add_message("user", "Hello")
        self.conversation.add_message("assistant", "Hi there")

        messages = self.conversation.get_recent_messages()

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "Hello")
        self.assertEqual(messages[1].content, "Hi there")

    def test_clear_history(self) -> None:
        """clear_history should remove all conversation messages."""
        self.conversation.add_message("user", "Hello")
        self.conversation.add_message("assistant", "Hi")

        deleted_count = self.conversation.clear_history()
        remaining = self.conversation.get_recent_messages()

        self.assertEqual(deleted_count, 2)
        self.assertEqual(remaining, [])

    def test_conversation_persistence(self) -> None:
        """Conversation history should persist across manager instances."""
        self.conversation.add_message("user", "Persistent message")
        reloaded = ConversationManager(
            self.provider,
            MemoryManager(self.database),
            self.database,
        )

        messages = reloaded.get_recent_messages()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Persistent message")

    def test_generate_response_saves_messages(self) -> None:
        """generate_response should save user and assistant messages."""
        response = self.conversation.generate_response("Hello")

        messages = self.conversation.get_recent_messages()

        self.assertEqual(response, "Test response")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[1].role, "assistant")

    def test_generate_response_includes_memories_in_prompt(self) -> None:
        """generate_response should include relevant memories in the prompt."""
        self.memory_manager.save_memory("My favorite language is Java")

        self.conversation.generate_response("What is my favorite language?")

        prompt = self.provider.generate.call_args[0][0]
        self.assertIn("My favorite language is Java", prompt)

    def test_remember_command(self) -> None:
        """/remember should save a memory and return confirmation."""
        response = self.conversation.handle_command(
            "/remember My favorite programming language is Java"
        )

        memories = self.memory_manager.get_memories()

        self.assertEqual(response, "I'll remember that.")
        self.assertEqual(len(memories), 1)

    def test_recall_command(self) -> None:
        """/recall should list stored memories."""
        self.memory_manager.save_memory("My favorite language is Java")

        response = self.conversation.handle_command("/recall")

        self.assertIn("My favorite language is Java", response)

    def test_history_command(self) -> None:
        """/history should display conversation history."""
        self.conversation.add_message("user", "Hello")
        self.conversation.add_message("assistant", "Hi there")

        response = self.conversation.handle_command("/history")

        self.assertIn("Hello", response)
        self.assertIn("Hi there", response)

    def test_forget_command(self) -> None:
        """/forget should delete a memory by id."""
        memory = self.memory_manager.save_memory("Temporary memory")

        response = self.conversation.handle_command(f"/forget {memory.id}")

        self.assertIn("Forgot memory", response)
        self.assertEqual(self.memory_manager.get_memories(), [])

    def test_clear_memory_command(self) -> None:
        """/clear-memory should remove all memories."""
        self.memory_manager.save_memory("Memory one")

        response = self.conversation.handle_command("/clear-memory")

        self.assertIn("Cleared 1 memories", response)
        self.assertEqual(self.memory_manager.get_memories(), [])

    def test_clear_history_command(self) -> None:
        """/clear-history should remove all conversation messages."""
        self.conversation.add_message("user", "Hello")

        response = self.conversation.handle_command("/clear-history")

        self.assertIn("Cleared 1 conversation messages", response)
        self.assertEqual(self.conversation.get_recent_messages(), [])

    def test_invalid_forget_request(self) -> None:
        """Invalid recall/forget requests should not crash."""
        response = self.conversation.handle_command("/forget abc")
        self.assertIn("Usage", response)

    def test_typed_tool_request_uses_orchestrator(self) -> None:
        """Typed tool requests should go through the shared conversation pipeline."""
        from tools import build_tool_orchestrator

        orchestrator, confirmation = build_tool_orchestrator(self.provider)
        conversation = ConversationManager(
            self.provider,
            self.memory_manager,
            self.database,
            tool_orchestrator=orchestrator,
            confirmation_manager=confirmation,
        )
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True):
            response = conversation.generate_response("Open YouTube.")

        self.assertIn("opened", response.lower())
        self.provider.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
