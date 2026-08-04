import json
import os

import httpx
import pytest

from app.core.config import get_settings
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


def _json_response(status_code: int, payload: dict | list | None = None) -> httpx.Response:
    content = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "application/json"},
    )


def _transport_with_handler(
    handler,
    *,
    api_key: str = "test-key",
    auth_mode: str = "bearer",
) -> HttpWebsiteTransport:
    mock = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=mock, base_url="https://website.test")
    return HttpWebsiteTransport(
        base_url="https://website.test",
        api_key=api_key,
        timeout=1.0,
        max_retries=2,
        retry_backoff_seconds=0.0,
        auth_mode=auth_mode,  # type: ignore[arg-type]
        http_client=client,
    )


async def test_http_transport_returns_json_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert request.headers["Authorization"] == "Bearer test-key"
        return _json_response(200, {"products": [{"sku": "P-1", "name": "Насос"}]})

    transport = _transport_with_handler(handler)
    try:
        payload = await transport.request("GET", "/search", params={"q": "насос"})
    finally:
        await transport.close()

    assert payload["products"][0]["sku"] == "P-1"


async def test_http_transport_sends_x_api_key_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "secret-key"
        assert "Authorization" not in request.headers
        return _json_response(200, {"products": []})

    transport = _transport_with_handler(handler, api_key="secret-key", auth_mode="api_key")
    try:
        payload = await transport.request("GET", "/search")
    finally:
        await transport.close()

    assert payload == {"products": []}


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, WebsiteUnauthorizedError),
        (403, WebsiteForbiddenError),
        (404, WebsiteNotFoundError),
        (429, WebsiteRateLimitError),
        (500, WebsiteServerError),
        (502, WebsiteServerError),
        (400, WebsiteUnavailableError),
    ],
)
async def test_http_transport_maps_status_codes(status_code: int, error_type: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(status_code, {"error": "failed"})

    transport = _transport_with_handler(handler)
    try:
        with pytest.raises(error_type):
            await transport.request("GET", "/search")
    finally:
        await transport.close()


async def test_http_transport_retries_on_server_error_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return _json_response(503, {"error": "busy"})
        return _json_response(200, {"products": []})

    transport = _transport_with_handler(handler)
    try:
        payload = await transport.request("GET", "/search")
    finally:
        await transport.close()

    assert payload == {"products": []}
    assert calls["count"] == 3


async def test_http_transport_retries_exhausted_on_rate_limit() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return _json_response(429, {"error": "rate limit"})

    transport = _transport_with_handler(handler)
    try:
        with pytest.raises(WebsiteRateLimitError):
            await transport.request("GET", "/search")
    finally:
        await transport.close()

    assert calls["count"] == 3  # initial + 2 retries


async def test_http_transport_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    transport = _transport_with_handler(handler)
    try:
        with pytest.raises(WebsiteTimeoutError):
            await transport.request("GET", "/search")
    finally:
        await transport.close()


async def test_http_transport_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        HttpWebsiteTransport(base_url="")


async def test_client_uses_http_transport_when_base_url_configured() -> None:
    client = WebsiteApiClient(base_url="https://website.test", api_key="k", auth_mode="bearer")
    assert isinstance(client.transport, HttpWebsiteTransport)
    await client.close()


async def test_client_stays_not_configured_without_base_url() -> None:
    client = WebsiteApiClient()
    assert isinstance(client.transport, NotConfiguredWebsiteTransport)


async def test_client_with_http_transport_search_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert request.url.params["q"] == "насос"
        return _json_response(
            200,
            {
                "products": [
                    {
                        "sku": "P-1",
                        "name": "Насос",
                        "price": 1000,
                        "currency": "RUB",
                        "stock_qty": 3,
                    }
                ]
            },
        )

    transport = _transport_with_handler(handler)
    client = WebsiteApiClient(transport=transport)
    provider = WebsiteApiProvider(client=client)

    try:
        result = await provider.search("насос")
    finally:
        await transport.close()

    assert result.confirmed is True
    product = result.products[0]
    assert product.sku == "P-1"
    assert "price" in product.confirmed_fields
    assert "currency" in product.confirmed_fields
    assert "stock_qty" in product.confirmed_fields


async def test_client_with_http_transport_get_product_by_sku() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/products/by-sku/P-42"
        assert request.headers["Authorization"] == "Bearer test-key"
        return _json_response(
            200,
            {
                "sku": "P-42",
                "name": "Насос промышленный",
                "price": 2500,
                "availability_status": "in_stock",
                "characteristics": {"power": "2 kW"},
            },
        )

    transport = _transport_with_handler(handler)
    provider = WebsiteApiProvider(client=WebsiteApiClient(transport=transport))

    try:
        product = await provider.get_product_by_sku("P-42")
    finally:
        await transport.close()

    assert product is not None
    assert product.sku == "P-42"
    assert "price" in product.confirmed_fields
    assert "availability_status" in product.confirmed_fields
    assert "characteristics" in product.confirmed_fields
    assert "currency" not in product.confirmed_fields  # default only, not in API payload


async def test_confirmed_fields_do_not_include_absent_price() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, {"products": [{"sku": "P-1", "name": "Насос", "description": "Описание"}]})

    transport = _transport_with_handler(handler)
    provider = WebsiteApiProvider(client=WebsiteApiClient(transport=transport))

    try:
        result = await provider.search("насос")
    finally:
        await transport.close()

    product = result.products[0]
    assert product.confirmed_fields == {"sku", "name", "description"}
    assert "price" not in product.confirmed_fields


