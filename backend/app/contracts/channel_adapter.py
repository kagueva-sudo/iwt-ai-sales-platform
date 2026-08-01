from abc import ABC, abstractmethod

from app.domain.messages import Message


class ChannelAdapter(ABC):
    @abstractmethod
    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        """Convert a channel-specific payload into a domain Message."""

    @abstractmethod
    async def send_message(self, message: Message) -> str:
        """Send an outbound message through the channel and return delivery id."""
