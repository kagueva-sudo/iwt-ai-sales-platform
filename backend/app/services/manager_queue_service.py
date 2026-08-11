from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus
from app.learning.service import LearningService


class ManagerQueueService:
    """Thin service over ManagerQueueRepository for manager-facing operations."""

    def __init__(
        self,
        repository: ManagerQueueRepository,
        learning_service: LearningService | None = None,
    ) -> None:
        self.repository = repository
        self.learning_service = learning_service

    async def list_items(self, status: ManagerQueueStatus | None = None) -> list[ManagerQueueItem]:
        if status is None:
            return await self.repository.list_all()
        return await self.repository.list_by_status(status)

    async def get_item(self, request_id: str) -> ManagerQueueItem | None:
        return await self.repository.get(request_id)

    async def update_status(
        self,
        request_id: str,
        status: ManagerQueueStatus,
        *,
        manager_answer: str | None = None,
    ) -> ManagerQueueItem | None:
        item = await self.repository.update_status(request_id, status)
        if (
            item is not None
            and status == ManagerQueueStatus.DONE
            and self.learning_service is not None
        ):
            await self.learning_service.on_manager_done(item, manager_answer=manager_answer)
        return item
