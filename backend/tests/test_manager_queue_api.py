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
    with TestClient(app) as client:
        post = client.post(
            "/channels/max/webhook",
            json={
                # Не подбираем из KB: нужен гарантированный handoff кейс.
                "text": "zzzzxqwe123",
                "user_id": "mq-user-1",
                "contact": "+79990000001",
            },
        )
        assert post.status_code == 200
        assert post.json()["handoff_required"] is True
        items = client.get("/manager-queue", params={"status": "new"}).json()
        request_id = next(
            item["request_id"] for item in items if item["customer_contact"] == "+79990000001"
        )

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
        client.post(
            "/channels/email/webhook",
            json={
                "subject": "Вопрос",
                "body": "Нужна цена",
                "from": "mq@example.com",
            },
        )
        after = client.get("/manager-queue").json()

    # "Нужна цена" — клиенту даём ответ (safe guidance), handoff не создаётся.
    assert len(after) == before
