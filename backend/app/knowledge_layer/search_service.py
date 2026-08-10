import re

from app.contracts.knowledge_repository import KnowledgeRepository
from app.domain.knowledge import KnowledgeItem


_WORD_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
_STOPWORDS = {
    "а",
    "и",
    "в",
    "на",
    "по",
    "с",
    "у",
    "о",
    "к",
    "из",
    "от",
    "до",
    "за",
    "для",
    "при",
    "или",
    "как",
    "что",
    "это",
    "же",
    "ли",
    "бы",
    "не",
    "ни",
    "вы",
    "мы",
    "я",
    "он",
    "она",
    "они",
    "the",
    "a",
    "an",
}


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
        normalized = (
            query.lower()
            .replace("б/у", " бу ")
            .replace("б\\у", " бу ")
            .replace("trade-in", " tradein ")
            .replace("трейд-ин", " трейдин ")
        )
        words = _WORD_RE.findall(normalized)
        return [word for word in words if len(word) > 1 and word not in _STOPWORDS]

    def _score(self, item: KnowledgeItem, words: list[str]) -> int:
        title = item.title.lower()
        tags = " ".join(tag.lower() for tag in item.tags)
        category = item.category.lower()
        content = item.content.lower()
        score = 0
        for word in words:
            if self._matches(title, word):
                score += 5
            if self._matches(tags, word):
                score += 4
            if self._matches(category, word):
                score += 2
            if self._matches(content, word):
                score += 1
        return score

    def _matches(self, field: str, word: str) -> bool:
        tokens = _WORD_RE.findall(field)
        if any(token == word for token in tokens):
            return True
        # Short words: exact token only (avoids "день" → "деньги").
        if len(word) < 5:
            return False
        stem_len = 5
        stem = word[:stem_len]
        for token in tokens:
            if token.startswith(stem) or (
                len(token) >= stem_len and stem.startswith(token[:stem_len])
            ):
                return True
        return False
