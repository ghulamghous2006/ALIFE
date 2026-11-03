"""Return safe local system information."""

import logging
import platform
import sys
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    """Report safe system information."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Get safe local system information"

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Unknown",
            "python_version": sys.version.split()[0],
        }
        message = (
            f"Operating system: {info['os']} {info['os_release']}. "
            f"CPU: {info['processor']}. "
            f"Python: {info['python_version']}."
        )
        logger.info("Reported safe system information")
        return ToolResult(success=True, message=message, data=info)
