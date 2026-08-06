from uuid import uuid4

from app.channel_adapters.max_payload import (
    extract_max_chat_id,
    extract_max_external_message_id,
    extract_max_text,
    extract_max_user_id,
    extract_max_username,
    is_max_processable_update,
)
from app.contracts.channel_adapter import ChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.integrations.max.config import get_max_config, is_max_configured
from app.integrations.max.exceptions import MaxError, MaxNotConfiguredError
from app.integrations.max.transport import HttpMaxTransport


class MaxChannelAdapter(ChannelAdapter):
    """MAX channel adapter: MAX webhook/polling payload → domain Message → MAX API send.

    Does not contain AI logic. Uses HttpMaxTransport when MAX_BOT_TOKEN is configured.
    """

    channel = ChannelType.MAX

    def __init__(self, transport: HttpMaxTransport | None = None) -> None:
        self.sent: list[Message] = []
        self._routes: dict[str, dict[str, str]] = {}
        self._transport = transport

    async def normalize_incoming(self, payload: dict[str, object]) -> Message:
        if not is_max_processable_update(payload):
            raise ProviderError("MAX update is not a processable text message.")

        text = extract_max_text(payload)
        if not text:
            raise ProviderError("MAX payload is missing message text.")

        user_id = extract_max_user_id(payload)
        chat_id = extract_max_chat_id(payload)
        if not user_id and not chat_id:
            raise ProviderError("MAX payload is missing user_id/chat_id.")

        customer_id = user_id or chat_id or ""
        if customer_id:
            route: dict[str, str] = {}
            if user_id:
                route["user_id"] = user_id
            if chat_id:
                route["chat_id"] = chat_id
            self._routes[customer_id] = route

        external_id = extract_max_external_message_id(payload)
        message = Message(
            text=text,
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id=customer_id,
            customer_contact=extract_max_username(payload),
            id=external_id or str(uuid4()),
        )
        return message

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        transport = self._resolve_transport()
        if transport is None:
            return message.id

        route = self._routes.get(message.customer_id or "", {})
        user_id = route.get("user_id") or message.customer_id
        chat_id = route.get("chat_id")

        try:
            result = await transport.send_text(
                message.text,
                user_id=user_id if not chat_id else None,
                chat_id=chat_id,
            )
        except MaxError as exc:
            raise ProviderError(str(exc)) from exc

        message_block = result.get("message")
        if isinstance(message_block, dict):
            mid = message_block.get("body", {}).get("mid") if isinstance(message_block.get("body"), dict) else None
            if mid:
                return str(mid)
        return message.id

    def _resolve_transport(self) -> HttpMaxTransport | None:
        if self._transport is not None:
            return self._transport
        if not is_max_configured():
            return None
        config = get_max_config()
        return HttpMaxTransport(
            bot_token=config.bot_token,
            base_url=str(config.api_base_url),
            timeout=config.timeout,
            verify_tls=not config.tls_insecure,
        )
