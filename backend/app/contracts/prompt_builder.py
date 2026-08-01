from abc import ABC, abstractmethod

from app.domain.conversations import ConversationContext
from app.domain.messages import Message
from app.domain.prompt_context import PromptContext
from app.domain.sessions import SessionContext
from app.domain.sources import VerifiedSource
from app.domain.tools import ToolDescription


class PromptBuilder(ABC):
    @abstractmethod
    async def build(
        self,
        message: Message,
        session: SessionContext,
        conversation: ConversationContext,
        verified_sources: list[VerifiedSource],
        available_tools: list[ToolDescription],
    ) -> PromptContext:
        """Build PromptContext from already prepared data."""
