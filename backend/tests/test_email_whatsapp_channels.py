import pytest
from fastapi.testclient import TestClient

from app.channel_adapters.email_adapter import EmailChannelAdapter
from app.channel_adapters.whatsapp_adapter import WhatsAppChannelAdapter
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.main import app
from app.services.response_sender import ChannelResponseSender, InMemoryResponseSender


@pytest.mark.asyncio
async def test_email_adapter_normalizes_subject_and_body() -> None:
    adapter = EmailChannelAdapter()

    message = await adapter.normalize_incoming(
        {
            "subject": "Запрос цены",
            "body": "Сколько стоит насос?",
            "from": "client@example.com",
            "message_id": "email-1",
        }
    )

    assert message.channel == ChannelType.EMAIL
    assert message.direction == MessageDirection.INBOUND
    assert "Subject: Запрос цены" in message.text
    assert "Сколько стоит насос?" in message.text
    assert message.customer_id == "email-1"
    assert message.customer_contact == "client@example.com"


@pytest.mark.asyncio
async def test_email_adapter_rejects_empty_payload() -> None:
    adapter = EmailChannelAdapter()

    with pytest.raises(ProviderError):
        await adapter.normalize_incoming({"from": "client@example.com"})


@pytest.mark.asyncio
async def test_whatsapp_adapter_normalizes_payload() -> None:
    adapter = WhatsAppChannelAdapter()

    message = await adapter.normalize_incoming(
        {
            "text": "Нужна цена насоса",
            "wa_id": "79001234567",
            "from": "+79001234567",
        }
    )

    assert message.channel == ChannelType.WHATSAPP
    assert message.customer_id == "79001234567"
    assert message.customer_contact == "+79001234567"


@pytest.mark.asyncio
async def test_whatsapp_adapter_rejects_empty_payload() -> None:
    adapter = WhatsAppChannelAdapter()

    with pytest.raises(ProviderError):
        await adapter.normalize_incoming({"wa_id": "1"})


@pytest.mark.asyncio
async def test_channel_response_sender_routes_email_and_whatsapp() -> None:
    email = EmailChannelAdapter()
    whatsapp = WhatsAppChannelAdapter()
    sender = ChannelResponseSender(
        adapters={
            ChannelType.EMAIL: email,
            ChannelType.WHATSAPP: whatsapp,
        },
        fallback=InMemoryResponseSender(),
    )

    email_msg = Message(text="mail", channel=ChannelType.EMAIL, direction=MessageDirection.OUTBOUND)
    wa_msg = Message(text="wa", channel=ChannelType.WHATSAPP, direction=MessageDirection.OUTBOUND)

    await sender.send(email_msg)
    await sender.send(wa_msg)

    assert email.sent == [email_msg]
    assert whatsapp.sent == [wa_msg]


def test_email_webhook_creates_handoff_without_sources() -> None:
    with TestClient(app) as client:
        before = len(client.get("/manager-queue").json())
        response = client.post(
            "/channels/email/webhook",
            json={
                "subject": "Цена",
                "body": "Сколько стоит насос?",
                "from": "client@example.com",
            },
        )
        after = len(client.get("/manager-queue").json())

    assert response.status_code == 200
    assert response.json()["handoff_required"] is True
    assert after == before + 1


def test_whatsapp_webhook_creates_handoff_without_sources() -> None:
    with TestClient(app) as client:
        before = len(client.get("/manager-queue").json())
        response = client.post(
            "/channels/whatsapp/webhook",
            json={
                "text": "Сколько стоит насос?",
                "wa_id": "79001112233",
                "phone": "+79001112233",
            },
        )
        after = len(client.get("/manager-queue").json())

    assert response.status_code == 200
    assert response.json()["handoff_required"] is True
    assert after == before + 1


def test_email_and_whatsapp_webhooks_reject_invalid_payload() -> None:
    with TestClient(app) as client:
        email_response = client.post("/channels/email/webhook", json={"from": "a@b.c"})
        wa_response = client.post("/channels/whatsapp/webhook", json={"wa_id": "1"})

    assert email_response.status_code == 400
    assert wa_response.status_code == 400


def test_ai_core_does_not_know_email_or_whatsapp_adapters() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "EmailChannelAdapter" not in source
    assert "WhatsAppChannelAdapter" not in source
    assert "channel_adapters" not in source
