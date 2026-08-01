from dataclasses import dataclass, field


@dataclass(slots=True)
class KnowledgeItem:
    id: str
    title: str
    content: str
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
