from app.contracts.knowledge_provider import KnowledgeProvider
from app.domain.knowledge import KnowledgeItem
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.search_service import KnowledgeSearchService
from app.repositories.knowledge import InMemoryKnowledgeRepository


class KnowledgeBaseProvider(KnowledgeProvider):
    """Knowledge Base adapter for Source Selector via KnowledgeProvider contract."""

    provider_name = "knowledge_base"

    def __init__(self, search_service: KnowledgeSearchService) -> None:
        self.search_service = search_service

    @classmethod
    def from_items(cls, items: list[KnowledgeItem] | None = None) -> "KnowledgeBaseProvider":
        repository = InMemoryKnowledgeRepository(items)
        return cls(KnowledgeSearchService(repository))

    async def search(self, query: str) -> SourceSelectionResult:
        matched_items = await self.search_service.search(query)
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
            metadata={
                "category": item.category,
                "item_type": item.item_type,
                "confirmed_fields": ",".join(sorted(item.confirmed_fields)),
                **item.metadata,
            },
        )


# Backward-compatible alias for existing imports/tests.
class InMemoryKnowledgeBaseProvider(KnowledgeBaseProvider):
    def __init__(self, items: list[KnowledgeItem] | None = None) -> None:
        repository = InMemoryKnowledgeRepository(items)
        super().__init__(KnowledgeSearchService(repository))
