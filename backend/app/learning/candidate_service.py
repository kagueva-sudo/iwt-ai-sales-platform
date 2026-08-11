from datetime import UTC, datetime

from app.contracts.knowledge_repository import KnowledgeRepository
from app.contracts.logging_service import LoggingService
from app.core.errors import ProviderError
from app.domain.knowledge import KnowledgeItem
from app.learning.eligibility import is_publishable_as_faq
from app.learning.models import (
    KnowledgeCandidate,
    KnowledgeCandidateStatus,
    LearningEvent,
    LearningEventType,
)
from app.learning.repository import LearningRepository


class CandidateService:
    """Human review workflow for KnowledgeCandidate. Never auto-publishes."""

    def __init__(
        self,
        learning_repository: LearningRepository,
        knowledge_repository: KnowledgeRepository,
        logging_service: LoggingService | None = None,
    ) -> None:
        self.learning_repository = learning_repository
        self.knowledge_repository = knowledge_repository
        self.logging_service = logging_service

    async def list_candidates(
        self,
        status: KnowledgeCandidateStatus | None = None,
    ) -> list[KnowledgeCandidate]:
        return await self.learning_repository.list_candidates(status=status)

    async def get_candidate(self, candidate_id: str) -> KnowledgeCandidate | None:
        return await self.learning_repository.get_candidate(candidate_id)

    async def approve(
        self,
        candidate_id: str,
        *,
        reviewed_by: str,
    ) -> KnowledgeCandidate:
        candidate = await self.learning_repository.get_candidate(candidate_id)
        if candidate is None:
            raise ProviderError(f"Knowledge candidate {candidate_id} not found.")
        if candidate.status != KnowledgeCandidateStatus.PENDING:
            raise ProviderError(f"Candidate {candidate_id} is not pending.")
        if not is_publishable_as_faq(candidate.intent):
            raise ProviderError(
                "Commercial dynamic facts cannot be published from learning candidates."
            )

        content = (candidate.manager_answer or candidate.ai_answer or "").strip()
        if not content:
            raise ProviderError("Candidate has no manager/AI answer to publish.")

        kb_id = f"learning-{candidate.id[:8]}"
        kb_version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        item = KnowledgeItem(
            id=kb_id,
            title=candidate.question[:200] or "Learning FAQ",
            content=content,
            category="learning",
            item_type="faq",
            tags=["learning", "approved"],
            source="learning_loop",
            confirmed_fields={"id", "title", "content", "category", "item_type", "tags"},
            metadata={
                "candidate_id": candidate.id,
                "reviewed_by": reviewed_by,
                "kb_version": kb_version,
                "conversation_id": candidate.conversation_id,
            },
        )
        await self.knowledge_repository.add(item)

        candidate.status = KnowledgeCandidateStatus.APPROVED
        candidate.reviewed_at = datetime.now(UTC)
        candidate.reviewed_by = reviewed_by
        candidate.published_knowledge_id = kb_id
        candidate.kb_version = kb_version
        saved = await self.learning_repository.update_candidate(candidate)

        await self._audit(
            LearningEventType.KNOWLEDGE_CANDIDATE_APPROVED,
            candidate=saved,
            extra={
                "reviewed_by": reviewed_by,
                "kb_item_id": kb_id,
                "kb_version": kb_version,
                "source": "learning_loop",
            },
        )
        return saved

    async def reject(
        self,
        candidate_id: str,
        *,
        reviewed_by: str,
        reason: str | None = None,
    ) -> KnowledgeCandidate:
        candidate = await self.learning_repository.get_candidate(candidate_id)
        if candidate is None:
            raise ProviderError(f"Knowledge candidate {candidate_id} not found.")
        if candidate.status != KnowledgeCandidateStatus.PENDING:
            raise ProviderError(f"Candidate {candidate_id} is not pending.")

        candidate.status = KnowledgeCandidateStatus.REJECTED
        candidate.reviewed_at = datetime.now(UTC)
        candidate.reviewed_by = reviewed_by
        if reason:
            candidate.reason = reason
        saved = await self.learning_repository.update_candidate(candidate)
        await self._audit(
            LearningEventType.KNOWLEDGE_CANDIDATE_REJECTED,
            candidate=saved,
            extra={"reviewed_by": reviewed_by, "reason": reason or ""},
        )
        return saved

    async def _audit(
        self,
        event_type: LearningEventType,
        *,
        candidate: KnowledgeCandidate,
        extra: dict[str, str],
    ) -> None:
        await self.learning_repository.add_event(
            LearningEvent(
                conversation_id=candidate.conversation_id,
                event_type=event_type,
                payload={"candidate_id": candidate.id, **extra},
            )
        )
        if self.logging_service is not None:
            await self.logging_service.log_audit(
                event_type.value,
                {
                    "candidate_id": candidate.id,
                    "conversation_id": candidate.conversation_id,
                    **extra,
                },
                category="learning",
            )
