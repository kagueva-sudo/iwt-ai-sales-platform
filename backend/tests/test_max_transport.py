import json

import httpx
import pytest

from app.channel_adapters.max_adapter import MaxChannelAdapter
from app.channel_adapters.max_payload import (
    extract_max_chat_id,
    extract_max_text,
    extract_max_user_id,
    is_max_processable_update,
)
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.integrations.max.exceptions import MaxUnauthorizedError
from app.integrations.max.transport import HttpMaxTransport


pytestmark = pytest.mark.asyncio


def _json_response(status_code: int, payload: dict | None = None) -> httpx.Response:
    content = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return httpx.Response(status_code=status_code, content=content, headers={"Content-Type": "application/json"})


def _max_transport(handler) -> HttpMaxTransport:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://platform-api2.max.ru")
    return HttpMaxTransport(bot_token="test-token", http_client=client, max_retries=0)


async def test_max_adapter_normalizes_simplified_payload() -> None:
    adapter = MaxChannelAdapter()

    message = await adapter.normalize_incoming(
        {
            "text": "Нужна цена насоса",
            "user_id": "max-user-1",
            "username": "@client",
        }
    )

    assert message.channel == ChannelType.MAX
    assert message.direction == MessageDirection.INBOUND
    assert message.text == "Нужна цена насоса"
    assert message.customer_id == "max-user-1"
    assert message.customer_contact == "@client"


async def test_max_adapter_normalizes_native_max_payload() -> None:
    payload = {
        "update_type": "message_created",
        "user_id": 4242,
        "chat_id": 9001,
        "message": {
            "body": {"text": "Сколько стоит насос?", "mid": "mid-42"},
            "recipient": {"chat_id": 9001},
        },
        "sender": {"user_id": 4242, "username": "ivan"},
    }
    assert is_max_processable_update(payload)
    assert extract_max_text(payload) == "Сколько стоит насос?"
    assert extract_max_user_id(payload) == "4242"
    assert extract_max_chat_id(payload) == "9001"

    message = await MaxChannelAdapter().normalize_incoming(payload)
    assert message.text == "Сколько стоит насос?"
    assert message.customer_id == "4242"
    assert message.id == "mid-42"


async def test_max_adapter_skips_callback_updates() -> None:
    with pytest.raises(ProviderError):
        await MaxChannelAdapter().normalize_incoming(
            {"update_type": "message_callback", "callback": {"payload": "m:main"}}
        )


async def test_max_adapter_rejects_empty_payload() -> None:
    adapter = MaxChannelAdapter()

    with pytest.raises(ProviderError):
        await adapter.normalize_incoming({"user_id": "1"})


async def test_max_adapter_stub_send_without_token() -> None:
    adapter = MaxChannelAdapter()
    outbound = Message(
        text="Ответ",
        channel=ChannelType.MAX,
        direction=MessageDirection.OUTBOUND,
        customer_id="max-user-1",
    )
    await adapter.normalize_incoming({"text": "hi", "user_id": "max-user-1"})

    delivery_id = await adapter.send_message(outbound)

    assert delivery_id == outbound.id
    assert adapter.sent == [outbound]


async def test_max_adapter_live_send_uses_user_id() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["Authorization"] == "test-token"
        assert request.url.params.get("user_id") == "max-user-1"
        return _json_response(200, {"message": {"body": {"mid": "out-1"}}})

    transport = _max_transport(handler)
    adapter = MaxChannelAdapter(transport=transport)
    await adapter.normalize_incoming({"text": "вопрос", "user_id": "max-user-1"})

    delivery_id = await adapter.send_message(
        Message(
            text="Ответ AI",
            channel=ChannelType.MAX,
            direction=MessageDirection.OUTBOUND,
            customer_id="max-user-1",
        )
    )

    assert delivery_id == "out-1"
    assert len(calls) == 1
    await transport.close()


async def test_max_transport_maps_unauthorized() -> None:
    transport = _max_transport(lambda request: _json_response(401, {}))
    try:
        with pytest.raises(MaxUnauthorizedError):
            await transport.send_text("hi", user_id="1")
    finally:
        await transport.close()
