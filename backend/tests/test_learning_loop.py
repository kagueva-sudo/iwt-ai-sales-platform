"""Learning Loop v1 tests — outside AI Core."""

from pathlib import Path

import pytest

from app.ai_core import core as ai_core_module
from app.core.constants import ChannelType, HandoffReason
from app.core.errors import ProviderError
from app.domain.manager_queue import ManagerQueueStatus
from app.domain.processing import ProcessingDecision, ProcessingResult
from app.learning.candidate_service import CandidateService
from app.learning.eligibility import is_candidate_eligible
from app.learning.evaluation import run_evaluation_file
from app.learning.models import KnowledgeCandidate, KnowledgeCandidateStatus, LearningEventType
from app.learning.repository import InMemoryLearningRepository
from app.learning.service import LearningService
from app.repositories.knowledge import InMemoryKnowledgeRepository
from app.repositories.manager_queue import InMemoryManagerQueueRepository
from app.services.handoff_manager import DefaultHandoffManager
from app.services.logging_service import InMemoryLoggingService
from app.services.manager_queue_service import ManagerQueueService


pytestmark = pytest.mark.asyncio

ROOT = Path(__file__).resolve().parents[2]


def _handoff_result(**kwargs) -> ProcessingResult:
    defaults = {
        "decision": ProcessingDecision.HANDOFF,
        "response_text": "Передаю менеджеру",
        "request_id": "req-learn-1",
        "channel": ChannelType.MAX,
        "customer_name": "Клиент",
        "customer_contact": "+79991112233",
        "conversation_history": ["Какая гарантия на сервер?"],
        "handoff_reason": HandoffReason.NO_CONFIRMED_DATA,
        "sources": ["kb:faq"],
        "metadata": {"intent": "warranty"},
    }
    defaults.update(kwargs)
    return ProcessingResult(**defaults)


async def test_learning_event_on_handoff() -> None:
    learning_repo = InMemoryLearningRepository()
    learning = LearningService(learning_repo)
    queue = InMemoryManagerQueueRepository()
    manager = DefaultHandoffManager(queue, learning_service=learning)

    request_id = await manager.create_handoff(_handoff_result())
    events = await learning_repo.list_events(conversation_id=request_id)
    assert any(event.event_type == LearningEventType.HANDOFF for event in events)


async def test_candidate_created_for_eligible_handoff() -> None:
    learning_repo = InMemoryLearningRepository()
    learning = LearningService(learning_repo)
    queue = InMemoryManagerQueueRepository()
    manager = DefaultHandoffManager(queue, learning_service=learning)

    request_id = await manager.create_handoff(_handoff_result())
    candidates = await learning_repo.list_candidates()
    assert len(candidates) == 1
    assert candidates[0].conversation_id == request_id
    assert candidates[0].status == KnowledgeCandidateStatus.PENDING
    assert candidates[0].question == "Какая гарантия на сервер?"


async def test_no_candidate_for_price_unknown() -> None:
    learning_repo = InMemoryLearningRepository()
    learning = LearningService(learning_repo)
    queue = InMemoryManagerQueueRepository()
    manager = DefaultHandoffManager(queue, learning_service=learning)

    await manager.create_handoff(
        _handoff_result(
            handoff_reason=HandoffReason.PRICE_UNKNOWN,
            metadata={"intent": "price"},
            conversation_history=["Сколько стоит ноутбук?"],
        )
    )
    assert await learning_repo.list_candidates() == []
    events = await learning_repo.list_events()
    assert any(event.event_type == LearningEventType.HANDOFF for event in events)
    assert not is_candidate_eligible(
        handoff_reason=HandoffReason.PRICE_UNKNOWN,
        intent="price",
    )


