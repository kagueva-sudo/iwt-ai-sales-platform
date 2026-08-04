from app.channel_adapters.payload import first_str
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message


class MaxChannelAdapter(ChannelAdapter):
    """MAX channel adapter: normalize inbound payloads and stub outbound delivery.

    Does not contain AI logic. Real MAX API transport is out of scope for this sprint.
    """

    channel = ChannelType.MAX

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        text = first_str(payload, ("text", "message", "body"))
        if not text:
            raise ProviderError("MAX payload is missing message text.")

        return Message(
            text=text,
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id=first_str(payload, ("user_id", "customer_id", "chat_id")),
            customer_contact=first_str(payload, ("contact", "username", "phone")),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        return message.id
