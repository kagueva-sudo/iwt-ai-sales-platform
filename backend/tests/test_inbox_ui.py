from fastapi.testclient import TestClient

from app.main import app


def test_inbox_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/inbox")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Входящие" in response.text
        assert "/static/inbox/inbox.js" in response.text


def test_inbox_static_assets_are_served() -> None:
    with TestClient(app) as client:
        css = client.get("/static/inbox/styles.css")
        js = client.get("/static/inbox/inbox.js")
        assert css.status_code == 200
        assert "queue-list" in css.text
        assert js.status_code == 200
        assert "manager-queue" in js.text


def test_inbox_ui_does_not_import_ai_core() -> None:
    import app.main as main_module

    source = open(main_module.__file__, encoding="utf-8").read()
    assert "AICore" not in source
