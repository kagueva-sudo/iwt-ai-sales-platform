from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.core.constants import ChannelType


@dataclass(slots=True)
class SessionContext:
    client_id: str
    channel: ChannelType
    dialog_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid4()))
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)
