from app.contracts.knowledge_repository import KnowledgeRepository
from app.domain.knowledge import KnowledgeItem


class KnowledgeSearchService:
    """Simple local keyword search over Knowledge Base items.

    Returns candidate items only. Never ranks or decides which source is better.
    Source selection is the responsibility of SourceSelector.

    No RAG, embeddings, or vector search in this foundation sprint.
    """

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    async def search(self, query: str) -> list[KnowledgeItem]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        items = await self.repository.list_all()
        return [item for item in items if self._matches(item, normalized_query)]

    def _matches(self, item: KnowledgeItem, normalized_query: str) -> bool:
        if normalized_query in item.title.lower():
            return True
        if normalized_query in item.content.lower():
            return True
        if normalized_query in item.category.lower():
            return True
        if normalized_query in item.item_type.lower():
            return True
        return any(normalized_query in tag.lower() for tag in item.tags)
