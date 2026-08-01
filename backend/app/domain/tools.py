from dataclasses import dataclass, field


@dataclass(slots=True)
class ToolDescription:
    name: str
    description: str
    input_schema: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ToolRequest:
    tool_name: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    success: bool
    data: dict[str, str] = field(default_factory=dict)
    error: str | None = None
