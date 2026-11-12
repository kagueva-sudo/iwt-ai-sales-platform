from email.message import EmailMessage

from app.integrations.email.parsing import parse_raw_email


def _raw_from_message(msg: EmailMessage) -> bytes:
    return msg.as_bytes()


def test_parse_plain_email() -> None:
    msg = EmailMessage()
    msg["From"] = "Client <client@example.com>"
    msg["Subject"] = "Нужен принтер"
    msg["Message-ID"] = "<abc-123@example.com>"
    msg.set_content("Здравствуйте, подскажите модель.")
    inbound = parse_raw_email(_raw_from_message(msg), imap_uid="10")
    assert inbound.from_address == "client@example.com"
    assert inbound.subject == "Нужен принтер"
    assert "подскажите модель" in inbound.body
    assert inbound.message_id == "<abc-123@example.com>"
    assert inbound.imap_uid == "10"


def test_parse_html_fallback() -> None:
    msg = EmailMessage()
    msg["From"] = "a@b.ru"
    msg["Subject"] = "HTML"
    msg["Message-ID"] = "<html-1@b.ru>"
    msg.set_content("<p>Оплата <b>безналом</b></p>", subtype="html")
    inbound = parse_raw_email(_raw_from_message(msg))
    assert "Оплата" in inbound.body
    assert "безналом" in inbound.body
