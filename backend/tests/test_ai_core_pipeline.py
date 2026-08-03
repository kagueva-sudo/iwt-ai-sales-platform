import pytest

from app.ai_core.core import AICore
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.validator import AIValidator
from app.contracts.knowledge_provider import KnowledgeProvider
from app.core.constants import ChannelType, HandoffReason, MessageDirection
from app.core.errors import ProviderError
from app.domain.messages import Message
from app.domain.processing import ProcessingDecision
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.source_selector import SourceSelector
from app.prompt_builder import DefaultPromptBuilder
from app.repositories.conversations import InMemoryConversationRepository
from app.repositories.sessions import InMemorySessionRepository
from app.services.conversation_state_service import ConversationStateService
from app.services.message_pipeline import MessagePipelineService


pytestmark = pytest.mark.asyncio


class StubLLMProvider(LLMProvider):
    def __init__(self, text: str = "Цена насоса 1000 рублей.") -> None:
        self.text = text

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        assert "Verified sources" in system_prompt
        return self.text


class FailingLLMProvider(LLMProvider):
    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        raise ProviderError("LLM failed.")


class StubKnowledgeProvider(KnowledgeProvider):
    def __init__(self, sources: list[VerifiedSource] | None = None) -> None:
        self._sources = sources or []

    async def search(self, query: str) -> SourceSelectionResult:
        return SourceSelectionResult(query=query, sources=list(self._sources))


def _build_pipeline(
    llm: LLMProvider,
    sources: list[VerifiedSource] | None = None,
) -> MessagePipelineService:
    conversation_state = ConversationStateService(
        session_repository=InMemorySessionRepository(),
        conversation_repository=InMemoryConversationRepository(),
    )
    return MessagePipelineService(
        conversation_state=conversation_state,
        source_selector=SourceSelector(providers=[StubKnowledgeProvider(sources)]),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(llm_provider=llm, validator=AIValidator()),
    )


def _price_source(*, confirmed_price: bool) -> VerifiedSource:
    confirmed = "name,price,sku" if confirmed_price else "name,sku"
    return VerifiedSource(
        source_id="P-1",
        source_type="knowledge_base",
        title="Насос",
        content="Насос промышленный",
        metadata={"confirmed_fields": confirmed},
    )


async def test_pipeline_responds_with_confirmed_sources() -> None:
    pipeline = _build_pipeline(StubLLMProvider(), sources=[_price_source(confirmed_price=True)])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == "Цена насоса 1000 рублей."
    assert "P-1" in result.sources
    assert result.metadata["session_id"]
    assert result.metadata["dialog_id"]


async def test_pipeline_handoff_without_sources() -> None:
    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.HANDOFF
    assert result.handoff_reason == HandoffReason.NO_CONFIRMED_DATA


async def test_pipeline_needs_more_data_when_price_not_confirmed() -> None:
    pipeline = _build_pipeline(StubLLMProvider(), sources=[_price_source(confirmed_price=False)])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.NEEDS_MORE_DATA
    assert "price" in result.metadata.get("reason", "")


async def test_ai_core_returns_error_on_llm_failure() -> None:
    pipeline = _build_pipeline(FailingLLMProvider(), sources=[_price_source(confirmed_price=True)])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.ERROR
    assert result.handoff_reason == HandoffReason.LLM_ERROR
    assert result.errors == ["LLM failed."]


async def test_ai_core_does_not_import_providers() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "WebsiteProvider" not in source
    assert "KnowledgeRepository" not in source
    assert "HandoffService" not in source
    assert "HandoffManager" not in source
    assert "DecisionRouter" not in source
    assert "product_provider" not in source
    assert "from app.providers" not in source
    assert "from app.knowledge_layer" not in source
    assert "from app.api" not in source
