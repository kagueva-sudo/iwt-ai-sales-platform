from dataclasses import dataclass, field
from enum import StrEnum

from app.core.constants import HandoffReason


class ProcessingDecision(StrEnum):
    RESPOND = "respond"
    HANDOFF = "handoff"
    ERROR = "error"
    NEEDS_MORE_DATA = "needs_more_data"


@dataclass(slots=True)
class ProcessingResult:
    decision: ProcessingDecision
    response_text: str | None = None
    handoff_reason: HandoffReason | None = None
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
