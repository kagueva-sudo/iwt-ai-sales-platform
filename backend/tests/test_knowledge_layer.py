import pytest

from app.domain.products import Product
from app.domain.website import WebsiteSearchResult
from app.knowledge_layer.knowledge_base_provider import InMemoryKnowledgeBaseProvider
from app.knowledge_layer.schemas import KnowledgeItem
from app.knowledge_layer.source_selector import SourceSelector
from app.knowledge_layer.website_provider import WebsiteKnowledgeProvider


pytestmark = pytest.mark.asyncio


class FakeWebsiteProvider:
    async def search(self, query: str) -> WebsiteSearchResult:
        return WebsiteSearchResult(
            query=query,
            products=[
                Product(
                    sku="P-1",
                    name="Насос",
                    description="Описание насоса",
                    price=1000,
                    stock_qty=5,
                    source="website_catalog",
                    confirmed_fields={"sku", "name", "description", "price", "stock_qty"},
                )
            ],
        )

    async def get_product_by_sku(self, sku: str) -> Product | None:
        return None

    async def get_delivery_info(self) -> None:
        return None

    async def get_payment_info(self) -> None:
        return None

    async def get_warranty_info(self) -> None:
        return None

    async def get_contacts(self) -> None:
        return None


async def test_knowledge_base_provider_returns_confirmed_source() -> None:
    provider = InMemoryKnowledgeBaseProvider(
        items=[KnowledgeItem(id="faq-1", title="Доставка", content="Доставка занимает 2 дня.", tags=["доставка"])]
    )

    result = await provider.search("доставка")

    assert result.has_sources
    assert result.sources[0].source_type == "knowledge_base"


async def test_website_knowledge_provider_returns_product_source() -> None:
    provider = WebsiteKnowledgeProvider(FakeWebsiteProvider())

    result = await provider.search("насос")

    assert result.has_sources
    assert result.sources[0].source_type == "website_provider"
    assert result.sources[0].metadata["price"] == "1000"


async def test_source_selector_combines_sources_in_provider_order() -> None:
    knowledge_provider = InMemoryKnowledgeBaseProvider(
        items=[KnowledgeItem(id="faq-1", title="Насос", content="FAQ по насосам.")]
    )
    website_provider = WebsiteKnowledgeProvider(FakeWebsiteProvider())
    selector = SourceSelector([knowledge_provider, website_provider])

    result = await selector.select_sources("насос")

    assert [source.source_type for source in result.sources] == ["knowledge_base", "website_provider"]
