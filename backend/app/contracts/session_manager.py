from abc import ABC, abstractmethod

from app.core.constants import ChannelType
from app.domain.sessions import SessionContext


class SessionManager(ABC):
    @abstractmethod
    async def get_or_create_session(self, client_id: str, channel: ChannelType) -> SessionContext:
        """Return an active session for the client."""
