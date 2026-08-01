from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversationMessage:
    role: str
    text: str
    message_id: str | None = None


@dataclass(slots=True)
class ConversationContext:
    conversation_id: str
    recent_messages: list[ConversationMessage] = field(default_factory=list)
    conversation_summary: str | None = None
    active_topic: str | None = None
    active_product: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
