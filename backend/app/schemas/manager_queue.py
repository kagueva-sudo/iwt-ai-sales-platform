from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import ChannelType, HandoffReason
from app.domain.manager_queue import ManagerQueueStatus


class ManagerQueueItemSchema(BaseModel):
    request_id: str
    channel: ChannelType
    customer_name: str | None = None
    customer_contact: str | None = None
    conversation_history: list[str] = Field(default_factory=list)
    ai_response: str | None = None
    handoff_reason: HandoffReason
    status: ManagerQueueStatus
    created_at: datetime


class ManagerQueueStatusUpdateSchema(BaseModel):
    status: ManagerQueueStatus
