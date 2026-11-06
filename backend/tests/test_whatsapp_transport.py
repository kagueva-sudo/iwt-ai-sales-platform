import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.channel_adapters.whatsapp_adapter import WhatsAppChannelAdapter
from app.channel_adapters.whatsapp_payload import (
    extract_whatsapp_text,
    extract_whatsapp_wa_id,
    is_whatsapp_processable_update,
)
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.integrations.whatsapp.exceptions import WhatsAppUnauthorizedError
from app.integrations.whatsapp.transport import HttpWhatsAppTransport
from app.main import app


def _json_response(status_code: int, payload: dict | None = None) -> httpx.Response:
    content = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return httpx.Response(status_code=status_code, content=content, headers={"Content-Type": "application/json"})


def _wa_transport(handler) -> HttpWhatsAppTransport:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://graph.facebook.com")
    return HttpWhatsAppTransport(
        access_token="test-token",
        phone_number_id="1234567890",
        http_client=client,
        max_retries=0,
    )


def _cloud_text_payload(*, text: str = "Нужна цена насоса", wa_id: str = "79001234567") -> dict:
    from uuid import uuid4

    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "1234567890",
                            },
                            "contacts": [{"profile": {"name": "Иван"}, "wa_id": wa_id}],
                            "messages": [
                                {
                                    "from": wa_id,
                                    "id": f"wamid.{uuid4().hex}",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_whatsapp_adapter_normalizes_simplified_payload() -> None:
    adapter = WhatsAppChannelAdapter()
    message = await adapter.normalize_incoming(
        {
            "text": "Нужна цена насоса",
            "wa_id": "79001234567",
            "from": "+79001234567",
        }
    )

    assert message.channel == ChannelType.WHATSAPP
    assert message.direction == MessageDirection.INBOUND
    assert message.text == "Нужна цена насоса"
    assert message.customer_id == "79001234567"


@pytest.mark.asyncio
async def test_whatsapp_adapter_normalizes_cloud_api_payload() -> None:
    payload = _cloud_text_payload()
    assert is_whatsapp_processable_update(payload)
    assert extract_whatsapp_text(payload) == "Нужна цена насоса"
    assert extract_whatsapp_wa_id(payload) == "79001234567"

    message = await WhatsAppChannelAdapter().normalize_incoming(payload)
    assert message.text == "Нужна цена насоса"
    assert message.customer_id == "79001234567"
    assert message.customer_contact == "Иван"
    assert len(message.id) == 36


@pytest.mark.asyncio
async def test_whatsapp_adapter_rejects_status_only_payload() -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [{"id": "wamid.1", "status": "delivered"}],
                        }
                    }
                ]
            }
        ],
    }
    assert not is_whatsapp_processable_update(payload)
    with pytest.raises(ProviderError):
        await WhatsAppChannelAdapter().normalize_incoming(payload)


@pytest.mark.asyncio
async def test_whatsapp_transport_sends_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v21.0/1234567890/messages"
        assert request.headers["Authorization"] == "Bearer test-token"
        body = json.loads(request.content.decode("utf-8"))
        assert body["to"] == "79001234567"
        assert body["text"]["body"] == "Ответ"
        return _json_response(200, {"messages": [{"id": "wamid.OUT1"}]})

    transport = _wa_transport(handler)
    result = await transport.send_text("Ответ", to="79001234567")
    assert result["messages"][0]["id"] == "wamid.OUT1"
    await transport.close()


@pytest.mark.asyncio
async def test_whatsapp_adapter_send_uses_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, {"messages": [{"id": "wamid.OUT2"}]})

    adapter = WhatsAppChannelAdapter(transport=_wa_transport(handler))
    await adapter.normalize_incoming({"text": "Привет", "wa_id": "79001112233"})
    outbound = Message(
        text="Здравствуйте!",
        channel=ChannelType.WHATSAPP,
        direction=MessageDirection.OUTBOUND,
        customer_id="79001112233",
    )
    sent_id = await adapter.send_message(outbound)
    assert sent_id == "wamid.OUT2"
    assert adapter.sent == [outbound]


@pytest.mark.asyncio
async def test_whatsapp_transport_maps_401() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(401, {"error": {"message": "invalid"}})

    transport = _wa_transport(handler)
    with pytest.raises(WhatsAppUnauthorizedError):
        await transport.send_text("x", to="79001112233")
    await transport.close()


def test_whatsapp_webhook_verify_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret-verify")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/channels/whatsapp/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "secret-verify",
                    "hub.challenge": "12345",
                },
            )
        assert response.status_code == 200
        assert response.text == "12345"
    finally:
        get_settings.cache_clear()


def test_whatsapp_webhook_verify_rejects_bad_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret-verify")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/channels/whatsapp/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong",
                    "hub.challenge": "12345",
                },
            )
        assert response.status_code == 403
    finally:
        get_settings.cache_clear()


def test_whatsapp_webhook_ignores_status_callback() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/channels/whatsapp/webhook",
            json={
                "object": "whatsapp_business_account",
                "entry": [{"changes": [{"value": {"statuses": [{"status": "sent"}]}}]}],
            },
        )
    assert response.status_code == 200
    assert response.text == "EVENT_RECEIVED"


def test_whatsapp_cloud_webhook_runs_pipeline() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/channels/whatsapp/webhook",
            json=_cloud_text_payload(text="Какая мощность насоса?"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["handoff_required"] is True
