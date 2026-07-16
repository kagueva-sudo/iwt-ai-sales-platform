from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import SAFE_HANDOFF_MESSAGE, SYSTEM_PROMPT
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus, HandoffReason, MessageDirection, ProcessingStatus
from app.domain.ai import AIResponse
from app.domain.messages import Message
from app.providers.customer_provider import CustomerProvider
from app.providers.product_provider import ProductProvider
from app.services.handoff_service import HandoffService


class AISalesCore:
    def __init__(
        self,
        llm_provider: LLMProvider,
        product_provider: ProductProvider,
        customer_provider: CustomerProvider,
        handoff_service: HandoffService,
        validator: AIValidator,
    ) -> None:
        self.llm_provider = llm_provider
        self.product_provider = product_provider
        self.customer_provider = customer_provider
        self.handoff_service = handoff_service
        self.validator = validator

    async def process_message(self, message: Message) -> Message:
        await self.customer_provider.get_customer(message.customer_id, message.customer_contact)
        product_data = await self.product_provider.search_products(message.text)

        if not product_data.has_confirmed_data:
            ai_response = AIResponse(
                text=SAFE_HANDOFF_MESSAGE,
                sources=[product_data.source],
                needs_handoff=True,
                handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
            )
        else:
            draft = await self.llm_provider.generate_response(SYSTEM_PROMPT, message.text)
            ai_response = AIResponse(text=draft, sources=[product_data.source])

        validation = self.validator.validate(ai_response, product_data)

        if validation.status != AIValidationStatus.APPROVED:
            await self.handoff_service.create_handoff(
                channel=message.channel,
                message=message.text,
                reason=ai_response.handoff_reason or HandoffReason.NO_CONFIRMED_DATA,
                customer_id=message.customer_id,
                customer_contact=message.customer_contact,
                ai_recommendation=validation.reason,
            )
            message.status = ProcessingStatus.HANDOFF_REQUIRED
            response_text = validation.approved_text or SAFE_HANDOFF_MESSAGE
        else:
            message.status = ProcessingStatus.PROCESSED
            response_text = validation.approved_text or ai_response.text

        return Message(
            text=response_text,
            channel=message.channel,
            direction=MessageDirection.OUTBOUND,
            customer_id=message.customer_id,
            customer_contact=message.customer_contact,
            status=message.status,
        )
