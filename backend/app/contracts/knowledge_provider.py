from abc import ABC, abstractmethod

from app.domain.sources import SourceSelectionResult


class KnowledgeProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> SourceSelectionResult:
        """Search confirmed knowledge sources."""
