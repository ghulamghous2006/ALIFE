"""Confirmation handling for destructive ALIFE actions."""

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

AFFIRMATIVE_RESPONSES = {"yes", "y"}
NEGATIVE_RESPONSES = {"no", "n", "nope", "cancel", "stop", "don't", "do not"}


@dataclass(frozen=True)
class PendingConfirmation:
    """A destructive action awaiting explicit user confirmation."""

    tool_name: str
    arguments: dict[str, Any]
    prompt: str
    execute_callback: Callable[[], str]


class ConfirmationManager:
    """Tracks pending destructive actions requiring user confirmation."""

    def __init__(self) -> None:
        """Initialize an empty confirmation manager."""
        self._pending: PendingConfirmation | None = None

    def has_pending(self) -> bool:
        """Return True if a destructive action is awaiting confirmation."""
        return self._pending is not None

    def set_pending(self, pending: PendingConfirmation) -> None:
        """Store a pending destructive action."""
        self._pending = pending
        logger.info("Awaiting confirmation for tool=%s", pending.tool_name)

    def clear(self) -> None:
        """Clear any pending confirmation."""
        self._pending = None

    @property
    def prompt(self) -> str | None:
        """Return the confirmation prompt for the pending action."""
        return self._pending.prompt if self._pending else None

    def handle_response(self, user_message: str) -> str | None:
        """Handle a user confirmation response.

        Returns:
            Response text if confirmation was handled, otherwise ``None``.
        """
        if self._pending is None:
            return None

        normalized = user_message.strip().lower()
        if normalized in AFFIRMATIVE_RESPONSES:
            pending = self._pending
            self.clear()
            logger.info("User confirmed destructive action tool=%s", pending.tool_name)
            return pending.execute_callback()

        if normalized in NEGATIVE_RESPONSES:
            tool_name = self._pending.tool_name
            self.clear()
            logger.info("User cancelled destructive action tool=%s", tool_name)
            return "Okay, I cancelled that action."

        return (
            "Please confirm with 'yes' or 'no'. "
            f"{self._pending.prompt}"
        )
