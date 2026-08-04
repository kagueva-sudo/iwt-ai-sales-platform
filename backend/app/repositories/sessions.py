import json
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.session_repository import SessionRepository
from app.core.constants import ChannelType
from app.db.models import SessionModel
from app.db.session import SessionLocal
from app.domain.sessions import SessionContext


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}

    async def get_or_create(self, client_id: str, channel: str) -> SessionContext:
        key = f"{client_id}:{channel}"
        session = self._sessions.get(key)
        if session is None:
            session = SessionContext(client_id=client_id, channel=ChannelType(channel))
            self._sessions[key] = session
        return session

    async def save(self, session: SessionContext) -> None:
        key = f"{session.client_id}:{session.channel.value}"
        self._sessions[key] = session


class SqlAlchemySessionRepository(SessionRepository):
    """PostgreSQL/SQLite-backed SessionRepository via SQLAlchemy."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    async def get_or_create(self, client_id: str, channel: str) -> SessionContext:
        with self._session_factory() as db:
            model = db.scalars(
                select(SessionModel).where(
                    SessionModel.client_id == client_id,
                    SessionModel.channel == channel,
                )
            ).first()
            if model is None:
                context = SessionContext(client_id=client_id, channel=ChannelType(channel))
                db.add(self._to_model(context))
                db.commit()
                return context
            return self._to_domain(model)

    async def save(self, session: SessionContext) -> None:
        with self._session_factory() as db:
            model = db.get(SessionModel, session.session_id)
            if model is None:
                db.add(self._to_model(session))
            else:
                model.client_id = session.client_id
                model.channel = session.channel.value
                model.dialog_id = session.dialog_id
                model.expires_at = session.expires_at
                model.created_at = session.created_at
                model.metadata_json = json.dumps(session.metadata, ensure_ascii=False)
            db.commit()

    def _to_model(self, session: SessionContext) -> SessionModel:
        return SessionModel(
            session_id=session.session_id,
            client_id=session.client_id,
            channel=session.channel.value,
            dialog_id=session.dialog_id,
            expires_at=session.expires_at,
            created_at=session.created_at,
            metadata_json=json.dumps(session.metadata, ensure_ascii=False),
        )

    def _to_domain(self, model: SessionModel) -> SessionContext:
        try:
            metadata = json.loads(model.metadata_json or "{}")
            if not isinstance(metadata, dict):
                metadata = {}
        except json.JSONDecodeError:
            metadata = {}

        return SessionContext(
            session_id=model.session_id,
            client_id=model.client_id,
            channel=ChannelType(model.channel),
            dialog_id=model.dialog_id,
            expires_at=model.expires_at,
            created_at=model.created_at,
            metadata={str(key): str(value) for key, value in metadata.items()},
        )
