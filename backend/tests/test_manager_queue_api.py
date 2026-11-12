from fastapi.testclient import TestClient

from app.main import app


def test_manager_queue_lists_handoff_from_channel_webhook() -> None:
    with TestClient(app) as client:
        before = len(client.get("/manager-queue").json())
        webhook = client.post(
            "/channels/website/form",
            json={
                "message": "Сколько стоит насос?",
                "email": "client@example.com",
                "form_id": "mq-form-1",
            },
        )
        assert webhook.status_code == 200
        assert webhook.json()["handoff_required"] is False

        after = len(client.get("/manager-queue").json())

    # Для запросов по цене/остатку без точного товара мы отвечаем клиенту,
    # а не создаём handoff кейс в менеджерскую очередь.
    assert after == before


def test_manager_queue_get_and_update_status() -> None:
    import asyncio
    from uuid import uuid4

    from app.core.constants import ChannelType, HandoffReason
    from app.domain.manager_queue import ManagerQueueItem
    from app.services.composition import get_manager_queue_repository

    request_id = f"mq-api-{uuid4()}"

    async def _seed() -> None:
        await get_manager_queue_repository().add(
            ManagerQueueItem(
                request_id=request_id,
                channel=ChannelType.MAX,
                customer_name="Test Client",
                customer_contact="+79990000001",
                conversation_history=["Нужна помощь"],
                ai_response="Передаю менеджеру",
                handoff_reason=HandoffReason.NO_INFORMATION,
            )
        )

    asyncio.run(_seed())

    with TestClient(app) as client:
        detail = client.get(f"/manager-queue/{request_id}")
        assert detail.status_code == 200
        assert detail.json()["request_id"] == request_id
        assert detail.json()["channel"] == "max"

        updated = client.patch(
            f"/manager-queue/{request_id}/status",
            json={"status": "in_progress"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "in_progress"

        done = client.patch(
            f"/manager-queue/{request_id}/status",
            json={"status": "done"},
        )
        assert done.status_code == 200
        assert done.json()["status"] == "done"

        new_items = client.get("/manager-queue", params={"status": "new"}).json()
        assert all(item["request_id"] != request_id for item in new_items)


def test_manager_queue_not_found() -> None:
    with TestClient(app) as client:
        missing = client.get("/manager-queue/does-not-exist")
        update = client.patch(
            "/manager-queue/does-not-exist/status",
            json={"status": "cancelled"},
        )

    assert missing.status_code == 404
    assert update.status_code == 404


def test_manager_queue_api_does_not_import_ai_core() -> None:
    import app.api.manager_queue as api_module
    import app.services.manager_queue_service as service_module

    api_source = open(api_module.__file__, encoding="utf-8").read()
    service_source = open(service_module.__file__, encoding="utf-8").read()

    assert "ai_core" not in api_source
    assert "AICore" not in api_source
    assert "ai_core" not in service_source
    assert "PromptBuilder" not in service_source


def test_manager_queue_lists_all_items() -> None:
    with TestClient(app) as client:
        before = len(client.get("/manager-queue").json())
        response = client.post(
            "/channels/email/webhook",
            json={
                "subject": "Вопрос",
                "body": "Нужна цена",
                "from": "mq@example.com",
                "message_id": "<mq-email-list@example.com>",
            },
        )
        assert response.status_code == 200
        assert response.json()["handoff_required"] is True
        after = client.get("/manager-queue").json()

    # Email — всегда в /inbox с черновиком AI (без автоответа клиенту).
    assert len(after) == before + 1
    assert after[0]["channel"] == "email"
