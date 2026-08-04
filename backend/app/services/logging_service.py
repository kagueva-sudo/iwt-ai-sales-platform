import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.logging_service import LoggingService
from app.db.models import ProcessingLogModel
from app.db.session import SessionLocal
from app.domain.processing import ProcessingResult


@dataclass(slots=True)
class LogRecord:
    category: str
    event_type: str
    details: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def request_id(self) -> str | None:
        value = self.details.get("request_id")
        return value or None


class InMemoryLoggingService(LoggingService):
    """In-memory LoggingService for unit tests."""

    def __init__(self) -> None:
        self.records: list[LogRecord] = []

    async def log_processing(self, result: ProcessingResult) -> None:
        await self.log_audit(
            "processing",
            {
                "decision": result.decision.value,
                "request_id": result.request_id or "",
                "response_text": result.response_text or "",
                "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
                "sources": ",".join(result.sources),
                "errors": "|".join(result.errors),
            },
            category="ai",
        )

    async def log_error(self, result: ProcessingResult) -> None:
        await self.log_audit(
            "processing_error",
            {
                "decision": result.decision.value,
                "request_id": result.request_id or "",
                "errors": "|".join(result.errors) or "unknown_error",
                "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
            },
            category="error",
        )

    async def log_audit(
        self,
        event_type: str,
        details: dict[str, str],
        category: str = "audit",
    ) -> None:
        self.records.append(LogRecord(category=category, event_type=event_type, details=dict(details)))

    async def list_events(
        self,
        request_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for record in self.records:
            if request_id is not None and record.details.get("request_id") != request_id:
                continue
            if event_type is not None and record.event_type != event_type:
                continue
            events.append(
                {
                    "id": record.id,
                    "category": record.category,
                    "event_type": record.event_type,
                    "request_id": record.details.get("request_id", ""),
                    "details": json.dumps(record.details, ensure_ascii=False),
                    "created_at": record.created_at.isoformat(),
                }
            )
        return events


class SqlAlchemyLoggingService(LoggingService):
    """PostgreSQL/SQLite-backed unified LoggingService."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    async def log_processing(self, result: ProcessingResult) -> None:
        await self.log_audit(
            "processing",
            {
                "decision": result.decision.value,
                "request_id": result.request_id or "",
                "response_text": result.response_text or "",
                "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
                "sources": ",".join(result.sources),
                "errors": "|".join(result.errors),
            },
            category="ai",
        )

    async def log_error(self, result: ProcessingResult) -> None:
        await self.log_audit(
            "processing_error",
            {
                "decision": result.decision.value,
                "request_id": result.request_id or "",
                "errors": "|".join(result.errors) or "unknown_error",
                "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
            },
            category="error",
        )

    async def log_audit(
        self,
        event_type: str,
        details: dict[str, str],
        category: str = "audit",
    ) -> None:
        payload = dict(details)
        with self._session_factory() as session:
            session.add(
                ProcessingLogModel(
                    id=str(uuid4()),
                    category=category,
                    event_type=event_type,
                    request_id=payload.get("request_id") or None,
                    details_json=json.dumps(payload, ensure_ascii=False),
                )
            )
            session.commit()

    async def list_events(
        self,
        request_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, str]]:
        with self._session_factory() as session:
            stmt = select(ProcessingLogModel).order_by(ProcessingLogModel.created_at.asc())
            if request_id is not None:
                stmt = stmt.where(ProcessingLogModel.request_id == request_id)
            if event_type is not None:
                stmt = stmt.where(ProcessingLogModel.event_type == event_type)
            rows = session.scalars(stmt).all()
            return [
                {
                    "id": row.id,
                    "category": row.category,
                    "event_type": row.event_type,
                    "request_id": row.request_id or "",
                    "details": row.details_json,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
