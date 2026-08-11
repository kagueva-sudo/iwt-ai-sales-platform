from fastapi.testclient import TestClient

from app.main import app


def test_gateway_accepts_normalized_message() -> None:
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
