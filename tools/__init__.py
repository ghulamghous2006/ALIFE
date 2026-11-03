"""Tool module exports and factory helpers."""

from tools.base import BaseTool, ToolParameter, ToolResult
from tools.builtin.get_time import GetTimeTool
from tools.builtin.open_application import OpenApplicationTool
from tools.builtin.open_website import OpenWebsiteTool
from tools.builtin.shutdown import RequestShutdownTool
from tools.builtin.system_info import SystemInfoTool
from tools.confirmation import ConfirmationManager
from tools.orchestrator import ToolOrchestrator
from tools.registry import ToolRegistry


def build_default_registry() -> ToolRegistry:
    """Create a registry with the default safe ALIFE tools."""
    registry = ToolRegistry()
    for tool in (
        OpenWebsiteTool(),
        OpenApplicationTool(),
        GetTimeTool(),
        SystemInfoTool(),
        RequestShutdownTool(),
    ):
        registry.register(tool)
    return registry


def build_tool_orchestrator(provider) -> tuple[ToolOrchestrator, ConfirmationManager]:
    """Create the default tool orchestrator and confirmation manager."""
    confirmation_manager = ConfirmationManager()
    registry = build_default_registry()
    orchestrator = ToolOrchestrator(provider, registry, confirmation_manager)
    return orchestrator, confirmation_manager


__all__ = [
    "BaseTool",
    "ConfirmationManager",
    "ToolOrchestrator",
    "ToolParameter",
    "ToolRegistry",
    "ToolResult",
    "build_default_registry",
    "build_tool_orchestrator",
]
