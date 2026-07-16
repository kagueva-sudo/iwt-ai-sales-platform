from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.core.constants import ChannelType, MessageDirection, ProcessingStatus


@dataclass(slots=True)
class Message:
    text: str
    channel: ChannelType
    direction: MessageDirection
    customer_id: str | None = None
    customer_contact: str | None = None
    status: ProcessingStatus = ProcessingStatus.RECEIVED
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
