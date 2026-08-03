from dataclasses import dataclass, field


@dataclass(slots=True)
class KnowledgeItem:
    id: str
    title: str
    content: str
    category: str = "general"
    item_type: str = "faq"
    tags: list[str] = field(default_factory=list)
    source: str = "knowledge_base"
    confirmed_fields: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)

    def with_default_confirmed_fields(self) -> "KnowledgeItem":
        """Return a copy with explicitly confirmed content fields."""
        confirmed = {"id", "title", "content", "category", "item_type"}
        if self.tags:
            confirmed.add("tags")
        return KnowledgeItem(
            id=self.id,
            title=self.title,
            content=self.content,
            category=self.category,
            item_type=self.item_type,
            tags=list(self.tags),
            source=self.source,
            confirmed_fields=confirmed,
            metadata=dict(self.metadata),
        )
