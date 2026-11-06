"""Public iwt.ru storefront catalog provider (no Bitrix)."""

import pytest

from app.integrations.website_store.client import WebsiteStoreClient
from app.knowledge_layer.website_provider import WebsiteKnowledgeProvider
from app.providers.website_store_provider import WebsiteStoreProvider
from app.services.composition import build_source_selector


SAMPLE_HTML = """
<div class="product-card item " id="bx_3966226736_122567_7e1b8e3524755c391129a9d7e6f2d206">
    <div class="price" id="bx_3966226736_122567_7e1b8e3524755c391129a9d7e6f2d206_price">
            7 900 руб.        </div>
<a href="/catalog/ofisnaya_tekhnika/raskhodnye_materialy/kartridzhi/kartridzh_lazernyy_xerox_108r00909_chernyy_s_chipom/" title="Картридж лазерный Xerox 108R00909 черный, с чипом" class="name font-title">Картридж лазерный Xerox 108R00909 черный, с чипом</a>
</div>
<div class="product-card item " id="bx_3966226736_119392_362ce596257894d11ab5c1d73d13c755">
    <div class="price" id="bx_3966226736_119392_362ce596257894d11ab5c1d73d13c755_price">
            5 940 руб.        </div>
<a href="/catalog/ofisnaya_tekhnika/raskhodnye_materialy/kartridzhi_i_tonery_kyocera/kartridzh_tk_8345k/" title="Картридж TK-8345K для Kyocera" class="name font-title">Картридж TK-8345K для Kyocera</a>
</div>
"""


def test_parse_catalog_html_extracts_name_price_sku_and_url() -> None:
    products = WebsiteStoreClient.parse_catalog_html(SAMPLE_HTML, base_url="https://www.iwt.ru")
    assert len(products) == 2
    first = products[0]
    assert first.sku == "122567"
    assert "Xerox" in first.name
    assert first.price == 7900.0
    assert first.url.startswith("https://www.iwt.ru/catalog/")


@pytest.mark.asyncio
async def test_website_store_provider_maps_confirmed_price() -> None:
    class StubClient:
        async def search_products(self, query: str, limit: int | None = None):
            return WebsiteStoreClient.parse_catalog_html(SAMPLE_HTML)

    provider = WebsiteStoreProvider(client=StubClient())  # type: ignore[arg-type]
    result = await provider.search("картридж")
    assert len(result.products) == 2
    product = result.products[0]
    assert product.price == 7900.0
    assert "price" in product.confirmed_fields
    assert "Цена на сайте" in (product.description or "")


@pytest.mark.asyncio
async def test_website_knowledge_provider_exposes_store_products() -> None:
    class StubClient:
        async def search_products(self, query: str, limit: int | None = None):
            return WebsiteStoreClient.parse_catalog_html(SAMPLE_HTML)

    knowledge = WebsiteKnowledgeProvider(WebsiteStoreProvider(client=StubClient()))  # type: ignore[arg-type]
    result = await knowledge.search("картридж")
    assert len(result.sources) == 2
    assert result.sources[0].source_type == "website_provider"
    assert "7900" in result.sources[0].metadata.get("price", "") or "7900" in result.sources[0].content


def test_build_source_selector_prefers_store_over_bitrix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IWT_STORE_ENABLED", "true")
    monkeypatch.delenv("WEBSITE_API_URL", raising=False)
    selector = build_source_selector()
    names = [getattr(p, "provider_name", type(p).__name__) for p in selector.providers]
    assert "knowledge_base" in names or any("Knowledge" in n for n in names)
    assert any(n == "website_provider" for n in names)