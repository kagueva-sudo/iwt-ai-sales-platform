from app.api.processing_mappers import map_processing_result_to_message
from app.contracts.decision_router import DecisionRouter
from app.db.session import SessionLocal
from app.domain.customers import Customer
from app.domain.messages import Message
from app.domain.processing import ProcessingResult
from app.repositories.customers import CustomerRepository
from app.repositories.messages import MessageRepository
from app.services.composition import build_decision_router, build_message_pipeline
from app.services.message_pipeline import MessagePipelineService


class MessageService:
    """Gateway entry: Message → Freeze pipeline → DecisionRouter → outbound Message."""

    def __init__(
        self,
        pipeline: MessagePipelineService | None = None,
        decision_router: DecisionRouter | None = None,
    ) -> None:
        self.pipeline = pipeline or build_message_pipeline()
        self.decision_router = decision_router or build_decision_router()

    async def process_message(self, message: Message) -> Message:
        result = await self.process_to_result(message)
        return map_processing_result_to_message(result, inbound=message)

    async def process_to_result(self, message: Message) -> ProcessingResult:
        with SessionLocal() as session:
            message_repository = MessageRepository(session)
            customer_repository = CustomerRepository(session)

            try:
                customer_repository.get_or_create(
                    Customer(id=message.customer_id, contact=message.customer_contact)
                )
                message_repository.add(message)
                session.flush()

                result = await self.pipeline.process(message)
                await self.decision_router.route(result)

                outbound = map_processing_result_to_message(result, inbound=message)
                message_repository.add(outbound)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
