from abc import ABC, abstractmethod

from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus


class ManagerQueueRepository(ABC):
    @abstractmethod
    async def add(self, item: ManagerQueueItem) -> ManagerQueueItem:
        """Persist a new manager queue item."""

    @abstractmethod
    async def get(self, request_id: str) -> ManagerQueueItem | None:
        """Return queue item by request_id."""

    @abstractmethod
    async def update_status(self, request_id: str, status: ManagerQueueStatus) -> ManagerQueueItem | None:
        """Update queue item status."""

    @abstractmethod
    async def list_by_status(self, status: ManagerQueueStatus) -> list[ManagerQueueItem]:
        """List queue items with the given status."""

    @abstractmethod
    async def list_all(self) -> list[ManagerQueueItem]:
        """List all manager queue items."""
