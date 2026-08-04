from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus


class ManagerQueueService:
    """Thin service over ManagerQueueRepository for manager-facing operations."""

    def __init__(self, repository: ManagerQueueRepository) -> None:
        self.repository = repository

    async def list_items(self, status: ManagerQueueStatus | None = None) -> list[ManagerQueueItem]:
        if status is None:
            return await self.repository.list_all()
        return await self.repository.list_by_status(status)

    async def get_item(self, request_id: str) -> ManagerQueueItem | None:
        return await self.repository.get(request_id)

    async def update_status(self, request_id: str, status: ManagerQueueStatus) -> ManagerQueueItem | None:
        return await self.repository.update_status(request_id, status)
