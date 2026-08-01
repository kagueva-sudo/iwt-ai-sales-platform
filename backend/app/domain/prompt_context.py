from dataclasses import dataclass, field

from app.domain.conversations import ConversationMessage
from app.domain.prompts import PromptMetadata, ResponseConstraint, SafetyRule
from app.domain.sources import VerifiedSource
from app.domain.tools import ToolDescription


@dataclass(slots=True)
class PromptContext:
    system_prompt: str
    user_message: str
    conversation_summary: str | None = None
    recent_messages: list[ConversationMessage] = field(default_factory=list)
    active_topic: str | None = None
    active_product: str | None = None
    verified_sources: list[VerifiedSource] = field(default_factory=list)
    available_tools: list[ToolDescription] = field(default_factory=list)
    safety_rules: list[SafetyRule] = field(default_factory=list)
    response_constraints: list[ResponseConstraint] = field(default_factory=list)
    metadata: PromptMetadata = field(default_factory=PromptMetadata)
