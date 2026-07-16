from app.ai_core.openai_provider import OpenAIProvider
from app.ai_core.orchestrator import AISalesCore
from app.ai_core.validator import AIValidator
from app.core.config import get_settings
from app.core.constants import MessageDirection
from app.domain.messages import Message
from app.providers.mock_providers import MockCRMProvider, MockCustomerProvider, MockProductProvider
from app.schemas.messages import IncomingMessageRequest
from app.services.handoff_service import HandoffService


def build_ai_core() -> AISalesCore:
    settings = get_settings()
    crm_provider = MockCRMProvider()
    return AISalesCore(
        llm_provider=OpenAIProvider(settings.openai_api_key, settings.openai_model),
        product_provider=MockProductProvider(),
        customer_provider=MockCustomerProvider(),
        handoff_service=HandoffService(crm_provider),
        validator=AIValidator(),
    )


class MessageService:
    def __init__(self, ai_core: AISalesCore | None = None) -> None:
        self.ai_core = ai_core or build_ai_core()

    async def process_incoming_message(self, payload: IncomingMessageRequest) -> Message:
        message = Message(
            text=payload.text,
            channel=payload.channel,
            direction=MessageDirection.INBOUND,
            customer_id=payload.customer_id,
            customer_contact=payload.customer_contact,
        )
        return await self.ai_core.process_message(message)
