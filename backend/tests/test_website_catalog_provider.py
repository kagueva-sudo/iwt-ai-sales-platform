import pytest

from app.ai_core.source_mapping import products_to_verified_sources
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse
from app.integrations.catalog.exceptions import CatalogServerError
from app.integrations.catalog.schemas import CatalogProductDTO
from app.providers.website_catalog_provider import WebsiteCatalogProvider


pytestmark = pytest.mark.asyncio


class FakeCatalogClient:
    def __init__(self, products: list[CatalogProductDTO] | None = None, error: Exception | None = None) -> None:
        self.products = products or []
        self.error = error

    async def search_products(self, query: str) -> list[CatalogProductDTO]:
        if self.error is not None:
            raise self.error
        return self.products


async def test_website_catalog_provider_successful_search() -> None:
    provider = WebsiteCatalogProvider(
        client=FakeCatalogClient(
            products=[
                CatalogProductDTO(
                    id="1",
                    sku="P-1",
                    name="Насос",
                    price=1000,
                    stock_qty=5,
                    characteristics={"power": "1 kW"},
                    delivery_terms="2 дня",
                )
            ]
        )
    )

    result = await provider.search_products("насос")

    assert result.has_confirmed_data
    assert result.has_confirmed_price
    assert result.has_confirmed_stock
    assert result.has_confirmed_characteristics
    assert result.has_confirmed_delivery_terms


async def test_website_catalog_provider_missing_product_requires_data() -> None:
    provider = WebsiteCatalogProvider(client=FakeCatalogClient(products=[]))

    result = await provider.search_products("несуществующий товар")
    validation = AIValidator().validate(
        AIResponse(text="Товар найден.", sources=[result.source]),
        products_to_verified_sources(result),
    )

    assert not result.has_confirmed_data
    assert validation.status == AIValidationStatus.NEEDS_DATA


async def test_website_catalog_provider_missing_price_requires_data() -> None:
    provider = WebsiteCatalogProvider(
        client=FakeCatalogClient(products=[CatalogProductDTO(id="1", sku="P-1", name="Насос")])
    )

    result = await provider.search_products("насос")
    validation = AIValidator().validate(
        AIResponse(text="Цена насоса 1000 рублей.", sources=[result.source], requested_facts={"price"}),
        products_to_verified_sources(result),
    )

    assert validation.status == AIValidationStatus.NEEDS_DATA
    assert "price" in (validation.reason or "")


async def test_website_catalog_provider_missing_availability_requires_data() -> None:
    provider = WebsiteCatalogProvider(
        client=FakeCatalogClient(products=[CatalogProductDTO(id="1", sku="P-1", name="Насос", price=1000)])
    )

    result = await provider.search_products("насос")
    validation = AIValidator().validate(
        AIResponse(text="Насос есть в наличии.", sources=[result.source], requested_facts={"stock"}),
        products_to_verified_sources(result),
    )

    assert validation.status == AIValidationStatus.NEEDS_DATA
    assert "stock" in (validation.reason or "")


async def test_website_catalog_provider_api_error_requires_data() -> None:
    provider = WebsiteCatalogProvider(client=FakeCatalogClient(error=CatalogServerError("catalog failed")))

    result = await provider.search_products("насос")
    validation = AIValidator().validate(
        AIResponse(text="Товар найден.", sources=[result.source]),
        products_to_verified_sources(result),
    )

    assert not result.has_confirmed_data
    assert validation.status == AIValidationStatus.NEEDS_DATA
