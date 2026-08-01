from pydantic import BaseModel, Field


class CatalogProductDTO(BaseModel):
    id: str
    sku: str
    name: str
    description: str | None = None
    price: float | None = None
    stock_qty: int | None = None
    characteristics: dict[str, str] = Field(default_factory=dict)
    delivery_terms: str | None = None


class CatalogSearchResponseDTO(BaseModel):
    items: list[CatalogProductDTO] = Field(default_factory=list)


class CatalogPriceDTO(BaseModel):
    product_id: str
    price: float | None = None
    currency: str = "RUB"


class CatalogAvailabilityDTO(BaseModel):
    product_id: str
    stock_qty: int | None = None
    available: bool | None = None
