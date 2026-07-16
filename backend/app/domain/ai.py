from dataclasses import dataclass, field

from app.core.constants import AIValidationStatus, HandoffReason
from app.domain.messages import Message


@dataclass(slots=True)
class AIResponse:
    text: str
    sources: list[str] = field(default_factory=list)
    requested_facts: set[str] = field(default_factory=set)
    needs_handoff: bool = False
    handoff_reason: HandoffReason | None = None


@dataclass(slots=True)
class ValidationResult:
    status: AIValidationStatus
    approved_text: str | None = None
    reason: str | None = None
    sources: list[str] = field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        return self.status == AIValidationStatus.APPROVED


@dataclass(slots=True)
class AIProcessingResult:
    inbound_message: Message
    outbound_message: Message
    ai_response: AIResponse
    validation_result: ValidationResult
    handoff_id: str | None = None
    error: str | None = None
