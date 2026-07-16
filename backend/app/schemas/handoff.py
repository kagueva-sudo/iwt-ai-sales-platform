from pydantic import BaseModel

from app.core.constants import ChannelType, HandoffReason


class HandoffRequestSchema(BaseModel):
    channel: ChannelType
    customer_id: str | None = None
    customer_contact: str | None = None
    message: str
    reason: HandoffReason
    ai_recommendation: str | None = None


class HandoffResponseSchema(BaseModel):
    handoff_id: str
    status: str
    reason: HandoffReason
