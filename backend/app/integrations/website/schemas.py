from pydantic import BaseModel, Field


class WebsiteProductDTO(BaseModel):
    id: str | None = None
    sku: str
    name: str
    description: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    price: float | None = None
    currency: str = "RUB"
    availability_status: str | None = None
    stock_qty: int | None = None
    characteristics: dict[str, str] = Field(default_factory=dict)
    delivery_terms: str | None = None
    payment_terms: str | None = None
    warranty_terms: str | None = None
    source_url: str | None = None


class WebsiteCategoryDTO(BaseModel):
    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    source_url: str | None = None


class WebsiteFAQItemDTO(BaseModel):
    id: str
    question: str
    answer: str
    topic: str | None = None
    source_url: str | None = None


class WebsiteCompanyInfoDTO(BaseModel):
    topic: str
    title: str
    content: str
    source_url: str | None = None


class WebsiteContactInfoDTO(BaseModel):
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    working_hours: str | None = None
    source_url: str | None = None


class WebsiteSearchResponseDTO(BaseModel):
    products: list[WebsiteProductDTO] = Field(default_factory=list)
    categories: list[WebsiteCategoryDTO] = Field(default_factory=list)
    faq_items: list[WebsiteFAQItemDTO] = Field(default_factory=list)
    company_info: list[WebsiteCompanyInfoDTO] = Field(default_factory=list)
    contacts: list[WebsiteContactInfoDTO] = Field(default_factory=list)
