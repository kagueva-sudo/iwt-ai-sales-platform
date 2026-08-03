from app.domain.products import Product, ProductSearchResult
from app.domain.sources import VerifiedSource


def product_to_verified_source(product: Product, source_type: str | None = None) -> VerifiedSource:
    """Map a Product into VerifiedSource for AIValidator (legacy product path)."""
    return VerifiedSource(
        source_id=product.sku,
        source_type=source_type or product.source,
        title=product.name,
        content=product.description or product.name,
        metadata={
            "confirmed_fields": ",".join(sorted(product.confirmed_fields)),
        },
    )


def products_to_verified_sources(product_data: ProductSearchResult) -> list[VerifiedSource]:
    return [
        product_to_verified_source(product, source_type=product_data.source)
        for product in product_data.products
    ]
