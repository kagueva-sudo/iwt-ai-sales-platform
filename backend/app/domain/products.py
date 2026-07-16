from dataclasses import dataclass


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    description: str | None = None
    price: float | None = None
    stock_qty: int | None = None
    source: str = "unknown"


@dataclass(slots=True)
class ProductSearchResult:
    query: str
    products: list[Product]
    source: str

    @property
    def has_confirmed_data(self) -> bool:
        return bool(self.products)
