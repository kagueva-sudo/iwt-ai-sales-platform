from uuid import uuid4

from app.channel_adapters.whatsapp_payload import (
    extract_whatsapp_contact_name,
    extract_whatsapp_external_message_id,
    extract_whatsapp_text,
    extract_whatsapp_wa_id,
    is_whatsapp_processable_update,
)
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.integrations.whatsapp.config import get_whatsapp_config, is_whatsapp_configured
from app.integrations.whatsapp.exceptions import WhatsAppError
from app.integrations.whatsapp.transport import HttpWhatsAppTransport


class WhatsAppChannelAdapter(ChannelAdapter):
    """WhatsApp channel adapter: Cloud API / simplified payload → Message → send.

    Does not contain AI logic. Uses HttpWhatsAppTransport when credentials are set.
    """

    channel = ChannelType.WHATSAPP

    def __init__(self, transport: HttpWhatsAppTransport | None = None) -> None:
        self.sent: list[Message] = []
        self._routes: dict[str, str] = {}
        self._transport = transport

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        if not is_whatsapp_processable_update(payload):
            raise ProviderError("WhatsApp update is not a processable text message.")

        text = extract_whatsapp_text(payload)
        if not text:
            raise ProviderError("WhatsApp payload is missing message text.")

        wa_id = extract_whatsapp_wa_id(payload)
        if not wa_id:
            raise ProviderError("WhatsApp payload is missing wa_id/from.")

        self._routes[wa_id] = wa_id

        external_id = extract_whatsapp_external_message_id(payload)
        return Message(
            text=text,
            channel=ChannelType.WHATSAPP,
            direction=MessageDirection.INBOUND,
            customer_id=wa_id,
            customer_contact=extract_whatsapp_contact_name(payload) or wa_id,
            id=external_id or str(uuid4()),
        )

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        transport = self._resolve_transport()
        if transport is None:
            return message.id

        to = self._routes.get(message.customer_id or "") or message.customer_id
        if not to:
            raise ProviderError("WhatsApp outbound requires customer_id (wa_id).")

        try:
            result = await transport.send_text(message.text, to=to)
        except WhatsAppError as exc:
            raise ProviderError(str(exc)) from exc

        messages = result.get("messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict) and first.get("id"):
                return str(first["id"])
        return message.id

    def _resolve_transport(self) -> HttpWhatsAppTransport | None:
        if self._transport is not None:
            return self._transport
        if not is_whatsapp_configured():
            return None
        config = get_whatsapp_config()
        return HttpWhatsAppTransport(
            access_token=config.access_token,
            phone_number_id=config.phone_number_id,
            base_url=str(config.api_base_url),
            api_version=config.api_version,
            timeout=config.timeout,
        )
