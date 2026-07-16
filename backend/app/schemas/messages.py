from pydantic import BaseModel, Field

from app.core.constants import ChannelType


class IncomingMessageRequest(BaseModel):
    channel: ChannelType = Field(..., description="Client communication channel")
    customer_id: str | None = Field(default=None, description="External customer id")
    customer_contact: str | None = Field(default=None, description="Phone, email, or messenger handle")
    text: str = Field(..., min_length=1, description="Incoming client message")


class MessageAcceptedResponse(BaseModel):
    message_id: str
    status: str
