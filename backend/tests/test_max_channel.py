import pytest
from fastapi.testclient import TestClient

from app.channel_adapters.max_adapter import MaxChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.main import app
from app.services.response_sender import ChannelResponseSender, InMemoryResponseSender


@pytest.mark.asyncio
async def test_max_adapter_normalizes_payload() -> None:
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


@pytest.mark.asyncio
async def test_max_adapter_rejects_empty_payload() -> None:
    adapter = MaxChannelAdapter()

    with pytest.raises(ProviderError):
        await adapter.normalize_incoming({"user_id": "1"})


@pytest.mark.asyncio
async def test_max_adapter_stub_send() -> None:
    adapter = MaxChannelAdapter()
    outbound = Message(
        text="Ответ",
        channel=ChannelType.MAX,
        direction=MessageDirection.OUTBOUND,
    )

    delivery_id = await adapter.send_message(outbound)

    assert delivery_id == outbound.id
    assert adapter.sent == [outbound]


@pytest.mark.asyncio
async def test_channel_response_sender_uses_max_adapter() -> None:
    adapter = MaxChannelAdapter()
    sender = ChannelResponseSender(
        adapters={ChannelType.MAX: adapter},
        fallback=InMemoryResponseSender(),
    )
    outbound = Message(
        text="Ответ",
        channel=ChannelType.MAX,
        direction=MessageDirection.OUTBOUND,
    )

    await sender.send(outbound)

    assert adapter.sent == [outbound]


def test_max_webhook_creates_handoff_without_sources() -> None:
    with TestClient(app) as client:
        before = len(client.get("/manager-queue").json())
        response = client.post(
            "/channels/max/webhook",
            json={
                "text": "Сколько стоит насос?",
                "user_id": "max-42",
                "contact": "+79991112233",
            },
        )
        after = len(client.get("/manager-queue").json())

    assert response.status_code == 200
    body = response.json()
    assert body["handoff_required"] is False
    assert body["validation_status"] == "approved"
    assert after == before


def test_max_webhook_rejects_invalid_payload() -> None:
    with TestClient(app) as client:
        response = client.post("/channels/max/webhook", json={"user_id": "max-42"})

    assert response.status_code == 400


def test_gateway_still_accepts_normalized_message() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/gateway/messages",
            json={
                "channel": "website",
                "text": "Сколько стоит насос?",
                "customer_id": "customer-1",
                "customer_contact": "client@example.com",
                "external_message_id": "web-1",
                "metadata": {"form": "contact"},
            },
        )

    assert response.status_code == 200
    assert response.json()["handoff_required"] is False
    assert response.json()["validation_status"] == "approved"


def test_ai_core_unchanged_by_channel_layer() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "MaxChannelAdapter" not in source
    assert "channel_adapters" not in source
    assert "DecisionRouter" not in source
