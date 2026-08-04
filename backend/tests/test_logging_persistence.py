from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai_core.core import AICore
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.validator import AIValidator
from app.contracts.knowledge_provider import KnowledgeProvider
from app.core.constants import ChannelType, MessageDirection
from app.db.models import Base
from app.domain.messages import Message
from app.domain.pipeline_events import PipelineEventType
from app.domain.processing import ProcessingDecision
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.source_selector import SourceSelector
from app.main import app
from app.prompt_builder import DefaultPromptBuilder
from app.repositories.conversations import InMemoryConversationRepository
from app.repositories.manager_queue import InMemoryManagerQueueRepository
from app.repositories.sessions import InMemorySessionRepository
from app.services.conversation_state_service import ConversationStateService
from app.services.decision_router import DefaultDecisionRouter
from app.services.handoff_manager import DefaultHandoffManager
from app.services.logging_service import InMemoryLoggingService, SqlAlchemyLoggingService
from app.services.message_pipeline import MessagePipelineService
from app.services.response_sender import InMemoryResponseSender


class StubLLMProvider(LLMProvider):
    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        return "Цена насоса 1000 рублей."


class StubKnowledgeProvider(KnowledgeProvider):
    def __init__(self, sources: list[VerifiedSource] | None = None) -> None:
        self._sources = sources or []

    async def search(self, query: str) -> SourceSelectionResult:
        return SourceSelectionResult(query=query, sources=list(self._sources))


def _price_source() -> VerifiedSource:
    return VerifiedSource(
        source_id="P-1",
        source_type="knowledge_base",
        title="Насос",
        content="Насос",
        metadata={"confirmed_fields": "name,price,sku"},
    )


def _session_factory(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_sqlalchemy_logging_persists_and_survives_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "processing_logs.db"
    logger1 = SqlAlchemyLoggingService(session_factory=_session_factory(db_path))
    await logger1.log_audit(
        PipelineEventType.MESSAGE_RECEIVED.value,
        {"request_id": "req-log-1", "channel": "max"},
        category="pipeline",
    )

    logger2 = SqlAlchemyLoggingService(session_factory=_session_factory(db_path))
    events = await logger2.list_events(request_id="req-log-1")

    assert len(events) == 1
    assert events[0]["event_type"] == PipelineEventType.MESSAGE_RECEIVED.value


@pytest.mark.asyncio
async def test_pipeline_logs_handoff_sequence_without_sources() -> None:
    logging_service = InMemoryLoggingService()
    pipeline = MessagePipelineService(
        conversation_state=ConversationStateService(
            session_repository=InMemorySessionRepository(),
            conversation_repository=InMemoryConversationRepository(),
        ),
        source_selector=SourceSelector(providers=[StubKnowledgeProvider([])]),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(llm_provider=StubLLMProvider(), validator=AIValidator()),
        logging_service=logging_service,
    )
    router = DefaultDecisionRouter(
        response_sender=InMemoryResponseSender(),
        handoff_manager=DefaultHandoffManager(InMemoryManagerQueueRepository()),
        logging_service=logging_service,
    )
    message = Message(
        text="Сколько стоит насос?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-log-1",
    )

    result = await pipeline.process(message)
    await router.route(result)

    event_types = [record.event_type for record in logging_service.records]
    assert event_types == [
        PipelineEventType.MESSAGE_RECEIVED.value,
        PipelineEventType.SOURCES_SELECTED.value,
        PipelineEventType.PROMPT_BUILT.value,
        PipelineEventType.VALIDATOR_DECISION.value,
        "processing",
        PipelineEventType.DECISION_ROUTER.value,
        PipelineEventType.HANDOFF.value,
    ]
    assert result.decision == ProcessingDecision.HANDOFF
    assert PipelineEventType.LLM_CALLED.value not in event_types
    assert PipelineEventType.RESPONSE_SENT.value not in event_types


@pytest.mark.asyncio
async def test_pipeline_logs_approved_sequence_with_sources() -> None:
    logging_service = InMemoryLoggingService()
    pipeline = MessagePipelineService(
        conversation_state=ConversationStateService(
            session_repository=InMemorySessionRepository(),
            conversation_repository=InMemoryConversationRepository(),
        ),
        source_selector=SourceSelector(providers=[StubKnowledgeProvider([_price_source()])]),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(llm_provider=StubLLMProvider(), validator=AIValidator()),
        logging_service=logging_service,
    )
    router = DefaultDecisionRouter(
        response_sender=InMemoryResponseSender(),
        handoff_manager=DefaultHandoffManager(InMemoryManagerQueueRepository()),
        logging_service=logging_service,
    )
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.WEBSITE_CHAT,
        direction=MessageDirection.INBOUND,
        customer_id="c-log-2",
    )

    result = await pipeline.process(message)
    await router.route(result)

    event_types = [record.event_type for record in logging_service.records]
    assert event_types == [
        PipelineEventType.MESSAGE_RECEIVED.value,
        PipelineEventType.SOURCES_SELECTED.value,
        PipelineEventType.PROMPT_BUILT.value,
        PipelineEventType.LLM_CALLED.value,
        PipelineEventType.VALIDATOR_DECISION.value,
        "processing",
        PipelineEventType.DECISION_ROUTER.value,
        PipelineEventType.RESPONSE_SENT.value,
    ]
    assert result.decision == ProcessingDecision.RESPOND
    assert PipelineEventType.HANDOFF.value not in event_types


@pytest.mark.asyncio
async def test_webhook_persists_pipeline_events() -> None:
    from app.services.composition import get_logging_service

    with TestClient(app) as client:
        response = client.post(
            "/channels/max/webhook",
            json={
                "text": "Сколько стоит насос?",
                "user_id": "log-user-1",
                "contact": "+79990000099",
            },
        )
        assert response.status_code == 200
        events = await get_logging_service().list_events()

    event_types = [event["event_type"] for event in events]
    assert PipelineEventType.MESSAGE_RECEIVED.value in event_types
    assert PipelineEventType.SOURCES_SELECTED.value in event_types
    assert PipelineEventType.PROMPT_BUILT.value in event_types
    assert PipelineEventType.DECISION_ROUTER.value in event_types
    assert PipelineEventType.HANDOFF.value in event_types


def test_ai_core_does_not_know_logging_service() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "LoggingService" not in source
    assert "log_audit" not in source
    assert "PipelineEventType" not in source
