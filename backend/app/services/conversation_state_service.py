from app.contracts.conversation_manager import ConversationManager
from app.contracts.conversation_repository import ConversationRepository
from app.contracts.session_manager import SessionManager
from app.contracts.session_repository import SessionRepository
from app.core.constants import ChannelType
from app.domain.conversations import ConversationContext, ConversationMessage
from app.domain.messages import Message
from app.domain.sessions import SessionContext


class ConversationStateService(SessionManager, ConversationManager):
    """MVP implementation of SessionManager + ConversationManager interfaces."""

    def __init__(
        self,
        session_repository: SessionRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self.session_repository = session_repository
        self.conversation_repository = conversation_repository

    async def get_or_create_session(self, client_id: str, channel: ChannelType) -> SessionContext:
        return await self.session_repository.get_or_create(client_id, channel.value)

    async def load_context(self, conversation_id: str) -> ConversationContext:
        return await self.conversation_repository.get_context(conversation_id)

    async def append_message(self, conversation_id: str, message: ConversationMessage) -> None:
        await self.conversation_repository.add_message(conversation_id, message)

    async def prepare_for_message(self, message: Message) -> tuple[SessionContext, ConversationContext]:
        client_id = message.customer_id or message.customer_contact or "anonymous"
        session = await self.get_or_create_session(client_id, message.channel)
        conversation = await self.load_context(session.dialog_id)
        await self.append_message(
            session.dialog_id,
            ConversationMessage(role="user", text=message.text, message_id=message.id),
        )
        conversation = await self.load_context(session.dialog_id)
        return session, conversation
