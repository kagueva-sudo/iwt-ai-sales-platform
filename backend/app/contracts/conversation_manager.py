from abc import ABC, abstractmethod

from app.domain.conversations import ConversationContext, ConversationMessage


class ConversationManager(ABC):
    @abstractmethod
    async def load_context(self, conversation_id: str) -> ConversationContext:
        """Load conversation context by dialog/conversation id."""

    @abstractmethod
    async def append_message(self, conversation_id: str, message: ConversationMessage) -> None:
        """Append a message to conversation history."""
