import json
import os
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

from app.core.config import get_settings
from app.integrations.website.bitrix_mapper import map_bitrix_product_to_dto
from app.integrations.website.client import NotConfiguredWebsiteTransport, WebsiteApiClient
from app.integrations.website.config import build_website_api_client, is_website_api_configured
from app.integrations.website.exceptions import (
    WebsiteForbiddenError,
    WebsiteNotFoundError,
    WebsiteRateLimitError,
    WebsiteServerError,
    WebsiteTimeoutError,
    WebsiteUnauthorizedError,
    WebsiteUnavailableError,
)
from app.integrations.website.transport import HttpWebsiteTransport
from app.knowledge_layer.website_provider import WebsiteKnowledgeProvider
from app.providers.website_provider import WebsiteApiProvider


pytestmark = pytest.mark.asyncio

SAMPLE_PRODUCT = {
    "id": 112415,
    "iblockId": 86,
    "name": "Жесткий диск HPE 600GB SAS 15K SFF SC DS HDD 870757-B21",
    "code": "zhestkiy_disk_hpe_600gb_sas_15k_sff_sc_ds_hdd_870757_b21",
    "xmlId": "f344956e-272d-11e9-8133-002564fd2133",
    "quantity": 1,
    "available": "Y",
    "previewText": "Жесткий диск HPE 600GB",
    "iblockSectionId": 1255,
    "property11836": {"value": "225609", "valueEnum": "SAS", "valueId": "1"},
}

SAMPLE_PRICE = {
    "prices": [
        {
            "id": 59790,
            "productId": 112415,
            "price": 52100,
            "currency": "RUB",
            "catalogGroupId": 1,
        }
    ]
}


def _json_response(status_code: int, payload: dict | list | None = None) -> httpx.Response:
    content = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "application/json"},
    )


def _params(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.url.query.decode() if isinstance(request.url.query, bytes) else str(request.url.query))


def _bitrix_transport(handler) -> HttpWebsiteTransport:
    mock = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=mock, base_url="https://iwt.ru/rest/1/webhook")
    return HttpWebsiteTransport(
        base_url="https://iwt.ru/rest/1/webhook",
        api_key="",
        timeout=1.0,
        max_retries=1,
        retry_backoff_seconds=0.0,
        auth_mode="none",
        http_client=client,
    )


async def test_http_transport_none_auth_skips_authorization_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        assert "X-API-Key" not in request.headers
        return _json_response(200, {"result": {}})

    transport = _bitrix_transport(handler)
    try:
        await transport.request("GET", "/catalog.product.get.json", params={"id": 1})
    finally:
        await transport.close()


async def test_http_transport_sends_bearer_when_configured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return _json_response(200, {"ok": True})

    mock = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=mock, base_url="https://website.test")
    transport = HttpWebsiteTransport(
        base_url="https://website.test",
        api_key="test-key",
        auth_mode="bearer",
        http_client=client,
        max_retries=0,
    )
    try:
        await transport.request("GET", "/ping")
    finally:
        await transport.close()


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, WebsiteUnauthorizedError),
        (403, WebsiteForbiddenError),
        (404, WebsiteNotFoundError),
        (429, WebsiteRateLimitError),
        (500, WebsiteServerError),
        (400, WebsiteUnavailableError),
    ],
)
async def test_http_transport_maps_status_codes(status_code: int, error_type: type[Exception]) -> None:
    transport = _bitrix_transport(lambda request: _json_response(status_code, {"error": "failed"}))
    try:
        with pytest.raises(error_type):
            await transport.request("GET", "/catalog.product.list.json")
    finally:
        await transport.close()


async def test_http_transport_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    transport = _bitrix_transport(handler)
    try:
        with pytest.raises(WebsiteTimeoutError):
            await transport.request("GET", "/catalog.product.list.json")
    finally:
        await transport.close()


async def test_http_transport_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        HttpWebsiteTransport(base_url="")


async def test_client_uses_http_transport_when_base_url_configured() -> None:
    client = WebsiteApiClient(base_url="https://iwt.ru/rest/1/webhook", auth_mode="none")
    assert isinstance(client.transport, HttpWebsiteTransport)
    await client.close()


async def test_client_stays_not_configured_without_base_url() -> None:
    client = WebsiteApiClient()
    assert isinstance(client.transport, NotConfiguredWebsiteTransport)


