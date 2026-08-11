from datetime import datetime

from pydantic import BaseModel, Field

from app.learning.models import KnowledgeCandidateStatus, LearningEventType


class KnowledgeCandidateSchema(BaseModel):
    id: str
    conversation_id: str
    question: str
    ai_answer: str | None = None
    manager_answer: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    intent: str | None = None
    reason: str | None = None
    status: KnowledgeCandidateStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    published_knowledge_id: str | None = None
    kb_version: str | None = None


class CandidateReviewSchema(BaseModel):
    reviewed_by: str = Field(min_length=1)
    reason: str | None = None


class LearningEventSchema(BaseModel):
    id: str
    conversation_id: str
    event_type: LearningEventType
    payload: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
