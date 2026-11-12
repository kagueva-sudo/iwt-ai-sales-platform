"""Background worker: poll IMAP and enqueue email drafts into /inbox."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.integrations.email.config import get_email_config, is_email_configured
from app.services.email_poller import EmailPoller
from app.services.knowledge_loader import default_knowledge_dir, seed_knowledge_from_dir

logger = logging.getLogger(__name__)


async def run_forever() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    await seed_knowledge_from_dir(default_knowledge_dir())

    while not is_email_configured():
        logger.warning(
            "Email worker waiting for config: set EMAIL_ENABLED=true and IMAP/SMTP credentials."
        )
        await asyncio.sleep(60)

    config = get_email_config()
    poller = EmailPoller()
    logger.info(
        "Email worker started (mailbox=%s, poll=%ss)",
        config.mailbox,
        config.poll_seconds,
    )
    while True:
        try:
            count = await poller.poll_once()
            if count:
                logger.info("Processed %s inbound email(s)", count)
        except Exception:
            logger.exception("Email poll cycle failed")
        await asyncio.sleep(get_email_config().poll_seconds)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
