import pytest

from app.ai_core.llm_provider import LLMProvider
from app.ai_core.orchestrator import AISalesCore
from app.ai_core.validator import AIValidator
from app.core.constants import ChannelType, HandoffReason, MessageDirection, ProcessingStatus
from app.core.errors import ProviderError
from app.domain.customers import Customer
from app.domain.handoff import HandoffCase
from app.domain.messages import Message
from app.domain.products import Product, ProductSearchResult
from app.providers.crm_provider import CRMProvider
from app.providers.customer_provider import CustomerProvider
from app.providers.product_provider import ProductProvider
from app.services.handoff_service import HandoffService


class FailingLLMProvider(LLMProvider):
    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        raise ProviderError("LLM failed.")


class ConfirmedProductProvider(ProductProvider):
    provider_name = "test_product_provider"

    async def search_products(self, query: str) -> ProductSearchResult:
        return ProductSearchResult(
            query=query,
            products=[
                Product(
                    sku="P-1",
                    name="Насос",
                    price=1000,
                    source="1c",
                    confirmed_fields={"sku", "name", "price"},
                )
            ],
            source="1c",
        )


class TestCustomerProvider(CustomerProvider):
    provider_name = "test_customer_provider"

    async def get_customer(self, customer_id: str | None, contact: str | None) -> Customer:
        return Customer(id=customer_id, contact=contact)


class CollectingCRMProvider(CRMProvider):
    provider_name = "test_crm_provider"

    def __init__(self) -> None:
        self.handoff_cases: list[HandoffCase] = []

    async def create_handoff_case(self, handoff_case: HandoffCase) -> str:
        self.handoff_cases.append(handoff_case)
        return f"crm-{handoff_case.id}"


@pytest.mark.asyncio
async def test_ai_core_falls_back_to_handoff_on_llm_error() -> None:
    crm_provider = CollectingCRMProvider()
    ai_core = AISalesCore(
        llm_provider=FailingLLMProvider(),
        product_provider=ConfirmedProductProvider(),
        customer_provider=TestCustomerProvider(),
        handoff_service=HandoffService(crm_provider),
        validator=AIValidator(),
    )
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await ai_core.process_message(message)

    assert result.outbound_message.status == ProcessingStatus.HANDOFF_REQUIRED
    assert result.ai_response.handoff_reason == HandoffReason.LLM_ERROR
    assert result.error == "LLM failed."
    assert len(crm_provider.handoff_cases) == 1
