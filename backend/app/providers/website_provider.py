from app.contracts.website_provider import WebsiteProvider
from app.domain.products import Product
from app.domain.website import (
    Category,
    CompanyInfo,
    ContactInfo,
    FAQItem,
    WebsiteSearchResult,
    WebsiteSourceError,
)
from app.integrations.website.client import WebsiteApiClient
from app.integrations.website.config import build_website_api_client
from app.integrations.website.exceptions import (
    WebsiteError,
    WebsiteForbiddenError,
    WebsiteNotConfiguredError,
    WebsiteNotFoundError,
    WebsiteRateLimitError,
    WebsiteServerError,
    WebsiteTimeoutError,
    WebsiteUnauthorizedError,
)
from app.integrations.website.schemas import (
    WebsiteCategoryDTO,
    WebsiteCompanyInfoDTO,
    WebsiteContactInfoDTO,
    WebsiteFAQItemDTO,
    WebsiteProductDTO,
)


class WebsiteApiProvider(WebsiteProvider):
    """Concrete WebsiteProvider backed by Website API (live HttpWebsiteTransport when configured)."""

    provider_name = "website"

    def __init__(self, client: WebsiteApiClient | None = None) -> None:
        self.client = client or self._build_client()

    async def search(self, query: str) -> WebsiteSearchResult:
        try:
            payload = await self.client.search(query)
        except WebsiteNotFoundError:
            return WebsiteSearchResult(query=query)
        except WebsiteError as exc:
            return WebsiteSearchResult(
                query=query,
                errors=[self._to_source_error(exc)],
            )

        return WebsiteSearchResult(
            query=query,
            products=[self._to_product(item) for item in payload.products],
            categories=[self._to_category(item) for item in payload.categories],
            faq_items=[self._to_faq(item) for item in payload.faq_items],
            company_info=[self._to_company_info(item) for item in payload.company_info],
            contacts=[self._to_contacts(item) for item in payload.contacts],
        )

    async def get_product_by_sku(self, sku: str) -> Product | None:
        try:
            payload = await self.client.get_product_by_sku(sku)
        except WebsiteNotFoundError:
            return None
        except WebsiteError:
            return None
        return self._to_product(payload)

    async def get_delivery_info(self) -> CompanyInfo | None:
        return await self._get_company_info(self.client.get_delivery_info)

    async def get_payment_info(self) -> CompanyInfo | None:
        return await self._get_company_info(self.client.get_payment_info)

    async def get_warranty_info(self) -> CompanyInfo | None:
        return await self._get_company_info(self.client.get_warranty_info)

    async def get_contacts(self) -> ContactInfo | None:
        try:
            payload = await self.client.get_contacts()
        except WebsiteNotFoundError:
            return None
        except WebsiteError:
            return None
        return self._to_contacts(payload)

    async def _get_company_info(self, loader) -> CompanyInfo | None:
        try:
            payload = await loader()
        except WebsiteNotFoundError:
            return None
        except WebsiteError:
            return None
        return self._to_company_info(payload)

    def _build_client(self) -> WebsiteApiClient:
        return build_website_api_client()

    def _to_product(self, item: WebsiteProductDTO) -> Product:
        fields_set = item.model_fields_set
        confirmed_fields: set[str] = {"sku", "name"}

        if "id" in fields_set and item.id:
            confirmed_fields.add("id")
        if "description" in fields_set and item.description:
            confirmed_fields.add("description")
        if "category_id" in fields_set and item.category_id:
            confirmed_fields.add("category_id")
        if "category_name" in fields_set and item.category_name:
            confirmed_fields.add("category_name")
        if "price" in fields_set and item.price is not None:
            confirmed_fields.add("price")
        if "currency" in fields_set and item.currency:
            confirmed_fields.add("currency")
        if "availability_status" in fields_set and item.availability_status:
            confirmed_fields.add("availability_status")
        if "stock_qty" in fields_set and item.stock_qty is not None:
            confirmed_fields.add("stock_qty")
        if "characteristics" in fields_set and item.characteristics:
            confirmed_fields.add("characteristics")
        if "delivery_terms" in fields_set and item.delivery_terms:
            confirmed_fields.add("delivery_terms")
        if "payment_terms" in fields_set and item.payment_terms:
            confirmed_fields.add("payment_terms")
        if "warranty_terms" in fields_set and item.warranty_terms:
            confirmed_fields.add("warranty_terms")

        return Product(
            sku=item.sku,
            name=item.name,
            id=item.id,
            description=item.description,
            category_id=item.category_id,
            category_name=item.category_name,
            price=item.price,
            currency=item.currency,
            availability_status=item.availability_status,
            stock_qty=item.stock_qty,
            characteristics=item.characteristics or None,
            delivery_terms=item.delivery_terms,
            payment_terms=item.payment_terms,
            warranty_terms=item.warranty_terms,
            source=self.provider_name,
            source_url=item.source_url,
            confirmed_fields=confirmed_fields,
        )

    def _to_category(self, item: WebsiteCategoryDTO) -> Category:
        fields_set = item.model_fields_set
        confirmed_fields = {"id", "name"}
        if "description" in fields_set and item.description:
            confirmed_fields.add("description")
        if "parent_id" in fields_set and item.parent_id:
            confirmed_fields.add("parent_id")
        return Category(
            id=item.id,
            name=item.name,
            description=item.description,
            parent_id=item.parent_id,
            source=self.provider_name,
            source_url=item.source_url,
            confirmed_fields=confirmed_fields,
        )

    def _to_faq(self, item: WebsiteFAQItemDTO) -> FAQItem:
        fields_set = item.model_fields_set
        confirmed_fields = {"id", "question", "answer"}
        if "topic" in fields_set and item.topic:
            confirmed_fields.add("topic")
        return FAQItem(
            id=item.id,
            question=item.question,
            answer=item.answer,
            topic=item.topic,
            source=self.provider_name,
            source_url=item.source_url,
            confirmed_fields=confirmed_fields,
        )

    def _to_company_info(self, item: WebsiteCompanyInfoDTO) -> CompanyInfo:
        return CompanyInfo(
            topic=item.topic,
            title=item.title,
            content=item.content,
            source=self.provider_name,
            source_url=item.source_url,
            confirmed_fields={"topic", "title", "content"},
        )

    def _to_contacts(self, item: WebsiteContactInfoDTO) -> ContactInfo:
        fields_set = item.model_fields_set
        confirmed_fields: set[str] = set()
        if "phone" in fields_set and item.phone:
            confirmed_fields.add("phone")
        if "email" in fields_set and item.email:
            confirmed_fields.add("email")
        if "address" in fields_set and item.address:
            confirmed_fields.add("address")
        if "working_hours" in fields_set and item.working_hours:
            confirmed_fields.add("working_hours")
        return ContactInfo(
            phone=item.phone,
            email=item.email,
            address=item.address,
            working_hours=item.working_hours,
            source=self.provider_name,
            source_url=item.source_url,
            confirmed_fields=confirmed_fields,
        )

    def _to_source_error(self, exc: WebsiteError) -> WebsiteSourceError:
        code = "WEBSITE_API_UNAVAILABLE"
        retryable = False
        if isinstance(exc, WebsiteNotConfiguredError):
            code = "WEBSITE_API_NOT_CONFIGURED"
        elif isinstance(exc, WebsiteTimeoutError):
            code = "TIMEOUT"
            retryable = True
        elif isinstance(exc, WebsiteUnauthorizedError):
            code = "WEBSITE_API_UNAUTHORIZED"
        elif isinstance(exc, WebsiteForbiddenError):
            code = "WEBSITE_API_FORBIDDEN"
        elif isinstance(exc, WebsiteRateLimitError):
            code = "WEBSITE_API_RATE_LIMIT"
            retryable = True
        elif isinstance(exc, WebsiteServerError):
            code = "WEBSITE_API_ERROR"
            retryable = True
        return WebsiteSourceError(code=code, message=str(exc), retryable=retryable)
