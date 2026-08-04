from app.channel_adapters.payload import first_str
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message


class WhatsAppChannelAdapter(ChannelAdapter):
    """WhatsApp channel adapter: normalize inbound payloads and stub outbound delivery.

    Does not contain AI logic. Real WhatsApp Business API is out of scope.
    """

    channel = ChannelType.WHATSAPP

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        text = first_str(payload, ("text", "body", "message", "caption"))
        if not text:
            raise ProviderError("WhatsApp payload is missing message text.")

        return Message(
            text=text,
            channel=ChannelType.WHATSAPP,
            direction=MessageDirection.INBOUND,
            customer_id=first_str(payload, ("wa_id", "user_id", "customer_id", "chat_id")),
            customer_contact=first_str(payload, ("from", "phone", "contact", "profile_name")),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        return message.id
