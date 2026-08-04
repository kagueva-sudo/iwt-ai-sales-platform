from app.channel_adapters.website_mapper import map_website_payload_to_message
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType
from app.domain.messages import Message


class WebsiteChatAdapter(ChannelAdapter):
    """Website online chat adapter: chat payload → domain Message only."""

    channel = ChannelType.WEBSITE_CHAT

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        return map_website_payload_to_message(
            channel=ChannelType.WEBSITE_CHAT,
            payload=payload,
            text_keys=("text", "message", "body"),
            missing_text_error="Website chat payload is missing message text.",
            customer_id_keys=("visitor_id", "session_id", "customer_id", "chat_id"),
            contact_keys=("contact", "email", "phone", "name"),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        return message.id
