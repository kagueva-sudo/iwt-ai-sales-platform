import json
from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.contracts.conversation_repository import ConversationRepository
from app.db.models import ConversationMessageModel, ConversationModel
from app.db.session import SessionLocal
from app.domain.conversations import ConversationContext, ConversationMessage

_MAX_RECENT_MESSAGES = 20


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
        if len(context.recent_messages) > _MAX_RECENT_MESSAGES:
            context.recent_messages = context.recent_messages[-_MAX_RECENT_MESSAGES:]


class SqlAlchemyConversationRepository(ConversationRepository):
    """PostgreSQL/SQLite-backed ConversationRepository via conversation_messages."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    async def get_context(self, conversation_id: str) -> ConversationContext:
        with self._session_factory() as db:
            header = db.get(ConversationModel, conversation_id)
            if header is None:
                header = ConversationModel(conversation_id=conversation_id)
                db.add(header)
                db.commit()
                db.refresh(header)

            rows = db.scalars(
                select(ConversationMessageModel)
                .where(ConversationMessageModel.conversation_id == conversation_id)
                .order_by(ConversationMessageModel.id.asc())
            ).all()
            recent = rows[-_MAX_RECENT_MESSAGES:]
            return self._to_domain(header, recent)

    async def add_message(self, conversation_id: str, message: ConversationMessage) -> None:
        with self._session_factory() as db:
            header = db.get(ConversationModel, conversation_id)
            if header is None:
                db.add(ConversationModel(conversation_id=conversation_id))
                db.flush()

            db.add(
                ConversationMessageModel(
                    conversation_id=conversation_id,
                    role=message.role,
                    text=message.text,
                    message_id=message.message_id,
                )
            )
            db.flush()

            ids = db.scalars(
                select(ConversationMessageModel.id)
                .where(ConversationMessageModel.conversation_id == conversation_id)
                .order_by(ConversationMessageModel.id.asc())
            ).all()
            if len(ids) > _MAX_RECENT_MESSAGES:
                obsolete = ids[:-_MAX_RECENT_MESSAGES]
                db.execute(
                    delete(ConversationMessageModel).where(ConversationMessageModel.id.in_(obsolete))
                )
            db.commit()

    def _to_domain(
        self,
        header: ConversationModel,
        rows: list[ConversationMessageModel],
    ) -> ConversationContext:
        try:
            metadata = json.loads(header.metadata_json or "{}")
            if not isinstance(metadata, dict):
                metadata = {}
        except json.JSONDecodeError:
            metadata = {}

        return ConversationContext(
            conversation_id=header.conversation_id,
            recent_messages=[
                ConversationMessage(role=row.role, text=row.text, message_id=row.message_id)
                for row in rows
            ],
            conversation_summary=header.conversation_summary,
            active_topic=header.active_topic,
            active_product=header.active_product,
            metadata={str(key): str(value) for key, value in metadata.items()},
        )
