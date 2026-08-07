import pytest

from app.core.constants import ChannelType, HandoffReason
from app.domain.manager_queue import ManagerQueueStatus
from app.domain.processing import ProcessingDecision, ProcessingResult
from app.repositories.manager_queue import InMemoryManagerQueueRepository
from app.services.decision_router import DefaultDecisionRouter
from app.services.handoff_manager import DefaultHandoffManager
from app.services.logging_service import InMemoryLoggingService
from app.services.response_sender import InMemoryResponseSender


pytestmark = pytest.mark.asyncio


def _build_router() -> tuple[
    DefaultDecisionRouter,
    InMemoryResponseSender,
    InMemoryManagerQueueRepository,
    InMemoryLoggingService,
]:
    sender = InMemoryResponseSender()
    queue = InMemoryManagerQueueRepository()
    logging_service = InMemoryLoggingService()
    router = DefaultDecisionRouter(
        response_sender=sender,
        handoff_manager=DefaultHandoffManager(queue),
        logging_service=logging_service,
    )
    return router, sender, queue, logging_service


def _result(decision: ProcessingDecision, **kwargs) -> ProcessingResult:
    defaults = {
        "response_text": "Ответ",
        "request_id": "req-1",
        "channel": ChannelType.MAX,
        "customer_name": "Иван",
        "customer_contact": "+79990001122",
        "conversation_history": ["Какая цена насоса?"],
        "handoff_reason": HandoffReason.NO_CONFIRMED_DATA,
        "sources": ["P-1"],
        "errors": [],
    }
    defaults.update(kwargs)
    return ProcessingResult(decision=decision, **defaults)


async def test_router_sends_approved_response_and_logs() -> None:
    router, sender, queue, logging_service = _build_router()

    await router.route(_result(ProcessingDecision.RESPOND, handoff_reason=None))

    assert len(sender.sent) == 1
    assert sender.sent[0].text == "Ответ"
    assert sender.sent[0].channel == ChannelType.MAX
    assert await queue.list_by_status(ManagerQueueStatus.NEW) == []
    assert any(record.category == "ai" for record in logging_service.records)


async def test_router_enqueues_handoff_and_logs() -> None:
    router, sender, queue, logging_service = _build_router()

    await router.route(_result(ProcessingDecision.HANDOFF))

    items = await queue.list_by_status(ManagerQueueStatus.NEW)
    assert len(sender.sent) == 1
    assert sender.sent[0].text == "Ответ"
    assert len(items) == 1
    item = items[0]
    assert item.request_id == "req-1"
    assert item.channel == ChannelType.MAX
    assert item.customer_name == "Иван"
    assert item.customer_contact == "+79990001122"
    assert item.conversation_history == ["Какая цена насоса?"]
    assert item.ai_response == "Ответ"
    assert item.handoff_reason == HandoffReason.NO_CONFIRMED_DATA
    assert item.status == ManagerQueueStatus.NEW
    assert item.created_at is not None
    assert any(record.category == "ai" for record in logging_service.records)


async def test_router_enqueues_needs_more_data_as_handoff() -> None:
    router, sender, queue, _logging_service = _build_router()

    await router.route(_result(ProcessingDecision.NEEDS_MORE_DATA))

    assert len(sender.sent) == 1
    assert len(await queue.list_by_status(ManagerQueueStatus.NEW)) == 1


async def test_router_logs_error_and_sends_safe_text() -> None:
    router, sender, queue, logging_service = _build_router()

    await router.route(
        _result(
            ProcessingDecision.ERROR,
            errors=["LLM failed."],
            handoff_reason=HandoffReason.LLM_ERROR,
        )
    )

    assert len(sender.sent) == 1
    assert sender.sent[0].text == "Ответ"
    assert await queue.list_by_status(ManagerQueueStatus.NEW) == []
    assert any(record.category == "ai" for record in logging_service.records)
    assert any(record.category == "error" for record in logging_service.records)


async def test_manager_queue_status_updates() -> None:
    queue = InMemoryManagerQueueRepository()
    manager = DefaultHandoffManager(queue)
    request_id = await manager.create_handoff(_result(ProcessingDecision.HANDOFF))

    updated = await queue.update_status(request_id, ManagerQueueStatus.IN_PROGRESS)
    assert updated is not None
    assert updated.status == ManagerQueueStatus.IN_PROGRESS

    done = await queue.update_status(request_id, ManagerQueueStatus.DONE)
    assert done is not None
    assert done.status == ManagerQueueStatus.DONE

    cancelled_id = await manager.create_handoff(
        _result(ProcessingDecision.HANDOFF, request_id="req-2")
    )
    cancelled = await queue.update_status(cancelled_id, ManagerQueueStatus.CANCELLED)
    assert cancelled is not None
    assert cancelled.status == ManagerQueueStatus.CANCELLED


async def test_ai_core_does_not_know_sprint7_components() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "DecisionRouter" not in source
    assert "HandoffManager" not in source
    assert "ResponseSender" not in source
    assert "LoggingService" not in source
    assert "ManagerQueue" not in source
    assert "from app.services" not in source


async def test_decision_router_stays_thin() -> None:
    import app.services.decision_router as router_module

    source = open(router_module.__file__, encoding="utf-8").read()
    assert "AIValidator" not in source
    assert "LLMProvider" not in source
    assert "PromptBuilder" not in source
    assert "SourceSelector" not in source
    assert "confirmed_fields" not in source
    assert "generate_response" not in source
