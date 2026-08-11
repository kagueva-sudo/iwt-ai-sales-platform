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


async def test_pipeline_stock_question_gives_site_guidance() -> None:
    from app.ai_core.prompts import CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="У вас есть в наличии ноутбуки?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE.format(category="ноутбуки")
    assert result.metadata.get("reason") == "category_price_narrowing"


async def test_pipeline_buyback_question_answers_no() -> None:
    from app.ai_core.prompts import NO_BUYBACK_MESSAGE

    # Wrong KB hit (selection FAQ) must not override buyback policy.
    wrong = VerifiedSource(
        source_id="faq-pc-selection",
        source_type="knowledge_base",
        title="Помощь с выбором",
        content="Помощь с выбором техники в IWT.",
        metadata={"confirmed_fields": "content"},
    )
    pipeline = _build_pipeline(StubLLMProvider(), sources=[wrong])
    message = Message(
        text="Вы скупаете ноутбуки?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == NO_BUYBACK_MESSAGE
    assert result.metadata.get("reason") == "no_buyback"
    assert "не скупает" in (result.response_text or "").lower()


async def test_pipeline_buyback_without_question_mark() -> None:
    from app.ai_core.prompts import NO_BUYBACK_MESSAGE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    for text in (
        "Вы покупаете б/у",
        "вы покупаете ноутбуки",
        "Принимаете б/у технику",
        "Скупаете компьютеры",
    ):
        message = Message(
            text=text,
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="c-1",
        )
        result = await pipeline.process(message)
        assert result.decision == ProcessingDecision.RESPOND, text
        assert result.response_text == NO_BUYBACK_MESSAGE, text
        assert result.metadata.get("reason") == "no_buyback", text


async def test_pipeline_greets_on_hello_without_sources() -> None:
    from app.ai_core.prompts import GREETING_MESSAGE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="Привет",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == GREETING_MESSAGE
    assert result.metadata.get("reason") == "conversational_greeting"


async def test_pipeline_greets_despite_unrelated_kb_sources() -> None:
    from app.ai_core.prompts import GREETING_MESSAGE

    payment = VerifiedSource(
        source_id="payment-overview",
        source_type="knowledge_base",
        title="Способы оплаты",
        content="Способы оплаты IWT.ru: вернуть деньги на карту.",
        metadata={"confirmed_fields": "content,payment_terms"},
    )
    pipeline = _build_pipeline(FailingLLMProvider(), sources=[payment])
    message = Message(
        text="добрый день",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == GREETING_MESSAGE
    assert "Способы оплаты" not in (result.response_text or "")
    assert result.metadata.get("reason") == "conversational_greeting"


async def test_pipeline_greets_on_start_without_sources() -> None:
    from app.ai_core.prompts import GREETING_MESSAGE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="/start",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert "IWT.ru" in (result.response_text or "")
    assert result.response_text == GREETING_MESSAGE


async def test_pipeline_price_without_sources_gives_site_guidance() -> None:
    from app.ai_core.prompts import STOCK_PRICE_GUIDANCE_MESSAGE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == STOCK_PRICE_GUIDANCE_MESSAGE
    assert result.metadata.get("reason") == "stock_price_guidance"


async def test_pipeline_handoff_without_sources_for_non_stock_price() -> None:
    pipeline = _build_pipeline(StubLLMProvider(), sources=[])
    message = Message(
        text="Какая мощность насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.HANDOFF
    assert result.handoff_reason == HandoffReason.NO_CONFIRMED_DATA


async def test_pipeline_price_guidance_when_price_not_confirmed() -> None:
    from app.ai_core.prompts import STOCK_PRICE_GUIDANCE_MESSAGE

    pipeline = _build_pipeline(StubLLMProvider(), sources=[_price_source(confirmed_price=False)])
    message = Message(
        text="Какая цена насоса?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == STOCK_PRICE_GUIDANCE_MESSAGE
    assert result.metadata.get("reason") == "stock_price_guidance"


async def test_pipeline_falls_back_to_kb_when_llm_fails() -> None:
    source = VerifiedSource(
        source_id="delivery-1",
        source_type="knowledge_base",
        title="Доставка",
        content="Бесплатная доставка от 5000 рублей.",
        metadata={"confirmed_fields": "content,delivery_terms"},
    )
    pipeline = _build_pipeline(FailingLLMProvider(), sources=[source])
    message = Message(
        text="Доставка платная?",
        channel=ChannelType.MAX,
        direction=MessageDirection.INBOUND,
        customer_id="c-1",
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert "Бесплатная доставка" in (result.response_text or "")
    assert result.metadata.get("reason") == "llm_fallback_kb"


async def test_ai_core_returns_error_on_llm_failure_without_covering_sources() -> None:
    pipeline = _build_pipeline(FailingLLMProvider(), sources=[_price_source(confirmed_price=False)])
    message = Message(
        text="Какая мощность насоса?",
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
