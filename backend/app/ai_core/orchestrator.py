from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import SAFE_HANDOFF_MESSAGE, SYSTEM_PROMPT
from app.ai_core.source_mapping import products_to_verified_sources
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus, HandoffReason, MessageDirection, ProcessingStatus
from app.core.errors import ProviderError
from app.domain.ai import AIProcessingResult, AIResponse
from app.domain.messages import Message
from app.providers.customer_provider import CustomerProvider
from app.providers.product_provider import ProductProvider
from app.services.handoff_service import HandoffService


class AISalesCore:
    """Legacy orchestrator used by MessageService.

    Prefer AICore + MessagePipelineService for Architecture Freeze v2.2 pipeline.
    """

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

    async def process_message(self, message: Message) -> AIProcessingResult:
        await self.customer_provider.get_customer(message.customer_id, message.customer_contact)
        product_data = await self.product_provider.search_products(message.text)
        requested_facts = self._detect_requested_commercial_facts(message.text)
        error: str | None = None

        if not product_data.has_confirmed_data:
            ai_response = AIResponse(
                text=SAFE_HANDOFF_MESSAGE,
                sources=[product_data.source],
                requested_facts=requested_facts,
                needs_handoff=True,
                handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
            )
        else:
            try:
                draft = await self.llm_provider.generate_response(SYSTEM_PROMPT, message.text)
                ai_response = AIResponse(text=draft, sources=[product_data.source], requested_facts=requested_facts)
            except ProviderError as exc:
                error = str(exc)
                ai_response = AIResponse(
                    text=SAFE_HANDOFF_MESSAGE,
                    sources=[product_data.source],
                    requested_facts=requested_facts,
                    needs_handoff=True,
                    handoff_reason=HandoffReason.LLM_ERROR,
                )

        verification = products_to_verified_sources(product_data)
        validation = self.validator.validate(ai_response, verification)
        handoff_id: str | None = None

        if validation.status != AIValidationStatus.APPROVED:
            handoff_id = await self.handoff_service.create_handoff(
                channel=message.channel,
                message=message.text,
                reason=ai_response.handoff_reason or HandoffReason.NO_CONFIRMED_DATA,
                customer_id=message.customer_id,
                customer_contact=message.customer_contact,
                history=[message.text],
                ai_response=ai_response.text,
                ai_recommendation=validation.reason,
            )
            message.status = ProcessingStatus.HANDOFF_REQUIRED
            response_text = validation.approved_text or SAFE_HANDOFF_MESSAGE
        else:
            message.status = ProcessingStatus.PROCESSED
            response_text = validation.approved_text or ai_response.text

        outbound_message = Message(
            text=response_text,
            channel=message.channel,
            direction=MessageDirection.OUTBOUND,
            customer_id=message.customer_id,
            customer_contact=message.customer_contact,
            status=message.status,
        )
        return AIProcessingResult(
            inbound_message=message,
            outbound_message=outbound_message,
            ai_response=ai_response,
            validation_result=validation,
            handoff_id=handoff_id,
            error=error,
        )

    def _detect_requested_commercial_facts(self, text: str) -> set[str]:
        lowered = text.lower()
        fact_keywords = {
            "price": ("цена", "стоимость", "сколько стоит", "прайс"),
            "stock": ("налич", "остат", "на складе"),
            "characteristics": ("характерист", "параметр", "мощность", "размер", "габарит"),
            "delivery_terms": ("срок", "поставка", "доставка", "когда будет"),
        }
        return {
            fact
            for fact, keywords in fact_keywords.items()
            if any(keyword in lowered for keyword in keywords)
        }
