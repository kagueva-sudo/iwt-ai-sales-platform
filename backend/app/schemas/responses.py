from pydantic import BaseModel, Field

from app.core.constants import AIValidationStatus


class AIResponseSchema(BaseModel):
    text: str
    validation_status: AIValidationStatus
    sources: list[str] = Field(default_factory=list)
    handoff_required: bool = False
    reason: str | None = None
