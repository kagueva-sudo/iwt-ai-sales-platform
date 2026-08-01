from app.domain.products import Product, ProductSearchResult
from app.integrations.catalog.client import CatalogApiClient
from app.integrations.catalog.config import get_catalog_config
from app.integrations.catalog.exceptions import CatalogError
from app.integrations.catalog.schemas import CatalogProductDTO
from app.providers.product_provider import ProductProvider


class WebsiteCatalogProvider(ProductProvider):
    provider_name = "website_catalog"

    def __init__(self, client: CatalogApiClient | None = None) -> None:
        self.client = client or self._build_client()

    async def search_products(self, query: str) -> ProductSearchResult:
        try:
            catalog_products = await self.client.search_products(query)
        except CatalogError:
            return ProductSearchResult(query=query, products=[], source=self.provider_name)

        return ProductSearchResult(
            query=query,
            products=[self._to_domain_product(product) for product in catalog_products],
            source=self.provider_name,
        )

    def _build_client(self) -> CatalogApiClient:
        config = get_catalog_config()
        if config.api_url is None:
            return CatalogApiClient(base_url="http://catalog-api-not-configured.local", timeout=config.timeout)
        return CatalogApiClient(
            base_url=str(config.api_url),
            api_key=config.api_key,
            timeout=config.timeout,
        )

    def _to_domain_product(self, product: CatalogProductDTO) -> Product:
        return Product(
            sku=product.sku,
            name=product.name,
            description=product.description,
            price=product.price,
            stock_qty=product.stock_qty,
            characteristics=product.characteristics,
            delivery_terms=product.delivery_terms,
            source=self.provider_name,
        )
