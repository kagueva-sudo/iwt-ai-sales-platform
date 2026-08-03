from app.contracts.conversation_repository import ConversationRepository
from app.domain.conversations import ConversationContext, ConversationMessage


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._conversations: dict[str, ConversationContext] = {}

    async def get_context(self, conversation_id: str) -> ConversationContext:
        context = self._conversations.get(conversation_id)
        if context is None:
            context = ConversationContext(conversation_id=conversation_id)
            self._conversations[conversation_id] = context
        return context

    async def add_message(self, conversation_id: str, message: ConversationMessage) -> None:
        context = await self.get_context(conversation_id)
        context.recent_messages.append(message)
        if len(context.recent_messages) > 20:
            context.recent_messages = context.recent_messages[-20:]
