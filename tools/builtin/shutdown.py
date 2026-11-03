"""Controlled shutdown request tool.

Real operating-system shutdown is disabled and cannot be invoked from this module.
"""

import logging
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Real shutdown.exe / restart / logoff execution is permanently disabled in this
# codebase until a future, explicit, reviewed change reintroduces it.
SHUTDOWN_EXECUTION_ENABLED = False

SHUTDOWN_DISABLED_MESSAGE = (
    "Shutdown is disabled in ALIFE for safety. "
    "I will not power off or restart this computer."
)


class RequestShutdownTool(BaseTool):
    """Request a controlled computer shutdown with confirmation."""

    @property
    def name(self) -> str:
        return "request_shutdown"

    @property
    def description(self) -> str:
        return "Request a controlled computer shutdown (disabled / dry-run only)"

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            success=True,
            message=(
                "Shutting down would close your computer. "
                "Do you want me to continue? (actual shutdown is currently disabled)"
            ),
            requires_confirmation=True,
            data={"action": "shutdown", "dry_run": True},
        )


def perform_shutdown() -> str:
    """Handle a confirmed shutdown request without executing OS commands.

    Returns:
        User-facing message describing the dry-run result.
    """
    logger.warning(
        "Shutdown confirmation received; execution remains disabled "
        "(SHUTDOWN_EXECUTION_ENABLED=%s)",
        SHUTDOWN_EXECUTION_ENABLED,
    )
    return SHUTDOWN_DISABLED_MESSAGE