async def test_manager_done_fills_manager_answer() -> None:
    learning_repo = InMemoryLearningRepository()
    learning = LearningService(learning_repo)
    queue = InMemoryManagerQueueRepository()
    handoff = DefaultHandoffManager(queue, learning_service=learning)
    mq = ManagerQueueService(queue, learning_service=learning)

    request_id = await handoff.create_handoff(_handoff_result())
    updated = await mq.update_status(
        request_id,
        ManagerQueueStatus.DONE,
        manager_answer="Гарантия 12 месяцев от производителя.",
    )
    assert updated is not None
    candidate = await learning_repo.find_candidate_by_conversation(request_id)
    assert candidate is not None
    assert candidate.manager_answer == "Гарантия 12 месяцев от производителя."
    events = await learning_repo.list_events(conversation_id=request_id)
    assert any(event.event_type == LearningEventType.MANAGER_CORRECTION for event in events)


async def test_approve_and_reject() -> None:
    learning_repo = InMemoryLearningRepository()
    knowledge_repo = InMemoryKnowledgeRepository()
    logging = InMemoryLoggingService()
    learning = LearningService(learning_repo)
    candidates = CandidateService(learning_repo, knowledge_repo, logging)

    await learning.on_handoff(_handoff_result(), "req-approve")
    pending = (await learning_repo.list_candidates())[0]
    pending.manager_answer = "Ответ менеджера по FAQ."
    await learning_repo.update_candidate(pending)

    approved = await candidates.approve(pending.id, reviewed_by="manager-1")
    assert approved.status == KnowledgeCandidateStatus.APPROVED
    assert approved.published_knowledge_id is not None
    kb_items = await knowledge_repo.list_all()
    assert any(item.id == approved.published_knowledge_id for item in kb_items)
    assert "price" not in (kb_items[0].confirmed_fields or set())

    await learning.on_handoff(
        _handoff_result(request_id="req-reject", conversation_history=["Условия доставки?"]),
        "req-reject",
    )
    reject_pending = [
        item for item in await learning_repo.list_candidates(status=KnowledgeCandidateStatus.PENDING)
    ][0]
    rejected = await candidates.reject(
        reject_pending.id,
        reviewed_by="manager-1",
        reason="дубликат",
    )
    assert rejected.status == KnowledgeCandidateStatus.REJECTED
    assert rejected.reason == "дубликат"


async def test_no_autopublish_without_approve() -> None:
    learning_repo = InMemoryLearningRepository()
    knowledge_repo = InMemoryKnowledgeRepository()
    learning = LearningService(learning_repo)
    CandidateService(learning_repo, knowledge_repo)

    await learning.on_handoff(_handoff_result(), "req-no-auto")
    assert len(await knowledge_repo.list_all()) == 0
    assert (await learning_repo.list_candidates())[0].status == KnowledgeCandidateStatus.PENDING


async def test_cannot_approve_price_intent() -> None:
    learning_repo = InMemoryLearningRepository()
    knowledge_repo = InMemoryKnowledgeRepository()
    service = CandidateService(learning_repo, knowledge_repo)
    candidate = KnowledgeCandidate(
        conversation_id="c-price",
        question="Сколько стоит?",
        ai_answer="Цена 100000",
        manager_answer="Цена 99999",
        intent="price",
    )
    await learning_repo.add_candidate(candidate)
    with pytest.raises(ProviderError, match="Commercial dynamic facts"):
        await service.approve(candidate.id, reviewed_by="m1")
    assert len(await knowledge_repo.list_all()) == 0


async def test_dynamic_fact_safety_evaluation() -> None:
    dataset = ROOT / "knowledge" / "learning" / "evaluation_dataset.jsonl"
    metrics = run_evaluation_file(dataset)
    assert metrics.total >= 4
    assert metrics.dynamic_fact_safety == 1.0
    assert metrics.hallucination_rate == 0.0


async def test_ai_core_does_not_import_learning() -> None:
    source = Path(ai_core_module.__file__).read_text(encoding="utf-8")
    assert "app.learning" not in source
    assert "KnowledgeCandidate" not in source
    assert "LearningService" not in source
    assert "LearningRepository" not in source
