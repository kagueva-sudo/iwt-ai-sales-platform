from abc import abstractmethod

from app.domain.handoff import HandoffCase
from app.providers.base import Provider


class CRMProvider(Provider):
    @abstractmethod
    async def create_handoff_case(self, handoff_case: HandoffCase) -> str:
        """Create lead, task, or comment in CRM and return external id."""
