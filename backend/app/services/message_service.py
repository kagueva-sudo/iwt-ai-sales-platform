from app.ai_core.openai_provider import OpenAIProvider
from app.ai_core.orchestrator import AISalesCore
from app.ai_core.validator import AIValidator
from app.core.config import get_settings
from app.core.constants import MessageDirection
from app.db.session import SessionLocal
from app.domain.customers import Customer
from app.domain.messages import Message
from app.providers.mock_providers import MockCRMProvider, MockCustomerProvider, MockProductProvider
from app.repositories.ai_logs import AILogRepository
from app.repositories.customers import CustomerRepository
from app.repositories.errors import ErrorLogRepository
from app.repositories.handoff import HandoffRepository
from app.repositories.messages import MessageRepository
from app.schemas.messages import IncomingMessageRequest
from app.services.handoff_service import HandoffService


def build_ai_core(handoff_repository: HandoffRepository | None = None) -> AISalesCore:
    settings = get_settings()
    crm_provider = MockCRMProvider()
    return AISalesCore(
        llm_provider=OpenAIProvider(settings.openai_api_key, settings.openai_model),
        product_provider=MockProductProvider(),
        customer_provider=MockCustomerProvider(),
        handoff_service=HandoffService(crm_provider, handoff_repository),
        validator=AIValidator(),
    )


class MessageService:
    def __init__(self, ai_core: AISalesCore | None = None) -> None:
        self.ai_core = ai_core

    async def process_incoming_message(self, payload: IncomingMessageRequest) -> Message:
        with SessionLocal() as session:
            message_repository = MessageRepository(session)
            ai_log_repository = AILogRepository(session)
            customer_repository = CustomerRepository(session)
            error_repository = ErrorLogRepository(session)
            handoff_repository = HandoffRepository(session)
            ai_core = self.ai_core or build_ai_core(handoff_repository)

            message = Message(
                text=payload.text,
                channel=payload.channel,
                direction=MessageDirection.INBOUND,
                customer_id=payload.customer_id,
                customer_contact=payload.customer_contact,
            )

            try:
                customer_repository.get_or_create(Customer(id=payload.customer_id, contact=payload.customer_contact))
                message_repository.add(message)
                session.flush()

                result = await ai_core.process_message(message)

                message_repository.add(result.outbound_message)
                ai_log_repository.add(
                    message_id=result.inbound_message.id,
                    request_text=result.inbound_message.text,
                    response_text=result.ai_response.text,
                    validation_status=result.validation_result.status.value,
                )
                if result.error is not None:
                    error_repository.add(
                        message_id=result.inbound_message.id,
                        error_type="ai_provider_error",
                        error_message=result.error,
                    )

                session.commit()
                return result.outbound_message
            except Exception:
                session.rollback()
                raise
