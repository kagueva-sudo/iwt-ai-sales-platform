from abc import ABC, abstractmethod

from app.domain.tools import ToolDescription, ToolRequest, ToolResult


class Tool(ABC):
    @abstractmethod
    def describe(self) -> ToolDescription:
        """Return tool description for Prompt Builder."""

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResult:
        """Execute tool request."""


class ToolRegistry(ABC):
    @abstractmethod
    async def list_tools(self) -> list[ToolDescription]:
        """Return available tool descriptions."""
