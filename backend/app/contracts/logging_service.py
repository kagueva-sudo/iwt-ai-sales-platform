from abc import ABC, abstractmethod

from app.domain.processing import ProcessingResult


class LoggingService(ABC):
    """Unified AI / Audit / Error logging. No separate ErrorLogger or AuditLog."""

    @abstractmethod
    async def log_processing(self, result: ProcessingResult) -> None:
        """Record every processing outcome."""

    @abstractmethod
    async def log_error(self, result: ProcessingResult) -> None:
        """Record an error outcome."""

    @abstractmethod
    async def log_audit(
        self,
        event_type: str,
        details: dict[str, str],
        category: str = "audit",
    ) -> None:
        """Record an audit/pipeline event."""

    @abstractmethod
    async def list_events(
        self,
        request_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, str]]:
        """Return persisted events for diagnostics/tests."""
