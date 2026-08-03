from app.contracts.knowledge_repository import KnowledgeRepository
from app.domain.knowledge import KnowledgeItem


class InMemoryKnowledgeRepository(KnowledgeRepository):
    """Local in-memory knowledge store for MVP foundation."""

    def __init__(self, items: list[KnowledgeItem] | None = None) -> None:
        self._items: dict[str, KnowledgeItem] = {}
        for item in items or []:
            stored = item if item.confirmed_fields else item.with_default_confirmed_fields()
            self._items[stored.id] = stored

    async def list_all(self) -> list[KnowledgeItem]:
        return list(self._items.values())

    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        return self._items.get(item_id)

    async def add(self, item: KnowledgeItem) -> KnowledgeItem:
        stored = item if item.confirmed_fields else item.with_default_confirmed_fields()
        self._items[stored.id] = stored
        return stored
