from app.ai_core.core import AICore
from app.contracts.logging_service import LoggingService
from app.contracts.prompt_builder import PromptBuilder
from app.domain.conversations import ConversationMessage
from app.domain.messages import Message
from app.domain.pipeline_events import PipelineEventType
from app.domain.processing import ProcessingDecision, ProcessingResult
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
        logging_service: LoggingService | None = None,
    ) -> None:
        self.conversation_state = conversation_state
        self.source_selector = source_selector
        self.prompt_builder = prompt_builder
        self.ai_core = ai_core
        self.logging_service = logging_service

    async def process(self, message: Message) -> ProcessingResult:
        request_id = message.id
        await self._log(
            PipelineEventType.MESSAGE_RECEIVED,
            {
                "request_id": request_id,
                "channel": message.channel.value,
                "text": message.text,
                "customer_id": message.customer_id or "",
                "customer_contact": message.customer_contact or "",
            },
        )

        session, conversation = await self.conversation_state.prepare_for_message(message)
        selection = await self.source_selector.select_sources(message.text)
        await self._log(
            PipelineEventType.SOURCES_SELECTED,
            {
                "request_id": request_id,
                "sources_count": str(len(selection.sources)),
                "source_ids": ",".join(source.source_id for source in selection.sources),
            },
        )

        prompt_context = await self.prompt_builder.build(
            message=message,
            session=session,
            conversation=conversation,
            verified_sources=selection.sources,
            available_tools=[],
        )
        await self._log(
            PipelineEventType.PROMPT_BUILT,
            {
                "request_id": request_id,
                "prompt_type": prompt_context.metadata.prompt_type,
                "has_sources": str(bool(prompt_context.verified_sources)).lower(),
            },
        )

        result = await self.ai_core.process(prompt_context)
        await self._log_ai_core_outcome(request_id, had_sources=bool(selection.sources), result=result)

        if result.response_text:
            await self.conversation_state.append_message(
                session.dialog_id,
                ConversationMessage(role="assistant", text=result.response_text),
            )

        result.request_id = request_id
        result.channel = message.channel
        result.customer_name = message.customer_id
        result.customer_contact = message.customer_contact
        result.conversation_history = [item.text for item in conversation.recent_messages]
        result.metadata.setdefault("session_id", session.session_id)
        result.metadata.setdefault("dialog_id", session.dialog_id)
        result.metadata.setdefault("sources_count", str(len(selection.sources)))
        return result

    async def _log_ai_core_outcome(
        self,
        request_id: str,
        *,
        had_sources: bool,
        result: ProcessingResult,
    ) -> None:
        if had_sources:
            await self._log(
                PipelineEventType.LLM_CALLED,
                {
                    "request_id": request_id,
                    "status": "error" if result.decision == ProcessingDecision.ERROR else "completed",
                    "errors": "|".join(result.errors),
                },
            )

        if had_sources and result.decision != ProcessingDecision.ERROR:
            await self._log(
                PipelineEventType.VALIDATOR_DECISION,
                {
                    "request_id": request_id,
                    "decision": result.decision.value,
                    "reason": result.metadata.get("reason", ""),
                    "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
                },
            )
        elif not had_sources:
            await self._log(
                PipelineEventType.VALIDATOR_DECISION,
                {
                    "request_id": request_id,
                    "decision": result.decision.value,
                    "reason": result.metadata.get("reason", "no_verified_sources"),
                    "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
                },
            )

    async def _log(self, event_type: PipelineEventType, details: dict[str, str]) -> None:
        if self.logging_service is None:
            return
        await self.logging_service.log_audit(event_type.value, details, category="pipeline")
