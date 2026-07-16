from app.domain.customers import Customer
from app.domain.handoff import HandoffCase
from app.domain.products import ProductSearchResult
from app.providers.crm_provider import CRMProvider
from app.providers.customer_provider import CustomerProvider
from app.providers.product_provider import ProductProvider


class MockProductProvider(ProductProvider):
    provider_name = "mock_product_provider"

    async def search_products(self, query: str) -> ProductSearchResult:
        return ProductSearchResult(query=query, products=[], source=self.provider_name)


class MockCustomerProvider(CustomerProvider):
    provider_name = "mock_customer_provider"

    async def get_customer(self, customer_id: str | None, contact: str | None) -> Customer:
        return Customer(id=customer_id, contact=contact)


class MockCRMProvider(CRMProvider):
    provider_name = "mock_crm_provider"

    async def create_handoff_case(self, handoff_case: HandoffCase) -> str:
        return f"mock-crm-{handoff_case.id}"
