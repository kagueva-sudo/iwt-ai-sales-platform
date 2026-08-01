from abc import ABC, abstractmethod

from app.domain.sessions import SessionContext


class SessionRepository(ABC):
    @abstractmethod
    async def get_or_create(self, client_id: str, channel: str) -> SessionContext:
        """Return an active session or create a new one."""

    @abstractmethod
    async def save(self, session: SessionContext) -> None:
        """Persist session state."""
