from app.core.constants import MessageDirection
from app.domain.messages import Message
from app.schemas.gateway import GatewayMessageRequest
from app.schemas.messages import IncomingMessageRequest


def map_incoming_request_to_message(payload: IncomingMessageRequest) -> Message:
    return Message(
        text=payload.text,
        channel=payload.channel,
        direction=MessageDirection.INBOUND,
        customer_id=payload.customer_id,
        customer_contact=payload.customer_contact,
    )


def map_gateway_request_to_message(payload: GatewayMessageRequest) -> Message:
    return Message(
        text=payload.text,
        channel=payload.channel,
        direction=MessageDirection.INBOUND,
        customer_id=payload.customer_id,
        customer_contact=payload.customer_contact,
    )
