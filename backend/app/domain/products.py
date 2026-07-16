from dataclasses import dataclass


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    description: str | None = None
    price: float | None = None
    stock_qty: int | None = None
    characteristics: dict[str, str] | None = None
    delivery_terms: str | None = None
    source: str = "unknown"


@dataclass(slots=True)
class ProductSearchResult:
    query: str
    products: list[Product]
    source: str

    @property
    def has_confirmed_data(self) -> bool:
        return bool(self.products)

    @property
    def has_confirmed_price(self) -> bool:
        return any(product.price is not None for product in self.products)

    @property
    def has_confirmed_stock(self) -> bool:
        return any(product.stock_qty is not None for product in self.products)

    @property
    def has_confirmed_characteristics(self) -> bool:
        return any(product.characteristics or product.description for product in self.products)

    @property
    def has_confirmed_delivery_terms(self) -> bool:
        return any(product.delivery_terms for product in self.products)
