from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.core.constants import ChannelType, HandoffReason


@dataclass(slots=True)
class HandoffCase:
    channel: ChannelType
    message: str
    reason: HandoffReason
    customer_id: str | None = None
    customer_contact: str | None = None
    history: list[str] = field(default_factory=list)
    ai_response: str | None = None
    ai_recommendation: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
