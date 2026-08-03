from abc import ABC, abstractmethod

from app.domain.products import Product
from app.domain.website import CompanyInfo, ContactInfo, WebsiteSearchResult


class WebsiteProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> WebsiteSearchResult:
        """Search public website data and return domain models only."""

    @abstractmethod
    async def get_product_by_sku(self, sku: str) -> Product | None:
        """Return confirmed product data by SKU if it exists."""

    @abstractmethod
    async def get_delivery_info(self) -> CompanyInfo | None:
        """Return confirmed delivery information."""

    @abstractmethod
    async def get_payment_info(self) -> CompanyInfo | None:
        """Return confirmed payment information."""

    @abstractmethod
    async def get_warranty_info(self) -> CompanyInfo | None:
        """Return confirmed warranty information."""

    @abstractmethod
    async def get_contacts(self) -> ContactInfo | None:
        """Return confirmed company contacts."""
