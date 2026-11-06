from app.contracts.knowledge_provider import KnowledgeProvider
from app.contracts.website_provider import WebsiteProvider
from app.domain.products import Product
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.domain.website import CompanyInfo, ContactInfo, FAQItem


class WebsiteKnowledgeProvider(KnowledgeProvider):
    provider_name = "website_provider"

    def __init__(self, website_provider: WebsiteProvider) -> None:
        self.website_provider = website_provider

    async def search(self, query: str) -> SourceSelectionResult:
        website_result = await self.website_provider.search(query)
        return SourceSelectionResult(
            query=query,
            sources=[
                *[self._product_to_source(product) for product in website_result.products],
                *[self._faq_to_source(item) for item in website_result.faq_items],
                *[self._company_info_to_source(item) for item in website_result.company_info],
                *[self._contact_to_source(item) for item in website_result.contacts],
                *website_result.sources,
            ],
        )

    def _product_to_source(self, product: Product) -> VerifiedSource:
        metadata = {
            "sku": product.sku,
            "source": product.source,
            "confirmed_fields": ",".join(sorted(product.confirmed_fields)),
        }
        if product.price is not None:
            metadata["price"] = str(product.price)
        if product.stock_qty is not None:
            metadata["stock_qty"] = str(product.stock_qty)
        if product.delivery_terms:
            metadata["delivery_terms"] = product.delivery_terms
        if product.source_url:
            metadata["source_url"] = product.source_url

        content = product.description or product.name
        if product.source_url and product.source_url not in content:
            content = f"{content}\nСсылка: {product.source_url}"

        return VerifiedSource(
            source_id=product.sku,
            source_type=self.provider_name,
            title=product.name,
            content=content,
            metadata=metadata,
        )

    def _faq_to_source(self, item: FAQItem) -> VerifiedSource:
        return VerifiedSource(
            source_id=item.id,
            source_type=self.provider_name,
            title=item.question,
            content=item.answer,
            metadata={"topic": item.topic or "", "confirmed_fields": ",".join(sorted(item.confirmed_fields))},
        )

    def _company_info_to_source(self, item: CompanyInfo) -> VerifiedSource:
        return VerifiedSource(
            source_id=item.topic,
            source_type=self.provider_name,
            title=item.title,
            content=item.content,
            metadata={"confirmed_fields": ",".join(sorted(item.confirmed_fields))},
        )

    def _contact_to_source(self, item: ContactInfo) -> VerifiedSource:
        content = "\n".join(
            value
            for value in [item.phone, item.email, item.address, item.working_hours]
            if value
        )
        return VerifiedSource(
            source_id="contacts",
            source_type=self.provider_name,
            title="Контакты",
            content=content,
            metadata={"confirmed_fields": ",".join(sorted(item.confirmed_fields))},
        )
