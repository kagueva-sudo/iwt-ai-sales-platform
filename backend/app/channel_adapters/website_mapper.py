from app.channel_adapters.payload import first_str
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message


def map_website_payload_to_message(
    *,
    channel: ChannelType,
    payload: dict[str, object],
    text_keys: tuple[str, ...],
    missing_text_error: str,
    customer_id_keys: tuple[str, ...],
    contact_keys: tuple[str, ...],
) -> Message:
    """Shared website channel mapper: payload → domain Message only."""
    text = first_str(payload, text_keys)
    if not text:
        raise ProviderError(missing_text_error)

    return Message(
        text=text,
        channel=channel,
        direction=MessageDirection.INBOUND,
        customer_id=first_str(payload, customer_id_keys),
        customer_contact=first_str(payload, contact_keys),
    )
