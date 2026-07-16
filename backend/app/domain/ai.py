from dataclasses import dataclass, field

from app.core.constants import AIValidationStatus, HandoffReason


@dataclass(slots=True)
class AIResponse:
    text: str
    sources: list[str] = field(default_factory=list)
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
