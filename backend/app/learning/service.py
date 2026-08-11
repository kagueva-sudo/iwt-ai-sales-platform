from app.core.constants import HandoffReason
from app.domain.manager_queue import ManagerQueueItem
from app.domain.processing import ProcessingResult
from app.learning.eligibility import is_candidate_eligible
from app.learning.models import KnowledgeCandidate, LearningEvent, LearningEventType
from app.learning.repository import LearningRepository


class LearningService:
    """Creates learning events and pending knowledge candidates outside AI Core."""

    def __init__(self, repository: LearningRepository) -> None:
        self.repository = repository

    async def record_event(
        self,
        *,
        conversation_id: str,
        event_type: LearningEventType,
        payload: dict[str, str] | None = None,
    ) -> LearningEvent:
        event = LearningEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            payload=dict(payload or {}),
        )
        return await self.repository.add_event(event)

    async def on_handoff(self, result: ProcessingResult, request_id: str) -> KnowledgeCandidate | None:
        # Use queue request_id so manager-done can find the same candidate.
        conversation_id = request_id
        question = ""
        if result.conversation_history:
            question = result.conversation_history[-1]
        elif result.metadata.get("text"):
            question = result.metadata["text"]

        reason = result.handoff_reason.value if result.handoff_reason else ""
        await self.record_event(
            conversation_id=conversation_id,
            event_type=LearningEventType.HANDOFF,
            payload={
                "request_id": request_id,
                "dialog_id": result.metadata.get("dialog_id", ""),
                "session_id": result.metadata.get("session_id", ""),
                "handoff_reason": reason,
                "decision": result.decision.value,
            },
        )

        intent = result.metadata.get("intent") or self._infer_intent(result.handoff_reason)
        if not is_candidate_eligible(handoff_reason=result.handoff_reason, intent=intent):
            return None

        candidate = KnowledgeCandidate(
            conversation_id=conversation_id,
            question=question or "(unknown question)",
            ai_answer=result.response_text,
            source_refs=list(result.sources),
            intent=intent,
            reason=reason or result.metadata.get("reason"),
        )
        saved = await self.repository.add_candidate(candidate)
        await self.record_event(
            conversation_id=conversation_id,
            event_type=LearningEventType.KNOWLEDGE_CANDIDATE_CREATED,
            payload={"candidate_id": saved.id, "request_id": request_id},
        )
        return saved

    async def on_manager_done(
        self,
        item: ManagerQueueItem,
        *,
        manager_answer: str | None = None,
    ) -> KnowledgeCandidate | None:
        conversation_id = item.request_id
        answer = (manager_answer or "").strip() or None
        await self.record_event(
            conversation_id=conversation_id,
            event_type=LearningEventType.MANAGER_CORRECTION,
            payload={
                "request_id": item.request_id,
                "has_manager_answer": "true" if answer else "false",
            },
        )
        candidate = await self.repository.find_candidate_by_conversation(conversation_id)
        if candidate is None:
            return None
        if answer:
            candidate.manager_answer = answer
            await self.repository.update_candidate(candidate)
        return candidate

    def _infer_intent(self, handoff_reason: HandoffReason | None) -> str:
        if handoff_reason == HandoffReason.PRICE_UNKNOWN:
            return "price"
        if handoff_reason == HandoffReason.AVAILABILITY_UNKNOWN:
            return "stock"
        if handoff_reason == HandoffReason.NO_CONFIRMED_DATA:
            return "missing_knowledge"
        return "general"
