from __future__ import annotations

from app.contracts.website_provider import WebsiteProvider
from app.domain.products import Product
from app.domain.website import CompanyInfo, ContactInfo, WebsiteSearchResult
from app.integrations.website_store.client import StoreProductDTO, WebsiteStoreClient
from app.integrations.website_store.config import get_website_store_config


class WebsiteStoreProvider(WebsiteProvider):
    """WebsiteProvider backed by public iwt.ru HTML catalog (no Bitrix access)."""

    provider_name = "website_store"

    def __init__(self, client: WebsiteStoreClient | None = None) -> None:
        self.client = client or WebsiteStoreClient(get_website_store_config())

    async def search(self, query: str) -> WebsiteSearchResult:
        items = await self.client.search_products(query)
        return WebsiteSearchResult(
            query=query,
            products=[self._to_product(item) for item in items],
        )

    async def get_product_by_sku(self, sku: str) -> Product | None:
        items = await self.client.search_products(sku, limit=5)
        for item in items:
            if item.sku == sku or sku.lower() in item.name.lower():
                return self._to_product(item)
        return None

    async def get_delivery_info(self) -> CompanyInfo | None:
        return None

    async def get_payment_info(self) -> CompanyInfo | None:
        return None

    async def get_warranty_info(self) -> CompanyInfo | None:
        return None

    async def get_contacts(self) -> ContactInfo | None:
        return None

    def _to_product(self, item: StoreProductDTO) -> Product:
        confirmed = {"sku", "name", "description"}
        parts = [item.name]
        if item.price is not None:
            parts.append(f"Цена на сайте: {item.price:,.0f} руб.".replace(",", " "))
            confirmed.add("price")
        parts.append(f"Ссылка: {item.url}")
        return Product(
            sku=item.sku,
            name=item.name,
            description=". ".join(parts),
            price=item.price,
            currency=item.currency,
            source=self.provider_name,
            source_url=item.url,
            confirmed_fields=confirmed,
        )