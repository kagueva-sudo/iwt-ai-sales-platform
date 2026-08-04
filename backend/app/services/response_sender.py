from app.contracts.channel_adapter import ChannelAdapter
from app.contracts.response_sender import ResponseSender
from app.core.constants import ChannelType
from app.domain.messages import Message


class InMemoryResponseSender(ResponseSender):
    """Stub ResponseSender without real channel delivery."""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def send(self, message: Message) -> str:
        self.sent.append(message)
        return message.id


class ChannelResponseSender(ResponseSender):
    """Routes outbound messages to channel adapters; falls back to stub sender."""

    def __init__(
        self,
        adapters: dict[ChannelType, ChannelAdapter],
        fallback: ResponseSender | None = None,
    ) -> None:
        self.adapters = adapters
        self.fallback = fallback or InMemoryResponseSender()

    async def send(self, message: Message) -> str:
        adapter = self.adapters.get(message.channel)
        if adapter is not None:
            return await adapter.send_message(message)
        return await self.fallback.send(message)
