from app.contracts.knowledge_repository import KnowledgeRepository
from app.domain.knowledge import KnowledgeItem


class KnowledgeSearchService:
    """Local keyword search over Knowledge Base items.

    Returns candidate items ordered by relevance (match count).
    Does not decide which source is better across providers — that remains
    SourceSelector responsibility.

    No RAG, embeddings, or vector search.
    """

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    async def search(self, query: str) -> list[KnowledgeItem]:
        words = self._tokenize(query)
        if not words:
            return []

        items = await self.repository.list_all()
        scored: list[tuple[int, KnowledgeItem]] = []
        for item in items:
            score = self._score(item, words)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [item for _, item in scored]

    def _tokenize(self, query: str) -> list[str]:
        return [word for word in query.strip().lower().split() if word]

    def _score(self, item: KnowledgeItem, words: list[str]) -> int:
        fields = [
            item.title.lower(),
            item.content.lower(),
            item.category.lower(),
            *[tag.lower() for tag in item.tags],
        ]
        score = 0
        for word in words:
            for field in fields:
                if word in field:
                    score += 1
        return score