def _bitrix_router(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = _params(request)

    if path.endswith("/catalog.product.get.json"):
        product_id = params.get("id", [""])[0]
        if product_id != "112415":
            return _json_response(200, {"error": "PRODUCT_NOT_FOUND", "error_description": "not found"})
        return _json_response(200, {"result": {"product": SAMPLE_PRODUCT}})

    if path.endswith("/catalog.product.list.json"):
        products: list[dict[str, Any]] = []
        if params.get("filter[code]", [None])[0] == SAMPLE_PRODUCT["code"]:
            products = [SAMPLE_PRODUCT]
        elif params.get("filter[xmlId]", [None])[0] == SAMPLE_PRODUCT["xmlId"]:
            products = [SAMPLE_PRODUCT]
        elif params.get("filter[%name]", [None])[0] and "HPE" in params["filter[%name]"][0]:
            products = [SAMPLE_PRODUCT]
        elif params.get("filter[id]", [None])[0] == "112415":
            products = [SAMPLE_PRODUCT]
        return _json_response(200, {"result": {"products": products}, "total": len(products)})

    if path.endswith("/catalog.price.list.json"):
        product_id = params.get("filter[productId]", [""])[0]
        if product_id == "112415":
            return _json_response(200, {"result": SAMPLE_PRICE})
        return _json_response(200, {"result": {"prices": []}, "total": 0})

    return _json_response(404, {"error": "unknown"})


async def test_bitrix_search_by_name_returns_product_with_confirmed_price() -> None:
    transport = _bitrix_transport(_bitrix_router)
    client = WebsiteApiClient(transport=transport, iblock_id=86)
    provider = WebsiteApiProvider(client=client)

    try:
        result = await provider.search("HPE 600GB")
    finally:
        await transport.close()

    assert len(result.products) == 1
    product = result.products[0]
    assert product.sku == SAMPLE_PRODUCT["code"]
    assert product.id == "112415"
    assert product.price == 52100
    assert "price" in product.confirmed_fields
    assert "currency" in product.confirmed_fields
    assert "sku" in product.confirmed_fields
    assert product.characteristics is not None
    assert product.characteristics["xmlId"] == SAMPLE_PRODUCT["xmlId"]


async def test_bitrix_search_by_code_xml_id_and_bitrix_id() -> None:
    transport = _bitrix_transport(_bitrix_router)
    client = WebsiteApiClient(transport=transport, iblock_id=86)

    try:
        by_code = await client.search(SAMPLE_PRODUCT["code"])
        by_xml = await client.search(SAMPLE_PRODUCT["xmlId"])
        by_id = await client.search("112415")
    finally:
        await transport.close()

    assert by_code.products[0].sku == SAMPLE_PRODUCT["code"]
    assert by_xml.products[0].sku == SAMPLE_PRODUCT["code"]
    assert by_id.products[0].id == "112415"


async def test_bitrix_get_product_by_sku_uses_code_and_loads_price() -> None:
    transport = _bitrix_transport(_bitrix_router)
    provider = WebsiteApiProvider(client=WebsiteApiClient(transport=transport, iblock_id=86))

    try:
        product = await provider.get_product_by_sku(SAMPLE_PRODUCT["code"])
    finally:
        await transport.close()

    assert product is not None
    assert product.sku == SAMPLE_PRODUCT["code"]
    assert product.price == 52100
    assert "price" in product.confirmed_fields
    assert "availability_status" in product.confirmed_fields


async def test_bitrix_get_product_by_xml_id_and_bitrix_id() -> None:
    transport = _bitrix_transport(_bitrix_router)
    client = WebsiteApiClient(transport=transport, iblock_id=86)

    try:
        by_xml = await client.get_product_by_sku(SAMPLE_PRODUCT["xmlId"])
        by_id = await client.get_product_by_sku("112415")
    finally:
        await transport.close()

    assert by_xml.sku == SAMPLE_PRODUCT["code"]
    assert by_id.id == "112415"


async def test_bitrix_price_list_allows_validator_to_approve_price() -> None:
    transport = _bitrix_transport(_bitrix_router)
    knowledge = WebsiteKnowledgeProvider(
        WebsiteApiProvider(client=WebsiteApiClient(transport=transport, iblock_id=86))
    )
    try:
        sources = await knowledge.search("HPE")
    finally:
        await transport.close()

    from app.ai_core.validator import AIValidator
    from app.core.constants import AIValidationStatus
    from app.domain.ai import AIResponse

    result = AIValidator().validate(
        AIResponse(text="Цена 52100 руб.", sources=[sources.sources[0].source_id]),
        sources.sources,
    )
    assert "price" in sources.sources[0].metadata["confirmed_fields"]
    assert result.status == AIValidationStatus.APPROVED


async def test_bitrix_without_price_forces_needs_data_and_manager_handoff() -> None:
    def router_without_price(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/catalog.price.list.json"):
            return _json_response(200, {"result": {"prices": []}, "total": 0})
        return _bitrix_router(request)

    transport = _bitrix_transport(router_without_price)
    knowledge = WebsiteKnowledgeProvider(
        WebsiteApiProvider(client=WebsiteApiClient(transport=transport, iblock_id=86))
    )
    try:
        sources = await knowledge.search("HPE")
    finally:
        await transport.close()

    from app.ai_core.validator import AIValidator
    from app.core.constants import AIValidationStatus, HandoffReason
    from app.domain.ai import AIResponse
    from app.domain.processing import ProcessingDecision, ProcessingResult
    from app.repositories.manager_queue import InMemoryManagerQueueRepository
    from app.services.decision_router import DefaultDecisionRouter
    from app.services.handoff_manager import DefaultHandoffManager
    from app.services.logging_service import InMemoryLoggingService
    from app.services.response_sender import InMemoryResponseSender

    assert "price" not in sources.sources[0].metadata.get("confirmed_fields", "")

    validation = AIValidator().validate(
        AIResponse(text="Цена 52100 руб.", sources=[sources.sources[0].source_id]),
        sources.sources,
    )
    assert validation.status == AIValidationStatus.NEEDS_DATA
    assert "price" in (validation.reason or "")

    queue = InMemoryManagerQueueRepository()
    router = DefaultDecisionRouter(
        response_sender=InMemoryResponseSender(),
        handoff_manager=DefaultHandoffManager(queue),
        logging_service=InMemoryLoggingService(),
    )
    await router.route(
        ProcessingResult(
            decision=ProcessingDecision.NEEDS_MORE_DATA,
            response_text=validation.approved_text or "",
            handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
            sources=[sources.sources[0].source_id],
            metadata={"reason": validation.reason or ""},
            request_id="req-price-missing",
        )
    )
    items = await queue.list_all()
    assert len(items) == 1


async def test_knowledge_provider_preserves_confirmed_fields_metadata() -> None:
    transport = _bitrix_transport(_bitrix_router)
    knowledge = WebsiteKnowledgeProvider(
        WebsiteApiProvider(client=WebsiteApiClient(transport=transport, iblock_id=86))
    )

    try:
        result = await knowledge.search("HPE")
    finally:
        await transport.close()

    confirmed = set(result.sources[0].metadata["confirmed_fields"].split(","))
    assert {"sku", "name", "price", "currency"} <= confirmed


async def test_composition_includes_website_provider_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBSITE_API_URL", "https://iwt.ru/rest/1/webhook")
    monkeypatch.setenv("WEBSITE_API_AUTH_MODE", "none")
    get_settings.cache_clear()

    from app.services.composition import build_source_selector

    try:
        selector = build_source_selector()
        names = [provider.provider_name for provider in selector.providers]
        assert "knowledge_base" in names
        assert "website_provider" in names
        assert is_website_api_configured() is True
    finally:
        get_settings.cache_clear()


async def test_composition_skips_website_provider_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBSITE_API_URL", "")
    monkeypatch.setenv("IWT_STORE_ENABLED", "false")
    get_settings.cache_clear()

    from app.services.composition import build_source_selector

    try:
        selector = build_source_selector()
        names = [provider.provider_name for provider in selector.providers]
        assert names == ["knowledge_base"]
    finally:
        get_settings.cache_clear()


async def test_composition_uses_public_store_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBSITE_API_URL", "")
    monkeypatch.setenv("IWT_STORE_ENABLED", "true")
    get_settings.cache_clear()

    from app.services.composition import build_source_selector

    try:
        selector = build_source_selector()
        names = [provider.provider_name for provider in selector.providers]
        assert names == ["knowledge_base", "website_provider"]
    finally:
        get_settings.cache_clear()


@pytest.mark.skipif(
    not os.getenv("WEBSITE_API_LIVE_SMOKE"),
    reason="Set WEBSITE_API_LIVE_SMOKE=1 and WEBSITE_API_URL to Bitrix webhook base.",
)
async def test_live_bitrix_smoke_search_and_product() -> None:
    get_settings.cache_clear()
    client = build_website_api_client()
    provider = WebsiteApiProvider(client=client)
    try:
        search = await provider.search("HPE 600GB")
        assert search.errors == []
        assert search.products
        product = search.products[0]
        assert product.sku
        assert "sku" in product.confirmed_fields
        fetched = await provider.get_product_by_sku(product.sku)
        assert fetched is not None
        assert fetched.sku == product.sku
        if fetched.price is not None:
            assert "price" in fetched.confirmed_fields
    finally:
        await client.close()
        get_settings.cache_clear()