async def test_provider_maps_forbidden_and_rate_limit_errors() -> None:
    forbidden_transport = _transport_with_handler(lambda request: _json_response(403, {}))
    rate_limit_transport = _transport_with_handler(lambda request: _json_response(429, {}))

    try:
        forbidden = await WebsiteApiProvider(
            client=WebsiteApiClient(transport=forbidden_transport)
        ).search("насос")
        rate_limited = await WebsiteApiProvider(
            client=WebsiteApiClient(transport=rate_limit_transport)
        ).search("насос")
    finally:
        await forbidden_transport.close()
        await rate_limit_transport.close()

    assert forbidden.errors[0].code == "WEBSITE_API_FORBIDDEN"
    assert forbidden.errors[0].retryable is False
    assert rate_limited.errors[0].code == "WEBSITE_API_RATE_LIMIT"
    assert rate_limited.errors[0].retryable is True


async def test_provider_maps_unauthorized_error() -> None:
    transport = _transport_with_handler(lambda request: _json_response(401, {}))
    try:
        result = await WebsiteApiProvider(client=WebsiteApiClient(transport=transport)).search("насос")
    finally:
        await transport.close()

    assert result.errors[0].code == "WEBSITE_API_UNAUTHORIZED"


async def test_knowledge_provider_preserves_confirmed_fields_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            200,
            {"products": [{"sku": "P-1", "name": "Насос", "price": 1000, "stock_qty": 2}]},
        )

    transport = _transport_with_handler(handler)
    knowledge = WebsiteKnowledgeProvider(WebsiteApiProvider(client=WebsiteApiClient(transport=transport)))

    try:
        result = await knowledge.search("насос")
    finally:
        await transport.close()

    assert result.has_sources
    confirmed = set(result.sources[0].metadata["confirmed_fields"].split(","))
    assert {"sku", "name", "price", "stock_qty"} <= confirmed


async def test_composition_includes_website_provider_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBSITE_API_URL", "https://website.test")
    monkeypatch.setenv("WEBSITE_API_KEY", "test-key")
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
    monkeypatch.delenv("WEBSITE_API_URL", raising=False)
    monkeypatch.setenv("WEBSITE_API_URL", "")
    get_settings.cache_clear()

    from app.services.composition import build_source_selector

    try:
        selector = build_source_selector()
        names = [provider.provider_name for provider in selector.providers]
        assert names == ["knowledge_base"]
    finally:
        get_settings.cache_clear()


@pytest.mark.skipif(
    not os.getenv("WEBSITE_API_LIVE_SMOKE"),
    reason="Set WEBSITE_API_LIVE_SMOKE=1 and real WEBSITE_API_* env to run live smoke.",
)
async def test_live_website_api_smoke_search_and_product() -> None:
    get_settings.cache_clear()
    client = build_website_api_client()
    provider = WebsiteApiProvider(client=client)
    try:
        search = await provider.search("насос")
        assert search.errors == [] or search.products or search.faq_items
        if search.products:
            product = search.products[0]
            assert product.sku
            assert "sku" in product.confirmed_fields
            assert "name" in product.confirmed_fields
            fetched = await provider.get_product_by_sku(product.sku)
            assert fetched is not None
            assert fetched.sku == product.sku
    finally:
        await client.close()
        get_settings.cache_clear()
