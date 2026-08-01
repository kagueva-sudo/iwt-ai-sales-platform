from abc import ABC, abstractmethod

from app.domain.processing import ProcessingResult


class DecisionRouter(ABC):
    @abstractmethod
    async def route(self, result: ProcessingResult) -> None:
        """Route already decided processing result to its handler."""
