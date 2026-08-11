from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class KnowledgeCandidateStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LearningEventType(StrEnum):
    ANSWER_FAILED = "answer_failed"
    HANDOFF = "handoff"
    MANAGER_CORRECTION = "manager_correction"
    RETRIEVAL_FAILURE = "retrieval_failure"
    VALIDATOR_REJECTION = "validator_rejection"
    HALLUCINATION_DETECTED = "hallucination_detected"
    KNOWLEDGE_CANDIDATE_CREATED = "knowledge_candidate_created"
    KNOWLEDGE_CANDIDATE_APPROVED = "knowledge_candidate_approved"
    KNOWLEDGE_CANDIDATE_REJECTED = "knowledge_candidate_rejected"


@dataclass(slots=True)
class KnowledgeCandidate:
    conversation_id: str
    question: str
    ai_answer: str | None = None
    manager_answer: str | None = None
    source_refs: list[str] = field(default_factory=list)
    intent: str | None = None
    reason: str | None = None
    status: KnowledgeCandidateStatus = KnowledgeCandidateStatus.PENDING
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    published_knowledge_id: str | None = None
    kb_version: str | None = None


@dataclass(slots=True)
class LearningEvent:
    conversation_id: str
    event_type: LearningEventType
    payload: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
