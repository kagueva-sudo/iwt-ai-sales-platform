from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    id: str | None = None
    description: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    price: float | None = None
    currency: str = "RUB"
    availability_status: str | None = None
    stock_qty: int | None = None
    characteristics: dict[str, str] | None = None
    delivery_terms: str | None = None
    payment_terms: str | None = None
    warranty_terms: str | None = None
    source: str = "unknown"
    source_url: str | None = None
    updated_at: datetime | None = None
    confirmed_fields: set[str] = field(default_factory=set)

    def is_field_confirmed(self, field_name: str) -> bool:
        """Return True only if the field is explicitly listed in confirmed_fields.

        An empty confirmed_fields set never confirms any field.
        """
        return field_name in self.confirmed_fields


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
        return any(product.price is not None and product.is_field_confirmed("price") for product in self.products)

    @property
    def has_confirmed_stock(self) -> bool:
        return any(
            (product.stock_qty is not None or product.availability_status is not None)
            and (
                product.is_field_confirmed("stock_qty")
                or product.is_field_confirmed("availability_status")
            )
            for product in self.products
        )

    @property
    def has_confirmed_characteristics(self) -> bool:
        return any(
            (product.characteristics or product.description)
            and (
                product.is_field_confirmed("characteristics")
                or product.is_field_confirmed("description")
            )
            for product in self.products
        )

    @property
    def has_confirmed_delivery_terms(self) -> bool:
        return any(
            product.delivery_terms and product.is_field_confirmed("delivery_terms")
            for product in self.products
        )
