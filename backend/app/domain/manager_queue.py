from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from app.core.constants import ChannelType, HandoffReason


class ManagerQueueStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ManagerQueueItem:
    channel: ChannelType
    customer_contact: str | None
    conversation_history: list[str]
    ai_response: str | None
    handoff_reason: HandoffReason
    request_id: str = field(default_factory=lambda: str(uuid4()))
    customer_name: str | None = None
    status: ManagerQueueStatus = ManagerQueueStatus.NEW
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
