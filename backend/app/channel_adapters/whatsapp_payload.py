from typing import Any

from app.channel_adapters.payload import first_str


def _as_dict(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_change_value(payload: dict[str, object]) -> dict[str, Any] | None:
    for entry in _as_list(payload.get("entry")):
        entry_dict = _as_dict(entry)
        if entry_dict is None:
            continue
        for change in _as_list(entry_dict.get("changes")):
            change_dict = _as_dict(change)
            if change_dict is None:
                continue
            value = _as_dict(change_dict.get("value"))
            if value is not None:
                return value
    return None


def _first_message(payload: dict[str, object]) -> dict[str, Any] | None:
    value = _first_change_value(payload)
    if value is None:
        return None
    for message in _as_list(value.get("messages")):
        message_dict = _as_dict(message)
        if message_dict is not None:
            return message_dict
    return None


def is_whatsapp_cloud_payload(payload: dict[str, object]) -> bool:
    return payload.get("object") == "whatsapp_business_account" or _first_change_value(payload) is not None


def is_whatsapp_processable_update(payload: dict[str, object]) -> bool:
    """True when payload has inbound user text (simplified or Cloud API)."""
    if first_str(payload, ("text", "body", "message", "caption")):
        return True
    message = _first_message(payload)
    if message is None:
        return False
    if message.get("type") != "text":
        return False
    text_block = _as_dict(message.get("text"))
    if text_block is None:
        return False
    body = text_block.get("body")
    return isinstance(body, str) and bool(body.strip())


def extract_whatsapp_text(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("text", "body", "message", "caption"))
    if direct:
        return direct

    message = _first_message(payload)
    if message is None:
        return None
    text_block = _as_dict(message.get("text"))
    if text_block is None:
        return None
    body = text_block.get("body")
    if isinstance(body, str) and body.strip():
        return body.strip()
    return None


def extract_whatsapp_wa_id(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("wa_id", "user_id", "customer_id", "chat_id", "from"))
    if direct:
        return direct.lstrip("+")

    message = _first_message(payload)
    if message is not None:
        sender = message.get("from")
        if sender is not None and str(sender).strip():
            return str(sender).strip().lstrip("+")

    value = _first_change_value(payload)
    if value is None:
        return None
    for contact in _as_list(value.get("contacts")):
        contact_dict = _as_dict(contact)
        if contact_dict is None:
            continue
        wa_id = contact_dict.get("wa_id")
        if wa_id is not None and str(wa_id).strip():
            return str(wa_id).strip().lstrip("+")
    return None


def extract_whatsapp_contact_name(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("profile_name", "contact", "phone", "from"))
    if direct:
        return direct

    value = _first_change_value(payload)
    if value is None:
        return None
    for contact in _as_list(value.get("contacts")):
        contact_dict = _as_dict(contact)
        if contact_dict is None:
            continue
        profile = _as_dict(contact_dict.get("profile"))
        if profile is None:
            continue
        name = profile.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def extract_whatsapp_external_message_id(payload: dict[str, object]) -> str | None:
    direct = first_str(payload, ("message_id", "id"))
    if direct:
        return direct

    message = _first_message(payload)
    if message is None:
        return None
    mid = message.get("id")
    if mid is not None and str(mid).strip():
        return str(mid).strip()
    return None
