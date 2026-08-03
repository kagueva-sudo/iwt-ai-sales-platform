from app.ai_core.core import AICore
from app.contracts.prompt_builder import PromptBuilder
from app.domain.conversations import ConversationMessage
from app.domain.messages import Message
from app.domain.processing import ProcessingResult
from app.knowledge_layer.source_selector import SourceSelector
from app.services.conversation_state_service import ConversationStateService


class MessagePipelineService:
    """Assembles Freeze pipeline up to ProcessingResult (DecisionRouter stays outside)."""

    def __init__(
        self,
        conversation_state: ConversationStateService,
        source_selector: SourceSelector,
        prompt_builder: PromptBuilder,
        ai_core: AICore,
    ) -> None:
        self.conversation_state = conversation_state
        self.source_selector = source_selector
        self.prompt_builder = prompt_builder
        self.ai_core = ai_core

    async def process(self, message: Message) -> ProcessingResult:
        session, conversation = await self.conversation_state.prepare_for_message(message)
        selection = await self.source_selector.select_sources(message.text)
        prompt_context = await self.prompt_builder.build(
            message=message,
            session=session,
            conversation=conversation,
            verified_sources=selection.sources,
            available_tools=[],
        )
        result = await self.ai_core.process(prompt_context)

        if result.response_text:
            await self.conversation_state.append_message(
                session.dialog_id,
                ConversationMessage(role="assistant", text=result.response_text),
            )

        result.metadata.setdefault("session_id", session.session_id)
        result.metadata.setdefault("dialog_id", session.dialog_id)
        result.metadata.setdefault("sources_count", str(len(selection.sources)))
        return result
