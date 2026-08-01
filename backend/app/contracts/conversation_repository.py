from abc import ABC, abstractmethod

from app.domain.conversations import ConversationContext, ConversationMessage


class ConversationRepository(ABC):
    @abstractmethod
    async def get_context(self, conversation_id: str) -> ConversationContext:
        """Return conversation context."""

    @abstractmethod
    async def add_message(self, conversation_id: str, message: ConversationMessage) -> None:
        """Append message to conversation history."""
