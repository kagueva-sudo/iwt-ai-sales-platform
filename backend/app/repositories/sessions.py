from app.contracts.session_repository import SessionRepository
from app.core.constants import ChannelType
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
