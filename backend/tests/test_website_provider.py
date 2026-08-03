from typing import Any

import pytest

from app.ai_core.source_mapping import products_to_verified_sources
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse
from app.domain.products import ProductSearchResult
from app.integrations.website.client import WebsiteApiClient
from app.integrations.website.exceptions import WebsiteNotConfiguredError, WebsiteUnavailableError
from app.providers.website_provider import WebsiteApiProvider


pytestmark = pytest.mark.asyncio


class FakeWebsiteTransport:
    def __init__(self, payload: Any = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    async def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        if self.error is not None:
            raise self.error
        return self.payload


async def test_website_provider_returns_confirmed_product_data() -> None:
    client = WebsiteApiClient(
        transport=FakeWebsiteTransport(
            payload={
                "products": [
                    {
                        "id": "1",
                        "sku": "P-1",
                        "name": "Насос",
                        "description": "Описание насоса",
                        "price": 1000,
                        "stock_qty": 5,
                        "characteristics": {"power": "1 kW"},
                        "delivery_terms": "2 дня",
                    }
                ]
            }
        )
    )
    provider = WebsiteApiProvider(client=client)

    result = await provider.search("насос")

    assert result.confirmed is True
    assert len(result.products) == 1
    product = result.products[0]
    assert "price" in product.confirmed_fields
    assert "stock_qty" in product.confirmed_fields
    assert product.source == "website"


async def test_website_provider_returns_empty_result_when_no_data() -> None:
    client = WebsiteApiClient(transport=FakeWebsiteTransport(payload={"products": []}))
    provider = WebsiteApiProvider(client=client)

    result = await provider.search("несуществующий товар")

    assert result.confirmed is False
    assert result.products == []
    assert result.errors == []


async def test_website_provider_marks_incomplete_product_without_price_confirmation() -> None:
    client = WebsiteApiClient(
        transport=FakeWebsiteTransport(
            payload={
                "products": [
                    {
                        "sku": "P-1",
                        "name": "Насос",
                        "description": "Описание",
                    }
                ]
            }
        )
    )
    provider = WebsiteApiProvider(client=client)

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
    client = WebsiteApiClient(transport=FakeWebsiteTransport(error=WebsiteUnavailableError("down")))
    provider = WebsiteApiProvider(client=client)

    result = await provider.search("насос")

    assert result.confirmed is False
    assert result.products == []
    assert result.errors[0].code == "WEBSITE_API_UNAVAILABLE"


async def test_website_provider_handles_not_configured_transport() -> None:
    provider = WebsiteApiProvider(client=WebsiteApiClient())

    result = await provider.search("насос")

    assert result.confirmed is False
    assert result.errors[0].code == "WEBSITE_API_NOT_CONFIGURED"


async def test_website_provider_returns_company_and_contact_info() -> None:
    delivery_client = WebsiteApiClient(
        transport=FakeWebsiteTransport(
            payload={"topic": "delivery", "title": "Доставка", "content": "Доставка 2 дня"}
        )
    )
    contacts_client = WebsiteApiClient(
        transport=FakeWebsiteTransport(
            payload={"phone": "+7-000", "email": "info@iwt.ru", "address": "Москва"}
        )
    )

    delivery = await WebsiteApiProvider(client=delivery_client).get_delivery_info()
    contacts = await WebsiteApiProvider(client=contacts_client).get_contacts()

    assert delivery is not None
    assert "content" in delivery.confirmed_fields
    assert contacts is not None
    assert "email" in contacts.confirmed_fields


async def test_default_client_raises_not_configured_without_transport() -> None:
    client = WebsiteApiClient()

    with pytest.raises(WebsiteNotConfiguredError):
        await client.search("насос")
