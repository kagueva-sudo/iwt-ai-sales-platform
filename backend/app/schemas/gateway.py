from pydantic import BaseModel, Field

from app.core.constants import ChannelType


class GatewayMessageRequest(BaseModel):
    channel: ChannelType = Field(..., description="Source channel")
    text: str = Field(..., min_length=1, description="Normalized client message text")
    customer_id: str | None = Field(default=None, description="Channel-independent customer id")
    customer_contact: str | None = Field(default=None, description="Client contact from channel")
    external_message_id: str | None = Field(default=None, description="Original channel message id")
    metadata: dict[str, str] = Field(default_factory=dict, description="Channel metadata without business logic")
