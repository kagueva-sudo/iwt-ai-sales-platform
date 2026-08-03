from abc import ABC, abstractmethod

from app.domain.knowledge import KnowledgeItem


class KnowledgeRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[KnowledgeItem]:
        """Return all local knowledge items."""

    @abstractmethod
    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        """Return a knowledge item by id."""

    @abstractmethod
    async def add(self, item: KnowledgeItem) -> KnowledgeItem:
        """Persist a knowledge item locally."""
