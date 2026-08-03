from dataclasses import dataclass, field
from datetime import datetime

from app.domain.products import Product
from app.domain.sources import VerifiedSource


@dataclass(slots=True)
class Category:
    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    source: str = "website"
    source_url: str | None = None
    confirmed_fields: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class FAQItem:
    id: str
    question: str
    answer: str
    topic: str | None = None
    source: str = "website"
    source_url: str | None = None
    updated_at: datetime | None = None
    confirmed_fields: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class CompanyInfo:
    topic: str
    title: str
    content: str
    source: str = "website"
    source_url: str | None = None
    updated_at: datetime | None = None
    confirmed_fields: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ContactInfo:
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    working_hours: str | None = None
    source: str = "website"
    source_url: str | None = None
    confirmed_fields: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WebsiteSourceError:
    code: str
    message: str
    retryable: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WebsiteSearchResult:
    query: str
    products: list[Product] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    faq_items: list[FAQItem] = field(default_factory=list)
    company_info: list[CompanyInfo] = field(default_factory=list)
    contacts: list[ContactInfo] = field(default_factory=list)
    sources: list[VerifiedSource] = field(default_factory=list)
    errors: list[WebsiteSourceError] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def confirmed(self) -> bool:
        return bool(self.sources) or any(
            item.confirmed_fields
            for collection in [
                self.products,
                self.categories,
                self.faq_items,
                self.company_info,
                self.contacts,
            ]
            for item in collection
        )
