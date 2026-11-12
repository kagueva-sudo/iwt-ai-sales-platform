"""Parse raw RFC822 email bytes into plain-text inbound fields."""

from __future__ import annotations

import email
import re
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr

from app.integrations.email.schemas import InboundEmail

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return value.strip()


def extract_address(value: str | None) -> str:
    _, addr = parseaddr(value or "")
    return addr.strip()


def html_to_text(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


def extract_body(msg: Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = (part.get_content_type() or "").lower()
            disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain":
                plain_parts.append(text.strip())
            elif content_type == "text/html":
                html_parts.append(html_to_text(text))
    else:
        payload = msg.get_payload(decode=True)
        if payload is not None:
            charset = msg.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            content_type = (msg.get_content_type() or "").lower()
            if content_type == "text/html":
                html_parts.append(html_to_text(text))
            else:
                plain_parts.append(text.strip())

    if plain_parts:
        return "\n\n".join(part for part in plain_parts if part).strip()
    return "\n\n".join(part for part in html_parts if part).strip()


def parse_raw_email(raw: bytes, *, imap_uid: str | None = None) -> InboundEmail:
    msg = email.message_from_bytes(raw)
    message_id = decode_mime_header(msg.get("Message-ID") or msg.get("Message-Id"))
    if not message_id:
        # Stable fallback when Message-ID is absent.
        message_id = f"generated-{abs(hash(raw))}"
    subject = decode_mime_header(msg.get("Subject"))
    from_address = extract_address(msg.get("From"))
    body = extract_body(msg)
    return InboundEmail(
        message_id=message_id,
        from_address=from_address,
        subject=subject,
        body=body,
        imap_uid=imap_uid,
    )
