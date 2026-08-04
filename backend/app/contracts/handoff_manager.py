from abc import ABC, abstractmethod

from app.domain.processing import ProcessingResult


class HandoffManager(ABC):
    @abstractmethod
    async def create_handoff(self, result: ProcessingResult) -> str:
        """Create manager queue item from ProcessingResult and return request_id."""
