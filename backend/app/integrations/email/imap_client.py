"""IMAP client for unread inbox fetch (Yandex-compatible)."""

from __future__ import annotations

import imaplib
from collections.abc import Sequence

from app.integrations.email.config import EmailConfig
from app.integrations.email.exceptions import EmailError, EmailNotConfiguredError, EmailTransportError
from app.integrations.email.parsing import parse_raw_email
from app.integrations.email.schemas import InboundEmail


class ImapEmailClient:
    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def _connect(self) -> imaplib.IMAP4_SSL:
        if not self.config.username or not self.config.password:
            raise EmailNotConfiguredError("EMAIL_USERNAME/EMAIL_PASSWORD are required.")
        try:
            client = imaplib.IMAP4_SSL(self.config.imap_host, self.config.imap_port)
            client.login(self.config.username, self.config.password)
            return client
        except Exception as exc:  # noqa: BLE001 — surface as transport error
            raise EmailTransportError(f"IMAP connect failed: {exc}") from exc

    def fetch_unseen(self, limit: int = 20) -> list[InboundEmail]:
        client = self._connect()
        try:
            status, _ = client.select(self.config.mailbox)
            if status != "OK":
                raise EmailTransportError(f"IMAP select {self.config.mailbox!r} failed.")
            status, data = client.search(None, "UNSEEN")
            if status != "OK":
                raise EmailTransportError("IMAP SEARCH UNSEEN failed.")
            ids = (data[0] or b"").split()
            if not ids:
                return []
            selected = ids[-limit:]
            messages: list[InboundEmail] = []
            for raw_id in selected:
                uid = raw_id.decode("ascii", errors="ignore")
                status, fetched = client.fetch(raw_id, "(RFC822)")
                if status != "OK" or not fetched or not fetched[0]:
                    continue
                part = fetched[0]
                if not isinstance(part, tuple) or len(part) < 2:
                    continue
                raw = part[1]
                if not isinstance(raw, (bytes, bytearray)):
                    continue
                messages.append(parse_raw_email(bytes(raw), imap_uid=uid))
            return messages
        except EmailError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmailTransportError(f"IMAP fetch failed: {exc}") from exc
        finally:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass

    def mark_seen(self, uids: Sequence[str]) -> None:
        if not uids:
            return
        client = self._connect()
        try:
            status, _ = client.select(self.config.mailbox)
            if status != "OK":
                raise EmailTransportError(f"IMAP select {self.config.mailbox!r} failed.")
            for uid in uids:
                if not uid:
                    continue
                client.store(uid.encode("ascii"), "+FLAGS", "\\Seen")
        except EmailError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmailTransportError(f"IMAP mark seen failed: {exc}") from exc
        finally:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass
