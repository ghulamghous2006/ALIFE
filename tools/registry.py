"""Tool registry for registering and executing approved ALIFE tools."""

import logging
from typing import Any

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of explicitly approved ALIFE tools."""

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by name."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Return a tool by name."""
        return self._tools.get(name.strip().lower())

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def describe_tools(self) -> str:
        """Return a text description of all registered tools."""
        lines: list[str] = []
        for tool in self.list_tools():
            params = ", ".join(
                f"{param.name}: {param.description}" for param in tool.parameters
            )
            param_text = f" Parameters: {params}." if params else ""
            lines.append(f"- {tool.name}: {tool.description}.{param_text}")
        return "\n".join(lines)

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Find and execute a registered tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Structured tool result.
        """
        tool = self.get(name)
        if tool is None:
            logger.warning("Unknown tool requested: %s", name)
            return ToolResult(
                success=False,
                message=f"I don't know how to run the tool '{name}'.",
            )

        payload = arguments or {}
        try:
            validated = tool.validate_arguments(payload)
            result = tool.execute(validated)
            logger.info("Tool executed: %s success=%s", tool.name, result.success)
            return result
        except ValueError as exc:
            logger.warning("Invalid arguments for tool %s: %s", tool.name, exc)
            return ToolResult(success=False, message=str(exc))
        except Exception as exc:
            logger.exception("Tool execution failed for %s: %s", tool.name, exc)
            return ToolResult(
                success=False,
                message=f"The tool '{tool.name}' failed: {exc}",
            )
