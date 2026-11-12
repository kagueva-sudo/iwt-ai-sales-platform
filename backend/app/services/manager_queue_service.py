from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.core.constants import ChannelType, MessageDirection
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus
from app.domain.messages import Message
from app.learning.service import LearningService


class ManagerQueueService:
    """Thin service over ManagerQueueRepository for manager-facing operations."""

    def __init__(
        self,
        repository: ManagerQueueRepository,
        learning_service: LearningService | None = None,
        email_adapter=None,
    ) -> None:
        self.repository = repository
        self.learning_service = learning_service
        self.email_adapter = email_adapter

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
        if item is None:
            return None

        if status == ManagerQueueStatus.DONE:
            answer = (manager_answer or "").strip()
            if item.channel == ChannelType.EMAIL and answer and self.email_adapter is not None:
                subject = item.email_subject or item.customer_name or "IWT"
                outbound = Message(
                    text=answer,
                    channel=ChannelType.EMAIL,
                    direction=MessageDirection.OUTBOUND,
                    customer_id=item.request_id,
                    customer_contact=item.customer_contact,
                    metadata={
                        "outbound_kind": "manager_reply",
                        "email_message_id": item.email_message_id or "",
                        "email_subject": subject,
                    },
                )
                await self.email_adapter.send_message(outbound)
            if self.learning_service is not None:
                await self.learning_service.on_manager_done(item, manager_answer=manager_answer)
        return item
