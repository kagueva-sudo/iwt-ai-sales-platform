from app.channel_adapters.payload import first_str
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.integrations.email.config import get_email_config, is_email_configured
from app.integrations.email.exceptions import EmailError, EmailNotConfiguredError
from app.integrations.email.smtp_client import SmtpEmailClient


class EmailChannelAdapter(ChannelAdapter):
    """Email channel adapter for iwt.iwt@ya.ru-style inbound/outbound mail.

    Does not contain AI logic. Auto-replies are disabled by EmailInboxPolicy;
    SMTP send is used for manager replies from /inbox.
    """

    channel = ChannelType.EMAIL

    def __init__(self, smtp_client: SmtpEmailClient | None = None) -> None:
        self.sent: list[Message] = []
        self._smtp_client = smtp_client

    def _smtp(self) -> SmtpEmailClient:
        if self._smtp_client is not None:
            return self._smtp_client
        return SmtpEmailClient(get_email_config())

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        body = first_str(payload, ("body", "text", "message", "html_body"))
        subject = first_str(payload, ("subject",))
        if not body and not subject:
            raise ProviderError("Email payload is missing subject/body.")

        if subject and body:
            text = f"Subject: {subject}\n\n{body}"
        else:
            text = body or subject or ""

        message_id = first_str(
            payload,
            ("message_id", "email_id", "Message-ID", "message-id"),
        )
        from_address = first_str(payload, ("from", "from_email", "reply_to", "contact"))
        metadata: dict[str, str] = {}
        if message_id:
            metadata["email_message_id"] = message_id
        if subject:
            metadata["email_subject"] = subject
        imap_uid = first_str(payload, ("imap_uid", "uid"))
        if imap_uid:
            metadata["imap_uid"] = imap_uid

        return Message(
            text=text,
            channel=ChannelType.EMAIL,
            direction=MessageDirection.INBOUND,
            customer_id=first_str(payload, ("customer_id",)) or message_id,
            customer_contact=from_address,
            metadata=metadata,
        )

    async def send_message(self, message: Message) -> str:
        """Send only explicit manager replies (metadata outbound_kind=manager_reply)."""
        self.sent.append(message)
        if message.metadata.get("outbound_kind") != "manager_reply":
            return message.id
        if not is_email_configured():
            raise EmailNotConfiguredError("Email SMTP is not configured.")
        to_address = (message.customer_contact or "").strip()
        subject = message.metadata.get("email_subject") or "Re: IWT"
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        try:
            self._smtp().send(
                to_address=to_address,
                subject=subject,
                body=message.text,
                in_reply_to=message.metadata.get("email_message_id"),
                references=message.metadata.get("email_message_id"),
            )
        except EmailError:
            raise
        return message.id
