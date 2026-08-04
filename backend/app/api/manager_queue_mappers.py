from app.domain.manager_queue import ManagerQueueItem
from app.schemas.manager_queue import ManagerQueueItemSchema


def map_manager_queue_item_to_schema(item: ManagerQueueItem) -> ManagerQueueItemSchema:
    return ManagerQueueItemSchema(
        request_id=item.request_id,
        channel=item.channel,
        customer_name=item.customer_name,
        customer_contact=item.customer_contact,
        conversation_history=list(item.conversation_history),
        ai_response=item.ai_response,
        handoff_reason=item.handoff_reason,
        status=item.status,
        created_at=item.created_at,
    )
