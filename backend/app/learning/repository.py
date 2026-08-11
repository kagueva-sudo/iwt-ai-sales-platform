import json
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.db.models import KnowledgeCandidateModel, LearningEventModel
from app.db.session import SessionLocal
from app.learning.models import (
    KnowledgeCandidate,
    KnowledgeCandidateStatus,
    LearningEvent,
    LearningEventType,
)


class LearningRepository:
    async def add_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        raise NotImplementedError

    async def get_candidate(self, candidate_id: str) -> KnowledgeCandidate | None:
        raise NotImplementedError

    async def list_candidates(
        self,
        status: KnowledgeCandidateStatus | None = None,
    ) -> list[KnowledgeCandidate]:
        raise NotImplementedError

    async def update_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        raise NotImplementedError

    async def find_candidate_by_conversation(self, conversation_id: str) -> KnowledgeCandidate | None:
        raise NotImplementedError

    async def add_event(self, event: LearningEvent) -> LearningEvent:
        raise NotImplementedError

    async def list_events(self, conversation_id: str | None = None) -> list[LearningEvent]:
        raise NotImplementedError


class InMemoryLearningRepository(LearningRepository):
    def __init__(self) -> None:
        self._candidates: dict[str, KnowledgeCandidate] = {}
        self._events: dict[str, LearningEvent] = {}

    async def add_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        self._candidates[candidate.id] = candidate
        return candidate

    async def get_candidate(self, candidate_id: str) -> KnowledgeCandidate | None:
        return self._candidates.get(candidate_id)

    async def list_candidates(
        self,
        status: KnowledgeCandidateStatus | None = None,
    ) -> list[KnowledgeCandidate]:
        items = list(self._candidates.values())
        if status is not None:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    async def update_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        self._candidates[candidate.id] = candidate
        return candidate

    async def find_candidate_by_conversation(self, conversation_id: str) -> KnowledgeCandidate | None:
        matches = [
            item
            for item in self._candidates.values()
            if item.conversation_id == conversation_id
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.created_at, reverse=True)[0]

    async def add_event(self, event: LearningEvent) -> LearningEvent:
        self._events[event.id] = event
        return event

    async def list_events(self, conversation_id: str | None = None) -> list[LearningEvent]:
        items = list(self._events.values())
        if conversation_id is not None:
            items = [item for item in items if item.conversation_id == conversation_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)


class SqlAlchemyLearningRepository(LearningRepository):
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal

    async def add_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        with self._session_factory() as session:
            session.add(self._candidate_to_model(candidate))
            session.commit()
        return candidate

    async def get_candidate(self, candidate_id: str) -> KnowledgeCandidate | None:
        with self._session_factory() as session:
            model = session.get(KnowledgeCandidateModel, candidate_id)
            return self._candidate_to_domain(model) if model is not None else None

    async def list_candidates(
        self,
        status: KnowledgeCandidateStatus | None = None,
    ) -> list[KnowledgeCandidate]:
        with self._session_factory() as session:
            query = session.query(KnowledgeCandidateModel)
            if status is not None:
                query = query.filter(KnowledgeCandidateModel.status == status.value)
            rows = query.order_by(KnowledgeCandidateModel.created_at.desc()).all()
            return [self._candidate_to_domain(row) for row in rows]

    async def update_candidate(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate:
        with self._session_factory() as session:
            model = session.get(KnowledgeCandidateModel, candidate.id)
            if model is None:
                session.add(self._candidate_to_model(candidate))
            else:
                self._apply_candidate(model, candidate)
            session.commit()
        return candidate

    async def find_candidate_by_conversation(self, conversation_id: str) -> KnowledgeCandidate | None:
        with self._session_factory() as session:
            model = (
                session.query(KnowledgeCandidateModel)
                .filter(KnowledgeCandidateModel.conversation_id == conversation_id)
                .order_by(KnowledgeCandidateModel.created_at.desc())
                .first()
            )
            return self._candidate_to_domain(model) if model is not None else None

    async def add_event(self, event: LearningEvent) -> LearningEvent:
        with self._session_factory() as session:
            session.add(self._event_to_model(event))
            session.commit()
        return event

    async def list_events(self, conversation_id: str | None = None) -> list[LearningEvent]:
        with self._session_factory() as session:
            query = session.query(LearningEventModel)
            if conversation_id is not None:
                query = query.filter(LearningEventModel.conversation_id == conversation_id)
            rows = query.order_by(LearningEventModel.created_at.desc()).all()
            return [self._event_to_domain(row) for row in rows]

    def _candidate_to_model(self, candidate: KnowledgeCandidate) -> KnowledgeCandidateModel:
        model = KnowledgeCandidateModel(id=candidate.id)
        self._apply_candidate(model, candidate)
        return model

    def _apply_candidate(self, model: KnowledgeCandidateModel, candidate: KnowledgeCandidate) -> None:
        model.conversation_id = candidate.conversation_id
        model.question = candidate.question
        model.ai_answer = candidate.ai_answer
        model.manager_answer = candidate.manager_answer
        model.source_refs_json = json.dumps(candidate.source_refs, ensure_ascii=False)
        model.intent = candidate.intent
        model.reason = candidate.reason
        model.status = candidate.status.value
        model.created_at = candidate.created_at
        model.reviewed_at = candidate.reviewed_at
        model.reviewed_by = candidate.reviewed_by
        model.published_knowledge_id = candidate.published_knowledge_id
        model.kb_version = candidate.kb_version

    def _candidate_to_domain(self, model: KnowledgeCandidateModel) -> KnowledgeCandidate:
        refs_raw = model.source_refs_json or "[]"
        try:
            refs = json.loads(refs_raw)
            if not isinstance(refs, list):
                refs = []
        except json.JSONDecodeError:
            refs = []
        return KnowledgeCandidate(
            id=model.id,
            conversation_id=model.conversation_id,
            question=model.question,
            ai_answer=model.ai_answer,
            manager_answer=model.manager_answer,
            source_refs=[str(item) for item in refs],
            intent=model.intent,
            reason=model.reason,
            status=KnowledgeCandidateStatus(model.status),
            created_at=model.created_at,
            reviewed_at=model.reviewed_at,
            reviewed_by=model.reviewed_by,
            published_knowledge_id=model.published_knowledge_id,
            kb_version=model.kb_version,
        )

    def _event_to_model(self, event: LearningEvent) -> LearningEventModel:
        return LearningEventModel(
            id=event.id,
            conversation_id=event.conversation_id,
            event_type=event.event_type.value,
            payload_json=json.dumps(event.payload, ensure_ascii=False),
            created_at=event.created_at,
        )

    def _event_to_domain(self, model: LearningEventModel) -> LearningEvent:
        payload_raw = model.payload_json or "{}"
        try:
            payload = json.loads(payload_raw)
            if not isinstance(payload, dict):
                payload = {}
        except json.JSONDecodeError:
            payload = {}
        return LearningEvent(
            id=model.id,
            conversation_id=model.conversation_id,
            event_type=LearningEventType(model.event_type),
            payload={str(key): str(value) for key, value in payload.items()},
            created_at=model.created_at,
        )
