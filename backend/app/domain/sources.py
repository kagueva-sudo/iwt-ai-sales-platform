from dataclasses import dataclass, field


@dataclass(slots=True)
class VerifiedSource:
    source_id: str
    source_type: str
    title: str
    content: str
    confidence: float = 1.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SourceSelectionResult:
    query: str
    sources: list[VerifiedSource] = field(default_factory=list)

    @property
    def has_sources(self) -> bool:
        return bool(self.sources)
