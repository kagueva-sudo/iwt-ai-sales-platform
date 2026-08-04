from app.channel_adapters.website_mapper import map_website_payload_to_message
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType
from app.domain.messages import Message


class WebsiteFormAdapter(ChannelAdapter):
    """Website contact form adapter: HTTP payload → domain Message only."""

    channel = ChannelType.WEBSITE_FORM

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        return map_website_payload_to_message(
            channel=ChannelType.WEBSITE_FORM,
            payload=payload,
            text_keys=("message", "text", "body", "comment"),
            missing_text_error="Website form payload is missing message text.",
            customer_id_keys=("customer_id", "form_id", "submission_id"),
            contact_keys=("email", "phone", "contact", "name"),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        return message.id
