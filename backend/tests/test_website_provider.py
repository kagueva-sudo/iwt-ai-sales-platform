from typing import Any

import pytest

from app.ai_core.source_mapping import products_to_verified_sources
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse
from app.domain.products import ProductSearchResult
from app.integrations.website.client import WebsiteApiClient
from app.integrations.website.exceptions import WebsiteNotConfiguredError, WebsiteUnavailableError
from app.integrations.website.schemas import WebsiteProductDTO, WebsiteSearchResponseDTO
from app.providers.website_provider import WebsiteApiProvider


pytestmark = pytest.mark.asyncio


class StubWebsiteClient:
    def __init__(
        self,
        search_result: WebsiteSearchResponseDTO | None = None,
        product: WebsiteProductDTO | None = None,
        error: Exception | None = None,
    ) -> None:
        self.search_result = search_result or WebsiteSearchResponseDTO()
        self.product = product
        self.error = error

    async def search(self, query: str, limit: int = 10) -> WebsiteSearchResponseDTO:
        if self.error is not None:
            raise self.error
        return self.search_result

    async def get_product_by_sku(self, sku: str) -> WebsiteProductDTO:
        if self.error is not None:
            raise self.error
        if self.product is None:
            from app.integrations.website.exceptions import WebsiteNotFoundError

            raise WebsiteNotFoundError("missing")
        return self.product

    async def get_delivery_info(self) -> Any:
        from app.integrations.website.exceptions import WebsiteNotFoundError

        raise WebsiteNotFoundError("n/a")

    async def get_payment_info(self) -> Any:
        from app.integrations.website.exceptions import WebsiteNotFoundError

        raise WebsiteNotFoundError("n/a")

    async def get_warranty_info(self) -> Any:
        from app.integrations.website.exceptions import WebsiteNotFoundError

        raise WebsiteNotFoundError("n/a")

    async def get_contacts(self) -> Any:
        from app.integrations.website.exceptions import WebsiteNotFoundError

        raise WebsiteNotFoundError("n/a")


async def test_website_provider_returns_confirmed_product_data() -> None:
    client = StubWebsiteClient(
        search_result=WebsiteSearchResponseDTO(
            products=[
                WebsiteProductDTO.model_validate(
                    {
                        "id": "112415",
                        "sku": "disk-hpe-600",
                        "name": "Насос",
                        "description": "Описание насоса",
                        "price": 1000,
                        "currency": "RUB",
                        "stock_qty": 5,
                        "characteristics": {"power": "1 kW"},
                        "delivery_terms": "2 дня",
                    }
                )
            ]
        )
    )
    provider = WebsiteApiProvider(client=client)  # type: ignore[arg-type]

    result = await provider.search("насос")

    assert result.confirmed is True
    assert len(result.products) == 1
    product = result.products[0]
    assert product.sku == "disk-hpe-600"
    assert "price" in product.confirmed_fields
    assert "stock_qty" in product.confirmed_fields
    assert product.source == "website"


async def test_website_provider_returns_empty_result_when_no_data() -> None:
    provider = WebsiteApiProvider(client=StubWebsiteClient())  # type: ignore[arg-type]

    result = await provider.search("несуществующий товар")

    assert result.confirmed is False
    assert result.products == []
    assert result.errors == []


async def test_website_provider_marks_incomplete_product_without_price_confirmation() -> None:
    client = StubWebsiteClient(
        search_result=WebsiteSearchResponseDTO(
            products=[
                WebsiteProductDTO.model_validate(
                    {
                        "sku": "P-1",
                        "name": "Насос",
                        "description": "Описание",
                    }
                )
            ]
        )
    )
    provider = WebsiteApiProvider(client=client)  # type: ignore[arg-type]

    result = await provider.search("насос")
    product = result.products[0]
    product_data = ProductSearchResult(query="насос", products=[product], source="website")
    validation = AIValidator().validate(
        AIResponse(text="Цена насоса 1000 рублей.", sources=["website"], requested_facts={"price"}),
        products_to_verified_sources(product_data),
    )

    assert "price" not in product.confirmed_fields
    assert validation.status == AIValidationStatus.NEEDS_DATA


async def test_website_provider_handles_unavailable_source() -> None:
    provider = WebsiteApiProvider(
        client=StubWebsiteClient(error=WebsiteUnavailableError("down"))  # type: ignore[arg-type]
    )

    result = await provider.search("насос")

    assert result.confirmed is False
    assert result.products == []
    assert result.errors[0].code == "WEBSITE_API_UNAVAILABLE"


async def test_website_provider_handles_not_configured_transport() -> None:
    provider = WebsiteApiProvider(client=WebsiteApiClient())

    result = await provider.search("насос")

    assert result.confirmed is False
    assert result.errors[0].code == "WEBSITE_API_NOT_CONFIGURED"


async def test_website_provider_returns_none_for_missing_company_info() -> None:
    provider = WebsiteApiProvider(client=StubWebsiteClient())  # type: ignore[arg-type]

    assert await provider.get_delivery_info() is None
    assert await provider.get_contacts() is None


async def test_default_client_raises_not_configured_without_transport() -> None:
    client = WebsiteApiClient()

    with pytest.raises(WebsiteNotConfiguredError):
        await client.search("насос")
