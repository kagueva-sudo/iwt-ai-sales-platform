from dataclasses import dataclass, field


@dataclass(slots=True)
class SafetyRule:
    code: str
    description: str


@dataclass(slots=True)
class ResponseConstraint:
    code: str
    description: str


@dataclass(slots=True)
class PromptMetadata:
    prompt_type: str = "default"
    language: str = "ru"
    values: dict[str, str] = field(default_factory=dict)
