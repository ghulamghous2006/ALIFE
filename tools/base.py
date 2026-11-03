"""Base types and interface for ALIFE tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by a tool execution."""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ToolParameter:
    """Definition of a single tool parameter."""

    name: str
    description: str
    required: bool = True


class BaseTool(ABC):
    """Common interface for all ALIFE tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable tool description."""

    @property
    def parameters(self) -> list[ToolParameter]:
        """Return parameter definitions for this tool."""
        return []

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated arguments."""

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize tool arguments.

        Raises:
            ValueError: If required arguments are missing or invalid.
        """
        normalized = {key: value for key, value in arguments.items() if value is not None}
        for parameter in self.parameters:
            if parameter.required and parameter.name not in normalized:
                raise ValueError(f"Missing required argument: {parameter.name}")
        return normalized
