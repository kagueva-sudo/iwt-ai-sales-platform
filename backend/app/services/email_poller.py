"""IMAP poller: unread mail → Freeze pipeline → manager inbox (no auto-reply)."""

from __future__ import annotations

import logging

from app.api.channel_webhook import process_channel_webhook
from app.channel_adapters.email_adapter import EmailChannelAdapter
from app.integrations.email.config import get_email_config, is_email_configured
from app.integrations.email.imap_client import ImapEmailClient
from app.repositories.email_processed import EmailProcessedRepository

logger = logging.getLogger(__name__)


class EmailPoller:
    def __init__(
        self,
        *,
        imap_client: ImapEmailClient | None = None,
        processed_repo: EmailProcessedRepository | None = None,
        adapter: EmailChannelAdapter | None = None,
    ) -> None:
        self.config = get_email_config()
        self.imap = imap_client or ImapEmailClient(self.config)
        self.processed = processed_repo or EmailProcessedRepository()
        self.adapter = adapter or EmailChannelAdapter()

    async def poll_once(self, limit: int = 20) -> int:
        if not is_email_configured():
            logger.debug("Email poller skipped: not configured")
            return 0

        messages = self.imap.fetch_unseen(limit=limit)
        processed_count = 0
        seen_uids: list[str] = []

        for inbound in messages:
            message_id = (inbound.message_id or "").strip()
            if not message_id:
                continue
            if self.processed.exists(message_id):
                if inbound.imap_uid:
                    seen_uids.append(inbound.imap_uid)
                continue

            payload = {
                "message_id": message_id,
                "from": inbound.from_address,
                "subject": inbound.subject,
                "body": inbound.body or inbound.subject or "(пустое письмо)",
                "imap_uid": inbound.imap_uid or "",
            }
            try:
                result = await process_channel_webhook(self.adapter, payload)
            except Exception:
                logger.exception("Failed to process inbound email %s", message_id)
                continue

            self.processed.mark_processed(
                message_id,
                request_id=result.request_id,
                from_address=inbound.from_address,
                subject=inbound.subject,
            )
            if inbound.imap_uid:
                seen_uids.append(inbound.imap_uid)
            processed_count += 1

        if seen_uids:
            try:
                self.imap.mark_seen(seen_uids)
            except Exception:
                logger.exception("Failed to mark IMAP messages as Seen")

        return processed_count
