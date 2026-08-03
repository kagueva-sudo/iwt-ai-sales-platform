from app.schemas.gateway import GatewayMessageRequest
from app.schemas.messages import IncomingMessageRequest


class GatewayService:
    def normalize(self, payload: GatewayMessageRequest) -> IncomingMessageRequest:
        return IncomingMessageRequest(
            channel=payload.channel,
            customer_id=payload.customer_id,
            customer_contact=payload.customer_contact,
            text=payload.text,
        )
