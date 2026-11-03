"""Open approved applications from a controlled registry."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from tools.base import BaseTool, ToolParameter, ToolResult
from tools.config import resolve_application

logger = logging.getLogger(__name__)


class OpenApplicationTool(BaseTool):
    """Launch a configured application on Windows."""

    @property
    def name(self) -> str:
        return "open_application"

    @property
    def description(self) -> str:
        return "Open an approved configured application"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="app",
                description="Application name such as chrome, vscode, or whatsapp",
            )
        ]

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        app_name = str(arguments["app"])
        configured_path = resolve_application(app_name)
        if configured_path is None:
            return ToolResult(
                success=False,
                message=f"I don't have the application '{app_name}' configured yet.",
            )

        expanded_path = os.path.expandvars(configured_path)
        executable = Path(expanded_path)
        if not executable.exists():
            return ToolResult(
                success=False,
                message=(
                    f"I don't have the application '{app_name}' configured yet. "
                    f"Expected path: {executable}"
                ),
                data={"path": str(executable)},
            )

        try:
            subprocess.Popen([str(executable)], shell=False)
        except Exception as exc:
            logger.error("Failed to launch application app=%s: %s", app_name, exc)
            return ToolResult(
                success=False,
                message=f"I couldn't open {app_name.title()}: {exc}",
                data={"path": str(executable)},
            )

        logger.info("Launched application app=%s path=%s", app_name, executable)
        return ToolResult(
            success=True,
            message=f"Done. I've opened {app_name.title()}.",
            data={"path": str(executable)},
        )
