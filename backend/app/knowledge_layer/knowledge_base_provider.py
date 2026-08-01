from app.contracts.knowledge_provider import KnowledgeProvider
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.schemas import KnowledgeItem


class InMemoryKnowledgeBaseProvider(KnowledgeProvider):
    provider_name = "knowledge_base"

    def __init__(self, items: list[KnowledgeItem] | None = None) -> None:
        self.items = items or []

    async def search(self, query: str) -> SourceSelectionResult:
        normalized_query = query.lower()
        matched_items = [
            item
            for item in self.items
            if normalized_query in item.title.lower()
            or normalized_query in item.content.lower()
            or any(normalized_query in tag.lower() for tag in item.tags)
        ]
        return SourceSelectionResult(
            query=query,
            sources=[self._to_verified_source(item) for item in matched_items],
        )

    def _to_verified_source(self, item: KnowledgeItem) -> VerifiedSource:
        return VerifiedSource(
            source_id=item.id,
            source_type=self.provider_name,
            title=item.title,
            content=item.content,
            metadata={"category": item.category, **item.metadata},
        )
