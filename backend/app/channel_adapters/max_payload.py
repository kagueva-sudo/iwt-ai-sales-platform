from typing import Any

from app.channel_adapters.payload import first_str


def extract_max_text(payload: dict[str, object]) -> str | None:
    """Extract user text from simplified or native MAX webhook payloads."""
    direct = first_str(payload, ("text",))
    if direct:
        return direct

    body = payload.get("body")
    if isinstance(body, dict):
        text = first_str(body, ("text",))
        if text:
            return text

    message = payload.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, dict):
            text = first_str(body, ("text",))
            if text:
                return text
        text = first_str(message, ("text",))
        if text:
            return text

    return None


def extract_max_user_id(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("user_id", "customer_id"))
    if direct:
        return direct

    sender = payload.get("sender")
    if isinstance(sender, dict):
        uid = first_str(sender, ("user_id", "id"))
        if uid:
            return uid

    user = payload.get("user")
    if isinstance(user, dict):
        uid = first_str(user, ("user_id", "id"))
        if uid:
            return uid

    for key in ("user_id",):
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def extract_max_chat_id(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("chat_id",))
    if direct:
        return direct

    recipient = payload.get("recipient")
    if isinstance(recipient, dict):
        chat_id = first_str(recipient, ("chat_id", "chatId"))
        if chat_id:
            return chat_id

    message = payload.get("message")
    if isinstance(message, dict):
        recipient = message.get("recipient")
        if isinstance(recipient, dict):
            chat_id = first_str(recipient, ("chat_id", "chatId"))
            if chat_id:
                return chat_id

    value = payload.get("chat_id")
    if value is not None and str(value).strip():
        return str(value).strip()

    return None


def extract_max_username(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("username", "contact"))
    if direct:
        return direct

    for key in ("sender", "user"):
        block = payload.get(key)
        if isinstance(block, dict):
            username = first_str(block, ("username",))
            if username:
                return username if username.startswith("@") else f"@{username}"

    return None


def extract_max_external_message_id(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("external_message_id", "message_id"))
    if direct:
        return direct

    message = payload.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, dict):
            mid = first_str(body, ("mid", "message_id"))
            if mid:
                return mid
        mid = first_str(message, ("mid", "message_id"))
        if mid:
            return mid

    return first_str(payload, ("message_id",))


def is_max_processable_update(payload: dict[str, object]) -> bool:
    """Return True for text messages we should send to AI pipeline."""
    update_type = first_str(payload, ("update_type", "type", "event"))
    if update_type:
        normalized = update_type.lower()
        if normalized in {"message_callback", "bot_started"}:
            return False
        if normalized not in {"message_created", "message"}:
            return False
    return extract_max_text(payload) is not None


def as_plain_dict(payload: Any) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    return {}
