from abc import ABC, abstractmethod

from app.domain.handoff import HandoffCase


class HandoffManager(ABC):
    @abstractmethod
    async def create_handoff(self, handoff_case: HandoffCase) -> str:
        """Create handoff case and return internal id."""
