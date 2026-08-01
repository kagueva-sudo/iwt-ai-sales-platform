from app.contracts.knowledge_provider import KnowledgeProvider
from app.domain.products import Product
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.providers.website_catalog_provider import WebsiteCatalogProvider


class WebsiteKnowledgeProvider(KnowledgeProvider):
    provider_name = "website_provider"

    def __init__(self, website_catalog_provider: WebsiteCatalogProvider | None = None) -> None:
        self.website_catalog_provider = website_catalog_provider or WebsiteCatalogProvider()

    async def search(self, query: str) -> SourceSelectionResult:
        product_result = await self.website_catalog_provider.search_products(query)
        return SourceSelectionResult(
            query=query,
            sources=[self._to_verified_source(product) for product in product_result.products],
        )

    def _to_verified_source(self, product: Product) -> VerifiedSource:
        metadata = {
            "sku": product.sku,
            "source": product.source,
        }
        if product.price is not None:
            metadata["price"] = str(product.price)
        if product.stock_qty is not None:
            metadata["stock_qty"] = str(product.stock_qty)
        if product.delivery_terms:
            metadata["delivery_terms"] = product.delivery_terms

        return VerifiedSource(
            source_id=product.sku,
            source_type=self.provider_name,
            title=product.name,
            content=product.description or product.name,
            metadata=metadata,
        )
