"""Return the current local time."""

import logging
from datetime import datetime
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GetTimeTool(BaseTool):
    """Report the current local computer time."""

    @property
    def name(self) -> str:
        return "get_time"

    @property
    def description(self) -> str:
        return "Get the current local time"

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        now = datetime.now()
        formatted = now.strftime("%I:%M %p").lstrip("0")
        message = f"It is {formatted}."
        logger.info("Reported local time: %s", formatted)
        return ToolResult(success=True, message=message, data={"time": formatted})
