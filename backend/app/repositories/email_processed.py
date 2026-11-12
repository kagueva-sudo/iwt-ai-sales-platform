from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import EmailProcessedModel
from app.db.session import SessionLocal


class EmailProcessedRepository:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal

    def exists(self, message_id: str) -> bool:
        if not message_id.strip():
            return False
        with self._session_factory() as session:
            return session.get(EmailProcessedModel, message_id.strip()) is not None

    def mark_processed(
        self,
        message_id: str,
        *,
        request_id: str | None = None,
        from_address: str | None = None,
        subject: str | None = None,
    ) -> None:
        cleaned = message_id.strip()
        if not cleaned:
            return
        with self._session_factory() as session:
            existing = session.get(EmailProcessedModel, cleaned)
            if existing is not None:
                return
            session.add(
                EmailProcessedModel(
                    message_id=cleaned,
                    request_id=request_id,
                    from_address=from_address,
                    subject=subject,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()
