from abc import abstractmethod

from app.domain.products import ProductSearchResult
from app.providers.base import Provider


class ProductProvider(Provider):
    @abstractmethod
    async def search_products(self, query: str) -> ProductSearchResult:
        """Return confirmed product data from 1C, catalog, or knowledge base."""
