from abc import ABC, abstractmethod

from app.domain.messages import Message


class ResponseSender(ABC):
    @abstractmethod
    async def send(self, message: Message) -> str:
        """Send an approved outbound response."""
