from uuid import uuid4

from app.contracts.handoff_manager import HandoffManager
from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.core.constants import ChannelType, HandoffReason
from app.domain.manager_queue import ManagerQueueItem
from app.domain.processing import ProcessingResult
from app.learning.service import LearningService


class DefaultHandoffManager(HandoffManager):
    """Creates internal manager queue records. Does not call CRM or AI Core."""

    def __init__(
        self,
        repository: ManagerQueueRepository,
        learning_service: LearningService | None = None,
    ) -> None:
        self.repository = repository
        self.learning_service = learning_service

    async def create_handoff(self, result: ProcessingResult) -> str:
        item = ManagerQueueItem(
            request_id=result.request_id or str(uuid4()),
            channel=result.channel or ChannelType.INTERNAL,
            customer_name=result.customer_name,
            customer_contact=result.customer_contact,
            conversation_history=list(result.conversation_history),
            ai_response=result.response_text,
            handoff_reason=result.handoff_reason or HandoffReason.UNKNOWN,
        )
        saved = await self.repository.add(item)
        if self.learning_service is not None:
            await self.learning_service.on_handoff(result, saved.request_id)
        return saved.request_id
