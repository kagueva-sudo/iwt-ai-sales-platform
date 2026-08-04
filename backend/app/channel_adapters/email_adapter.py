from app.channel_adapters.payload import first_str
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message


class EmailChannelAdapter(ChannelAdapter):
    """Email channel adapter for info@iwt.ru-style inbound mail.

    Does not contain AI logic. Real SMTP/IMAP transport is out of scope.
    """

    channel = ChannelType.EMAIL

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        body = first_str(payload, ("body", "text", "message", "html_body"))
        subject = first_str(payload, ("subject",))
        if not body and not subject:
            raise ProviderError("Email payload is missing subject/body.")

        if subject and body:
            text = f"Subject: {subject}\n\n{body}"
        else:
            text = body or subject or ""

        return Message(
            text=text,
            channel=ChannelType.EMAIL,
            direction=MessageDirection.INBOUND,
            customer_id=first_str(payload, ("customer_id", "message_id", "email_id")),
            customer_contact=first_str(payload, ("from", "from_email", "reply_to", "contact")),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        return message.id
