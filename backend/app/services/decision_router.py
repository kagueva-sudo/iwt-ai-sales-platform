from uuid import uuid4

from app.contracts.decision_router import DecisionRouter
from app.contracts.handoff_manager import HandoffManager
from app.contracts.logging_service import LoggingService
from app.contracts.response_sender import ResponseSender
from app.core.constants import ChannelType, MessageDirection
from app.domain.messages import Message
from app.domain.pipeline_events import PipelineEventType
from app.domain.processing import ProcessingDecision, ProcessingResult


class DefaultDecisionRouter(DecisionRouter):
    """Thin router: dispatches ProcessingResult only. No AI/business analysis."""

    def __init__(
        self,
        response_sender: ResponseSender,
        handoff_manager: HandoffManager,
        logging_service: LoggingService,
    ) -> None:
        self.response_sender = response_sender
        self.handoff_manager = handoff_manager
        self.logging_service = logging_service

    async def route(self, result: ProcessingResult) -> None:
        await self.logging_service.log_processing(result)
        await self.logging_service.log_audit(
            PipelineEventType.DECISION_ROUTER.value,
            {
                "request_id": result.request_id or "",
                "decision": result.decision.value,
            },
            category="pipeline",
        )

        if result.decision == ProcessingDecision.RESPOND:
            await self.response_sender.send(self._to_outbound_message(result))
            await self.logging_service.log_audit(
                PipelineEventType.RESPONSE_SENT.value,
                {
                    "request_id": result.request_id or "",
                    "channel": (result.channel or ChannelType.INTERNAL).value,
                    "response_text": result.response_text or "",
                },
                category="pipeline",
            )
            return

        if result.decision in (ProcessingDecision.HANDOFF, ProcessingDecision.NEEDS_MORE_DATA):
            if result.response_text:
                await self.response_sender.send(self._to_outbound_message(result))
                await self.logging_service.log_audit(
                    PipelineEventType.RESPONSE_SENT.value,
                    {
                        "request_id": result.request_id or "",
                        "channel": (result.channel or ChannelType.INTERNAL).value,
                        "response_text": result.response_text,
                        "with_handoff": "true",
                    },
                    category="pipeline",
                )
            handoff_id = await self.handoff_manager.create_handoff(result)
            await self.logging_service.log_audit(
                PipelineEventType.HANDOFF.value,
                {
                    "request_id": result.request_id or "",
                    "handoff_id": handoff_id,
                    "decision": result.decision.value,
                    "handoff_reason": result.handoff_reason.value if result.handoff_reason else "",
                },
                category="pipeline",
            )
            return

        if result.decision == ProcessingDecision.ERROR:
            await self.logging_service.log_error(result)

    def _to_outbound_message(self, result: ProcessingResult) -> Message:
        return Message(
            text=result.response_text or "",
            channel=result.channel or ChannelType.INTERNAL,
            direction=MessageDirection.OUTBOUND,
            customer_id=result.customer_name,
            customer_contact=result.customer_contact,
            id=result.request_id or str(uuid4()),
        )
